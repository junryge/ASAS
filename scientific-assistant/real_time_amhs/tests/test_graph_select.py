# -*- coding: utf-8 -*-
"""더블클릭 그래프 — 작은 칸마다 더블클릭한 분 표시 · 선 · 검정 글자 (2026-10-07).

고객
    "실제지표에 더블클릭하면 거기 실제지표 가로줄 검은색줄로 표시가 되야지 — 그게 없으니까 헷갈리네"
    "기존 하던데로 작은 칸칸으로 하면 되지 — 가로줄 표시 안 어렵잖아"
    "왜 막대로 주냐 — 선으로 주라" · "pio 관련은 선을 2개 3개로 하면 되고"
    "가까이 되면 글자가 안 보이잖아 — 노란색 — 검은색으로 해라"
    "M16HUB.LFT.6ABL6011.TOTAL_CURRENTQCNT … 리프터 데이터는 왜 안 나오는데"

지키는 것
    ① 칸은 예전 격자(한 줄에 셋까지) 그대로.
    ② 칸마다 더블클릭한 분: 세로선 + 그 분 값 높이의 가로줄(흰 배경이면 검정) + 점
       + '시각 · 값' 꼬리표. 칸 안 시간축은 분 번호로 잡아 빈 분이 있어도 안 밀린다.
    ③ 막대가 없다 — 모두 선. PIO 는 경로마다 선 하나, 리프터 걸림/안 걸림은 계단 선.
    ④ 글자는 본문색(흰 배경이면 검정). 노랑·주황은 선 · 띠 · 점에만.
    ⑤ 리프터 호기 칸 — 주피터 CSV 에 호기별 대기량이 없으면 리프터 정체 룰이 그 호기를
       지목한 분(M16HUB_rev_lids)을 그린다. 이름만 다른 컬럼이 있으면 그 값을 쓴다.
       화면에 '역증가' 라는 말은 안 쓴다 (고객: "역증가 → 감소 — 역증가 같은 거는 없어").
"""
import datetime as dt
import re
import unittest

from . import util  # noqa: F401

import graphs as G  # noqa: E402
from lp_client import load_config  # noqa: E402

from .test_real_new import (CENTER, _cells, _empty_line, _hub_rows, _names,  # noqa: E402
                            _rows, _section_y)

CFG = load_config()
LIDS = ("6ABL6011", "6ABL6012", "6ABL6021", "6ABL0112", "6ABL0122")
LFT_REASON = ("발동: M16HUB[R-A'(AVGTOTALTIME1MIN=12분/기준9.0),"
              f"R-C'(역증가5개:{','.join(LIDS)}),R-D(FAB저장=26%)]")


def _lids(i):
    """분마다 지목된 호기 — 6011 은 짝수 분, 6012 는 3의 배수 분."""
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


def _cell(svg, name):
    return next(c for c in _cells(svg) if c[0] == name)


def _frame_of(chunk):
    x, y, w = (float(v) for v in re.match(
        r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)"', chunk).groups())
    return x, y, w


class 작은_칸_그대로(unittest.TestCase):

    def test_한_줄에_셋까지(self):
        svg = G.render(_hub_rows(), CENTER, 60, cfg=CFG)
        fr = _frames(svg)
        self.assertGreaterEqual(len(fr), 3)
        ws = {w for _x, _y, w in fr}
        self.assertEqual(len(ws), 1, "칸 폭이 같아야 같은 자로 읽힌다")
        self.assertLess(ws.pop(), (1000 - G.PAD * 2) / 2, "가로 전체 폭이 아니라 작은 칸")
        ys = [y for _x, y, _w in fr]
        self.assertLess(len(set(ys)), len(ys), "같은 줄에 칸이 여럿 서야 한다")


class 더블클릭한_분_표시(unittest.TestCase):
    """고객: "거기 실제지표 가로줄 검은색줄로 표시가 되야지"."""

    def setUp(self):
        self.svg = G.render(_hub_rows(), CENTER, 60, cfg=CFG)
        self.c = _cell(self.svg, "M16HUB.QUE.M14TOM16.MESCURRENTQCNT")[2]

    def test_세로선이_그_분_자리(self):
        x, _y, w = _frame_of(self.c)
        x0, x1 = x + 12, x + w - 12
        # 창 09:15~09:59 (45분) 중 09:45 는 30번째
        want = x0 + (x1 - x0) * 30 / 44
        got = float(re.search(r'<line class="gsel" x1="([\d.]+)" y1="[\d.]+" x2="\1"', self.c).group(1))
        self.assertAlmostEqual(got, want, delta=0.11)

    def test_그_분_값_높이에_가로줄(self):
        m = re.search(r'<line class="gsel" x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="\2" '
                      r'[^>]*stroke-dasharray', self.c)
        self.assertTrue(m, "고른 분 가로줄이 없다")
        x, _y, w = _frame_of(self.c)
        self.assertAlmostEqual(float(m.group(1)), x + 12, delta=0.11)
        self.assertAlmostEqual(float(m.group(3)), x + w - 12, delta=0.11)
        cy = float(re.search(r'<circle cx="[\d.]+" cy="([\d.]+)" r="3.6"', self.c).group(1))
        self.assertAlmostEqual(float(m.group(2)), cy, delta=0.11, msg="점과 같은 높이 — 그 분 값 자리")

    def test_그_분_값을_적는다(self):
        self.assertRegex(self.c, r'class="gtag"[^>]*>09:45 · 525건<')     # 480 + 45분

    def test_흰_배경이면_검정(self):
        svg = G.render(_hub_rows(), CENTER, 60, cfg=CFG, theme="light")
        c = _cell(svg, "M16HUB.QUE.TIME.AVGTOTALTIME1MIN")[2]
        sel = G._pal("light")["sel"]
        self.assertRegex(c, r'<line class="gsel" [^>]*stroke="%s"[^>]*stroke-dasharray' % sel)
        r, g, b = (int(sel[k:k + 2], 16) for k in (1, 3, 5))
        self.assertLess(max(r, g, b), 0x40, "흰 배경에서 고른 분 줄은 검정 계열이어야 한다")

    def test_빈_분이_있어도_안_밀린다(self):
        """예전엔 값이 있는 분만 세서 칸 시간축을 잡아, 빈 분이 있으면 자리가 밀렸다."""
        rows = _hub_rows()
        for r in rows[15:25]:
            r["M16HUB.QUE.M14TOM16.MESCURRENTQCNT"] = ""
        c = _cell(G.render(rows, CENTER, 60, cfg=CFG), "M16HUB.QUE.M14TOM16.MESCURRENTQCNT")[2]
        x, _y, w = _frame_of(c)
        want = x + 12 + (w - 24) * 30 / 44
        got = float(re.search(r'<line class="gsel" x1="([\d.]+)" y1="[\d.]+" x2="\1"', c).group(1))
        self.assertAlmostEqual(got, want, delta=0.11)


class 막대는_없다_모두_선(unittest.TestCase):
    """고객: "왜 막대로 주냐 — 선으로 주라" · "pio 관련은 선을 2개 3개로"."""

    def _pio_rows(self):
        base = dt.datetime(2026, 9, 16, 14, 0)
        rows = []
        for i in range(60):
            rows.append({"datetime": (base + dt.timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M:%S"),
                         "unified_risk_score": str(30 + i % 20), "hot_area": "M14",
                         "all_score": "55", "area_score": str(30 + i % 20),
                         "reason": "발동: M14[R-A(AVGLOADTIME1MIN=9분)]; PIO(M14A<-M14B=4개/10분,합22)",
                         "M14_ra": str(8 + i % 5),
                         "M14A<-M14B_PIOERROR_DEPOSITED": str((i % 7 == 0) * 2),
                         "M16HUB<-M14A_PIOERROR_DEPOSITED": str(int(i % 9 == 3) * 3)})
        return base, rows

    def test_PIO_는_경로마다_선_하나(self):
        base, rows = self._pio_rows()
        svg = G.render(rows, base + dt.timedelta(minutes=30), 60, cfg=CFG)
        lines = re.findall(r'<path class="pio" d="[^"]+" fill="none" stroke="(#\w+)"', svg)
        self.assertEqual(len(lines), 2, "M14 경로 둘 — 선 둘")
        self.assertEqual(len(set(lines)), 2, "경로마다 색이 달라야 범례로 가린다")
        self.assertNotRegex(svg, r'<rect [^>]*width="[\d.]+" height="[\d.]+" fill="#\w+" opacity="0.95"/>')

    def test_리프터는_계단_선(self):
        rows = _rows("M16HUB", LFT_REASON, M16HUB_ra=lambda i: 8 + i % 5,
                     M16HUB_rd_fab=lambda i: 22 + i % 6, M16HUB_rev_lids=_lids)
        svg = G.render(rows, CENTER, 60, cfg=CFG)
        c = _cell(svg, "M16HUB.LFT.6ABL6011.TOTAL_CURRENTQCNT")[2]
        d = re.search(r'<path d="([^"]+)" fill="none" stroke="#\w+" stroke-width="2"', c).group(1)
        xs = re.findall(r'L([\d.]+),[\d.]+ L\1,', d)
        self.assertTrue(xs, "계단(같은 x 에서 위아래로 꺾임)이 없다")
        self.assertNotIn('rx="1.2"', svg, "막대가 남아 있다")


class 글자는_검정(unittest.TestCase):
    """고객: "가까이 되면 글자가 안 보이잖아 — 노란색 — 검은색으로 해라"."""

    def setUp(self):
        rows = _hub_rows()
        for r in rows[40:44]:
            r["unified_risk_score"] = "88"              # 사건 딱지가 서게
        self.svg = G.render(rows, CENTER, 60, cfg=CFG, theme="light")
        self.P = G._pal("light")

    def test_마우스를_대면_뜨는_글자(self):
        self.assertIn(".hvt{font:700 10.5px Consolas,monospace;text-anchor:end;fill:%s}"
                      % self.P["tx"], self.svg)
        self.assertNotIn('<g class="hv" fill=', self.svg, "칸 색(노랑)을 물려받으면 안 된다")

    def test_넘은_칸의_값_글자(self):
        c = _cell(self.svg, "M16HUB.QUE.TIME.AVGTOTALTIME1MIN")[2]
        self.assertIn("▲", c, "넘은 칸이어야 이 시험이 문다")
        m = re.search(r'font-size="14" font-weight="800" fill="(#\w+)"', c)
        self.assertEqual(m.group(1), self.P["tx"])
        badge = re.search(r'font-size="10.5" font-weight="700" text-anchor="middle" '
                          r'fill="(#\w+)">▲', c)
        self.assertEqual(badge.group(1), self.P["tx"])
        # 색은 선이 맡는다
        self.assertRegex(c, r'stroke="(%s|%s)" stroke-width="2"' % (self.P["evt"], self.P["crit"]))

    def test_사건_딱지(self):
        m = re.search(r'text-anchor="middle" fill="(#\w+)">사건1 ', self.svg)
        self.assertTrue(m, "사건 딱지가 없다")
        self.assertEqual(m.group(1), self.P["tx"])

    def test_노랑_주황_글자가_없다(self):
        warm = {self.P["evt"], self.P["crit"]} | set(self.P["path"]) | set(self.P["palette"])
        for col in re.findall(r'<text [^>]*fill="(#\w+)"', self.svg):
            self.assertNotIn(col, warm, "글자에 경계 · 주의 색을 썼다")


class 리프터_호기(unittest.TestCase):
    """주피터 발동이벤트 CSV(예측기 EVENT_FIELDS)에는 호기별 대기량 컬럼이 없다 —
    룰이 지목한 호기 이름만 M16HUB_rev_lids 에 실린다 (원문 표기는 '역증가')."""

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
        nm, lb, c, _y = _cell(svg, "M16HUB.LFT.6ABL6011.TOTAL_CURRENTQCNT")
        self.assertIn("감소 지목 분", lb)
        self.assertNotIn("역증가", c, "화면에 '역증가' 를 쓰지 않는다")
        self.assertIn("대기량 값은 CSV에 없음", c)
        self.assertIn("22분 걸림", c)               # 창 09:15~09:59 중 짝수 분
        self.assertRegex(c, r'class="gtag"[^>]*>09:45 · 안 걸림<')

    def test_값은_지목_목록에서(self):
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
        """예측기 CSV 에 호기별 컬럼이 생기면(구분자만 다르게 와도) 대기량 값으로 그린다."""
        svg = self._svg(M16HUB_rev_lids=_lids,
                        M16HUB_LFT_6ABL6011_TOTAL_CURRENTQCNT=lambda i: 3 + i % 4)
        nm, lb, c, _y = _cell(svg, "M16HUB.LFT.6ABL6011.TOTAL_CURRENTQCNT")
        self.assertNotIn("감소 지목", lb)
        self.assertRegex(c, r'class="gtag"[^>]*>09:45 · 4대<')       # 3 + 45 % 4

    def test_리프터_합_변화도_신규_지표로(self):
        """R-C' 는 지목 호기 수와 10대 합의 20분 변화(감소)를 같이 본다 — 음수도 그린다."""
        svg = self._svg(M16HUB_rev_lids=_lids,
                        M16HUB_rev_count=lambda i: len([x for x in _lids(i).split(",") if x]),
                        M16HUB_rc_trend=lambda i: (i % 15) - 10)
        ny = _section_y(svg, "신규 지표")
        new = {c[0]: c for c in _cells(svg) if c[3] > ny}
        self.assertIn("M16HUB_rev_count", new)
        self.assertIn("M16HUB_rc_trend", new)
        self.assertIn('stroke-dasharray="2 3"', new["M16HUB_rc_trend"][2], "0 자리에 가는 줄")


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


if __name__ == "__main__":
    unittest.main()
