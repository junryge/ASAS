# -*- coding: utf-8 -*-
"""배경 검정 ↔ 흰색.

관제실은 어둡지만 사무실·회의실 화면에서는 검은 배경이 안 읽힌다.
[배경] 단추로 고른다 — 그런데 두 가지가 어긋나 있었다.

  · 흰색이 **순백**이라 하루 종일 보면 눈이 아프다
  · 그래프만 늘 검게 나왔다 (서버가 그린 SVG 라 CSS 로 안 바뀐다)
    → 흰 화면 한가운데 검은 상자가 박혀서 거기만 눈이 아프다
"""
import os
import re
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import graphs                                               # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _lum(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4) for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _ratio(a, b):
    l1, l2 = sorted((_lum(a), _lum(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def _rows(n=40):
    base = datetime(2026, 9, 4, 7, 0)
    return base, [{
        "datetime": (base + timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M:%S"),
        "unified_risk_score": 44 + (i % 30), "hot_area": "M16HUB",
        "M16HUB.QUE.TIME.AVGTOTALTIME1MIN": 4.0 + (i % 9) * 0.6,
        "reason": "발동: M16HUB[R-A_sus,R-C]; PIO(M14A<-M14B=4건/10분,합18)",
        "M14A<-M14B_PIOERROR_DEPOSITED": 0, "pio_10min_cnt": 18,
    } for i in range(n)]


class 그래프도_배경을_따라간다(unittest.TestCase):

    def _svg(self, theme):
        base, rows = _rows()
        return graphs.render(rows, base + timedelta(minutes=20), 40, theme=theme)

    def test_흰_배경이면_바탕이_밝다(self):
        svg = self._svg("light")
        bg = re.search(r'<rect width="100%" height="100%" fill="(#[0-9A-Fa-f]{6})"', svg)
        self.assertIsNotNone(bg)
        self.assertGreater(_lum(bg.group(1)), 0.8)

    def test_검은_배경은_그대로다(self):
        """늘 보던 화면이다. 흰색을 넣는다고 검은 쪽이 바뀌면 안 된다."""
        svg = self._svg("dark")
        self.assertIn('fill="#0D1119"', svg)
        self.assertNotIn("#F4F7FB", svg)

    def test_모르는_값은_검은_배경(self):
        """예전 주소로 부르던 곳(?theme= 없음)이 그대로 돌아가야 한다."""
        base, rows = _rows()
        self.assertEqual(graphs.render(rows, base + timedelta(minutes=20), 40),
                         self._svg("dark"))
        self.assertEqual(self._svg("웃긴값"), self._svg("dark"))

    def test_순백을_쓰지_않는다(self):
        """관제실 조명 아래 흰 화면을 하루 종일 보면 눈이 아프다."""
        self.assertNotIn(graphs._LIGHT["bg"].upper(), ("#FFFFFF", "#FFF"))
        self.assertLess(_lum(graphs._LIGHT["bg"]), 0.95)

    def test_흰_배경에서_글자와_선이_읽힌다(self):
        """어두운 배경용 노랑·청록을 그대로 쓰면 흰 바탕에서 사라진다."""
        P = graphs._LIGHT
        bg = P["bg"]
        for key in ("tx", "tx2", "tx3", "score", "evt", "crit"):
            self.assertGreaterEqual(round(_ratio(P[key], bg), 2), 3.9,
                                    f"{key}={P[key]} 가 흰 배경에서 안 읽힌다")
        for c in list(P["palette"]) + list(P["path"]) + list(P["kind"].values()):
            self.assertGreaterEqual(round(_ratio(c, bg), 2), 3.9,
                                    f"{c} 가 흰 배경에서 안 읽힌다")

    def test_두_벌의_칸이_같다(self):
        """한쪽에만 키가 있으면 그 색만 검은 값으로 새어 나온다."""
        self.assertEqual(set(graphs._LIGHT), set(graphs._DARK))
        self.assertEqual(len(graphs._LIGHT["bands"]), len(graphs._DARK["bands"]))
        self.assertEqual(set(graphs._LIGHT["kind"]), set(graphs._DARK["kind"]))


class 화면이_그래프에_배경을_넘긴다(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(_BASE, "static", "dashboard.html"),
                  encoding="utf-8") as f:
            cls.html = f.read()
        with open(os.path.join(_BASE, "server.py"), encoding="utf-8") as f:
            cls.server = f.read()

    def test_요청에_붙여_보낸다(self):
        self.assertIn("&theme=${document.documentElement.getAttribute('data-theme')||'dark'}",
                      self.html)

    def test_서버가_받아_넘긴다(self):
        self.assertIn('request.args.get("theme")', self.server)
        self.assertIn('theme=("light" if theme == "light" else "dark")', self.server)

    def test_배경을_바꾸면_열린_그래프도_다시_그린다(self):
        """SVG 는 서버가 그린 그림이라 CSS 로 안 바뀐다 — 다시 받아야 한다."""
        self.assertIn("window.drawGraph = drawGraph;", self.html)
        blk = self.html.split("window.__setTheme = function(t){")[1].split("};")[0]
        self.assertIn("window.drawGraph()", blk)

    def test_흰_배경이_순백이_아니다(self):
        m = re.search(r'--bg:(#[0-9A-Fa-f]{6}); --panel:(#[0-9A-Fa-f]{6})',
                      self.html.split(':root[data-theme="light"]')[1])
        self.assertIsNotNone(m)
        for c in m.groups():
            self.assertNotEqual(c.upper(), "#FFFFFF")
            self.assertLess(_lum(c), 0.95)


if __name__ == "__main__":
    unittest.main()
