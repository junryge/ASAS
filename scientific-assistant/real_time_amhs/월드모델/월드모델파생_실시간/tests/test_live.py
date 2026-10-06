#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""월드모델파생_실시간 시험 — 가짜 로그프레소(tests/mock_logpresso.py)로 끝까지 돌린다.

    cd 월드모델파생_실시간 && python -m unittest discover -s tests -t .

진짜 데이터는 하나도 없다 (차 번호 · 운반물 다 지어낸 것).
"""
import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import unittest
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.dirname(HERE)
for p in (LIVE, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)
try:                                     # 이 상자에 pandas 가 없으면 빈 것으로 (logpresso_query import 용)
    import pandas  # noqa: F401
except ImportError:
    sys.path.insert(0, os.path.join(HERE, "_stub"))

KEY = "dummy-key"
os.environ.setdefault("MOCK_LP_KEY", KEY)

import live_engine as LE                 # noqa: E402
from mock_logpresso import World         # noqa: E402

T0 = datetime(2026, 10, 6, 10, 0, 0)


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class 피드(unittest.TestCase):
    """LiveFeed — 로그프레소 대신 가짜 줄(World)을 바로 먹인다."""

    @classmethod
    def setUpClass(cls):
        cls.w = World("M16A_BR")

    def setUp(self):
        self.now = [T0]
        self.wall = [1000.0]
        self.calls = []

        def fetch(table, s, e):
            self.calls.append((table, s, e))
            return self.w.rows(s, min(e, self.now[0]))
        self.f = LE.LiveFeed("M16A", "BR", fetch=fetch, clock=lambda: self.now[0],
                             wall=lambda: self.wall[0])

    def step(self, sec=5):
        self.now[0] += timedelta(seconds=sec)
        self.wall[0] += sec
        return self.f.poll_once()

    def test_처음엔_최근_몇_분을_받는다(self):
        self.f.poll_once()
        table, s, e = self.calls[0]
        self.assertEqual(table, "oht_data_m16br", "허브룸 지도 → 허브룸 테이블")
        self.assertEqual(s, T0 - timedelta(seconds=LE.WARM_SEC))
        self.assertGreaterEqual(e, T0)
        self.assertEqual(len(self.f.state), 32 + 4 + 1 + 3, "멈춰 있어 드물게 보고하는 차까지 다 올라온다")

    def test_재생과_같은_판정(self):
        self.f.poll_once()
        t, snap = self.f.current()
        vs = snap["vehicleStats"]
        self.assertEqual(vs["ht_stop"], 1, "HT_STOP 1대 (보고가 살아 있다)")
        self.assertEqual(vs["jam_live"], 4, "JAM 4대")
        # 미보고 — 3분에 한 번만 보고하는 차. 데이터 시계로 50초 넘으면 미보고
        exp = sum(1 for m in self.w.miss
                  if LE.MISS_SEC <= (t - self._last_report(m, t)).total_seconds() < LE.IDLE_SEC)
        self.assertEqual(vs["missing"], exp)
        self.assertEqual(vs["ohtAlert"]["level"], "전조", "HT_STOP 1대 이상 = 전조 (config.OHT_ALERT)")
        hs = [h for h in snap["hotspots"] if h["kind"] == "cluster"]
        self.assertTrue(hs and hs[0]["stopped"] >= 4, "한 주소에 몰린 JAM 이 정체 묶음으로 잡힌다")
        v = next(x for x in snap["vehicles"] if x["vid"] == "V09000")
        for k in ("x", "y", "state", "isFull", "vhlCycle", "currentNode", "nextNode", "missSec", "carrierId"):
            self.assertIn(k, v)
        self.assertEqual(snap["state"], "playing")
        self.assertEqual(snap["date"], "LIVE")

    def _last_report(self, m, t):
        sec = int(t.timestamp())
        while (sec + m["phase"]) % 180:
            sec -= 1
        return datetime.fromtimestamp(sec)

    def test_겹쳐_묻고_같은_줄은_한_번만(self):
        self.f.poll_once()
        cur = self.f.cursor
        n = self.step(5)
        _, s, _ = self.calls[-1]
        self.assertEqual(s, cur - timedelta(seconds=LE.OVERLAP_SEC), "늦게 들어온 줄을 받으려고 겹쳐 묻는다")
        new_rows = self.w.rows(cur + timedelta(seconds=1), self.now[0])
        self.assertEqual(n, len([r for r in new_rows]), "겹친 부분은 다시 얹지 않는다")

    def test_늦게_온_옛_줄은_버린다(self):
        self.f.poll_once()
        before = dict(self.f.state["V09000"])
        old = self.w.rows(T0 - timedelta(seconds=60), T0 - timedelta(seconds=58))
        self.assertEqual(self.f._ingest([r for r in old if r["VEHICLE"] == "V09000"]), 0)
        self.assertEqual(self.f.state["V09000"]["currentNode"], before["currentNode"])

    def test_오래_끊겼으면_처음부터(self):
        self.f.poll_once()
        self.now[0] += timedelta(seconds=LE.MAX_GAP_SEC + 60)
        self.f.poll_once()
        _, s, _ = self.calls[-1]
        self.assertEqual(s, self.now[0] - timedelta(seconds=LE.WARM_SEC), "끊긴 뒤엔 WARM 부터")
        self.assertTrue(self.f.status["warm"])

    def test_부드럽게_늦춰서_차례로(self):
        self.f.poll_once()
        newest = self.f.frames[-1][0]
        t1, _ = self.f.current()
        self.assertLessEqual(t1, newest - timedelta(seconds=LE.BUFFER_SEC) + timedelta(seconds=2))
        seen = [t1]
        for _ in range(4):                      # 벽시계만 흐른다 (새 데이터 없음)
            self.wall[0] += 1
            seen.append(self.f.current()[0])
        self.assertEqual(seen, sorted(seen), "화면 시각은 뒤로 가지 않는다")
        self.assertGreater(seen[-1], seen[0], "2초 칸을 차례로 넘긴다")
        self.wall[0] += 600
        self.assertEqual(self.f.current()[0], newest, "새 데이터가 없으면 가장 새 칸에서 멈춘다")

    def test_프레임은_최근_3분만(self):
        self.f.poll_once()
        for _ in range(50):
            self.step(5)
        span = (self.f.frames[-1][0] - self.f.frames[0][0]).total_seconds()
        self.assertLessEqual(span, LE.KEEP_SEC)

    def test_실패하면_적고_천천히(self):
        def boom(*a):
            raise RuntimeError("HTTP 401 테스트")
        self.f.fetch = boom
        w1 = self.f.tick()
        w2 = self.f.tick()
        self.assertGreater(w2, w1)
        self.assertLessEqual(self.f.tick(), 60.0)
        info = self.f.info()
        self.assertIn("401", info["error"])
        self.assertEqual(info["fails"], 3)
        self.f.fetch = lambda t, s, e: self.w.rows(s, min(e, self.now[0]))
        self.assertEqual(self.f.tick(), LE.POLL_SEC)
        self.assertIsNone(self.f.info()["error"], "다시 되면 오류를 지운다")


class 지도와_테이블(unittest.TestCase):
    def test_짝(self):
        self.assertEqual(LE.table_for("M14B", "A"), "oht_data_m14b", "규칙대로면 m14a 가 된다 — 적어 둔 짝을 쓴다")
        self.assertEqual(LE.table_for("M16A", "BR"), "oht_data_m16br")
        self.assertEqual(LE.table_for("M16A", "E"), "oht_data_m16e", "모르는 지도는 규칙")

    def test_캐시만_있어도_목록에(self):
        keys = {(e["fab"], e["prefix"]) for e in LE.catalog()}
        self.assertTrue({("M14A", "A"), ("M16A", "BR"), ("M16B", "B")} <= keys)


class 로그프레소(unittest.TestCase):
    """fetch_rows — 진짜 HTTP 로 가짜 로그프레소에 묻는다 (월드모델파생 logpresso_query 의 서버·키 규칙)."""

    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        env = dict(os.environ, MOCK_LP_KEY=KEY, MOCK_LAG_SEC="0")
        cls.p = subprocess.Popen([sys.executable, os.path.join(HERE, "mock_logpresso.py"), str(cls.port)],
                                 env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", cls.port), 0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        cls.env = {k: os.environ.get(k) for k in ("LP_HOST", "LP_PORT")}
        os.environ["LP_HOST"], os.environ["LP_PORT"] = "127.0.0.1", str(cls.port)
        cls.LQ = LE._lq()
        cls.key0 = cls.LQ.API_KEY

    @classmethod
    def tearDownClass(cls):
        cls.p.kill()
        cls.p.wait()
        cls.LQ.API_KEY = cls.key0
        for k, v in cls.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_지금_줄을_받는다(self):
        self.LQ.API_KEY = KEY
        now = datetime.now()
        rows = LE.fetch_rows("oht_data_m16br", now - timedelta(seconds=10), now)
        self.assertTrue(rows)
        self.assertEqual(set(rows[0]) >= {"_time", "VEHICLE", "ADDRESS", "DISTANCE", "NEXT_ADDRESS", "STATUS"}, True)
        self.assertTrue(LE.server_of("oht_data_m16br").startswith(f"127.0.0.1:{self.port} (운영판"))

    def test_상세_쿼리_그대로(self):
        self.LQ.API_KEY = KEY
        now = datetime.now()
        LE.fetch_rows("oht_data_m14a", now - timedelta(seconds=3), now)
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("GET", "/mock/hits")
        q = json.loads(c.getresponse().read())["last_q"]
        self.assertIn("oht_data_m14a", q)
        self.assertIn('search MSG_ID == "2"', q, "재생판 '상세' 쿼리와 같다")
        self.assertNotIn("remote", q, "운영은 remote 로 감싸지 않는다")

    def test_키가_틀리면_401_과_끝_4자(self):
        self.LQ.API_KEY = "dummy-wrong-9876"         # 가짜 (관제 test_secrets 가 'dummy' 를 자리표시로 본다)
        now = datetime.now()
        with self.assertRaises(RuntimeError) as cm:
            LE.fetch_rows("oht_data_m16br", now - timedelta(seconds=3), now)
        self.assertIn("HTTP 401", str(cm.exception))
        self.assertIn("…9876", str(cm.exception))
        self.assertNotIn("dummy-wrong", str(cm.exception), "키를 통째로 적지 않는다")

    def test_키가_없으면_알려_준다(self):
        self.LQ.API_KEY = ""
        with self.assertRaises(RuntimeError) as cm:
            LE.fetch_rows("oht_data_m16br", datetime.now(), datetime.now())
        self.assertIn("API 키", str(cm.exception))


class 기존판_logpresso_query(unittest.TestCase):
    """현장 월드모델파생이 운영 전환 전 판이어도 그 판대로 묻는다 (2026-10-06 현장: "변경 안 했다, 기존꺼").

    기존판 = 서버 한 대(HOST · PORT) · 쿼리를 remote {REMOTE_NODE} [ … ] 로 감쌈 · server_for 없음.
    현장에서 실제로 난 오류: module 'logpresso_query' has no attribute 'server_for'."""

    @classmethod
    def setUpClass(cls):
        import types
        cls.port = _free_port()
        env = dict(os.environ, MOCK_LP_KEY=KEY, MOCK_LAG_SEC="0")
        cls.p = subprocess.Popen([sys.executable, os.path.join(HERE, "mock_logpresso.py"), str(cls.port)],
                                 env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", cls.port), 0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        cls.env = {k: os.environ.pop(k, None) for k in ("LP_HOST", "LP_PORT")}
        old = types.ModuleType("logpresso_query")      # 기존판과 같은 겉모양
        old.HOST, old.PORT, old.API_KEY, old.REMOTE_NODE = "127.0.0.1", cls.port, KEY, "icamcslogdt01"

        def _build_query(from_dt, to_dt, table, profile=None):
            inner = f'table from={from_dt} to={to_dt} {table} | search MSG_ID == "2" | sort _time'
            return f"remote {old.REMOTE_NODE} [ {inner} ]" if old.REMOTE_NODE else inner
        old._build_query = _build_query
        cls.old = old
        cls._lq0 = LE._lq
        LE._lq = lambda: old

    @classmethod
    def tearDownClass(cls):
        LE._lq = cls._lq0
        cls.p.kill()
        cls.p.wait()
        for k, v in cls.env.items():
            if v is not None:
                os.environ[k] = v

    def test_server_for_가_없어도_묻는다(self):
        self.assertFalse(hasattr(self.old, "server_for"))
        self.assertEqual(LE.route("oht_data_m14a"),
                         ("127.0.0.1", self.port, "기존판 · 서버 한 대 · remote icamcslogdt01"))
        now = datetime.now()
        rows = LE.fetch_rows("oht_data_m14a", now - timedelta(seconds=10), now)
        self.assertTrue(rows, "기존판 서버에서 줄을 받는다")
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("GET", "/mock/hits")
        q = json.loads(c.getresponse().read())["last_q"]
        self.assertTrue(q.startswith("remote icamcslogdt01 [ table from="), "그 판의 쿼리 모양(remote) 그대로")
        self.assertIn("기존판", LE.server_of("oht_data_m14a"))

    def test_피드도_돈다(self):
        f = LE.LiveFeed("M16A", "BR")
        f.poll_once()
        self.assertTrue(f.frames, "기존판으로도 차가 올라온다")
        self.assertIn("기존판", f.info()["server"])

    def test_주소가_아예_없으면_알려_준다(self):
        self.old.HOST = ""
        try:
            with self.assertRaises(RuntimeError) as cm:
                LE.route("oht_data_m14a")
            self.assertIn("서버 주소가 없습니다", str(cm.exception))
        finally:
            self.old.HOST = "127.0.0.1"


class 서버(unittest.TestCase):
    """main.py — 표준 파이썬 서버. 로그프레소는 가짜, 화면은 월드모델파생 것 그대로."""

    @classmethod
    def setUpClass(cls):
        cls.mport = _free_port()
        env = dict(os.environ, MOCK_LP_KEY=KEY, MOCK_LAG_SEC="0")
        cls.mock = subprocess.Popen([sys.executable, os.path.join(HERE, "mock_logpresso.py"), str(cls.mport)],
                                    env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", cls.mport), 0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        cls.env = {k: os.environ.get(k) for k in ("LP_HOST", "LP_PORT")}
        os.environ["LP_HOST"], os.environ["LP_PORT"] = "127.0.0.1", str(cls.mport)
        cls.LQ = LE._lq()
        cls.key0 = cls.LQ.API_KEY
        cls.LQ.API_KEY = KEY
        import importlib.util           # ★이름이 같은 월드모델파생/main.py 와 헷갈리지 않게 파일로 읽는다
        spec = importlib.util.spec_from_file_location("live_main", os.path.join(LIVE, "main.py"))
        M = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(M)
        cls.M = M
        cls.port = _free_port()
        cls.srv = M.Server(("127.0.0.1", cls.port), M.Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.mock.kill()
        cls.mock.wait()
        cls.LQ.API_KEY = cls.key0
        for k, v in cls.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def req(self, method, path, body=None, cookie=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        h = {"Content-Type": "application/json"}
        if cookie:
            h["Cookie"] = cookie
        c.request(method, path, json.dumps(body) if body is not None else None, h)
        r = c.getresponse()
        data = r.read()
        return r.status, dict(r.getheaders()), data

    def test_화면은_월드모델파생_그대로_조각_둘(self):
        st, h, body = self.req("GET", "/")
        self.assertEqual(st, 200)
        html = body.decode("utf-8")
        with open(os.path.join(LE.WM_DIR, "dashboard.html"), encoding="utf-8") as f:
            orig = f.read()
        self.assertIn('id="map-canvas"', html)
        self.assertIn("LiveSocket", html, "웹소켓 → HTTP 조각")
        self.assertIn("live-chip", html, "상태줄 조각")
        self.assertLess(html.index("LiveSocket"), html.index("function connectWS()"),
                        "웹소켓 조각은 화면 스크립트보다 먼저")
        self.assertGreater(html.index("live-chip"), html.index("bootFabs().then(autoFromQuery)"),
                           "상태줄 조각은 화면 스크립트 뒤")
        # 조각 둘을 빼면 월드모델파생 화면과 한 글자도 안 다르다 (화면 파일은 그대로 쓴다)
        head = "\n<script>\n" + self.M._read("live_ws.js") + "\n</script>\n"
        tail = "<script>\n" + self.M._read("live_ui.js") + "\n</script>\n"
        self.assertEqual(html.replace(head, "", 1).replace(tail, "", 1), orig)
        self.assertIn("no-store", h.get("Cache-Control", ""))
        self.assertIn("oht_live_sid=", h.get("Set-Cookie", ""))

    def test_지도_고르고_실시간_한_장(self):
        st, h, _ = self.req("GET", "/api/fabs")
        cookie = h["Set-Cookie"].split(";")[0]
        st, _, b = self.req("POST", "/api/fab/select", {"fab": "M16A", "prefix": "BR"}, cookie)
        self.assertEqual(st, 200)
        d = json.loads(b)
        self.assertEqual((d["fab"], d["prefix"], d["table"]), ("M16A", "BR", "oht_data_m16br"))
        st, _, b = self.req("GET", "/api/layout-graph", cookie=cookie)
        g = json.loads(b)
        self.assertGreater(len(g["nodes"]), 1000)
        self.assertIn("stations", g)
        snap = None
        for _ in range(60):                       # 첫 조회(5분치)를 기다린다
            st, _, b = self.req("GET", "/api/live/snapshot", cookie=cookie)
            snap = json.loads(b)
            if snap.get("vehicles"):
                break
            time.sleep(0.25)
        self.assertTrue(snap["vehicles"], "차가 올라온다")
        L = snap["live"]
        self.assertEqual(L["table"], "oht_data_m16br")
        self.assertTrue(L["server"].startswith(f"127.0.0.1:{self.mport}"), L["server"])
        self.assertEqual(L["key"], "…" + KEY[-4:])
        self.assertIsNone(L["error"])
        self.assertIsNotNone(L["lag_sec"])
        self.assertNotIn(KEY, b.decode("utf-8"), "키를 화면에 내주지 않는다")

    def test_주소로_지도를_고른다(self):
        st, h, _ = self.req("GET", "/?fab=M16B&prefix=B")
        cookie = h["Set-Cookie"].split(";")[0]
        st, _, b = self.req("GET", "/api/fabs", cookie=cookie)
        self.assertEqual(json.loads(b)["current"], {"fab": "M16B", "prefix": "B"})

    def test_재생_조회는_없다고_답한다(self):
        st, _, b = self.req("POST", "/api/logpresso/load", {"from_dt": "20261006100000"})
        self.assertEqual(st, 200)
        self.assertTrue(json.loads(b)["live"])

    def test_정적_파일과_바깥_막기(self):
        st, h, _ = self.req("GET", "/static/js/oht3d/oht3d.js")
        self.assertEqual(st, 200)
        self.assertTrue(h["Content-Type"].startswith("text/javascript"))
        for bad in ("/static/../main.py", "/static/%2e%2e/config.py", "/static/..%2fconfig.py"):
            st, _, _ = self.req("GET", bad)
            self.assertEqual(st, 404, bad)

    def test_모르는_지도는_거절(self):
        st, _, b = self.req("POST", "/api/fab/select", {"fab": "X", "prefix": "Y"})
        self.assertEqual(st, 400)


class 화면_조각(unittest.TestCase):
    def test_웹소켓_대신_HTTP(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node 가 없다")
        with open(os.path.join(LIVE, "live_ws.js"), encoding="utf-8") as f:
            js = f.read()
        prog = """
const window = { WebSocket: function(u){ this.real = u; } };
let n = 0;
global.fetch = (u) => { n++; return Promise.resolve({ text: () => Promise.resolve('{"time_short":"10:00:00","u":"' + u + '"}') }); };
global.setTimeout = (fn, ms) => { if (ms === 0 || n < 3) setImmediate(fn); };
""" + js.replace("(function () {", "(function () {", 1) + """
const ws = new window.WebSocket('ws://h/ws');
const got = [];
ws.onmessage = (e) => got.push(JSON.parse(e.data));
ws.send('{"action":"play"}');
const other = new window.WebSocket('ws://h/other');
setImmediate(() => setImmediate(() => setImmediate(() => setImmediate(() => {
  console.log(JSON.stringify({ got, other: other.real || null, isLive: !!ws._tick }));
}))));
"""
        r = subprocess.run([node, "-e", prog], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertTrue(out["isLive"])
        self.assertTrue(out["got"], "onmessage 로 스냅샷이 간다")
        self.assertEqual(out["got"][0]["u"], "/api/live/snapshot")
        self.assertEqual(out["other"], "ws://h/other", "다른 웹소켓은 진짜로")

    def test_재생_단추를_숨기고_상태줄(self):
        with open(os.path.join(LIVE, "live_ui.js"), encoding="utf-8") as f:
            js = f.read()
        for need in ("#topbar .tb-query", 'button[onclick^="sendCmd("]', ".speed-btn", "slider-container",
                     "frame-display", "statusMap.playing = '실시간'", "window.updateUI = function",
                     "badge badge-playing", "badge badge-stopped"):
            self.assertIn(need, js)


if __name__ == "__main__":
    unittest.main()
