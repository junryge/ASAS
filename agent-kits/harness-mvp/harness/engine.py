from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from .history import HistoryLog
from .models import PermissionDenial, TurnResult, UsageSummary
from .permissions import ToolPermissionContext, CodeGuard
from .registry import ToolRegistry
from .router import ToolRouter
from .session import StoredSession, load_session, save_session
from .transcript import TranscriptStore


@dataclass(frozen=True)
class EngineConfig:
    max_turns: int = 8
    max_budget_tokens: int = 2000
    compact_after_turns: int = 12
    structured_output: bool = False


@dataclass
class HarnessEngine:
    registry: ToolRegistry
    router: ToolRouter
    config: EngineConfig = field(default_factory=EngineConfig)
    session_id: str = field(default_factory=lambda: uuid4().hex)
    messages: list[str] = field(default_factory=list)
    history: HistoryLog = field(default_factory=HistoryLog)
    transcript: TranscriptStore = field(default_factory=TranscriptStore)
    usage: UsageSummary = field(default_factory=UsageSummary)
    _denials: list[PermissionDenial] = field(default_factory=list)

    @classmethod
    def create(cls, registry: ToolRegistry, config: EngineConfig | None = None) -> HarnessEngine:
        return cls(
            registry=registry,
            router=ToolRouter(registry),
            config=config or EngineConfig(),
        )

    @classmethod
    def from_session(
        cls,
        session_id: str,
        registry: ToolRegistry,
        directory: Path | None = None,
    ) -> HarnessEngine:
        stored = load_session(session_id, directory)
        transcript = TranscriptStore(entries=list(stored.messages), flushed=True)
        return cls(
            registry=registry,
            router=ToolRouter(registry),
            session_id=stored.session_id,
            messages=list(stored.messages),
            usage=UsageSummary(stored.input_tokens, stored.output_tokens),
            transcript=transcript,
        )

    def submit(
        self,
        prompt: str,
        permission_ctx: ToolPermissionContext | None = None,
    ) -> TurnResult:
        if len(self.messages) >= self.config.max_turns:
            return TurnResult(
                prompt=prompt,
                output=f'Max turns reached before processing: {prompt}',
                matched_tools=(),
                permission_denials=(),
                usage=self.usage,
                stop_reason='max_turns_reached',
            )

        matches = self.router.route(prompt)
        denials: list[PermissionDenial] = []
        allowed_names: list[str] = []

        for match in matches:
            if permission_ctx and permission_ctx.blocks(match.name):
                denials.append(PermissionDenial(tool_name=match.name, reason='blocked by permission context'))
            else:
                allowed_names.append(match.name)

        output_parts: list[str] = []
        for name in allowed_names:
            result = self.registry.execute(name, prompt)
            if result.handled:
                output_parts.append(f'[{result.tool_name}] {result.output}')
            else:
                output_parts.append(f'[{result.tool_name}] {result.output}')

        if not output_parts:
            output_parts.append(f'No tools matched prompt: {prompt}')

        output = self._format_output(output_parts)
        projected_usage = self.usage.add_turn(prompt, output)

        stop_reason = 'completed'
        if projected_usage.input_tokens + projected_usage.output_tokens > self.config.max_budget_tokens:
            stop_reason = 'max_budget_reached'

        self.messages.append(prompt)
        self.transcript.append(prompt)
        self._denials.extend(denials)
        self.usage = projected_usage
        self.history.add('turn', f'tools={len(allowed_names)} denials={len(denials)} stop={stop_reason}')
        self._compact_if_needed()

        return TurnResult(
            prompt=prompt,
            output=output,
            matched_tools=tuple(allowed_names),
            permission_denials=tuple(denials),
            usage=self.usage,
            stop_reason=stop_reason,
        )

    def run_loop(
        self,
        prompt: str,
        max_turns: int | None = None,
        permission_ctx: ToolPermissionContext | None = None,
    ) -> list[TurnResult]:
        turns = max_turns or self.config.max_turns
        results: list[TurnResult] = []
        for turn in range(turns):
            turn_prompt = prompt if turn == 0 else f'{prompt} [turn {turn + 1}]'
            result = self.submit(turn_prompt, permission_ctx)
            results.append(result)
            if result.stop_reason != 'completed':
                break
        return results

    def stream_submit(
        self,
        prompt: str,
        permission_ctx: ToolPermissionContext | None = None,
    ) -> Iterator[dict[str, object]]:
        yield {'type': 'message_start', 'session_id': self.session_id, 'prompt': prompt}

        matches = self.router.route(prompt)
        if matches:
            yield {'type': 'tool_match', 'tools': tuple(m.name for m in matches)}

        result = self.submit(prompt, permission_ctx)

        if result.permission_denials:
            yield {'type': 'permission_denial', 'denials': [d.tool_name for d in result.permission_denials]}

        yield {'type': 'message_delta', 'text': result.output}
        yield {
            'type': 'message_stop',
            'usage': {'input_tokens': result.usage.input_tokens, 'output_tokens': result.usage.output_tokens},
            'stop_reason': result.stop_reason,
            'transcript_size': len(self.transcript.entries),
        }

    def persist(self, directory: Path | None = None) -> str:
        self.transcript.flush()
        path = save_session(
            StoredSession(
                session_id=self.session_id,
                messages=tuple(self.messages),
                input_tokens=self.usage.input_tokens,
                output_tokens=self.usage.output_tokens,
            ),
            directory,
        )
        self.history.add('session_store', str(path))
        return str(path)

    def render_session_report(self) -> str:
        lines = [
            '# Harness Session Report',
            '',
            f'Session ID: {self.session_id}',
            f'Messages: {len(self.messages)}',
            f'Usage: in={self.usage.input_tokens} out={self.usage.output_tokens}',
            f'Tools registered: {len(self.registry.list_all())}',
            f'Denials tracked: {len(self._denials)}',
            f'Max turns: {self.config.max_turns}',
            f'Max budget: {self.config.max_budget_tokens}',
            f'Transcript flushed: {self.transcript.flushed}',
            '',
            self.history.as_markdown(),
        ]
        return '\n'.join(lines)

    def _compact_if_needed(self) -> None:
        if len(self.messages) > self.config.compact_after_turns:
            self.messages[:] = self.messages[-self.config.compact_after_turns:]
        self.transcript.compact(self.config.compact_after_turns)

    def _format_output(self, parts: list[str]) -> str:
        if self.config.structured_output:
            try:
                return json.dumps({'results': parts, 'session_id': self.session_id}, indent=2)
            except (TypeError, ValueError):
                return json.dumps({'results': ['structured output error'], 'session_id': self.session_id})
        return '\n'.join(parts)

    # ── Pre-commit Hook: 코드 실행 전 안전성 검사 ──

    def pre_commit_check(self, code: str, harness_map: str = "") -> dict:
        """코드 실행/커밋 전 안전성 검사 (Pre-commit Hook)

        Args:
            code: 검사할 코드 문자열
            harness_map: 프로젝트 하네스 맵 내용 (금지 규칙 포함)

        Returns:
            {"safe": bool, "violations": list, "message": str}
        """
        guard = CodeGuard()

        # 하네스 맵에서 금지 규칙 로드
        if harness_map:
            guard.load_from_harness_map(harness_map)

        violations = guard.check(code)
        if violations:
            reasons = [v["reason"] for v in violations[:5]]
            return {
                "safe": False,
                "violations": violations,
                "message": f"⚠️ 금지 패턴 감지 ({len(violations)}건): {', '.join(reasons)}",
            }
        return {
            "safe": True,
            "violations": [],
            "message": "✅ 코드 검사 통과",
        }
