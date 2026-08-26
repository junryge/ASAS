# -*- coding: utf-8 -*-
"""FAB 그래프 — 안 보여지는 것을 그리느라 자리를 먹지 않는가.

실제 지적
    "fab 그래프 보여주는 부분 필요없는 부분이나 안 보여지는건 전부 다 제거했지?"

무엇이 문제였나
    발동 지표 패널은 reason 에 적힌 컬럼마다 88px 짜리 칸을 만들었다.
    그런데 그 구간에 값이 안 오는 컬럼도 **칸은 그대로 만들고** 안에
    "데이터 없음" 만 적었다. 그래프만 길어지고 볼 것은 없다.

지금 규칙
    · 두 점도 안 되는 지표는 **패널을 만들지 않는다** (높이도 안 먹는다)
    · 대신 "이 구간에 값이 안 온 컬럼: …" 을 한 줄로 남긴다
      — 그 사실도 정보다 (수집이 빠진 것인지 확인해야 한다)
    · M16_PKT · M16_WT 는 애초에 안 그린다 (2026-08 · 영향 없는 영역)
"""
import re
import unittest
from datetime import datetime, timedelta

from . import util  # noqa: F401

import graphs  # noqa: E402
from lp_client import load_config  # noqa: E402


def _rows(n=20, **cols):
    """1분 간격 n행. cols 로 컬럼값을 준다 (None 이면 빈 문자열)."""
    t0 = datetime(2026, 8, 26, 10, 0)
    out = []
    for i in range(n):
        r = {"datetime": (t0 + timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M"),
             "unified_risk_score": str(60 + i % 5),
             "hot_area": "M16HUB",
             "reason": "발동: M16HUB[R-A(AVGTOTALTIME1MIN=15.9분), "
                       "R-C(역증가 리프터)]"}
        for k, v in cols.items():
            r[k] = "" if v is None else str(v)
        out.append(r)
    return out


def _panels(svg):
    """지표 패널 제목 수 — 패널 하나당 하나."""
    return svg.count('font-size="11.5" font-weight="700"')


def _height(svg):
    return int(re.search(r'height="(\d+)"', svg).group(1))


class 값이_없는_지표는_칸을_안_만든다(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config()
        self.center = datetime(2026, 8, 26, 10, 10)

    def _svg(self, rows):
        return graphs.render(rows, self.center, minutes=60, cfg=self.cfg)

    def test_둘_다_값이_있으면_둘_다_그린다(self):
        svg = self._svg(_rows(M16HUB_ra=15.9, M16HUB_rev_count=7))
        self.assertEqual(_panels(svg), 2)

    def test_한쪽이_비면_칸이_하나_준다(self):
        """★예전엔 '데이터 없음' 칸을 그려서 높이가 그대로였다."""
        full = self._svg(_rows(M16HUB_ra=15.9, M16HUB_rev_count=7))
        half = self._svg(_rows(M16HUB_ra=15.9, M16HUB_rev_count=None))
        self.assertEqual(_panels(half), 1)
        self.assertLess(_height(half), _height(full), "높이가 안 줄었다 — 빈 칸이 남아 있다")

    def test_빈_칸_문구가_사라졌다(self):
        svg = self._svg(_rows(M16HUB_ra=15.9, M16HUB_rev_count=None))
        self.assertNotIn("데이터 없음", svg)

    def test_안_온_컬럼은_한_줄로_밝힌다(self):
        """★그냥 지우기만 하면 "왜 안 보이나" 에 답이 없다."""
        svg = self._svg(_rows(M16HUB_ra=15.9, M16HUB_rev_count=None))
        self.assertIn("값이 안 온 컬럼", svg)
        self.assertIn("리프터 정체", svg)

    def test_다_비면_패널이_하나도_없다(self):
        svg = self._svg(_rows(M16HUB_ra=None, M16HUB_rev_count=None))
        self.assertEqual(_panels(svg), 0)
        self.assertIn("값이 안 온 컬럼", svg)

    def test_한_점만_있는_것도_선이_안_되니_뺀다(self):
        rows = _rows(M16HUB_ra=15.9, M16HUB_rev_count=None)
        rows[0]["M16HUB_rev_count"] = "7"          # 딱 한 점
        svg = self._svg(rows)
        self.assertEqual(_panels(svg), 1, "점 하나로는 추이를 못 그린다")


class 제외된_영역은_안_그린다(unittest.TestCase):
    """★M16_PKT 제외 (2026-08) · M16_WT 는 원래 제외."""

    def test_reason_에_있어도_안_뽑는다(self):
        got = graphs.parse_reason_metrics(
            "발동: M16_PKT[R-A(AVGTOTALTIME1MIN=9분)] "
            "M16HUB[R-A(AVGTOTALTIME1MIN=15.9분)]")
        cols = [m["col"] for m in got]
        self.assertNotIn("M16_PKT_ra", cols)
        self.assertIn("M16HUB_ra", cols)

    def test_M16_WT_도_마찬가지(self):
        got = graphs.parse_reason_metrics("발동: M16_WT[R-A(AVGTOTALTIME1MIN=9분)]")
        self.assertEqual(got, [])

    def test_막는_자리가_둘_다_살아_있다(self):
        """★실제 관문은 영역 정규식이다 — 거기에 M16_PKT 가 들어가면
        컬럼 필터만으로는 못 막는 경로가 생긴다. 둘 다 확인한다."""
        with open(graphs.__file__, encoding="utf-8") as f:
            src = f.read()
        area_re = re.search(r're\.finditer\(r"\(([^)]*)\)', src).group(1)
        self.assertNotIn("M16_PKT", area_re, "영역 정규식이 M16_PKT 를 받는다")
        self.assertNotIn("M16_WT", area_re)
        self.assertIn('"M16_PKT", "M16_WT"', src, "컬럼 쪽 방어가 사라졌다")


class 하루_그래프도_빈_계열을_거른다(unittest.TestCase):
    """report_graphs 는 원래 걸러 왔다 — 되돌아가지 않게 못 박는다."""

    def test_값이_없거나_전부_0이면_뺀다(self):
        import report_graphs
        with open(report_graphs.__file__, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("if pts and any(v != 0 for _, v in pts):", src)


if __name__ == "__main__":
    unittest.main()
