# -*- coding: utf-8 -*-
"""더블클릭 구간 그래프 — 2026-09 전면 개편.

고객 지적: "데이터는 맞는데 그래프 보는 게 마음에 안 든다." 실제 자료로
렌더해 재 보니 취향이 아니라 구조였다.

  · 세로 1054px 인데 모달은 92vh(~900px) — 늘 스크롤. 지표 여덟이면 1310px.
  · 패널마다 **자기 min~max 로 정규화**해서, 임계의 0.9배(정상)인 지표가
    2.5배(심각)인 지표와 똑같이 꽉 차 보인다. 심각도가 통째로 왜곡된다.
  · 지표 패널에 **임계선이 없다** — 넘었는지를 눈으로 못 본다.
  · 면적을 전부 빨강/주황으로 채워 정상 지표도 위험해 보인다.

그래서 색은 '넘었다' 는 뜻으로만 쓰고, 안 넘은 것은 회색으로 죽이고, 배수
큰 순으로 깐다. 이 시험이 지키는 것은 **그 규칙** 이지 그림의 픽셀이 아니다.
"""
import datetime as dt
import os
import re
import sys
import unittest

from . import util  # noqa: F401
import graphs
from lp_client import load_config


def _rows(n=40, **cols):
    base = dt.datetime(2026, 9, 12, 15, 0)
    out = []
    for i in range(n):
        r = {"datetime": (base + dt.timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M"),
             "unified_risk_score": "40", "hot_area": "M16HUB",
             "reason": "발동: M16HUB[R-A'(AVGTOTALTIME1MIN=22.5분/기준9.0),"
                       "R-D(FAB저장=14.2%)]; M14[R-A_sus]"}
        for k, v in cols.items():
            r[k] = "" if v is None else str(v(i) if callable(v) else v)
        out.append(r)
    return base, out


def _cells(svg):
    """칸 단위로 자른다 — {이름표: 그 칸의 마크업}.

    ★두 번 틀렸다. 처음엔 svg.split("M14 …")[1] 로 잘랐더니 **뒤 칸까지**
      딸려 와 그쪽 색을 보고 통과했다. 다음엔 이름표부터 잘랐더니 이름표
      **앞**에 그리는 배지가 빠졌다. 칸 테두리(rx="10")부터 다음 테두리까지
      끊는다 — 그게 칸의 진짜 경계다.
    """
    marks = [m.start() for m in re.finditer(r'<rect x="[\d.]+" y="[\d.]+" '
                                            r'width="[\d.]+" height="[\d.]+" rx="10"', svg)]
    out = {}
    for k, pos in enumerate(marks):
        end = marks[k + 1] if k + 1 < len(marks) else len(svg)
        chunk = svg[pos:end]
        nm = re.search(r'font-size="11\.5" font-weight="700"[^>]*>([^<]*)', chunk)
        if nm:
            out[nm.group(1)] = chunk
    return out


def _data_colors(cell):
    """그 칸에서 **자료를 그린** 색만 — 값 글자·추이 선·막대.

    ★임계선은 어느 칸에나 빨갛게 긋는다(한계가 어디인지 보여야 하니까).
      그걸 같이 세면 '안 넘었는데 칠했다' 로 잘못 읽는다.
    """
    got = set()
    m = re.search(r'font-size="14" font-weight="800" fill="(#[0-9A-Fa-f]{6})"', cell)
    if m:
        got.add(m.group(1))
    got |= set(re.findall(r'stroke="(#[0-9A-Fa-f]{6})" stroke-width="2"', cell))
    got |= set(re.findall(r'rx="1\.2" fill="(#[0-9A-Fa-f]{6})"', cell))
    return got


class 임계를_넘은_것만_칠한다(unittest.TestCase):
    """★이게 이번 개편의 뿌리다. 색이 '넘었다' 는 뜻이 아니면 현장에서
    그래프를 봐도 어디를 봐야 할지 알 수 없다."""

    def setUp(self):
        self.cfg = load_config()
        # M16HUB 반송시간 임계 9.0 → 22.5 는 2.5배 (넘음)
        # M14 적재시간   임계 3.3 → 2.0 은 0.6배 (안 넘음)
        base, rows = _rows(M16HUB_ra=22.5, M14_ra=2.0, M16HUB_rd_fab=14.2)
        self.cells = _cells(graphs.render(rows, base + dt.timedelta(minutes=20),
                                          40, cfg=self.cfg))

    def test_안_넘은_지표는_회색이다(self):
        got = _data_colors(self.cells["M14 반송시간"])
        for c in (graphs._DARK["crit"], graphs._DARK["evt"]):
            self.assertNotIn(c, got, "0.6배인데 칠했다 — 색이 뜻을 잃는다")
        self.assertIn(graphs._DARK["tx3"], got, "회색으로 그려야 한다")

    def test_넘은_지표는_칠한다(self):
        got = _data_colors(self.cells["M16HUB 반송시간"])
        self.assertTrue(graphs._DARK["crit"] in got or graphs._DARK["evt"] in got,
                        "2.5배인데 색이 없다: %r" % got)

    def test_임계선은_어느_칸에나_긋는다(self):
        """한계가 어디인지는 안 넘은 칸에서도 보여야 한다."""
        for nm in ("M16HUB 반송시간", "M14 반송시간"):
            self.assertIn('stroke="%s" stroke-width="1" opacity=".55"'
                          % graphs._DARK["crit"], self.cells[nm], nm)

    def test_배수_배지를_붙인다(self):
        self.assertRegex(self.cells["M16HUB 반송시간"], r"▲[\d.]+배")
        self.assertNotIn("▲", self.cells["M14 반송시간"],
                         "안 넘었는데 ▲ 를 붙이면 넘은 걸로 읽는다")


class 배수_큰_순으로_깐다(unittest.TestCase):
    """왼쪽 위가 늘 제일 심한 것 — 눈을 굴릴 필요가 없어야 한다."""

    def setUp(self):
        self.cfg = load_config()

    def test_reason_순서가_아니라_배수_순이다(self):
        """★reason 에 **나중에** 나온 지표가 제일 심한 경우로 잡는다.
        앞쪽 것이 제일 심하면 정렬을 빼도 순서가 같아 시험이 안 문다."""
        base, rows = _rows()
        for r in rows:
            # reason 순서: M16HUB 반송 → M16HUB FAB저장 → M14 적재
            # 배수 순서 : M14(3배) → M16HUB 반송(1.1배) → FAB저장(0.55배)
            r["M16HUB_ra"] = "10.0"      # 임계 9.0  → 1.1배
            r["M16HUB_rd_fab"] = "14.2"  # 임계 25.75 → 0.55배
            r["M14_ra"] = "9.9"          # 임계 3.3  → 3.0배
        svg = graphs.render(rows, base + dt.timedelta(minutes=20), 40, cfg=self.cfg)
        names = list(_cells(svg))
        self.assertEqual(names[0], "M14 반송시간",
                         "제일 심한 것이 맨 앞이어야 한다: %r" % names)
        self.assertLess(names.index("M16HUB 반송시간"),
                        names.index("M16HUB FAB저장율"), "%r" % names)


class 칸마다_임계를_적는다(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config()

    def test_임계값을_글자로_적는다(self):
        base, rows = _rows(M16HUB_ra=22.5, M16HUB_rd_fab=14.2)
        svg = graphs.render(rows, base + dt.timedelta(minutes=20), 40, cfg=self.cfg)
        self.assertIn("임계", svg, "임계가 얼마인지 없으면 배수를 못 믿는다")

    def test_실제_AMOS_컬럼명을_적는다(self):
        """현장에서 이걸 보고 원 지표를 찾아간다."""
        base, rows = _rows(M16HUB_ra=22.5, M16HUB_rd_fab=14.2)
        svg = graphs.render(rows, base + dt.timedelta(minutes=20), 40, cfg=self.cfg)
        self.assertIn("AVGTOTALTIME1MIN", svg)

    def _line_y(self, cell):
        """그 칸 추이선의 y — 작을수록 위(=값이 큼)."""
        m = re.search(r'd="M[\d.]+,([\d.]+)', cell)
        return float(m.group(1))

    def test_칸끼리_같은_자로_잰다(self):
        """★이게 옛 그래프의 가장 큰 문제였다. 칸마다 자기 min~max 로 재면
        임계의 0.6배(정상)인 값이 2.5배(심각)인 값과 똑같이 꽉 차 보인다.
        임계를 기준으로 재야 두 칸을 나란히 놓고 읽을 수 있다."""
        base, rows = _rows(M16HUB_ra=22.5, M14_ra=2.0, M16HUB_rd_fab=14.2)
        cells = _cells(graphs.render(rows, base + dt.timedelta(minutes=20),
                                     40, cfg=self.cfg))
        hi = self._line_y(cells["M16HUB 반송시간"])   # 2.5배 → 위쪽
        lo = self._line_y(cells["M14 반송시간"])      # 0.6배 → 아래쪽
        self.assertLess(hi, lo,
                        "2.5배가 0.6배보다 위에 있어야 한다 (자기 min~max 로 "
                        "재면 둘 다 같은 높이가 된다)")

    def _band(self, cell):
        """(그림 위, 바닥, 임계선) y — 바닥선과 임계선을 자료에서 읽는다."""
        by = float(re.search(r'y1="([\d.]+)"[^>]*stroke="%s" stroke-width="1"/>'
                             % graphs._DARK["line"], cell).group(1))
        ty = float(re.search(r'y1="([\d.]+)"[^>]*stroke="%s" stroke-width="1" '
                             r'opacity="\.55"' % graphs._DARK["crit"], cell).group(1))
        return by - (graphs.CELL_H - 66 - 12), by, ty

    def test_임계_2배_안이면_임계선이_가운데다(self):
        """0~임계×2 로 재니 임계는 가운데 — 눈이 기준선을 찾을 필요가 없다."""
        base, rows = _rows(M16HUB_ra=22.5, M14_ra=2.0, M16HUB_rd_fab=14.2)
        cells = _cells(graphs.render(rows, base + dt.timedelta(minutes=20),
                                     40, cfg=self.cfg))
        top, by, ty = self._band(cells["M14 반송시간"])   # 2.0 < 임계 3.3 의 2배
        self.assertAlmostEqual(ty, top + (by - top) / 2, delta=3)

    def test_임계_2배를_넘으면_눈금이_늘어난다(self):
        """★값이 임계의 2.5배인데 눈금을 2배에 고정하면 선이 칸 밖으로 잘린다.
        늘어나야 맞고, 그만큼 임계선은 가운데보다 아래로 내려간다."""
        base, rows = _rows(M16HUB_ra=22.5, M14_ra=2.0, M16HUB_rd_fab=14.2)
        cells = _cells(graphs.render(rows, base + dt.timedelta(minutes=20),
                                     40, cfg=self.cfg))
        c = cells["M16HUB 반송시간"]
        top, by, ty = self._band(c)
        self.assertGreater(ty, top + (by - top) / 2,
                           "값이 2배를 넘으면 임계선이 가운데 아래로 와야 한다")
        ly = float(re.search(r'd="M[\d.]+,([\d.]+)', c).group(1))
        self.assertGreaterEqual(ly, top - 0.5, "선이 칸 위로 삐져나갔다")
        self.assertLessEqual(ly, by, "선이 바닥 아래로 내려갔다")



class 원문을_뿌리지_않는다(unittest.TestCase):
    """★호버 말풍선이 CSV 의 reason 을 통째로 뿌리고 있었다.

    "hot_area=M16HUB; S3확정; 발동: M16HUB[R-A'(AVGTOTALTIME1MIN=22.5분/…)]"
    같은 기계 글자다. 읽을 것이 아니라 덮는 것이 된다. 화면 목록이 쓰는
    summarize_reason 과 같은 한글 요약을 쓴다.
    """

    def setUp(self):
        self.cfg = load_config()
        base, rows = _rows(M16HUB_ra=22.5, M16HUB_rd_fab=14.2)
        for r in rows:
            r["reason"] = ("hot_area=M16HUB; S3확정; 발동: "
                           "M16HUB[R-A'(AVGTOTALTIME1MIN=22.5분/기준9.0),"
                           "R-D(FAB저장=14.2%)]; M14[R-A_sus]")
        self.svg = graphs.render(rows, base + dt.timedelta(minutes=20),
                                 40, cfg=self.cfg)

    def test_룰_코드가_안_보인다(self):
        for bad in ("R-A'", "R-A_sus", "R-D(", "hot_area=", "S3확정"):
            self.assertNotIn(bad, self.svg, "원문이 새어 나왔다: %s" % bad)

    def test_한글_요약은_들어간다(self):
        """빼기만 하고 대신 아무것도 안 주면 말풍선이 쓸모없어진다."""
        self.assertIn("반송지연", self.svg)
        self.assertIn("Storage FULL", self.svg)


class 한_화면에_들어간다(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config()

    def test_모달_높이_안에_들어간다(self):
        """모달은 max-height 92vh — 1080p 에서 약 900px 이다."""
        base, rows = _rows(M16HUB_ra=22.5, M14_ra=2.0, M16HUB_rd_fab=14.2,
                           M16A_ra=2.0, M16B_ra=2.0, M14B_ra=2.0)
        svg = graphs.render(rows, base + dt.timedelta(minutes=20), 40, cfg=self.cfg)
        h = float(re.search(r'viewBox="0 0 [\d.]+ ([\d.]+)"', svg).group(1))
        self.assertLess(h, 900, "지표가 여럿이어도 한 화면에 들어가야 한다")


class 클릭할_수_있게_시각을_실어_보낸다(unittest.TestCase):
    """★말풍선(<title>)만으로는 관제에서 약하다 — 1초 늦게 뜨고, 손 떼면
    사라지고, 여러 명이 같이 못 본다. 눌러서 표로 남길 수 있어야 한다."""

    def setUp(self):
        self.cfg = load_config()
        self.base, self.rows = _rows(M16HUB_ra=22.5, M16HUB_rd_fab=14.2)
        self.svg = graphs.render(self.rows, self.base + dt.timedelta(minutes=20),
                                 40, cfg=self.cfg)

    def test_분마다_히트_영역이_있다(self):
        self.assertEqual(self.svg.count('class="ghit"'), 40)

    def test_히트_영역에_시각이_실려_있다(self):
        self.assertIn('data-at="2026-09-12T15:20:00"', self.svg)

    def test_말풍선도_그대로_있다(self):
        """클릭을 넣었다고 호버를 없애면 안 된다 — 훑어볼 때는 그쪽이 빠르다."""
        self.assertIn("<title>", self.svg)
        self.assertIn("15:20", self.svg)

    def test_화면이_클릭을_받는다(self):
        html = open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "static", "dashboard.html"),
            encoding="utf-8").read()
        self.assertIn("bindGraphPin", html)
        self.assertIn("el.dataset.at", html, "실어 보낸 시각을 받아 써야 한다")
        self.assertIn("#gpin", html, "고정한 내용을 놓을 자리가 있어야 한다")


if __name__ == "__main__":
    unittest.main()
