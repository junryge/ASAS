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

    def test_설정_JSON_은_저장소에_두지_않는다(self):
        """고객: "이거 설정 지워라, 로컬에 나한데만 있어야되".
           사람마다 고쳐 쓰는 것이라 저장소에 두지 않는다 — .gitignore 로 막는다.
           ★있으면 그것이 이기고, 없으면 HTML 에 박힌 기본 설정으로 뜬다.
             그래서 없어도 화면은 그대로 돈다 (아래 sideLoad 시험이 그 길을 본다)."""
        gi = os.path.join(os.path.dirname(os.path.dirname(APP)), ".gitignore")   # ASAS/
        self.assertTrue(os.path.isfile(gi), ".gitignore 를 못 찾았다: " + gi)
        with open(gi, encoding="utf-8") as fh:
            self.assertIn("**/OHT_Bridge_Monitor_설정.json", fh.read())

    def test_없어도_화면은_돈다(self):
        """★파일이 없으면 fetch 가 404 로 떨어지고, 그때는 HTML 에 박힌 것으로 간다."""
        h = _read("static", MON)
        self.assertIn("return r.ok ? r.json() : null;", h)
        self.assertIn(".catch(function () {});                           // 없으면 없는 대로", h)

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
        """틀이 원래 쓰던 색 그대로 — 색 규칙을 아예 안 만든다.
        (그래프 테마 이름만 들고 있다. bgCss 는 page/stage/grid/glow/light 만 보므로
         theme 이 있어도 규칙은 한 줄도 안 나온다.)"""
        m = re.search(r"\{ name: '다크', bg: (\{[^}]*\}) \}", self.h)
        self.assertTrue(m, "다크 칸을 못 찾았다")
        for k in ("page", "stage", "grid", "glow", "light"):
            self.assertNotIn(k, m.group(1), "다크가 " + k + " 를 덮는다")
        self.assertIn("theme: 'dark'", m.group(1))


class FAB_더블클릭하면_그래프(unittest.TestCase):
    """고객: "fab을 더블 클릭하면 오른쪽에 fab 관련 그래프가 나오도록 해주라".

    관제의 /api/graph 가 SVG 를 통째로 내준다 — 관제 목록에서 행을 더블클릭할 때
    뜨는 그 구간 그래프와 **같은 그림**이다. 여기서 다시 그리지 않는다.
    graphs.render 가 fabs 를 받으면 "그 FAB 의 영역점수를 스코어 패널에 겹쳐" 그린다.
    """

    @classmethod
    def setUpClass(cls):
        cls.h = _read("static", MON)

    def test_판도_패널도_더블클릭을_받는다(self):
        self.assertIn("document.addEventListener('dblclick'", self.h)
        self.assertIn("e.target.closest('[data-bm-card]')", self.h)
        self.assertIn("e.target.closest('[data-bm-plate]')", self.h)

    def test_판과_관제_FAB_이_짝이다(self):
        want = "{ m14b: 'M14B', m14a: 'M14', m16hub: 'M16HUB', m16a: 'M16A', m16b: 'M16B' }"
        self.assertIn("var PLATE_FAB = " + want, self.h)

    def test_관제_그래프를_그대로_쓴다(self):
        """★여기서 다시 그리면 관제 그래프와 다른 그림이 두 벌 생긴다."""
        self.assertIn("location.origin + '/api/graph' + q", self.h)
        self.assertNotIn("function graphRender", self.h)

    def test_그_FAB_만_그린다(self):
        self.assertIn("'&fabs=' + encodeURIComponent(GRAPH_FAB)", self.h)

    def test_등급_밴드를_그_FAB_컷으로(self):
        """★sys 를 안 넘기면 ALL 컷으로 칠해져, 패널에 적힌 경계값과 그래프가
           서로 다른 말을 한다."""
        self.assertIn("'?sys=' + encodeURIComponent(GRAPH_FAB)", self.h)

    def test_자료_시각_기준이다(self):
        """★지금 시각이 아니라 관제가 준 at 을 기준으로 본다."""
        self.assertIn("LIVE_AT = (data && data.at) || LIVE_AT;", self.h)
        self.assertIn("'&at=' + encodeURIComponent(LIVE_AT.replace(' ', 'T'))", self.h)

    def test_화면_색을_그래프에도_넘긴다(self):
        """★안 넘기면 남색 화면 한가운데 검은 상자가 박힌다 (관제도 같은 이유로 넘긴다)."""
        self.assertIn("var theme = (CFG.bg && CFG.bg.theme) || 'dark';", self.h)
        self.assertIn("'&theme=' + encodeURIComponent(theme)", self.h)
        for nm, th in (("다크", "dark"), ("네이비", "navy"), ("고대비", "contrast"), ("화이트", "light")):
            self.assertIn("{ name: '%s', bg: { theme: '%s'" % (nm, th), self.h, nm)

    def test_구간을_바꿀_수_있다(self):
        self.assertIn("[[60, '1시간'], [180, '3시간'], [720, '12시간']]", self.h)

    def test_점수를_다시_읽을_때_그래프도_새로(self):
        self.assertIn("if (GRAPH_FAB) graphDraw();", self.h)

    def test_화면_돌리기에_안_뺏긴다(self):
        """★무대 위에 얹는 상자다 — 여기서 누른 것을 틀에 넘기면 화면이 돌아간다."""
        self.assertIn("['mousedown', 'wheel', 'pointerdown', 'dblclick'].forEach", self.h)


class 판마다_무슨_FAB_인지(unittest.TestCase):
    """고객: "저기 판.맵중간 이게 무슨 fab인지 기입 해주라" →
    "아니 정면으로 봤을때 저기 빈공간 있잖아 앞으로 바라보면 거기에 이름을
    기입해달라고" · "위쪽 아니야" · "회전 0도에서 봤을때".

    ★판 **앞면**(앞으로 바라볼 때 보이는 30px 띠)에 적는다. 판 위에 얹어 봤더니
      레일과 겹쳐 지저분했고, 바닥에 깔면 레일 밑으로 묻혔다. 앞면은 원래 비어
      있던 자리라 가리는 것도 없고 정면에서 바로 읽힌다.
    """

    @classmethod
    def setUpClass(cls):
        cls.h = _read("static", MON)

    def test_앞면을_찾아_적는다(self):
        self.assertIn("function fabMark(pe, key)", self.h)
        self.assertIn("""pe.querySelector(':scope > div[style*="rotateX(-90deg)"]')""", self.h)
        self.assertIn("face.appendChild(e);", self.h)
        self.assertIn("e.textContent = fab;", self.h)

    def test_직계_자식만_본다(self):
        """★:scope > 로 **그 판의 직계 자식**만 본다. 그냥 찾으면 판 밖의
           브릿지·컨베이어에도 rotateX(-90deg) 가 있어 엉뚱한 데를 집는다
           (틀 전체에는 여러 개다 — 아래에서 센다)."""
        self.assertIn("':scope > div[style*=", self.h)
        import json
        tpl = json.loads(re.search(r'<script type="__bundler/template">(.*?)</script>',
                                   self.h, re.S).group(1))
        n = len(re.findall(r'<div style="[^"]*rotateX\(-90deg\)', tpl))
        self.assertGreaterEqual(n, 5, "판 다섯의 앞면이 있어야 한다 (%d개)" % n)

    def test_앞면이_없으면_안_적는다(self):
        """★틀이 바뀌어 앞면을 못 찾으면 엉뚱한 데 붙이지 않고 그냥 둔다."""
        self.assertIn("if (!fab || !face) { if (e) e.remove(); return; }", self.h)

    def test_맵을_다시_그릴_때마다_같이(self):
        self.assertIn("renderMap(pe, k);\n      fabMark(pe, k);", self.h)
        self.assertIn("{ renderMap(pe, key); fabMark(pe, key); }", self.h)

    def test_띠에_꽉_차게_가운데(self):
        self.assertIn(".bm-fab{position:absolute;inset:0;display:flex;"
                      "align-items:center;justify-content:center;", self.h)

    def test_마우스를_안_먹는다(self):
        self.assertIn("pointer-events:none;white-space:nowrap;", self.h)


class 그래프를_제대로_보여준다(unittest.TestCase):
    """고객: "그래프 똑바로 안할래" · "저런게 작아서 우째보노 사이드를 크게" ·
    "1개 스코어만 보이면 안되지, 다른것도 실제 지표 그래프도" ·
    "그래프쪽 클릭하면 데이터가 뭐지 나와야지"."""

    @classmethod
    def setUpClass(cls):
        cls.h = _read("static", MON)

    def test_img_가_아니라_SVG_를_그대로_넣는다(self):
        """★핵심. /api/graph 는 그 구간에 자료가 없으면 SVG 가 아니라
           <div>이 구간에 자료가 없습니다</div> 를 돌려준다(graphs.py). <img> 로는
           그걸 못 그려서 **빈 상자**만 남았다 — 화면으로 보내 주신 그것이다.
           글로 받아 넣으면 안내도 보이고, SVG 안의 읽기값도 살아난다."""
        self.assertNotIn("bm-gbody\"><img", self.h)
        self.assertIn("body.innerHTML = t;", self.h)
        self.assertIn("return r.ok ? r.text()", self.h)

    def test_못_불러오면_그렇게_말한다(self):
        self.assertIn("그래프를 못 불러왔습니다", self.h)

    def test_서랍을_키웠다(self):
        """고객: "더블클릭해서 그래프 보는 건 남는 공간이 너무 많아. 그래프도 작고".
        폭은 넓게, 높이는 **그림만큼** — 아래로 늘 끝까지 뻗던 것을 뺐다."""
        i = self.h.index("'.bm-graph{position:absolute;")
        blk = self.h[i:self.h.index("'.bm-ghead{", i)]
        m = re.search(r"width:min\((\d+)%,(\d+)px\)", blk)
        self.assertTrue(m, "서랍 크기를 못 찾았다")
        self.assertGreaterEqual(int(m.group(1)), 70, "너무 좁다")
        self.assertGreaterEqual(int(m.group(2)), 1200, "너무 좁다")
        self.assertIn("max-height:calc(100% - 24px)", blk, "그림이 길면 서랍 안에서 굴린다")
        self.assertNotIn("bottom:12px", blk, "아래로 늘 뻗으면 빈 자리가 남는다")

    def test_더_넓게도_된다(self):
        self.assertIn("'.bm-graph.wide{width:calc(100% - 24px)}'", self.h)
        self.assertIn("if (v === 'w') { GRAPH_WIDE = !GRAPH_WIDE; graphDraw(); return; }", self.h)

    def test_그림이_뭉개지지_않게_최소_너비(self):
        """★viewBox 1000 짜리다. 좁은 칸에 욱여넣으면 글자가 뭉개진다."""
        self.assertIn("'.bm-gbody svg{width:100%;min-width:880px;height:auto;display:block}'", self.h)

    def test_눌러서_그_분_값을_붙박이로(self):
        """★관제 SVG 가 이미 분마다 '시각 · 값' 을 그려 두고 .hv:hover 로 보여 준다
           (graphs.py, JS 없이 CSS 로). 같은 규칙에 .bm-pin 짝을 달았을 뿐이다 —
           값을 여기서 새로 읽지 않는다."""
        self.assertIn("var hv = e.target.closest && e.target.closest('.hv');", self.h)
        self.assertIn("hv.classList.add('bm-pin')", self.h)
        self.assertIn("'.bm-gbody .hv.bm-pin .hvt{opacity:1}'", self.h)
        self.assertIn("'.bm-gbody .hv.bm-pin .hvr{opacity:.97}'", self.h)

    def test_누르면_남는다고_적어_둔다(self):
        self.assertIn("그래프를 누르면 그 분 값이 남습니다", self.h)


class 다시_싣기를_뺐다(unittest.TestCase):
    """고객: "ui대쉬보드 다시 싣기 삭제해라!".
    화면 안 도구줄의 단추 · 제목 옆 안내 글 · 그 단추만 쓰던 uiReload 를 같이 뺐다."""

    @classmethod
    def setUpClass(cls):
        cls.h = _read("static", "dashboard.html")

    def test_단추가_없다(self):
        self.assertNotIn("mk('다시 싣기'", self.h)
        self.assertNotIn("function uiReload(", self.h)
        self.assertNotIn("uiReload", self.h.replace("function uiReload(", ""))

    def test_안내_글에도_없다(self):
        i = self.h.index('<div class="page hidden" id="tab-ui">')
        self.assertNotIn("<b>다시 싣기</b>", self.h[i:i + 1500])

    def test_새_창_단추는_그대로(self):
        self.assertIn("mk('⧉ 새 창'", self.h)


class 제목에_준비중(unittest.TestCase):
    """고객: "UI대쉬보드 FAB별 실시간상황별 ---> FAB별 실시간상황별(준비중) 이라고 해줄래".
    ★제목 글자는 그대로 두고 뒤에 (준비중)만 붙였다."""

    def test_탭_제목(self):
        h = _read("static", "dashboard.html")
        i = h.index('<div class="page hidden" id="tab-ui">')
        self.assertIn("<h2>FAB별 실시간 상황표(준비중)", h[i:i + 1500])
