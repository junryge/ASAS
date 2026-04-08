"""Tests for plugin loading."""

import tempfile
import json
from pathlib import Path

from openharness.plugins.loader import PluginLoader, _load_plugin_json
from openharness.engine.registry import ToolRegistry


def _create_plugin(base: Path, name: str, commands: list[str] | None = None):
    """Helper to create a minimal plugin structure."""
    plugin_dir = base / name
    plugin_dir.mkdir(parents=True)
    meta_dir = plugin_dir / ".claude-plugin"
    meta_dir.mkdir()
    (meta_dir / "plugin.json").write_text(json.dumps({
        "name": name,
        "description": f"Test plugin: {name}",
        "version": "1.0.0",
    }))
    if commands:
        cmd_dir = plugin_dir / "commands"
        cmd_dir.mkdir()
        for cmd in commands:
            (cmd_dir / f"{cmd}.md").write_text(f"# {cmd}\nDo {cmd} things.\n")
    return plugin_dir


def test_load_plugin_json():
    with tempfile.TemporaryDirectory() as d:
        _create_plugin(Path(d), "test-plugin")
        pj = _load_plugin_json(Path(d) / "test-plugin")
        assert pj is not None
        assert pj["name"] == "test-plugin"


def test_plugin_loader_scan():
    with tempfile.TemporaryDirectory() as d:
        _create_plugin(Path(d), "plugin-a", commands=["cmd-a"])
        _create_plugin(Path(d), "plugin-b", commands=["cmd-b1", "cmd-b2"])

        loader = PluginLoader(search_paths=[Path(d)])
        plugins = loader.scan()
        assert len(plugins) == 2
        assert "plugin-a" in loader.list_plugins()


def test_plugin_loader_commands():
    with tempfile.TemporaryDirectory() as d:
        _create_plugin(Path(d), "my-plugin", commands=["review", "deploy"])

        loader = PluginLoader(search_paths=[Path(d)])
        loader.scan()
        cmds = loader.list_all_commands()
        assert "/review" in cmds
        assert "/deploy" in cmds


def test_plugin_loader_register_all():
    with tempfile.TemporaryDirectory() as d:
        _create_plugin(Path(d), "code-review", commands=["code-review"])

        loader = PluginLoader(search_paths=[Path(d)])
        registry = ToolRegistry()
        count = loader.register_all(registry)
        assert count == 1
        assert registry.get("code-review") is not None


def test_no_plugin_json():
    with tempfile.TemporaryDirectory() as d:
        # Directory without .claude-plugin/plugin.json
        (Path(d) / "not-a-plugin").mkdir()

        loader = PluginLoader(search_paths=[Path(d)])
        plugins = loader.scan()
        assert len(plugins) == 0
