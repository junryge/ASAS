#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""main.py 를 통째로 읽어 핸들러 · 웹소켓을 직접 부른다 — test_live.서버_한_벌 이 따로 띄운다.

    python tests/main_harness.py <배포 폴더> <가짜 로그프레소 포트> <가짜 관제 포트>

★FastAPI 가 없는 자리(이 시험 상자 · 폐쇄망 개발 PC)에서도 main.py 의 **실제 코드**를 돌려 보려는 것.
  FastAPI 가 있으면 진짜를 쓰고, 없으면 아래 _stub() 이 이름만 채운다 — 데코레이터는 함수를 그대로
  돌려주므로(진짜 FastAPI 도 그렇다) 핸들러를 그냥 부르면 된다. HTTP 서버는 안 띄운다.
★배포 폴더는 시험이 만든다 (main.py · 지도 캐시 · 가짜 layout.zip). config 가 그 폴더 기준으로
  OHT_MAP 을 찾으므로, 저장소 폴더를 건드리지 않는다.
★결과는 마지막 줄에 JSON 한 줄. 진짜 데이터는 하나도 없다.
"""
import asyncio
import functools
import json
import os
import sys
import time
import types

ROOT, LP_PORT, GW_PORT = sys.argv[1], sys.argv[2], sys.argv[3]
os.environ.update(LP_HOST="127.0.0.1", LP_PORT=LP_PORT, LP_API_KEY="dummy-key",
                  GWANJE_URL=f"http://127.0.0.1:{GW_PORT}", LIVE_POLL_SEC="1")


def _stub():
    """FastAPI · Starlette · uvicorn 이름만 — 핸들러를 직접 부를 수 있을 만큼."""
    fa = types.ModuleType("fastapi")

    class App:
        def __init__(self, **k):
            pass

        def _deco(self, *a, **k):
            return lambda f: f
        get = post = websocket = middleware = on_event = _deco

        def mount(self, *a, **k):
            pass

    class WebSocketDisconnect(Exception):
        pass

    fa.FastAPI, fa.WebSocketDisconnect = App, WebSocketDisconnect
    fa.WebSocket = fa.Request = object
    fa.Query = lambda default=None, **k: default
    rs = types.ModuleType("fastapi.responses")

    class Response:
        media_type = None

        def __init__(self, content=b"", status_code=200, headers=None, media_type=None):
            self.body = content if isinstance(content, bytes) else str(content).encode("utf-8")
            self.status_code, self.headers = status_code, dict(headers or {})
            self.media_type = media_type or self.media_type

        def set_cookie(self, *a, **k):
            pass

    class JSONResponse(Response):
        media_type = "application/json"

        def __init__(self, content=None, status_code=200, headers=None):
            super().__init__(json.dumps(content, default=str).encode("utf-8"), status_code, headers)

    class HTMLResponse(Response):
        media_type = "text/html; charset=utf-8"

    rs.Response, rs.JSONResponse, rs.HTMLResponse = Response, JSONResponse, HTMLResponse
    sf = types.ModuleType("fastapi.staticfiles")

    class StaticFiles:
        def __init__(self, directory=None, **k):
            pass

    sf.StaticFiles = StaticFiles
    st = types.ModuleType("starlette")
    cc = types.ModuleType("starlette.concurrency")

    async def run_in_threadpool(fn, *a, **k):
        return await asyncio.get_running_loop().run_in_executor(None, functools.partial(fn, *a, **k))

    cc.run_in_threadpool = run_in_threadpool
    uv = types.ModuleType("uvicorn")
    uv.run = lambda *a, **k: None
    sys.modules.update({"fastapi": fa, "fastapi.responses": rs, "fastapi.staticfiles": sf,
                        "starlette": st, "starlette.concurrency": cc, "uvicorn": uv})


try:
    import fastapi  # noqa: F401
except ImportError:
    _stub()
try:
    import pandas  # noqa: F401
except ImportError:                       # logpresso_query 가 맨 위에서 import 한다 (실시간은 안 쓴다)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_stub"))

sys.path.insert(0, ROOT)
import main as M                          # noqa: E402  (배포 폴더의 main.py)


class Req:
    """FastAPI Request 대신 — 핸들러가 쓰는 것만."""

    def __init__(self, sid=None, body=None, q=None):
        self.cookies = {M.SESSION_COOKIE: sid} if sid else {}
        self.state = types.SimpleNamespace()
        self.query_params = dict(q or {})
        self._body = body or {}
        self.url = types.SimpleNamespace(path="/")

    async def json(self):
        return self._body


class WS:
    """가짜 웹소켓 — 보낸 것을 모으고, 정해 둔 명령을 차례로 준다."""

    def __init__(self, sid, script):
        self.cookies = {M.SESSION_COOKIE: sid}
        self.script = list(script)        # [(보낸 장면 수가 이만큼이면, 줄 명령)]
        self.sent = []
        self.ws_during = None

    async def accept(self):
        pass

    async def receive_text(self):
        while True:
            if self.script and len(self.sent) >= self.script[0][0]:
                return json.dumps(self.script.pop(0)[1])
            await asyncio.sleep(0.02)

    async def send_text(self, s):
        self.sent.append(json.loads(s))
        if self.ws_during is None:
            self.ws_during = SESS["A"].ws
        if len(self.sent) >= 12:
            raise M.WebSocketDisconnect()


def body(r):
    """핸들러 반환값 → (상태, dict 또는 bytes, 헤더)."""
    if isinstance(r, (dict, list)):
        return 200, r, {}
    raw = getattr(r, "body", b"")
    try:
        return r.status_code, json.loads(raw.decode("utf-8")), dict(r.headers)
    except (ValueError, UnicodeDecodeError):
        return r.status_code, raw, dict(r.headers)


SESS = {}
OUT = {}


async def scenario():
    LE = M.LE
    a, _ = M.get_session(None)
    b, _ = M.get_session(None)
    SESS["A"], SESS["B"] = a, b
    A, B = a.sid, b.sid

    # ── FAB 고르고 PLAY → 차가 올라온다 ──
    st, d, _ = body(await M.select_fab(Req(A, {"fab": "M16A", "prefix": "BR"})))
    OUT["select"] = [st, d.get("fab"), d.get("prefix")]
    snap = await M.live_snapshot(Req(A))
    OUT["before_play"] = [snap["live"]["me_playing"], snap["live"]["playing"], snap["live"]["table"]]
    st, d, _ = body(await M.live_cmd(Req(A, {"action": "play"})))
    OUT["play"] = [st, d["playing"], d["me_playing"]]
    for _ in range(150):
        snap = await M.live_snapshot(Req(A))
        if snap["vehicles"]:
            break
        await asyncio.sleep(0.1)
    OUT["vehicles"] = len(snap["vehicles"])
    OUT["key_shown"] = snap["live"]["key"]
    OUT["key_leak"] = "dummy-key" in json.dumps(snap, default=str)

    # ── 여럿 — B 도 같은 FAB 을 PLAY, A 가 정지해도 돈다 ──
    await M.select_fab(Req(B, {"fab": "M16A", "prefix": "BR"}))
    await M.live_cmd(Req(B, {"action": "play"}))
    await M.live_cmd(Req(A, {"action": "stop"}))
    OUT["after_a_stop"] = LE.feed_for("M16A", "BR").playing
    st, d, _ = body(await M.live_cmd(Req(B, {"action": "stop"})))
    OUT["after_b_stop"] = [LE.feed_for("M16A", "BR").playing, d["me_playing"]]

    # ── PLAY 중에 FAB 을 바꾸면 PLAY 가 따라가고 앞 FAB 은 멈춘다 ──
    await M.select_fab(Req(A, {"fab": "M14A", "prefix": "A"}))
    await M.live_cmd(Req(A, {"action": "play"}))
    await M.select_fab(Req(A, {"fab": "M16B", "prefix": "B"}))
    OUT["moved"] = [LE.feed_for("M14A", "A").playing, LE.feed_for("M16B", "B").playing,
                    list(LE.playing_key(A) or [])]

    # ── 모르는 명령 · 상태 한눈에 ──
    st, d, _ = body(await M.live_cmd(Req(A, {"action": "jump"})))
    OUT["bad_cmd"] = st
    stt = await M.live_status(Req(A))
    OUT["status"] = [sorted(stt["players"]), stt["sessions"] >= 2]

    # ── 관제 스코어 중계 ──
    await M.select_fab(Req(B, {"fab": "M16A", "prefix": "BR"}))
    st, d, _ = body(await M.score_feed(Req(B, q={"limit": "30"})))
    OUT["score"] = [st, d.get("ok"), d.get("sys"), len(d.get("rows") or [])]
    # 화면이 limit 없이 / 하루치로 물으면 오늘 하루(1440분)까지 — 예전엔 90분(최대 240)이었다
    st, d, _ = body(await M.score_feed(Req(B, q={})))
    OUT["score_day"] = [len(d.get("rows") or [])]
    st, d, _ = body(await M.score_feed(Req(B, q={"limit": "99999"})))
    OUT["score_day"].append(len(d.get("rows") or []))
    st, raw, h = body(await M.score_graph(Req(B, q={"at": "2026-10-06T10:24:00", "minutes": "120",
                                                    "theme": "light"})))
    OUT["graph"] = [st, b'data-sys="M16HUB"' in raw if isinstance(raw, bytes) else False]
    st, raw, h = body(await M.score_report(Req(B, q={"day": "20261006", "name": "PROBLEM_MAP_X.html"})))
    OUT["report"] = [st, "attachment" in (h.get("Content-Disposition") or "")]

    # ── 웹소켓 — 리플레이로 시작 → 실시간 장면 → 실시간 중 재생 명령은 버림 → 다시 리플레이 ──
    await M.select_fab(Req(A, {"fab": "M16A", "prefix": "BR"}))
    a.engine.pause()
    ws = WS(A, [(2, {"action": "mode", "mode": "live"}), (5, {"action": "play"}),
                (8, {"action": "mode", "mode": "replay"})])
    await M.websocket_endpoint(ws)
    kinds = ["L" if "live" in f else "R" for f in ws.sent]
    OUT["ws_kinds"] = "".join(kinds)
    OUT["ws_open_during"] = ws.ws_during
    OUT["ws_open_after"] = a.ws
    OUT["replay_state_after_live_play"] = a.engine.state
    live = [f for f in ws.sent if "live" in f]
    OUT["ws_live_shape"] = sorted(k for k in ("vehicles", "vehicleStats", "time_short", "live")
                                  if live and k in live[-1])
    OUT["ws_live_fab"] = [live[-1]["live"]["fab"], live[-1]["live"]["prefix"]] if live else None

    # ── 세션을 치우면 PLAY 를 놓는다 ──
    await M.live_cmd(Req(A, {"action": "play"}))
    before = list(LE.playing_key(A) or [])
    a.close()
    OUT["close"] = [before, LE.playing_key(A)]
    for f in list(LE._FEEDS.values()):
        f.stop("시험 끝")


asyncio.run(scenario())
print(json.dumps(OUT, ensure_ascii=False, default=str))
sys.stdout.flush()
os._exit(0)                               # 피드 실(데몬)을 기다리지 않는다
