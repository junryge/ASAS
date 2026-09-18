"""오프닝(시스템 선택) 화면 — 대시보드 HTML 을 글자로 검사한다.

브라우저를 띄우는 테스트는 공장 서버에 깔 게 늘어나서 안 쓴다. 대신
**깨지면 바로 티가 나는 것**만 붙잡아 둔다.

  · 시스템 6개(ALL·M14·M14B·M16A·M16B·M14HUB)가 목록에 다 있다
  · 고르기 전에는 수집이 돌지 않는다
      → setInterval(pollStatus/pollCases) 가 최상위에 있으면 안 되고
        startLive() 안에만 있어야 한다. 예전엔 최상위에서 바로 돌았다.
  · 상단 AMOS 표시등은 없다 (주피터 CSV 에 이미 들어 있어 조인을 안 한다)
"""
import os
import re
import unittest

from . import util

SYSTEMS = ("ALL", "M14", "M14B", "M16A", "M16B", "M16HUB")


def _html():
    with open(os.path.join(util.BASE, "static", "dashboard.html"),
              encoding="utf-8") as f:
        return f.read()


def _script(html):
    return html.split("<script>", 1)[1].rsplit("</script>", 1)[0]


class OpeningScreen(unittest.TestCase):
    def setUp(self):
        self.html = _html()
        self.js = _script(self.html)

    def test_시스템_6개가_다_있다(self):
        block = self.js.split("const SYSTEMS", 1)[1].split("];", 1)[0]
        codes = re.findall(r"code:\s*'([^']+)'", block)
        self.assertEqual(tuple(codes), SYSTEMS)

    def test_여섯_시스템_전부_운영중이다(self):
        """FAB 별 fab분리 CSV 가 붙어서 전부 실시간이다. ready:false 가
        남아 있으면 그 FAB 은 눌러도 안 들어간다."""
        block = self.js.split("const SYSTEMS", 1)[1].split("];", 1)[0]
        pairs = re.findall(r"code:\s*'([^']+)'.*?ready:\s*(true|false)", block)
        ready = {c: v == "true" for c, v in pairs}
        self.assertEqual(len(ready), len(SYSTEMS))
        for code in SYSTEMS:
            self.assertTrue(ready[code], f"{code} 가 준비 중으로 꺼져 있습니다")

    def test_고르기_전에는_수집이_안_돈다(self):
        """★최상위에서 폴링을 시작하면 안 고른 화면이 데이터로 차 버린다.

        setInterval(pollStatus…) 는 startLive() 함수 안에만 있어야 한다.
        (들여쓰기 없이 줄 맨 앞에 있으면 최상위 실행이다.)"""
        bad = [ln for ln in self.js.splitlines()
               if re.match(r"setInterval\(poll(Status|Cases)", ln)]
        self.assertEqual(bad, [], "최상위에서 폴링이 시작됩니다: " + "; ".join(bad))
        start = self.js.split("function startLive()", 1)
        self.assertEqual(len(start), 2, "startLive() 가 없습니다")
        body = start[1].split("\n}", 1)[0]
        for fn in ("pollStatus", "pollCases"):
            self.assertIn(f"setInterval({fn}", body,
                          f"startLive() 안에서 {fn} 를 걸지 않습니다")

    def test_준비중은_눌러도_안_들어간다(self):
        """pickSystem 이 ready 를 확인하고 되돌아가야 한다."""
        body = self.js.split("function pickSystem(", 1)[1].split("\n}", 1)[0]
        self.assertRegex(body, r"!s\.ready.*return|return.*!s\.ready")

    def test_오프닝_뼈대가_있다(self):
        for need in ('id="open"', 'id="sysgrid"', 'id="syschip"'):
            self.assertIn(need, self.html, f"{need} 가 없습니다")

    def test_폰트를_바깥에서_받아오지_않는다(self):
        """★공장 서버는 바깥으로 못 나간다. 구글 폰트 CDN 을 부르면 그냥
        기본 글꼴로 떨어져서 디자인이 아니게 된다 — 파일에 박아 넣어야 한다."""
        css = self.html.split("<style>", 1)[1].split("</style>", 1)[0]
        outside = re.findall(r"url\(\s*['\"]?(https?://[^)'\"]+)", css)
        self.assertEqual(outside, [], "바깥 주소에서 폰트를 받습니다: " + str(outside))
        for fam in ("Caprasimo", "Figtree"):
            self.assertRegex(
                css, r"@font-face\{font-family:" + fam + r";[^}]*data:font/woff2;base64,",
                f"{fam} 가 파일에 박혀 있지 않습니다")

    def test_오프닝을_닫으면_배경_애니메이션이_멈춘다(self):
        """★관제 화면은 며칠씩 떠 있다. 안 멈추면 보이지도 않는 캔버스가
        계속 rAF 로 돌면서 CPU 를 먹는다."""
        stop = self.js.split("function opBgStop()", 1)
        self.assertEqual(len(stop), 2, "opBgStop() 이 없습니다")
        self.assertIn("cancelAnimationFrame", stop[1].split("\n}", 1)[0])
        hide = self.js.split("function openHide()", 1)
        self.assertEqual(len(hide), 2, "openHide() 가 없습니다")
        self.assertIn("opBgStop()", hide[1].split("\n", 1)[0])
        # 숨기는 곳은 전부 openHide() 를 거쳐야 한다 — 직접 add('hidden') 금지
        direct = [ln.strip() for ln in self.js.splitlines()
                  if "classList.add('hidden')" in ln and "#open" in ln
                  and "function openHide" not in ln]
        self.assertEqual(direct, [], "openHide() 를 안 거치고 숨깁니다: " + str(direct))

    def test_FAB_타일이_위_줄_카드보다_작다(self):
        """오프닝의 계층 — 위 줄(ALL·AVATAR_2D)이 크고 아래 FAB 다섯은 작다.
        다섯이 위 줄만큼 커지면 화면이 카드로 가득 차서 무엇을 먼저 눌러야
        하는지가 사라진다."""
        def _h(sel):
            m = re.search(re.escape(sel) + r"\{[^}]*min-height:(\d+)px", self.html)
            self.assertIsNotNone(m, sel + " 의 min-height 가 없다")
            return int(m.group(1))

        def _cd(sel):
            m = re.search(re.escape(sel) + r" \.cd\{[^}]*font-size:([\d.]+)px", self.html)
            self.assertIsNotNone(m, sel + " .cd 의 크기가 없다")
            return float(m.group(1))

        self.assertLess(_h(".sys.fab"), _h(".sys.hero"))
        self.assertLess(_h(".sys.fab"), _h(".sys.app"))
        self.assertLess(_cd(".sys.fab"), _cd(".sys.hero"))

    def test_FAB_상태줄만_따로_줄인다(self):
        """.sys .st 는 아바타 카드도 같이 쓴다. 거기를 줄이면 위 줄의 큰
        카드까지 같이 작아진다."""
        self.assertIn(".sys.fab .st{", self.html)


    def test_상단_AMOS_표시등이_없다(self):
        """주피터 CSV 에 AMOS 컬럼이 들어 있어 조인을 안 한다 —
        표시등은 항상 빨간색이라 연결이 끊긴 것처럼 보였다."""
        self.assertNotIn("ch-amos", self.html)
        self.assertNotIn("amos_warn", self.html)



class 새_오프닝_시안(unittest.TestCase):
    """고객이 준 시안(LLM ANOMALY WATCH)으로 오프닝을 바꿨다.

    눈썹 한 줄 · 큰 표제 · 설명 · 지표 띠 · 오른쪽 발광 구 · 테마 고르기.
    ★시안은 검은 배경 한 벌이지만 이 화면은 테마가 넷이다 — 색을 박지 않고
      토큰(--bg·--tx·--cy…)에서 꺼내 쓴다.
    """

    @classmethod
    def setUpClass(cls):
        cls.h = _html()

    def test_시안의_글이_그대로_있다(self):
        for t in ("FAB OPERATIONS INTELLIGENCE", "LLM ANOMALY WATCH",
                  "실시간 이상감지", "관제", "플랫폼"):
            self.assertIn(t, self.h, t)

    def test_발광_구가_있다(self):
        self.assertIn('class="oorb"', self.h)
        for c in ("core", "ring r1", "ring r2", "scan"):
            self.assertIn(c, self.h, c)
        # 클릭을 먹으면 그 아래 단추가 안 눌린다
        self.assertIn("pointer-events:none;opacity:var(--oorb,1)", self.h)

    def test_밝은_테마에서는_구를_옅게(self):
        """어두운 시안 그대로 두면 밝은 바탕에 얼룩처럼 보인다."""
        self.assertRegex(self.h, r':root\[data-theme="light"\]\{--oorb:\.\d+;')
        self.assertRegex(self.h, r':root\[data-theme="contrast"\]\{--oorb:\.\d+;')

    def test_가로_스크롤을_막았다(self):
        """구가 상자 밖으로 나가 있어 안 막으면 아래에 가로 막대가 생긴다."""
        i = self.h.index(".open{position:fixed")
        self.assertIn("overflow-y:auto;overflow-x:hidden", self.h[i - 200:i + 200])

    def test_지표는_실제_값으로_채운다(self):
        """시안의 1,284 · 240ms · 3 은 그림에 박힌 숫자다 — 그대로 두면 거짓말이다."""
        for i in ("opk-sys", "opk-lat", "opk-alert"):
            self.assertIn('id="%s"' % i, self.h, i)
        # 시안의 가짜 숫자가 **화면에** 남으면 안 된다 (주석에 적힌 설명은 괜찮다)
        body = self.h.split("<body>", 1)[1]
        for fake in ("1,284", "240 ms", ">3<"):
            self.assertNotIn(fake, body.split('<div class="ostat">', 1)[1][:900], fake)
        self.assertIn("async function openStats()", self.h)
        j = self.h.index("async function openStats()")
        body = self.h[j:j + 1200]
        self.assertIn("/api/status?sys=ALL", body)
        self.assertIn("/api/cases?all=1&sys=ALL", body)
        self.assertIn("'–'", body, "못 받았으면 0 이 아니라 '–' (0 은 '이상 없음' 으로 읽힌다)")

    def test_테마_넷을_오프닝에서_고른다(self):
        i = self.h.index('class="othm"')
        box = self.h[i:i + 700]
        for t, nm in (("dark", "다크"), ("light", "화이트"),
                      ("navy", "네이비"), ("contrast", "고대비")):
            self.assertIn('data-theme="%s">%s<' % (t, nm), box, nm)

    def test_테마_단추는_한_길을_쓴다(self):
        """상단 바와 오프닝에 단추가 둘이다 — 한쪽만 갱신하면 다른 쪽 불이 남는다."""
        self.assertIn("'#themechip button[data-theme], .othm button[data-theme]'", self.h)
        self.assertIn("window.__setTheme(b.getAttribute('data-theme'))", self.h)

    def test_아바타_카드를_뺐다(self):
        """고객: "아바타 2D는 일단 빼둬라". 관제 시스템이 아니라 새 탭으로
        뜨는 다른 앱이라, 고르는 자리에 같이 두면 무엇을 고르는 화면인지 흐려진다."""
        self.assertNotIn('id="sys-avatar"', self.h)
        i = self.h.index("function renderOpen()")
        blk = self.h[i:i + 2200]
        # 주석의 설명은 괜찮다 — 실제로 그리는 자리(템플릿 문자열)에만 없으면 된다
        tpl = blk.split("$('#sysgrid').innerHTML = `", 1)[1].split("`;", 1)[0]
        self.assertNotIn("AVATAR_2D", tpl, "오프닝이 아직 카드를 그린다")
        self.assertNotIn("sys-avatar", tpl)
        self.assertNotIn("wireAvatar();", blk, "renderOpen 이 아직 부른다")
        # 다시 넣을 수 있게 배선은 남긴다 ('일단' 이라고 하셨다)
        self.assertIn("async function wireAvatar()", self.h)

    def test_ALL_이_혼자_한_줄을_쓴다(self):
        """아바타를 뺐으니 옆칸이 빈다 — 가로로 길고 낮게."""
        i = self.h.index("function renderOpen()")
        self.assertIn('<div class="lead solo">', self.h[i:i + 900])
        self.assertIn(".sysgrid .lead.solo .sys.hero{min-height:0", self.h)

    def test_고르는_시스템은_여전히_여섯(self):
        """ALL + FAB 다섯 — 서버 systems() 와 같아야 한다 (test_fabs 가 본다)."""
        i = self.h.index("const SYSTEMS = [")
        blk = self.h[i:self.h.index("];", i)]
        for c in ("'ALL'", "'M14'", "'M14B'", "'M16A'", "'M16B'", "'M16HUB'"):
            self.assertIn(c, blk, c)


if __name__ == "__main__":
    unittest.main()
