"""
agents.py — 부품 ⑤ 서브에이전트 ('짓는 AI' vs '검사하는 AI' 분리)

코드를 짠 모델은 자기 결과를 후하게 본다.
  실측 예: 같은 글을 자기채점 9.04 / 독립채점 7.43 → 1.6점 갭.
그래서 generator 와 verifier 를 '반드시 다른 에이전트'(가능하면 다른 모델)로 분리하고,
같은 모델 계열이면 self-bias 경고 플래그를 강제로 단다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .llm import LLMClient, Message
from .verifier import CheckSuite, Rubric, Verdict


# ---------------------------------------------------------------------------
# 모델 계열 판정 (self-bias 경고용)
# ---------------------------------------------------------------------------
def _model_family(model: str) -> str:
    """대략적인 계열 추출. 'qwen3.5-397b' -> 'qwen', 'gpt-oss-20b' -> 'gpt-oss'..."""
    m = (model or "").lower()
    for fam in ("qwen", "glm", "gpt-oss", "gemma", "llama", "mistral", "deepseek", "claude"):
        if fam in m:
            return fam
    return m.split("-")[0] if m else "unknown"


def same_family(a: str, b: str) -> bool:
    return _model_family(a) == _model_family(b)


# ---------------------------------------------------------------------------
# Agent 베이스
# ---------------------------------------------------------------------------
@dataclass
class Agent:
    """역할 + 시스템 프롬프트 + 모델 + LLM 클라이언트."""
    name: str
    role_system: str
    client: LLMClient
    model: Optional[str] = None
    temperature: Optional[float] = None
    history: List[Message] = field(default_factory=list)

    def run(self, user_prompt: str, keep_history: bool = False,
            extra_system: str = "") -> str:
        sys = self.role_system
        if extra_system:
            sys = f"{sys}\n\n{extra_system}"
        msgs: List[Message] = [{"role": "system", "content": sys}]
        if keep_history:
            msgs.extend(self.history)
        msgs.append({"role": "user", "content": user_prompt})
        out = self.client.chat(
            msgs,
            model=self.model or self.client.cfg.generator_model,
            temperature=self.temperature,
        ).text
        if keep_history:
            self.history.append({"role": "user", "content": user_prompt})
            self.history.append({"role": "assistant", "content": out})
        return out


# ---------------------------------------------------------------------------
# Generator — '짓는 AI'
# ---------------------------------------------------------------------------
class Generator(Agent):
    def __init__(self, client: LLMClient, name: str = "generator",
                 role_system: Optional[str] = None,
                 model: Optional[str] = None,
                 temperature: Optional[float] = None):
        super().__init__(
            name=name,
            role_system=role_system or (
                "너는 작업을 '완성된 형태로' 산출하는 실행 에이전트다. "
                "추측으로 빈칸을 메우지 말고, 주어진 스킬/계약/맥락을 따른다. "
                "요청된 산출물만 출력하고 군더더기 설명은 생략한다."
            ),
            client=client,
            model=model or client.cfg.generator_model,
            temperature=temperature if temperature is not None else client.cfg.temperature,
        )

    def generate(self, goal: str, context: str = "",
                 prior_feedback: str = "") -> str:
        prompt = f"[목표]\n{goal}\n"
        if context:
            prompt += f"\n[맥락/스킬/계약]\n{context}\n"
        if prior_feedback:
            prompt += f"\n[직전 검증 피드백 — 반드시 반영]\n{prior_feedback}\n"
        prompt += "\n위 목표를 만족하는 산출물을 작성하라."
        return self.run(prompt)


# ---------------------------------------------------------------------------
# Verifier — '검사하는 AI' (반드시 generator 와 분리)
# ---------------------------------------------------------------------------
class VerifierAgent:
    """하드체크(CheckSuite) + LLM 루브릭(Rubric) 으로 Verdict 생성.

    generator_model 을 받아 self-bias 를 자동 감지한다.
    """

    def __init__(self, client: LLMClient,
                 check_suite: Optional[CheckSuite] = None,
                 rubric: Optional[Rubric] = None,
                 verifier_model: Optional[str] = None,
                 generator_model: Optional[str] = None,
                 name: str = "verifier"):
        self.name = name
        self.client = client
        self.checks = check_suite or CheckSuite()
        self.rubric = rubric
        self.verifier_model = verifier_model or client.cfg.verifier_model
        self.generator_model = generator_model or client.cfg.generator_model

    def verify(self, artifact: str, goal: str,
               ctx: Optional[dict] = None) -> Verdict:
        # 1) 하드 체크 (closed loop floor)
        check_results = self.checks.run(artifact, ctx or {})
        # critical=False 인 체크는 stop 막지 않게: critical 실패만 본다
        critical_fail = any(
            (not r.passed) and getattr(c, "critical", True)
            for r, c in zip(check_results, self.checks.checks)
        )

        # 2) LLM 루브릭 (open loop quality bar)
        rubric_res = None
        if self.rubric is not None:
            rubric_res = self.rubric.judge(
                self.client, artifact, goal, model=self.verifier_model)

        # 3) self-bias 경고
        bias = same_family(self.generator_model, self.verifier_model)

        rubric_ok = (rubric_res is None) or rubric_res.passed
        done = (not critical_fail) and rubric_ok

        return Verdict(
            done=done,
            check_results=check_results,
            rubric=rubric_res,
            self_bias_warning=bias,
            notes=("" if not bias else
                   f"generator={self.generator_model} / verifier={self.verifier_model}"),
        )
