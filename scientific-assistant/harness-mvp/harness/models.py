from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: Callable[[str], str]


@dataclass(frozen=True)
class Task:
    id: str
    description: str


@dataclass(frozen=True)
class ToolExecution:
    tool_name: str
    payload: str
    handled: bool
    output: str


@dataclass(frozen=True)
class RoutedMatch:
    name: str
    score: int
    description: str


@dataclass(frozen=True)
class UsageSummary:
    input_tokens: int = 0
    output_tokens: int = 0

    def add_turn(self, prompt: str, output: str) -> UsageSummary:
        return UsageSummary(
            self.input_tokens + len(prompt.split()),
            self.output_tokens + len(output.split()),
        )


@dataclass(frozen=True)
class PermissionDenial:
    tool_name: str
    reason: str


@dataclass(frozen=True)
class TurnResult:
    prompt: str
    output: str
    matched_tools: tuple[str, ...]
    permission_denials: tuple[PermissionDenial, ...]
    usage: UsageSummary
    stop_reason: str


def default_tasks() -> list[Task]:
    return [
        Task('tool-registry-check', 'Verify all registered tools are functional'),
        Task('session-persistence', 'Validate session save/load round-trip'),
        Task('turn-loop-audit', 'Run multi-turn loop and verify budget enforcement'),
    ]
