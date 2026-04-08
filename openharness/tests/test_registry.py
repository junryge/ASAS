"""Tests for ToolRegistry."""

from openharness.engine.models import Tool
from openharness.engine.registry import ToolRegistry


def _echo(payload: str) -> str:
    return payload


def _upper(payload: str) -> str:
    return payload.upper()


def test_register_and_get():
    reg = ToolRegistry()
    reg.register(Tool("echo", "Echo input", _echo))
    tool = reg.get("echo")
    assert tool is not None
    assert tool.name == "echo"


def test_case_insensitive_get():
    reg = ToolRegistry()
    reg.register(Tool("Echo", "Echo input", _echo))
    assert reg.get("echo") is not None
    assert reg.get("ECHO") is not None
    assert reg.get("Echo") is not None


def test_unregister():
    reg = ToolRegistry()
    reg.register(Tool("echo", "Echo input", _echo))
    assert reg.unregister("echo") is True
    assert reg.get("echo") is None
    assert reg.unregister("echo") is False


def test_list_all():
    reg = ToolRegistry()
    reg.register(Tool("echo", "Echo", _echo))
    reg.register(Tool("upper", "Upper", _upper))
    tools = reg.list_all()
    assert len(tools) == 2


def test_find():
    reg = ToolRegistry()
    reg.register(Tool("echo", "Echo the input", _echo))
    reg.register(Tool("upper", "Convert to uppercase", _upper))
    matches = reg.find("echo")
    assert len(matches) == 1
    assert matches[0].name == "echo"


def test_execute_success():
    reg = ToolRegistry()
    reg.register(Tool("echo", "Echo", _echo))
    result = reg.execute("echo", "hello")
    assert result.handled is True
    assert result.output == "hello"


def test_execute_not_found():
    reg = ToolRegistry()
    result = reg.execute("missing", "test")
    assert result.handled is False
    assert "not found" in result.error


def test_execute_error():
    def bad_handler(p: str) -> str:
        raise ValueError("boom")

    reg = ToolRegistry()
    reg.register(Tool("bad", "Bad tool", bad_handler))
    result = reg.execute("bad", "test")
    assert result.handled is False
    assert "boom" in result.error


def test_count():
    reg = ToolRegistry()
    assert reg.count == 0
    reg.register(Tool("echo", "Echo", _echo))
    assert reg.count == 1


def test_render_index():
    reg = ToolRegistry()
    reg.register(Tool("echo", "Echo input", _echo))
    md = reg.render_index()
    assert "echo" in md
    assert "Echo input" in md
