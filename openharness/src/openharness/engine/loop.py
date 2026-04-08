"""Harness Engine - agent loop with budget management and streaming."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Iterator

from .models import (
    PermissionDenial,
    TurnResult,
    UsageSummary,
)
from .registry import ToolRegistry
from .router import ToolRouter
from ..permissions import ToolPermissionContext
from ..memory.session import StoredSession, save_session, load_session
from ..memory.history import HistoryLog
from ..memory.transcript import TranscriptStore


@dataclass(frozen=True)
class EngineConfig:
    """Configuration for the harness engine."""
    max_turns: int = 8
    max_budget_tokens: int = 50000
    compact_after_turns: int = 12
    structured_output: bool = False


@dataclass
class HarnessEngine:
    """Core agent loop: prompt → route → permission check → execute → loop."""

    registry: ToolRegistry
    router: ToolRouter
    config: EngineConfig
    session_id: str
    messages: list[str]
    history: HistoryLog
    transcript: TranscriptStore
    usage: UsageSummary
    _turn_count: int = 0
    _denials: list[PermissionDenial] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        registry: ToolRegistry,
        config: EngineConfig | None = None,
    ) -> HarnessEngine:
        """Factory: create a new engine with fresh session."""
        return cls(
            registry=registry,
            router=ToolRouter(registry),
            config=config or EngineConfig(),
            session_id=uuid.uuid4().hex,
            messages=[],
            history=HistoryLog(),
            transcript=TranscriptStore(),
            usage=UsageSummary(),
        )

    @classmethod
    def from_session(
        cls,
        session_id: str,
        registry: ToolRegistry,
        directory: str | None = None,
    ) -> HarnessEngine:
        """Load engine state from a persisted session."""
        session = load_session(session_id, directory)
        return cls(
            registry=registry,
            router=ToolRouter(registry),
            config=EngineConfig(),
            session_id=session.session_id,
            messages=list(session.messages),
            history=HistoryLog(),
            transcript=TranscriptStore(),
            usage=UsageSummary(session.input_tokens, session.output_tokens),
        )

    def submit(
        self,
        prompt: str,
        permission_ctx: ToolPermissionContext | None = None,
    ) -> TurnResult:
        """Execute a single turn."""
        # Check turn limit
        if self._turn_count >= self.config.max_turns:
            return TurnResult(
                prompt=prompt,
                output="",
                matched_tools=(),
                permission_denials=(),
                usage=self.usage,
                stop_reason="max_turns_reached",
            )

        self._turn_count += 1

        # Route prompt to tools
        matches = self.router.route(prompt)

        # Permission check
        denials: list[PermissionDenial] = []
        allowed_names: list[str] = []
        for match in matches:
            if permission_ctx and permission_ctx.blocks(match.name):
                denials.append(PermissionDenial(
                    tool_name=match.name,
                    reason=f"Blocked by permission policy",
                ))
            else:
                allowed_names.append(match.name)

        # Execute allowed tools
        output_parts: list[str] = []
        for name in allowed_names:
            result = self.registry.execute(name, prompt)
            if result.handled:
                output_parts.append(f"[{name}] {result.output}")
            elif result.error:
                output_parts.append(f"[{name}] Error: {result.error}")

        output = "\n".join(output_parts) if output_parts else "(no tools matched)"

        # Format output
        if self.config.structured_output:
            import json
            output = json.dumps({
                "tools": allowed_names,
                "output": output,
                "denials": [{"tool": d.tool_name, "reason": d.reason} for d in denials],
            }, ensure_ascii=False)

        # Check budget
        projected = self.usage.add_turn(prompt, output)
        if projected.total > self.config.max_budget_tokens:
            stop_reason = "max_budget_reached"
        else:
            stop_reason = "completed"

        self.usage = projected

        # Update state
        self.messages.append(prompt)
        self.messages.append(output)
        self.transcript.append(f"User: {prompt}\nAssistant: {output}")
        self.history.add("turn", f"Turn {self._turn_count}: {len(allowed_names)} tools")
        self._denials.extend(denials)

        # Compact if needed
        if self._turn_count > self.config.compact_after_turns:
            self.transcript.compact(keep_last=10)

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
        """Multi-turn execution loop."""
        results: list[TurnResult] = []
        turns = max_turns or self.config.max_turns

        for i in range(turns):
            turn_prompt = prompt if i == 0 else f"{prompt} [turn {i + 1}]"
            result = self.submit(turn_prompt, permission_ctx)
            results.append(result)
            if result.stop_reason != "completed":
                break

        return results

    def stream_submit(
        self,
        prompt: str,
        permission_ctx: ToolPermissionContext | None = None,
    ) -> Iterator[dict]:
        """Streaming turn execution yielding events."""
        yield {"type": "message_start", "session_id": self.session_id, "prompt": prompt}

        matches = self.router.route(prompt)
        allowed = [m.name for m in matches if not (permission_ctx and permission_ctx.blocks(m.name))]
        blocked = [m.name for m in matches if permission_ctx and permission_ctx.blocks(m.name)]

        yield {"type": "tool_match", "tools": tuple(allowed)}

        if blocked:
            yield {"type": "permission_denial", "denials": blocked}

        # Execute
        output_parts = []
        for name in allowed:
            result = self.registry.execute(name, prompt)
            if result.handled:
                output_parts.append(f"[{name}] {result.output}")

        output = "\n".join(output_parts) if output_parts else "(no tools matched)"
        yield {"type": "message_delta", "text": output}

        self.usage = self.usage.add_turn(prompt, output)
        self._turn_count += 1

        yield {
            "type": "message_stop",
            "usage": {"input": self.usage.input_tokens, "output": self.usage.output_tokens},
            "stop_reason": "completed",
        }

    def persist(self, directory: str | None = None) -> str:
        """Save session to disk."""
        session = StoredSession(
            session_id=self.session_id,
            messages=tuple(self.messages),
            input_tokens=self.usage.input_tokens,
            output_tokens=self.usage.output_tokens,
        )
        save_session(session, directory)
        return self.session_id

    def render_session_report(self) -> str:
        """Generate markdown session report."""
        lines = [
            f"# Session Report",
            f"- ID: {self.session_id}",
            f"- Turns: {self._turn_count}",
            f"- Tokens: {self.usage.total} (in: {self.usage.input_tokens}, out: {self.usage.output_tokens})",
            f"- Tools registered: {self.registry.count}",
            "",
            self.history.as_markdown(),
        ]
        return "\n".join(lines)
