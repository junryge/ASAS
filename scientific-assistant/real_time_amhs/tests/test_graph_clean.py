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


class 글자_지표도_제대로_나온다(unittest.TestCase):
    """★"all, fab 다른 지표들도 제대로 나오지?" — 확인해 보니 안 나왔다.

    hot_area · flow_signals · maxcapa_signals 는 **글자** 컬럼인데
    readings() 가 무조건 숫자로 읽어(_num) 'M16HUB' 가 None 이 됐다.
    값이 멀쩡히 있는데 화면에는 늘 '값 없음' 으로 떴다 — 관제가 제일
    먼저 보는 '최고 위험 구역' 이 그것이다.
    """

    ROW = {"hot_area": "M16HUB", "stage": "3", "flow_score": "15",
           "layer1_total": "32", "unified_risk_score": "19",
           "flow_signals": "M16A_2F_TO_HUB=2.0x(위험)"}

    def _all(self):
        import fab_score as F
        return {r["label"]: r for r in F.readings(self.ROW, "ALL")}

    def test_최고_위험_구역이_나온다(self):
        r = self._all()["최고 위험 구역"]
        self.assertEqual(r["value"], "M16HUB")
        self.assertTrue(r["has_value"])
        self.assertTrue(r["is_text"])

    def test_흐름_신호도_나온다(self):
        r = self._all()["흐름 — 어느 노드가 몇 배인가"]
        self.assertEqual(r["value"], "M16A_2F_TO_HUB=2.0x(위험)")
        self.assertTrue(r["has_value"])

    def test_숫자_지표는_그대로_숫자다(self):
        r = self._all()["전체 점수"]
        self.assertEqual(r["value"], 19.0)
        self.assertFalse(r["is_text"])

    def test_빈_글자는_값_없음이다(self):
        import fab_score as F
        got = {r["label"]: r for r in F.readings({"hot_area": "  "}, "ALL")}
        self.assertFalse(got["최고 위험 구역"]["has_value"])

    def test_값_컬럼이_없는_정의_항목은_따로_표시된다(self):
        """★흐름 노드 10개는 CSV 에 값 컬럼이 없다 — 빈 줄 열 개가 되면 안 된다."""
        import fab_score as F
        rs = F.readings(self.ROW, "ALL")
        defs = [r for r in rs if r["no_csv"]]
        self.assertEqual(len(defs), 10)
        self.assertTrue(all(not r["has_value"] for r in defs))
        shown = [r for r in rs if not r["no_csv"]]
        self.assertGreaterEqual(sum(1 for r in shown if r["has_value"]), 5,
                                "값이 뜨는 항목이 너무 적다")

    def test_아바타_그래프는_정의_항목을_안_그린다(self):
        import os
        with open(os.path.join(util.BASE, "avatar_2d", "avatar", "sentinel.py"),
                  encoding="utf-8") as f:
            src = f.read()
        self.assertIn('if not c.get("no_csv")', src,
                      "값 컬럼 없는 항목까지 게이지를 그린다")

    def test_근거는_값_없음과_정의_항목을_구분해_말한다(self):
        import os
        with open(os.path.join(util.BASE, "avatar_2d", "avatar", "sentinel.py"),
                  encoding="utf-8") as f:
            src = f.read()
        self.assertIn("값 컬럼이 없는 항목", src)
        self.assertIn("CSV 에 값 없음", src)


class ALL_값이_화면까지_간다(unittest.TestCase):
    """★ALL 지표는 **임계가 없다**(집계·글자). 그래서 '임계 대비 게이지' 에
    하나도 안 걸려, 흐름 신호·최고 위험 구역이 화면에서 통째로 빠져 있었다.
    값이 있는 것은 요약 줄로라도 나와야 한다."""

    def _all(self):
        import time
        import fab_score as F
        from lp_client import load_config
        from store_csv import read_day
        sys_path = __import__("sys").path
        base = util.BASE + "/avatar_2d"
        if base not in sys_path:
            sys_path.insert(0, base)
        from avatar import sentinel as S
        cfg = load_config()
        rows = read_day("20260728", cfg)
        if not rows:
            self.skipTest("고정 자료 없음")
        out = F.compare(rows, None, cfg, day="20260728")
        S._get = lambda p: (out if "compare" in p else {"ok": True, "rules": []}, "")
        S._cache.update(at=0.0, compare=None, good_at=0.0)
        S._cols_cache.update(at=time.time(), columns={"ok": True, "rules": []})
        return S.chart()["all"]

    def test_요약_지표가_실린다(self):
        a = self._all()
        labels = [n["label"] for n in (a.get("notes") or [])]
        self.assertTrue(labels, "ALL 값이 하나도 안 실린다")
        self.assertTrue(any("흐름" in x for x in labels), labels)

    def test_전체_점수는_두_번_안_적는다(self):
        """막대에 이미 있는 값이다."""
        a = self._all()
        self.assertNotIn("전체 점수", [n["label"] for n in (a.get("notes") or [])])

    def test_값_없는_것은_안_싣는다(self):
        a = self._all()
        for n in (a.get("notes") or []):
            self.assertIsNotNone(n["value"])

    def test_화면이_글자_값을_숫자로_안_바꾼다(self):
        """★gnum() 에 글자를 넣으면 '—' 가 된다 — 흐름 신호가 그렇게 사라졌다."""
        import os
        with open(os.path.join(util.BASE, "avatar_2d", "static", "app.js"),
                  encoding="utf-8") as f:
            js = f.read()
        i = js.index("for(const n of (a.notes||[]))")
        blk = js[i:i + 500]
        self.assertIn("typeof v==='number'", blk, "글자도 gnum 에 넣고 있다")
        self.assertIn("shown.has", blk, "이미 적은 값을 또 적는다")


class 하루_그래프도_빈_계열을_거른다(unittest.TestCase):
    """report_graphs 는 원래 걸러 왔다 — 되돌아가지 않게 못 박는다."""

    def test_값이_없거나_전부_0이면_뺀다(self):
        import report_graphs
        with open(report_graphs.__file__, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("if pts and any(v != 0 for _, v in pts):", src)


if __name__ == "__main__":
    unittest.main()
