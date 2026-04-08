"""Tests for ToolRouter."""

from openharness.engine.models import Tool
from openharness.engine.registry import ToolRegistry
from openharness.engine.router import ToolRouter


def _noop(p: str) -> str:
    return ""


def _make_router():
    reg = ToolRegistry()
    reg.register(Tool("echo", "Echo the input payload back", _noop))
    reg.register(Tool("upper", "Convert input to uppercase", _noop))
    reg.register(Tool("word-count", "Count words in input", _noop))
    return ToolRouter(reg)


def test_route_match():
    router = _make_router()
    matches = router.route("echo hello")
    assert len(matches) >= 1
    assert matches[0].name == "echo"
    assert matches[0].score > 0


def test_route_no_match():
    router = _make_router()
    matches = router.route("xyz123abc")
    assert len(matches) == 0


def test_route_limit():
    router = _make_router()
    matches = router.route("input count", limit=1)
    assert len(matches) <= 1


def test_route_sort_by_score():
    router = _make_router()
    matches = router.route("count words input")
    if len(matches) >= 2:
        assert matches[0].score >= matches[1].score


def test_tokenize():
    tokens = ToolRouter._tokenize("hello/world-test foo")
    assert "hello" in tokens
    assert "world" in tokens
    assert "test" in tokens
    assert "foo" in tokens
