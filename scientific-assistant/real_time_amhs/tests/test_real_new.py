# -*- coding: utf-8 -*-
"""더블클릭 구간 그래프 = 그 줄 실시간 표 '실제지표' 칸 그대로 (2026-10-07).

고객
    "실제지표에 M16HUB.QUE.M14TOM16.MESCURRENTQCNT · M16HUB.QUE.TIME.AVGTOTALTIME1MIN ·
     M16HUB.STRATE.ALL.FABSTORAGERATIO 이런게 나오면 더블클릭했을 저 그래프들이
     나와야지 — 1개만 나오네 그러면 안되"
    "더블클릭하면 1개는 똑바로 나오고 나머지는 전혀 다른게 나와 — 실제지표에 맞게 하라고"
    "pio 대표 1개만 표시해라 전부다" · "기여도 추정 삭제해라 필요없어"
    (전날) "M16HUB 리프터 정체 하고 밑에 실제 컬럼이 있는데 반대로 해라"
           "우리가 만든 rb… 지표는 신규 지표라고 해서 따로"

지키는 것
    ① 그래프 '실제지표' 칸 = 그 줄 표 '실제지표' 칸 (같은 함수 · 같은 인자). 더하지도
       빼지도 않는다 — 값이 안 온 것은 칸 대신 '값이 안 온 컬럼' 줄에 이름이 남는다.
    ② 다른 분의 실제지표 · 그 줄과 상관없는 FAB 룰 컬럼을 끼워 넣지 않는다.
    ③ PIO 는 한 칸 (경로 전부를 쌓는다). 점수 · 가중합 · 10분 합 칸은 따로 없다.
    ④ 신규 지표 = 그 줄 룰이 본 계산 컬럼만 (R-B → rb_diff).
    ⑤ 칸 윗줄 = 컬럼 이름, 아랫줄 = 한글 이름.
"""
import datetime as dt
import re
import unittest

from . import util  # noqa: F401

import graphs as G  # noqa: E402
import sentinel as S  # noqa: E402
from lp_client import load_config  # noqa: E402

CFG = load_config()
BASE = dt.datetime(2026, 10, 6, 9, 0)
CENTER = BASE + dt.timedelta(minutes=45)
PIO_SUF = "_PIOERROR_DEPOSITED"

# 고객이 짚은 그 줄 — M16HUB 화면, R-B · R-A′ · R-D(FAB저장)
HUB_REASON = ("hot_area=M16HUB; S2경고; 발동: M16HUB[R-A'(AVGTOTALTIME1MIN=10.4분/기준9.0),"
              "R-B(30분+120건),R-D(FAB저장=26.1%)]")


def _rows(fab="", reason="", n=60, **cols):
    """1분 간격 n행. fab 을 주면 FAB 분리 파일 행(all_score 있음)이다."""
    out = []
    for i in range(n):
        r = {"datetime": (BASE + dt.timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M:%S"),
             "unified_risk_score": str(30 + i % 25), "hot_area": fab or "M16HUB",
             "reason": reason(i) if callable(reason) else reason}
        if fab:
            r.update({"all_score": "50", "area_score": r["unified_risk_score"]})
        for k, v in cols.items():
            r[k] = "" if v is None else str(v(i) if callable(v) else v)
        out.append(r)
    return out


def _hub_rows(**more):
    """M16HUB 분리 파일 — 고객 화면처럼 실제지표 셋 + **상관없는 컬럼도 값이 잔뜩** 있다."""
    cols = {"M16HUB_ra": lambda i: 8 + i % 4, "M16HUB_rd_fab": lambda i: 24 + i % 4,
            "M16HUB_rb_diff30": lambda i: 80 + i, "M16HUB_rb_diff10": lambda i: 20 + i % 9,
            "M16HUB.QUE.M14TOM16.MESCURRENTQCNT": lambda i: 480 + i,
            # ↓ 그 줄 실제지표가 아니다 — 그래프에 섰다간 '전혀 다른게' 가 된다
            "sla_M16HUB": lambda i: 4 + i % 4, "M16HUB_sla_cnt": lambda i: 400 + 3 * i,
            "sorter_M16HUB": lambda i: i % 40, "M16HUB_rev_count": lambda i: i % 5,
            "M16HUB.QUE.ALL.3F_TO_3F_MLUD_JOB": lambda i: 40 + i % 25,
            "M16HUB.QUE.LFT.3F_LFT_MAXCAPA": 120, "area_pio_score": lambda i: i % 10,
            "area_pio_wsum10": lambda i: 3 * (i % 9)}
    cols.update(more)
    return _rows("M16HUB", HUB_REASON, **cols)


def _un(s):
    return s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def _cells(svg):
    """[(윗줄 컬럼 이름, 아랫줄 한글 이름, 칸 마크업, 칸 y)] — 그린 순서대로."""
    marks = list(re.finditer(r'<rect x="([\d.]+)" y="([\d.]+)" width="[\d.]+" '
                             r'height="[\d.]+" rx="10"', svg))
    out = []
    for k, m in enumerate(marks):
        end = marks[k + 1].start() if k + 1 < len(marks) else len(svg)
        chunk = svg[m.start():end]
        # 묶음의 마지막 칸 뒤에는 다음 묶음 제목·'값이 안 온' 줄(x=PAD)이 붙는다 — 떼어 낸다
        cut = chunk.find('<text x="16" ')
        chunk = chunk[:cut] if cut > 0 else chunk
        nm = re.search(r'class="mname"[^>]*>([^<]*)', chunk)
        lb = re.search(r'class="mlbl"[^>]*>([^<]*)', chunk)
        if nm and lb:
            out.append((_un(nm.group(1)), _un(lb.group(1)), chunk, float(m.group(2))))
    return out


def _names(svg):
    return [c[0] for c in _cells(svg)]


def _empty_line(svg):
    m = re.search(r">(값이 안 온 컬럼 — [^<]*)", svg)
    t = re.search(r"값이 안 온 컬럼 — [^<]*<title>([^<]*)</title>", svg)
    return _un((m.group(1) if m else "") + " " + (t.group(1) if t else ""))


def _section_y(svg, title):
    m = re.search(r'<text x="\d+" y="([\d.]+)"[^>]*>' + title + " <tspan", svg)
    return float(m.group(1)) if m else None


def _sel_row(rows, at=CENTER):
    pts = G.window_rows(rows, at, 60, CFG)
    return min(pts, key=lambda tr: abs((tr[0] - at).total_seconds()))[1]


class 그래프는_그_줄_실제지표_칸_그대로(unittest.TestCase):
    """★핵심. 표 칸에 셋이면 그래프 실제지표도 그 셋 — 엉뚱한 칸이 끼면 안 된다."""

    def _check(self, rows, fab=""):
        """표 칸(row_metrics = 서버 /api/feed 와 같은 함수)과 그래프가 1:1 인가."""
        svg = G.render(rows, CENTER, 60, cfg=CFG)
        table = G.row_metrics(_sel_row(rows), fab)
        want = {m["raw"] for m in table if not G._is_pio(m)}
        has_pio = any(G._is_pio(m) for m in table)
        ny = _section_y(svg, "신규 지표")
        cells = _cells(svg)
        real = [c for c in cells if ny is None or c[3] < ny]
        pio = [c for c in real if c[0].endswith(PIO_SUF) or "PIO" in c[1]]
        drawn = {c[0] for c in real if c not in pio}
        empty = _empty_line(svg)
        for name in drawn:
            self.assertIn(name, want, f"표 칸에 없는 {name} 이 그래프에 섰다 — '전혀 다른게'")
        for raw in want:
            self.assertTrue(raw in drawn or raw in empty,
                            f"표 칸의 {raw} 가 그래프에서 말없이 빠졌다")
        self.assertEqual(len(pio), 1 if has_pio else 0, [c[0] for c in pio])
        return svg, table

    def test_고객이_짚은_그_줄(self):
        """MESCURRENTQCNT · AVGTOTALTIME1MIN · FABSTORAGERATIO — 그 셋이 칸으로 선다."""
        svg, table = self._check(_hub_rows(), "M16HUB")
        self.assertEqual({m["raw"] for m in table},
                         {"M16HUB.QUE.M14TOM16.MESCURRENTQCNT",
                          "M16HUB.QUE.TIME.AVGTOTALTIME1MIN",
                          "M16HUB.STRATE.ALL.FABSTORAGERATIO"})
        names = set(_names(svg))
        for want in ("M16HUB.QUE.M14TOM16.MESCURRENTQCNT", "M16HUB.QUE.TIME.AVGTOTALTIME1MIN",
                     "M16HUB.STRATE.ALL.FABSTORAGERATIO"):
            self.assertIn(want, names)

    def test_상관없는_컬럼은_값이_있어도_안_선다(self):
        names = set(_names(G.render(_hub_rows(), CENTER, 60, cfg=CFG)))
        for gone in ("M16HUB.QUE.ALL.TRANSPORT4MINOVERRATIO", "M16HUB.QUE.ALL.TRANSPORT4MINOVERCNT",
                     "M16HUB.SORTER.ABN.SORTERWAITCOUNTOVER", "M16HUB.QUE.ALL.3F_TO_3F_MLUD_JOB",
                     "M16HUB.QUE.LFT.3F_LFT_MAXCAPA", "area_pio_score", "area_pio_wsum10",
                     "M16HUB_rev_count"):
            self.assertNotIn(gone, names)

    def test_ALL(self):
        """ALL 표 칸은 hot_area 블록만 본다 — M14 블록 칸이 섞이면 안 된다."""
        svg, _t = self._check(_rows(
            reason="발동: M16HUB[R-A_sus,R-D(FAB저장=26%)]; M14[R-A_sus]",
            M16HUB_ra=lambda i: 7 + i % 3, M14_ra=lambda i: 3 + i % 2,
            M16HUB_rd_fab=lambda i: 20 + i % 5))
        names = _names(svg)
        self.assertNotIn("M14.QUE.LOAD.AVGLOADTIME1MIN", names)
        self.assertIn("M16HUB.QUE.TIME.AVGTOTALTIME1MIN", names)

    def test_ALL_PIO(self):
        self._check(_rows(
            reason="발동: M16HUB[R-A_sus]; PIO(M14A<-M14B=9개/10분,합30)",
            M16HUB_ra=7, pio_10min_cnt=lambda i: 10 + i % 20,
            **{"M14A<-M14B" + PIO_SUF: lambda i: i % 4}))

    def test_다른_분의_실제지표는_안_끼운다(self):
        """바로 앞 분에 R-D 가 떴어도 누른 분 칸에 없으면 그래프에도 없다."""
        rows = _rows(reason=lambda i: ("발동: M16HUB[R-D(FAB저장=27%)]" if i == 40
                                       else "발동: M16HUB[R-A_sus]"),
                     M16HUB_ra=7, M16HUB_rd_fab=lambda i: 20 + i % 8)
        names = _names(G.render(rows, CENTER, 60, cfg=CFG))
        self.assertNotIn("M16HUB.STRATE.ALL.FABSTORAGERATIO", names)
        self.assertIn("M16HUB.QUE.TIME.AVGTOTALTIME1MIN", names)

    def test_원본_이름으로만_실려_와도_그린다(self):
        """CSV 가 M16HUB_ra 대신 원본 이름으로만 싣는 곳도 칸이 선다."""
        rows = _rows(reason="발동: M16HUB[R-A_sus]",
                     **{"M16HUB.QUE.TIME.AVGTOTALTIME1MIN": lambda i: 6 + i % 4})
        svg = G.render(rows, CENTER, 60, cfg=CFG)
        self.assertIn("M16HUB.QUE.TIME.AVGTOTALTIME1MIN", _names(svg))
        self.assertNotIn("AVGTOTALTIME1MIN", _empty_line(svg))

    def test_값이_안_온_실제지표는_이름이_남는다(self):
        """원본 대기 물량이 CSV 에 없으면 칸 대신 맨 아래 줄에 — 말없이 빠지지 않는다."""
        rows = _hub_rows(**{"M16HUB.QUE.M14TOM16.MESCURRENTQCNT": None})
        svg, _t = self._check(rows, "M16HUB")
        self.assertIn("M16HUB.QUE.M14TOM16.MESCURRENTQCNT", _empty_line(svg))


class 실제지표와_신규_지표(unittest.TestCase):

    def setUp(self):
        self.svg = G.render(_hub_rows(), CENTER, 60, cfg=CFG)

    def test_두_묶음_제목(self):
        self.assertIn(">실제지표 <", self.svg)
        self.assertIn(">신규 지표 <", self.svg)

    def test_신규_지표는_그_줄_룰이_본_계산_컬럼만(self):
        """R-B 가 떴다 → rb_diff30. R-B_fast 가 아니니 rb_diff10 은 없다. 리프터 정체는
        그 줄 룰이 아니다 — 값이 있어도 안 선다."""
        ny = _section_y(self.svg, "신규 지표")
        new = [c[0] for c in _cells(self.svg) if c[3] > ny]
        self.assertEqual(new, ["M16HUB_rb_diff30"])

    def test_R_B_fast_면_10분_증가도(self):
        rows = _rows("M16HUB", "발동: M16HUB[R-B(30분+120건),R-B_fast(10분+40건)]",
                     M16HUB_rb_diff30=lambda i: 80 + i, M16HUB_rb_diff10=lambda i: 20 + i % 9)
        svg = G.render(rows, CENTER, 60, cfg=CFG)
        ny = _section_y(svg, "신규 지표")
        new = {c[0] for c in _cells(svg) if c[3] > ny}
        self.assertEqual(new, {"M16HUB_rb_diff30", "M16HUB_rb_diff10"})

    def test_두_묶음이_같은_칸_폭이다(self):
        """위아래 칸 폭이 다르면 같은 자로 잰 그래프로 안 읽힌다."""
        ws = set(re.findall(r'<rect x="[\d.]+" y="[\d.]+" width="([\d.]+)" '
                            r'height="[\d.]+" rx="10"', self.svg))
        self.assertEqual(len(ws), 1, ws)

    def test_분류_규칙(self):
        for c in ("M16HUB_rb_diff30", "M14B_rb_diff10", "M14_cnv_skew", "M16HUB_rev_count",
                  "M16HUB_rc_trend", "pio_10min_cnt", "area_pio_score", "area_pio_wsum10",
                  "M16B_PIO_SCORE"):
            self.assertTrue(G.is_new_metric(c), c)
        for c in ("M16HUB_ra", "sla_M16B", "sorter_M14", "M16B_rd_oht", "M16HUB_rd_fab",
                  "M16HUB_stb_util", "M16B_sla_cnt", "M16A_sorter_fail",
                  "M16A->M16B" + PIO_SUF, "M16HUB.QUE.TIME.AVGTOTALTIME1MIN"):
            self.assertFalse(G.is_new_metric(c), c)


class PIO_는_대표_한_칸(unittest.TestCase):
    """고객: "pio 대표 1개만 표시해라 전부다" — 경로 전부를 한 칸에 쌓는다."""

    def _rows(self):
        return _rows("M14", "발동: M14[R-A(AVGLOADTIME1MIN=9분)]; PIO(M14A<-M14B=4개/10분,합22)",
                     M14_ra=lambda i: 8 + i % 5, area_pio_score=lambda i: i % 10,
                     area_pio_wsum10=lambda i: 4 * (i % 9),
                     **{"M14A<-M14B" + PIO_SUF: lambda i: i % 4,
                        "M16HUB<-M14A" + PIO_SUF: lambda i: i % 3})

    def test_한_칸에_경로가_다_있다(self):
        svg = G.render(self._rows(), CENTER, 60, cfg=CFG)
        pio = [c for c in _cells(svg) if "PIO" in c[1] or c[0].endswith(PIO_SUF)]
        self.assertEqual(len(pio), 1, [c[0] for c in pio])
        legend = {_un(x) for x in re.findall(r'font-size="8.5"[^>]*>([^<]*)', pio[0][2])}
        tips = " ".join(_un(x) for x in re.findall(r'class="hvt"[^>]*>([^<]*)', pio[0][2]))
        for p in ("M14A<-M14B", "M16HUB<-M14A"):
            self.assertTrue(any(x.startswith(p) for x in legend) or p in tips, p)

    def test_점수_가중합_칸은_없다(self):
        names = _names(G.render(self._rows(), CENTER, 60, cfg=CFG))
        self.assertNotIn("area_pio_score", names)
        self.assertNotIn("area_pio_wsum10", names)


class 실제지표가_없는_분(unittest.TestCase):

    def test_FAB_은_룰_컬럼을_대신_보여_주고_그렇다고_적는다(self):
        """룰이 안 걸린 분 — 점수 그래프 하나만 뜨면 무엇이 얼마였는지 볼 길이 없다."""
        rows = _rows("M16B", "", M16B_ra=lambda i: 2.5 + (i % 7) * 0.2,
                     M16B_rd_oht=lambda i: 78 + i % 9)
        svg = G.render(rows, CENTER, 60, cfg=CFG)
        self.assertIn("이 분은 발동한 룰이 없어 M16B 룰 컬럼", svg)
        self.assertIn("M16B.QUE.LOAD.AVGLOADTIME1MIN", _names(svg))

    def test_ALL_은_없다고_말한다(self):
        rows = _rows(reason="", M16HUB_ra=7)
        svg = G.render(rows, CENTER, 60, cfg=CFG)
        self.assertEqual(_names(svg), [])
        self.assertIn("이 구간에 그릴 실제지표가 없습니다", svg)


class 칸_윗줄은_컬럼_아랫줄은_한글(unittest.TestCase):
    """고객: "실제지표를 하고 밑에 M16HUB 리프터 정체" — 예전과 순서가 반대다."""

    def setUp(self):
        rows = _rows(reason="발동: M16HUB[R-A'(AVGTOTALTIME1MIN=12분/기준9.0),R-C]",
                     M16HUB_ra=lambda i: 8 + i % 5, M16HUB_rev_count=lambda i: i % 6)
        self.cells = {c[1]: c for c in _cells(G.render(rows, CENTER, 60, cfg=CFG))}

    def test_리프터_정체(self):
        name, _label, chunk, _y = self.cells["M16HUB 리프터 정체"]
        self.assertEqual(name, "M16HUB_rev_count")
        ny = float(re.search(r'class="mname" x="[\d.]+" y="([\d.]+)"', chunk).group(1))
        ly = float(re.search(r'class="mlbl" x="[\d.]+" y="([\d.]+)"', chunk).group(1))
        self.assertLess(ny, ly, "컬럼 이름이 한글 이름보다 위에 있어야 한다")

    def test_실제지표는_AMOS_이름이_위(self):
        self.assertEqual(self.cells["M16HUB 반송시간"][0], "M16HUB.QUE.TIME.AVGTOTALTIME1MIN")

    def test_컬럼_이름은_굵게(self):
        chunk = self.cells["M16HUB 반송시간"][2]
        self.assertRegex(chunk, r'class="mname"[^>]*font-weight="700"')
        self.assertNotRegex(chunk, r'class="mlbl"[^>]*font-weight="700"')

    def test_긴_이름은_자르지_않고_줄인다(self):
        """3열 칸에서도 가장 긴 원본 이름(44자)이 통째로 남는다."""
        rows = _rows("M16HUB", "발동: M16HUB[R-A_sus,R-D(수동=40,FAB저장=26%),SLA(6.1%4분초과)]", **{
            "M16HUB.QUE.ALL.M16HUBTOM14MANUAL_CURRENTQCNT": lambda i: 20 + i % 15,
            "M16HUB_ra": 7, "sla_M16HUB": 3, "M16HUB_rd_fab": 24})
        svg = G.render(rows, CENTER, 60, cfg=CFG)
        self.assertGreaterEqual(len(_names(svg)), 3, "3열이 되어야 좁은 칸을 시험한다")
        self.assertIn("M16HUB.QUE.ALL.M16HUBTOM14MANUAL_CURRENTQCNT", _names(svg))


class 임계를_엉뚱한_값에_긋지_않는다(unittest.TestCase):

    def _cell(self, svg, name):
        return next(c[2] for c in _cells(svg) if c[0] == name)

    def test_원본_대기물량에는_증가량_임계를_안_긋는다(self):
        """R-B 임계(30분 +100건)는 증가량에 거는 값이다 — 물량 500건에 그으면 5배가 된다."""
        svg = G.render(_hub_rows(), CENTER, 60, cfg=CFG)
        raw = self._cell(svg, "M16HUB.QUE.M14TOM16.MESCURRENTQCNT")
        self.assertNotIn("임계", raw)
        self.assertNotIn("▲", raw)
        self.assertIn("임계 100", self._cell(svg, "M16HUB_rb_diff30"))

    def test_누적_건수에는_임계를_안_긋는다(self):
        rows = _rows("M16HUB", "발동: M16HUB[SLA(6.1%4분초과)]",
                     sla_M16HUB=lambda i: 4 + i % 4, M16HUB_sla_cnt=lambda i: 400 + 3 * i)
        svg = G.render(rows, CENTER, 60, cfg=CFG)
        c = self._cell(svg, "M16HUB.QUE.ALL.TRANSPORT4MINOVERCNT")
        self.assertNotIn("임계", c)
        self.assertNotIn("▲", c)
        self.assertIn("누적", c, "누적 값이라는 걸 이름에 적어야 한다")

    def test_원본으로만_싣는_컬럼도_임계가_선다(self):
        """MLUD 잡은 CSV 복사본이 없다 — 원본 이름으로 임계(50)를 찾아야 한다."""
        rows = _rows("M16HUB", "발동: M16HUB[R-D(MLUD=60)]",
                     **{"M16HUB.QUE.ALL.3F_TO_3F_MLUD_JOB": lambda i: 40 + i % 25})
        svg = G.render(rows, CENTER, 60, cfg=CFG)
        self.assertIn("임계 50", self._cell(svg, "M16HUB.QUE.ALL.3F_TO_3F_MLUD_JOB"))


class 값이_안_온_컬럼은_컬럼_이름으로(unittest.TestCase):

    def test_이름과_한글을_같이_적는다(self):
        rows = _rows(reason="발동: M16HUB[R-A(AVGTOTALTIME1MIN=15.9분),R-C]", M16HUB_ra=12)
        line = _empty_line(G.render(rows, CENTER, 60, cfg=CFG))
        self.assertIn("M16HUB_rev_count (M16HUB 리프터 정체)", line)

    def test_넘치면_접고_말풍선에_전부(self):
        lifts = ",".join(S._HUB_LIFTERS)
        rows = _rows("M16HUB", f"발동: M16HUB[R-C'(역증가10개:{lifts})]", M16HUB_ra=7)
        svg = G.render(rows, CENTER, 60, cfg=CFG)
        self.assertRegex(svg, r"값이 안 온 컬럼 — [^<]* 외 \d+개<title>")
        for x in S._HUB_LIFTERS:
            self.assertIn(f"M16HUB.LFT.{x}.TOTAL_CURRENTQCNT", _empty_line(svg))


class 실시간_화면에서_자주_보는_모양(unittest.TestCase):
    """월드모델파생 실시간 스코어 탭은 늘 **마지막 분**을 더블클릭한다."""

    def test_끝_분을_고르면_시각이_안_겹친다(self):
        """고른 시각과 끝 시각이 한자리에 겹쳐 '23:2344' 로 읽혔다."""
        rows = _rows("M14", "", M14_ra=3)
        svg = G.render(rows, BASE + dt.timedelta(minutes=59), 60, cfg=CFG)
        self.assertEqual(svg.count(">09:59<"), 1, "끝 시각을 두 번 적었다")
        self.assertRegex(svg, r'text-anchor="end" fill="[^"]+" font-weight="700"[^>]*>09:59<',
                         "고른 시각이 칸 밖으로 안 나가게 끝에 맞춰야 한다")

    def test_가운데를_고르면_양끝이_다_있다(self):
        svg = G.render(_rows("M14", "", M14_ra=3), CENTER, 60, cfg=CFG)
        for t in (">09:15<", ">09:45<", ">09:59<"):
            self.assertIn(t, svg)

    def test_R_B_fast_이름이_무엇의_증가인지_말한다(self):
        """상세도 표 이름 '같은 대기 10분 증가' 만으로는 무엇과 같은지 모른다."""
        svg = G.render(_rows("M14", "", M14_rb_diff10=lambda i: i % 7), CENTER, 60, cfg=CFG)
        lb = [c[1] for c in _cells(svg)]
        self.assertIn("M14 3F→HUB 대기 10분 증가", lb)
        self.assertFalse([x for x in lb if "같은 " in x], lb)


class 기여도_추정은_없다(unittest.TestCase):
    """고객: "기여도 추정 삭제해라 필요없어"."""

    def test_관제_그래프_밑에_안_붙는다(self):
        import os
        with open(os.path.join(util.BASE, "static", "dashboard.html"), encoding="utf-8") as f:
            h = f.read()
        i = h.index("async function drawGraph(){")
        body = h[i:h.index("\n}", i)]
        self.assertNotIn("/api/contrib", body)
        self.assertNotIn("${con}", body)

    def test_열려_있던_옛_화면도_빈_글을_받는다(self):
        """새로고침 안 한 화면이 아직 /api/contrib 를 부른다 — 404 페이지가 박히면 안 된다."""
        import os
        with open(os.path.join(util.BASE, "server.py"), encoding="utf-8") as f:
            src = f.read()
        i = src.index("def api_contrib():")
        body = src[i:src.index("\n@app.route", i)]
        self.assertIn('Response(b"", mimetype="text/html")', body)
        self.assertNotIn("explain_html", src)


if __name__ == "__main__":
    unittest.main()
