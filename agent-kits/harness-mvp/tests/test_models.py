from __future__ import annotations

import unittest

from harness.models import (
    PermissionDenial, RoutedMatch, Task, Tool, ToolExecution,
    TurnResult, UsageSummary, default_tasks,
)


class TestUsageSummary(unittest.TestCase):
    def test_default_is_zero(self) -> None:
        u = UsageSummary()
        self.assertEqual(u.input_tokens, 0)
        self.assertEqual(u.output_tokens, 0)

    def test_add_turn_increments(self) -> None:
        u = UsageSummary()
        u2 = u.add_turn('hello world', 'ok fine thanks')
        self.assertEqual(u2.input_tokens, 2)
        self.assertEqual(u2.output_tokens, 3)

    def test_frozen(self) -> None:
        u = UsageSummary()
        with self.assertRaises(AttributeError):
            u.input_tokens = 5  # type: ignore[misc]


class TestTool(unittest.TestCase):
    def test_handler_callable(self) -> None:
        t = Tool('echo', 'Echo', handler=lambda p: p)
        self.assertEqual(t.handler('hello'), 'hello')

    def test_frozen(self) -> None:
        t = Tool('echo', 'Echo', handler=lambda p: p)
        with self.assertRaises(AttributeError):
            t.name = 'other'  # type: ignore[misc]


class TestDefaultTasks(unittest.TestCase):
    def test_returns_three_tasks(self) -> None:
        tasks = default_tasks()
        self.assertEqual(len(tasks), 3)
        self.assertIsInstance(tasks[0], Task)

    def test_task_ids_unique(self) -> None:
        tasks = default_tasks()
        ids = [t.id for t in tasks]
        self.assertEqual(len(ids), len(set(ids)))


class TestTurnResult(unittest.TestCase):
    def test_construction(self) -> None:
        r = TurnResult(
            prompt='test', output='out',
            matched_tools=('echo',), permission_denials=(),
            usage=UsageSummary(1, 1), stop_reason='completed',
        )
        self.assertEqual(r.stop_reason, 'completed')


if __name__ == '__main__':
    unittest.main()
