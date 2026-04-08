"""Permission system - deny-list based tool access control."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolPermissionContext:
    """Deny-list permission context for tool execution."""

    deny_names: frozenset[str] = field(default_factory=frozenset)
    deny_prefixes: tuple[str, ...] = ()

    @classmethod
    def from_iterables(
        cls,
        deny_names: list[str] | None = None,
        deny_prefixes: list[str] | None = None,
    ) -> ToolPermissionContext:
        return cls(
            deny_names=frozenset(n.lower() for n in (deny_names or [])),
            deny_prefixes=tuple(p.lower() for p in (deny_prefixes or [])),
        )

    def blocks(self, tool_name: str) -> bool:
        """Check if a tool is blocked by this context."""
        lowered = tool_name.lower()
        if lowered in self.deny_names:
            return True
        return any(lowered.startswith(prefix) for prefix in self.deny_prefixes)
