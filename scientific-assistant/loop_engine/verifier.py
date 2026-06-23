"""
verifier.py — 루프의 병목. "verifier 작성이 새로운 프롬프트 엔지니어링."

generator(모델)는 이제 충분히 좋고 거의 공짜로 반복된다.
그 결과가 가치 있는지 '판정'하는 verifier 가 진짜 병목이다.
verifier 가 약하면 루프는 조용히 망하는 게 아니라, 쓰레기를 자신있게 수백 번 만든다.

두 종류:
  - Check     : 측정 가능한 하드 패스 (closed loop). 코드로 yes/no.
  - Rubric    : LLM 채점 (open loop). 점수 + 통과기준.
Verdict 가 둘을 합쳐 done? / retry? 를 결정한다.

verifier 는 곧 reward function 이다. 당신의 도메인 지식이 곧 보상함수다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Check — 하드 패스 (closed loop)
# ---------------------------------------------------------------------------
@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""

    def __str__(self):
        mark = "PASS" if self.passed else "FAIL"
        return f"[{mark}] {self.name}" + (f" — {self.detail}" if self.detail else "")


class Check:
    """하나의 측정 가능한 합격 조건.
    fn(artifact, ctx) -> bool | (bool, str) 를 감싼다.
    """

    def __init__(self, name: str,
                 fn: Callable[..., Any],
                 critical: bool = True):
        self.name = name
        self.fn = fn
        self.critical = critical          # critical=False 면 통과 못 해도 stop 막지 않음(경고)

    def run(self, artifact: Any, ctx: Optional[dict] = None) -> CheckResult:
        try:
            out = self.fn(artifact, ctx or {})
        except TypeError:
            out = self.fn(artifact)       # ctx 안 받는 함수 허용
        if isinstance(out, tuple):
            passed, detail = bool(out[0]), str(out[1])
        else:
            passed, detail = bool(out), ""
        return CheckResult(self.name, passed, detail)


# --- 자주 쓰는 체크 빌더 (재사용) ---
def check_min_length(min_chars: int, name: Optional[str] = None) -> Check:
    def fn(art, ctx=None):
        s = art if isinstance(art, str) else str(art)
        return len(s) >= min_chars, f"len={len(s)} (>= {min_chars})"
    return Check(name or f"min_length>={min_chars}", fn)


def check_contains(substr: str, name: Optional[str] = None) -> Check:
    def fn(art, ctx=None):
        s = art if isinstance(art, str) else str(art)
        return (substr in s), f"contains '{substr}'"
    return Check(name or f"contains:{substr}", fn)


def check_regex(pattern: str, name: Optional[str] = None) -> Check:
    rx = re.compile(pattern)
    def fn(art, ctx=None):
        s = art if isinstance(art, str) else str(art)
        return bool(rx.search(s)), f"regex /{pattern}/"
    return Check(name or f"regex:{pattern}", fn)


def check_valid_json(name: str = "valid_json") -> Check:
    def fn(art, ctx=None):
        s = art if isinstance(art, str) else json.dumps(art)
        try:
            json.loads(s)
            return True, "json ok"
        except Exception as e:
            return False, f"json error: {e}"
    return Check(name, fn)


def check_python_syntax(name: str = "python_syntax") -> Check:
    def fn(art, ctx=None):
        s = art if isinstance(art, str) else str(art)
        try:
            compile(s, "<verify>", "exec")
            return True, "compiles"
        except SyntaxError as e:
            return False, f"SyntaxError: {e}"
    return Check(name, fn)


def check_no_placeholder(tokens=("TODO", "FIXME", "...전체", "생략"),
                         name: str = "no_placeholder") -> Check:
    def fn(art, ctx=None):
        s = art if isinstance(art, str) else str(art)
        hit = [t for t in tokens if t in s]
        return (len(hit) == 0), (f"발견: {hit}" if hit else "없음")
    return Check(name, fn)


def check_callable(fn: Callable[..., Any], name: str, critical: bool = True) -> Check:
    """임의 함수를 그대로 체크로. (테스트 실행, 외부 검증 등)"""
    return Check(name, fn, critical=critical)


class CheckSuite:
    """여러 체크 묶음. closed loop 의 '바닥(floor)'."""

    def __init__(self, checks: Optional[List[Check]] = None):
        self.checks: List[Check] = list(checks or [])

    def add(self, check: Check) -> "CheckSuite":
        self.checks.append(check)
        return self

    def run(self, artifact: Any, ctx: Optional[dict] = None) -> List[CheckResult]:
        return [c.run(artifact, ctx) for c in self.checks]


# ---------------------------------------------------------------------------
# Rubric — LLM 채점 (open loop)
# ---------------------------------------------------------------------------
@dataclass
class RubricResult:
    score: float            # 0~10
    passed: bool
    reasons: str = ""
    raw: str = ""


class Rubric:
    """LLM 으로 산출물을 0~10 채점. pass_score 이상이면 통과.
    judge_client 는 '검사하는 AI'(가능하면 generator 와 다른 모델!).
    """

    def __init__(self, criteria: str, pass_score: float = 8.0,
                 scale_max: float = 10.0):
        self.criteria = criteria
        self.pass_score = pass_score
        self.scale_max = scale_max

    def _prompt(self, artifact: str, goal: str) -> List[Dict[str, str]]:
        sys = (
            "너는 엄격한 평가자다. 절대 후하게 주지 마라. "
            "오직 JSON 으로만 답한다. 형식: "
            '{"score": <0~%g 실수>, "reasons": "<근거 한국어>"}' % self.scale_max
        )
        usr = (
            f"[목표]\n{goal}\n\n"
            f"[평가 기준]\n{self.criteria}\n\n"
            f"[평가 대상]\n{artifact}\n\n"
            "위 기준으로 채점하라. JSON 외 출력 금지."
        )
        return [{"role": "system", "content": sys},
                {"role": "user", "content": usr}]

    def judge(self, judge_client, artifact: str, goal: str,
              model: Optional[str] = None) -> RubricResult:
        msgs = self._prompt(artifact, goal)
        resp = judge_client.chat(
            msgs,
            model=model or judge_client.cfg.verifier_model,
            temperature=judge_client.cfg.verifier_temperature,
        )
        score, reasons = self._parse(resp.text)
        return RubricResult(
            score=score,
            passed=(score >= self.pass_score),
            reasons=reasons,
            raw=resp.text,
        )

    @staticmethod
    def _parse(text: str):
        # JSON 블록 추출 (코드펜스/잡설 방어)
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                d = json.loads(m.group(0))
                return float(d.get("score", 0)), str(d.get("reasons", "")).strip()
            except Exception:
                pass
        # 숫자라도 건진다
        m2 = re.search(r"(\d+(?:\.\d+)?)", text)
        return (float(m2.group(1)) if m2 else 0.0), text.strip()[:500]


# ---------------------------------------------------------------------------
# Verdict — 하드체크 + 루브릭 합산 판정
# ---------------------------------------------------------------------------
@dataclass
class Verdict:
    done: bool                                  # 출시 가능?
    check_results: List[CheckResult] = field(default_factory=list)
    rubric: Optional[RubricResult] = None
    self_bias_warning: bool = False             # generator==verifier 모델 경고
    notes: str = ""

    @property
    def critical_failures(self) -> List[CheckResult]:
        return [r for r in self.check_results if (not r.passed)]

    def summary(self) -> str:
        lines = [str(r) for r in self.check_results]
        if self.rubric:
            lines.append(f"[RUBRIC] score={self.rubric.score} "
                         f"pass={self.rubric.passed} :: {self.rubric.reasons[:160]}")
        if self.self_bias_warning:
            lines.append("⚠ SELF-BIAS: generator 와 verifier 가 같은 모델 계열 "
                         "— 점수 부풀려질 수 있음(평가자 분리 권장).")
        lines.append(f"=> DONE={self.done}")
        return "\n".join(lines)

    def feedback_for_retry(self) -> str:
        """generator 에게 되돌릴 때 줄 개선 지시."""
        parts = []
        for r in self.critical_failures:
            parts.append(f"- 실패: {r.name} :: {r.detail}")
        if self.rubric and not self.rubric.passed:
            parts.append(f"- 품질 미달(점수 {self.rubric.score}): {self.rubric.reasons}")
        return "다음을 고쳐서 다시 작성하라:\n" + "\n".join(parts) if parts else ""
