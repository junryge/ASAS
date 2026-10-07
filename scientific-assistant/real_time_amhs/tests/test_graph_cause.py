# -*- coding: utf-8 -*-
"""더블클릭 그래프 — 원인 문장 · 칸 하나 크게 · 원본 값이 없는 실제지표 (2026-10-07).

고객
    "실제지표에 M16HUB.QUE.M14TOM16.MESCURRENTQCNT 이것도 있는데 이거는 왜 그래프에 안 나오냐"
    "원인 내용 좀 적어 주라 — 룰이잖아 · 그래프 클릭하면 원인 내용 적어 주라 ·
     역증가 → 감소 라고 하고, 역증가 같은 거는 없어"
    "그래프 더블클릭하고 … 다시 여기서 그래프 더블클릭하면 1개 크게 확대해서 볼 수 있게"

지키는 것
    ① 표 '실제지표' 칸의 컬럼은 원본 값이 CSV 에 없어도 그래프 칸이 선다 — 그 룰이 본 값
       (R-B 면 30분 증가)으로 그리고 '원본 값 없음' 이라고 적는다. 원본이 있으면 원본.
    ② 원인 = 룰마다 한 줄, 값과 기준. 룰 코드 · 영문 원문 · '역증가' 는 안 나온다.
    ③ 칸에 이름표(data-m)가 있고, 그 이름으로 그 칸 하나를 크게(눈금 · 시간축) 그린다.
"""
import datetime as dt
import os
import re
import unittest

from . import util  # noqa: F401

import graphs as G  # noqa: E402
import sentinel as S  # noqa: E402
from lp_client import load_config  # noqa: E402

from .test_real_new import CENTER, HUB_REASON, _cells, _empty_line, _rows  # noqa: E402

CFG = load_config()
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MES = "M16HUB.QUE.M14TOM16.MESCURRENTQCNT"
BANNED = ("역증가", "R-A", "R-B", "R-C", "R-D", "hot_area=", "S3확정")

# 예측기(hubroom_predictor._build_reason)가 실제로 써 보내는 모양
REAL_REASON = ("hot_area=M16HUB; S3확정; 발동: M16HUB[R-A'(AVGTOTALTIME1MIN=10.40분/기준9.0),R-A_sus,"
               "R-B(MESCURRENTQCNT+120/30분/기준+100),R-B_fast(+45/10분),"
               "R-C'(역증가5개:6ABL6011,6ABL6012,6ABL6021,6ABL0112,6ABL0122),"
               "R-D(FAB저장=26.1%,STB=97.0%),SLA(6.1%4분초과),MAXCAPA1개변경]; "
               "M14[R-A_sus,R-C'(CNV쏠림),R-D(OHT=94.0%)]")
REAL_ROW = {"M16HUB_rc_trend": "-7", "M16HUB_ra_count": "6", "M16HUB_ra": "10.4",
            "M16HUB_rd_fab": "26.1", "M16HUB_stb_util": "97", "M14_cnv_skew": "0.78",
            "maxcapa_signals": "M16HUB:3F_LFT_MAXCAPA=95(<=100)"}


def _jupyter_rows():
    """실제 주피터 발동이벤트 CSV 모양 — 대기 물량 원본(MESCURRENTQCNT) 컬럼이 없다."""
    return _rows("M16HUB", HUB_REASON, M16HUB_ra=lambda i: 8 + i % 4,
                 M16HUB_rd_fab=lambda i: 24 + i % 4,
                 M16HUB_rb_diff30=lambda i: 80 + i, M16HUB_rb_diff10=lambda i: 20 + i % 9)


class 원본_값이_없는_실제지표(unittest.TestCase):

    def setUp(self):
        self.svg = G.render(_jupyter_rows(), CENTER, 60, cfg=CFG)
        self.cells = {c[0]: c for c in _cells(self.svg)}

    def test_칸이_선다(self):
        self.assertIn(MES, self.cells, "표에 있는 실제지표가 그래프에서 빠졌다")
        self.assertNotIn(MES, _empty_line(self.svg))

    def test_룰이_본_값으로_그리고_밝힌다(self):
        _n, lb, c, _y = self.cells[MES]
        self.assertIn("30분 증가", lb)
        self.assertIn("원본 값 없음 · 임계 100건", c)
        self.assertRegex(c, r'class="gtag"[^>]*>09:45 · 125건<')       # rb_diff30 = 80 + 45

    def test_원본이_있으면_원본(self):
        rows = _jupyter_rows()
        for i, r in enumerate(rows):
            r[MES] = str(480 + i)
        c = {x[0]: x for x in _cells(G.render(rows, CENTER, 60, cfg=CFG))}[MES][2]
        self.assertNotIn("원본 값 없음", c)
        self.assertRegex(c, r'class="gtag"[^>]*>09:45 · 525건<')
        self.assertNotIn("임계", c, "대기 물량에 증가량 임계를 긋지 않는다")


class 원인(unittest.TestCase):
    """고객: "원인 내용 좀 적어 주라 — 룰이잖아"."""

    def setUp(self):
        self.cs = S.rule_causes(REAL_REASON, "M16HUB", REAL_ROW)
        self.by = {c["rule"]: c["text"] for c in self.cs}

    def test_룰마다_한_줄(self):
        for rule in ("반송지연", "반송지연 지속", "Queue 누적", "Queue 상승", "리프터 정체",
                     "Storage FULL", "4분초과", "운영자 용량변경"):
            self.assertIn(rule, self.by, rule)

    def test_값과_기준(self):
        self.assertEqual(self.by["반송지연"], "M16HUB 반송시간 10.4분 — 기준 9분 넘음")
        self.assertEqual(self.by["Queue 누적"], "M16HUB M14→M16 대기 30분 동안 +120건 — 기준 +100건 넘음")
        self.assertIn("10분 동안 +45건", self.by["Queue 상승"])
        self.assertIn("FAB 적재율 26.1% — 기준 25.75% 넘음", self.by["Storage FULL"])
        self.assertIn("4분 넘게 걸린 반송 6.1% — 기준 5% 넘음", self.by["4분초과"])
        self.assertIn("3F 리프터 상한 95", self.by["운영자 용량변경"])

    def test_리프터는_감소로(self):
        t = self.by["리프터 정체"]
        self.assertIn("20분 전보다 7대 감소", t)
        self.assertIn("지목 5대 (6ABL6011, 6ABL6012, 6ABL6021, 6ABL0112, 6ABL0122)", t)

    def test_룰_코드도_역증가도_없다(self):
        for c in self.cs:
            for bad in BANNED:
                self.assertNotIn(bad, c["text"], (bad, c["text"]))
                self.assertNotIn(bad, c["rule"])

    def test_FAB_화면은_그_FAB_것만(self):
        self.assertEqual({c["area"] for c in self.cs}, {"M16HUB"})
        m14 = S.rule_causes(REAL_REASON, "M14", REAL_ROW)
        self.assertEqual({c["area"] for c in m14}, {"M14"})
        self.assertIn("M14 컨베이어 북/남 한쪽 쏠림 78% — 기준 70% 넘음",
                      [c["text"] for c in m14])

    def test_ALL_은_주_영역_블록(self):
        got = S.rule_causes(REAL_REASON, "", REAL_ROW, area="M14")
        self.assertEqual({c["area"] for c in got}, {"M14"})
        both = S.rule_causes(REAL_REASON, "", REAL_ROW, area="")
        self.assertEqual({c["area"] for c in both}, {"M16HUB", "M14"})

    def test_예전_모양도_읽는다(self):
        """시험 · 옛 파일의 'R-B(30분+120건)' 모양."""
        got = {c["rule"]: c["text"] for c in S.rule_causes(
            "발동: M16HUB[R-B(30분+120건)]", "M16HUB", {})}
        self.assertEqual(got["Queue 누적"], "M16HUB M14→M16 대기 30분 동안 +120건 — 기준 +100건 넘음")

    def test_룰이_없으면_빈_목록(self):
        self.assertEqual(S.rule_causes("", "M16HUB", {}), [])


class 원인_강조(unittest.TestCase):
    """고객: "원인 쪽 글자 조금 더 크게 굵게 하고 강조 임팩트 부분은 빨간색 굵게"."""

    def setUp(self):
        self.cs = S.rule_causes(REAL_REASON, "M16HUB", REAL_ROW)
        self.by = {c["rule"]: c for c in self.cs}

    def test_빨갛게_할_값(self):
        want = {"반송지연": ["10.4분"], "Queue 누적": ["+120건"], "Queue 상승": ["+45건"],
                "리프터 정체": ["7대 감소", "지목 5대"], "Storage FULL": ["26.1%"],
                "4분초과": ["6.1%"], "운영자 용량변경": ["95"]}
        for rule, hot in want.items():
            self.assertEqual(self.by[rule]["hot"], hot, rule)

    def test_기준은_빨갛지_않다(self):
        for c in self.cs:
            for h in c["hot"]:
                self.assertNotIn("기준", h, (c["rule"], h))

    def test_글자는_깨끗하고_끊은_조각을_이으면_글자(self):
        for c in self.cs + S.rule_causes(REAL_REASON, "M14", REAL_ROW):
            self.assertNotRegex(c["text"], "[⟦⟧]")
            self.assertEqual("".join(c["parts"]), c["text"])
            self.assertEqual(c["parts"][1::2], c["hot"])

    def test_짧은_값도_제자리만(self):
        """화면이 글자를 다시 찾으면 'M16HUB' 안의 '16' 이 칠해진다 — 서버가 끊어 준다."""
        c = S.rule_causes("발동: M16HUB[MAXCAPA1개변경]", "M16HUB",
                          {"maxcapa_signals": "M16HUB:3F_LFT_MAXCAPA=16(<=100)"})[0]
        self.assertEqual(c["hot"], ["16"])
        self.assertTrue(c["parts"][0].startswith("M16HUB "), c["parts"])


class 칸_하나_크게(unittest.TestCase):
    """고객: "그래프 더블클릭하면 1개 크게 확대해서 볼 수 있게"."""

    def setUp(self):
        self.rows = _jupyter_rows()

    def test_칸마다_이름표(self):
        svg = G.render(self.rows, CENTER, 60, cfg=CFG)
        names = re.findall(r'rx="10" data-m="([^"]+)"', svg)
        self.assertEqual(names, [c[0] for c in _cells(svg)])

    def test_그_칸만_크게(self):
        one = G.render_one(self.rows, CENTER, "M16HUB.QUE.TIME.AVGTOTALTIME1MIN", 60, cfg=CFG)
        self.assertEqual(re.findall(r'class="mname"[^>]*>([^<]+)', one),
                         ["M16HUB.QUE.TIME.AVGTOTALTIME1MIN"])
        w = float(re.search(r'<rect x="[\d.]+" y="[\d.]+" width="([\d.]+)" height="([\d.]+)" rx="10"',
                            one).group(1))
        self.assertGreater(w, 900, "가로 전체 폭")
        self.assertIn(">09:15<", one, "시간축")
        self.assertIn(">09:30<", one)
        self.assertIn('<line class="gsel"', one, "더블클릭한 분 표시")
        self.assertRegex(one, r'text-anchor="end" fill="#\w+" font-family="Consolas,monospace">18<',
                         "왼쪽 눈금 (임계 9 의 두 배)")

    def test_작은_칸과_같은_값(self):
        small = {c[0]: c for c in _cells(G.render(self.rows, CENTER, 60, cfg=CFG))}[MES][2]
        one = G.render_one(self.rows, CENTER, MES, 60, cfg=CFG)
        for need in ("원본 값 없음 · 임계 100건", "09:45 · 125건"):
            self.assertIn(need, small)
            self.assertIn(need, one)

    def test_신규_지표도(self):
        one = G.render_one(self.rows, CENTER, "M16HUB_rb_diff30", 60, cfg=CFG)
        self.assertIn("신규 지표", one)
        self.assertIn("M16HUB_rb_diff30", one)

    def test_없는_칸이면_말한다(self):
        self.assertIn("찾지 못했습니다", G.render_one(self.rows, CENTER, "NOPE", 60, cfg=CFG))


class 화면과_서버가_잇는다(unittest.TestCase):
    """flask 없이도 볼 수 있는 것 — 길과 화면 코드."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(_BASE, "server.py"), encoding="utf-8") as f:
            cls.srv = f.read()
        with open(os.path.join(_BASE, "static", "dashboard.html"), encoding="utf-8") as f:
            cls.html = f.read()

    def test_길이_있다(self):
        self.assertIn('@app.route("/api/cause")', self.srv)
        self.assertIn('@app.route("/api/graph1")', self.srv)
        self.assertIn("rule_causes(", self.srv)

    def test_화면이_부른다(self):
        for need in ("/api/cause?at=", "/api/graph1?at=", "rect[data-m]", "← 전체 그래프",
                     "pinAt(GAT)", 'id="gcause"'):
            self.assertIn(need, self.html)

    def test_원인이_맨_위_발동_룰은_맨_아래(self):
        """고객: "발동 룰을 제일 아래로 · 원인 쪽 글자 조금 더 크게 굵게 · 강조 부분은 빨간색 굵게"."""
        body = self.html[self.html.index("function pinAt(at){"):]
        body = body[:body.index("\n}\n")]
        rows = re.findall(r"<tr><td[^>]*>([^<]+)</td>", body)
        self.assertEqual(rows, ["원인", "실제지표", "FAB 점수", "발동 룰"])
        self.assertRegex(body, r'<td[^>]*font-weight:700[^>]*>원인</td>')
        self.assertIn("font-size:14px;font-weight:700", body)
        self.assertIn('color:var(--crit);font-weight:800', body)
        self.assertIn("c.parts", body)


if __name__ == "__main__":
    unittest.main()
