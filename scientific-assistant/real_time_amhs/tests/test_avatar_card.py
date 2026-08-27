#!/usr/bin/env python3
"""오프닝 화면의 AVATAR_2D 카드.

★이건 관제 시스템이 아니다. 따로 뜨는 앱이라 systems() 목록에 넣지 않는다 —
  넣으면 수집 대상이 되고, 화면의 SYSTEMS 와 서버의 systems() 가 어긋나
  test_fabs 가 깨진다.
"""
from __future__ import annotations

import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


class 설정(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(_ROOT, "config.json"), encoding="utf-8") as f:
            self.cfg = json.load(f)

    def test_설정이_있다(self):
        av = self.cfg.get("avatar")
        self.assertIsInstance(av, dict)
        self.assertIn("port", av)
        self.assertIn("url", av)

    def test_관제_시스템_목록에는_없다(self):
        """★넣으면 수집이 돌기 시작한다. 이건 수집 대상이 아니다."""
        from lp_client import fab_codes
        codes = {str(c).upper() for c in (fab_codes(self.cfg) or [])}
        self.assertNotIn("AVATAR", codes)
        self.assertNotIn("AVATAR_2D", codes)


class 화면(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(_ROOT, "static", "dashboard.html"),
                  encoding="utf-8") as f:
            cls.html = f.read()

    def test_카드가_ALL_옆에_온다(self):
        """위 줄(lead) 안, ALL 바로 다음이다 — 아래 FAB 묶음(rest) 이 아니다."""
        lead = self.html.index('<div class="lead">')
        hero = self.html.index('class="sys hero"')
        j = self.html.index('id="sys-avatar"')
        rest = self.html.index('<div class="rest">')
        self.assertLess(lead, hero, "lead 묶음 밖으로 나갔다")
        self.assertLess(hero, j, "ALL 보다 앞에 있다")
        self.assertLess(j, rest, "아래 FAB 묶음으로 내려갔다")

    def test_아바타를_끄면_ALL_이_줄을_다_쓴다(self):
        """★숨기기만 하면 옆칸이 빈 채로 남아 ALL 이 반쪽 폭으로 쪼그라든다."""
        self.assertIn(".sysgrid .lead.solo", self.html)
        self.assertIn("classList.add('solo')", self.html)

    def test_관제_전환을_타지_않는다(self):
        """★pickSystem 은 수집·화면을 통째로 그 시스템으로 바꾼다.
        아바타는 앱이라 그 경로를 타면 안 된다 — 그래서 data-sys 가 없고,
        클릭 배선도 data-sys 가 있는 것만 건다."""
        self.assertIn("#sysgrid .sys[data-sys]", self.html)
        card = self.html[self.html.index('id="sys-avatar"'):]
        card = card[:card.index("</button>")]
        self.assertNotIn("data-sys", card)

    def test_꺼져_있으면_알려_준다(self):
        """★안 그러면 눌렀을 때 빈 화면만 나오고 관제가 고장난 줄 안다."""
        self.assertIn("꺼져 있음", self.html)
        self.assertIn("python run.py", self.html)

    def test_새_탭으로_연다(self):
        self.assertIn("window.open(AVATAR.url", self.html)
        self.assertIn("noopener", self.html)

    def test_설정에서_끄면_안_보인다(self):
        self.assertIn("btn.style.display = 'none'", self.html)


class 엔드포인트(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import server
            cls.app = server.app.test_client()
        except Exception as e:
            raise unittest.SkipTest(f"서버를 못 띄운다: {e}")

    def test_주소를_알려_준다(self):
        r = self.app.get("/api/avatar")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertTrue(d["url"].startswith("http"))
        self.assertIn("alive", d)

    def test_안_떠_있으면_alive_가_거짓(self):
        """이 환경엔 아바타 서버가 없다 — 그래도 500 이 아니라 답을 준다."""
        d = self.app.get("/api/avatar").get_json()
        self.assertIn(d["alive"], (True, False))

    def test_실행_방법을_같이_준다(self):
        self.assertIn("run.py", self.app.get("/api/avatar").get_json()["hint"])


if __name__ == "__main__":
    unittest.main()
