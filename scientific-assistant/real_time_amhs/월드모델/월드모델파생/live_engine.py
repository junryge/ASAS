#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
live_engine.py — 월드모델파생 '실시간' 모드: 로그프레소 '지금' 데이터를 몇 초마다 받아 월드모델 상태로.

고객 2026-10-06: "월드모델 파생, OHT 실시간 같은 포트 사용하게 해 주라. 리플레이 모드 · 실시간 모드
변경 가능하게" · "10005번 포트" · "메인은 월드모델파생이 메인이야!"
  → 따로 띄우던 확인판(월드모델파생_실시간 · 10006)을 이 앱에 합쳤다. 서버는 main.py 하나(10005),
    화면도 하나(dashboard.html) — 화면 위 [리플레이 | 실시간] 으로 바꾼다 (static/js/live_mode.js).

★재생(리플레이)과 같은 것을 쓴다 — 따로 만들지 않는다.
    지도 · HID 존                        main.get_layout — 재생과 한 벌을 같이 쓴다 (use_layouts)
    줄 → 차량 상태                       data_loader.parse_oht_data_m14a_row
    위치 · 속도 · 정체 묶음              world_model.WorldModel
    미보고 · HT_STOP · 전조 판정 기준    config.MISS_SEC · IDLE_SEC · OHT_ALERT (재생과 같은 기준)
    로그프레소 서버 · 키 · 쿼리          logpresso_query (SERVERS · API_KEY · '상세' 쿼리)
  그래서 현장 판정 기준 · 서버 주소 · 키를 한 곳에서 고치면 리플레이 · 실시간 둘 다 바뀐다.

어떻게 도나 — FAB(지도) 하나에 피드(LiveFeed) 하나, 보는 사람이 몇이든 같이 쓴다.
  · ★화면의 [▶ 실시간 PLAY] 를 눌러야 묻는다 · [■ 정지] 를 눌러야 멈춘다 (2026-10-06 고객:
    "PLAY 버튼 만들고 … 보는 사람 없어 조회를 멈춘다고 해서 좀 그래"). 저절로 멈추지 않는다.
    보는 FAB 하나만 돈다 — 화면에서 FAB 을 옮기거나 리플레이로 돌아가면 앞 FAB 은 놓는다(그 FAB 을
    PLAY 중인 다른 화면이 없으면 멈춘다). ("전부 다 조회하면 안 되니까")
    누가 무엇을 PLAY 중인지는 아래 _PLAYERS 가 화면(세션)마다 적어 둔다.
  · ★작게 묻는다 — 한 번에 STEP_SEC(60초)까지. 현장에서 5분치를 '지금' 까지 한 번에 묻다가
    응답이 중간에 끊겼다 (IncompleteRead · 0.8~1.7MB 받고 끊김) — 그리고 끊길 때마다 같은
    큰 조회를 다시 했다.
      처음        지금부터 STEP_SEC 만 → 바로 보인다
      그다음      POLL_SEC(5초)마다 [마지막 시각 − OVERLAP_SEC, 지금] (밀렸으면 STEP_SEC 씩 따라잡기)
      거꾸로 채움 묻을 때마다 STEP_SEC 씩 WARM_SEC(5분)까지 — 멈춰 있어 보고가 드문 차까지
    끊긴 응답은 **받은 데까지 쓴다** (시간순이라 앞부분은 온전하다) — 다음엔 거기서부터 묻는다.
    JUMP_SEC(60초) 넘게 못 물었으면(정지했다 다시 PLAY · 실패가 이어짐) 1분씩 따라잡지 않고
    지금으로 건너뛴다 — 그 사이 구멍은 거꾸로 채운다. (따라잡으면 화면 시각이 크게 여러 번 뛴다)
    실패하면 묻는 폭을 반으로 (최소 10초), 되면 다시 넓힌다.
    '지금' 의 끝 EDGE_SEC(3초)는 묻지 않는다 — 적재 중인 끝이다.
  · 겹쳐 묻는 OVERLAP 은 로그프레소에 **늦게 들어온 줄**을 받으려는 것이다. 같은 줄을
    두 번 받으면 차마다 '마지막으로 본 시각' 보다 새 것만 얹는다.
  · 받은 줄은 재생 엔진과 똑같이 **2초 칸**으로 묶어 시간 순서대로 얹는다 — 속도(m/min)를
    재는 방법이 같아야 재생과 같은 그림이 나온다.
  · 칸마다 스냅샷(재생 엔진 get_current_snapshot 과 같은 모양)을 만들어 최근 3분을 들고 있다.
    화면에는 웹소켓(/ws)이 1초마다 실어 보낸다 — 리플레이와 같은 관이다 (main.py).
  · 화면에는 BUFFER_SEC 만큼 **늦춰서** 2초 칸을 차례로 내준다 — 5초마다 한 번에 도착한
    줄을 그대로 보이면 차가 5초마다 뛴다. 늦춘 만큼은 화면 상태줄에 '지연' 으로 적는다.
    BUFFER_SEC=0 이면 늘 가장 새 칸을 준다 (부드러움 대신 빠름).
  · 미보고는 **데이터 시계**로 잰다 (벽시계가 아니다). 로그프레소 적재가 통째로 1분 늦으면
    벽시계로는 모든 차가 미보고가 된다 — 그건 차의 일이 아니라 수집의 일이라, 상태줄의
    '지연' 으로 따로 보인다.
"""

import csv
import http.client
import io
import json
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
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import config as WC                                            # noqa: E402
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
STEP_Q_SEC = _env("LIVE_STEP_SEC", 60, int)      # 한 번에 묻는 최대 폭 (초) — 크게 물으면 응답이 끊긴다
EDGE_SEC = _env("LIVE_EDGE_SEC", 3, int)           # '지금' 의 끝 몇 초는 묻지 않는다 (적재 중)
JUMP_SEC = _env("LIVE_JUMP_SEC", 60, int)          # 이만큼 못 물었으면(정지 · 실패) 따라잡지 않고 '지금' 으로
TIMEOUT_SEC = _env("LIVE_TIMEOUT_SEC", 60, int)    # 로그프레소 한 번 묻는 데 기다리는 한도
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
    """[{fab, prefix, table, zip, cache, hid_csv}] — 카탈로그(MAP/*.layout.zip)에 이미 만들어진
    캐시(OHT_MAP/cache)를 더한다. 현장은 zip 이, 저장소는 캐시만 있다 (시험은 캐시로 돈다)."""
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


# ── 지도 읽기 ───────────────────────────────────────────────────────────
# ★서버(main.py)는 재생과 **같은** 지도를 쓴다 — use_layouts(get_layout). M14A 만 해도 노드 9,403 ·
#   엣지 10,424 라, 리플레이 · 실시간이 따로 읽으면 메모리와 시간이 두 배로 든다. 존(HID Zone)도
#   재생과 같은 것이 선다. 아래 제 읽기(_own_layout)는 서버 없이 이 파일만 쓸 때(시험)의 길이다.
_LAYOUT_SRC = None
_LAYOUTS: dict = {}
_LL = threading.Lock()


def use_layouts(fn):
    """지도 읽는 길을 바꿔 끼운다 — fn(fab, prefix) → (layout, hid_zones)."""
    global _LAYOUT_SRC
    _LAYOUT_SRC = fn


def layout_for(fab: str, prefix: str):
    """(layout, hid_zones) — FAB 마다 한 벌만 읽어 같이 쓴다 (읽기만 하는 자료다)."""
    if _LAYOUT_SRC is not None:
        return _LAYOUT_SRC(fab, prefix)
    return _own_layout(fab, prefix)


def _own_layout(fab: str, prefix: str):
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
    """리플레이 조회와 같은 logpresso_query — 서버(SERVERS) · 키(API_KEY) · 쿼리 규칙을 같이 쓴다."""
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


class Rows(list):
    """fetch_rows 결과. cut = 응답이 중간에 끊겨 받은 데까지만 담겼다."""
    cut = False
    cut_bytes = 0


def fetch_rows(table: str, start: datetime, end: datetime) -> list:
    """[start, end) 를 '상세' 쿼리로 묻는다 → CSV 줄(dict) 목록 (Rows).

    ★키는 주소에 실려 가므로 주소를 통째로 찍지 않는다 (끝 4자만).
    ★응답이 중간에 끊기면(IncompleteRead) 받은 데까지 쓴다 — 쿼리가 시간순(sort _time)이라
      앞부분은 온전하다. 마지막 줄은 반쯤 잘렸을 수 있어 버린다. (현장 2026-10-06:
      'IncompleteRead(801577 bytes read)' 로 실패만 되풀이했다)"""
    LQ = _lq()
    if not LQ.API_KEY:
        raise RuntimeError("로그프레소 API 키가 없습니다 — 월드모델파생/logpresso_query.py 의 API_KEY, "
                           "환경변수 LP_API_KEY, 또는 관제 config.json 의 api_key")
    host, port = LQ.server_for(table)
    q = LQ._build_query(start.strftime(FMT), end.strftime(FMT), table, "raw")
    url = (f"http://{host}:{port}/logpresso/httpexport/query.csv?_apikey={LQ.API_KEY}"
           f"&_q={urllib.parse.quote(q, safe='')}")
    cut = False
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SEC) as r:
            try:
                raw = r.read()
            except http.client.IncompleteRead as e:
                raw, cut = e.partial or b"", True
    except urllib.error.HTTPError as e:
        body = e.read()[:300].decode("utf-8", "replace")
        hint = " — 키와 서버가 안 맞습니다 (키 끝 4자 " + key_tail() + ")" if e.code == 401 else ""
        raise RuntimeError(f"HTTP {e.code} {host}:{port}{hint} · {body}") from None
    except OSError as e:
        raise RuntimeError(f"{host}:{port} 접속 실패 — {e}") from None
    text = raw.decode("utf-8-sig", "replace")
    if cut:
        text = text[:text.rfind("\n") + 1]           # 반쯤 잘린 마지막 줄은 버린다
    out = Rows(csv.DictReader(io.StringIO(text)) if text.strip() else [])
    out.cut, out.cut_bytes = cut, len(raw)
    return out


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
        self.playing = False                        # [▶ 실시간 PLAY] 를 눌러야 True
        self.last_view = self.wall()
        self.step = STEP_Q_SEC                      # 지금 묻는 폭 — 실패하면 줄이고 되면 넓힌다
        self._ok_wall = None                        # 마지막으로 물어서 된 벽시계 — 오래 쉬었나
        self.json_cache = None                      # (칸, 그 칸의 글자) — 여럿이 보면 한 번만 만든다
        self.status = {"polls": 0, "rows_last": 0, "rows_total": 0, "error": None,
                       "error_at": None, "last_poll": None, "poll_ms": None, "fails": 0,
                       "cuts": 0, "cut_at": None}
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
        self.back_to = None         # 거꾸로 채운 데까지 (이 시각 앞은 아직 안 물었다)
        self.warm_until = None      # 거꾸로 채울 끝 (처음 받은 시각 − WARM_SEC)

    # ── 묻기 ──
    def poll_once(self) -> int:
        """한 번 묻는다 — 새 줄(작게) + 거꾸로 채움(작게). 얹은 줄 수."""
        now = self.clock()
        live_end = now - timedelta(seconds=EDGE_SEC)
        gap = (now - self.cursor).total_seconds() if self.cursor else None
        first = self.cursor is None or gap > MAX_GAP_SEC
        # ★오래 못 물었으면(정지했다 다시 PLAY · 실패가 이어짐) 밀린 것을 1분씩 따라잡지 않고 **지금으로
        #   건너뛴다** — 따라잡으면 화면 시각이 몇 번에 걸쳐 크게 뛴다 (고객: "갑자기 늘었다 다시 과거로
        #   가고 그러면 안 돼"). 그 사이 구멍은 거꾸로 채우기로 메운다 (멈춰 있던 차의 마지막 보고).
        #   ★벽시계로 잰다 — 데이터 시각으로 재면 로그프레소 적재가 늦을 때마다 건너뛴다.
        idle = (self.wall() - self._ok_wall) if self._ok_wall else 0.0
        jump = not first and idle > JUMP_SEC
        old_cursor = self.cursor
        if first or jump:
            start = live_end - timedelta(seconds=self.step)
            end = live_end
        else:
            start = self.cursor - timedelta(seconds=OVERLAP_SEC)
            end = min(live_end, start + timedelta(seconds=self.step + OVERLAP_SEC))   # 밀렸으면 조금씩 따라잡기
        t0 = time.perf_counter()
        try:
            rows = self.fetch(self.table, start, end)
        except Exception:
            self.step = max(10, self.step // 2)          # 실패하면 묻는 폭을 반으로
            raise
        with self.lock:
            if first and self.cursor is not None:
                print(f"[실시간] {self.fab}/{self.prefix} {int(gap)}초 끊겼다 — 처음부터 다시 받습니다")
                self._reset()
            n = self._ingest(rows)
            if first and rows:
                self.back_to, self.warm_until = start, live_end - timedelta(seconds=WARM_SEC)
            elif jump:
                print(f"[실시간] {self.fab}/{self.prefix} {int(idle)}초 쉬었다가 다시 — 지금으로 건너뛰고 "
                      f"그 사이는 거꾸로 채웁니다")
                self.back_to = start
                self.warm_until = max(old_cursor - timedelta(seconds=OVERLAP_SEC),
                                      live_end - timedelta(seconds=WARM_SEC))
            st = self.status
            st.update(polls=st["polls"] + 1, rows_last=len(rows), rows_total=st["rows_total"] + len(rows),
                      error=None, last_poll=now.strftime("%H:%M:%S"), fails=0,
                      poll_ms=int((time.perf_counter() - t0) * 1000), warm=first, jumped=jump)
            self._ok_wall = self.wall()
            self._note_cut(rows, now)
        if not getattr(rows, "cut", False):
            self.step = min(STEP_Q_SEC, int(self.step * 1.5) + 1)
        n += self._backfill(now)
        return n

    def _backfill(self, now) -> int:
        """처음 받은 시각에서 WARM_SEC 까지 거꾸로, 한 번에 self.step 씩 — 멈춰 있어 보고가 드문 차.
        ★실패해도 새 줄(위)은 이미 얹었다 — 채움만 다음에 다시 한다."""
        with self.lock:
            b1, until = self.back_to, self.warm_until
        if not b1 or not until or b1 <= until:
            return 0
        b0 = max(until, b1 - timedelta(seconds=self.step))
        try:
            rows = self.fetch(self.table, b0, b1)
        except Exception as e:                        # noqa: BLE001
            self.step = max(10, self.step // 2)
            print(f"[실시간] {self.fab}/{self.prefix} 거꾸로 채우기 실패 — 다음에 다시 ({type(e).__name__})")
            return 0
        with self.lock:
            n = self._ingest(rows)
            if getattr(rows, "cut", False) and rows:
                # 끊겼으면 받은 데까지만 채운 것으로 친다 (앞에서부터 시간순이다)
                t = max((parse_time(r.get("_time")) for r in rows), default=None)
                self.back_to = max(b0, t) if t and t < b1 else b0
            else:
                self.back_to = b0
            self._note_cut(rows, now)
        return n

    def _note_cut(self, rows, now):
        if getattr(rows, "cut", False):
            st = self.status
            st["cuts"] = st.get("cuts", 0) + 1
            st["cut_at"] = now.strftime("%H:%M:%S")
            print(f"[실시간] {self.fab}/{self.prefix} 로그프레소 응답이 중간에 끊겼습니다 — 받은 데까지 씁니다 "
                  f"({len(rows)}줄 · {getattr(rows, 'cut_bytes', 0):,}바이트) · 다음엔 {self.step}초씩")

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
            # 거꾸로 채운 폭 (처음 WARM_SEC 중 몇 초) — 상태줄에 '처음 5분 중 2분' 처럼
            filled = None
            if self.back_to and self.warm_until:
                filled = int(WARM_SEC - max(0.0, (self.back_to - self.warm_until).total_seconds()))
        return {
            "fab": self.fab, "prefix": self.prefix, "table": self.table,
            "server": server_of(self.table), "key": key_tail(),
            "poll_sec": POLL_SEC, "buffer_sec": BUFFER_SEC, "miss_sec": MISS_SEC,
            "now": now.strftime("%H:%M:%S"),
            "data_time": newest.strftime("%Y-%m-%d %H:%M:%S") if newest else None,
            "shown_time": shown_t.strftime("%Y-%m-%d %H:%M:%S") if shown_t else None,
            "lag_sec": int((now - shown_t).total_seconds()) if shown_t else None,
            "data_lag_sec": int((now - newest).total_seconds()) if newest else None,
            "vehicles": nveh, "running": self.running(), "playing": self.playing,
            "step_sec": self.step, "warm_sec": WARM_SEC, "filled_sec": filled,
            **{k: st.get(k) for k in ("polls", "rows_last", "rows_total", "error", "error_at",
                                      "last_poll", "poll_ms", "fails", "warm", "cuts", "cut_at")},
        }

    # ── 돌리기 — [▶ 실시간 PLAY] · [■ 정지] ──
    def touch(self):
        """누가 이 지도를 보고 있다 (상태줄용 기록일 뿐 — 이것으로 멈추거나 켜지 않는다)."""
        self.last_view = self.wall()

    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def play(self, why: str = ""):
        """묻기 시작 — 이미 돌고 있으면 그대로."""
        self.playing = True
        with self.lock:
            if self._thread and self._thread.is_alive():
                return
            self._thread = threading.Thread(target=self._loop, daemon=True,
                                            name=f"live-{self.fab}-{self.prefix}")
            self._thread.start()
        print(f"[실시간] {self.fab}/{self.prefix} ▶ PLAY{(' (' + why + ')') if why else ''} — "
              f"{self.table} @ {server_of(self.table)} · {POLL_SEC:g}초마다 · 키 {key_tail()}")

    def stop(self, why: str = ""):
        """묻기를 멈춘다 — 받아 둔 그림은 그대로 둔다 (다시 PLAY 하면 이어서 묻는다)."""
        if self.playing:
            print(f"[실시간] {self.fab}/{self.prefix} ■ 정지{(' (' + why + ')') if why else ''}")
        self.playing = False

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
            print(f"[실시간] {self.fab}/{self.prefix} 조회 실패 ({n}번째, 다음엔 {self.step}초씩): {st['error']}")
            return min(POLL_SEC * (2 ** n), 60.0)

    def _loop(self):
        while self.playing:
            end = time.time() + self.tick()
            while self.playing and time.time() < end:
                time.sleep(0.2)                       # ■ 정지를 누르면 바로 멈춘다


_FEEDS: dict = {}
_FL = threading.Lock()


def feed_for(fab: str, prefix: str) -> LiveFeed:
    """그 지도의 피드 (없으면 만든다) — 보는 사람이 몇이든 하나다.
    ★만들기만 한다. 묻기는 [▶ 실시간 PLAY] (feed.play) 를 눌러야 시작한다."""
    key = (fab, prefix)
    with _FL:
        f = _FEEDS.get(key)
    if f is None:
        f = LiveFeed(fab, prefix)                   # 지도 읽기는 잠금 밖에서 (오래 걸린다)
        with _FL:
            f = _FEEDS.setdefault(key, f)
    f.touch()
    return f


# ── 누가 어느 지도를 PLAY 중인가 — 화면(세션)마다 ──────────────────────────
# ★보는 FAB 하나만 묻는다 (고객: "전부 다 조회하면 안 되니까"). 한 화면은 한 지도만 PLAY 한다 —
#   지도를 옮기면 앞 지도는 놓는다. 그 지도를 PLAY 중인 화면이 하나도 안 남으면 피드를 멈춘다.
# ★여럿이 같은 지도를 보면 피드 하나를 같이 쓴다 — 한 사람이 정지해도 다른 사람 것은 그대로 돈다.
_PLAYERS: dict = {}          # (fab, prefix) → {sid, ...}
_PL = threading.Lock()


def playing_key(sid):
    """이 화면이 PLAY 중인 지도 (fab, prefix) — 없으면 None."""
    with _PL:
        return next((k for k, s in _PLAYERS.items() if sid in s), None)


def _drop_locked(sid, keep=None):
    """sid 를 keep 말고 다른 지도에서 뺀다 → 아무도 안 남은 지도들 (_PL 잠금 안에서 부른다)."""
    empty = []
    for k, s in _PLAYERS.items():
        if k != keep and sid in s:
            s.discard(sid)
            if not s:
                empty.append(k)
    for k in empty:
        _PLAYERS.pop(k, None)
    return empty


def _stop_feeds(keys, why):
    for k in keys:
        with _FL:
            f = _FEEDS.get(k)
        if f:
            f.stop(why)


def play(sid, fab: str, prefix: str, why: str = "") -> LiveFeed:
    """이 화면이 (fab, prefix) 를 PLAY. 앞에 PLAY 하던 다른 지도는 놓는다 (아무도 안 남으면 멈춘다)."""
    key = (fab, prefix)
    f = feed_for(fab, prefix)                     # 처음이면 지도를 읽느라 오래 걸린다 — 잠금 밖에서
    with _PL:
        empty = _drop_locked(sid, keep=key)
        _PLAYERS.setdefault(key, set()).add(sid)
    _stop_feeds(empty, f"화면이 {fab}/{prefix} 로 옮김")
    f.play(why)
    return f


def stop(sid, why: str = "■ 정지") -> list:
    """이 화면의 PLAY 를 놓는다. ★그 지도를 PLAY 중인 다른 화면이 있으면 피드는 그대로 돈다.
    리플레이로 돌아갈 때 · 접속이 오래 끊겨 세션을 치울 때도 이것을 부른다."""
    with _PL:
        empty = _drop_locked(sid)
    _stop_feeds(empty, why)
    return empty


def live_info(sid, fab: str, prefix: str, shown_t=None) -> dict:
    """화면 상태줄 — 피드 상태 + 이 화면이 PLAY 중인지 (me_playing)."""
    f = feed_for(fab, prefix)
    return dict(f.info(shown_t), me_playing=playing_key(sid) == (fab, prefix))


def snapshot(sid, fab: str, prefix: str) -> dict:
    """화면 한 장 — 재생 웹소켓이 보내던 것과 같은 모양 + 'live' (상태줄). 웹소켓이 1초마다 보낸다."""
    f = feed_for(fab, prefix)
    t, snap = f.current()
    out = dict(snap) if snap else {
        "time": "", "time_short": "--:--:--", "frame": 0, "totalFrames": 0, "state": "playing",
        "speed": 1, "date": "LIVE", "vehicleStats": {"total": 0}, "vehicles": [], "star": None,
        "prediction": {}, "hidSpeeds": {}, "railCuts": [], "zoneCounts": {}, "hotspots": []}
    out["live"] = live_info(sid, fab, prefix, t)
    return out


def snapshot_json(sid, fab: str, prefix: str) -> str:
    """웹소켓이 1초마다 보내는 글자 — snapshot() 과 같은 내용.

    ★여럿이 같은 FAB 을 보면 같은 장면을 사람마다 다시 글자로 바꾸지 않는다 (고객: "여러 사람이
      접속할 거야"). 차 수백 대면 장면 하나가 100KB 쯤이다 — 스무 명이면 1초에 2MB 를 다시 만든다.
      장면(칸) 하나는 한 번만 바꿔 피드에 걸어 두고, 사람마다 다른 상태줄('live' — 이 사람이
      PLAY 중인지 등)만 붙인다."""
    f = feed_for(fab, prefix)
    t, snap = f.current()
    live = json.dumps(live_info(sid, fab, prefix, t), default=str)
    if not snap:
        return json.dumps(snapshot(sid, fab, prefix), default=str)
    hit = f.json_cache
    if hit and hit[0] is snap:
        body = hit[1]
    else:
        body = json.dumps(snap, default=str)          # 'live' 는 없다 — 칸에는 안 넣는다
        f.json_cache = (snap, body)
    return body[:-1] + ', "live": ' + live + '}'


def status() -> dict:
    """조회 상태 한눈에 — 지도마다 피드 상태 · PLAY 중인 화면 수 (/api/live/status)."""
    with _FL:
        feeds = list(_FEEDS.values())
    with _PL:
        players = {f"{k[0]}/{k[1]}": len(s) for k, s in _PLAYERS.items()}
    return {"feeds": [f.info() for f in feeds], "players": players,
            "poll_sec": POLL_SEC, "step_sec": STEP_Q_SEC, "buffer_sec": BUFFER_SEC, "key": key_tail()}

