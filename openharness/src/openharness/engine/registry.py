"""Tool Registry - O(1) tool lookup and management."""

from __future__ import annotations

from .models import Tool, ToolExecution


class ToolRegistry:
    """Dict-based tool registry with case-insensitive O(1) lookup."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool by lowercased name."""
        self._tools[tool.name.lower()] = tool

    def unregister(self, name: str) -> bool:
        """Remove a tool. Returns True if found and removed."""
        return self._tools.pop(name.lower(), None) is not None

    def get(self, name: str) -> Tool | None:
        """Case-insensitive tool lookup."""
        return self._tools.get(name.lower())

    def list_all(self) -> list[Tool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def find(self, query: str, limit: int = 20) -> list[Tool]:
        """Search tools by name or description substring."""
        q = query.lower()
        matches = [
            t for t in self._tools.values()
            if q in t.name.lower() or q in t.description.lower()
        ]
        return matches[:limit]

    def filter(self, permission_ctx: object | None = None) -> list[Tool]:
        """Return tools filtered by permission context."""
        if permission_ctx is None:
            return self.list_all()
        from ..permissions import ToolPermissionContext
        if isinstance(permission_ctx, ToolPermissionContext):
            return [t for t in self._tools.values() if not permission_ctx.blocks(t.name)]
        return self.list_all()

    def execute(self, name: str, payload: str) -> ToolExecution:
        """Execute a tool by name."""
        tool = self.get(name)
        if tool is None:
            return ToolExecution(
                tool_name=name,
                payload=payload,
                handled=False,
                output="",
                error=f"Tool '{name}' not found",
            )
        try:
            output = tool.handler(payload)
            return ToolExecution(
                tool_name=name,
                payload=payload,
                handled=True,
                output=output,
            )
        except Exception as e:
            return ToolExecution(
                tool_name=name,
                payload=payload,
                handled=False,
                output="",
                error=str(e),
            )

    @property
    def count(self) -> int:
        return len(self._tools)

    def render_index(self, limit: int = 20, query: str | None = None) -> str:
        """Render tool list as markdown."""
        tools = self.find(query, limit) if query else self.list_all()[:limit]
        lines = [f"# Tools ({self.count} registered)\n"]
        for t in tools:
            lines.append(f"- **{t.name}**: {t.description}")
        return "\n".join(lines)
