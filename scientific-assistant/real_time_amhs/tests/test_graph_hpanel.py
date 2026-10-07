# -*- coding: utf-8 -*-
"""더블클릭 그래프 — 지표도 스코어처럼 가로줄 하나씩 (2026-10-07).

고객
    "실제지표 더블클릭하면 데이터 표시가 되야지 — 가로줄 스코어 처럼" · "신규 지표도 마찬가지"
    "실제지표에 더블클릭하면 거기 실제지표 가로줄 검은색줄로 표시가 되야지 — 그게 없으니까 헷갈리네"
    "M16HUB.LFT.6ABL6011.TOTAL_CURRENTQCNT … 리프터 데이터는 왜 안 나오는데 — 2개는 나오는데"

지키는 것
    ① 지표 칸은 스코어처럼 가로 전체 폭 — 한 줄에 하나, 실제지표 · 신규 지표 둘 다.
    ② 스코어와 같은 시간축 — 더블클릭한 분의 세로선이 위아래로 같은 x 에 선다.
    ③ 더블클릭한 분은 그 값 높이에 가로줄(흰 배경이면 검정 = 스코어의 고른 분 색)
       을 긋고, 칸 오른쪽 위에 '시각 · 값' 을 적는다.
    ④ 리프터 호기 칸 — 주피터 CSV 에 호기별 대기량 컬럼이 없다. 칸은 세우고 그 호기가
       역증가로 걸린 분(M16HUB_rev_lids)을 그린다. 이름만 다른 컬럼이 있으면 그 값을 쓴다.
"""
import datetime as dt
import re
import unittest

from . import util  # noqa: F401

import graphs as G  # noqa: E402
import sentinel as S  # noqa: E402
from lp_client import load_config  # noqa: E402

from .test_real_new import BASE, CENTER, HUB_REASON, _cells, _empty_line, _hub_rows, _names, _rows, _section_y  # noqa: E402,E501

CFG = load_config()
LIDS = ("6ABL6011", "6ABL6012", "6ABL6021", "6ABL0112", "6ABL0122")
LFT_REASON = ("발동: M16HUB[R-A'(AVGTOTALTIME1MIN=12분/기준9.0),"
              f"R-C'(역증가5개:{','.join(LIDS)}),R-D(FAB저장=26%)]")


def _lids(i):
    """분마다 역증가로 걸린 호기 — 6011 은 짝수 분, 6012 는 3의 배수 분."""
    got = []
    if i % 2 == 0:
        got.append("6ABL6011")
    if i % 3 == 0:
        got.append("6ABL6012")
    return ",".join(got)


def _frames(svg):
    """칸 테두리 [(x, y, w)]."""
    return [tuple(float(v) for v in m.groups()) for m in re.finditer(
        r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="[\d.]+" rx="10"', svg)]


def _sel_x(chunk):
    """그 칸(또는 스코어)에서 고른 분 세로선의 x."""
    return float(re.search(r'<line class="gsel" x1="([\d.]+)" y1="[\d.]+" x2="\1"', chunk).group(1))


class 스코어처럼_가로줄(unittest.TestCase):

    def setUp(self):
        self.svg = G.render(_hub_rows(), CENTER, 60, cfg=CFG)

    def test_칸마다_가로_전체_폭(self):
        fr = _frames(self.svg)
        self.assertGreaterEqual(len(fr), 3)
        for x, _y, w in fr:
            self.assertEqual(x, G.PAD)
            self.assertEqual(w, 1000 - G.PAD * 2)

    def test_한_줄에_하나(self):
        ys = [y for _x, y, _w in _frames(self.svg)]
        self.assertEqual(len(ys), len(set(ys)), "같은 줄에 칸이 둘 섰다")
        self.assertEqual(ys, sorted(ys))

    def test_신규_지표도_가로줄(self):
        ny = _section_y(self.svg, "신규 지표")
        new = [c for c in _cells(self.svg) if c[3] > ny]
        self.assertTrue(new)
        for _n, _l, chunk, _y in new:
            self.assertIn(f'width="{1000 - G.PAD * 2:.1f}" height="{G.PANEL_H:.1f}" rx="10"', chunk)

    def test_스코어와_같은_시간축(self):
        """더블클릭한 분의 세로선이 스코어와 모든 칸에서 같은 x."""
        score_x = float(re.search(r'<line x1="([\d.]+)" y1="[\d.]+" x2="\1" y2="[\d.]+" '
                                  r'stroke="[^"]+" stroke-width="1.4"/>', self.svg).group(1))
        for _n, _l, chunk, _y in _cells(self.svg):
            self.assertAlmostEqual(_sel_x(chunk), score_x, delta=0.11)

    def test_맨_아래에도_시간축(self):
        """칸이 여럿이면 스코어 밑 시간축은 스크롤 위로 사라진다."""
        self.assertEqual(self.svg.count(">09:15<"), 2)       # 창 시작 09:45-30분
        last = _frames(self.svg)[-1]
        ys = [float(y) for y in re.findall(r'<text x="[\d.]+" y="([\d.]+)"[^>]*>09:15<', self.svg)]
        self.assertGreater(max(ys), last[1] + G.PANEL_H, "맨 아래 시간축이 칸 밑에 있어야 한다")


class 더블클릭한_분_가로줄(unittest.TestCase):
    """고객: "거기 실제지표 가로줄 검은색줄로 표시가 되야지 — 그게 없으니까 헷갈리네"."""

    def _cell(self, svg, name):
        return next(c[2] for c in _cells(svg) if c[0] == name)

    def test_그_분_값_높이에_가로줄(self):
        svg = G.render(_hub_rows(), CENTER, 60, cfg=CFG)
        c = self._cell(svg, "M16HUB.QUE.M14TOM16.MESCURRENTQCNT")
        m = re.search(r'<line class="gsel" x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="\2" '
                      r'[^>]*stroke-dasharray', c)
        self.assertTrue(m, "고른 분 가로줄이 없다")
        self.assertGreater(float(m.group(3)) - float(m.group(1)), 800, "가로줄이 칸 폭을 다 지나야 한다")
        # 점(원)과 같은 높이 — 그 분 값 자리다
        cy = float(re.search(r'<circle cx="[\d.]+" cy="([\d.]+)" r="4"', c).group(1))
        self.assertAlmostEqual(float(m.group(2)), cy, delta=0.11)

    def test_흰_배경이면_검정(self):
        svg = G.render(_hub_rows(), CENTER, 60, cfg=CFG, theme="light")
        c = self._cell(svg, "M16HUB.QUE.TIME.AVGTOTALTIME1MIN")
        sel = G._pal("light")["sel"]
        self.assertRegex(c, r'<line class="gsel" [^>]*stroke="%s"[^>]*stroke-dasharray' % sel)
        r, g, b = (int(sel[k:k + 2], 16) for k in (1, 3, 5))
        self.assertLess(max(r, g, b), 0x40, "흰 배경에서 고른 분 줄은 검정 계열이어야 한다")

    def test_그_분_값을_적는다(self):
        svg = G.render(_hub_rows(), CENTER, 60, cfg=CFG)
        c = self._cell(svg, "M16HUB.QUE.M14TOM16.MESCURRENTQCNT")
        self.assertRegex(c, r'class="msel"[^>]*>09:45 · 525건<')   # 480 + 45분


class 리프터_호기(unittest.TestCase):
    """주피터 발동이벤트 CSV(예측기 EVENT_FIELDS)에는 호기별 대기량 컬럼이 없다 —
    역증가로 걸린 호기 이름만 M16HUB_rev_lids 에 실린다."""

    def _svg(self, **cols):
        rows = _rows("M16HUB", LFT_REASON, M16HUB_ra=lambda i: 8 + i % 5,
                     M16HUB_rd_fab=lambda i: 22 + i % 6, **cols)
        return G.render(rows, CENTER, 60, cfg=CFG)

    def test_표의_실제지표가_전부_선다(self):
        svg = self._svg(M16HUB_rev_lids=_lids)
        names = _names(svg)
        for x in LIDS:
            self.assertIn(f"M16HUB.LFT.{x}.TOTAL_CURRENTQCNT", names)
        self.assertNotIn("6ABL6011", _empty_line(svg))

    def test_걸린_분을_그린다고_밝힌다(self):
        svg = self._svg(M16HUB_rev_lids=_lids)
        c = next(c for c in _cells(svg) if c[0] == "M16HUB.LFT.6ABL6011.TOTAL_CURRENTQCNT")
        self.assertIn("역증가로 걸린 분", c[1])
        self.assertIn("CSV에 없음", c[1])
        self.assertRegex(c[2], r'class="msel"[^>]*>09:45 · 안 걸림<')    # 45분은 홀수
        self.assertIn("22분 걸림", c[2])           # 창 09:15~09:59 (자료 끝) 중 짝수 분

    def test_값은_역증가_목록에서(self):
        m = {"lid": "6ABL6012", "lids_col": "M16HUB_rev_lids"}
        self.assertEqual(G.metric_value(m, {"M16HUB_rev_lids": "6ABL6011,6ABL6012"}), 1.0)
        self.assertEqual(G.metric_value(m, {"M16HUB_rev_lids": "6ABL6011"}), 0.0)
        self.assertEqual(G.metric_value(m, {"M16HUB_rev_lids": ""}), 0.0)
        self.assertIsNone(G.metric_value(m, {}), "목록 컬럼이 없으면 모르는 것이다")

    def test_목록도_없으면_값이_안_온_컬럼(self):
        svg = self._svg()
        for x in LIDS:
            self.assertIn(f"M16HUB.LFT.{x}.TOTAL_CURRENTQCNT", _empty_line(svg))

    def test_이름만_다른_컬럼이_있으면_그_값(self):
        """예측기 CSV 에 호기별 컬럼이 생기면(구분자만 다르게 와도) 값으로 그린다."""
        svg = self._svg(M16HUB_rev_lids=_lids,
                        M16HUB_LFT_6ABL6011_TOTAL_CURRENTQCNT=lambda i: 3 + i % 4)
        c = next(c for c in _cells(svg) if c[0] == "M16HUB.LFT.6ABL6011.TOTAL_CURRENTQCNT")
        self.assertNotIn("역증가로 걸린 분", c[1])
        self.assertRegex(c[2], r'class="msel"[^>]*>09:45 · 4대<')       # 3 + 45 % 4

    def test_리프터_합_변화도_신규_지표로(self):
        """R-C' 는 역증가 호기 수와 10대 합의 20분 변화를 같이 본다 — 음수도 그린다."""
        svg = self._svg(M16HUB_rev_lids=_lids, M16HUB_rev_count=lambda i: len(_lids(i).split(",")),
                        M16HUB_rc_trend=lambda i: (i % 15) - 10)
        ny = _section_y(svg, "신규 지표")
        new = {c[0]: c for c in _cells(svg) if c[3] > ny}
        self.assertIn("M16HUB_rev_count", new)
        self.assertIn("M16HUB_rc_trend", new)
        chunk = new["M16HUB_rc_trend"][2]
        self.assertRegex(chunk, r'text-anchor="end"[^>]*>-\d+<', "음수 눈금이 있어야 0 아래가 보인다")
        self.assertIn('stroke-dasharray="2 3"', chunk, "0 자리에 가는 줄")


class 이름_찾기(unittest.TestCase):

    def test_구분자_대소문자만_다르면_찾는다(self):
        keys = {"M16HUB_LFT_6ABL6011_TOTAL_CURRENTQCNT", "M16HUB_ra"}
        self.assertEqual(G._find_col("M16HUB.LFT.6ABL6011.TOTAL_CURRENTQCNT", keys),
                         "M16HUB_LFT_6ABL6011_TOTAL_CURRENTQCNT")
        self.assertEqual(G._find_col("M16HUB.QUE.TIME.AVGTOTALTIME1MIN",
                                     {"m16hub_que_time_avgtotaltime1min"}),
                         "m16hub_que_time_avgtotaltime1min")

    def test_리프터는_호기_번호로(self):
        self.assertEqual(G._find_col("M16HUB.LFT.6ABL6012.TOTAL_CURRENTQCNT",
                                     {"LFT_6ABL6012_TOTAL_CURRENTQCNT", "M16HUB_rev_lids"}),
                         "LFT_6ABL6012_TOTAL_CURRENTQCNT")

    def test_남의_FAB_컬럼은_안_집는다(self):
        self.assertIsNone(G._find_col("M16HUB.QUE.TIME.AVGTOTALTIME1MIN",
                                      {"M14.QUE.TIME.AVGTOTALTIME1MIN"}))

    def test_후보가_둘이면_안_고른다(self):
        self.assertIsNone(G._find_col("M16HUB.LFT.6ABL6011.TOTAL_CURRENTQCNT",
                                      {"A_6ABL6011_TOTAL_CURRENTQCNT",
                                       "B_6ABL6011_TOTAL_CURRENTQCNT"}))


class 눈금(unittest.TestCase):

    def test_맨_위는_둥근_수(self):
        self.assertEqual(G._nice_ceil(23.62), 25)
        self.assertEqual(G._nice_ceil(6.6), 8)
        self.assertEqual(G._nice_ceil(105), 120)

    def test_큰_수는_k(self):
        self.assertEqual(G._tick_txt(12000), "12k")
        self.assertEqual(G._tick_txt(1500), "1.5k")
        self.assertEqual(G._tick_txt(25.75), "25.75")


if __name__ == "__main__":
    unittest.main()
