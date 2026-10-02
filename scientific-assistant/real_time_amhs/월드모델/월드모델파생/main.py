#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py - OHT 월드모델 시뮬레이션 서버

FastAPI 기반 통합 서버:
- 실 데이터 리플레이 (플레이/일시정지/속도조절/시간점프)
- 매크로 예측 (큐, TAT, 혼잡, 데드락)
- WebSocket 실시간 전송
- 스타/로그프레소 지표 연동 표시
"""

import asyncio
import json
import os
import secrets
import shutil
import sys
import threading
import time as _time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# 현재 디렉토리를 path에 추가 (개발 모드)
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_paths import bundled_dir, runtime_dir

from config import (
    SERVER_HOST, SERVER_PORT, DATA_DATES, DATA_BY_FAB, FAB_CATALOG,
    DEFAULT_FAB, DEFAULT_PREFIX, get_fab_entry, get_dates_for_fab,
    MAP_DIR, DATA_DIR,
)
from data_loader import LayoutData, HIDZoneData, get_available_dates, ensure_layout_cache
from replay_engine import ReplayEngine, ReplayState

# 경로 자동 인식 결과 표시
print(f"[경로] MAP_DIR  = {MAP_DIR}")
print(f"[경로] DATA_DIR = {DATA_DIR}")

# ============================================================
# 앱 초기화
# ============================================================

app = FastAPI(title="OHT 월드모델 시뮬레이션", version="1.0")

# ★정적 파일 — 3D 아이소메트리 보기(static/js/oht3d/*.js). 이 앱은 dashboard.html
#   한 장을 글자로 돌려주는 구조라 정적 폴더가 없었다. three.js 는 ES 모듈이라
#   <script type=module> 이 http 로 받아야 하고(file:// 는 브라우저가 막는다),
#   폐쇄망이라 CDN 이 아니라 **이 폴더**에서 나가야 한다.
#   PyInstaller 로 묶으면 sys._MEIPASS 밑에 풀리므로 bundled_dir() 기준이다
#   (oht_world.spec 의 datas 에 ('static', 'static') 이 같이 있어야 한다).
class _NoCacheStatic(StaticFiles):
    """정적 파일도 **늘 물어보고** 쓰게 한다.

    ★StaticFiles 는 ETag·Last-Modified 는 붙이지만 Cache-Control 을 안 붙인다.
      그러면 브라우저가 휴리스틱 캐시로 넘어가 **묻지도 않고** 옛 파일을 쓴다.
      oht3d.js 를 새로 올렸는데 3D 가 예전 모습 그대로였던 이유가 이것이다.
    ★no-cache 는 '쓰지 마라' 가 아니라 '쓰기 전에 물어봐라' 다. 안 바뀌었으면
      304 한 줄로 끝나니 통신량은 거의 그대로다(three.js 690KB 도 다시 안 받는다).
    """

    def file_response(self, *a, **k):
        r = super().file_response(*a, **k)
        r.headers["Cache-Control"] = "no-cache, must-revalidate"
        return r


_STATIC_DIR = bundled_dir() / "static"
if _STATIC_DIR.is_dir():
    app.mount("/static", _NoCacheStatic(directory=str(_STATIC_DIR)), name="static")
else:
    print(f"[경고] static 폴더가 없다 — 3D 아이소메트리 보기가 안 뜬다: {_STATIC_DIR}")


# ============================================================
# 로그프레소 캐시 폴더 — 서버 종료 시 자동 삭제
# ============================================================
LOGPRESSO_CACHE_DIR = str(runtime_dir() / "_logpresso_cache")


def _cleanup_logpresso_cache():
    """_logpresso_cache 폴더 전체 삭제. 종료 시 1회 호출."""
    import shutil
    if os.path.isdir(LOGPRESSO_CACHE_DIR):
        try:
            shutil.rmtree(LOGPRESSO_CACHE_DIR)
            print(f"[정리] 로그프레소 캐시 삭제 완료: {LOGPRESSO_CACHE_DIR}")
        except Exception as e:
            print(f"[정리] 캐시 삭제 실패: {e}")


@app.on_event("shutdown")
async def _on_shutdown():
    _cleanup_logpresso_cache()


# Ctrl+C / kill 신호로 종료될 때도 동작하도록 atexit 등록
import atexit
atexit.register(_cleanup_logpresso_cache)

def _load_fab(fab: str, prefix: str):
    """해당 FAB/prefix의 layout/hid_zones 로드. (layout, hid_zones) 반환."""
    entry = get_fab_entry(fab, prefix)
    if entry is None:
        raise ValueError(f"FAB not in catalog: {fab}/{prefix}")

    print(f"[초기화] {fab}/{prefix} layout 캐시 확보...")
    cache_path = ensure_layout_cache(fab, prefix)
    layout_obj = LayoutData().load(cache_path)
    print(f"  → 노드 {len(layout_obj.nodes)}개, 엣지 {len(layout_obj.edge_dist)}개")

    print(f"[초기화] {fab}/{prefix} HID_Zone_Master 로딩...")
    hid_csv = entry.get("hid_csv") or None
    hid_obj = HIDZoneData().load(hid_csv)
    print(f"  → Zone {len(hid_obj.zones)}개")

    return layout_obj, hid_obj


# ============================================================
# 접속자마다 제 상태를 갖는다 — 여럿이 같이 봐도 서로 안 섞인다
# ============================================================
# ★고객: "여러사람이 접속할껀데 지금 1사람이 접속하면 다른사람이 접속하면
#   1사람이 한내용이 보여."
#   맞다. 엔진(ReplayEngine)·고른 FAB·조회 번호가 **모듈 전역 하나**였다.
#   한 대 서버에 여럿이 붙으면 A 가 부른 날짜를 B 가 보고, B 가 누른 정지가
#   A 의 재생을 멈췄다. 조회 멈춤은 더 나빠서, 한 사람이 누르면 그때 돌던
#   **남의 조회까지** 같이 죽었다.
#
# 무엇을 나누고 무엇을 같이 쓰나
#   · 나눈다  — 엔진(재생 위치·불러온 날짜·월드모델) · 고른 FAB/prefix ·
#               조회 번호(멈춤) · 로그프레소 CSV 폴더
#   · 같이 쓴다 — layout·HID Zone. 한 번 읽고 **고치지 않는** 자료다
#     (ReplayEngine·WorldModel 은 읽기만 한다 — 좌표·엣지 길이·존 정의).
#     M14A 만 해도 노드 9,403 · 엣지 10,424 라, 사람마다 따로 읽으면 접속할
#     때마다 수백 MB 와 수 초가 그냥 날아간다.
#
# 누가 누구인지 — 쿠키(oht_sid) 한 줄. 화면(dashboard.html)은 손대지 않는다.
#   같은 브라우저의 여러 탭은 한 사람으로 본다(원래 한 사람이니 그게 맞다).
SESSION_COOKIE = "oht_sid"
# 이 시간 동안 아무 요청도 없으면 치운다 (그 사람 몫의 기억을 계속 들고 있을 이유가 없다)
SESSION_TTL_SEC = int(os.environ.get("OHT_SESSION_TTL", 3600))
# 동시에 들고 있을 수 있는 수 — 넘으면 **제일 오래 안 온 사람**부터 치운다.
# ★한 사람이 하루치를 부르면 프레임이 통째로 메모리에 남는다. 한도가 없으면
#   접속만 쌓여도 서버가 먹통이 된다.
SESSION_MAX = int(os.environ.get("OHT_SESSION_MAX", 24))

# layout·HID Zone 은 (fab, prefix) 마다 한 벌만 읽어 같이 쓴다
_LAYOUT_CACHE: dict = {}
_LAYOUT_LOCK = threading.Lock()


def get_layout(fab: str, prefix: str):
    """(layout, hid_zones) — 이미 읽었으면 그것을 준다.

    ★읽기가 오래 걸리므로 **잠금 밖에서** 읽는다. 둘이 동시에 같은 FAB 을
      처음 열면 두 번 읽힐 수는 있지만, 남는 쪽은 버려지고 결과는 하나다
      (setdefault). 잠금을 붙들고 읽으면 그동안 서버 전체가 멎는다.
    """
    key = (fab, prefix)
    with _LAYOUT_LOCK:
        hit = _LAYOUT_CACHE.get(key)
    if hit is not None:
        return hit
    val = _load_fab(fab, prefix)
    with _LAYOUT_LOCK:
        return _LAYOUT_CACHE.setdefault(key, val)


class Session:
    """한 사람 몫."""

    def __init__(self, sid: str):
        self.sid = sid
        self.fab = DEFAULT_FAB
        self.prefix = DEFAULT_PREFIX
        self.layout, self.hid_zones = get_layout(self.fab, self.prefix)
        self.engine = ReplayEngine(self.layout, self.hid_zones)
        # 조회 번호 — 멈춤은 **제 조회만** 멈춘다 (전역이던 시절엔 남의 것도 죽였다)
        self.lp = {"gen": 0, "stop_upto": 0}
        self.seen = _time.time()
        # 로그프레소 CSV 도 사람마다 따로 — 같은 구간을 둘이 조회하면 같은
        # 파일을 서로 덮어쓰다가 반쯤 쓰인 것을 읽는다
        self.cache_dir = os.path.join(LOGPRESSO_CACHE_DIR, sid)

    def touch(self):
        self.seen = _time.time()

    def select_fab(self, fab: str, prefix: str):
        """FAB 을 바꾸면 그 사람 엔진만 다시 세운다."""
        self.engine.stop()
        self.layout, self.hid_zones = get_layout(fab, prefix)
        self.engine = ReplayEngine(self.layout, self.hid_zones)
        self.fab = fab
        self.prefix = prefix

    def close(self):
        try:
            self.engine.stop()
        except Exception:
            pass
        shutil.rmtree(self.cache_dir, ignore_errors=True)


SESSIONS: dict = {}
_SESS_LOCK = threading.Lock()


def _reap_locked():
    """치울 세션을 골라 목록에서 뺀다. 실제 정리(close)는 잠금 밖에서."""
    now = _time.time()
    dead = [k for k, v in SESSIONS.items() if now - v.seen > SESSION_TTL_SEC]
    live = [v for k, v in SESSIONS.items() if k not in dead]
    live.sort(key=lambda v: v.seen)          # 오래 안 온 사람이 앞
    while len(live) > SESSION_MAX:
        dead.append(live.pop(0).sid)
    return [SESSIONS.pop(k) for k in dead if k in SESSIONS]


def get_session(sid):
    """(세션, 새로 만들었나). sid 가 없거나 모르는 것이면 새로 만든다."""
    fresh = False
    with _SESS_LOCK:
        s = SESSIONS.get(sid) if sid else None
        if s is None:
            sid = secrets.token_urlsafe(16)
            s = Session(sid)
            SESSIONS[sid] = s
            fresh = True
            print(f"[세션] 새 접속 {sid[:8]}… (지금 {len(SESSIONS)}명)")
        s.touch()
        gone = _reap_locked()
    for g in gone:
        print(f"[세션] 정리 {g.sid[:8]}… (오래 안 옴)")
        g.close()
    return s, fresh


def sess(request: Request) -> Session:
    """이 요청을 보낸 사람 몫. 미들웨어가 먼저 붙여 둔다."""
    s = getattr(request.state, "sess", None)
    if s is None:                                    # 미들웨어를 안 탄 경우(시험 등)
        s, _ = get_session(request.cookies.get(SESSION_COOKIE))
        request.state.sess = s
    return s


@app.middleware("http")
async def _session_mw(request: Request, call_next):
    """요청마다 '누구인지' 를 붙이고, 처음 온 사람에게는 쿠키를 준다."""
    # 정적 파일은 사람을 가릴 것이 없다 — 세션을 만들지 않는다
    if request.url.path.startswith("/static/"):
        return await call_next(request)
    sid = request.cookies.get(SESSION_COOKIE)
    s, fresh = get_session(sid)
    request.state.sess = s
    resp = await call_next(request)
    if fresh or sid != s.sid:
        # ★httponly — 화면 JS 가 읽을 일이 없다. samesite=lax — 같은 자리에서만.
        #   secure 는 안 붙인다: 폐쇄망이라 http 로 뜬다(붙이면 쿠키가 아예 안 간다).
        resp.set_cookie(SESSION_COOKIE, s.sid, httponly=True, samesite="lax",
                        max_age=SESSION_TTL_SEC, path="/")
    return resp


@app.on_event("startup")
async def _session_sweeper():
    """오래 안 온 사람을 주기적으로 치운다 — 아무도 요청을 안 보내도 돌게."""
    async def loop():
        while True:
            await asyncio.sleep(60)
            with _SESS_LOCK:
                gone = _reap_locked()
            for g in gone:
                print(f"[세션] 정리 {g.sid[:8]}… (오래 안 옴)")
                g.close()
    asyncio.create_task(loop())          # startup 은 이미 루프 안이다


# 시작할 때 기본 FAB 을 미리 읽어 둔다 — 첫 접속자가 기다리지 않게
layout, hid_zones = get_layout(DEFAULT_FAB, DEFAULT_PREFIX)

# WebSocket 연결 관리
ws_clients: list = []


# ============================================================
# API 엔드포인트
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """대시보드 HTML.

    ★캐시를 끈다. 이 화면은 한 번 띄우면 며칠씩 그대로 떠 있고, 그 사이
      dashboard.html 을 새로 올려도 브라우저가 예전 것을 계속 쓴다. 헤더를
      하나도 안 붙이면 브라우저가 **제 마음대로**(휴리스틱) 캐시하는데,
      그 기간이 '마지막 수정 이후 지난 시간의 10%' 라 오래된 파일일수록
      더 오래 붙들고 있는다 — "서버는 바뀌었는데 화면은 그대로" 가 그것이다.
      HTML 한 장이라 매번 받아도 부담이 없다.
    """
    html_path = str(bundled_dir() / "dashboard.html")
    with open(html_path, 'r', encoding='utf-8') as f:
        return HTMLResponse(f.read(), headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache", "Expires": "0"})


@app.get("/api/status")
async def get_status(request: Request):
    """현재 시뮬레이션 상태 — 부른 사람 것"""
    snapshot = sess(request).engine.get_current_snapshot()
    # 차량 위치는 WebSocket으로만 전송 (API에서는 제외)
    snapshot.pop('vehicles', None)
    return snapshot


@app.get("/api/dates")
async def get_dates(request: Request):
    """그 사람이 고른 FAB/prefix 의 사용 가능한 날짜 목록"""
    s = sess(request)
    date_map = get_dates_for_fab(s.fab, s.prefix)
    return get_available_dates(date_map)


@app.get("/api/fabs")
async def get_fabs(request: Request):
    """FAB/prefix 카탈로그 + **그 사람이** 고른 값. 데이터 폴더 매칭 포함."""
    s = sess(request)
    fabs = []
    for e in FAB_CATALOG:
        dates_map = get_dates_for_fab(e["fab"], e["prefix"])
        fabs.append({
            "fab": e["fab"],
            "prefix": e["prefix"],
            "has_data": bool(dates_map),
            "dates": sorted(dates_map.keys()),
        })
    return {
        "catalog": fabs,
        "current": {"fab": s.fab, "prefix": s.prefix},
    }


@app.post("/api/fab/select")
async def select_fab(request: Request):
    """FAB/prefix 전환 — **그 사람 엔진만** 다시 세운다.

    ★예전에는 전역을 갈아치워서, 한 사람이 M16A 로 바꾸면 M14A 를 보고 있던
      다른 사람 화면까지 같이 넘어갔다."""
    s = sess(request)
    body = await request.json()
    fab = body.get('fab', '').strip()
    prefix = body.get('prefix', '').strip()

    if get_fab_entry(fab, prefix) is None:
        return JSONResponse({"error": f"Unknown FAB: {fab}/{prefix}"}, status_code=400)

    if fab == s.fab and prefix == s.prefix:
        return {"fab": s.fab, "prefix": s.prefix, "changed": False,
                "bounds": s.layout.bounds, "nodes": len(s.layout.nodes),
                "zones": len(s.hid_zones.zones)}

    try:
        s.select_fab(fab, prefix)
    except Exception as e:
        return JSONResponse({"error": f"Load failed: {e}"}, status_code=500)

    return {
        "fab": s.fab,
        "prefix": s.prefix,
        "changed": True,
        "bounds": s.layout.bounds,
        "nodes": len(s.layout.nodes),
        "edges": len(s.layout.edge_dist),
        "zones": len(s.hid_zones.zones),
    }


@app.post("/api/replay/load")
async def load_date(request: Request):
    """날짜 데이터 로드 (그 사람이 고른 FAB/prefix 기준)"""
    s = sess(request)
    body = await request.json()
    date_key = body.get('date', '')

    date_map = get_dates_for_fab(s.fab, s.prefix)
    if date_key not in date_map:
        return JSONResponse(
            {"error": f"Invalid date for {s.fab}/{s.prefix}: {date_key}"},
            status_code=400,
        )

    print(f"[로드] {s.sid[:8]}… {s.fab}/{s.prefix} {date_key} 데이터 로딩 시작...")
    result = s.engine.load_date(date_key, date_map[date_key])
    print(f"[로드] 완료: {result.get('stats', {})}")
    return result


# ── 조회 멈춤 ────────────────────────────────────────────────────
# ★조각과 조각 사이에서만 듣는다 — 보낸 요청 하나는 중간에 못 끊는다.
# ★단순한 True/False 로는 안 된다. 멈춤을 누른 사람은 곧바로 다시 조회한다
#   ("다시 재조회 할 수도 있잖아"). 그때 새 조회가 플래그를 False 로 지우는데,
#   멈추라고 한 옛 조회가 아직 제 조각을 붙들고 있으면 그 False 를 보고 되살아나
#   두 조회가 같이 돌아 리플레이 엔진을 함께 건드린다.
#   그래서 조회마다 번호(gen)를 준다:
#     · 멈춤  = "지금 번호까지는 그만"  (stop_upto = gen)
#     · 새 조회 = gen + 1 → 멈춤에 안 걸리고, 옛 조회는 제 번호가 아니라 스스로 멎는다
# ★번호는 **사람마다** 따로다 (Session.lp). 전역 하나였을 때는 한 사람이
#   멈춤을 누르면 그때 돌던 **남의 조회까지** 같이 죽었다.


def _lp_should_cancel(s: "Session", my_gen: int):
    """이 조회(my_gen)가 멈춰야 하는지. 조각과 조각 사이에서 불린다."""
    def _f():
        if s.lp["stop_upto"] >= my_gen:
            return True                    # 그 사람이 멈춤을 눌렀다
        return s.lp["gen"] != my_gen       # 그 사람이 더 새 조회를 시작했다
    return _f


@app.post("/api/logpresso/cancel")
async def logpresso_cancel(request: Request):
    """조회 멈춤 — 다음 조각으로 넘어가기 전에 멈춘다. **제 조회만** 멈춘다."""
    s = sess(request)
    s.lp["stop_upto"] = s.lp["gen"]
    print(f"[로그프레소] {s.sid[:8]}… 멈춤 요청 (조회 #{s.lp['gen']}) — 다음 조각에서 멈춥니다")
    return {"ok": True, "gen": s.lp["gen"]}


@app.post("/api/logpresso/load")
async def logpresso_load(request: Request):
    """로그프레소에서 시간 구간을 조회 → CSV 저장 → 리플레이 엔진에 로드.

    body 예시:
      {
        "from_dt": "20260621000000",
        "to_dt"  : "20260621010000",
        "table"  : "oht_data_m16br",
        "chunk_minutes": 10,           (선택, 기본 10)
        "profile": "agg30" | "raw"     (선택 — 안 보내면 logpresso_query.PROFILE)
      }
    ★profile: 쿼리를 두 벌 들고 있다. agg30 = MSG_ID=2 만 30초로 묶은 것(기본),
      raw = 예전 쿼리(원본 그대로). 되돌릴 일이 있어 둘 다 남겨 뒀다.
    """
    s = sess(request)
    body = await request.json()
    from_dt = (body.get('from_dt') or '').strip()
    to_dt   = (body.get('to_dt')   or '').strip()
    table   = (body.get('table')   or '').strip()
    chunk_minutes = int(body.get('chunk_minutes', 10))
    profile = (body.get('profile') or '').strip() or None
    s.lp["gen"] += 1                   # 새 조회 — 번호를 하나 올린다
    _my_gen = s.lp["gen"]

    if not (from_dt and to_dt and table):
        return JSONResponse(
            {"error": "from_dt / to_dt / table 모두 필요"}, status_code=400)
    if len(from_dt) != 14 or len(to_dt) != 14:
        return JSONResponse(
            {"error": "from_dt/to_dt 는 yyyyMMddHHmmss (14자리)"}, status_code=400)

    try:
        from logpresso_query import query_oht_chunked
    except ImportError as e:
        return JSONResponse(
            {"error": f"logpresso_query 모듈 임포트 실패 (requests/pandas 필요): {e}"},
            status_code=500)

    print(f"[로그프레소] {s.sid[:8]}… 조회 시작: {table}  {from_dt}~{to_dt}  chunk={chunk_minutes}분"
          + (f"  profile={profile}" if profile else ""))
    t0 = _time.perf_counter()
    try:
        # ★조회는 **다른 실에서** 돌린다. 여기서 그냥 부르면 조회가 끝날 때까지
        #   서버가 통째로 멎어 /api/logpresso/cancel 요청 자체가 안 들어온다.
        #   (멈춤 단추를 눌러도 아무 일도 안 일어나는 이유가 그것이었다.)
        from starlette.concurrency import run_in_threadpool
        df = await run_in_threadpool(
            lambda: query_oht_chunked(from_dt, to_dt, table=table,
                                      chunk_minutes=chunk_minutes, profile=profile,
                                      should_cancel=_lp_should_cancel(s, _my_gen)))
    except Exception as e:
        # 멈춤은 실패가 아니다 — 화면이 빨간 오류로 띄우면 안 된다
        from logpresso_query import QueryCancelled
        if isinstance(e, QueryCancelled):
            print(f"[로그프레소] {e}")
            return JSONResponse({"cancelled": True, "error": str(e)}, status_code=200)
        print(f"[로그프레소] 조회 실패: {e}")
        return JSONResponse(
            {"error": f"로그프레소 조회 실패: {e}"}, status_code=502)
    elapsed = _time.perf_counter() - t0
    if df is None or df.empty:
        return JSONResponse(
            {"error": "조회 결과가 비어 있음", "rows": 0,
             "elapsed_sec": round(elapsed, 1)},
            status_code=200)

    # CSV 저장 → 폴더 구조를 date_config 형태로 wrap
    # ★사람마다 제 폴더 — 같은 구간을 둘이 조회하면 한 파일을 서로 덮어쓴다
    folder_name = f"{from_dt}_{to_dt}"
    save_dir = os.path.join(s.cache_dir, folder_name)
    os.makedirs(save_dir, exist_ok=True)
    csv_name = f"{table}_{from_dt}_{to_dt}.csv"
    csv_path = os.path.join(save_dir, csv_name)
    try:
        df.to_csv(csv_path, index=False, encoding='utf-8')
    except Exception as e:
        return JSONResponse({"error": f"CSV 저장 실패: {e}"}, status_code=500)
    print(f"[로그프레소] {len(df):,}건 저장: {csv_path}  ({elapsed:.1f}s)")

    # 가상 date_config (data_loader 형식과 일치) 구성
    date_key = f"LP_{from_dt}_{to_dt}"
    date_config = {
        "dir": save_dir,
        "fab": s.fab,
        "prefix": s.prefix,
        "oht_raw": csv_name,
        "oht_data_m14a": csv_name,   # parsed 포맷이므로 m14a 로더로 라우팅
        "hid_inout": None,
        "rail_cut": None,
        "star": None,
        "ts_resource": None,
        "oht_time_avg": None,
        "time_range": ("00:00:00", "23:59:59"),
        "description": f"로그프레소 {table} {from_dt}~{to_dt} ({len(df):,}건)",
    }

    print(f"[로드] {s.sid[:8]}… 가상 date_key={date_key} 데이터 로딩 시작...")
    result = s.engine.load_date(date_key, date_config)
    result['logpresso'] = {
        'rows': int(len(df)),
        'csv_path': csv_path,
        'elapsed_sec': round(elapsed, 1),
        'date_key': date_key,
    }
    print(f"[로드] 완료: {result.get('stats', {})}")
    return result


@app.post("/api/replay/play")
async def replay_play(request: Request):
    """리플레이 시작 — 부른 사람 것만"""
    e = sess(request).engine
    e.play()
    return {"state": e.state}


@app.post("/api/replay/pause")
async def replay_pause(request: Request):
    """리플레이 일시정지 — 부른 사람 것만"""
    e = sess(request).engine
    e.pause()
    return {"state": e.state}


@app.post("/api/replay/stop")
async def replay_stop(request: Request):
    """리플레이 정지 — 부른 사람 것만"""
    e = sess(request).engine
    e.stop()
    return {"state": e.state}


@app.post("/api/replay/speed")
async def replay_speed(request: Request):
    """재생 속도 변경 — 부른 사람 것만"""
    e = sess(request).engine
    body = await request.json()
    speed = float(body.get('speed', 1.0))
    e.set_speed(speed)
    return {"speed": e.speed}


@app.post("/api/replay/jump")
async def replay_jump(request: Request):
    """특정 시각으로 점프 — 부른 사람 것만"""
    e = sess(request).engine
    body = await request.json()

    # 시간 점프
    time_str = body.get('time')
    if time_str:
        ok = e.jump_to_time(time_str)
        if ok:
            return {"jumped": True, "time": e.current_time.strftime("%H:%M:%S") if e.current_time else ""}
        return JSONResponse({"error": "Invalid time"}, status_code=400)

    # 프레임 점프
    frame = body.get('frame')
    if frame is not None:
        ok = e.jump_to_frame(int(frame))
        if ok:
            return {"jumped": True, "frame": e.current_frame_idx}
        return JSONResponse({"error": "Invalid frame"}, status_code=400)

    return JSONResponse({"error": "Provide 'time' or 'frame'"}, status_code=400)


@app.get("/api/predict")
async def get_prediction(request: Request):
    """매크로 예측 결과"""
    return sess(request).engine.predictor.get_prediction()


@app.get("/api/predict-deadlock")
async def predict_deadlock(request: Request, force: bool = Query(False)):
    """데드락 예측"""
    w = sess(request).engine.world
    if not w.vehicles:
        return {"vehicleCount": 0, "horizons": {}, "summary": {"totalDeadlocks": 0}}
    return w.predict_deadlocks()


@app.get("/api/correlations")
async def get_correlations(request: Request):
    """데이터 간 상관관계"""
    return sess(request).engine.predictor.get_correlations()


@app.get("/api/star-history")
async def get_star_history(request: Request):
    """스타 전체 타임라인 (차트용)"""
    return sess(request).engine.get_star_history()


@app.get("/api/hotspot-history")
async def get_hotspot_history(request: Request):
    """전체 데이터에서 스캔한 데드락 핫스팟 이벤트 이력 (재생 전에 미리 채움)"""
    return sess(request).engine.get_hotspot_history()


@app.get("/api/hid-speeds")
async def get_hid_speeds(request: Request):
    """HID 구간별 속도 통계"""
    return sess(request).engine.get_hid_speed_summary()


@app.get("/api/obs-jam-history")
async def get_obs_jam_history(request: Request):
    """OBS/JAM 분 단위 시계열 (전체 데이터, 재생과 무관)"""
    return sess(request).engine.get_obs_jam_history()


@app.get("/api/bottleneck-analysis")
async def get_bottleneck_analysis(request: Request):
    """HID_INOUT × ts_resource 교차 병목 분석 (UDP 독립)"""
    return sess(request).engine.get_bottleneck_analysis()


@app.get("/api/ts-events")
async def get_ts_events(request: Request):
    """ts_resource 분 단위 집계"""
    return sess(request).engine.get_ts_events()


@app.get("/api/hid-zones")
async def get_hid_zones(request: Request):
    """HID Zone 현황"""
    return sess(request).engine.world.get_zone_status()


@app.get("/api/data-sources")
async def get_data_sources(request: Request):
    """로드된 데이터 현황 — 부른 사람 것"""
    e = sess(request).engine
    if e.data_loader:
        return {
            'date': e.current_date,
            'stats': e.data_loader.stats,
            'time_start': str(e.data_loader.time_start),
            'time_end': str(e.data_loader.time_end),
        }
    return {'date': None, 'stats': {}}


@app.get("/api/layout-bounds")
async def get_layout_bounds(request: Request):
    """레이아웃 바운드 정보 — 그 사람이 고른 FAB 것"""
    return sess(request).layout.bounds


@app.get("/api/layout-graph")
async def get_layout_graph(request: Request):
    """레이아웃 노드/엣지 전체 (맵 배경용) - 초기 1회만 로드.

    2026-09 부터 스테이션·라벨(ZC/HID/베이/열/MTL)·센서·노드 메타(글자방향·
    합류·분기)도 같이 준다 — 현장 HMI 캡처와 같은 맵을 그리기 위해서다.
    """
    s = sess(request)
    layout, hid_zones = s.layout, s.hid_zones      # ★그 사람이 고른 FAB 의 것
    nodes = {str(nid): [round(c[0], 1), round(c[1], 1)] for nid, c in layout.nodes.items()}
    edges = [[e[0], e[1]] for e in layout.edge_dist.keys()]

    # HID Zone: IN/OUT Lane 좌표 포함
    zone_list = []
    seen = set()
    for zid, zinfo in hid_zones.zones.items():
        if zid in seen:
            continue
        seen.add(zid)

        in_lanes = []
        for (a, b), z in hid_zones.in_lane_to_zone.items():
            if z == zid and a in layout.nodes and b in layout.nodes:
                in_lanes.append({'from': a, 'to': b})
        out_lanes = []
        for (a, b), z in hid_zones.out_lane_to_zone.items():
            if z == zid and a in layout.nodes and b in layout.nodes:
                out_lanes.append({'from': a, 'to': b})

        if not in_lanes and not out_lanes:
            continue

        # 중심점 계산
        all_nodes_set = set()
        for l in in_lanes + out_lanes:
            all_nodes_set.add(l['from'])
            all_nodes_set.add(l['to'])
        xs = [layout.nodes[n][0] for n in all_nodes_set if n in layout.nodes]
        ys = [layout.nodes[n][1] for n in all_nodes_set if n in layout.nodes]
        if not xs:
            continue

        zone_list.append({
            'id': zid,
            'name': zinfo.get('fullName', f'Zone-{zid}'),
            'bay': zinfo.get('bayZone', ''),
            'hid': zinfo.get('hidNo', ''),
            'max': zinfo.get('vehicleMax', 37),
            'inLanes': in_lanes,
            'outLanes': out_lanes,
            'cx': round(sum(xs)/len(xs), 1),
            'cy': round(sum(ys)/len(ys), 1),
        })

    # ★HMI 맵 재료 (스키마 2). 전부 layout.xml 에 있던 것을 캐시에 실어 둔 것이다.
    #   옛 캐시(스키마 1)면 빈 목록이 간다 — 화면은 레일만 그리고, 왜 그런지는
    #   schema 로 알 수 있다 (캐시를 지우고 다시 띄우면 된다).
    return {"nodes": nodes, "edges": edges, "bounds": layout.bounds, "zones": zone_list,
            "schema": getattr(layout, "schema", 1),
            "meta": {str(k): v for k, v in getattr(layout, "meta", {}).items()},
            "stations": getattr(layout, "stations", []),
            "labels": getattr(layout, "labels", []),
            "sensors": getattr(layout, "sensors", [])}


# ============================================================
# WebSocket
# ============================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # ★미들웨어는 http 요청에만 붙는다 — 여기서는 쿠키를 직접 읽는다.
    #   쿠키가 없으면(웹소켓만 따로 연 경우) 새 세션을 만들어 준다.
    _s, _ = get_session(websocket.cookies.get(SESSION_COOKIE))
    engine = _s.engine
    ws_clients.append(websocket)
    print(f"[WS] 연결 {_s.sid[:8]}… ({len(ws_clients)}개)")

    try:
        while True:
            # ★엔진은 매 바퀴 세션에서 다시 꺼낸다 — FAB 을 바꾸면 그 사람 엔진이
            #   새것으로 갈리는데, 처음 꺼낸 것을 붙들고 있으면 웹소켓만 옛 엔진을
            #   계속 돌려 "바꿨는데 화면이 그대로" 가 된다.
            engine = _s.engine
            _s.touch()                      # 재생 중인 사람은 살아 있는 사람이다

            # 클라이언트 메시지 수신 (keep-alive)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                # 클라이언트 명령 처리
                try:
                    cmd = json.loads(data)
                    action = cmd.get('action')
                    if action == 'play':
                        engine.play()
                    elif action == 'pause':
                        engine.pause()
                    elif action == 'stop':
                        engine.stop()
                    elif action == 'speed':
                        engine.set_speed(float(cmd.get('speed', 1.0)))
                    elif action == 'jump':
                        engine.jump_to_time(cmd.get('time', ''))
                    elif action == 'jump_frame':
                        engine.jump_to_frame(int(cmd.get('frame', 0)))
                    elif action == 'load':
                        date_key = cmd.get('date', '')
                        date_map = get_dates_for_fab(_s.fab, _s.prefix)
                        if date_key in date_map:
                            engine.load_date(date_key, date_map[date_key])
                except (json.JSONDecodeError, ValueError):
                    pass
            except asyncio.TimeoutError:
                pass

            # 상태 전송
            if engine.state == ReplayState.PLAYING:
                # 속도에 따라 프레임 스킵
                speed = engine.speed
                if speed <= 0:
                    # MAX: 한번에 10프레임 전진
                    for _ in range(10):
                        if not engine.advance_frame():
                            break
                elif speed >= 5:
                    # x5, x10: 속도만큼 프레임 스킵
                    for _ in range(int(speed)):
                        if not engine.advance_frame():
                            break
                else:
                    engine.advance_frame()

            snapshot = engine.get_current_snapshot()
            # 차량 위치만 간소화 (빠른 전송)
            await websocket.send_text(json.dumps(snapshot, default=str))

            # 속도에 맞는 대기 시간
            if engine.state == ReplayState.PLAYING:
                spd = engine.speed
                if spd <= 0:
                    await asyncio.sleep(0.05)
                elif spd >= 5:
                    await asyncio.sleep(0.1)
                else:
                    await asyncio.sleep(0.4 / max(1, spd))
            else:
                await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        ws_clients.remove(websocket)
        print(f"[WS] 연결 해제 ({len(ws_clients)}개)")
    except Exception as e:
        if websocket in ws_clients:
            ws_clients.remove(websocket)
        print(f"[WS] 오류: {e}")


# ============================================================
# 메인
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  OHT 월드모델 시뮬레이션 서버")
    print(f"  http://localhost:{SERVER_PORT}")
    print("=" * 60)
    print(f"  FAB/Layout: {DEFAULT_FAB}/{DEFAULT_PREFIX} (접속자마다 제 것을 고른다)")
    print(f"  레이아웃: {len(layout.nodes)} 노드, {len(layout.edge_dist)} 엣지")
    print(f"  HID Zone: {len(hid_zones.zones)}개")
    _catalog_summary = [f"{e['fab']}/{e['prefix']}" for e in FAB_CATALOG]
    print(f"  FAB 카탈로그: {_catalog_summary}")
    for _k, _v in DATA_BY_FAB.items():
        print(f"  데이터[{_k}]: {sorted(_v.keys())}")
    print(f"  기본 FAB 날짜: {list(get_dates_for_fab(DEFAULT_FAB, DEFAULT_PREFIX).keys())}")
    print(f"  세션: 최대 {SESSION_MAX}명 · {SESSION_TTL_SEC}초 쉬면 정리")
    print("=" * 60)

    # ★일꾼(worker)을 늘리지 마라. 세션은 이 프로세스 메모리에 있다 —
    #   여럿으로 띄우면 같은 사람이 요청마다 다른 일꾼에 붙어 제 화면을 잃는다.
    #   (한 프로세스로도 충분하다. 무거운 조회는 run_in_threadpool 로 비켜 둔다.)
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
