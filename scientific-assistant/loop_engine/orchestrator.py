"""
orchestrator.py — 여러 루프를 '공유 두뇌'로 묶어 복리로 굴린다.

단일 루프도 유용하지만, 같은 파일시스템(signals/artifacts)을 읽고 쓰는 루프들이
서로의 발견을 이어받을 때 레버리지가 복리로 쌓인다.
  예) SEO 루프의 '이 키워드는 전환되는데 콘텐츠 없음' 시그널 → 콘텐츠 루프가 픽업.

LoopSystem 이:
  - LoopConfig 로 작업공간 구성 (runs/artifacts/skills/contracts/WORKLOG)
  - LLMClient / SkillRegistry / ArtifactStore / WorkLog 보유
  - 루프 등록 + 트리거 연결 (Scheduler)
  - 각 실행마다 RunContext 격리
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .config import LoopConfig
from .llm import LLMClient
from .loop import Loop, LoopResult, LoopSpec
from .skills import SkillRegistry
from .state import (ArtifactStore, Contract, RunContext, Signal, WorkLog,
                    new_run_id)
from .tools import ToolRegistry, Tool
from .discover import DiscoverContext, skill_context
from .triggers import Job, Scheduler


@dataclass
class RegisteredLoop:
    spec: LoopSpec
    contract: Optional[Contract] = None


class LoopSystem:
    """루프 엔지니어링 런타임. 이거 하나로 모든 부품이 연결된다."""

    def __init__(self, config: Optional[LoopConfig] = None,
                 client: Optional[LLMClient] = None):
        self.cfg = (config or LoopConfig()).ensure_dirs()
        self.client = client or LLMClient(self.cfg.llm)
        self.skills = SkillRegistry(self.cfg.skills_dir)
        self.tools = ToolRegistry()
        self.artifacts = ArtifactStore(self.cfg.artifacts_dir)
        self.worklog = WorkLog(self.cfg.worklog_path)
        self.scheduler = Scheduler(on_error=self._on_sched_error)
        self._loops: Dict[str, RegisteredLoop] = {}

    # -- 등록 --
    def register(self, spec: LoopSpec,
                 contract: Optional[Contract] = None) -> RegisteredLoop:
        if contract:
            contract.save(self.cfg.contracts_dir)
        reg = RegisteredLoop(spec=spec, contract=contract)
        self._loops[spec.name] = reg
        return reg

    def names(self) -> List[str]:
        return sorted(self._loops)

    # -- 도구/스킬/discover 헬퍼 (③④ 배선) --
    def register_tool(self, tool: Tool) -> "LoopSystem":
        """에이전트가 쓸 외부 도구 등록 (내부 API 호출, Logpresso 쿼리, 파일 등)."""
        self.tools.add(tool)
        return self

    def skill_context(self, names: Optional[List[str]] = None):
        """스킬을 루프 context_provider 로. names=None 이면 전체."""
        return skill_context(self.skills, names)

    def discover_context(self, skill_names: Optional[List[str]] = None,
                         include_open_signals: bool = True,
                         worklog_tail: int = 8,
                         triage_provider=None,
                         extra_provider=None) -> DiscoverContext:
        """스킬 + 시그널 + 워크로그 + triage 를 묶은 discover context_provider 생성."""
        return DiscoverContext(
            skills=self.skills, artifacts=self.artifacts, worklog=self.worklog,
            skill_names=skill_names, include_open_signals=include_open_signals,
            worklog_tail=worklog_tail, triage_provider=triage_provider,
            extra_provider=extra_provider,
        )

    # -- 단발 실행 (격리된 run 디렉토리에서) --
    def run_once(self, loop_name: str,
                 on_round=None) -> LoopResult:
        reg = self._loops[loop_name]
        # 계약 먼저 읽기 (매 실행 전 contract 확인 원칙)
        contract = (Contract.load(self.cfg.contracts_dir, loop_name)
                    or reg.contract)
        if contract:
            contract.log("run start")
            contract.save(self.cfg.contracts_dir)

        run_ctx = RunContext(self.cfg.runs_dir, run_id=new_run_id(loop_name))
        loop = Loop(reg.spec, worklog=self.worklog, on_round=on_round)
        result = loop.run(run_ctx)
        if contract:
            contract.log(f"run end: {result.status.value} ({result.n_rounds} rounds)")
            contract.save(self.cfg.contracts_dir)
        return result

    # -- 트리거 연결 --
    def schedule_cron(self, loop_name: str, expr: str) -> Job:
        return self.scheduler.cron(loop_name, expr,
                                   lambda: self.run_once(loop_name))

    def schedule_every(self, loop_name: str, seconds: float) -> Job:
        return self.scheduler.every(loop_name, seconds,
                                    lambda: self.run_once(loop_name))

    def enable_manual(self, loop_name: str) -> Job:
        return self.scheduler.manual(loop_name,
                                     lambda: self.run_once(loop_name))

    def start(self, background: bool = True):
        self.worklog.append("system", "scheduler start", f"loops={self.names()}")
        self.scheduler.start(background=background)

    def stop(self):
        self.scheduler.stop()
        self.worklog.append("system", "scheduler stop")

    # -- 공유 두뇌 헬퍼 (복리) --
    def emit_signal(self, summary: str, kind: str = "friction",
                    sources: Optional[List[str]] = None,
                    created_by: str = "") -> Signal:
        sig = Signal(id=new_run_id("sig"), summary=summary, kind=kind,
                     sources=sources or [], created_by=created_by)
        self.artifacts.emit_signal(sig)
        self.worklog.append(created_by or "loop", "signal", f"{kind}: {summary[:80]}")
        return sig

    def open_signals(self) -> List[Signal]:
        return self.artifacts.read_signals(status="open")

    def _on_sched_error(self, job_name: str, exc: Exception):
        self.worklog.append("scheduler", f"job error: {job_name}", str(exc))
