"""Slash command registry and execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class Command:
    """A slash command definition."""
    name: str
    description: str
    handler: Callable[[str, Any], str]
    hidden: bool = False


class CommandRegistry:
    """Registry for slash commands (/help, /skills, /models, etc.)."""

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(self, cmd: Command) -> None:
        self._commands[cmd.name.lower()] = cmd

    def get(self, name: str) -> Command | None:
        # Strip leading slash
        clean = name.lstrip("/").lower()
        return self._commands.get(clean)

    def list_all(self) -> list[Command]:
        return [c for c in self._commands.values() if not c.hidden]

    def is_command(self, text: str) -> bool:
        """Check if text starts with a slash command."""
        return text.startswith("/") and len(text) > 1

    def render_help(self) -> str:
        lines = ["# Available Commands\n"]
        for cmd in sorted(self._commands.values(), key=lambda c: c.name):
            if not cmd.hidden:
                lines.append(f"  /{cmd.name:<20s} {cmd.description}")
        return "\n".join(lines)


def _cmd_help(args: str, ctx: Any) -> str:
    return ctx.command_registry.render_help()


def _cmd_skills(args: str, ctx: Any) -> str:
    skills = ctx.skill_loader.list_skills()
    if not skills:
        return "No skills loaded. Place SKILL.md files in ~/.openharness/skills/"
    lines = [f"# Skills ({len(skills)} loaded)\n"]
    for name in skills:
        meta = ctx.skill_loader.get_skill(name)
        desc = meta.description if meta else ""
        lines.append(f"  /{name:<20s} {desc}")
    return "\n".join(lines)


def _cmd_plugins(args: str, ctx: Any) -> str:
    plugins = ctx.plugin_loader.list_plugins()
    if not plugins:
        return "No plugins loaded. Place plugins in ~/.openharness/plugins/"
    lines = [f"# Plugins ({len(plugins)} loaded)\n"]
    for name in plugins:
        meta = ctx.plugin_loader.get_plugin(name)
        if meta:
            cmds = ", ".join(f"/{c.name}" for c in meta.commands)
            lines.append(f"  {name} v{meta.version}: {meta.description}")
            if cmds:
                lines.append(f"    Commands: {cmds}")
    return "\n".join(lines)


def _cmd_models(args: str, ctx: Any) -> str:
    from ..api.models import MODEL_REGISTRY
    lines = ["# Available Models\n"]
    for key, cfg in MODEL_REGISTRY.items():
        marker = "→ " if key == ctx.provider.default_model else "  "
        lines.append(f"  {marker}{key:<25s} {cfg['name']:<20s} [{cfg['cost_tier']}]")
    return "\n".join(lines)


def _cmd_model(args: str, ctx: Any) -> str:
    if not args.strip():
        return f"Current model: {ctx.provider.default_model}"
    from ..api.models import get_model_config
    new_model = args.strip()
    if get_model_config(new_model):
        ctx.provider.default_model = new_model
        return f"Model set to: {new_model}"
    return f"Unknown model: {new_model}. Use /models to see available models."


def _cmd_status(args: str, ctx: Any) -> str:
    lines = [
        "# Status",
        f"  Token: {'loaded' if ctx.provider.has_token else 'missing'}",
        f"  Model: {ctx.provider.default_model}",
        f"  Tools: {ctx.registry.count}",
        f"  Skills: {ctx.skill_loader.count}",
        f"  Plugins: {ctx.plugin_loader.count}",
    ]
    return "\n".join(lines)


def _cmd_clear(args: str, ctx: Any) -> str:
    return "\033[2J\033[H"  # ANSI clear screen


def _cmd_exit(args: str, ctx: Any) -> str:
    raise SystemExit(0)


# Default commands
DEFAULT_COMMANDS = [
    Command("help", "Show available commands", _cmd_help),
    Command("skills", "List loaded skills", _cmd_skills),
    Command("plugins", "List loaded plugins", _cmd_plugins),
    Command("models", "List available LLM models", _cmd_models),
    Command("model", "Get/set current model", _cmd_model),
    Command("status", "Show system status", _cmd_status),
    Command("clear", "Clear screen", _cmd_clear),
    Command("exit", "Exit OpenHarness", _cmd_exit),
    Command("quit", "Exit OpenHarness", _cmd_exit),
]


def run_command(text: str, ctx: Any, cmd_registry: CommandRegistry) -> str | None:
    """Parse and execute a slash command. Returns output or None if not a command."""
    if not text.startswith("/"):
        return None
    parts = text[1:].split(None, 1)
    cmd_name = parts[0] if parts else ""
    args = parts[1] if len(parts) > 1 else ""

    cmd = cmd_registry.get(cmd_name)
    if cmd is None:
        return f"Unknown command: /{cmd_name}. Type /help for available commands."
    return cmd.handler(args, ctx)
