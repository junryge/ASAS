"""Core data models for the harness engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class Tool:
    """A callable tool with metadata."""
    name: str
    description: str
    handler: Callable[[str], str]
    category: str = "general"
    requires_permission: bool = False


@dataclass(frozen=True)
class ToolExecution:
    """Result of executing a tool."""
    tool_name: str
    payload: str
    handled: bool
    output: str
    error: str = ""


@dataclass(frozen=True)
class RoutedMatch:
    """A tool matched by the router."""
    name: str
    score: int
    description: str


@dataclass(frozen=True)
class UsageSummary:
    """Token usage tracking."""
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens

    def add_turn(self, prompt: str, output: str) -> UsageSummary:
        return UsageSummary(
            self.input_tokens + len(prompt.split()),
            self.output_tokens + len(output.split()),
        )


@dataclass(frozen=True)
class PermissionDenial:
    """Record of a denied tool execution."""
    tool_name: str
    reason: str


@dataclass(frozen=True)
class TurnResult:
    """Complete result of a single turn."""
    prompt: str
    output: str
    matched_tools: tuple[str, ...]
    permission_denials: tuple[PermissionDenial, ...]
    usage: UsageSummary
    stop_reason: str  # 'completed', 'max_turns_reached', 'max_budget_reached'
