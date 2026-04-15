from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.engine import EngineConfig, HarnessEngine
from harness.models import Tool
from harness.permissions import ToolPermissionContext
from harness.registry import ToolRegistry, builtin_tools


def _make_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool in builtin_tools():
        registry.register(tool)
    return registry


class TestHarnessEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = _make_registry()
        self.engine = HarnessEngine.create(self.registry)

    def test_submit_single_turn(self) -> None:
        result = self.engine.submit('echo hello')
        self.assertEqual(result.stop_reason, 'completed')
        self.assertIn('echo', result.matched_tools)
        self.assertIn('hello', result.output)

    def test_submit_no_match(self) -> None:
        result = self.engine.submit('xyznonexistent')
        self.assertEqual(result.stop_reason, 'completed')
        self.assertIn('No tools matched', result.output)

    def test_max_turns_reached(self) -> None:
        config = EngineConfig(max_turns=2)
        engine = HarnessEngine.create(self.registry, config)
        engine.submit('echo one')
        engine.submit('echo two')
        result = engine.submit('echo three')
        self.assertEqual(result.stop_reason, 'max_turns_reached')

    def test_max_budget_reached(self) -> None:
        config = EngineConfig(max_budget_tokens=5)
        engine = HarnessEngine.create(self.registry, config)
        result = engine.submit('echo a very long prompt with many words to exhaust the budget quickly')
        self.assertEqual(result.stop_reason, 'max_budget_reached')

    def test_run_loop(self) -> None:
        results = self.engine.run_loop('echo test', max_turns=3)
        self.assertGreaterEqual(len(results), 1)
        self.assertLessEqual(len(results), 3)

    def test_run_loop_stops_on_budget(self) -> None:
        config = EngineConfig(max_budget_tokens=10)
        engine = HarnessEngine.create(self.registry, config)
        results = engine.run_loop('echo a b c d e f g h i j k', max_turns=5)
        last = results[-1]
        self.assertIn(last.stop_reason, ('max_budget_reached', 'max_turns_reached'))

    def test_permission_denial(self) -> None:
        ctx = ToolPermissionContext.from_iterables(deny_names=['echo'])
        result = self.engine.submit('echo hello', permission_ctx=ctx)
        denied_names = [d.tool_name for d in result.permission_denials]
        self.assertIn('echo', denied_names)

    def test_structured_output(self) -> None:
        config = EngineConfig(structured_output=True)
        engine = HarnessEngine.create(self.registry, config)
        result = engine.submit('echo hello')
        self.assertIn('"results"', result.output)

    def test_stream_submit(self) -> None:
        events = list(self.engine.stream_submit('echo hello'))
        types = [e['type'] for e in events]
        self.assertIn('message_start', types)
        self.assertIn('message_stop', types)

    def test_persist_and_reload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.engine.submit('echo hello')
            path = self.engine.persist(Path(tmpdir))
            self.assertTrue(Path(path).exists())

            restored = HarnessEngine.from_session(
                self.engine.session_id, self.registry, Path(tmpdir),
            )
            self.assertEqual(restored.session_id, self.engine.session_id)
            self.assertEqual(len(restored.messages), 1)

    def test_render_session_report(self) -> None:
        self.engine.submit('echo test')
        report = self.engine.render_session_report()
        self.assertIn('Harness Session Report', report)
        self.assertIn('Session History', report)

    def test_compaction(self) -> None:
        config = EngineConfig(max_turns=20, compact_after_turns=3)
        engine = HarnessEngine.create(self.registry, config)
        for i in range(5):
            engine.submit(f'echo turn {i}')
        self.assertLessEqual(len(engine.messages), 3)

    def test_history_tracked(self) -> None:
        self.engine.submit('echo hello')
        self.assertGreaterEqual(len(self.engine.history.events), 1)


if __name__ == '__main__':
    unittest.main()
