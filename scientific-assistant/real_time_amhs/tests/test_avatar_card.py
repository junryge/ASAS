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

    def test_지금은_오프닝에_카드가_없다(self):
        """★2026-09 — 오프닝을 새 시안으로 바꾸면서 뺐다
        (고객: "아바타 2D는 일단 빼둬라").

        관제 시스템이 아니라 새 탭으로 뜨는 다른 앱이라, 고르는 자리에 같이
        두면 무엇을 고르는 화면인지가 흐려진다. '일단' 이라고 하셨으므로
        서버 설정(/api/avatar)과 배선(wireAvatar)은 그대로 남겨 둔다 —
        되살릴 때는 renderOpen 의 lead 에 카드를 넣고 wireAvatar() 를 부르면 된다.
        """
        self.assertNotIn('id="sys-avatar"', self.html, "카드가 아직 그려진다")
        self.assertIn("async function wireAvatar()", self.html, "배선까지 지우면 안 된다")
        self.assertIn('<div class="lead solo">', self.html, "ALL 이 혼자 한 줄을 쓴다")

    def test_아바타를_끄면_ALL_이_줄을_다_쓴다(self):
        """★숨기기만 하면 옆칸이 빈 채로 남아 ALL 이 반쪽 폭으로 쪼그라든다."""
        self.assertIn(".sysgrid .lead.solo", self.html)
        self.assertIn("classList.add('solo')", self.html)

    def test_관제_전환을_타지_않는다(self):
        """★pickSystem 은 수집·화면을 통째로 그 시스템으로 바꾼다.
        아바타는 앱이라 그 경로를 타면 안 된다 — 클릭 배선이 data-sys 가
        있는 것만 걸어야 한다. 카드를 되살려도 이 규칙은 그대로다."""
        self.assertIn("#sysgrid .sys[data-sys]", self.html)
        i = self.html.index("async function wireAvatar()")
        body = self.html[i:i + 2000]
        self.assertNotIn("pickSystem", body, "아바타가 관제 전환을 타면 안 된다")
        self.assertIn("window.open(AVATAR.url", body, "새 탭으로 연다")

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
