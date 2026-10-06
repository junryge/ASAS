#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
live_engine.py — 월드모델파생_실시간: 로그프레소 '지금' 데이터를 몇 초마다 받아 월드모델 상태로.

고객 2026-10-06: "따로 해서 만들어 보자 — 로그프레소 데이터 있어, API 데이터 전부 다 있는데
실시간 형태 만들어 볼 수 있지 않아??"

★옆 폴더 **월드모델파생**의 것을 그대로 가져다 쓴다 — 복사하지 않는다.
    지도(OHT_MAP/cache · layout.zip)   data_loader.LayoutData · ensure_layout_cache
    줄 → 차량 상태                       data_loader.parse_oht_data_m14a_row
    위치 · 속도 · 정체 묶음              world_model.WorldModel
    미보고 · HT_STOP · 전조 판정 기준    config.MISS_SEC · IDLE_SEC · OHT_ALERT (재생과 같은 기준)
    로그프레소 서버 · 키 · 쿼리          logpresso_query (SERVERS · API_KEY · '상세' 쿼리)
  그래서 월드모델파생에서 고친 것(현장 판정 기준 · 서버 주소 · 키)이 여기에도 그대로 들어온다.
  두 폴더는 **나란히** 있어야 한다:  월드모델/월드모델파생 · 월드모델/월드모델파생_실시간
  (다른 자리면 환경변수 WM_DIR 에 월드모델파생 폴더를 적는다.)

어떻게 도나 — FAB(지도) 하나에 피드(LiveFeed) 하나, 보는 사람이 몇이든 같이 쓴다.
  · POLL_SEC(5초)마다 [마지막으로 받은 시각 − OVERLAP_SEC, 지금] 을 '상세' 쿼리로 묻는다.
    처음(또는 MAX_GAP_SEC 넘게 끊긴 뒤)에는 지금부터 WARM_SEC(5분) 거꾸로 묻는다 —
    멈춰 있어 보고가 드문 차까지 지도에 올리려고.
  · 겹쳐 묻는 OVERLAP 은 로그프레소에 **늦게 들어온 줄**을 받으려는 것이다. 같은 줄을
    두 번 받으면 차마다 '마지막으로 본 시각' 보다 새 것만 얹는다.
  · 받은 줄은 재생 엔진과 똑같이 **2초 칸**으로 묶어 시간 순서대로 얹는다 — 속도(m/min)를
    재는 방법이 같아야 재생과 같은 그림이 나온다.
  · 칸마다 스냅샷(재생 엔진 get_current_snapshot 과 같은 모양)을 만들어 최근 3분을 들고 있다.
  · 화면에는 BUFFER_SEC 만큼 **늦춰서** 2초 칸을 차례로 내준다 — 5초마다 한 번에 도착한
    줄을 그대로 보이면 차가 5초마다 뛴다. 늦춘 만큼은 화면 상태줄에 '지연' 으로 적는다.
    BUFFER_SEC=0 이면 늘 가장 새 칸을 준다 (부드러움 대신 빠름).
  · 미보고는 **데이터 시계**로 잰다 (벽시계가 아니다). 로그프레소 적재가 통째로 1분 늦으면
    벽시계로는 모든 차가 미보고가 된다 — 그건 차의 일이 아니라 수집의 일이라, 상태줄의
    '지연' 으로 따로 보인다.
  · 아무도 IDLE_STOP_SEC(5분) 동안 안 보면 조회를 멈춘다 (로그프레소를 괜히 두드리지 않게).
    다시 보면 이어서 묻고, 오래 끊겼으면 처음처럼 WARM 부터 다시 받는다.
"""

import csv
import io
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
WM_DIR = os.path.abspath(os.environ.get("WM_DIR") or os.path.join(HERE, "..", "월드모델파생"))
if not os.path.isfile(os.path.join(WM_DIR, "world_model.py")):
    raise SystemExit(f"[실시간] 월드모델파생 폴더를 못 찾았습니다: {WM_DIR}\n"
                     f"  이 폴더 옆에 '월드모델파생' 이 있어야 합니다 (아니면 환경변수 WM_DIR).")
if WM_DIR not in sys.path:
    # ★이 폴더 **바로 뒤**에 넣는다 — 두 폴더에 같은 이름(main.py)이 있다. 이 폴더가 먼저여야
    #   `import main` 이 실시간판 것이 되고, config · data_loader 같은 것은 월드모델파생에서 온다.
    _i = next((k for k, x in enumerate(sys.path) if os.path.abspath(x or ".") == HERE), -1)
    sys.path.insert(_i + 1, WM_DIR)

import config as WC                                            # noqa: E402  (월드모델파생)
from data_loader import (HIDZoneData, LayoutData,              # noqa: E402
                         ensure_layout_cache, parse_oht_data_m14a_row)
from world_model import WorldModel                             # noqa: E402

MISS_SEC = getattr(WC, "MISS_SEC", 50)
IDLE_SEC = getattr(WC, "IDLE_SEC", 1800)
OHT_ALERT = getattr(WC, "OHT_ALERT", None) or {
    "pre_miss": 5, "pre_jam": 10, "pre_ht": 1, "alert_miss": 30, "alert_jam": 20,
    "alert_ht": 10, "confirm_miss": 100, "confirm_jam": 40, "confirm_ht": 30, "gap_ratio": 0.9}


def _env(name, default, cast=float):
    try:
        return cast(os.environ.get(name, "") or default)
    except ValueError:
        return default


# ── 설정 (환경변수로 바꾼다) ────────────────────────────────────────────
POLL_SEC = _env("LIVE_POLL_SEC", 5.0)              # 몇 초마다 로그프레소에 묻나
WARM_SEC = _env("LIVE_WARM_SEC", 300, int)         # 처음 열 때 거꾸로 몇 초치
OVERLAP_SEC = _env("LIVE_OVERLAP_SEC", 20, int)    # 늦게 들어온 줄을 받으려고 겹쳐 묻는 폭
MAX_GAP_SEC = _env("LIVE_MAX_GAP_SEC", 600, int)   # 이보다 오래 끊겼으면 처음부터(WARM)
BUFFER_SEC = _env("LIVE_BUFFER_SEC", POLL_SEC + 3)  # 부드럽게 — 이만큼 늦춰 2초 칸을 차례로
IDLE_STOP_SEC = _env("LIVE_IDLE_STOP_SEC", 300, int)  # 아무도 안 보면 조회를 멈춘다
TIMEOUT_SEC = _env("LIVE_TIMEOUT_SEC", 30, int)    # 로그프레소 한 번 묻는 데 기다리는 한도
STEP_SEC = 2                                       # 프레임 간격 — 재생 엔진(snapshot_interval)과 같다
KEEP_SEC = 180                                     # 들고 있는 프레임 (최근 3분)
FMT = "%Y%m%d%H%M%S"

# ── FAB(지도) → 로그프레소 테이블 ──────────────────────────────────────
# 관제 world_link.MAP 과 같은 짝이다. ★규칙(oht_data_m{번호}{prefix})만으로는 M14B 가
#   oht_data_m14a 가 된다 — 그래서 아는 것은 적어 둔다. 모르는 지도만 규칙을 쓴다.
TABLES = {
    ("M14A", "A"): "oht_data_m14a",
    ("M14B", "A"): "oht_data_m14b",
    ("M16A", "A"): "oht_data_m16a",
    ("M16B", "B"): "oht_data_m16b",
    ("M16A", "BR"): "oht_data_m16br",     # 허브룸 (관제 M16HUB)
}


def table_for(fab: str, prefix: str) -> str:
    t = TABLES.get((fab, prefix))
    if t:
        return t
    m = re.search(r"\d+", fab or "")
    return f"oht_data_m{m.group(0) if m else ''}{prefix}".lower()


# ── 지도 목록 ───────────────────────────────────────────────────────────
_CACHE_RE = re.compile(r"^([A-Za-z0-9]+)_([A-Za-z0-9]+)_layout_cache\.json$")


def catalog() -> list:
    """[{fab, prefix, table, zip, cache, hid_csv}] — 월드모델파생 카탈로그(MAP/*.layout.zip)에
    이미 만들어진 캐시(OHT_MAP/cache)를 더한다. 현장은 zip 이, 저장소는 캐시만 있다."""
    out = {}
    for e in getattr(WC, "FAB_CATALOG", []) or []:
        out[(e["fab"], e["prefix"])] = {"fab": e["fab"], "prefix": e["prefix"],
                                        "zip": e.get("layout_zip") or "",
                                        "cache": e.get("layout_cache") or "",
                                        "hid_csv": e.get("hid_csv") or ""}
    d = str(getattr(WC, "LAYOUT_CACHE_DIR", ""))
    if d and os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            m = _CACHE_RE.match(f)
            if m and (m.group(1), m.group(2)) not in out:
                out[(m.group(1), m.group(2))] = {"fab": m.group(1), "prefix": m.group(2), "zip": "",
                                                 "cache": os.path.join(d, f), "hid_csv": ""}
    for v in out.values():
        v["table"] = table_for(v["fab"], v["prefix"])
    return [out[k] for k in sorted(out)]


def default_fab() -> tuple:
    """처음 보이는 지도 — LIVE_FAB=M16A/BR 처럼 고를 수 있다. 없으면 월드모델파생 기본값."""
    want = os.environ.get("LIVE_FAB", "")
    cat = catalog()
    keys = [(e["fab"], e["prefix"]) for e in cat]
    if "/" in want and tuple(want.split("/", 1)) in keys:
        return tuple(want.split("/", 1))
    d = (getattr(WC, "DEFAULT_FAB", ""), getattr(WC, "DEFAULT_PREFIX", ""))
    if d in keys:
        return d
    return keys[0] if keys else d


_LAYOUTS: dict = {}
_LL = threading.Lock()


def layout_for(fab: str, prefix: str):
    """(layout, hid_zones) — FAB 마다 한 벌만 읽어 같이 쓴다 (읽기만 하는 자료다)."""
    key = (fab, prefix)
    with _LL:
        hit = _LAYOUTS.get(key)
    if hit is not None:
        return hit
    ent = next((e for e in catalog() if (e["fab"], e["prefix"]) == key), None)
    if ent is None:
        raise ValueError(f"모르는 지도입니다: {fab}/{prefix}")
    if ent["zip"] and os.path.isfile(ent["zip"]):
        path = ensure_layout_cache(fab, prefix)          # zip 이 새것이면 캐시를 다시 만든다
    else:
        path = ent["cache"]
    lay = LayoutData().load(path)
    # ★HID 존 목록이 없는 지도에 기본값(M14A 것)을 얹지 않는다 — 다른 FAB 위에 M14A 존이 선다
    hz = HIDZoneData().load(ent["hid_csv"]) if ent["hid_csv"] and os.path.isfile(ent["hid_csv"]) \
        else HIDZoneData()
    print(f"[실시간] 지도 {fab}/{prefix}: 노드 {len(lay.nodes):,} · 엣지 {len(lay.edge_dist):,}"
          f" · 존 {len(hz.zones)}")
    with _LL:
        return _LAYOUTS.setdefault(key, (lay, hz))


# ── 로그프레소 ──────────────────────────────────────────────────────────
def _lq():
    """월드모델파생의 logpresso_query — 서버(SERVERS) · 키(API_KEY) · 쿼리 규칙을 같이 쓴다."""
    import logpresso_query as LQ
    return LQ


def key_tail() -> str:
    try:
        k = _lq().API_KEY or ""
    except Exception:                     # noqa: BLE001
        return "?"
    return ("…" + k[-4:]) if len(k) >= 4 else "없음"


def server_of(table: str) -> str:
    try:
        h, p = _lq().server_for(table)
        return f"{h}:{p}"
    except Exception as e:                # noqa: BLE001
        return f"? ({e})"


def fetch_rows(table: str, start: datetime, end: datetime) -> list:
    """[start, end) 를 '상세' 쿼리로 묻는다 → CSV 줄(dict) 목록.

    ★키는 주소에 실려 가므로 주소를 통째로 찍지 않는다 (끝 4자만)."""
    LQ = _lq()
    if not LQ.API_KEY:
        raise RuntimeError("로그프레소 API 키가 없습니다 — 월드모델파생/logpresso_query.py 의 API_KEY, "
                           "환경변수 LP_API_KEY, 또는 관제 config.json 의 api_key")
    host, port = LQ.server_for(table)
    q = LQ._build_query(start.strftime(FMT), end.strftime(FMT), table, "raw")
    url = (f"http://{host}:{port}/logpresso/httpexport/query.csv?_apikey={LQ.API_KEY}"
           f"&_q={urllib.parse.quote(q, safe='')}")
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SEC) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        body = e.read()[:300].decode("utf-8", "replace")
        hint = " — 키와 서버가 안 맞습니다 (키 끝 4자 " + key_tail() + ")" if e.code == 401 else ""
        raise RuntimeError(f"HTTP {e.code} {host}:{port}{hint} · {body}") from None
    except OSError as e:
        raise RuntimeError(f"{host}:{port} 접속 실패 — {e}") from None
    text = raw.decode("utf-8-sig", "replace")
    return list(csv.DictReader(io.StringIO(text))) if text.strip() else []


_TFMTS = ("%Y-%m-%d %H:%M:%S.%f%z", "%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S.%f",
          "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M")


def parse_time(s):
    """_time → datetime (data_loader.DateDataLoader._parse_time 과 같은 형식들)."""
    s = str(s or "").strip().strip('"')
    if not s:
        return None
    for f in _TFMTS:
        try:
            return datetime.strptime(s, f).replace(tzinfo=None)
        except ValueError:
            continue
    return None


def oht_alert_level(miss: int, jam: int, ht: int, total: int) -> str:
    """OHT 전조 판정 — 재생 엔진(replay_engine.oht_alert_level)과 같은 규칙."""
    a = OHT_ALERT
    if total and miss >= total * a["gap_ratio"] and jam == 0 and ht == 0:
        return "수집누락"
    if (miss >= a["confirm_miss"] and (jam > 0 or ht > 0)) or jam >= a["confirm_jam"] \
            or ht >= a["confirm_ht"]:
        return "확정"
    if miss >= a["alert_miss"] or jam >= a["alert_jam"] or ht >= a["alert_ht"]:
        return "경보"
    if (miss >= a["pre_miss"] and jam >= a["pre_jam"]) or ht >= a["pre_ht"]:
        return "전조"
    return "정상"


def _step_floor(t: datetime) -> datetime:
    return t.replace(microsecond=0) - timedelta(seconds=t.second % STEP_SEC)


# ── 피드 ────────────────────────────────────────────────────────────────
class LiveFeed:
    """지도 하나의 실시간 상태. fetch · clock 은 시험에서 바꿔 끼운다."""

    def __init__(self, fab: str, prefix: str, fetch=None, clock=None, wall=None):
        self.fab, self.prefix = fab, prefix
        self.table = table_for(fab, prefix)
        self.layout, self.hz = layout_for(fab, prefix)
        self.fetch = fetch or fetch_rows
        self.clock = clock or datetime.now          # 로그프레소에 묻는 '지금'
        self.wall = wall or time.time               # 재생 시계가 흐르는 벽시계
        self.lock = threading.Lock()
        self._thread = None
        self.last_view = self.wall()
        self.status = {"polls": 0, "rows_last": 0, "rows_total": 0, "error": None,
                       "error_at": None, "last_poll": None, "poll_ms": None, "fails": 0}
        self._reset()

    # 상태 초기화 — 처음 · 오래 끊긴 뒤
    def _reset(self):
        lay, hz = self.layout, self.hz
        adj = {n: [(nb, lay.edge_dist.get((n, nb), 1000.0)) for nb in nbs]
               for n, nbs in lay.adj.items()}
        self.world = WorldModel(graph=adj, edge_dist_map=lay.edge_dist,
                                zone_data=dict(hz.zones),
                                in_lane_to_zone=hz.in_lane_to_zone,
                                out_lane_to_zone=hz.out_lane_to_zone)
        self.state = {}             # vid → 마지막 상태
        self.seen = {}              # vid → 마지막 보고 시각
        self.cursor = None          # 받은 줄 중 가장 새 시각 (데이터 시계)
        self.frames = deque()       # [(t, snapshot)] 2초 칸, 최근 KEEP_SEC
        self.anchor = None          # (가장 새 프레임 시각, 그것이 도착한 벽시계)
        self.shown = None           # 화면에 마지막으로 내준 프레임 시각 — 뒤로 가지 않게

    # ── 묻기 ──
    def poll_once(self) -> int:
        now = self.clock()
        warm = self.cursor is None or (now - self.cursor).total_seconds() > MAX_GAP_SEC
        start = now - timedelta(seconds=WARM_SEC) if warm else self.cursor - timedelta(seconds=OVERLAP_SEC)
        t0 = time.perf_counter()
        rows = self.fetch(self.table, start, now + timedelta(seconds=1))
        with self.lock:
            if warm and self.cursor is not None:
                print(f"[실시간] {self.fab}/{self.prefix} {int((now - self.cursor).total_seconds())}초 "
                      f"끊겼다 — 처음부터 다시 받습니다")
                self._reset()
            n = self._ingest(rows)
            st = self.status
            st.update(polls=st["polls"] + 1, rows_last=len(rows), rows_total=st["rows_total"] + len(rows),
                      error=None, last_poll=now.strftime("%H:%M:%S"), fails=0,
                      poll_ms=int((time.perf_counter() - t0) * 1000), warm=warm)
        return n

    def _ingest(self, rows: list) -> int:
        """줄 → 차량 상태. 차마다 '마지막으로 본 시각' 보다 새 줄만 얹는다 (겹쳐 물은 줄 · 늦게 온 옛 줄)."""
        ups = []
        for r in rows:
            t = parse_time(r.get("_time"))
            if t is None:
                continue
            p = parse_oht_data_m14a_row(r, t)
            if not p or not p.get("vid"):
                continue
            ups.append(p)
        ups.sort(key=lambda p: p["_time"])
        if not ups:
            return 0
        last_frame = self.frames[-1][0] if self.frames else None
        keep_from = ups[-1]["_time"] - timedelta(seconds=KEEP_SEC)
        applied = 0
        i = 0
        while i < len(ups):
            step = _step_floor(ups[i]["_time"])
            j = i
            fresh = False
            ft = step
            while j < len(ups) and _step_floor(ups[j]["_time"]) == step:
                p = ups[j]
                prev = self.seen.get(p["vid"])
                if prev is None or p["_time"] > prev:
                    self.state[p["vid"]] = p
                    self.seen[p["vid"]] = p["_time"]
                    applied += 1
                    fresh = True
                ft = max(ft, p["_time"].replace(microsecond=0))   # 그 칸에서 본 가장 새 시각
                j += 1
            if fresh:
                # 시간 순서로 월드모델에 얹는다 — 재생과 같은 방식으로 속도를 잰다
                self.world.load_vehicles_from_frame(list(self.state.values()), ft)
                if ft >= keep_from and (last_frame is None or ft > last_frame):
                    self.frames.append((ft, self._snapshot(ft)))
                    last_frame = ft
            i = j
        if self.cursor is None or ups[-1]["_time"] > self.cursor:
            self.cursor = ups[-1]["_time"]
        while self.frames and self.frames[0][0] < self.frames[-1][0] - timedelta(seconds=KEEP_SEC):
            self.frames.popleft()
        if self.frames and (self.anchor is None or self.frames[-1][0] > self.anchor[0]):
            self.anchor = (self.frames[-1][0], self.wall())
        return applied

    # ── 스냅샷 (재생 엔진 get_current_snapshot 과 같은 모양) ──
    def _snapshot(self, t: datetime) -> dict:
        w, lay, hz = self.world, self.layout, self.hz
        vs = w.get_vehicle_stats()
        pos = w.get_vehicle_positions(lay)
        miss_n = idle_n = jam_live = ht_live = 0
        for p in pos:
            ls = self.seen.get(p["vid"])
            ms = int((t - ls).total_seconds()) if ls else 0
            p["missSec"] = ms
            p["missing"] = MISS_SEC <= ms < IDLE_SEC
            p["idle"] = ms >= IDLE_SEC
            if p["missing"]:
                miss_n += 1
            elif p["idle"]:
                idle_n += 1
            elif p.get("state") == 7:
                jam_live += 1
            elif p.get("state") == 8:
                ht_live += 1
            c = self.state.get(p["vid"]) or {}
            if c.get("carrierId"):
                p["carrierId"] = c["carrierId"]
        vs.update(missing=miss_n, idle=idle_n, ht_stop=ht_live, jam_live=jam_live,
                  ohtAlert={"level": oht_alert_level(miss_n, jam_live, ht_live, len(pos) - idle_n),
                            "miss": miss_n, "jam": jam_live, "ht": ht_live, "missSec": MISS_SEC})
        zc = {}
        for v in self.state.values():
            e = (v.get("currentNode", 0), v.get("nextNode", 0))
            z = hz.in_lane_to_zone.get(e)
            if z is None:
                z = hz.out_lane_to_zone.get(e)
            if z is not None:
                zc[z] = zc.get(z, 0) + 1
        return {
            "time": t.strftime("%Y-%m-%d %H:%M:%S"), "time_short": t.strftime("%H:%M:%S"),
            "frame": 0, "totalFrames": 0, "state": "playing", "speed": 1, "date": "LIVE",
            "vehicleStats": vs, "vehicles": pos, "star": None, "prediction": {},
            "hidSpeeds": {}, "railCuts": [], "zoneCounts": zc,
            "hotspots": w.get_deadlock_hotspots(lay),
        }

    # ── 화면에 내줄 칸 ──
    def current(self):
        """(프레임 시각, 스냅샷) — BUFFER_SEC 만큼 늦춘 재생 시계의 칸. 없으면 (None, None)."""
        with self.lock:
            if not self.frames:
                return None, None
            if BUFFER_SEC <= 0 or not self.anchor:
                t, snap = self.frames[-1]
            else:
                at, wall0 = self.anchor
                play = at - timedelta(seconds=BUFFER_SEC) + timedelta(seconds=self.wall() - wall0)
                if self.shown and play < self.shown:
                    play = self.shown                     # 화면 시각이 뒤로 가지 않게
                t, snap = self.frames[0]
                for ft, s in self.frames:
                    if ft <= play:
                        t, snap = ft, s
                    else:
                        break
            self.shown = t
            return t, snap

    def info(self, shown_t=None) -> dict:
        """화면 상태줄 — 조회 상태 · 지연."""
        now = self.clock()
        with self.lock:
            st = dict(self.status)
            newest = self.frames[-1][0] if self.frames else None
            nveh = len(self.state)
        return {
            "fab": self.fab, "prefix": self.prefix, "table": self.table,
            "server": server_of(self.table), "key": key_tail(),
            "poll_sec": POLL_SEC, "buffer_sec": BUFFER_SEC, "miss_sec": MISS_SEC,
            "now": now.strftime("%H:%M:%S"),
            "data_time": newest.strftime("%Y-%m-%d %H:%M:%S") if newest else None,
            "shown_time": shown_t.strftime("%Y-%m-%d %H:%M:%S") if shown_t else None,
            "lag_sec": int((now - shown_t).total_seconds()) if shown_t else None,
            "data_lag_sec": int((now - newest).total_seconds()) if newest else None,
            "vehicles": nveh, "running": self.running(),
            **{k: st.get(k) for k in ("polls", "rows_last", "rows_total", "error", "error_at",
                                      "last_poll", "poll_ms", "fails", "warm")},
        }

    # ── 돌리기 ──
    def touch(self):
        self.last_view = self.wall()
        if not self.running():
            self.start()

    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self):
        with self.lock:
            if self._thread and self._thread.is_alive():
                return
            self._thread = threading.Thread(target=self._loop, daemon=True,
                                            name=f"live-{self.fab}-{self.prefix}")
            self._thread.start()
        print(f"[실시간] {self.fab}/{self.prefix} 조회 시작 - {self.table} @ {server_of(self.table)} "
              f"· {POLL_SEC:g}초마다 · 키 {key_tail()}")

    def tick(self) -> float:
        """한 번 묻는다 → 다음까지 기다릴 초. 실패하면 상태에 적고 점점 천천히 (최대 1분)."""
        try:
            self.poll_once()
            return POLL_SEC
        except Exception as e:                        # noqa: BLE001
            with self.lock:
                st = self.status
                st["fails"] = st.get("fails", 0) + 1
                st["error"] = f"{type(e).__name__}: {e}"[:400]
                st["error_at"] = self.clock().strftime("%H:%M:%S")
                n = st["fails"]
            print(f"[실시간] {self.fab}/{self.prefix} 조회 실패 ({n}번째): {st['error']}")
            return min(POLL_SEC * (2 ** n), 60.0)

    def _loop(self):
        while True:
            if self.wall() - self.last_view > IDLE_STOP_SEC:
                print(f"[실시간] {self.fab}/{self.prefix} {IDLE_STOP_SEC}초 동안 보는 사람이 없어 조회를 멈춥니다")
                return
            time.sleep(self.tick())


_FEEDS: dict = {}
_FL = threading.Lock()


def feed_for(fab: str, prefix: str) -> LiveFeed:
    """그 지도의 피드 (없으면 만든다) — 보는 사람이 몇이든 하나다. 부를 때마다 '보고 있음' 표시."""
    key = (fab, prefix)
    with _FL:
        f = _FEEDS.get(key)
    if f is None:
        f = LiveFeed(fab, prefix)                   # 지도 읽기는 잠금 밖에서 (오래 걸린다)
        with _FL:
            f = _FEEDS.setdefault(key, f)
    f.touch()
    return f
