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


class 패널에_관제_점수를_적는다(unittest.TestCase):
    """고객: "패널 m14b>m14b LFT 이게아니라 M14B AREA_SCORE 야, 현재값을 기입해야되
    55/67 이면 55는 현재 값/경계값 정책에 있어, 정책 연결해서 볼수 있도록"
    · "다른것도 마찬가지겠지 그치".

    관제의 /api/fab/compare 가 ALL+FAB 다섯을 한 시각으로 준다 — 줄마다
    area_score 와 **그 FAB 의 컷**이 같이 온다. 경계값은 정책 탭의 그 값이다.
    """

    @classmethod
    def setUpClass(cls):
        import json
        h = _read("static", MON)
        cls.tpl = json.loads(
            re.search(r'<script type="__bundler/template">(.*?)</script>', h, re.S).group(1))
        cls.h = h

    def _slots(self, card):
        i = self.tpl.index('data-bm-card="%s"' % card)
        j = self.tpl.find('data-bm-card="', i + 10)
        blk = self.tpl[i:j if j > 0 else len(self.tpl)]
        return set(re.findall(r'data-bm-slot="(\w+)"', blk))

    def test_다섯_패널에_자리가_있다(self):
        """★부제·현재값·경계값 셋은 반드시 있어야 한다 — 없으면 옛 숫자가 남아 거짓말을 한다."""
        for c in ("M14B", "M14A", "M16HUBOHT", "M166F", "M16EUV"):
            self.assertTrue({"sub", "val", "cap"} <= self._slots(c), c + " 에 자리가 빈다")

    def test_M16EUV_는_단위_막대가_없다(self):
        """★칸마다 마크업이 다르다. 없는 것을 있다고 치면 만들 때 멈춘다."""
        self.assertNotIn("bar", self._slots("M16EUV"))
        self.assertTrue({"bar", "unit"} <= self._slots("M14B"))

    def test_카드와_관제_FAB_이_짝이다(self):
        want = "{ M14B: 'M14B', M14A: 'M14', M16HUBOHT: 'M16HUB', M166F: 'M16B', M16EUV: 'M16A' }"
        self.assertIn("var CARD_FAB = " + want, self.h)

    def test_경계값은_서버가_준_컷을_그대로_쓴다(self):
        """★여기서 다시 계산하면 정책 탭과 언젠가 어긋난다."""
        self.assertIn("var cuts = r.cuts || {}", self.h)
        self.assertIn("'/ ' + warn", self.h)
        self.assertNotIn("warn = 60", self.h)

    def test_부제는_FAB_AREA_SCORE(self):
        self.assertIn("e.textContent = fab + ' AREA_SCORE';", self.h)

    def test_정책_컷_셋을_말풍선에_보여준다(self):
        self.assertIn("정책 컷 — 경계 ", self.h)
        self.assertIn("관제 정책 탭에서 고치면 여기도 따라 바뀝니다.", self.h)

    def test_관제가_없으면_안_건드린다(self):
        """★더블클릭(file://)이나 관제가 꺼져 있을 때. 거짓 숫자를 만드느니 틀의 것을 둔다."""
        self.assertIn("if (location.protocol === 'file:') return null;", self.h)
        self.assertIn(".catch(function () {});                                // 안 되면 틀의 숫자 그대로", self.h)


class 옆에_있는_설정을_먼저_읽는다(unittest.TestCase):
    """고객: "OHT_Bridge_Monitor_설정.json 같이 있어 처음에 로드할때 이거 먼저
    읽어들여야되, 자꾸 바꿀수는 없잖아" · "static 같은 폴더에 존재해 무조건 읽어들여야되"."""

    def test_설정_JSON_이_static_에_있다(self):
        p = os.path.join(APP, "static", "OHT_Bridge_Monitor_설정.json")
        self.assertTrue(os.path.isfile(p), "static/ 에 설정 JSON 이 없다")
        import json
        with open(p, encoding="utf-8") as fh:
            c = json.load(fh)
        self.assertIn("plates", c)
        self.assertIn("cards", c)

    def test_열_때_옆_파일을_읽는다(self):
        h = _read("static", MON)
        self.assertIn("var SIDE_NAME = 'OHT_Bridge_Monitor_설정.json';", h)
        self.assertIn("sideLoad().then(function () {", h)

    def test_옆_파일이_이긴다(self):
        """★HTML 에 박힌 것도, 이 브라우저에 남긴 것도 누른다 — 파일만 갈아 끼우면 된다."""
        h = _read("static", MON)
        self.assertIn("if (!SIDE_OK) {", h)
        self.assertIn("if (!h || SIDE_OK) return;", h)

    def test_캐시를_끈다(self):
        """★안 끄면 새 JSON 을 놔도 브라우저가 옛 걸 계속 쓴다 — 바로 그 불평이었다."""
        h = _read("static", MON)
        self.assertIn("'?t=' + Date.now()", h)
        self.assertIn("cache: 'no-store'", h)


class 스크롤을_숨긴다(unittest.TestCase):
    """고객: "ui대쉬보드 안에꺼 스크롤좀 숨겨라". 그 화면 뿌리가 min-height:100vh 라
    틀 높이보다 padding 만큼 넘쳐 스크롤이 났다."""

    def test_틀에_맞추는_style_을_넣는다(self):
        h = _read("static", "dashboard.html")
        self.assertIn("st.id = 'ui-host-fit';", h)
        self.assertIn("html,body{height:100%!important;margin:0!important;overflow:hidden!important}", h)
        self.assertIn("min-height:0!important;height:100%!important", h)

    def test_관제_안에_넣었을_때만이다(self):
        """★더블클릭으로 열면 예전 그대로여야 한다 — 그 화면 자체는 안 건드린다."""
        self.assertNotIn("ui-host-fit", _read("static", MON))


class 패널_글자와_시각(unittest.TestCase):
    """고객: "패널 글자 값 크기좀 키워주라 그리고 너무 안보인다" ·
    "시간을 기입해줘야지 fab실시간 상황표에 날짜-시간 기입해주고" ·
    "내용은 실시간으로 변경되는거 맞이?? 데이터 고정되어 있스면 안되요"."""

    @classmethod
    def setUpClass(cls):
        cls.h = _read("static", MON)

    def _size(self, sel):
        m = re.search(re.escape(sel) + r"\{font-size:([\d.]+)px", self.h)
        return float(m.group(1)) if m else None

    def test_글자를_키웠다(self):
        """틀 값은 이름 13 · 부제 11 · 값 19 · 경계 12 · 단위 10 이었다."""
        for sel, was in (('[data-bm-name]', 13), ('[data-bm-slot="sub"]', 11),
                         ('[data-bm-slot="val"]', 19), ('[data-bm-slot="cap"]', 12),
                         ('[data-bm-slot="unit"]', 10)):
            got = self._size(sel)
            self.assertIsNotNone(got, sel + " 크기를 안 정했다")
            self.assertGreater(got, was, f"{sel} 가 {got} — 틀의 {was} 보다 커야 한다")

    def test_흐린_글자를_밝혔다(self):
        """"너무 안보인다" — 부제·경계·단위가 흐린 회색이었다."""
        self.assertIn('[data-bm-slot="sub"]{font-size:12.5px !important;color:#b8c9d8', self.h)
        self.assertIn('color:#8fa3b5 !important}', self.h)

    def test_자료_시각을_적는다(self):
        self.assertIn("function liveClock(at, day)", self.h)
        self.assertIn("e.className = 'bm-clock';", self.h)
        self.assertIn(".bm-clock{position:absolute;left:16px;top:12px", self.h)

    def test_지금_시각이_아니라_자료_시각이다(self):
        """★수집이 멎으면 시계만 돌고 숫자는 옛것인 화면이 제일 위험하다."""
        self.assertIn("liveClock(data && data.at, data && data.day)", self.h)
        self.assertIn("이 점수를 잰 시각입니다 (지금 시각이 아닙니다).", self.h)
        self.assertIn("mins + '분 전'", self.h, "몇 분 전 자료인지도 보여야 한다")

    def test_계속_다시_읽는다(self):
        """고객: "값은 계속 변경되잖아" — 30초마다. 브라우저 캐시도 끈다."""
        self.assertIn("var LIVE_MS = 30000;", self.h)
        self.assertIn("liveTimer = setInterval(livePoll, LIVE_MS);", self.h)
        self.assertIn("fetch(u, { cache: 'no-store' })", self.h)


class 바탕색은_관제_것을_쓴다(unittest.TestCase):
    """고객: "화이트 글자가 안보이네, 우리 화이트 빼자. 기존에 실시간 관제에서
    사용하는 색상이 좋을것 같은데".

    ★이 화면은 판(맵)·레일·패널이 **어두운 바탕에 밝은 선**이다. 바탕만 희게
      하면 레일이 날아가고 판 글자도 안 읽힌다 — 바탕 한 칸으로 될 일이 아니었다.
    """

    @classmethod
    def setUpClass(cls):
        cls.h = _read("static", MON)
        cls.d = _read("static", "dashboard.html")

    def _token(self, theme, name):
        """관제 dashboard.html 의 :root[data-theme=…] 에서 토큰 하나를 읽는다."""
        blk = re.search(r':root\[data-theme="%s"\]\{(.*?)\n  \}' % theme, self.d, re.S).group(1)
        return re.search(r'--%s:(#[0-9A-Fa-f]{6})' % name, blk).group(1)

    def test_넷이다(self):
        names = re.findall(r"\{ name: '([^']+)', bg:", self.h)
        self.assertEqual(names, ["다크", "네이비", "고대비", "화이트"], names)

    def test_옛_화이트는_버렸다(self):
        """★바탕만 희게 하던 그 값이다. 판이 반투명이라 판 위 글자가 1.1 까지 떨어졌다."""
        self.assertNotIn("#eef2f7", self.h)
        self.assertNotIn("#fbfcfe", self.h)

    def test_화이트도_관제_것을_쓴다(self):
        self.assertIn("page: { col: '%s'" % self._token("light", "bg"), self.h)
        self.assertIn("stage: { col: '%s' }" % self._token("light", "line"), self.h)
        self.assertIn("fg: '%s' }" % self._token("light", "tx"), self.h)

    def test_화이트는_판을_어둡게_둔다(self):
        """★핵심. 판(plate)이 반투명이라 무대를 밝히면 그 빛이 판을 뚫고 올라와
           판 위 글자(7F · 3F · M16 HUB ROOM)가 안 읽힌다. 판 뒤에 불투명한
           어두운 바닥을 깔아 무대 빛만 막는다 — 방은 밝게, 판은 어둡게."""
        self.assertIn("light: true", self.h)
        self.assertIn("'[data-bm-plate]{background-color:#0E1821 !important}'", self.h)
        self.assertIn("if (b.light) out.push(LIGHT_CSS);", self.h)

    def test_화이트에서_무대_위_글자는_뒤집는다(self):
        """무대 위에 바로 놓인 것(시각 배지·안내)은 밝은 쪽으로."""
        self.assertIn(".bm-clock{background:rgba(255,255,255,.86)", self.h)
        self.assertIn('[data-bm-text="hint"]{color:#42546A !important}', self.h)

    def test_도구줄은_어둡게_둔다(self):
        """★단추마다 제 어두운 배경이 있다 — 밝게 뒤집으면 어두운 단추에 어두운 글자가
           된다 (한 번 그렇게 했다가 대비 1.21 로 떨어뜨렸다)."""
        self.assertIn("'[data-bm-area=\"toolbar\"]{background-color:#111A24 !important}'", self.h)
        self.assertNotIn('[data-bm-area="toolbar"] *{color:', self.h)

    def test_네이비는_관제_네이비_그대로(self):
        """★관제와 같은 화면으로 보이는 것이 목적이다 — 값을 지어내지 않는다."""
        self.assertIn("page: { col: '%s' }" % self._token("navy", "bg"), self.h)
        self.assertIn("stage: { col: '%s' }" % self._token("navy", "panel"), self.h)
        self.assertIn("grid: { col: '%s' }" % self._token("navy", "cy"), self.h)

    def test_고대비는_관제_고대비_그대로(self):
        self.assertIn("page: { col: '%s'" % self._token("contrast", "bg"), self.h)
        self.assertIn("stage: { col: '%s'" % self._token("contrast", "panel"), self.h)
        self.assertIn("grid: { col: '%s'" % self._token("contrast", "cy"), self.h)

    def test_다크는_아무것도_안_덮는다(self):
        """틀이 원래 쓰던 색 그대로 — 규칙을 아예 안 만든다."""
        self.assertIn("{ name: '다크', bg: {} }", self.h)
