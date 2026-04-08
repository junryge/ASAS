"""CLI entry point - main application loop.

Usage:
    oh                          # Interactive mode, auto-detect model
    oh --model prod             # Use specific model
    oh run "fix the tests"      # Headless single-shot mode
    oh --trust                  # Auto-approve tool permissions
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from dataclasses import dataclass

from .api.token import load_token, print_token_status, find_token_file
from .api.provider import Provider
from .api.models import MODEL_REGISTRY, DEFAULT_MODEL
from .engine.registry import ToolRegistry
from .engine.router import ToolRouter
from .engine.loop import HarnessEngine, EngineConfig
from .tools.builtin import register_builtin_tools
from .skills.loader import SkillLoader
from .plugins.loader import PluginLoader
from .permissions import ToolPermissionContext
from .hooks import HookRegistry
from .commands.registry import CommandRegistry, Command, DEFAULT_COMMANDS, run_command

BANNER = r"""
  ╔══════════════════════════════════════════╗
  ║     OpenHarness  v0.1.0                  ║
  ║     Open Agent Harness for Teams         ║
  ╚══════════════════════════════════════════╝
"""

PACKAGE_DIR = Path(__file__).parent.parent.parent  # openharness/ root


@dataclass
class AppContext:
    """Shared context passed to commands and handlers."""
    provider: Provider
    registry: ToolRegistry
    router: ToolRouter
    engine: HarnessEngine
    skill_loader: SkillLoader
    plugin_loader: PluginLoader
    hook_registry: HookRegistry
    command_registry: CommandRegistry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oh",
        description="OpenHarness - Open Agent Harness",
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help=f"Model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--trust", "-t",
        action="store_true",
        help="Auto-approve all tool permissions",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    parser.add_argument(
        "--skills-dir",
        default=None,
        help="Additional skills directory to scan",
    )
    parser.add_argument(
        "--plugins-dir",
        default=None,
        help="Additional plugins directory to scan",
    )

    sub = parser.add_subparsers(dest="command")

    # oh run "prompt"
    run_parser = sub.add_parser("run", help="Run a single prompt headlessly")
    run_parser.add_argument("prompt", help="The prompt to execute")
    run_parser.add_argument("--max-turns", type=int, default=1)

    # oh status
    sub.add_parser("status", help="Show system status")

    # oh skills
    sub.add_parser("skills", help="List loaded skills")

    # oh plugins
    sub.add_parser("plugins", help="List loaded plugins")

    # oh models
    sub.add_parser("models", help="List available models")

    return parser


def initialize(args: argparse.Namespace) -> AppContext:
    """Initialize all subsystems and return app context."""
    # 1. Token & Provider
    token = load_token()
    model = args.model or DEFAULT_MODEL
    provider = Provider(token=token, default_model=model)

    # 2. Tool Registry
    registry = ToolRegistry()
    builtin_count = register_builtin_tools(registry)

    # 3. Skills
    skill_search = []
    # Bundled skills (anthropic/)
    bundled_skills = PACKAGE_DIR / "skills" / "anthropic"
    if bundled_skills.is_dir():
        skill_search.append(bundled_skills)
    # Also check package-level skills/
    pkg_skills = PACKAGE_DIR / "skills"
    if pkg_skills.is_dir() and pkg_skills != bundled_skills:
        skill_search.append(pkg_skills)
    # User custom skills
    user_skills = Path.home() / ".openharness" / "skills"
    skill_search.append(user_skills)
    # CLI argument
    if args.skills_dir:
        skill_search.append(Path(args.skills_dir))

    skill_loader = SkillLoader(search_paths=skill_search)
    skill_count = skill_loader.register_all(registry)

    # 4. Plugins
    plugin_search = []
    bundled_plugins = PACKAGE_DIR / "plugins" / "anthropic"
    if bundled_plugins.is_dir():
        plugin_search.append(bundled_plugins)
    pkg_plugins = PACKAGE_DIR / "plugins"
    if pkg_plugins.is_dir() and pkg_plugins != bundled_plugins:
        plugin_search.append(pkg_plugins)
    user_plugins = Path.home() / ".openharness" / "plugins"
    plugin_search.append(user_plugins)
    if args.plugins_dir:
        plugin_search.append(Path(args.plugins_dir))

    plugin_loader = PluginLoader(search_paths=plugin_search)
    plugin_count = plugin_loader.register_all(registry)

    # 5. Hooks
    hook_registry = HookRegistry()

    # 6. Engine
    engine_config = EngineConfig(structured_output=args.json)
    router = ToolRouter(registry)
    engine = HarnessEngine.create(registry, engine_config)

    # 7. Commands
    command_registry = CommandRegistry()
    for cmd in DEFAULT_COMMANDS:
        command_registry.register(cmd)
    # Register skill names as commands
    for skill_name in skill_loader.list_skills():
        meta = skill_loader.get_skill(skill_name)
        if meta:
            content = meta.content

            def make_skill_cmd(c: str):
                def handler(a: str, ctx: object) -> str:
                    return c[:3000]
                return handler

            command_registry.register(Command(
                name=skill_name,
                description=meta.description,
                handler=make_skill_cmd(content),
            ))
    # Register plugin commands
    for plugin_name in plugin_loader.list_plugins():
        plugin = plugin_loader.get_plugin(plugin_name)
        if plugin:
            for cmd in plugin.commands:
                content = cmd.content

                def make_plugin_cmd(c: str):
                    def handler(a: str, ctx: object) -> str:
                        return c[:3000]
                    return handler

                command_registry.register(Command(
                    name=cmd.name,
                    description=f"[{plugin_name}] {cmd.description}",
                    handler=make_plugin_cmd(content),
                ))

    ctx = AppContext(
        provider=provider,
        registry=registry,
        router=router,
        engine=engine,
        skill_loader=skill_loader,
        plugin_loader=plugin_loader,
        hook_registry=hook_registry,
        command_registry=command_registry,
    )

    return ctx


def print_startup(ctx: AppContext) -> None:
    """Print startup banner and status."""
    print(BANNER)
    ctx.provider.print_status()
    print(f"  🔧 Tools: {ctx.registry.count} ({ctx.skill_loader.count} skills, "
          f"{ctx.plugin_loader.count} plugins)")
    print(f"  💬 Type /help for commands, /exit to quit\n")


def interactive_loop(ctx: AppContext) -> None:
    """Main interactive REPL loop."""
    permission_ctx = None  # No restrictions by default

    while True:
        try:
            prompt = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not prompt:
            continue

        # Check for slash commands
        if prompt.startswith("/"):
            output = run_command(prompt, ctx, ctx.command_registry)
            if output:
                print(output)
            continue

        # Chat with LLM
        try:
            messages = [
                {"role": "system", "content": "You are a helpful AI assistant running inside OpenHarness CLI."},
                {"role": "user", "content": prompt},
            ]
            response = ctx.provider.chat(messages)
            print(f"\n{response.content}\n")
            if response.fallback_used:
                print(f"  (used fallback: {response.model})")
        except Exception as e:
            print(f"\n  Error: {e}\n")


def main() -> None:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    ctx = initialize(args)

    # Handle subcommands
    if args.command == "run":
        # Headless mode
        try:
            messages = [
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": args.prompt},
            ]
            response = ctx.provider.chat(messages)
            print(response.content)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if args.command == "status":
        print(run_command("/status", ctx, ctx.command_registry))
        return

    if args.command == "skills":
        print(run_command("/skills", ctx, ctx.command_registry))
        return

    if args.command == "plugins":
        print(run_command("/plugins", ctx, ctx.command_registry))
        return

    if args.command == "models":
        print(run_command("/models", ctx, ctx.command_registry))
        return

    # Interactive mode
    print_startup(ctx)
    interactive_loop(ctx)
