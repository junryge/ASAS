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

    def test_흐릿한_유사만으로는_추천하지_않는다(self) -> None:
        """근거가 '글자가 좀 겹친다' 뿐이면 기권한다.

        ★'decompression' 과 'compression' 은 글자가 겹칠 뿐 다른 말이다.
          이런 걸 그럴듯한 1위로 내보내면, 에이전트는 엉뚱한 스킬을 열고
          사용자는 그게 근거 있는 추천인 줄 안다. 모르면 모른다고 해야 한다.
        """
        self.registry.register(Tool('compression', 'compression', handler=lambda p: p))
        names = [m.name for m in self.router.route('decompression')]
        self.assertNotIn('compression', names)

    def test_설명에_실제로_있으면_추천한다(self) -> None:
        """기권 규칙이 멀쩡한 일치까지 막으면 안 된다 (반대쪽 확인)."""
        names = [m.name for m in self.router.route('compression')]
        self.registry.register(Tool('zipper', 'compression helper', handler=lambda p: p))
        names = [m.name for m in self.router.route('compression')]
        self.assertIn('zipper', names)


if __name__ == '__main__':
    unittest.main()
