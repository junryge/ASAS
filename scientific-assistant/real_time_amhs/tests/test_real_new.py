# -*- coding: utf-8 -*-
"""더블클릭 구간 그래프 · 기여도 추정 — 실제지표 / 신규 지표 (2026-10-06).

고객
    "우리 더블클릭해서 그래프 보여주는 부분 실제지표 데이터를 보여줘 상위에는
     스코어 그리고 실제지표 그래프를 보여주라. 실제지표 전부다 … 하단에 기여도
     추정에는 실제지표 기여도를 추정을 보여주고"
    "실시간 보면 실제지표 컬럼들을 그래프로 보여주라 기여도도 마찬가지 실제지표로"
    "M16HUB 리프터 정체 하고 밑에 실제 컬럼이 있는데 반대로 해라 —
     실제지표를 하고 밑에 M16HUB 리프터 정체"
    "우리가 만든 rb… 지표는 신규 지표라고 해서 따로 … 실제지표로 따로 신규지표로 따로"

지키는 것
    ① 실시간 표 '실제지표' 칸에 뜨는 컬럼은 **전부** 그래프에 칸으로 서거나,
       값이 안 왔으면 '값이 안 온 컬럼' 줄에 이름이 남는다 (말없이 빠지지 않는다).
    ② 칸 윗줄 = 컬럼 이름, 아랫줄 = 한글 이름.
    ③ 우리가 계산해 만든 컬럼(rb_diff·rev_count·PIO 점수…)은 '신규 지표' 묶음에.
    ④ 기여도 추정이 그래프와 **같은 목록**을 따지고, 두 묶음을 따로 100% 로 나눈다.
"""
import datetime as dt
import re
import unittest

from . import util  # noqa: F401

import contrib as C  # noqa: E402
import graphs as G  # noqa: E402
import sentinel as S  # noqa: E402
from lp_client import load_config  # noqa: E402

CFG = load_config()
BASE = dt.datetime(2026, 10, 6, 9, 0)
CENTER = BASE + dt.timedelta(minutes=45)


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


def _cells(svg):
    """[(윗줄 컬럼 이름, 아랫줄 한글 이름, 칸 마크업, 칸 y)] — 그린 순서대로."""
    marks = [m for m in re.finditer(r'<rect x="([\d.]+)" y="([\d.]+)" width="[\d.]+" '
                                    r'height="[\d.]+" rx="10"', svg)]
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


def _un(s):
    return s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def _names(svg):
    return [c[0] for c in _cells(svg)]


def _empty_line(svg):
    m = re.search(r">(값이 안 온 컬럼 — [^<]*)", svg)
    t = re.search(r"값이 안 온 컬럼 — [^<]*<title>([^<]*)</title>", svg)
    return _un((m.group(1) if m else "") + " " + (t.group(1) if t else ""))


def _section_y(svg, title):
    m = re.search(r'<text x="\d+" y="([\d.]+)"[^>]*>' + title + " <tspan", svg)
    return float(m.group(1)) if m else None


class 칸_윗줄은_컬럼_아랫줄은_한글(unittest.TestCase):
    """고객: "실제지표를 하고 밑에 M16HUB 리프터 정체" — 예전과 순서가 반대다."""

    def setUp(self):
        rows = _rows(reason="발동: M16HUB[R-A'(AVGTOTALTIME1MIN=12분/기준9.0),R-C]",
                     M16HUB_ra=lambda i: 8 + i % 5, M16HUB_rev_count=lambda i: i % 6)
        self.cells = {c[1]: c for c in _cells(G.render(rows, CENTER, 60, cfg=CFG))}

    def test_리프터_정체(self):
        name, label, chunk, _y = self.cells["M16HUB 리프터 정체"]
        self.assertEqual(name, "M16HUB_rev_count")
        ny = float(re.search(r'class="mname" x="[\d.]+" y="([\d.]+)"', chunk).group(1))
        ly = float(re.search(r'class="mlbl" x="[\d.]+" y="([\d.]+)"', chunk).group(1))
        self.assertLess(ny, ly, "컬럼 이름이 한글 이름보다 위에 있어야 한다")

    def test_실제지표는_AMOS_이름이_위(self):
        name, _l, _c, _y = self.cells["M16HUB 반송시간"]
        self.assertEqual(name, "M16HUB.QUE.TIME.AVGTOTALTIME1MIN")

    def test_컬럼_이름은_굵게(self):
        chunk = self.cells["M16HUB 반송시간"][2]
        self.assertRegex(chunk, r'class="mname"[^>]*font-weight="700"')
        self.assertNotRegex(chunk, r'class="mlbl"[^>]*font-weight="700"')

    def test_긴_이름은_자르지_않고_줄인다(self):
        """3열 칸에서도 가장 긴 원본 이름(44자)이 통째로 남는다."""
        rows = _rows("M16HUB", "발동: M16HUB[R-D(수동=40)]", **{
            "M16HUB.QUE.ALL.M16HUBTOM14MANUAL_CURRENTQCNT": lambda i: 20 + i % 15,
            "M16HUB_ra": 7, "sla_M16HUB": 3, "sorter_M16HUB": 9})
        svg = G.render(rows, CENTER, 60, cfg=CFG)
        self.assertIn("M16HUB.QUE.ALL.M16HUBTOM14MANUAL_CURRENTQCNT", _names(svg))


class 실제지표와_신규_지표를_따로_깐다(unittest.TestCase):

    def setUp(self):
        self.rows = _rows("M16B", "발동: M16B[R-A'(AVGLOADTIME1MIN=3.6분/기준3.12),R-B(30분+25건)]",
                          M16B_ra=lambda i: 2.5 + (i % 7) * 0.2,
                          M16B_rb_diff30=lambda i: i % 30 - 5,
                          M16B_rb_diff10=lambda i: i % 12 - 3,
                          M16B_rd_oht=lambda i: 78 + i % 9,
                          sla_M16B=lambda i: 8 + i % 8, sorter_M16B=lambda i: i % 40,
                          **{"M16A->M16B_PIOERROR_DEPOSITED": lambda i: i % 3})
        self.svg = G.render(self.rows, CENTER, 60, cfg=CFG)

    def test_두_묶음_제목이_있다(self):
        self.assertIn(">실제지표 <", self.svg)
        self.assertIn(">신규 지표 <", self.svg)

    def test_rb_diff_는_신규_지표_묶음에(self):
        ny = _section_y(self.svg, "신규 지표")
        by = {c[0]: c[3] for c in _cells(self.svg)}
        for col in ("M16B_rb_diff30", "M16B_rb_diff10"):
            self.assertGreater(by[col], ny, f"{col} 이 신규 지표 묶음 밖에 있다")

    def test_원본은_실제지표_묶음에(self):
        ny = _section_y(self.svg, "신규 지표")
        by = {c[0]: c[3] for c in _cells(self.svg)}
        for col in ("M16B.QUE.LOAD.AVGLOADTIME1MIN", "M16B.QUE.OHT.OHTUTIL",
                    "M16B.QUE.ALL.TRANSPORT4MINOVERRATIO",
                    "M16B.SORTER.ABN.SORTERWAITCOUNTOVER", "M16A->M16B_PIOERROR_DEPOSITED"):
            self.assertLess(by[col], ny, f"{col} 이 실제지표 묶음 밖에 있다")

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
                  "M16A->M16B_PIOERROR_DEPOSITED", "M16HUB.QUE.TIME.AVGTOTALTIME1MIN"):
            self.assertFalse(G.is_new_metric(c), c)


class 실시간_표_실제지표가_전부_선다(unittest.TestCase):
    """서버 /api/feed 의 '실제지표' 칸(sentinel.fab_metrics / reason_metrics)에
    뜨는 컬럼마다 — 칸이 서거나, 값이 안 왔으면 '값이 안 온 컬럼' 에 이름이 남는다."""

    def _check(self, rows, fab=""):
        svg = G.render(rows, CENTER, 60, cfg=CFG)
        names = set(_names(svg))
        legend = set(_un(x) for x in re.findall(r'font-size="8.5"[^>]*>([^<]*)', svg))
        tips = " ".join(_un(x) for x in re.findall(r'class="hvt"[^>]*>([^<]*)', svg))
        empty = _empty_line(svg)
        for _t, r in G.window_rows(rows, CENTER, 60, CFG):
            ms = (S.fab_metrics(r["reason"], fab, r) if fab
                  else S.reason_metrics(r["reason"], r["hot_area"], r))
            for m in ms:
                raw, col = m["raw"], m["col"]
                if col.endswith("_PIOERROR_DEPOSITED"):
                    path = col[:-len("_PIOERROR_DEPOSITED")]
                    ok = (col in names or any(x.startswith(path) for x in legend)
                          or path in tips or col in empty)
                else:
                    ok = raw in names or col in names or raw in empty or col in empty
                self.assertTrue(ok, f"실시간 표 실제지표 {raw} ({col}) 가 그래프에서 말없이 빠졌다")
        return svg

    def test_FAB_M16HUB(self):
        svg = self._check(_rows(
            "M16HUB",
            lambda i: ("발동: M16HUB[R-A'(AVGTOTALTIME1MIN=10분/기준9.0),R-B(30분+120건),"
                       "R-C'(역증가4개:6ABL6021,6ABL6032),R-D(FAB저장=26%,MLUD=60),"
                       "SLA(6.1%4분초과)]" if i % 4 else "발동: M16HUB[R-A_sus]"),
            M16HUB_ra=lambda i: 8 + i % 4, M16HUB_rb_diff30=lambda i: 80 + i,
            M16HUB_rev_count=lambda i: i % 5, M16HUB_rd_fab=lambda i: 24 + i % 4,
            sla_M16HUB=lambda i: 4 + i % 4, M16HUB_sla_cnt=lambda i: 400 + 3 * i,
            **{"M16HUB.QUE.ALL.3F_TO_3F_MLUD_JOB": lambda i: 40 + i % 25,
               "M16HUB->M14A_PIOERROR_DEPOSITED": lambda i: i % 2}), "M16HUB")
        names = _names(svg)
        self.assertIn("M16HUB.QUE.ALL.3F_TO_3F_MLUD_JOB", names,
                      "CSV 에 원본 이름으로만 실려 오는 실제지표도 칸이 서야 한다")
        self.assertIn("M16HUB.LFT.6ABL6021.TOTAL_CURRENTQCNT", _empty_line(svg),
                      "값이 안 온 리프터 컬럼은 이름이 남아야 한다")

    def test_ALL(self):
        self._check(_rows(
            reason=lambda i: ("발동: M16HUB[R-A_sus,R-C,R-D(STB=99%)]; "
                              "PIO(M14A<-M14B=9개/10분,합30)" if i > 20 else
                              "발동: M14[R-A(AVGLOADTIME1MIN=4.1분)]"),
            M16HUB_ra=lambda i: 7 + i % 3, M14_ra=lambda i: 3 + i % 2,
            M16HUB_stb_util=99, M16HUB_rd_fab=lambda i: 20 + i % 5,
            pio_10min_cnt=lambda i: 10 + i % 20,
            **{"M14A<-M14B_PIOERROR_DEPOSITED": lambda i: i % 4}))

    def test_창_안_다른_분의_실제지표도_선다(self):
        """고른 분 reason 에는 없어도 바로 앞 분에 떴던 실제지표는 칸이 선다."""
        rows = _rows(reason=lambda i: ("발동: M16HUB[R-D(FAB저장=27%)]" if i == 40
                                       else "발동: M16HUB[R-A_sus]"),
                     M16HUB_ra=7, M16HUB_rd_fab=lambda i: 20 + i % 8)
        self.assertIn("M16HUB.STRATE.ALL.FABSTORAGERATIO",
                      _names(G.render(rows, CENTER, 60, cfg=CFG)))

    def test_원본_이름으로만_실려_와도_그린다(self):
        """CSV 가 M16HUB_ra 대신 원본 이름으로만 싣는 곳 — 예전엔 '값이 안 온 컬럼' 이었다."""
        rows = _rows(reason="발동: M16HUB[R-A_sus]",
                     **{"M16HUB.QUE.TIME.AVGTOTALTIME1MIN": lambda i: 6 + i % 4})
        svg = G.render(rows, CENTER, 60, cfg=CFG)
        self.assertIn("M16HUB.QUE.TIME.AVGTOTALTIME1MIN", _names(svg))
        self.assertNotIn("AVGTOTALTIME1MIN", _empty_line(svg))


class 임계를_엉뚱한_값에_긋지_않는다(unittest.TestCase):

    def _cell(self, svg, name):
        return next(c[2] for c in _cells(svg) if c[0] == name)

    def test_원본_대기물량에는_증가량_임계를_안_긋는다(self):
        """R-B 임계(30분 +100건)는 증가량에 거는 값이다 — 물량 500건에 그으면 5배가 된다."""
        rows = _rows("M16HUB", "발동: M16HUB[R-B(30분+120건)]",
                     M16HUB_rb_diff30=lambda i: 80 + i,
                     **{"M16HUB.QUE.M14TOM16.MESCURRENTQCNT": lambda i: 480 + i})
        svg = G.render(rows, CENTER, 60, cfg=CFG)
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
        end = BASE + dt.timedelta(minutes=59)
        svg = G.render(rows, end, 60, cfg=CFG)
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


class 기여도도_같은_목록이다(unittest.TestCase):
    """고객: "기여도 추정에는 실제지표 기여도를 추정을 보여주고" · "따로"."""

    @classmethod
    def setUpClass(cls):
        # 300분 — 앞 284분 정상, 200~215분 사건 (test_contrib 와 같은 모양)
        rows = []
        for i in range(300):
            ev = 200 <= i < 216
            rows.append({
                "datetime": (dt.datetime(2026, 10, 6, 0, 0) + dt.timedelta(minutes=i)
                             ).strftime("%Y-%m-%d %H:%M:%S"),
                "unified_risk_score": str(80 if ev else 15 + i % 10),
                "hot_area": "M16HUB", "all_score": "50",
                "reason": ("발동: M16HUB[R-A'(AVGTOTALTIME1MIN=12분/기준9.0),R-B(30분+130건),"
                           "SLA(7%4분초과)]" if ev else ""),
                "M16HUB_ra": str(12 if ev else 5 + (i % 7) * 0.1),
                "M16HUB_rb_diff30": str(130 if ev else (i % 11) - 5),
                "M16HUB_rb_diff10": str(40 if ev else (i % 7) - 3),
                "sla_M16HUB": str(7 if ev else 2 + (i % 5) * 0.1),
                # 누적 — 하루 내내 커진다. 사건 중엔 10분에 60건 (평소 10분에 10건)
                "M16HUB_sla_cnt": str(i + (5 * (i - 199) if ev else (80 if i >= 216 else 0))),
                "M16HUB.QUE.M14TOM16.MESCURRENTQCNT": str(300 + (i % 9)),
            })
        cls.rows = rows
        cls.at = dt.datetime(2026, 10, 6, 0, 0) + dt.timedelta(minutes=207)
        cls.d = C.explain(rows, cls.at, CFG)
        cls.svg = G.render(rows, cls.at, 60, cfg=CFG)

    def test_두_묶음을_따로_100퍼센트(self):
        d = self.d
        self.assertTrue(d["ok"], d)
        for k in ("real", "new"):
            self.assertTrue(d[k], f"{k} 묶음이 비었다")
            self.assertAlmostEqual(sum(i["pct"] for i in d[k]), 100, delta=3)
        self.assertAlmostEqual(sum(i["pct"] for i in d["items"]), 100, delta=3,
                               msg="items 는 예전처럼 합쳐 100% (ml_why 가 읽는다)")

    def test_그래프에_있는_지표만_따진다(self):
        shown = set(_names(self.svg))
        for i in self.d["real"] + self.d["new"]:
            self.assertIn(i["name"], shown, f"그래프에 없는 {i['name']} 를 기여도가 따졌다")

    def test_신규_지표는_신규_묶음에(self):
        self.assertIn("M16HUB_rb_diff30", [i["name"] for i in self.d["new"]])
        self.assertNotIn("M16HUB_rb_diff30", [i["name"] for i in self.d["real"]])
        self.assertIn("M16HUB.QUE.TIME.AVGTOTALTIME1MIN", [i["name"] for i in self.d["real"]])

    def test_원본_대기물량을_발동_상시로_몰지_않는다(self):
        """★룰이 본 것은 증가량이다. 물량이 평소와 같은데 '발동 · 상시 · 하루 내내'
        로 뜨면 "물량이 하루 내내 높았다" 는 없는 말이 된다."""
        q = [i for i in self.d["real"] if i["name"] == "M16HUB.QUE.M14TOM16.MESCURRENTQCNT"]
        for i in q:
            self.assertFalse(i["fired"])
            self.assertFalse(i["chronic"])

    def test_누적_건수는_10분_증가로_잰다(self):
        """하루 내내 커지는 값을 그대로 '평소' 와 견주면 저녁마다 높게 나온다."""
        it = next(i for i in self.d["items"] if i["name"] == "M16HUB.QUE.ALL.TRANSPORT4MINOVERCNT")
        self.assertIn("10분 증가", it["label"])
        self.assertLess(it["value"], 100, "누적값(200 넘음)이 아니라 10분 증가여야 한다")

    def test_HTML_두_묶음_윗줄이_컬럼(self):
        h = C.explain_html(self.rows, self.at, CFG)
        self.assertIn("실제지표 기여도 추정", h)
        self.assertIn("신규 지표 기여도 추정", h)
        self.assertLess(h.index("실제지표 기여도 추정"), h.index("신규 지표 기여도 추정"))
        i = h.index("M16HUB.QUE.TIME.AVGTOTALTIME1MIN")
        self.assertLess(i, h.index("M16HUB 반송시간", i), "컬럼 이름이 한글 이름보다 먼저")
        self.assertIn("추정", h)
        self.assertIn("점수식을 푼 값이 아닙니다", h)

    def test_실제지표가_없는_구간은_그렇게_말한다(self):
        """ALL 화면에서 앞뒤 30분 동안 룰이 하나도 안 떴으면 따질 실제지표가 없다 —
        지어내지 않고 그렇게 말한다. (FAB 화면은 룰 컬럼을 늘 세우므로 해당 없음)"""
        rows = [dict(r, all_score="", reason="") for r in self.rows]
        at = dt.datetime(2026, 10, 6, 0, 0) + dt.timedelta(minutes=60)
        d = C.explain(rows, at, CFG)
        self.assertTrue(d["ok"])
        self.assertEqual(d["items"], [])
        self.assertIn("실제지표가 없습니다", d["note"])
        self.assertIn("실제지표가 없습니다", C.explain_html(rows, at, CFG))

    def test_0_은_상시로_몰지_않는다(self):
        """PIO 는 10분 창으로 발동이 적히는데 그 분 실패 개수는 0 일 수 있다 —
        '0개 · 평소 0개 · 하루 내내' 로 기여도를 반씩 먹으면 안 된다."""
        rows = []
        for k, r in enumerate(self.rows):
            rows.append(dict(r, **{
                # 창 안 몇 분에만 실패 1개 — 고른 분(207)은 0
                "M16HUB->M14A_PIOERROR_DEPOSITED": "1" if k in (185, 190, 230) else "0",
                "reason": (r["reason"] + "; PIO(M16HUB->M14A=4개/10분,합9)")
                if r["reason"] else ""}))
        d = C.explain(rows, self.at, CFG)
        pio = [i for i in d["items"] if "PIOERROR" in i["name"]]
        self.assertEqual(pio, [], "0개 · 평소 0개 를 발동·상시로 올렸다")
        for i in d["items"]:
            self.assertFalse(i["chronic"] and i["value"] == 0, i)

    def test_ml_why_가_읽는_모양(self):
        for i in self.d["items"]:
            for k in ("label", "value", "raw", "unit", "pct", "base", "dir", "fired"):
                self.assertIn(k, i)
            self.assertIsInstance(i["value"], (int, float))


if __name__ == "__main__":
    unittest.main()
