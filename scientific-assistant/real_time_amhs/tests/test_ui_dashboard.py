# -*- coding: utf-8 -*-
"""UI대쉬보드 탭 — FAB별 실시간 상황표를 관제가 직접 내주나.

고객: "OHT_Bridge_Monitor.html 이거를 실시간 관제에 붙여주라. UI 화면을
      보고싶은 사람도 있을거 아니야" · "리포트.피드백 옆에 UI대쉬보드 라고해서".

월드모델파생에서 만든 그 화면을 static/ 에 두고 관제(8989)가 그대로 내준다.
월드모델(10005)을 따로 안 띄워도 관제만 열면 보인다.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
MON = "OHT_Bridge_Monitor.html"


def _read(*p):
    with open(os.path.join(APP, *p), encoding="utf-8") as fh:
        return fh.read()


class 상황표를_관제가_내준다(unittest.TestCase):
    def test_static_에_상황표가_있다(self):
        p = os.path.join(APP, "static", MON)
        self.assertTrue(os.path.isfile(p), f"static/{MON} 이 없다 — 관제가 내줄 게 없다")
        self.assertGreater(os.path.getsize(p), 1_000_000, "한 장짜리 번들이라 MB 단위다")

    def test_손본_화면이_맞다(self):
        """★고객 원본이 아니라 MAP_아이소_얹기.py 로 손본 것이어야 한다.
           원본을 갖다 두면 맵도 수정 모드도 없는 빈 틀이 뜬다."""
        h = _read("static", MON)
        for mark in ('id="bm-config"', "data-bm-plate=", "data-bm-bg=", "data-bm-card="):
            self.assertIn(mark, h, mark + " 가 없다")

    def test_바깥을_안_부른다(self):
        """폐쇄망이다 — 화면이 제 안에 다 들고 있어야 한다 (글꼴은 없으면 없는 대로)."""
        h = _read("static", MON)
        srcs = re.findall(r'<script[^>]+src="([^"]+)"', h)
        self.assertFalse([s for s in srcs if s.startswith(("http://", "https://", "//"))],
                         f"바깥 스크립트를 부른다: {srcs}")


class 대쉬보드에_붙어_있다(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = _read("static", "dashboard.html")

    def test_리포트_피드백_옆이다(self):
        """고객이 자리를 집어 줬다 — 리포트·피드백 **다음**."""
        i = self.h.index('data-tab="report"')
        j = self.h.index('data-tab="ui"')
        self.assertLess(i, j, "UI대쉬보드가 리포트·피드백보다 앞에 있다")
        사이 = self.h[i:j]
        self.assertNotIn("data-tab=", 사이[len('data-tab="report"'):], "둘 사이에 다른 탭이 끼었다")

    def test_이름이_UI대쉬보드다(self):
        self.assertIn('<button data-tab="ui">UI대쉬보드</button>', self.h)

    def test_탭_화면과_틀이_있다(self):
        self.assertIn('id="tab-ui"', self.h)
        self.assertIn('id="uiframe"', self.h)

    def test_탭_전환_목록에_들어_있다(self):
        """★여기서 빠지면 단추는 켜지는데 화면이 안 바뀐다 — 조용히 틀린다."""
        m = re.search(r"\['live','past','ml','analysis','report','ui','policy'\]", self.h)
        self.assertTrue(m, "탭 전환 목록에 'ui' 가 없다")

    def test_처음_열_때_싣는다(self):
        """★7MB 한 장이다. 미리 실으면 관제 여는 값이 그만큼 는다."""
        self.assertIn("initUi();", self.h)
        self.assertIn("let UI_LOADED = false;", self.h)
        self.assertRegex(self.h, r"if\(f && !UI_LOADED\)\{ f\.src = UI_SRC; UI_LOADED = true; \}")
        # 마크업의 iframe 에는 src 를 박아 두지 않는다
        tag = re.search(r"<iframe id=\"uiframe\"[^>]*>", self.h).group(0)
        self.assertNotIn("src=", tag, "iframe 에 src 가 박혀 있으면 탭을 안 열어도 싣는다")

    def test_관제가_내주는_주소를_가리킨다(self):
        self.assertIn("const UI_SRC = '/static/%s';" % MON, self.h)

    def test_새_창으로도_연다(self):
        """고객: "UI 화면을 보고싶은 사람도 있을거 아니야" — 크게 볼 길도 둔다."""
        self.assertIn('id="btnuiopen"', self.h)
        self.assertIn("window.open(UI_SRC, '_blank')", self.h)


if __name__ == "__main__":
    unittest.main()
