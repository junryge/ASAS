"""
tools.py — 부품 ④ 보강: 외부 도구/커넥터 (에이전트가 '실제 일'을 하게)

LLM 커넥터만으로는 글만 쓴다. 루프가 production 에서 가치를 내려면 에이전트가
실제로 뭔가를 '해야' 한다 — 내부 API 호출, Logpresso 쿼리, 파일 읽기/쓰기, 스크립트 실행.

폐쇄망 현실:
  내부 OpenAI 호환 서버(llama-cpp / vLLM)는 native function-calling 지원이 모델마다 들쭉날쭉.
  그래서 기본은 '텍스트 프로토콜'(ReAct식 JSON 액션) — 어떤 모델에서도 동작.
  native tools= 패스스루도 옵션으로 지원.

  Tool          : 이름 + 설명 + 인자스키마 + 파이썬 콜러블
  ToolRegistry  : 도구 모음
  ToolAgent     : 도구 사용 루프 (관찰->판단->행동 반복, max_steps 가드)
  ToolUsingGenerator : Loop 의 Generator 자리에 그대로 끼우는 어댑터
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .agents import Generator
from .llm import LLMClient, Message


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------
@dataclass
class Tool:
    """하나의 도구 = 이름 + 설명 + 인자설명 + 실행함수.
    fn(args: dict) -> str (관찰 결과 문자열).
    """
    name: str
    description: str
    fn: Callable[[Dict[str, Any]], Any]
    params: Dict[str, str] = field(default_factory=dict)   # 인자명 -> 설명

    def run(self, args: Dict[str, Any]) -> str:
        try:
            out = self.fn(args or {})
            return out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
        except Exception as e:
            return f"[TOOL ERROR] {self.name}: {e}"

    def to_openai_schema(self) -> dict:
        """native function-calling 패스스루용 스키마."""
        props = {k: {"type": "string", "description": v} for k, v in self.params.items()}
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": list(self.params.keys()),
                },
            },
        }

    def signature(self) -> str:
        """텍스트 프로토콜 프롬프트에 넣을 사람이 읽는 시그니처."""
        args = ", ".join(f"{k}(<{v}>)" for k, v in self.params.items()) or "없음"
        return f"- {self.name}: {self.description} | 인자: {args}"


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------
class ToolRegistry:
    def __init__(self, tools: Optional[List[Tool]] = None):
        self._tools: Dict[str, Tool] = {}
        for t in (tools or []):
            self.add(t)

    def add(self, tool: Tool) -> "ToolRegistry":
        self._tools[tool.name] = tool
        return self

    def tool(self, name: str, description: str,
             params: Optional[Dict[str, str]] = None):
        """데코레이터 등록: @registry.tool('name', 'desc', {'arg':'설명'})"""
        def deco(fn: Callable[[Dict[str, Any]], Any]) -> Callable:
            self.add(Tool(name=name, description=description, fn=fn,
                          params=params or {}))
            return fn
        return deco

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def names(self) -> List[str]:
        return sorted(self._tools)

    def all(self) -> List[Tool]:
        return [self._tools[n] for n in self.names()]

    def openai_schemas(self) -> List[dict]:
        return [t.to_openai_schema() for t in self.all()]

    def prompt_catalog(self) -> str:
        return "\n".join(t.signature() for t in self.all())


# ---------------------------------------------------------------------------
# ToolAgent — 텍스트 프로토콜 도구 사용 루프 (모델 무관)
# ---------------------------------------------------------------------------
_TOOL_PROTOCOL_SYSTEM = """너는 도구를 쓰는 에이전트다. 매 턴 아래 JSON 중 '하나'만 출력한다.

도구 호출:
{{"thought": "왜 이 도구를 쓰는지", "tool": "도구이름", "args": {{"인자명": "값"}}}}

작업 완료(최종 산출물):
{{"thought": "끝난 이유", "final": "<최종 산출물 전체>"}}

규칙:
- JSON 외 텍스트 절대 출력 금지. 코드펜스(```) 금지.
- 한 번에 도구 하나. 결과(관찰)를 받은 뒤 다음 판단.
- 추측으로 빈칸 메우지 말 것. 정보가 필요하면 도구로 가져온다.

[사용 가능한 도구]
{catalog}
"""


@dataclass
class ToolStep:
    kind: str           # "tool" | "final" | "error"
    thought: str = ""
    tool: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    observation: str = ""
    final: str = ""


@dataclass
class ToolRunResult:
    final: str
    steps: List[ToolStep] = field(default_factory=list)
    stopped_reason: str = "final"     # "final" | "max_steps"


class ToolAgent:
    """관찰->판단->행동 루프로 도구를 써서 작업을 완수.

    native=False(기본): 텍스트 JSON 프로토콜 — 모든 모델 호환(폐쇄망 안전).
    native=True       : 서버가 tools= 를 지원할 때 OpenAI tool_calls 사용.
    """

    def __init__(self, client: LLMClient, registry: ToolRegistry,
                 model: Optional[str] = None,
                 max_steps: int = 8,
                 temperature: float = 0.2,
                 native: bool = False,
                 name: str = "tool_agent"):
        self.name = name
        self.client = client
        self.registry = registry
        self.model = model or client.cfg.generator_model
        self.max_steps = max_steps
        self.temperature = temperature
        self.native = native

    # ---- 텍스트 프로토콜 ----
    def _run_text(self, task: str, context: str = "") -> ToolRunResult:
        sys = _TOOL_PROTOCOL_SYSTEM.format(catalog=self.registry.prompt_catalog())
        msgs: List[Message] = [{"role": "system", "content": sys}]
        user = task if not context else f"[맥락]\n{context}\n\n[작업]\n{task}"
        msgs.append({"role": "user", "content": user})

        steps: List[ToolStep] = []
        for _ in range(self.max_steps):
            text = self.client.chat(msgs, model=self.model,
                                    temperature=self.temperature).text
            action = self._parse_action(text)

            if action is None:
                # 프로토콜 위반 — 산출물로 간주하고 종료
                steps.append(ToolStep(kind="final", final=text))
                return ToolRunResult(final=text, steps=steps, stopped_reason="final")

            if "final" in action:
                fin = str(action.get("final", ""))
                steps.append(ToolStep(kind="final",
                                      thought=str(action.get("thought", "")),
                                      final=fin))
                return ToolRunResult(final=fin, steps=steps, stopped_reason="final")

            # 도구 호출
            tool_name = str(action.get("tool", ""))
            args = action.get("args", {}) or {}
            tool = self.registry.get(tool_name)
            if tool is None:
                obs = f"[ERROR] 알 수 없는 도구 '{tool_name}'. 사용 가능: {self.registry.names()}"
            else:
                obs = tool.run(args)
            steps.append(ToolStep(kind="tool",
                                  thought=str(action.get("thought", "")),
                                  tool=tool_name, args=args, observation=obs))
            # 대화에 행동+관찰을 이어붙임
            msgs.append({"role": "assistant", "content": text})
            msgs.append({"role": "user", "content": f"[관찰]\n{obs}\n\n다음 행동을 JSON 으로."})

        # max_steps 소진 — 마지막 관찰을 산출물로
        last_obs = steps[-1].observation if steps else ""
        return ToolRunResult(final=last_obs, steps=steps, stopped_reason="max_steps")

    # ---- native tool_calls ----
    def _run_native(self, task: str, context: str = "") -> ToolRunResult:
        msgs: List[Message] = []
        if context:
            msgs.append({"role": "system", "content": f"[맥락]\n{context}"})
        msgs.append({"role": "user", "content": task})

        steps: List[ToolStep] = []
        for _ in range(self.max_steps):
            resp = self.client.chat(
                msgs, model=self.model, temperature=self.temperature,
                extra={"tools": self.registry.openai_schemas(),
                       "tool_choice": "auto"})
            raw = resp.raw
            msg = (raw.get("choices") or [{}])[0].get("message", {})
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                fin = msg.get("content") or resp.text
                steps.append(ToolStep(kind="final", final=fin))
                return ToolRunResult(final=fin, steps=steps, stopped_reason="final")

            msgs.append(msg)  # assistant 메시지(툴콜 포함) 그대로 이어붙임
            for tc in tool_calls:
                fn = tc.get("function", {})
                tname = fn.get("name", "")
                try:
                    targs = json.loads(fn.get("arguments") or "{}")
                except Exception:
                    targs = {}
                tool = self.registry.get(tname)
                obs = tool.run(targs) if tool else f"[ERROR] unknown tool {tname}"
                steps.append(ToolStep(kind="tool", tool=tname, args=targs,
                                      observation=obs))
                msgs.append({"role": "tool",
                             "tool_call_id": tc.get("id", ""),
                             "content": obs})

        last_obs = steps[-1].observation if steps else ""
        return ToolRunResult(final=last_obs, steps=steps, stopped_reason="max_steps")

    def run(self, task: str, context: str = "") -> ToolRunResult:
        return self._run_native(task, context) if self.native \
            else self._run_text(task, context)

    @staticmethod
    def _parse_action(text: str) -> Optional[dict]:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except Exception:
            return None


# ---------------------------------------------------------------------------
# ToolUsingGenerator — Loop 의 Generator 자리에 끼우는 어댑터
# ---------------------------------------------------------------------------
class ToolUsingGenerator(Generator):
    """generate() 가 단순 LLM 호출 대신 도구 사용 루프를 돈다.
    Loop/LoopSpec 은 그대로 두고 generator 만 교체하면 도구 쓰는 루프가 된다.
    """

    def __init__(self, client: LLMClient, registry: ToolRegistry,
                 name: str = "tool_generator",
                 model: Optional[str] = None,
                 max_steps: int = 8,
                 native: bool = False,
                 role_system: Optional[str] = None):
        super().__init__(client, name=name, role_system=role_system, model=model)
        self.agent = ToolAgent(client, registry, model=model,
                               max_steps=max_steps, native=native)

    def generate(self, goal: str, context: str = "",
                 prior_feedback: str = "") -> str:
        task = goal
        if prior_feedback:
            task += f"\n\n[직전 검증 피드백 — 반드시 반영]\n{prior_feedback}"
        return self.agent.run(task, context=context).final
