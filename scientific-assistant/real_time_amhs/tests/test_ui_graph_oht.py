# -*- coding: utf-8 -*-
"""UI대쉬보드 그래프 서랍 → 그 1분 OHT 재생 (월드모델).

고객: "UI대쉬보드 위 그래프에 똑같이 월드모델 들어갈 수 있게 해주라" ·
      "골라서 OHT 들어갈 수 있게 해주면 좋을 것 같은데".

관제 구간 그래프의 '그 1분 OHT 재생' 줄과 같은 것 — 같은 /api/world 를 부르고,
같은 팝업 창으로 연다. 그래프에서 한 분을 누르면 그 분으로 바뀐다.
"""
import io
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
MON = "OHT_Bridge_Monitor.html"


def _read(*p):
    with io.open(os.path.join(APP, *p), encoding="utf-8", newline="") as fh:
        return fh.read()


class 관제와_같은_길로_연다(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.h = _read("static", MON)
        cls.d = _read("static", "dashboard.html")

    def test_같은_API_로_주소를_받는다(self):
        """★주소는 관제(world_link)가 만든다 — 여기서 테이블 이름을 다시 적지 않는다."""
        self.assertIn("fetch(location.origin + '/api/world?at=' + encodeURIComponent(at) +", self.h)
        self.assertNotIn("oht_data_m16br", self.h, "테이블 이름을 화면에 박았다")

    def test_같은_팝업_창이다(self):
        """★창 이름·크기가 관제와 같아야 여러 번 눌러도 창 하나로 모인다."""
        m = re.search(r"window\.open\(b\.dataset\.oht, '(\w+)',\s*'([^']+)'\)", self.d)
        self.assertTrue(m, "관제 쪽 팝업 여는 줄을 못 찾았다")
        self.assertIn("window.open(url, '%s', '%s')" % (m.group(1), m.group(2)), self.h)

    def test_팝업이_막히면_말한다(self):
        self.assertIn("alert('팝업이 막혀 있습니다. 이 주소의 팝업을 허용해 주세요.')", self.h)

    def test_월드모델이_꺼져_있으면_잠그고_할_일을_적는다(self):
        self.assertIn("(up ? '' : ' disabled')", self.h)
        self.assertIn("월드모델이 안 떠 있습니다</span> — ' + esc((d.server || {}).how || '')", self.h)

    def test_꺼_둔_설정이면_줄을_숨긴다(self):
        self.assertIn("if (!d || !d.enabled) { row.style.display = 'none'; return; }", self.h)

    def test_FAB_다섯_다_서랍_FAB_은_눈에_띄게(self):
        self.assertIn("(x.fab === GRAPH_FAB ? ' class=\"on\"' : '')", self.h)

    def test_어느_건인지_실어_보낸다(self):
        """★팝업이 증거 자료로 쓰인다 — 서랍 FAB · 그 분 · 점수를 case 로 남긴다."""
        self.assertIn("'&label=' + encodeURIComponent(ohtLabel(box))", self.h)
        self.assertIn("var s = 'UI대쉬보드 · ' + GRAPH_FAB + ' · '", self.h)


class 골라서_들어간다(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.h = _read("static", MON)

    def test_그래프에서_누른_분으로(self):
        self.assertIn("ohtPick(was ? null : hv, box);", self.h)
        self.assertIn("var g = hv && $('.ghit', hv), at = g && g.getAttribute('data-at');", self.h)

    def test_안_골랐으면_지금_자료_시각(self):
        self.assertIn("function ohtAt() { return GRAPH_PICK || String(LIVE_AT || '').replace(' ', 'T'); }", self.h)

    def test_30초마다_다시_그려도_고른_분은_남는다(self):
        self.assertIn("ohtRepin(body);", self.h)
        self.assertIn("var g = same[GRAPH_PICK_N] || same[0];", self.h)

    def test_지금으로_되돌린다(self):
        self.assertIn("<button data-oht-now", self.h)
        self.assertIn("e.target.closest('[data-oht-now]')", self.h)

    def test_새로_열면_처음부터(self):
        i = self.h.index("function graphOpen(fab) {")
        self.assertIn("GRAPH_PICK = null; OHT_WIN = null;", self.h[i:i + 300])

    def test_그새_다른_분을_골랐으면_늦은_답은_버린다(self):
        self.assertIn("if (now && ohtAt() === at) ohtPaint(now, d, at);", self.h)


class 화이트에서도_눌린_단추가_보인다(unittest.TestCase):
    """★화이트의 '.bm-ghead button{… !important}' 가 .on 을 지워, 어느 구간·어느 FAB 이
       눌렸는지 안 보였다."""

    def test_눌린_단추(self):
        h = _read("static", MON)
        i = h.index("var LIGHT_CSS = [")
        blk = h[i:h.index("].join", i)]
        self.assertIn("'.bm-ghead button.on{", blk)
        self.assertLess(blk.index("'.bm-ghead button{"), blk.index("'.bm-ghead button.on{"),
                        "눌린 단추 규칙이 뒤에 와야 이긴다")


if __name__ == "__main__":
    unittest.main()
