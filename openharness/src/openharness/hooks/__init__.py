"""Hooks subsystem - lifecycle event hooks (PreToolUse / PostToolUse)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Any


@dataclass
class HookEvent:
    """An event that can trigger hooks."""
    event_type: str  # "pre_tool_use", "post_tool_use", "pre_command", "post_command"
    tool_name: str
    payload: str
    cancelled: bool = False
    result: str = ""


HookHandler = Callable[[HookEvent], None]


@dataclass
class HookRegistry:
    """Registry for lifecycle hooks."""

    _hooks: dict[str, list[HookHandler]] = field(default_factory=dict)

    def register(self, event_type: str, handler: HookHandler) -> None:
        """Register a hook for an event type."""
        if event_type not in self._hooks:
            self._hooks[event_type] = []
        self._hooks[event_type].append(handler)

    def unregister(self, event_type: str, handler: HookHandler) -> bool:
        """Remove a hook. Returns True if found and removed."""
        handlers = self._hooks.get(event_type, [])
        try:
            handlers.remove(handler)
            return True
        except ValueError:
            return False

    def fire(self, event: HookEvent) -> HookEvent:
        """Fire all hooks for an event type. Returns the (possibly modified) event."""
        handlers = self._hooks.get(event.event_type, [])
        for handler in handlers:
            handler(event)
            if event.cancelled:
                break
        return event

    def list_hooks(self) -> dict[str, int]:
        """Return event types and their handler counts."""
        return {k: len(v) for k, v in self._hooks.items()}
