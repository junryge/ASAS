from __future__ import annotations

from .models import Tool, ToolExecution
from .permissions import ToolPermissionContext


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name.lower()] = tool

    def unregister(self, name: str) -> bool:
        return self._tools.pop(name.lower(), None) is not None

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name.lower())

    def list_all(self) -> list[Tool]:
        return list(self._tools.values())

    def find(self, query: str, limit: int = 20) -> list[Tool]:
        needle = query.lower()
        matches = [
            tool for tool in self._tools.values()
            if needle in tool.name.lower() or needle in tool.description.lower()
        ]
        return matches[:limit]

    def filter(self, permission_ctx: ToolPermissionContext | None = None) -> list[Tool]:
        tools = list(self._tools.values())
        if permission_ctx is None:
            return tools
        return [t for t in tools if not permission_ctx.blocks(t.name)]

    def execute(self, name: str, payload: str) -> ToolExecution:
        tool = self.get(name)
        if tool is None:
            return ToolExecution(
                tool_name=name, payload=payload, handled=False,
                output=f'Unknown tool: {name}',
            )
        try:
            result = tool.handler(payload)
        except Exception as exc:
            return ToolExecution(
                tool_name=tool.name, payload=payload, handled=False,
                output=f'Error executing {tool.name}: {exc}',
            )
        return ToolExecution(
            tool_name=tool.name, payload=payload, handled=True, output=result,
        )

    def render_index(self, limit: int = 20, query: str | None = None) -> str:
        tools = self.find(query, limit) if query else self.list_all()[:limit]
        lines = [f'Tool entries: {len(self._tools)}', '']
        if query:
            lines.extend([f'Filtered by: {query}', ''])
        lines.extend(f'- {t.name} -- {t.description}' for t in tools)
        return '\n'.join(lines)


def builtin_tools() -> list[Tool]:
    return [
        Tool('echo', 'Echo the input payload back', handler=lambda p: p),
        Tool('upper', 'Convert input to uppercase', handler=lambda p: p.upper()),
        Tool('word-count', 'Count words in the input', handler=lambda p: str(len(p.split()))),
        Tool('reverse', 'Reverse the input string', handler=lambda p: p[::-1]),
        Tool('char-count', 'Count characters in the input', handler=lambda p: str(len(p))),
    ]
