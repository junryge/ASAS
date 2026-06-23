"""
discover.py — discover 단계 배선 (스킬/시그널/워크로그/triage 를 루프 context 로)

루프의 첫 동작은 discover: 무엇을 할지/어떤 맥락이 필요한지 모은다.
지금까지 스킬·triage 가 정의만 되고 루프에 안 붙어 있었으므로, 여기서 연결한다.

  - skill_context()     : SkillRegistry 에서 스킬을 뽑아 context_provider 로
  - DiscoverContext     : 스킬 + open 시그널 + 워크로그 tail + triage 를 한 덩어리로
  - triage_to_lines()   : TriageItem 목록을 우선순위 순 텍스트로
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .skills import SkillRegistry
from .state import ArtifactStore, WorkLog
from .triggers import TriageItem, triage


def skill_context(registry: SkillRegistry,
                  names: Optional[List[str]] = None) -> Callable[[], str]:
    """루프 context_provider 로 쓸 클로저. 스킬 본문을 프롬프트 블록으로 묶어 반환.
    names=None 이면 전체 스킬.
    """
    def _provider() -> str:
        use = names if names is not None else registry.names()
        block = registry.bundle(use)
        return f"[적용 스킬]\n{block}" if block else ""
    return _provider


def triage_to_lines(items: List[TriageItem]) -> str:
    ordered = triage(items)
    if not ordered:
        return ""
    lines = [f"- (P{it.priority}) {it.key}"
             + (f" :: {it.payload}" if it.payload else "")
             for it in ordered]
    return "[우선순위 작업(triage)]\n" + "\n".join(lines)


@dataclass
class DiscoverContext:
    """discover 단계의 모든 입력을 하나의 context_provider 로 합친다.

    >>> dc = DiscoverContext(skills=sys.skills, artifacts=sys.artifacts,
    ...                      worklog=sys.worklog, skill_names=["logpresso_query"])
    >>> spec = LoopSpec(..., context_provider=dc.as_provider())
    """
    skills: Optional[SkillRegistry] = None
    artifacts: Optional[ArtifactStore] = None
    worklog: Optional[WorkLog] = None
    skill_names: Optional[List[str]] = None     # None=전체, []=안씀
    include_open_signals: bool = True
    worklog_tail: int = 8
    triage_provider: Optional[Callable[[], List[TriageItem]]] = None
    extra_provider: Optional[Callable[[], str]] = None

    def build(self) -> str:
        parts: List[str] = []

        # 1) 스킬 (인수인계 노트)
        if self.skills is not None and self.skill_names != []:
            use = self.skill_names if self.skill_names is not None else self.skills.names()
            block = self.skills.bundle(use)
            if block:
                parts.append(f"[적용 스킬]\n{block}")

        # 2) triage (할 일 우선순위)
        if self.triage_provider is not None:
            try:
                items = self.triage_provider() or []
                t = triage_to_lines(items)
                if t:
                    parts.append(t)
            except Exception:
                pass

        # 3) open 시그널 (공유 두뇌)
        if self.include_open_signals and self.artifacts is not None:
            sigs = self.artifacts.read_signals(status="open")
            if sigs:
                lines = [f"- [{s.kind}] {s.summary}" for s in sigs[:10]]
                parts.append("[열린 시그널]\n" + "\n".join(lines))

        # 4) 워크로그 tail (세션 간 기억)
        if self.worklog is not None and self.worklog_tail > 0:
            tail = self.worklog.tail_text(self.worklog_tail)
            if tail:
                parts.append(f"[최근 작업로그]\n{tail}")

        # 5) 사용자 정의 추가 맥락
        if self.extra_provider is not None:
            try:
                ex = self.extra_provider()
                if ex:
                    parts.append(ex)
            except Exception:
                pass

        return "\n\n".join(parts)

    def as_provider(self) -> Callable[[], str]:
        return self.build
