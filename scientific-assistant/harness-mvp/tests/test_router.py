from __future__ import annotations

import unittest

from harness.models import Tool
from harness.registry import ToolRegistry
from harness.router import ToolRouter


class TestToolRouter(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ToolRegistry()
        self.registry.register(Tool('echo', 'Echo the input payload back', handler=lambda p: p))
        self.registry.register(Tool('upper', 'Convert input to uppercase', handler=lambda p: p.upper()))
        self.registry.register(Tool('word-count', 'Count words in the input', handler=lambda p: str(len(p.split()))))
        self.router = ToolRouter(self.registry)

    def test_route_matches_by_name(self) -> None:
        matches = self.router.route('echo hello')
        names = [m.name for m in matches]
        self.assertIn('echo', names)

    def test_route_matches_by_description(self) -> None:
        matches = self.router.route('convert uppercase')
        names = [m.name for m in matches]
        self.assertIn('upper', names)

    def test_route_respects_limit(self) -> None:
        matches = self.router.route('echo upper count input', limit=2)
        self.assertLessEqual(len(matches), 2)

    def test_route_no_match(self) -> None:
        matches = self.router.route('xyznonexistent')
        self.assertEqual(len(matches), 0)

    def test_route_empty_prompt(self) -> None:
        matches = self.router.route('')
        self.assertEqual(len(matches), 0)

    def test_route_sorted_by_score_desc(self) -> None:
        matches = self.router.route('count words input')
        if len(matches) > 1:
            self.assertGreaterEqual(matches[0].score, matches[1].score)

    def test_score_static_method(self) -> None:
        score = ToolRouter._score({'echo', 'hello'}, 'echo', 'Echo the input')
        self.assertGreaterEqual(score, 1)


if __name__ == '__main__':
    unittest.main()
