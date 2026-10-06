#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""실시간 모드 시험 — 리플레이와 한 서버(10005)에 합친 판.
가짜 로그프레소(tests/mock_logpresso.py) · 가짜 관제(tests/mock_gwanje.py) 를 띄워서 본다.

    cd 월드모델파생 && python -m unittest discover -s tests

  · 피드 · 지도와_테이블 · 로그프레소   live_engine.py (로그프레소 '지금' → 월드모델 장면)
  · 누가_PLAY_중인가 · 장면_글자       여럿이 볼 때 — PLAY 는 화면(세션)마다, 피드 · 장면 글자는 FAB 마다 하나
  · 관제_스코어                        gwanje_score.py (관제 점수를 그대로 중계)
  · 서버_한_벌                         main.py 를 통째로 읽어 핸들러 · 웹소켓을 직접 부른다 (tests/main_harness.py)
  · 서버_연결 · 화면                   main.py · dashboard.html · static/js/live_mode.js (tests/live_mode.js)
진짜 데이터는 하나도 없다 (차 번호 · 운반물 · 점수 다 지어낸 것).
"""
import http.client
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
for p in (APP, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)
try:                                     # 이 상자에 pandas 가 없으면 빈 것으로 (logpresso_query import 용)
    import pandas  # noqa: F401
except ImportError:
    sys.path.insert(0, os.path.join(HERE, "_stub"))

KEY = "dummy-key"
os.environ.setdefault("MOCK_LP_KEY", KEY)

import gwanje_score as GS                # noqa: E402
import live_engine as LE                 # noqa: E402
from mock_logpresso import World         # noqa: E402

T0 = datetime(2026, 10, 6, 10, 0, 0)


def _read(*p):
    with open(os.path.join(APP, *p), encoding="utf-8") as fh:
        return fh.read()


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


def _node():
    return shutil.which("node")


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
        self.assertNotIn("보는 사람이 없어 조회를 멈춥니다", _read("live_engine.py"), "저절로 멈추는 동작은 없앴다")


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


def _quiet(fab, prefix):
    """묻지 않는 피드 — PLAY 해도 로그프레소에 안 간다 (누가 PLAY 중인지만 본다)."""
    f = LE.feed_for(fab, prefix)
    f.tick = lambda: 0.05
    return f


class 누가_PLAY_중인가(unittest.TestCase):
    """보는 FAB 하나만 묻는다 · 여럿이 같은 FAB 을 보면 피드 하나를 같이 쓴다.
    고객: "전부 다 조회하면 안 되니까" · "여러 사람이 접속할 거야"."""

    KEYS = (("M14A", "A"), ("M16A", "A"), ("M16A", "BR"), ("M16B", "B"))

    def setUp(self):
        self.fs = {k: _quiet(*k) for k in self.KEYS}

    def tearDown(self):
        for sid in ("a", "b", "c"):
            LE.stop(sid)
        for f in self.fs.values():
            f.stop()

    def test_PLAY_를_눌러야_돌고_정지하면_멈춘다(self):
        f = self.fs[("M16A", "BR")]
        LE.feed_for("M16A", "BR")
        self.assertFalse(f.playing, "보기만 해서는 안 묻는다")
        LE.play("a", "M16A", "BR", "시험")
        self.assertTrue(f.playing)
        self.assertEqual(LE.playing_key("a"), ("M16A", "BR"))
        self.assertTrue(LE.live_info("a", "M16A", "BR")["me_playing"])
        self.assertFalse(LE.live_info("b", "M16A", "BR")["me_playing"], "남의 PLAY 는 내 것이 아니다")
        LE.stop("a")
        self.assertFalse(f.playing, "정지하면 멈춘다")
        self.assertIsNone(LE.playing_key("a"))

    def test_FAB_을_옮기면_앞_FAB_은_멈춘다(self):
        LE.play("a", "M14A", "A")
        LE.play("a", "M16B", "B", "지도 바꿈")
        self.assertFalse(self.fs[("M14A", "A")].playing, "보는 FAB 하나만 — 앞 FAB 은 멈춘다")
        self.assertTrue(self.fs[("M16B", "B")].playing)

    def test_여럿이_같은_FAB_이면_한_사람이_멈춰도_돈다(self):
        for sid in ("a", "b", "c"):
            LE.play(sid, "M16A", "A")
        self.assertIs(LE.feed_for("M16A", "A"), self.fs[("M16A", "A")], "FAB 마다 피드 하나 — 사람 수만큼 안 묻는다")
        LE.stop("a")
        self.assertTrue(self.fs[("M16A", "A")].playing, "b · c 가 아직 PLAY 중이다")
        LE.play("b", "M14A", "A")
        self.assertTrue(self.fs[("M16A", "A")].playing, "c 가 아직 PLAY 중이다")
        LE.stop("c")
        self.assertFalse(self.fs[("M16A", "A")].playing, "아무도 안 남으면 멈춘다")
        self.assertTrue(self.fs[("M14A", "A")].playing)
        self.assertEqual(LE.status()["players"], {"M14A/A": 1})


class 장면_글자(unittest.TestCase):
    """웹소켓이 1초마다 보내는 글자 — 여럿이 보면 장면은 한 번만 글자로 바꾸고 상태줄만 사람마다."""

    def test_장면은_한_번_상태줄은_사람마다(self):
        w = World("M16A_BR")
        f = LE.LiveFeed("M16A", "BR", fetch=lambda t, s, e: LE.Rows(w.rows(s, min(e, T0))),
                        clock=lambda: T0, wall=lambda: 1000.0)
        f.poll_once()
        key = ("M16A", "BR")
        with LE._FL:
            old = LE._FEEDS.get(key)
            LE._FEEDS[key] = f
        with LE._PL:
            LE._PLAYERS[key] = {"a"}
        try:
            a = json.loads(LE.snapshot_json("a", "M16A", "BR"))
            hit = f.json_cache
            b = json.loads(LE.snapshot_json("b", "M16A", "BR"))
            self.assertIs(f.json_cache, hit, "같은 칸이면 글자를 다시 만들지 않는다")
            self.assertTrue(a["vehicles"])
            self.assertEqual({k: v for k, v in a.items() if k != "live"},
                             {k: v for k, v in b.items() if k != "live"}, "장면은 모두 같다")
            self.assertEqual((a["live"]["me_playing"], b["live"]["me_playing"]), (True, False),
                             "상태줄은 사람마다 — 내가 PLAY 중인지")
            ref = json.loads(json.dumps(LE.snapshot("b", "M16A", "BR"), default=str))
            self.assertEqual(ref, b, "웹소켓 글자 = /api/live/snapshot 과 같은 내용")
        finally:
            with LE._PL:
                LE._PLAYERS.pop(key, None)
            with LE._FL:
                if old is None:
                    LE._FEEDS.pop(key, None)
                else:
                    LE._FEEDS[key] = old


class 관제_스코어(unittest.TestCase):
    """gwanje_score.py — 관제가 매긴 그 FAB 의 점수를 그대로 받아 온다 (여기서 다시 계산하지 않는다)."""

    @classmethod
    def setUpClass(cls):
        cls.gport = _free_port()
        cls.gw = _spawn("mock_gwanje.py", cls.gport)
        cls.old = os.environ.get("GWANJE_URL")
        os.environ["GWANJE_URL"] = f"http://127.0.0.1:{cls.gport}"

    @classmethod
    def tearDownClass(cls):
        cls.gw.kill()
        cls.gw.wait()
        if cls.old is None:
            os.environ.pop("GWANJE_URL", None)
        else:
            os.environ["GWANJE_URL"] = cls.old

    def _last(self):
        return json.loads(_get(self.gport, "/mock/last")[1])

    def test_그_FAB_의_관제_시스템으로(self):
        d = GS.feed("M16A", "BR", 30)
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
        last = self._last()
        self.assertEqual((last["path"], last["q"]["sys"], last["q"]["limit"]), ("/api/feed", "M16HUB", "30"))

    def test_여럿이_봐도_관제에는_한_번(self):
        """여럿이 스코어 탭을 열어 두어도 5초 안의 같은 물음은 관제에 다시 안 간다."""
        GS.feed("M16B", "B", 17)
        n0 = self._last()["n"]
        for _ in range(5):
            self.assertTrue(GS.feed("M16B", "B", 17)["ok"])
        self.assertEqual(self._last()["n"], n0, "같은 것을 또 물었다")

    def test_그래프_기여도_레포트(self):
        at = "2026-10-06T10:24:00"
        st, ct, body, extra = GS.passthrough("M14B", "A", "graph", {"at": at, "minutes": "120", "theme": "light"})
        self.assertEqual(st, 200)
        self.assertTrue(ct.startswith("image/svg+xml"))
        svg = body.decode("utf-8")
        for need in ('data-sys="M14B"', 'data-theme="light"', 'data-min="120"', f'data-at="{at}"'):
            self.assertIn(need, svg, "그 FAB 의 관제 시스템 · 고른 폭 · 누르면 그 분을 고정할 자리(ghit)")
        st, ct, body, extra = GS.passthrough("M14B", "A", "contrib", {"at": at})
        self.assertIn("기여도", body.decode("utf-8"))
        name = "PROBLEM_MAP_M14B_20261006_1024_WARNING.html"
        st, ct, body, extra = GS.passthrough("M14B", "A", "report", {"day": "20261006", "name": name})
        self.assertEqual(st, 200)
        self.assertIn("attachment", extra.get("Content-Disposition", ""), "내려받기로 온다")

    def test_짝이_없는_지도(self):
        d = GS.feed("M16A", "E", 10)
        self.assertFalse(d["ok"])
        self.assertIn("짝이 없습니다", d["error"])
        self.assertEqual(GS.passthrough("M16A", "E", "graph", {})[0], 404)

    def test_관제가_꺼져_있으면_알려_준다(self):
        os.environ["GWANJE_URL"] = f"http://127.0.0.1:{_free_port()}"
        try:
            d = GS.feed("M16A", "BR", 31)
            self.assertFalse(d["ok"])
            self.assertIn("관제", d["error"])
            self.assertIn("켜져 있는지", d["error"])
            self.assertEqual(GS.passthrough("M16A", "BR", "contrib", {"at": "x"})[0], 502)
        finally:
            os.environ["GWANJE_URL"] = f"http://127.0.0.1:{self.gport}"

    def test_관제_주소는_config_의_포트(self):
        os.environ.pop("GWANJE_URL")
        try:
            self.assertTrue(GS.base().startswith("http://127.0.0.1:"))
        finally:
            os.environ["GWANJE_URL"] = f"http://127.0.0.1:{self.gport}"


class 서버_한_벌(unittest.TestCase):
    """main.py 를 통째로 읽어 핸들러 · 웹소켓을 직접 부른다 (tests/main_harness.py).
    ★FastAPI 가 없어도 돈다 — 시험은 배포 폴더를 하나 만들어(지도 캐시 · 가짜 layout.zip) 거기서 띄운다."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="wm_main")
        for f in os.listdir(APP):
            if f.endswith(".py") or f == "dashboard.html":
                shutil.copy2(os.path.join(APP, f), cls.tmp)
        os.makedirs(os.path.join(cls.tmp, "OHT_MAP"))
        src, dst = os.path.join(APP, "OHT_MAP", "cache"), os.path.join(cls.tmp, "OHT_MAP", "cache")
        try:
            os.symlink(src, dst)
        except OSError:                                 # 윈도는 권한이 없으면 링크를 못 만든다
            shutil.copytree(src, dst)
        for fab, pre in (("M14A", "A"), ("M14B", "A"), ("M16A", "A"), ("M16A", "BR"), ("M16B", "B")):
            d = os.path.join(cls.tmp, "OHT_MAP", "MAP", fab)
            os.makedirs(d, exist_ok=True)
            z = os.path.join(d, pre + ".layout.zip")
            zipfile.ZipFile(z, "w").close()
            os.utime(z, (946684800, 946684800))         # 2000-01-01 — 캐시가 더 새것이라 캐시를 그대로 쓴다
        cls.lport, cls.gport = _free_port(), _free_port()
        cls.lp = _spawn("mock_logpresso.py", cls.lport)
        cls.gw = _spawn("mock_gwanje.py", cls.gport)
        r = subprocess.run([sys.executable, os.path.join(HERE, "main_harness.py"), cls.tmp, str(cls.lport),
                            str(cls.gport)], capture_output=True, text=True, timeout=240,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        cls.log = (r.stdout or "") + (r.stderr or "")
        try:
            cls.R = json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            cls.R = None

    @classmethod
    def tearDownClass(cls):
        for p in (cls.lp, cls.gw):
            p.kill()
            p.wait()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        if self.R is None:
            self.fail("main_harness 가 결과를 못 냈다:\n" + self.log[-3000:])

    def test_FAB_고르고_PLAY_하면_차가_올라온다(self):
        R = self.R
        self.assertEqual(R["select"], [200, "M16A", "BR"])
        self.assertEqual(R["before_play"], [False, False, "oht_data_m16br"], "열기만 해서는 안 묻는다")
        self.assertEqual(R["play"], [200, True, True])
        self.assertGreater(R["vehicles"], 30)
        self.assertEqual(R["key_shown"], "…" + KEY[-4:])
        self.assertFalse(R["key_leak"], "키를 화면에 내주지 않는다")

    def test_여럿이_같은_FAB_을_보면(self):
        self.assertTrue(self.R["after_a_stop"], "B 가 아직 PLAY 중이다 — A 의 정지가 B 화면을 멈추면 안 된다")
        self.assertEqual(self.R["after_b_stop"], [False, False])

    def test_PLAY_중에_FAB_을_바꾸면_따라간다(self):
        self.assertEqual(self.R["moved"], [False, True, ["M16B", "B"]])

    def test_모르는_명령은_거절(self):
        self.assertEqual(self.R["bad_cmd"], 400)
        self.assertEqual(self.R["status"], [["M16B/B"], True])

    def test_관제_스코어_중계(self):
        self.assertEqual(self.R["score"], [200, True, "M16HUB", 30])
        self.assertEqual(self.R["graph"], [200, True])
        self.assertEqual(self.R["report"], [200, True])

    def test_웹소켓_하나로_두_모드(self):
        """리플레이 장면 둘 → 실시간 알림 → 실시간 장면 → (실시간 중 재생 명령은 버림) → 리플레이로."""
        R = self.R
        self.assertEqual(R["ws_kinds"], "RRLLLLLLRRRR")
        self.assertEqual(R["replay_state_after_live_play"], "paused", "실시간 중에 온 재생 명령은 버린다")
        self.assertEqual(R["ws_live_shape"], ["live", "time_short", "vehicleStats", "vehicles"])
        self.assertEqual(R["ws_live_fab"], ["M16A", "BR"])
        self.assertEqual((R["ws_open_during"], R["ws_open_after"]), (1, 0),
                         "보고 있는 동안만 '보는 사람' 으로 센다 (수 한도로 안 치운다)")

    def test_세션을_치우면_PLAY_를_놓는다(self):
        self.assertEqual(self.R["close"], [["M16A", "BR"], None])


class 서버_연결(unittest.TestCase):
    """main.py 글자 — 위 서버_한_벌 이 못 보는 것 (HTTP 길 · 다른 실 · 같은 포트)."""

    @classmethod
    def setUpClass(cls):
        cls.m = _read("main.py")

    def test_길이_있다(self):
        for r in ('@app.get("/api/live/snapshot")', '@app.get("/api/live/status")', '@app.post("/api/live/cmd")',
                  '@app.get("/api/score/feed")', '@app.get("/api/score/graph")', '@app.get("/api/score/contrib")',
                  '@app.get("/api/score/report")'):
            self.assertIn(r, self.m)

    def test_오래_걸리는_것은_다른_실에서(self):
        """지도 읽기 · 로그프레소 · 관제 묻기를 그냥 부르면 그동안 서버 전체(남의 웹소켓까지)가 멎는다."""
        for need in ("await run_in_threadpool(LE.play, s.sid, s.fab, s.prefix", "await run_in_threadpool(GS.feed",
                     "await run_in_threadpool(GS.passthrough", "await run_in_threadpool(LE.snapshot_json",
                     "await run_in_threadpool(LE.play, s.sid, fab, prefix"):
            self.assertIn(need, self.m)

    def test_지도는_리플레이와_한_벌(self):
        self.assertIn("LE.use_layouts(get_layout)", self.m)

    def test_같은_포트(self):
        """리플레이 · 실시간이 한 서버 · 한 포트 — 실시간용으로 따로 띄우는 서버가 없다."""
        self.assertIn("SERVER_PORT = 10005", _read("config.py"))
        self.assertEqual(self.m.count("uvicorn.run("), 1)
        self.assertIn("uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)", self.m)
        self.assertNotIn("LIVE_PORT", self.m)
        self.assertFalse(os.path.isdir(os.path.join(APP, "..", "월드모델파생_실시간")),
                         "따로 띄우던 실시간판은 합쳤다 — 두 벌이 남으면 어느 쪽을 고칠지 헷갈린다")

    def test_세션을_치우면_PLAY_를_놓는다(self):
        i = self.m.index("    def close(self):")
        self.assertIn("LE.stop(self.sid", self.m[i:i + 700])

    def test_보고_있는_사람은_수_한도로_안_치운다(self):
        self.assertIn("_s.ws += 1", self.m)
        self.assertIn("_s.ws = max(0, _s.ws - 1)", self.m)
        i = self.m.index("def _reap_locked(")
        self.assertIn('getattr(v, "ws", 0) > 0 or v.sid == keep', self.m[i:i + 1500])
        self.assertIn("gone = _reap_locked(keep=s.sid)", self.m, "방금 온 사람을 그 자리에서 치우면 안 된다")


class 화면(unittest.TestCase):
    """dashboard.html — [리플레이 | 실시간]. 하는 일은 tests/live_mode.js 가 가짜 화면 위에서 돌려 본다."""

    @classmethod
    def setUpClass(cls):
        cls.h = _read("dashboard.html")
        cls.js = _read("static", "js", "live_mode.js")

    def test_모드_단추와_숨김(self):
        self.assertIn('<button id="app-replay" class="toggle-btn on" onclick="setAppMode(\'replay\')">', self.h)
        self.assertIn('<button id="app-live" class="toggle-btn" onclick="setAppMode(\'live\')">', self.h)
        self.assertIn('body[data-app="live"] .replay-only { display:none !important; }', self.h)
        self.assertIn('body:not([data-app="live"]) .live-only { display:none !important; }', self.h)
        for frag in ('class="tb-group tb-query replay-only"', '<div class="tb-group tb-seg replay-only" title="재생 속도">',
                     '<span id="frame-display" class="replay-only">', '<div id="slider-container" class="replay-only">',
                     '<button class="replay-only" onclick="sendCmd(\'play\')">'):
            self.assertIn(frag, self.h, "리플레이에만 있는 것: " + frag)
        for frag in ('id="live-play" onclick="liveCmd(\'play\')"', 'id="live-pause" onclick="liveCmd(\'pause\')"',
                     'id="live-stop" onclick="liveCmd(\'stop\')"', 'class="tb-group live-only" id="live-chip"',
                     'class="rtab live-only" data-rt="score"', '<div id="rtab-score" class="live-only"'):
            self.assertIn(frag, self.h, "실시간에만 있는 것: " + frag)

    def test_실시간_조각을_부른다(self):
        self.assertIn('<script src="/static/js/live_mode.js"></script>', self.h)
        self.assertLess(self.h.index("window.BOOT = bootFabs().then(autoFromQuery)"),
                        self.h.index('<script src="/static/js/live_mode.js">'), "부팅 약속이 먼저 있어야 한다")
        self.assertIn("if (window.LiveMode) LiveMode.wsOpen();", self.h, "다시 붙으면 모드를 다시 알린다")

    def test_OHT_시각_이름(self):
        self.assertIn('body[data-app="live"] #time-display::before { content:\'OHT\';', self.h)

    def test_스코어_탭은_이름으로_고른다(self):
        i = self.h.index("function switchRTab(tab) {")
        body = self.h[i:i + 900]
        self.assertIn("b.dataset.rt === tab", body)
        self.assertNotIn("textContent.includes", body, "글자로 고르면 '스코어' 를 누를 때 HID Zone 이 켜졌다")

    def test_하는_일(self):
        node = _node()
        if not node:
            self.skipTest("node 가 없다")
        r = subprocess.run([node, os.path.join(HERE, "live_mode.js")], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK", r.stdout)

    def test_시계는_뒤로_안_간다(self):
        self.assertIn("if (t < SHOW) t = SHOW;", self.js)
        self.assertIn("if (!LAST || LAST.time !== d.time) LAST_AT = Date.now();", self.js,
                      "시계 기준은 장면이 바뀔 때만 — 아니면 시계가 그 초에 붙는다")

    def test_색은_화면에_있던_것만(self):
        for c in ("'NORMAL'", "'WARNING'", "'DANGER'", "'CRITICAL'", "#22c55e", "#f59e0b", "#ef4444"):
            self.assertIn(c, self.js)


def _rgb(c, bg=None):
    """'#rrggbb' · 'rgba(r,g,b,a)' → (r, g, b) 0~255 (반투명이면 bg 위에 얹은 색)."""
    c = c.strip()
    if c.startswith("#"):
        return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    v = [float(x) for x in re.findall(r"[\d.]+", c)]
    a = v[3] if len(v) > 3 else 1.0
    b = bg or (0, 0, 0)
    return tuple(v[i] * a + b[i] * (1 - a) for i in range(3))


def _contrast(c1, c2):
    def lum(c):
        def ch(x):
            x /= 255.0
            return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
        r, g, b = (ch(x) for x in c)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    a, b = sorted((lum(c1), lum(c2)), reverse=True)
    return (a + 0.05) / (b + 0.05)


class 배경_네_가지(unittest.TestCase):
    """고객: "배경 색상 가능하게 2D, 유사3D, 아이소메트리 배경 가능하게 해라 · 다크, 화이트, 네이비, 고대비"."""

    NAMES = (("dark", "다크"), ("hmi", "화이트"), ("navy", "네이비"), ("contrast", "고대비"))

    @classmethod
    def setUpClass(cls):
        cls.h = _read("dashboard.html")
        m = re.search(r"const MAP_THEMES = \{[\s\S]*?\n\};", cls.h)
        cls.themes = {}
        for name, body in re.findall(r"\n  (\w+):\s*\{([^}]*)\}", m.group(0)):
            cls.themes[name] = dict(re.findall(r"(\w+):'([^']*)'", body))

    def test_단추_넷_설정도_넷(self):
        for t, name in self.NAMES:
            self.assertRegex(self.h, r'data-bg="%s"\s+class="toggle-btn" onclick="setMapBg\(\'%s\'\)"[^>]*>%s<'
                             % (t, t, name))
        m = re.search(r'<select id="ms-mapTheme"[\s\S]*?</select>', self.h)
        self.assertEqual(re.findall(r'<option value="(\w+)"', m.group(0)), [t for t, _ in self.NAMES])

    def test_고르면_바로_바뀌고_남는다(self):
        i = self.h.index("function setMapBg(t) {")
        body = self.h[i:i + 400]
        for need in ("mapSettings.mapTheme = t;", "saveMapSettings();", "applyPageTheme();",
                     "railCacheCanvas = null;", "drawMap();"):
            self.assertIn(need, body)

    def test_세_보기가_같은_배경(self):
        """2D · 유사 3D 는 캔버스 바탕(mapPal().bg), 아이소메트리는 three.js 바탕(background) — 같은 값."""
        for need in ("v3d.setOptions({ dark: isDarkMap(), background: mapPal().bg,",
                     "colors: { state: v3dColors(), background: pal.bg", "mapCtx.fillStyle = mapPal().bg;",
                     "rc.fillStyle = mapPal().bg;", "rc.fillStyle = isDarkMap() ? 'rgba(255,255,255,0.05)' : '#dfe3ea';"):
            self.assertIn(need, self.h)
        self.assertNotIn("mapSettings.mapTheme === 'dark'", self.h,
                         "어두운 바탕은 다크 하나가 아니다 (네이비 · 고대비도) — isDarkMap()")

    def test_레일_글자가_바탕에_묻히지_않는다(self):
        """브릿지 모니터에서 흰 바탕에 흰 글자가 안 보였던 일 — 바탕마다 레일 3:1 · 글자 4.5:1 이상."""
        for t, name in self.NAMES:
            p = self.themes[t]
            bg = _rgb(p["bg"])
            rail = _contrast(_rgb(p["rail"], bg), bg)
            text = _contrast(_rgb(p["text"], bg), bg)
            self.assertGreaterEqual(rail, 3.0, f"{name} 레일 대비 {rail:.1f}")
            self.assertGreaterEqual(text, 4.5, f"{name} 글자 대비 {text:.1f}")

    def test_화면_색도_네_벌(self):
        """맵만 바뀌고 상단 · 패널이 따로 놀면 안 된다 (고객 지적) — 네이비 · 고대비도 변수를 다 채운다."""
        base = set(re.findall(r"(--[\w-]+):", re.search(r"\nbody \{([^}]*)\}", self.h).group(1)))
        for t in ("navy", "contrast"):
            blk = re.search(r'body\[data-theme="%s"\] \{([^}]*)\}' % t, self.h).group(1)
            self.assertEqual(set(re.findall(r"(--[\w-]+):", blk)), base, t + " 에 빠진 변수가 있다")

    def test_관제와_같은_색(self):
        """네이비 · 고대비는 관제 테마 4벌의 색 그대로 — 관제와 같은 화면으로 보이게."""
        g = os.path.join(APP, "..", "..", "static", "dashboard.html")
        if not os.path.isfile(g):
            self.skipTest("관제 화면이 옆에 없다 (월드모델만 따로 놓인 자리)")
        with open(g, encoding="utf-8") as fh:
            gw = fh.read()
        for t, toks in (("navy", ("--bg:#08131F", "--panel:#0E1E30")),
                        ("contrast", ("--bg:#000000", "--panel:#0A0A0A"))):
            theirs = re.search(r':root\[data-theme="%s"\]\{([^}]*)\}' % t, gw).group(1).replace(" ", "")
            mine = re.search(r'body\[data-theme="%s"\] \{([^}]*)\}' % t, self.h).group(1).replace(" ", "")
            for tok in toks:
                self.assertIn(tok, theirs, "관제 색이 바뀌었다 — 여기도 맞춰야 한다: " + tok)
                self.assertIn(tok, mine, t + " 이 관제와 다르다: " + tok)
        self.assertEqual(self.themes["navy"]["bg"], "#0E1E30", "맵 바탕 = 관제 네이비 패널색")
        self.assertEqual(self.themes["contrast"]["bg"], "#000000")


if __name__ == "__main__":
    unittest.main()
