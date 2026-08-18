"""단계적 공개(progressive disclosure) — 고른 뒤에만, 상관있는 것부터 읽는다.

Agent Skills 규격은 스킬을 3단으로 나눠 읽는다.
  1단 이름+설명   — 라우팅용. 항상 들고 있다.
  2단 SKILL.md 본문 — 고른 뒤에만 읽는다.
  3단 딸린 파일   — 본문이 가리킬 때만 연다.

★예전엔 2단에서 앞 2000자를 뚝 잘랐다. 문장 한가운데서 끊겨 마지막 절차가
  반토막 나고, 정작 필요한 뒤쪽 항목은 통째로 사라졌다. 길이가 모자라면
  버릴 것은 '뒤쪽' 이 아니라 '상관없는 쪽' 이어야 한다.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (_ROOT, os.path.join(_ROOT, "harness-mvp")):
    if p not in sys.path:
        sys.path.insert(0, p)

import harness_bridge as hb  # noqa: E402


def _md(*sections: tuple[str, str]) -> str:
    return "\n\n".join(f"## {t}\n{b}" for t, b in sections)


class ProgressiveDisclosure(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "SKILL.md")

    def _write(self, text: str) -> str:
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(text)
        return self.path

    def test_짧으면_통째로_준다(self):
        p = self._write("# 제목\n짧은 본문")
        self.assertIn("짧은 본문", hb.load_skill_body(p))

    def test_섹션_경계에서_끊는다(self):
        """문장 한가운데서 끊기면 안 된다 — 남은 건 온전한 섹션들이다."""
        p = self._write(_md(*[(f"항목{i}", "가" * 400) for i in range(10)]))
        out = hb.load_skill_body(p, "", max_chars=1200)
        body = out.split("_(관련")[0]
        # 살아남은 섹션은 전부 제목+400자가 온전하다
        for chunk in [c for c in body.split("## ") if c.strip()]:
            self.assertRegex(chunk, r"항목\d\n가{400}")

    def test_상관있는_섹션을_먼저_남긴다(self):
        """뒤쪽에 있어도, 질의에 걸리면 살아남아야 한다."""
        p = self._write(_md(
            ("설치", "채" * 800),
            ("사용법", "채" * 800),
            ("리프터 정체 대응", "리프터가 멈추면 이렇게 한다"),
        ))
        out = hb.load_skill_body(p, "리프터 정체 어떻게 해", max_chars=900)
        self.assertIn("리프터가 멈추면", out)

    def test_버린_섹션은_버렸다고_말한다(self):
        """조용히 잘라 놓고 '이게 전부' 인 척하면 안 된다."""
        p = self._write(_md(*[(f"항목{i}", "가" * 500) for i in range(8)]))
        out = hb.load_skill_body(p, "", max_chars=1000)
        self.assertIn("생략", out)

    def test_최대_길이를_넘기지_않는다(self):
        p = self._write(_md(*[(f"항목{i}", "가" * 500) for i in range(20)]))
        out = hb.load_skill_body(p, "", max_chars=2000)
        self.assertLessEqual(len(out.split("_(관련")[0]), 2000)

    def test_딸린_파일은_이름만_알려_준다(self):
        """3단 — 내용을 밀어 넣지 않고 '있다' 고만 한다."""
        p = self._write("# 제목\n본문")
        with open(os.path.join(self.tmp.name, "reference.md"), "w") as f:
            f.write("아주 긴 참고 자료" * 500)
        out = hb.load_skill_body(p)
        self.assertIn("reference.md", out)
        self.assertNotIn("아주 긴 참고 자료아주", out)

    def test_없는_파일이어도_안_죽는다(self):
        out = hb.load_skill_body(os.path.join(self.tmp.name, "없다.md"))
        self.assertIn("Error", out)


class RouteTelemetry(unittest.TestCase):
    """무엇을 물었고 무엇을 골랐는지 남는다 — 안 남으면 나중에 못 잰다."""

    def setUp(self):
        hb._ROUTE_LOG.clear()

    def tearDown(self):
        hb._ROUTE_LOG.clear()

    def test_고른_것과_점수차가_남는다(self):
        hb._log_route("엑셀", [{"name": "xlsx", "score": 21.0},
                              {"name": "file-organizer", "score": 15.0}])
        r = hb._ROUTE_LOG[-1]
        self.assertEqual(r["top"], "xlsx")
        self.assertEqual(r["margin"], 6.0)

    def test_못_고른_것도_남는다(self):
        hb._log_route("zzqq", [])
        s = hb.harness_route_stats()
        self.assertEqual(s["no_match"], 1)
        self.assertEqual(s["no_match_pct"], 100.0)

    def test_아슬아슬한_질의를_짚어_준다(self):
        """1·2등 차가 거의 없으면 그건 '찍은' 것이다 — 평가셋 후보."""
        hb._log_route("애매한 말", [{"name": "a", "score": 3.0},
                                 {"name": "b", "score": 2.8}])
        s = hb.harness_route_stats()
        self.assertEqual(s["low_margin"], 1)
        self.assertIn("애매한 말", s["low_margin_queries"])

    def test_기록이_무한정_쌓이지_않는다(self):
        for i in range(hb._ROUTE_LOG_MAX + 50):
            hb._log_route(f"q{i}", [{"name": "x", "score": 1.0}])
        self.assertEqual(len(hb._ROUTE_LOG), hb._ROUTE_LOG_MAX)


if __name__ == "__main__":
    unittest.main()
