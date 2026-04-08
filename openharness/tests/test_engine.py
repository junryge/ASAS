"""Tests for HarnessEngine."""

import tempfile
from pathlib import Path

from openharness.engine.models import Tool
from openharness.engine.registry import ToolRegistry
from openharness.engine.loop import HarnessEngine, EngineConfig
from openharness.permissions import ToolPermissionContext


def _echo(p: str) -> str:
    return p


def _make_engine(max_turns=8, max_budget=50000):
    reg = ToolRegistry()
    reg.register(Tool("echo", "Echo input back", _echo))
    reg.register(Tool("upper", "Convert to uppercase", lambda p: p.upper()))
    config = EngineConfig(max_turns=max_turns, max_budget_tokens=max_budget)
    return HarnessEngine.create(reg, config)


def test_single_turn():
    engine = _make_engine()
    result = engine.submit("echo hello")
    assert result.stop_reason == "completed"
    assert "echo" in result.matched_tools


def test_max_turns():
    engine = _make_engine(max_turns=2)
    engine.submit("echo a")
    engine.submit("echo b")
    result = engine.submit("echo c")
    assert result.stop_reason == "max_turns_reached"


def test_permission_denial():
    engine = _make_engine()
    ctx = ToolPermissionContext.from_iterables(deny_names=["echo"])
    result = engine.submit("echo hello", permission_ctx=ctx)
    assert len(result.permission_denials) > 0
    assert "echo" not in result.matched_tools


def test_run_loop():
    engine = _make_engine(max_turns=3)
    results = engine.run_loop("echo test", max_turns=2)
    assert len(results) >= 1
    assert results[0].stop_reason == "completed"


def test_stream_submit():
    engine = _make_engine()
    events = list(engine.stream_submit("echo streaming"))
    types = [e["type"] for e in events]
    assert "message_start" in types
    assert "tool_match" in types
    assert "message_stop" in types


def test_session_report():
    engine = _make_engine()
    engine.submit("echo test")
    report = engine.render_session_report()
    assert "Session Report" in report
    assert engine.session_id in report


def test_persist_and_load():
    with tempfile.TemporaryDirectory() as d:
        engine = _make_engine()
        engine.submit("echo persist-test")
        session_id = engine.persist(d)

        reg = ToolRegistry()
        reg.register(Tool("echo", "Echo", _echo))
        loaded = HarnessEngine.from_session(session_id, reg, d)
        assert loaded.session_id == session_id
        assert len(loaded.messages) > 0
