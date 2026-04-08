"""Plugin loader - scans for .claude-plugin/plugin.json and registers components.

Compatible with anthropics/claude-code plugins structure:
plugin-name/
  .claude-plugin/plugin.json   # metadata (required)
  commands/*.md                 # slash commands
  agents/*.md                   # agent definitions
  skills/*.md                   # bundled skills
  .mcp.json                     # MCP config (IGNORED - MCP excluded)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..engine.models import Tool
from ..engine.registry import ToolRegistry

PLUGIN_SEARCH_PATHS = [
    Path.home() / ".openharness" / "plugins",  # User plugins
]


@dataclass
class CommandDef:
    """A slash command from a plugin."""
    name: str
    description: str
    content: str
    path: Path


@dataclass
class AgentDef:
    """An agent definition from a plugin."""
    name: str
    content: str
    path: Path


@dataclass
class PluginMeta:
    """Loaded plugin metadata and components."""
    name: str
    description: str
    version: str
    path: Path
    commands: list[CommandDef] = field(default_factory=list)
    agents: list[AgentDef] = field(default_factory=list)
    skills: list[Path] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


def _load_plugin_json(plugin_dir: Path) -> dict | None:
    """Load .claude-plugin/plugin.json from a plugin directory."""
    pj = plugin_dir / ".claude-plugin" / "plugin.json"
    if not pj.is_file():
        return None
    try:
        return json.loads(pj.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _load_commands(plugin_dir: Path) -> list[CommandDef]:
    """Load all command .md files from commands/ directory."""
    cmd_dir = plugin_dir / "commands"
    if not cmd_dir.is_dir():
        return []
    commands = []
    for md_file in sorted(cmd_dir.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        name = md_file.stem  # e.g., "code-review.md" → "code-review"
        # Try to extract description from first line
        first_line = content.split("\n", 1)[0].strip().lstrip("#").strip()
        commands.append(CommandDef(
            name=name,
            description=first_line or f"Command: /{name}",
            content=content,
            path=md_file,
        ))
    return commands


def _load_agents(plugin_dir: Path) -> list[AgentDef]:
    """Load all agent .md files from agents/ directory."""
    agents_dir = plugin_dir / "agents"
    if not agents_dir.is_dir():
        return []
    agents = []
    for md_file in sorted(agents_dir.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        agents.append(AgentDef(
            name=md_file.stem,
            content=content,
            path=md_file,
        ))
    return agents


class PluginLoader:
    """Scans directories for plugins and registers their components."""

    def __init__(
        self,
        search_paths: list[Path] | None = None,
        bundled_path: Path | None = None,
    ) -> None:
        self.search_paths = list(search_paths or PLUGIN_SEARCH_PATHS)
        if bundled_path:
            self.search_paths.insert(0, bundled_path)
        self._plugins: dict[str, PluginMeta] = {}

    def scan(self) -> list[PluginMeta]:
        """Scan all search paths for plugins."""
        self._plugins.clear()
        for base_path in self.search_paths:
            if not base_path.is_dir():
                continue
            for plugin_dir in sorted(base_path.iterdir()):
                if not plugin_dir.is_dir():
                    continue

                pj = _load_plugin_json(plugin_dir)
                if pj is None:
                    continue

                name = pj.get("name", plugin_dir.name)
                if name in self._plugins:
                    continue

                meta = PluginMeta(
                    name=name,
                    description=pj.get("description", f"Plugin: {name}"),
                    version=pj.get("version", "0.0.0"),
                    path=plugin_dir,
                    commands=_load_commands(plugin_dir),
                    agents=_load_agents(plugin_dir),
                    skills=list((plugin_dir / "skills").glob("*/SKILL.md"))
                        if (plugin_dir / "skills").is_dir() else [],
                    extra={k: v for k, v in pj.items()
                           if k not in ("name", "description", "version")},
                )
                self._plugins[name] = meta

        return list(self._plugins.values())

    def register_all(self, registry: ToolRegistry) -> int:
        """Scan and register all plugin commands as tools."""
        plugins = self.scan()
        count = 0
        for plugin in plugins:
            for cmd in plugin.commands:
                content = cmd.content

                def make_handler(c: str):
                    def handler(payload: str) -> str:
                        return c[:2000]
                    return handler

                tool = Tool(
                    name=cmd.name,
                    description=f"[{plugin.name}] {cmd.description}",
                    handler=make_handler(content),
                    category="plugin-command",
                )
                registry.register(tool)
                count += 1
        return count

    def get_plugin(self, name: str) -> PluginMeta | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[str]:
        return sorted(self._plugins.keys())

    def list_all_commands(self) -> list[str]:
        """List all registered command names across all plugins."""
        commands = []
        for plugin in self._plugins.values():
            for cmd in plugin.commands:
                commands.append(f"/{cmd.name}")
        return sorted(commands)

    @property
    def count(self) -> int:
        return len(self._plugins)
