"""Tests for ToolPermissionContext."""

from openharness.permissions import ToolPermissionContext


def test_deny_names():
    ctx = ToolPermissionContext.from_iterables(deny_names=["echo", "shell"])
    assert ctx.blocks("echo") is True
    assert ctx.blocks("shell") is True
    assert ctx.blocks("read") is False


def test_deny_names_case_insensitive():
    ctx = ToolPermissionContext.from_iterables(deny_names=["Echo"])
    assert ctx.blocks("echo") is True
    assert ctx.blocks("ECHO") is True
    assert ctx.blocks("Echo") is True


def test_deny_prefixes():
    ctx = ToolPermissionContext.from_iterables(deny_prefixes=["mcp_"])
    assert ctx.blocks("mcp_server") is True
    assert ctx.blocks("mcp_client") is True
    assert ctx.blocks("echo") is False


def test_combined_deny():
    ctx = ToolPermissionContext.from_iterables(
        deny_names=["danger"],
        deny_prefixes=["unsafe_"],
    )
    assert ctx.blocks("danger") is True
    assert ctx.blocks("unsafe_tool") is True
    assert ctx.blocks("safe") is False


def test_empty_context_blocks_nothing():
    ctx = ToolPermissionContext()
    assert ctx.blocks("anything") is False
