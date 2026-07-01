"""
loop_engine — 폐쇄망용 루프 엔지니어링 프레임워크 (stdlib only)

루프 엔지니어링 6부품 + generator/verifier 분리를 코드화:
  ① 오토메이션   -> triggers.Scheduler / CronTrigger / IntervalTrigger
  ② 워크트리     -> state.RunContext (runs/<id>/ 격리)
  ③ 스킬         -> skills.SkillRegistry / Skill (SKILL.md)
  ④ 커넥터       -> llm.LLMClient (OpenAI 호환)
  ⑤ 서브에이전트 -> agents.Generator / VerifierAgent (self-bias 감지)
  ⑥ 상태/기억    -> state.ArtifactStore / Signal / WorkLog / Contract

핵심 진입점:
  >>> from loop_engine import LoopSystem, LoopConfig, LLMConfig
  >>> sys = LoopSystem(LoopConfig(llm=LLMConfig(endpoint="LOCAL")))
"""
from .config import DEFAULT_ENDPOINTS, LLMConfig, LoopConfig, load_token
from .llm import LLMClient, LLMError, LLMResponse, make_mock_transport
from .skills import Skill, SkillRegistry
from .state import (Artifact, ArtifactStore, Contract, RunContext, Signal,
                    WorkLog, new_run_id)
from .verifier import (Check, CheckResult, CheckSuite, Rubric, RubricResult,
                       Verdict, check_callable, check_contains,
                       check_min_length, check_no_placeholder,
                       check_python_syntax, check_regex, check_valid_json)
from .agents import Agent, Generator, VerifierAgent, same_family
from .tools import (Tool, ToolRegistry, ToolAgent, ToolUsingGenerator,
                    ToolStep, ToolRunResult)
from .discover import DiscoverContext, skill_context, triage_to_lines
from .loop import (Loop, LoopMode, LoopResult, LoopSpec, LoopStatus, Round)
from .triggers import (CronTrigger, IntervalTrigger, Job, ManualTrigger,
                       Scheduler, TriageItem, triage)
from .orchestrator import LoopSystem, RegisteredLoop

__version__ = "0.1.0"

__all__ = [
    # config
    "LoopConfig", "LLMConfig", "DEFAULT_ENDPOINTS", "load_token",
    # llm
    "LLMClient", "LLMResponse", "LLMError", "make_mock_transport",
    # skills
    "Skill", "SkillRegistry",
    # state
    "RunContext", "Artifact", "ArtifactStore", "Signal", "WorkLog",
    "Contract", "new_run_id",
    # verifier
    "Check", "CheckResult", "CheckSuite", "Rubric", "RubricResult", "Verdict",
    "check_min_length", "check_contains", "check_regex", "check_valid_json",
    "check_python_syntax", "check_no_placeholder", "check_callable",
    # agents
    "Agent", "Generator", "VerifierAgent", "same_family",
    # tools / connectors
    "Tool", "ToolRegistry", "ToolAgent", "ToolUsingGenerator",
    "ToolStep", "ToolRunResult",
    # discover
    "DiscoverContext", "skill_context", "triage_to_lines",
    # loop
    "Loop", "LoopSpec", "LoopResult", "LoopMode", "LoopStatus", "Round",
    # triggers
    "Scheduler", "CronTrigger", "IntervalTrigger", "ManualTrigger", "Job",
    "TriageItem", "triage",
    # orchestrator
    "LoopSystem", "RegisteredLoop",
]
