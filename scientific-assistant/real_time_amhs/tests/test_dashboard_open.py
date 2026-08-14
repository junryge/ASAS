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

SYSTEMS = ("ALL", "M14", "M14B", "M16A", "M16B", "M14HUB")


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

    def test_ALL_만_운영중이다(self):
        """나머지는 아직 수집이 안 붙었다 — 들어가면 빈 화면만 본다."""
        block = self.js.split("const SYSTEMS", 1)[1].split("];", 1)[0]
        pairs = re.findall(r"code:\s*'([^']+)'.*?ready:\s*(true|false)", block)
        ready = {c: v == "true" for c, v in pairs}
        self.assertEqual(len(ready), len(SYSTEMS))
        self.assertTrue(ready["ALL"])
        for code in SYSTEMS[1:]:
            self.assertFalse(ready[code], f"{code} 가 운영중으로 켜져 있습니다")

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

    def test_상단_AMOS_표시등이_없다(self):
        """주피터 CSV 에 AMOS 컬럼이 들어 있어 조인을 안 한다 —
        표시등은 항상 빨간색이라 연결이 끊긴 것처럼 보였다."""
        self.assertNotIn("ch-amos", self.html)
        self.assertNotIn("amos_warn", self.html)


if __name__ == "__main__":
    unittest.main()
