from __future__ import annotations

import unittest

from harness.history import HistoryEvent, HistoryLog


class TestHistoryLog(unittest.TestCase):
    def test_add_event(self) -> None:
        log = HistoryLog()
        log.add('test', 'detail')
        self.assertEqual(len(log.events), 1)
        self.assertEqual(log.events[0].title, 'test')

    def test_as_markdown(self) -> None:
        log = HistoryLog()
        log.add('turn', 'executed tools=2')
        log.add('session', 'persisted')
        md = log.as_markdown()
        self.assertIn('# Session History', md)
        self.assertIn('turn: executed tools=2', md)
        self.assertIn('session: persisted', md)

    def test_empty_log(self) -> None:
        log = HistoryLog()
        md = log.as_markdown()
        self.assertIn('# Session History', md)

    def test_event_frozen(self) -> None:
        event = HistoryEvent('title', 'detail')
        with self.assertRaises(AttributeError):
            event.title = 'other'  # type: ignore[misc]


if __name__ == '__main__':
    unittest.main()
