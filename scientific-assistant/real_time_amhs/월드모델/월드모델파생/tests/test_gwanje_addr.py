# -*- coding: utf-8 -*-
"""실시간 스코어 탭이 묻는 관제 주소 — 127.0.0.1 고정을 푼다 (2026-10-07).

고객
    "실시간관제 외부에서 접속하게 해야지 127.0.0.1 하면 안 되지"
    "실시간에서 다른 서버에서 접속하는데 경계가 있어야 하는데 없네" · "왜 경계값이 안 보이는데"

127.0.0.1 은 '월드모델파생이 도는 그 PC' 다. 관제가 다른 서버에 떠 있으면 그 관제의 경계 · 위험
줄과 경계 컷을 못 받는다. 그래서
    ① 사람이 넣지 않아도 답하는 관제를 찾는다 — 환경변수 GWANJE_URL(있으면 그것만) > 찾아 둔 주소
       (관제_주소.json, 이 PC 에만) > 이 PC > 관제 설정의 IP > 관제 화면에서 넘어온 주소(?gw= · referrer)
       · 이 서버에 들어온 주소. 사내 프록시를 타지 않는다.
       고객: "관제 주소를 왜 바꾸는데 — 처음부터 보이게" · "실시간인데 이런 것까지 해야 하나"
    ② 화면 스코어 탭에 지금 묻는 관제 주소가 보인다 (POST /api/score/gwanje 는 비상용으로 남긴다)
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
        # 현장 config.json 이 host 를 사내 IP 로 박아 두었으면 진짜 관제를 찾아 버린다 — 시험은 빼고 본다
        self.old_conf = GS._conf_base
        GS._conf_base = lambda: ""

    def tearDown(self):
        GS._conf_base = self.old_conf
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


class _가짜_관제:
    """/api/status 에 관제처럼 답하는 작은 서버 — 스스로 찾기 시험용."""

    def __init__(self):
        import http.server
        import threading

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                body = json.dumps({"systems": ["ALL", "M16HUB"],
                                   "cuts": {"warn": 60, "danger": 71, "critical": 85}}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


def _dead_url():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return f"http://127.0.0.1:{p}"


class 스스로_찾는다(_Addr):
    """고객: "관제 주소를 왜 바꾸는데 — 처음부터 보이게 하면 되지"."""

    def setUp(self):
        super().setUp()
        self.gw = _가짜_관제()
        self.old_default = GS._default_base
        GS._default_base = lambda: _dead_url()        # 이 PC 에는 관제가 없다고 친다
        self.old_hints = list(GS._HINTS)
        GS._HINTS.clear()
        GS._RES.update(at=0.0, key=None, ok=False, url="")

    def tearDown(self):
        GS._default_base = self.old_default
        GS._HINTS[:] = self.old_hints
        GS._RES.update(at=0.0, key=None, ok=False, url="")
        self.gw.close()
        super().tearDown()

    def test_사내_프록시를_타지_않는다(self):
        """빈 ProxyHandler 는 기본 프록시 처리기를 대신한다 — 프록시를 든 처리기가 하나도 없어야 한다."""
        import urllib.request
        with_proxy = [h for h in GS._OPENER.handlers
                      if isinstance(h, urllib.request.ProxyHandler) and getattr(h, "proxies", None)]
        self.assertEqual(with_proxy, [])
        os.environ["HTTP_PROXY"], old = "http://10.255.255.1:3128", os.environ.get("HTTP_PROXY")
        try:   # 시스템 프록시가 있어도 관제에는 곧장 간다
            self.assertTrue(GS._probe(self.gw.url))
        finally:
            if old is None:
                os.environ.pop("HTTP_PROXY", None)
            else:
                os.environ["HTTP_PROXY"] = old

    def test_관제_화면에서_넘어온_주소로_찾는다(self):
        GS.note_hints(self.gw.url)
        r = GS.resolve()
        self.assertEqual((r["url"], r["src"], r["ok"]), (self.gw.url, "auto", True))
        self.assertEqual(GS.base(), self.gw.url)

    def test_찾은_주소는_이_PC_에_적어_둔다(self):
        GS.note_hints(self.gw.url)
        GS.resolve()
        with open(GS.ADDR_FILE, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["url"], self.gw.url)

    def test_적어_둔_주소가_죽으면_다른_후보로(self):
        GS.set_addr(_dead_url())
        GS.note_hints(self.gw.url)
        self.assertEqual(GS.resolve(force=True)["url"], self.gw.url)

    def test_아무도_없으면_오류를_말한다(self):
        r = GS.check()
        self.assertFalse(r["ok"])
        self.assertIn("닿지 않습니다", r["error"])

    def test_환경변수면_그것만(self):
        os.environ["GWANJE_URL"] = _dead_url()
        GS.note_hints(self.gw.url)
        r = GS.resolve(force=True)
        self.assertEqual((r["src"], r["ok"]), ("env", False))

    def test_관제가_아닌_서버는_고르지_않는다(self):
        self.assertFalse(GS._probe(_dead_url()))
        self.assertTrue(GS._probe(self.gw.url))


class 관제_설정의_IP(_Addr):
    """관제 config.json 의 server.host 를 사내 IP 하나로 박으면 같은 PC 라도 127.0.0.1 로는 안 열린다."""

    def setUp(self):
        super().setUp()
        GS._conf_base = self.old_conf                 # 여기서는 진짜 것을 본다 (설정만 바꿔 끼운다)
        self.old = (GS._gw_server, GS._probe)
        self.old_hints = list(GS._HINTS)
        GS._HINTS.clear()
        GS._RES.update(at=0.0, key=None, ok=False, url="")

    def tearDown(self):
        GS._gw_server, GS._probe = self.old
        GS._HINTS[:] = self.old_hints
        GS._RES.update(at=0.0, key=None, ok=False, url="")
        super().tearDown()

    def test_IP_를_박았으면_그_IP_도_찾아_본다(self):
        GS._gw_server = lambda: {"host": "10.20.30.40", "port": 8989}
        self.assertEqual([u for u, _s in GS._candidates()],
                         ["http://127.0.0.1:8989", "http://10.20.30.40:8989"])
        GS._probe = lambda u, timeout=2.5: u == "http://10.20.30.40:8989"
        r = GS.resolve(force=True)
        self.assertEqual((r["url"], r["ok"]), ("http://10.20.30.40:8989", True))

    def test_모두_열기면_이_PC_만(self):
        for h in ("0.0.0.0", "", "127.0.0.1", "localhost", "bad host/x"):
            GS._gw_server = lambda h=h: {"host": h, "port": 8989}
            self.assertEqual([u for u, _s in GS._candidates()], ["http://127.0.0.1:8989"], h)


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
        for need in ("/api/score/gwanje", "gwLink(S)", "window.prompt(", "gwQ()", "document.referrer"):
            self.assertIn(need, js)

    def test_관제_링크에_관제_주소를_싣는다(self):
        """관제 'OHT 재생' 링크가 관제 자기 주소(gw)를 실어 보낸다 — 이걸로 스스로 찾는다."""
        sys.path.insert(0, os.path.join(APP, "..", ".."))
        import world_link as W
        from urllib.parse import parse_qs, urlparse
        x = W.link("M16HUB", "2026-10-07T09:00:00", {}, "10.1.2.3:8989")
        q = {k: v[0] for k, v in parse_qs(urlparse(x["url"]).query).items()}
        self.assertEqual(q["gw"], "http://10.1.2.3:8989")


if __name__ == "__main__":
    unittest.main()
