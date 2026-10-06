#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""월드모델파생_실시간 시험 — 가짜 로그프레소(tests/mock_logpresso.py) · 가짜 관제(tests/mock_gwanje.py).

    cd 월드모델파생_실시간 && python -m unittest discover -s tests -t .

진짜 데이터는 하나도 없다 (차 번호 · 운반물 · 점수 다 지어낸 것).
"""
import http.client
import importlib.util
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


def _spawn(script, port, **env):
    e = dict(os.environ, MOCK_LP_KEY=KEY, MOCK_LAG_SEC="0", **env)
    p = subprocess.Popen([sys.executable, os.path.join(HERE, script), str(port)], env=e,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(80):
        try:
            socket.create_connection(("127.0.0.1", port), 0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    return p


def _get(port, path):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    c.request("GET", path)
    r = c.getresponse()
    return r.status, r.read()


class 피드(unittest.TestCase):
    """LiveFeed — 로그프레소 대신 가짜 줄(World)을 바로 먹인다."""

    @classmethod
    def setUpClass(cls):
        cls.w = World("M16A_BR")

    def setUp(self):
        self.now = [T0]
        self.wall = [1000.0]
        self.calls = []
        self.f = LE.LiveFeed("M16A", "BR", fetch=self.fetch, clock=lambda: self.now[0],
                             wall=lambda: self.wall[0])

    def fetch(self, table, s, e):
        self.calls.append((table, s, e))
        return LE.Rows(self.w.rows(s, min(e, self.now[0])))

    def step(self, sec=5):
        self.now[0] += timedelta(seconds=sec)
        self.wall[0] += sec
        return self.f.poll_once()

    def warm(self):
        """처음 WARM_SEC 를 다 채울 때까지 묻는다."""
        self.f.poll_once()
        for _ in range(20):
            info = self.f.info()
            if info["filled_sec"] is not None and info["filled_sec"] >= LE.WARM_SEC:
                return
            self.step(5)
        self.fail("WARM_SEC 를 못 채웠다")

    def test_처음엔_1분만_받고_거꾸로_채운다(self):
        """현장: 5분치를 한 번에 묻다가 응답이 끊겼다 (IncompleteRead). 이제 한 번에 60초씩."""
        self.f.poll_once()
        edge = T0 - timedelta(seconds=LE.EDGE_SEC)
        table, s, e = self.calls[0]
        self.assertEqual(table, "oht_data_m16br", "허브룸 지도 → 허브룸 테이블")
        self.assertEqual((s, e), (edge - timedelta(seconds=LE.STEP_Q_SEC), edge), "처음엔 최근 STEP_SEC 만")
        _, s2, e2 = self.calls[1]
        self.assertEqual((s2, e2), (edge - timedelta(seconds=2 * LE.STEP_Q_SEC), s), "그 앞을 STEP_SEC 만큼 거꾸로")
        self.assertTrue(self.f.frames, "첫 조회만으로 바로 보인다")
        self.warm()
        for _, a, b in self.calls:
            self.assertLessEqual((b - a).total_seconds(), LE.STEP_Q_SEC + LE.OVERLAP_SEC, "크게 묻지 않는다")
        self.assertEqual(len(self.f.state), 32 + 4 + 1 + 3, "멈춰 있어 드물게 보고하는 차까지 다 올라온다")

    def test_재생과_같은_판정(self):
        self.warm()
        self.step(5)
        t, snap = self.f.current()
        vs = snap["vehicleStats"]
        self.assertEqual(vs["ht_stop"], 1, "HT_STOP 1대 (보고가 살아 있다)")
        self.assertEqual(vs["jam_live"], 4, "JAM 4대")
        exp = sum(1 for m in self.w.miss
                  if LE.MISS_SEC <= (t - self._last_report(m, t)).total_seconds() < LE.IDLE_SEC)
        self.assertEqual(vs["missing"], exp, "미보고 — 데이터 시계로 50초 넘으면")
        self.assertEqual(vs["ohtAlert"]["level"], "전조", "HT_STOP 1대 이상 = 전조 (config.OHT_ALERT)")
        hs = [h for h in snap["hotspots"] if h["kind"] == "cluster"]
        self.assertTrue(hs and hs[0]["stopped"] >= 4, "한 주소에 몰린 JAM 이 정체 묶음으로 잡힌다")
        v = next(x for x in snap["vehicles"] if x["vid"] == "V09000")
        for k in ("x", "y", "state", "isFull", "vhlCycle", "currentNode", "nextNode", "missSec", "carrierId"):
            self.assertIn(k, v)
        self.assertEqual((snap["state"], snap["date"]), ("playing", "LIVE"))

    def _last_report(self, m, t):
        sec = int(t.timestamp())
        while (sec + m["phase"]) % 180:
            sec -= 1
        return datetime.fromtimestamp(sec)

    def test_겹쳐_묻고_같은_줄은_한_번만(self):
        self.warm()
        cur = self.f.cursor
        seen0 = dict(self.f.seen)
        n0 = len(self.calls)
        n = self.step(5)
        _, s, e = self.calls[n0]                         # 이번 조회의 첫 물음 = 새 줄
        self.assertEqual(s, cur - timedelta(seconds=LE.OVERLAP_SEC), "늦게 들어온 줄을 받으려고 겹쳐 묻는다")
        newer = sum(1 for r in self.w.rows(s, e)
                    if LE.parse_time(r["_time"]) > seen0.get(r["VEHICLE"], datetime.min))
        self.assertEqual(n, newer, "겹친 부분은 다시 얹지 않는다")

    def test_밀렸으면_조금씩_따라잡는다(self):
        self.warm()
        self.now[0] += timedelta(seconds=300)            # 5분 밀림 (MAX_GAP 안)
        cur = self.f.cursor
        n0 = len(self.calls)
        self.f.poll_once()
        _, s, e = self.calls[n0]
        self.assertEqual(s, cur - timedelta(seconds=LE.OVERLAP_SEC))
        self.assertLessEqual((e - s).total_seconds(), LE.STEP_Q_SEC + LE.OVERLAP_SEC, "한 번에 5분을 묻지 않는다")

    def test_오래_쉬었으면_지금으로_건너뛰고_구멍은_거꾸로(self):
        """정지했다 다시 PLAY — 1분씩 따라잡으면 화면 시각이 여러 번 크게 뛴다
        (고객: "갑자기 늘었다 다시 과거로 가고 그러면 안 돼"). 한 번에 지금으로."""
        self.warm()
        old_cursor = self.f.cursor
        shown0, _ = self.f.current()
        self.now[0] += timedelta(seconds=LE.JUMP_SEC + 60)        # 정지해 있던 동안
        self.wall[0] += LE.JUMP_SEC + 60
        n0 = len(self.calls)
        self.f.poll_once()
        edge = self.now[0] - timedelta(seconds=LE.EDGE_SEC)
        _, s, e = self.calls[n0]
        self.assertEqual(e, edge, "지금까지 묻는다 (밀린 1분부터가 아니라)")
        self.assertEqual(s, edge - timedelta(seconds=self.f.step))
        self.assertTrue(self.f.status["jumped"])
        _, bs, be = self.calls[n0 + 1]
        self.assertEqual(be, s, "구멍은 거꾸로 채운다 — 건너뛴 시작에서 뒤로")
        for _ in range(6):
            self.step(5)
        self.assertLessEqual(self.f.back_to, old_cursor, "건너뛴 구멍을 다 채웠다")
        t, _ = self.f.current()
        self.assertGreater(t, shown0)
        seen = [t]
        for _ in range(6):                                          # 그 뒤로는 차례로, 뒤로 안 간다
            self.wall[0] += 1
            seen.append(self.f.current()[0])
        self.assertEqual(seen, sorted(seen))

    def test_적재가_늦은_것은_건너뛰지_않는다(self):
        """계속 묻고 있는데 로그프레소 적재만 늦으면(데이터 시각이 뒤처짐) 건너뛰지 않는다 —
        건너뛰면 아직 안 들어온 '지금' 만 묻다가 화면이 멈춘다."""
        self.warm()
        self.now[0] += timedelta(seconds=LE.JUMP_SEC + 60)        # 데이터만 밀림 (벽시계는 그대로)
        self.f.poll_once()
        self.assertFalse(self.f.status["jumped"])

    def test_늦게_온_옛_줄은_버린다(self):
        self.warm()
        before = dict(self.f.state["V09000"])
        old = self.w.rows(T0 - timedelta(seconds=60), T0 - timedelta(seconds=58))
        self.assertEqual(self.f._ingest([r for r in old if r["VEHICLE"] == "V09000"]), 0)
        self.assertEqual(self.f.state["V09000"]["currentNode"], before["currentNode"])

    def test_오래_끊겼으면_처음부터(self):
        self.f.poll_once()
        self.now[0] += timedelta(seconds=LE.MAX_GAP_SEC + 60)
        n0 = len(self.calls)
        self.f.poll_once()
        _, s, e = self.calls[n0]
        self.assertEqual(e, self.now[0] - timedelta(seconds=LE.EDGE_SEC), "끊긴 뒤엔 지금부터 다시")
        self.assertTrue(self.f.status["warm"])

    def test_부드럽게_늦춰서_차례로(self):
        self.warm()
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
        self.warm()
        for _ in range(50):
            self.step(5)
        span = (self.f.frames[-1][0] - self.f.frames[0][0]).total_seconds()
        self.assertLessEqual(span, LE.KEEP_SEC)

    def test_실패하면_적고_천천히_폭은_반으로(self):
        def boom(*a):
            raise RuntimeError("HTTP 500 테스트")
        self.f.fetch = boom
        w1 = self.f.tick()
        self.assertEqual(self.f.step, LE.STEP_Q_SEC // 2, "실패하면 묻는 폭을 반으로")
        w2 = self.f.tick()
        self.assertGreater(w2, w1)
        self.assertLessEqual(self.f.tick(), 60.0)
        self.assertGreaterEqual(self.f.step, 10, "폭은 10초 밑으로 안 줄인다")
        info = self.f.info()
        self.assertIn("500", info["error"])
        self.assertEqual(info["fails"], 3)
        self.f.fetch = self.fetch
        self.assertEqual(self.f.tick(), LE.POLL_SEC)
        self.assertIsNone(self.f.info()["error"], "다시 되면 오류를 지운다")
        self.assertGreater(self.f.step, 10, "되면 다시 넓힌다")

    def test_끊긴_응답은_받은_데까지(self):
        """현장: IncompleteRead(801577 bytes read) — 끊긴 데까지 쓰고 다음엔 거기서부터 묻는다."""
        def cut_fetch(table, s, e):
            self.calls.append((table, s, e))
            rows = self.w.rows(s, min(e, self.now[0]))
            out = LE.Rows(rows[:len(rows) // 2])        # 앞 절반만 받았다
            out.cut, out.cut_bytes = True, 123456
            return out
        self.f.fetch = cut_fetch
        self.f.poll_once()
        self.assertTrue(self.f.frames, "끊겼어도 받은 데까지 보인다")
        self.assertGreaterEqual(self.f.status["cuts"], 1)
        cur = self.f.cursor
        self.assertLess(cur, T0 - timedelta(seconds=LE.EDGE_SEC + 10), "끊긴 데까지만 받았다")
        self.f.fetch = self.fetch
        n0 = len(self.calls)
        self.step(5)
        self.assertEqual(self.calls[n0][1], cur - timedelta(seconds=LE.OVERLAP_SEC),
                         "다음엔 끊긴 데서부터 이어 묻는다")

    def test_PLAY_를_눌러야_돈다(self):
        """저절로 켜지거나 멈추지 않는다 — [▶ 실시간 PLAY] · [■ 정지] 로만."""
        f = self.f
        f.tick = lambda: 0.05
        self.assertFalse(f.playing)
        self.assertFalse(f.running())
        f.touch()
        self.assertFalse(f.running(), "보고 있다는 표시만으로는 안 켜진다")
        f.play()
        time.sleep(0.2)
        self.assertTrue(f.running())
        f.stop()
        for _ in range(50):
            if not f.running():
                break
            time.sleep(0.05)
        self.assertFalse(f.running(), "정지를 누르면 멈춘다")
        with open(os.path.join(LIVE, "live_engine.py"), encoding="utf-8") as fh:
            self.assertNotIn("보는 사람이 없어 조회를 멈춥니다", fh.read(), "저절로 멈추는 동작은 없앴다")


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
        cls.p = _spawn("mock_logpresso.py", cls.port)
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

    def setUp(self):
        _get(self.port, "/mock/cut?bytes=0")

    def test_지금_줄을_받는다(self):
        self.LQ.API_KEY = KEY
        now = datetime.now()
        rows = LE.fetch_rows("oht_data_m16br", now - timedelta(seconds=10), now)
        self.assertTrue(rows)
        self.assertFalse(rows.cut)
        self.assertTrue(set(rows[0]) >= {"_time", "VEHICLE", "ADDRESS", "DISTANCE", "NEXT_ADDRESS", "STATUS"})
        self.assertEqual(LE.server_of("oht_data_m16br"), f"127.0.0.1:{self.port}")

    def test_상세_쿼리_그대로(self):
        self.LQ.API_KEY = KEY
        now = datetime.now()
        LE.fetch_rows("oht_data_m14a", now - timedelta(seconds=3), now)
        q = json.loads(_get(self.port, "/mock/hits")[1])["last_q"]
        self.assertIn("oht_data_m14a", q)
        self.assertIn('search MSG_ID == "2"', q, "재생판 '상세' 쿼리와 같다")
        self.assertNotIn("remote", q, "운영은 remote 로 감싸지 않는다")

    def test_응답이_중간에_끊기면_받은_데까지(self):
        """현장 오류 IncompleteRead 를 흉내 낸다 — 실패로 버리지 않고 받은 줄을 쓴다."""
        self.LQ.API_KEY = KEY
        now = datetime.now()
        a, b = now - timedelta(seconds=60), now - timedelta(seconds=30)
        full = LE.fetch_rows("oht_data_m16br", a, b)
        _get(self.port, "/mock/cut?bytes=3000")
        part = LE.fetch_rows("oht_data_m16br", a, b)
        self.assertTrue(part.cut, "끊긴 것을 안다")
        self.assertTrue(0 < len(part) < len(full), (len(part), len(full)))
        self.assertEqual(part[-1], full[len(part) - 1], "마지막 줄도 온전하다 (반쯤 잘린 줄은 버렸다)")

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


class 서버(unittest.TestCase):
    """main.py — 표준 파이썬 서버. 로그프레소 · 관제는 가짜, 화면은 월드모델파생 것 그대로."""

    @classmethod
    def setUpClass(cls):
        cls.mport, cls.gport = _free_port(), _free_port()
        cls.mock = _spawn("mock_logpresso.py", cls.mport)
        cls.gw = _spawn("mock_gwanje.py", cls.gport)
        cls.env = {k: os.environ.get(k) for k in ("LP_HOST", "LP_PORT", "GWANJE_URL")}
        os.environ["LP_HOST"], os.environ["LP_PORT"] = "127.0.0.1", str(cls.mport)
        os.environ["GWANJE_URL"] = f"http://127.0.0.1:{cls.gport}"
        cls.LQ = LE._lq()
        cls.key0 = cls.LQ.API_KEY
        cls.LQ.API_KEY = KEY
        # ★이름이 같은 월드모델파생/main.py 와 헷갈리지 않게 파일로 읽는다
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
        cls.srv.server_close()
        with LE._FL:
            feeds = list(LE._FEEDS.values())
        for f in feeds:
            f.stop()
        for p in (cls.mock, cls.gw):
            p.kill()
            p.wait()
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
        return r.status, dict(r.getheaders()), r.read()

    def cookie(self, path="/api/fabs"):
        _, h, _ = self.req("GET", path)
        return h["Set-Cookie"].split(";")[0]

    def test_화면은_월드모델파생_그대로_조각_둘(self):
        st, h, body = self.req("GET", "/")
        self.assertEqual(st, 200)
        html = body.decode("utf-8")
        with open(os.path.join(LE.WM_DIR, "dashboard.html"), encoding="utf-8") as f:
            orig = f.read()
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

    def test_PLAY_를_눌러야_묻고_정지하면_멈춘다(self):
        ck = self.cookie()
        st, _, b = self.req("POST", "/api/fab/select", {"fab": "M16A", "prefix": "BR"}, ck)
        self.assertEqual(json.loads(b)["table"], "oht_data_m16br")
        snap = json.loads(self.req("GET", "/api/live/snapshot", cookie=ck)[2])
        self.assertFalse(snap["live"]["me_playing"], "열기만 해서는 안 묻는다")
        L = json.loads(self.req("POST", "/api/live/cmd", {"action": "play"}, ck)[2])
        self.assertTrue(L["playing"])
        self.assertTrue(L["me_playing"])
        for _ in range(80):
            snap = json.loads(self.req("GET", "/api/live/snapshot", cookie=ck)[2])
            if snap.get("vehicles"):
                break
            time.sleep(0.25)
        self.assertTrue(snap["vehicles"], "PLAY 하면 차가 올라온다")
        L = snap["live"]
        self.assertEqual(L["server"], f"127.0.0.1:{self.mport}")
        self.assertEqual(L["key"], "…" + KEY[-4:])
        self.assertIsNone(L["error"])
        self.assertNotIn(KEY, json.dumps(snap), "키를 화면에 내주지 않는다")
        L = json.loads(self.req("POST", "/api/live/cmd", {"action": "stop"}, ck)[2])
        self.assertFalse(L["playing"], "정지하면 멈춘다")

    def test_FAB_을_옮기면_앞_FAB_은_멈춘다(self):
        """보는 FAB 하나만 묻는다 — "전부 다 조회하면 안 되니까"."""
        ck = self.cookie()
        self.req("POST", "/api/fab/select", {"fab": "M14A", "prefix": "A"}, ck)
        self.req("POST", "/api/live/cmd", {"action": "play"}, ck)
        self.assertTrue(LE.feed_for("M14A", "A").playing)
        self.req("POST", "/api/fab/select", {"fab": "M16B", "prefix": "B"}, ck)
        self.assertFalse(LE.feed_for("M14A", "A").playing, "앞 FAB 은 멈춘다")
        self.assertTrue(LE.feed_for("M16B", "B").playing, "PLAY 중이었으면 새 FAB 으로 옮겨 PLAY")
        self.req("POST", "/api/live/cmd", {"action": "stop"}, ck)

    def test_다른_화면이_보고_있으면_안_멈춘다(self):
        a, b = self.cookie(), self.cookie()
        for ck in (a, b):
            self.req("POST", "/api/fab/select", {"fab": "M16A", "prefix": "A"}, ck)
            self.req("POST", "/api/live/cmd", {"action": "play"}, ck)
        self.req("POST", "/api/live/cmd", {"action": "stop"}, a)
        self.assertTrue(LE.feed_for("M16A", "A").playing, "b 가 아직 PLAY 중이다")
        self.req("POST", "/api/live/cmd", {"action": "stop"}, b)
        self.assertFalse(LE.feed_for("M16A", "A").playing)

    def test_모르는_명령은_거절(self):
        st, _, _ = self.req("POST", "/api/live/cmd", {"action": "jump"})
        self.assertEqual(st, 400)

    def test_주소로_지도를_고른다(self):
        ck = self.cookie("/?fab=M16B&prefix=B")
        st, _, b = self.req("GET", "/api/fabs", cookie=ck)
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
            self.assertEqual(self.req("GET", bad)[0], 404, bad)

    def test_모르는_지도는_거절(self):
        st, _, _ = self.req("POST", "/api/fab/select", {"fab": "X", "prefix": "Y"})
        self.assertEqual(st, 400)

    # ── 관제 스코어 중계 ──
    def test_스코어는_관제_것을_그_FAB_으로(self):
        ck = self.cookie()
        self.req("POST", "/api/fab/select", {"fab": "M16A", "prefix": "BR"}, ck)
        d = json.loads(self.req("GET", "/api/score/feed?limit=30", cookie=ck)[2])
        self.assertTrue(d["ok"], d)
        self.assertEqual(d["sys"], "M16HUB", "허브룸 지도 → 관제 M16HUB")
        self.assertEqual(len(d["rows"]), 30)
        r = d["rows"][0]
        for k in ("at", "datetime", "score", "level", "reason", "metrics", "hi_fab"):
            self.assertIn(k, r)
        self.assertNotIn("m", r, "무거운 칸은 빼고 넘긴다")
        self.assertNotIn("groups", d)
        self.assertEqual(d["fab_cuts"]["M16HUB"]["warn"], 60)
        self.assertTrue(any(x.get("hid") for x in d["rows"]), "HID_JAM · RET 줄도 같이 온다")
        last = json.loads(_get(self.gport, "/mock/last")[1])
        self.assertEqual((last["path"], last["q"]["sys"], last["q"]["limit"]), ("/api/feed", "M16HUB", "30"))

    def test_그래프_기여도_레포트도_관제_것(self):
        ck = self.cookie()
        self.req("POST", "/api/fab/select", {"fab": "M14B", "prefix": "A"}, ck)
        at = "2026-10-06T10:24:00"
        st, h, body = self.req("GET", f"/api/score/graph?at={at}&minutes=120&theme=light", cookie=ck)
        self.assertEqual(st, 200)
        self.assertTrue(h["Content-Type"].startswith("image/svg+xml"))
        svg = body.decode("utf-8")
        self.assertIn('data-sys="M14B"', svg, "그 FAB 의 관제 시스템으로 묻는다")
        self.assertIn('data-theme="light"', svg)
        self.assertIn('data-min="120"', svg)
        self.assertIn(f'data-at="{at}"', svg, "누르면 그 분을 고정할 자리(ghit)가 그대로 온다")
        st, _, body = self.req("GET", f"/api/score/contrib?at={at}", cookie=ck)
        self.assertIn("기여도", body.decode("utf-8"))
        name = "PROBLEM_MAP_M14B_20261006_1024_WARNING.html"
        st, h, body = self.req("GET", f"/api/score/report?day=20261006&name={name}", cookie=ck)
        self.assertEqual(st, 200)
        self.assertIn("attachment", h.get("Content-Disposition", ""), "내려받기로 온다")

    def test_관제가_꺼져_있으면_알려_준다(self):
        old = os.environ["GWANJE_URL"]
        os.environ["GWANJE_URL"] = f"http://127.0.0.1:{_free_port()}"
        try:
            d = json.loads(self.req("GET", "/api/score/feed")[2])
            self.assertFalse(d["ok"])
            self.assertIn("관제", d["error"])
            self.assertIn("켜져 있는지", d["error"])
        finally:
            os.environ["GWANJE_URL"] = old

    def test_관제_주소는_config_의_포트(self):
        old = os.environ.pop("GWANJE_URL")
        try:
            self.assertTrue(self.M.gwanje_base().startswith("http://127.0.0.1:"))
        finally:
            os.environ["GWANJE_URL"] = old


class 화면_조각(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(LIVE, "live_ui.js"), encoding="utf-8") as f:
            cls.js = f.read()

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
""" + js + """
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

    def test_PLAY_일시정지_정지_단추(self):
        """재생판 단추 자리·모양 그대로, 하는 일만 실시간으로."""
        for need in ("&#9654; 실시간 PLAY", "btnPlay.onclick = function () { setMode('play'); }",
                     "btnPause.onclick = function () { setMode('pause'); }",
                     "btnStop.onclick = function () { setMode('stop'); }",
                     "post('/api/live/cmd', { action: m })",
                     "if (MODE === 'play' && d && d.time) {"):
            self.assertIn(need, self.js)
        self.assertIn("if (!LAST || LAST.time !== d.time) LAST_AT = Date.now();", self.js,
                      "시계 기준은 장면이 바뀔 때만 — 아니면 시계가 그 초에 붙는다")
        # ★시계는 절대 뒤로 안 간다 (고객: "늘었다 다시 과거로 가면 안 돼")
        self.assertIn("if (t < SHOW) t = SHOW;", self.js)
        i = self.js.index("origUpdate(d);")
        self.assertIn("tickClock();", self.js[i:i + 400],
                      "화면 함수가 시계를 장면 시각으로 되돌린 직후 같은 차례에 다시 쓴다 (깜빡이며 뒤로 가던 것)")
        self.assertIn("SHOW = 0;", self.js, "FAB 을 바꾸면 시계를 새로")
        # OHT 시각 · 스코어 시각을 이름을 붙여 따로
        self.assertIn("cap.textContent = 'OHT';", self.js)
        self.assertIn("p.push('OHT <b", self.js)
        self.assertIn("el.textContent = '스코어 ' + (r.time || '')", self.js)
        for gone in ("slider-container", "frame-display", "#topbar .speed-btn", "#topbar .tb-query"):
            self.assertIn(gone, self.js, gone + " 를 숨긴다")

    def test_스코어_탭과_그래프_창(self):
        for need in ("tb.textContent = '스코어'", "window.switchRTab = function (tab)",
                     "/api/score/feed?limit=90", "/api/score/graph?at=", "/api/score/contrib?at=",
                     "'/api/score/report?day='", "el.ondblclick = function () { openGraph(el.dataset.at); }",
                     "#lg-body svg .ghit", "class=\"ms-card\"", "risk risk-"):
            self.assertIn(need, self.js)
        # 등급 색은 화면에 있던 것만 — risk-* 칩 · 차량 목록의 초록·주황·빨강
        for c in ("'NORMAL'", "'WARNING'", "'DANGER'", "'CRITICAL'", "#22c55e", "#f59e0b", "#ef4444"):
            self.assertIn(c, self.js)


if __name__ == "__main__":
    unittest.main()
