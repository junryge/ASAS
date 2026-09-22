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
        self.assertIn("if(f && !UI_LOADED){ f.src = UI_SRC; UI_LOADED = true; uiWaitBtn(); }", self.h)
        # 마크업의 iframe 에는 src 를 박아 두지 않는다
        tag = re.search(r"<iframe id=\"uiframe\"[^>]*>", self.h).group(0)
        self.assertNotIn("src=", tag, "iframe 에 src 가 박혀 있으면 탭을 안 열어도 싣는다")

    def test_관제가_내주는_주소를_가리킨다(self):
        self.assertIn("const UI_SRC = '/static/%s';" % MON, self.h)

    def test_단추는_화면_안_도구줄에_꽂는다(self):
        """고객: "새창열기,다시 싣기 프레임 안으로 집어 넣던지".
           카드 머리에 두지 않고, 그 화면의 도구줄(✎ 수정 옆)에 꽂는다."""
        self.assertNotIn('id="btnuiopen"', self.h, "단추가 아직 카드 머리에 있다")
        self.assertNotIn('id="btnuireload"', self.h, "단추가 아직 카드 머리에 있다")
        self.assertIn("""d.querySelector('[data-bm-area="toolbar"]')""", self.h)
        self.assertIn("b.className = 'bm-open ui-host';", self.h, "그 화면 모양새를 그대로 쓴다")
        self.assertIn("window.open(UI_SRC, '_blank')", self.h)
        self.assertIn("mk('다시 싣기'", self.h)
        self.assertIn("mk('⧉ 새 창'", self.h)

    def test_그_화면이_다_뜬_뒤에_꽂는다(self):
        """★boot 전에 꽂으면 도구줄도 없고 .bm-open 모양새도 아직 없다."""
        self.assertIn("if(!d || !w || !w.__bm) return false;", self.h)

    def test_두_번_꽂지_않는다(self):
        self.assertIn("if(bar.querySelector('.ui-host')) return true;", self.h)

    def test_단추를_눌러도_화면이_안_돌아간다(self):
        """★그 화면은 왼쪽 끌기가 돌리기다 — 단추 위에서 누른 것은 안 넘긴다."""
        self.assertIn("b.addEventListener('mousedown', e => e.stopPropagation());", self.h)


if __name__ == "__main__":
    unittest.main()


class 맨_위_제목_줄을_껐다(unittest.TestCase):
    """고객: "맨위에 AMHS · INTER-BUILDING BRIDGE / FAB별 실시간 상황표 이거
    삭제해라 아예 글자, 그러면 조금 더 넣어지겠지" — 관제 카드에 이미 같은 제목이
    있어 두 번 나왔다. 무대가 그만큼 넓어진다.

    ★틀은 JSON 문자열로 박혀 있다 (따옴표가 \" 로 escape 돼 있다) — 풀어서 본다.
    """

    @classmethod
    def setUpClass(cls):
        import json
        h = _read("static", MON)
        cls.tpl = json.loads(
            re.search(r'<script type="__bundler/template">(.*?)</script>', h, re.S).group(1))
        cls.cfg = json.loads(
            re.search(r'id="bm-config">(.*?)</script>', h, re.S).group(1).replace("<\\/", "</"))

    def test_머리_줄에_이름표가_달려_있다(self):
        self.assertEqual(self.tpl.count('data-bm-area="header"'), 1)
        i = self.tpl.index('data-bm-area="header"')
        self.assertTrue(self.tpl[self.tpl.rindex("<", 0, i):i].startswith("<header"),
                        "이름표가 <header> 에 안 붙었다")

    def test_제목_두_줄이_그_안에_있다(self):
        """★이걸 껐을 때 정말 그 두 줄이 사라지는지 — 자리를 못 박는다."""
        i = self.tpl.index('data-bm-area="header"')
        head = self.tpl[i:self.tpl.index("</header>", i)]
        self.assertIn("AMHS · INTER-BUILDING BRIDGE", head)
        self.assertIn("동간 브릿지 통합 반송 현황", head)

    def test_기본이_숨김이다(self):
        self.assertTrue(self.cfg["areas"]["header"]["hide"], "머리 줄이 아직 켜져 있다")

    def test_되살릴_길이_있다(self):
        """★지웠다 되돌릴 수 없으면 안 된다 — ✎ 수정 → 화면 에 칸을 둔다."""
        h = _read("static", MON)
        self.assertIn("맨 위 제목 줄", h)
        self.assertIn("★KPI 도 이 안에 있다", h, "KPI 가 같이 꺼지는 것을 밝혀야 한다")


if __name__ == "__main__":
    unittest.main()
