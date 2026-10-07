# -*- coding: utf-8 -*-
"""실시간 스코어 탭이 묻는 관제 주소 — 127.0.0.1 고정을 푼다 (2026-10-07).

고객
    "실시간관제 외부에서 접속하게 해야지 127.0.0.1 하면 안 되지"
    "실시간에서 다른 서버에서 접속하는데 경계가 있어야 하는데 없네" · "왜 경계값이 안 보이는데"

127.0.0.1 은 '월드모델파생이 도는 그 PC' 다. 관제가 다른 서버에 떠 있으면 그 관제의 경계 · 위험
줄과 경계 컷을 못 받는다. 그래서
    ① 주소 = 환경변수 GWANJE_URL > 화면에서 저장한 주소(관제_주소.json, 이 PC 에만) > 이 PC 의 관제
    ② 화면 스코어 탭에 지금 묻는 관제 주소가 보이고, 거기서 바꾼다 (POST /api/score/gwanje)
    ③ 관제가 FAB 컷을 비워 보내도 경계선 · '경계 60 · 위험 …' 이 사라지지 않게 /api/status 컷으로 채운다
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
for p in (APP, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import gwanje_score as GS                # noqa: E402


def _read(*p):
    with open(os.path.join(APP, *p), encoding="utf-8") as fh:
        return fh.read()


class _Addr(unittest.TestCase):
    """실제 폴더에 관제_주소.json 을 만들지 않게 임시 경로로 돌린다 · 환경변수도 되돌린다."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.old_file, self.old_env = GS.ADDR_FILE, os.environ.pop("GWANJE_URL", None)
        GS.ADDR_FILE = os.path.join(self.tmp, "관제_주소.json")

    def tearDown(self):
        GS.ADDR_FILE = self.old_file
        os.environ.pop("GWANJE_URL", None)
        if self.old_env is not None:
            os.environ["GWANJE_URL"] = self.old_env


class 주소_고르기(_Addr):

    def test_아무것도_없으면_이_PC(self):
        a = GS.addr()
        self.assertEqual(a["src"], "default")
        self.assertTrue(a["url"].startswith("http://127.0.0.1:"))

    def test_화면에서_저장한_주소(self):
        a = GS.set_addr("10.1.2.3:8989")
        self.assertEqual(a, {"url": "http://10.1.2.3:8989", "src": "file"})
        self.assertEqual(GS.base(), "http://10.1.2.3:8989")
        with open(GS.ADDR_FILE, encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"url": "http://10.1.2.3:8989"})

    def test_환경변수가_먼저(self):
        GS.set_addr("http://10.1.2.3:8989")
        os.environ["GWANJE_URL"] = "http://10.9.9.9:8989/"
        self.assertEqual(GS.addr(), {"url": "http://10.9.9.9:8989", "src": "env"})

    def test_비우면_이_PC_로(self):
        GS.set_addr("http://10.1.2.3:8989")
        self.assertEqual(GS.set_addr("")["src"], "default")
        self.assertFalse(os.path.exists(GS.ADDR_FILE))

    def test_엉뚱한_주소는_안_받는다(self):
        for bad in ("http://10.1.2.3:8989/api/feed", "ftp://10.1.2.3", "10.1.2.3:8989?x=1",
                    "javascript:alert(1)"):
            with self.assertRaises(ValueError, msg=bad):
                GS.set_addr(bad)
        self.assertEqual(GS.addr()["src"], "default")

    def test_바꾸면_옛_답을_안_쓴다(self):
        GS._CACHE["http://127.0.0.1:8989/api/feed?x=1"] = (0, (200, "", b"{}", ""))
        GS.set_addr("http://10.1.2.3:8989")
        self.assertEqual(GS._CACHE, {})


class 경계_컷이_비어도(_Addr):
    """관제가 fab_cuts 를 비워 보내면(FAB 점수표 계산 실패) 탭의 경계선 · 글자가 통째로 사라졌다."""

    def setUp(self):
        super().setUp()
        self.old_get = GS.get
        self.asked = []

        def fake(path, params, ttl=0.0, timeout=8.0):
            self.asked.append(path)
            if path == "/api/feed":
                d = {"rows": [{"at": "2026-10-07T09:00:00", "score": 62, "level": "경계"}],
                     "fab_cuts": {}}
                return 200, "application/json", json.dumps(d).encode("utf-8"), ""
            if path == "/api/status":
                d = {"cuts": {"warn": 60, "danger": 71, "critical": 85}}
                return 200, "application/json", json.dumps(d).encode("utf-8"), ""
            return 404, "", b"{}", ""
        GS.get = fake

    def tearDown(self):
        GS.get = self.old_get
        super().tearDown()

    def test_관제_status_컷으로_채운다(self):
        d = GS.feed("M16A", "BR", 30)
        self.assertTrue(d["ok"], d)
        self.assertEqual(d["fab_cuts"]["M16HUB"], {"warn": 60, "danger": 71, "critical": 85})
        self.assertIn("/api/status", self.asked)
        self.assertEqual(d["rows"][0]["level"], "경계")

    def test_주소_출처를_같이_준다(self):
        d = GS.feed("M16A", "BR", 30)
        self.assertEqual(d["gwanje_src"], "default")
        self.assertTrue(d["gwanje"].startswith("http://127.0.0.1:"))


class 화면과_서버가_잇는다(unittest.TestCase):

    def test_길이_있다(self):
        m = _read("main.py")
        self.assertIn('@app.get("/api/score/gwanje")', m)
        self.assertIn('@app.post("/api/score/gwanje")', m)

    def test_탭에서_보고_바꾼다(self):
        js = _read("static", "js", "live_mode.js")
        for need in ("/api/score/gwanje", "관제 주소 ", "gwLink(S)", "window.prompt("):
            self.assertIn(need, js)


if __name__ == "__main__":
    unittest.main()
