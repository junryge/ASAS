# -*- coding: utf-8 -*-
"""UI대쉬보드 — 오른쪽 FAB 실시간 상황판 · 바탕 그림.

고객: "각 FAB 별 숫자 · 경계·위험·초위험 알리는 내용 팻말 그리고 각각 그래프가
      보이면 좋을 것 같은데" · "옆에 뭔가를 볼 수 있는 게 나와야 돼" ·
      "실시간 상황표니까 간소하고 명확하게" · "오른쪽에 뭐가 잘 나와야 돼".
고객: "지금 바탕화면 색상 4개 있는데 이것도 같이 투명하게 뒤에 집어 넣어주라
      바탕화면에 맞게".
"""
import io
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
WORLD = os.path.join(APP, "월드모델", "월드모델파생")
MON = "OHT_Bridge_Monitor.html"
WM = "OHT_Bridge_Monitor_배경.webp"


def _read(*p):
    with io.open(os.path.join(*p), encoding="utf-8", newline="") as fh:
        return fh.read()


def _editor_block(html):
    a = '<script id="bm-editor">\n'
    i = html.index(a) + len(a)
    return html[i:html.index('\n  </script>', i)]


class 두_화면이_같은_편집기를_쓴다(unittest.TestCase):
    """★편집기는 bridge_editor.js 한 벌이다 — 관제 static/ 과 월드모델파생 두 HTML 에
       똑같이 박힌다. 한쪽만 고치면 두 화면이 서로 다른 말을 한다."""

    def test_HTML_두_벌이_같다(self):
        self.assertEqual(_read(APP, "static", MON), _read(WORLD, MON))

    def test_박힌_것이_bridge_editor_js_그대로다(self):
        self.assertEqual(_editor_block(_read(APP, "static", MON)),
                         _read(WORLD, "bridge_editor.js"))


class 관제가_추이를_준다(unittest.TestCase):
    """/api/fab/trend — FAB 마다 최근 N분 점수 + 지금 걸린 룰 한 줄."""

    @classmethod
    def setUpClass(cls):
        s = _read(APP, "server.py")
        i = s.index('@app.route("/api/fab/trend")')
        cls.f = s[i:s.index("@app.route(", i + 10)]

    def test_주소가_있다(self):
        self.assertIn("def api_fab_trend():", self.f)

    def test_구간은_10분에서_6시간(self):
        self.assertIn('max(10, min(360, int(request.args.get("minutes", 60))))', self.f)

    def test_점수를_다시_계산하지_않는다(self):
        """★FAB 분리 파일의 점수(수집 때 area_score 로 맞춘 그 칸)를 그대로 읽는다 —
           패널 숫자(/api/fab/compare)와 같은 원본."""
        self.assertIn('"score": round(_score(last), 1)', self.f)
        self.assertIn("[[t.strftime(\"%H:%M\"), round(_score(r), 1)]", self.f)

    def test_ALL_은_빼고_FAB_만(self):
        self.assertIn('if f == "ALL":', self.f)

    def test_옛_sentinel_이어도_돈다(self):
        """★파일 하나씩 올린다 — sentinel.py 가 옛것이면 걸린 룰만 비고 추이는 선다."""
        self.assertRegex(self.f, r"try:\n\s+from sentinel import fab_reason[^\n]*\n\s+except ImportError:\n\s+fab_reason = None")

    def test_오늘이_없으면_최근으로_물러서고_그_날을_준다(self):
        self.assertIn("latest_day(cfg)", self.f)
        self.assertIn('"fab": f, "day": day', self.f)

    def test_등급_설명은_설정_것을_그대로(self):
        self.assertIn('b.get("severity")', self.f)

    def test_원본이_그대로면_다시_안_만든다(self):
        self.assertIn("_cached_json(TREND_CACHE, str(minutes), sig, _build)", self.f)


class 오른쪽_상황판(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.h = _read(APP, "static", MON)

    def test_다섯_FAB_늘_같은_순서(self):
        self.assertIn("var SIDE_ORDER = ['M14', 'M14B', 'M16A', 'M16B', 'M16HUB'];", self.h)

    def test_ALL_은_안_세운다(self):
        self.assertIn("f !== 'ALL' && !(r && r.is_all)", self.h)

    def test_숫자와_등급은_패널과_같은_것(self):
        """★패널이 쓰는 /api/fab/compare 행을 그대로 받는다 — 둘이 다른 숫자를 말하면 안 된다."""
        self.assertIn("SIDE_ROWS = by; SIDE_AT = LIVE_AT;", self.h)

    def test_추이는_관제에서_받는다(self):
        self.assertIn("fetch(location.origin + '/api/fab/trend?minutes=' + SIDE_MIN", self.h)

    def test_등급_팻말(self):
        self.assertIn('<span class="bm-ssign">', self.h)
        self.assertIn("SIDE_TREND.severity[lv]", self.h)
        self.assertIn(".bm-srow.lv초위험 .bm-ssign{", self.h)

    def test_경계_위험_초위험_숫자를_같이(self):
        for k, w in (("warn", "점 · 경계 "), ("danger", " · 위험 "), ("critical", " · 초위험 ")):
            self.assertIn(w, self.h)
            self.assertIn("esc(cuts.%s == null ? '–' : cuts.%s)" % (k, k), self.h)

    def test_추이에_컷_점선(self):
        self.assertIn("[['warn', '#ffce7a'], ['danger', '#ff6b6b'], ['critical', '#ff3b3b']]", self.h)
        self.assertIn('stroke-dasharray="3 3"', self.h)

    def test_눈금은_값과_컷에_맞춘다(self):
        """★0~100 으로 두면 선이 납작해져 오르내림이 안 보였다."""
        self.assertIn("var lo = Math.max(0, Math.min.apply(null, vs) - 5)", self.h)

    def test_자료_시각과_멎음을_적는다(self):
        """★수집이 멎었는데 실시간처럼 보이는 것이 제일 위험하다."""
        self.assertIn("' 기준 · ' + (LIVE_MS / 1000) + '초마다 갱신'", self.h)
        self.assertIn("' 전 자료 — 수집 확인'", self.h)
        self.assertIn(".bm-shd.old .bm-sdot{background:#ffce7a;animation:none}", self.h)

    def test_모르면_걸린_룰_없음이라고_안_적는다(self):
        """★옛 관제라 추이를 못 받았으면 아무것도 안 적는다 — 모르는 것을 '없음' 이라 하면 거짓말."""
        i = self.h.index("function sideWhy(fab, t) {")
        self.assertIn("if (!SIDE_TREND) return '';", self.h[i:i + 200])

    def test_긴_룰은_말풍선에_다(self):
        self.assertIn('<div class="bm-swhy" title="\' + esc(w) + \'">', self.h)

    def test_누르면_그_FAB_그래프(self):
        self.assertIn("graphOpen(r.getAttribute('data-side-fab'))", self.h)

    def test_끌_수_있다(self):
        self.assertIn("['side', '오른쪽 FAB 실시간 상황판", self.h)
        self.assertIn("(CFG.areas.side && CFG.areas.side.hide) ? 'none' : ''", self.h)

    def test_무대를_밀어_올리지_않는다(self):
        """★안쪽 칸을 절대 위치로 — 넘치면 상황판 안에서만 굴린다 (다섯째 줄이 잘렸었다)."""
        self.assertIn(".bm-sin{position:absolute;inset:0;overflow:auto;", self.h)


class 바탕_그림(unittest.TestCase):
    """★회색 바탕을 뺀(투명) 그림 한 장을 무대 맨 뒤에 깐다. 바탕 넷에 맞춰
       진하기·색을 바꾼다 — 어두운 바탕은 밝기를 뒤집어 비추고, 화이트는 그대로 찍는다."""

    @classmethod
    def setUpClass(cls):
        cls.h = _read(APP, "static", MON)
        with open(os.path.join(APP, "static", WM), "rb") as fh:
            cls.img = fh.read()

    def test_그림이_두_화면_옆에_있다(self):
        """★HTML 옆 파일이다 (설정 JSON 처럼) — 관제는 /static/, 월드모델파생은 더블클릭."""
        self.assertIn("var WM_NAME = '%s';" % WM, self.h)
        with open(os.path.join(WORLD, WM), "rb") as fh:
            self.assertEqual(fh.read(), self.img)

    def test_webp_이고_가볍다(self):
        self.assertEqual(self.img[:4], b"RIFF")
        self.assertEqual(self.img[8:12], b"WEBP")
        self.assertLess(len(self.img), 600 * 1024)

    def test_투명하다(self):
        """★회색 바탕이 남으면 어두운 바탕 위에 잿빛 상자가 뜬다 — 알파가 있어야 한다."""
        self.assertEqual(self.img[12:16], b"VP8X")
        self.assertTrue(self.img[20] & 0x10, "VP8X 알파 표시가 없다")
        self.assertIn(b"ALPH", self.img[:4096])

    def test_바탕_넷에_맞춘다(self):
        m = re.search(r"var WM_THEME = \{(.*?)\n  \};", self.h, re.S)
        self.assertTrue(m)
        t = {k: (float(a), inv == "true")
             for k, a, inv in re.findall(r"(\w+):\s*\{ a: ([\d.]+), inv: (true|false) \}", m.group(1))}
        self.assertEqual(sorted(t), ["contrast", "dark", "light", "navy"])
        self.assertFalse(t["light"][1], "화이트는 그대로 얹는다")
        for k in ("dark", "navy", "contrast"):
            self.assertTrue(t[k][1], k + " 는 밝기를 뒤집어야 글자가 비친다")
        self.assertEqual(min(t, key=lambda k: t[k][0]), "contrast", "고대비는 읽기가 먼저 — 제일 옅게")
        for k, (a, _inv) in t.items():
            self.assertLessEqual(a, .2, k + " — 뒤에 깐 그림이다, 진하면 판이 안 읽힌다")
        self.assertIn("filter:invert(1) hue-rotate(180deg);mix-blend-mode:screen", self.h)
        self.assertIn("filter:none;mix-blend-mode:multiply", self.h)

    def test_맨_뒤에_깐다(self):
        self.assertIn("stage.insertBefore(e, stage.firstChild);", self.h)
        self.assertIn(".bm-wm{position:absolute;inset:0;pointer-events:none;", self.h)

    def test_옛_설정이어도_선다(self):
        """★옆의 설정 JSON 이 이긴다 — 그 JSON 에 wm 칸이 없어도 바탕 테마에 맞춰 떠야 한다."""
        self.assertIn("var m = b.wm || {}, md = wmDef();", self.h)

    def test_끄고_진하기를_바꾼다(self):
        self.assertIn("['page', 'stage', 'grid', 'glow', 'wm'].map(bgRow)", self.h)
        self.assertIn('data-path="bg.wm.show"', self.h)
        self.assertIn('data-path="bg.wm.a"', self.h)

    def test_바탕을_바꿔도_끔은_남는다(self):
        self.assertIn("if (wmOff) CFG.bg.wm = { hide: true };", self.h)


class 화이트에서_정상_숫자(unittest.TestCase):
    """★정상일 때는 숫자에 색을 안 줘서 바탕 글자색(화이트 = 어두운 색)을 물려받아
       어두운 패널 위에서 묻혔다. 경계·위험·초위험 색은 인라인 !important 라 안 덮인다."""

    def test_밝게_둔다(self):
        h = _read(APP, "static", MON)
        i = h.index("var LIGHT_CSS = [")
        self.assertIn("'[data-bm-slot=\"val\"]{color:#e8eff6 !important}'", h[i:h.index("].join", i)])
        self.assertIn("e.style.setProperty('color', LIVE_COL[lv], 'important')", h)


if __name__ == "__main__":
    unittest.main()
