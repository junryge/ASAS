#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HID_PROBLEM_MAP.py — 로그프레소에서 그 시각을 판정해 "문제맵"(HTML 지도) 만들기

  FAB · 시각만 주면 로그프레소에서 차량 보고를 받아 HID_BOTTLENECK.py 와 **같은 쿼리 · 같은 판정**으로
  그 1분(ALARM · 병목 HID 구역 1~3위 · missing · JAM · HT_STOP · ZONE_STOP …)을 구하고,
  월드모델파생 맵(OHT_MAP 레이아웃 + HID_Zone_Master) 위에 그린다 — 그 시각 어디가 막혔나.
    · 왼쪽 위 ALARM 칸   = 경계 / 위험 / 초위험 / 정상
    · 1위 구역(HID_ZONE) = ALARM 색, 2 · 3위 구역 = 파랑
    · OHT 차량            = 그 시각 위치 — 월드모델파생 2D 맵과 같은 삼각형(진행 방향) · 같은 색 · 같은 점,
                            미보고는 끊기기 직전 위치에 ✕
    · 보기                = [▭ 2D] [◈ 유사 3D] [⬢ 아이소메트리] — 월드모델파생과 같은 세 가지 (아이소메트리 안에서 원근 3D)
    · 🔥 히트맵           = 정체 무리(12 m 안 멈춘 차)를 대수대로 노랑 → 짙은 적 — 세 보기 다 (월드모델파생 히트맵 비전 그대로)
    · 오른쪽              = 그 1분 숫자 · 판정 근거
  결과 CSV 는 필요 없다. 시각 하나 = HTML 파일 하나 (브라우저로 열면 됨, 인터넷 · 서버 필요 없음).

  필요한 것 (같은 폴더)
    HID_BOTTLENECK.py      서버 · 쿼리 · 판정 · 주소 → HID 구역을 그대로 가져다 쓴다
    hdi_api_key.txt      로그프레소 키 (HID_BOTTLENECK.py 와 같은 것)
    HID_CONFIG.json      경계 · 위험 · 초위험 기준 (HID_BOTTLENECK.py 와 같은 것)
    OHT_MAP/             월드모델파생의 OHT_MAP 폴더 그대로
    oht3d/               월드모델파생 static/js/oht3d 의 oht3d.js · three.module.min.js — 있으면 ⬢ 아이소메트리를 HTML 안에 넣는다
    HID_MAP_SETTINGS.json  지도 표시 기본값 (없으면 만든다) — 월드모델파생 ⚙ 설정과 같은 이름 · 같은 기본값
                         vehicleRadius = OHT 크기 · 차량 색 · 테마(hmi/dark) … 지도 ⚙ 에서도 바로 바꿀 수 있다

  실행
    python HID_PROBLEM_MAP.py M16HUB                              지금 (방금 끝난 1분)
    python HID_PROBLEM_MAP.py M16HUB 202609031348                 그 1분 (YYYYMMDDHHMM)
    python HID_PROBLEM_MAP.py M16HUB 202609031348 202609290813    여러 시각 — 시각마다 파일 하나
    python HID_PROBLEM_MAP.py M16HUB 20260929                     그 날 하루를 판정해서 알람 난 분마다 파일 하나
      → HID_BOTTLENECK/PROBLEM_MAP/{FAB}_{YYYYMMDD}/PROBLEM_MAP_{FAB}_{YYYYMMDD}_{HHMM}_{ALARM}.html
         (ALARM = NORMAL 정상 · WARNING 경계 · DANGER 위험 · CRITICAL 초위험)
  판정은 그 시각 앞 100분(FLEET_AUTO_MIN)부터 받아서 한다 — 미보고(전체 차량) 셈이 HID_BOTTLENECK.py 와 같게.
"""
import argparse
import heapq
import csv
import io
import json
import re
import sys
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import HID_BOTTLENECK as HB                           # noqa: E402  (서버 · 쿼리 · 판정 · 맵을 그대로 쓴다)

LEVEL = {"경계": 1, "위험": 2, "초위험": 3}
ALARM_EN = {"정상": "NORMAL", "경계": "WARNING", "위험": "DANGER", "초위험": "CRITICAL"}   # 파일 이름은 영문
RANK = {None: 0, "경계": 1, "위험": 2, "초위험": 3}
MAP_OUT = HB.OUT_DIR / "PROBLEM_MAP"
STEP = timedelta(seconds=HB.BUCKET_SEC)


def say(msg):
    print(msg, flush=True)


# ==========================================================
# 월드모델파생 맵 → 지도 그림 재료
# ==========================================================
def load_map(fab):
    """HID_BOTTLENECK.py 와 똑같이 주소 → 구역을 만들고, HID_BOTTLENECK.py 와 같은 HID_ZONE 번호를 붙인다."""
    cfg = HB.FABS[fab]
    st = HB.FabState(fab, cfg)
    if not st.ok:
        return None, st.map_msg
    states = {fab: st}
    if fab != "M16HUB":                              # 번호 칸(ZONE_ID/ZONE_ID2)은 M16HUB 참조표로 정해진다
        hub = HB.FabState("M16HUB", HB.FABS["M16HUB"])
        if hub.ok:
            states["M16HUB"] = hub
    HB.resolve_hid_zone(states)
    _, layout = HB._find_map_files(*cfg["map"])
    L = json.loads(Path(layout).read_text(encoding="utf-8"))
    return {"st": st, "layout": L, "layout_file": Path(layout).name, "msg": st.map_msg}, ""


def zone_number(st, z, use):
    if use == "ZONE_ID2":
        return str(st.info.get(z, ("", "", "", 0))[2] or 0)
    return str(z or 0)



def geometry(m, use):
    st, L = m["st"], m["layout"]
    nodes = L.get("nodes", {})
    num = {z: zone_number(st, z, use) for z in st.info}
    ids, xs, ys, index = [], [], [], {}

    def idx(a):
        a = str(a)
        if a not in index and a in nodes:
            index[a] = len(ids)
            ids.append(a)
            xs.append(round(float(nodes[a][0]), 1))
            ys.append(round(float(nodes[a][1]), 1))
        return index.get(a)

    zlist = sorted({n for n in num.values() if n != "0"}, key=lambda s: (len(s), s))
    zi = {n: i for i, n in enumerate(zlist)}
    edges = []
    for k in L.get("edges", {}):
        a, _, b = str(k).partition(",")
        ia, ib = idx(a), idx(b)
        if ia is None or ib is None:
            continue
        za, zb = st.zone_of.get(a), st.zone_of.get(b)
        z = num.get(za) if za is not None and za == zb else None
        edges += [ia, ib, zi.get(z, -1) if z else -1]
    # 구역 정보 · 가운데 점 (라벨 · 클릭)
    acc = {n: [0.0, 0.0, 0, 1e18, 1e18, -1e18, -1e18] for n in zlist}
    for a, z in st.zone_of.items():
        n = num.get(z)
        if n in acc and str(a) in nodes:
            x, y = float(nodes[str(a)][0]), float(nodes[str(a)][1])
            c = acc[n]
            c[0] += x
            c[1] += y
            c[2] += 1
            c[3], c[4], c[5], c[6] = min(c[3], x), min(c[4], y), max(c[5], x), max(c[6], y)
    meta = {}
    for z, (name, bay, _, vmax) in st.info.items():
        n = num[z]
        if n != "0" and n not in meta:
            meta[n] = (name, bay, vmax)
    zones = []
    for n in zlist:
        sx, sy, c, x0, y0, x1, y1 = acc[n]
        name, bay, vmax = meta.get(n, ("", "", 0))
        zones.append({"id": n, "name": name, "bay": bay, "vmax": vmax, "n": c,
                      "cx": round(sx / c, 1) if c else None, "cy": round(sy / c, 1) if c else None,
                      "box": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)] if c else None})
    lanes = []                                       # [from, to, 구역, OUT?] — 월드모델파생 2D 의 HID 존 진입(실선) · 진출(점선)
    master, _ = HB._find_map_files(*st.cfg["map"])
    try:
        try:
            text = Path(master).read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            text = Path(master).read_text(encoding="cp949")
        rd = csv.DictReader(io.StringIO(text))
        cols = {c.strip().lower().replace(" ", "_"): c for c in (rd.fieldnames or [])}
        for r in rd:
            z = (r.get(cols.get("zone_id", ""), "") or "").strip()
            if not z or z == "0":
                continue
            n = zone_number(st, z, use)
            for key, out in (("in_lanes", 0), ("out_lanes", 1)):
                for a, b in HB._lanes(r.get(cols.get(key, ""), "") or ""):
                    ia, ib = idx(a), idx(b)
                    if ia is not None and ib is not None:
                        lanes.append([ia, ib, zi.get(n, -1), out])
    except Exception:
        pass
    m["_ids"] = ids
    return {"x": xs, "y": ys, "e": edges, "zones": zones, "lanes": lanes, "ids": ids}



# ==========================================================
# 로그프레소에서 판정 — HID_BOTTLENECK.py 와 같은 쿼리 · 같은 판정 · 같은 1분 줄
# ==========================================================
def _parse(body, seen):
    """조회 결과 → seen[구간][차량] = (상태들, 주소)"""
    for x in csv.DictReader(io.StringIO(body.decode("utf-8-sig", "replace"))):
        v, tt = (x.get("VEHICLE") or "").strip(), HB.parse_time(x.get("_time"))
        if v and tt:
            sts = {(x.get("STATUS") or "").strip(), (x.get("STATUS_LAST") or "").strip()}
            seen[HB.bucket_floor(tt)][v] = (sts, (x.get("ADDRESS") or "").strip())


def _vehicles(seen, b):
    """구간 b 의 차량 → [[차량, 상태(0 운행 · 1 JAM · 2 HT · 3 미보고), 주소]]
       미보고 = 그 구간에 보고 없고, 최근 30분(IDLE_MIN) 안에 보였고, 구간 2개 이상에서 보인 차 (HID_BOTTLENECK.py 와 같은 조건)"""
    rep = seen.get(b, {})
    last, cnt = {}, defaultdict(int)
    for k in sorted(seen):
        if k > b:
            break
        for v, (_, a) in seen[k].items():
            last[v] = (k, a)
            cnt[v] += 1
    out = [[v, 1 if "7" in sts else 2 if "8" in sts else 0, a] for v, (sts, a) in rep.items()]
    idle = b - timedelta(minutes=HB.IDLE_MIN)
    out += [[v, 3, a] for v, (lb, a) in last.items() if v not in rep and lb >= idle and cnt[v] >= HB.FLEET_MIN_SEEN]
    return out


SPEED_CAP_MM = 400_000          # 50초에 400 m 넘게는 안 찾는다 (그보다 멀면 속도 모름)


def _speed(m, a0, a1):
    """주소 a0 → a1 을 레일 방향대로 간 가장 짧은 거리(mm) ÷ 50초 → m/min. 같은 자리면 0, 못 찾으면 None"""
    if not a0 or not a1:
        return None
    if a0 == a1:
        return 0
    adj = m.setdefault("_adjw", None)
    if adj is None:
        adj = defaultdict(list)
        for k, mm in m["layout"].get("edges", {}).items():
            a, _, b = str(k).partition(",")
            adj[a].append((b, float(mm)))
        m["_adjw"] = adj
    dist, q = {a0: 0.0}, [(0.0, a0)]
    while q:
        d, n = heapq.heappop(q)
        if n == a1:
            return round(d / 1000 / HB.BUCKET_SEC * 60)
        if d > dist.get(n, 1e18) or d > SPEED_CAP_MM:
            continue
        for b, w in adj.get(n, ()):
            nd = d + w
            if nd < dist.get(b, 1e18) and nd <= SPEED_CAP_MM:
                dist[b] = nd
                heapq.heappush(q, (nd, b))
    return None


def _best_bucket(st, mm):
    """HID_BOTTLENECK.py minute_row 가 고르는 구간 (그 분 안에 끝난 구간 중 가장 높은 단계, 같으면 나중)"""
    best, level = None, None
    for k in st.buckets_of_minute(mm) or [st.bucket_of_minute(mm)]:
        lv, _ = st.alarm(k)
        if best is None or RANK[lv] >= RANK[level]:
            best, level = k, lv
    return best


def _row_dict(row):
    g = lambda i: str(row[i])
    return {"t": f"{row[0]} {row[1]}", "alarm": row[7], "z1": g(2), "z2": g(13), "z3": g(14), "sect": g(8),
            "n": row[3], "miss": row[4], "jam": row[5], "ht": row[6],
            "zstop": row[9], "zvhl": row[10], "vmax": row[11], "occ": row[12]}


def judge(m, frm, to, keep=lambda r: True):
    """frm ~ to(미포함) 의 1분들을 로그프레소에서 받아 판정 → [(줄, 차량, 구간)] (keep 이 참인 줄만)"""
    st = m["st"]
    st.buckets.clear(); st.last.clear(); st.first.clear(); st.nseen.clear()
    cur = HB.bucket_floor(frm - timedelta(minutes=HB.FLEET_AUTO_MIN))
    end = HB.bucket_floor(to) + STEP
    mins, mm = [], frm
    while mm < to:
        mins.append(mm)
        mm += timedelta(minutes=1)
    seen, out = defaultdict(dict), []
    while cur < end:
        nxt = min(HB.bucket_floor(cur + timedelta(minutes=HB.RANGE_CHUNK_MIN)), end)
        if nxt <= cur:
            nxt = cur + STEP
        body = st.fetch(cur, nxt, HB.RANGE_TIMEOUT)
        _parse(body, seen)
        st.ingest(body, cur, nxt)
        while mins and mins[0] + timedelta(seconds=60) <= nxt:
            mm = mins.pop(0)
            row, _ = st.minute_row(mm)
            r = _row_dict(row)
            if keep(r):
                b = _best_bucket(st, mm)
                vs = _vehicles(seen, b) if b in seen else []
                prev = seen.get(b - STEP, {}) if b is not None else {}
                for x in vs:                         # 50초 평균 속도 (m/min) — 3D 히트맵 · 차량 정보
                    x.append(_speed(m, prev[x[0]][1], x[2]) if (x[1] != 3 and x[0] in prev) else None)
                out.append((r, vs, b))
        old = nxt - timedelta(minutes=HB.IDLE_MIN + 10)
        for k in [k for k in seen if k < old]:
            del seen[k]
        cur = nxt
    return out


DETAIL_COLS = ["ADDRESS", "NEXT_ADDRESS", "STATUS", "STOCK_INFO", "VEHICLE_EXECUTE_CYCLE", "DESTINATION"]


def fetch_detail(st, b):
    """그 50초 구간 차량의 상세 — 월드모델파생 쿼리(logpresso_query.py)와 같은 칸.
       진행 방향(ADDRESS → NEXT_ADDRESS) · 적재(STOCK_INFO) · 사이클(점) · 목적지. 판정에는 안 쓴다 (그림만)."""
    inner = (f"table from={b:%Y%m%d%H%M%S} to={b + STEP:%Y%m%d%H%M%S} {st.cfg['table']}"
             ' | search MSG_ID == "2" | sort _time'
             " | stats " + ", ".join(f"last({c}) as {c}" for c in DETAIL_COLS) + " by VEHICLE")
    remote = HB.SERVERS[st.cfg["server"]].get("remote")
    q = f"remote {remote} [ {inner} ]" if (st.use_remote and remote) else inner
    body = HB.lp_get(st.cfg["server"], q, HB.RANGE_TIMEOUT)
    out = {}
    for x in csv.DictReader(io.StringIO(body.decode("utf-8-sig", "replace"))):
        v = (x.get("VEHICLE") or "").strip()
        if v:
            out[v] = {c: (x.get(c) or "").strip() for c in DETAIL_COLS}
    return out


def _i(v, d=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return d


def place(m, vs, r, b, det=None):
    """차량 주소 → 지도 노드. → (차량 목록, 설명)
       차량 = [ID, 판정상태(0 운행 · 1 JAM · 2 HT · 3 미보고), 노드, 주소, STATUS, 다음노드, 적재, 사이클, 목적지, 속도(m/min · 모르면 null)]"""
    if b is None or not vs:
        return [], f"{r['t']} 구간 차량 보고 없음"
    idx = {a: i for i, a in enumerate(m["_ids"])}
    det = det or {}
    out, nopos = [], 0
    for v, c, a, spd in vs:
        i = idx.get(str(a))
        if i is None:
            nopos += 1
            continue
        d = det.get(v, {}) if c != 3 else {}
        nx = idx.get(d.get("NEXT_ADDRESS", ""), -1)
        out.append([v, c, i, a, _i(d.get("STATUS"), -1), nx, _i(d.get("STOCK_INFO")),
                    _i(d.get("VEHICLE_EXECUTE_CYCLE")), _i(d.get("DESTINATION")), spd])
    cnt = [sum(1 for x in vs if x[1] == c) for c in range(4)]
    return out, (f"{b:%H:%M:%S} 구간 · 운행 {cnt[0]} · JAM {cnt[1]} · HT_STOP {cnt[2]} · 미보고 {cnt[3]}"
                 + (f" · 맵에 없는 주소 {nopos}대" if nopos else ""))


# ==========================================================
# 판정 근거 — HID_CONFIG.json 기준 (판정에 쓴 그 기준)
# ==========================================================
def reasons(r, P):
    """그 줄 숫자가 어느 조건에 걸렸나 (높은 단계부터)"""
    out = []
    for lv in ("초위험", "위험", "경계"):
        p = P[lv]
        if p["missing"] and p["JAM"] and r["miss"] >= p["missing"] and r["jam"] >= p["JAM"]:
            out.append(f"{lv}: missing {r['miss']} + JAM {r['jam']} 같이 (기준 {p['missing']} + {p['JAM']})")
        if p["missing_ONLY"] and r["miss"] >= p["missing_ONLY"]:
            out.append(f"{lv}: missing {r['miss']} 단독 (기준 {p['missing_ONLY']})")
        if p["HT_STOP"] and r["ht"] >= p["HT_STOP"]:
            out.append(f"{lv}: HT_STOP {r['ht']} (기준 {p['HT_STOP']})")
        if p.get("ZONE_STOP") and r["zstop"] >= p["ZONE_STOP"]:
            out.append(f"{lv}: 구역 멈춘 차 {r['zstop']} (기준 {p['ZONE_STOP']})")
    return out


# ==========================================================
# 지도 표시 설정 — 월드모델파생 ⚙ 설정(DEFAULT_MAP_SETTINGS)과 같은 이름 · 같은 기본값
# ==========================================================
SETTINGS_FILE = HERE / "HID_MAP_SETTINGS.json"
DEFAULT_SETTINGS = OrderedDict([
    ("mapTheme", "hmi"),         # 'hmi' = 현장 HMI 처럼 밝게 | 'dark' = 어두운 맵 (월드모델파생과 같음)
    ("vehicleRadius", 3),        # ★OHT 크기 (월드모델파생 기본 3)
    ("railScale", 1.0),          # 레일 굵기 배수
    ("zoneScale", 1.0),          # 문제 구역(1~3위) 굵기 배수
    ("labelScale", 1.0),         # 글자 크기 배수
    ("colorEmpty", "#22c55e"),   # 공차 (초록)        ┐
    ("colorLoaded", "#22d3ee"),  # 적재 (하늘)        │ 월드모델파생 차량 색
    ("colorObs", "#f59e0b"),     # OBS               │ (STATUS 6 OBS · 7 JAM · 2/8/9 정지,
    ("colorStop", "#9ca3af"),    # 정지 (HT_STOP 포함) │  나머지는 적재 여부)
    ("colorJam", "#ef4444"),     # JAM               ┘
    ("colorMiss", "#111827"),    # 미보고 ✕ (끊기기 직전 위치)
    ("carryDot", "on"),          # 삼각형 안 점 — 검은 점 들고 감 · 흰 점 가지러 감
    ("dotLoaded", "#000000"),
    ("dotAssign", "#ffffff"),
    ("dotSize", 0.55),
    ("heat", "off"),             # 히트맵 — 처음엔 꺼짐 (🔥 단추로 켠다) (정체 무리 — 대수대로 노랑 → 주황 → 빨강 → 짙은 적, 20대 이상 제일 짙게)
    ("jamMinJam", 1),            # ┐ 정체 판정 '몇 대 이상' — 월드모델파생 ⚙ 설정 기본값 그대로
    ("jamMinObs", 0),            # │  JAM · OBS · 멈춘 차(2·8·9) · 미보고 · HT_STOP, 0 = 안 봄
    ("jamMinStop", 0),           # │  한 무리(12 m 안) 안에서 어느 한 종류라도 그 수를 넘으면 정체
    ("jamMinMiss", 3),           # │
    ("jamMinHt", 1),             # ┘
])
SETTINGS_HELP = ("지도 표시 기본값 — 월드모델파생 ⚙ 설정과 같은 이름. 지도 오른쪽 위 ⚙ 에서 바꾸면 그 브라우저에만 저장되고, "
                 "여기를 고치면 앞으로 만드는 지도 전부의 기본값이 됩니다. vehicleRadius = OHT 크기.")


def load_settings():
    cfg = OrderedDict(DEFAULT_SETTINGS)
    try:
        if SETTINGS_FILE.exists():
            got = json.loads(SETTINGS_FILE.read_text(encoding="utf-8-sig"))
            for k, d in DEFAULT_SETTINGS.items():
                v = got.get(k)
                if v is None:
                    continue
                cfg[k] = float(v) if isinstance(d, float) else int(v) if isinstance(d, int) else str(v)
        else:
            SETTINGS_FILE.write_text(json.dumps({"_설명": SETTINGS_HELP, **DEFAULT_SETTINGS}, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    except Exception as ex:
        say(f"  {SETTINGS_FILE.name} 읽기 실패 — 기본값으로: {ex}")
    return cfg


# ==========================================================
# HTML — 판정된 1분 = 지도 하나 (월드모델파생 2D 맵과 같은 모양)
# ==========================================================
def build_html(fab, r, geo, info, why, oht=None, oht_desc="", settings=None):
    data = {"fab": fab, "info": info, "geo": geo, "why": why, "oht": oht, "ohtd": oht_desc,
            "set": settings or DEFAULT_SETTINGS, "r": {**r, "lv": LEVEL.get(r["alarm"], 0)}}
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    title = f"HID 문제맵 · {fab} · {r['t']} · {r['alarm']}"
    o3d, three = v3d_sources()
    return (HTML.replace("__TITLE__", title).replace("__DATA__", js)
            .replace("__OHT3D__", o3d).replace("__THREE__", three))


V3D_DIRS = [HERE / "oht3d", HERE / "static" / "js" / "oht3d"]   # 월드모델파생 static/js/oht3d 폴더 그대로
_v3d_cache = None


def v3d_sources():
    """월드모델파생의 3D 뷰어(oht3d.js + three.module.min.js) — HTML 안에 넣어 인터넷 · 서버 없이 아이소메트리를 연다."""
    global _v3d_cache
    if _v3d_cache is None:
        _v3d_cache = ("", "")
        for d in V3D_DIRS:
            a, b = d / "oht3d.js", d / "three.module.min.js"
            if a.exists() and b.exists():
                o3d, three = a.read_text(encoding="utf-8"), b.read_text(encoding="utf-8")
                _v3d_cache = (o3d.replace("</script", "<\\/script"), three.replace("</script", "<\\/script"))
                break
        else:
            say(f"  ★3D 뷰어 없음 — {V3D_DIRS[0]} 에 oht3d.js · three.module.min.js 를 두면 아이소메트리가 켜집니다 (2D · 유사 3D 는 됨)")
    return _v3d_cache


HTML = r"""<!doctype html>
<html lang="ko" data-theme="hmi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root,[data-theme="hmi"]{--bg:#eceef2;--panel:#fff;--fg:#111827;--fg2:#4b5563;--line:#d5dae2;--chip:#eef1f5;
--l0:#3f9b5f;--l1:#e0a12e;--l2:#e2533a;--l3:#8f1d4f;--sub:#2f6fb5}
[data-theme="dark"]{--bg:#0a0e17;--panel:#111827;--fg:#e5e7eb;--fg2:#9ca3af;--line:#273244;--chip:#1f2937;
--l0:#5cc283;--l1:#f0b545;--l2:#ff6b52;--l3:#e0508f;--sub:#5aa7ef}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{background:var(--bg);color:var(--fg);font:13px/1.5 "Malgun Gothic","Apple SD Gothic Neo",system-ui,sans-serif;display:flex;flex-direction:column}
header{padding:9px 16px;border-bottom:1px solid var(--line);background:var(--panel);display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center}
header h1{font-size:17px;margin:0}header .m{color:var(--fg2);font-size:12px}
.b{display:inline-block;border-radius:5px;padding:1px 10px;color:#fff;font-weight:700;font-size:14px}
.b0{background:var(--l0)}.b1{background:var(--l1);color:#222}.b2{background:var(--l2)}.b3{background:var(--l3)}
main{flex:1;display:flex;min-height:0}
#mapbox{flex:1;position:relative;min-width:0;min-height:320px}
canvas{display:block;width:100%;height:100%;cursor:grab}canvas.drag{cursor:grabbing}
#side{width:360px;max-width:100%;border-left:1px solid var(--line);background:var(--panel);overflow:auto;padding:12px 14px}
h2{font-size:13px;margin:14px 0 6px;color:var(--fg2);font-weight:600}h2:first-child{margin-top:0}
.zone{border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin-bottom:8px;cursor:pointer}
.zone .t{font-weight:700;font-size:15px}.zone .s{color:var(--fg2);font-size:12px}
.zone.r1{border-left:6px solid var(--lv)}.zone.r2,.zone.r3{border-left:6px solid var(--sub)}
table{border-collapse:collapse;width:100%;font-size:12.5px}td{padding:4px 6px;border-bottom:1px solid var(--line)}td:first-child{color:var(--fg2)}td:last-child{text-align:right;font-weight:600}
ul{margin:4px 0;padding-left:18px}li{margin:2px 0}
.ov{position:absolute;background:var(--panel);border:1px solid var(--line);border-radius:10px;box-shadow:0 2px 10px #0002}
#abox{left:10px;top:10px;padding:8px 12px}
#abox .lv{display:inline-block;font-size:22px;font-weight:800;border-radius:8px;padding:2px 14px;color:#fff}
#abox .lv.l0{background:var(--l0)}#abox .lv.l1{background:var(--l1);color:#222}#abox .lv.l2{background:var(--l2)}#abox .lv.l3{background:var(--l3)}
#abox .z{font-size:13px;font-weight:700;margin-top:4px}#abox .s{font-size:11.5px;color:var(--fg2)}
#abox .steps{display:flex;gap:3px;margin-top:6px}#abox .steps span{flex:1;font-size:10.5px;text-align:center;border-radius:4px;padding:1px 4px;color:#fff;opacity:.3}
#abox .steps span.on{opacity:1;outline:2px solid var(--fg);outline-offset:1px}
#lg{left:10px;bottom:10px;padding:6px 9px;font-size:11.5px;color:var(--fg2);border-radius:6px;max-width:calc(100% - 20px)}
#lg i{display:inline-block;width:18px;height:5px;border-radius:2px;margin:0 4px 2px 8px;vertical-align:middle}
#lg svg{vertical-align:-2px;margin:0 3px 0 8px}
.tools{position:absolute;right:10px;top:10px;display:flex;flex-wrap:wrap;justify-content:flex-end;gap:6px;z-index:5;max-width:calc(100% - 300px)}
.tools .seg{display:inline-flex}.tools .seg button{border-radius:0;margin-left:-1px}.tools .seg button:first-child{border-radius:6px 0 0 6px}.tools .seg button:last-child{border-radius:0 6px 6px 0}
.tools button.on{background:var(--fg);color:var(--panel);border-color:var(--fg)}
#map-3d{position:absolute;inset:0;display:none;z-index:1}#map-3d .err{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);max-width:520px;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 14px}
body.m3d #abox,body.m3d #lg{z-index:4}body.m3d #abox{top:auto;bottom:64px}body.m3d .tools{top:auto;bottom:10px;max-width:calc(100% - 20px)}body.m3d #lg{bottom:auto;top:auto;display:none}
body.m3d #set{top:auto;bottom:50px}.tools button{border:1px solid var(--line);background:var(--panel);color:var(--fg);border-radius:6px;padding:4px 9px;font:inherit;font-size:12px;cursor:pointer}
#set{right:10px;top:46px;z-index:6;width:290px;padding:10px 12px;display:none;font-size:12px;max-height:calc(100% - 60px);overflow:auto}#set.on{display:block}
#set label{display:grid;grid-template-columns:96px 1fr 38px;gap:6px;align-items:center;margin:5px 0}#set b{font-size:12.5px}
#set input[type=range]{width:100%}#set .c{display:grid;grid-template-columns:1fr 1fr;gap:4px 10px;margin-top:6px}
#set .c label{grid-template-columns:1fr 34px;margin:2px 0}#set input[type=color]{width:34px;height:22px;padding:0;border:1px solid var(--line);background:none}
#set select{font:inherit;background:var(--chip);color:var(--fg);border:1px solid var(--line);border-radius:4px}
#set .btns{display:flex;gap:6px;margin-top:8px}#set .btns button{flex:1;border:1px solid var(--line);background:var(--chip);color:var(--fg);border-radius:6px;padding:4px;font:inherit;cursor:pointer}
#tip{position:absolute;pointer-events:none;background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:5px 7px;font-size:12px;display:none;box-shadow:0 2px 8px #0003}
.warn{color:var(--l2);font-size:12px}.note{color:var(--fg2);font-size:11.5px}
@media (max-width:820px){main{flex-direction:column}#side{width:100%;border-left:0;border-top:1px solid var(--line);flex:none}#mapbox{height:62vh;flex:none}}
</style></head><body>
<header><h1 id="h1"></h1><span id="hb"></span><span class="m" id="hm"></span></header>
<main>
 <div id="mapbox"><canvas id="cv"></canvas>
  <div class="tools"><span class="seg"><button data-m="2d" class="on">▭ 2D</button><button data-m="iso">◈ 유사 3D</button><button data-m="3d">⬢ 아이소메트리</button></span>
   <button id="bt-heat">🔥 히트맵</button><button id="bt-z">◎ 문제 구역</button><button id="bt-all">⤢ 전체</button><button id="bt-set">⚙ 설정</button></div>
  <div id="map-3d"></div>
  <div class="ov" id="abox"></div><div class="ov" id="lg"></div><div class="ov" id="set"></div><div id="tip"></div></div>
 <aside id="side"></aside>
</main>
<script>
const D=__DATA__, R=D.r, G=D.geo, Z=G.zones, ZI={}; Z.forEach((z,i)=>ZI[z.id]=i);
const LV=['정상','경계','위험','초위험'];
const $=id=>document.getElementById(id);
const css=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const TOP=[[R.z1,1],[R.z2,2],[R.z3,3]].filter(([z])=>z&&z!=='0');
const ZOF={};for(let i=0;i<G.e.length;i+=3){if(G.e[i+2]>=0){ZOF[G.e[i]]=G.e[i+2];ZOF[G.e[i+1]]=G.e[i+2];}}   // 노드 → HID 구역
// ---------- 설정 (월드모델파생 ⚙ 설정과 같은 이름) — 파일 기본값 + 이 브라우저에서 바꾼 값 ----------
const SKEY='hid_problem_map_settings_v1';
let S={...D.set};try{const raw=localStorage.getItem(SKEY);if(raw)S={...D.set,...JSON.parse(raw)};}catch(e){}
S.heat=D.set.heat;                                   // 히트맵은 열 때마다 기본값(꺼짐)으로 — 켜 둔 채 저장돼 있어도
const save=()=>{try{localStorage.setItem(SKEY,JSON.stringify(S));}catch(e){}};
// 월드모델파생 MAP_THEMES 그대로 (hmi = 현장 HMI 처럼 밝은 바탕 · 검은 레일 · 초록 HID)
const THEMES={hmi:{bg:'#eceef2',rail:'#23272e',railW:1.15,textBg:'rgba(236,238,242,0.88)',hid:'#3ddc5a',hidText:'#062b10',zone:'#059669',vehicleStroke:'#0b0f14',text2:'#374151'},
 dark:{bg:'#0a0e17',rail:'rgba(255,255,255,0.75)',railW:1.0,textBg:'rgba(10,14,23,0.82)',hid:'#16a34a',hidText:'#ecfdf5',zone:'#00ff88',vehicleStroke:'#0a0e17',text2:'#cbd5e1'}};
const P=()=>THEMES[S.mapTheme]||THEMES.hmi;
const LVC=l=>css('--l'+(l||0));
$('h1').textContent=`HID 문제맵 · ${D.fab} · ${R.t}`;
$('hb').innerHTML=`<span class="b b${R.lv}">${R.alarm}</span>`;
$('hm').textContent=`맵 ${D.info.layout} · ${D.info.src}`;
// ---------- 좌표 — 월드모델파생 mapProjPoint 그대로: 유사 3D(등각) u=(x−y)·cos30°, v=(x+y)·sin30° ----------
const ISO_C=Math.cos(Math.PI/6),ISO_S=Math.sin(Math.PI/6);let mode='2d';   // '2d' | 'iso'(유사 3D) | '3d'(아이소메트리)
const proj=(x,y)=>mode==='iso'?[(x-y)*ISO_C,(x+y)*ISO_S]:[x,y];
let U=[],V=[],minx=0,miny=0,maxx=1,maxy=1;
function setProj(){U=new Array(G.x.length);V=new Array(G.x.length);minx=miny=Infinity;maxx=maxy=-Infinity;
 for(let i=0;i<G.x.length;i++){const [u,v]=proj(G.x[i],G.y[i]);U[i]=u;V[i]=v;if(u<minx)minx=u;if(u>maxx)maxx=u;if(v<miny)miny=v;if(v>maxy)maxy=v;}}
const cv=$('cv'),ctx=cv.getContext('2d');let W=0,H=0,zoom=1,px=0,py=0,base=1;
function fit(){const r=cv.getBoundingClientRect(),d=devicePixelRatio||1;W=r.width;H=r.height;cv.width=W*d;cv.height=H*d;ctx.setTransform(d,0,0,d,0,0);
 base=Math.min((W-40)/Math.max(1,maxx-minx),(H-40)/Math.max(1,maxy-miny));}
const S2=(u,v)=>{const s=base*zoom;return[20+(u-minx)*s+px,20+(v-miny)*s+py];};     // 투영 좌표 → 화면
const I2=(sx,sy)=>{const s=base*zoom;return[(sx-20-px)/s+minx,(sy-20-py)/s+miny];};
const SN=i=>S2(U[i],V[i]);                                                          // 노드 → 화면
const SP=(x,y)=>{const q=proj(x,y);return S2(q[0],q[1]);};                           // 도면 좌표 → 화면
function view(x0,y0,x1,y1){const w=Math.max(1,x1-x0),h=Math.max(1,y1-y0);zoom=Math.max(.5,Math.min(80,Math.min((W-80)/w,(H-80)/h)/base));
 const s=base*zoom;px=W/2-20-((x0+x1)/2-minx)*s;py=H/2-20-((y0+y1)/2-miny)*s;draw();}
const home=()=>view(minx,miny,maxx,maxy);
function pbox(b){const cs=[[b[0],b[1]],[b[2],b[1]],[b[0],b[3]],[b[2],b[3]]].map(c=>proj(c[0],c[1]));
 return[Math.min(...cs.map(c=>c[0])),Math.min(...cs.map(c=>c[1])),Math.max(...cs.map(c=>c[0])),Math.max(...cs.map(c=>c[1]))];}
function focusTop(){if(mode==='3d')return v3dFocus();const bs=TOP.map(([z])=>Z[ZI[z]]).filter(z=>z&&z.box).map(z=>pbox(z.box));if(!bs.length)return home();
 const x0=Math.min(...bs.map(b=>b[0])),y0=Math.min(...bs.map(b=>b[1])),x1=Math.max(...bs.map(b=>b[2])),y1=Math.max(...bs.map(b=>b[3]));
 const pad=Math.max(x1-x0,y1-y0)*.35+50;view(x0-pad,y0-pad,x1+pad,y1+pad);}
function focusZone(id){if(mode==='3d')return v3dFocus(id);const z=Z[ZI[id]];if(!z||!z.box)return;const b=pbox(z.box),pad=Math.max(b[2]-b[0],b[3]-b[1])*.6+50;view(b[0]-pad,b[1]-pad,b[2]+pad,b[3]+pad);}
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
// ---------- 차량 (월드모델파생 drawVehicleShape · drawCarryDot 그대로) ----------
const vehR=()=>Math.max(2.5,Math.min(10,(+S.vehicleRadius||3)*(1.2+0.18*Math.max(0,zoom))));
function vcolor(o){ if(o[1]===3)return S.colorMiss;
 let st=o[4];if(st<0)st=o[1]===1?7:o[1]===2?8:1;
 if(st===6)return S.colorObs;if(st===7||o[1]===1)return S.colorJam;if(st===2||st===8||st===9||o[1]===2)return S.colorStop;return o[6]?S.colorLoaded:S.colorEmpty;}
function vkind(o){if(o[7]===4)return'loaded';if(o[7]===2)return'assign';if(o[6])return'loaded';if(o[8]>0)return'assign';return'';}
function tri(sx,sy,rr,ang,color,stroke){ctx.save();ctx.translate(sx,sy);ctx.rotate(ang);const tr=rr*1.56;ctx.beginPath();ctx.moveTo(tr,0);ctx.lineTo(-tr*.7,tr*.78);ctx.lineTo(-tr*.7,-tr*.78);ctx.closePath();
 ctx.fillStyle=color;ctx.fill();ctx.strokeStyle=stroke;ctx.lineWidth=Math.max(.6,Math.min(1.2,rr*.18));ctx.stroke();ctx.restore();}
function dot(sx,sy,rr,kind,ang){if(!kind||S.carryDot==='off')return;const c=kind==='loaded'?S.dotLoaded:S.dotAssign;const dr=Math.max(.9,rr*(+S.dotSize||.55));
 ctx.save();ctx.translate(sx,sy);ctx.rotate(ang||0);ctx.beginPath();ctx.arc(-.133*rr*1.56,0,dr,0,6.283);ctx.fillStyle=c;ctx.fill();ctx.restore();}
// ---------- 히트맵 — 월드모델파생 JAM_RAMP · jamClusters · drawJamBlobs 그대로 ----------
const JAM_R=1200,JAM_HOT_N=20;                       // 12 m 안을 한 무리로 · 20대 이상이 제일 짙다
const JAM_RAMP=[[0,250,204,21,.30],[.45,249,115,22,.46],[.75,239,68,68,.62],[1,153,27,27,.78]];
function jamHeat(cnt){const n=Math.max(1,+cnt||1),t=Math.min(1,Math.max(0,(n-1)/(JAM_HOT_N-1)));let i=1;while(i<JAM_RAMP.length-1&&JAM_RAMP[i][0]<t)i++;
 const p=JAM_RAMP[i-1],q=JAM_RAMP[i],f=(t-p[0])/((q[0]-p[0])||1e-9),v=j=>p[j]+(q[j]-p[j])*f;return{r:Math.round(v(1)),g:Math.round(v(2)),b:Math.round(v(3)),a:v(4),t};}
const JAM_KIND=[['jamMinJam','JAM'],['jamMinObs','OBS'],['jamMinStop','멈춘 차'],['jamMinMiss','미보고'],['jamMinHt','HT_STOP']];
const jamMins=()=>JAM_KIND.map(([k])=>{const n=parseInt(S[k],10);return(isNaN(n)||n<0)?0:n;});
function vstate(o){let st=o[4];if(st<0)st=o[1]===1?7:o[1]===2?8:1;return st;}
function jamKindOf(o,mins){const live=o[1]!==3,st=vstate(o);
 const has=[live&&(st===7||o[1]===1),live&&st===6,live&&(st===2||st===8||st===9||o[1]===2),o[1]===3,live&&(st===8||o[1]===2)];
 for(let i=0;i<5;i++)if(mins[i]>0&&has[i])return i;return-1;}
let _cl=null;
function jamClusters(){if(_cl)return _cl;const mins=jamMins();_cl=[];if(!D.oht||!mins.some(n=>n>0))return _cl;
 const js=[];for(const o of D.oht){const k=jamKindOf(o,mins);if(k>=0)js.push({x:G.x[o[2]],y:G.y[o[2]],k,z:ZOF[o[2]]});}
 const used=js.map(()=>false),counted=js.map(()=>false);
 for(let guard=0;guard<js.length;guard++){let bi=-1,bc=0,bx=0,by=0;
  for(let i=0;i<js.length;i++){if(used[i])continue;let c=0,sx=0,sy=0;for(let k=0;k<js.length;k++){if(used[k])continue;if(Math.hypot(js[i].x-js[k].x,js[i].y-js[k].y)<=JAM_R){c++;sx+=js[k].x;sy+=js[k].y;}}
   if(c>bc){bc=c;bi=i;bx=sx/c;by=sy/c;}}
  if(bi<0)break;for(let k=0;k<js.length;k++)if(!used[k]&&Math.hypot(js[bi].x-js[k].x,js[bi].y-js[k].y)<=JAM_R)used[k]=true;
  const cnt=[0,0,0,0,0],zc={};for(let k=0;k<js.length;k++)if(used[k]&&!counted[k]&&Math.hypot(js[bi].x-js[k].x,js[bi].y-js[k].y)<=JAM_R){cnt[js[k].k]++;counted[k]=true;if(js[k].z!=null)zc[js[k].z]=(zc[js[k].z]||0)+1;}
  if(!cnt.some((c,i)=>mins[i]>0&&c>=mins[i]))continue;
  let zb=null,zn=0;for(const z in zc)if(zc[z]>zn){zn=zc[z];zb=+z;}       // 무리에 제일 많이 든 HID 구역
  _cl.push({x:bx,y:by,n:cnt.reduce((a,b)=>a+b,0),kinds:cnt,zone:zb});}
 return _cl;}
function drawJamBlobs(){const cl=jamClusters();if(!cl.length)return;const base=JAM_R*base_sc();ctx.save();
 for(const c of cl){const [sx,sy]=SP(c.x,c.y),R0=Math.max(18,base*(.9+.22*Math.log2(1+c.n)));if(sx<-R0||sy<-R0||sx>W+R0||sy>H+R0)continue;
  const hc=jamHeat(c.n),rgb=`${hc.r},${hc.g},${hc.b}`,g=ctx.createRadialGradient(sx,sy,0,sx,sy,R0);
  g.addColorStop(0,`rgba(${rgb},${hc.a.toFixed(3)})`);g.addColorStop(.35,`rgba(${rgb},${(hc.a*.52).toFixed(3)})`);g.addColorStop(.7,`rgba(${rgb},${(hc.a*.18).toFixed(3)})`);g.addColorStop(1,`rgba(${rgb},0)`);
  ctx.fillStyle=g;ctx.beginPath();ctx.arc(sx,sy,R0,0,6.283);ctx.fill();}
 ctx.restore();}
function drawJamText(){const cl=jamClusters();if(!cl.length)return;const base=JAM_R*base_sc();ctx.save();ctx.textAlign='center';ctx.textBaseline='middle';
 for(const c of cl){const [sx,sy]=SP(c.x,c.y),R0=Math.max(18,base*(.9+.22*Math.log2(1+c.n)));if(R0<26||sx<-R0||sy<-R0||sx>W+R0||sy>H+R0)continue;
  const fs=Math.round(Math.min(18,Math.max(11,R0*.22))*(+S.labelScale||1));ctx.lineWidth=3;ctx.strokeStyle='rgba(255,255,255,0.9)';ctx.font=`700 ${fs}px sans-serif`;
  const kk=c.kinds.map((n,i)=>n?`${JAM_KIND[i][1]} ${n}`:'').filter(Boolean),num=kk.length>1?kk.join(' · '):`${c.n}대`;
  ctx.strokeText(num,sx,sy);ctx.fillStyle='#b91c1c';ctx.fillText(num,sx,sy);
  const z=c.zone!=null?Z[c.zone]:null,nm=z?(z.name||'HID '+z.id):'구역 밖';ctx.font=`700 ${Math.round(fs*.92)}px sans-serif`;
  ctx.strokeText(nm,sx,sy-fs-3);ctx.fillStyle=z?'#7f1d1d':'#6b7280';ctx.fillText(nm,sx,sy-fs-3);}
 ctx.restore();}
const base_sc=()=>base*zoom;
// ---------- 그리기 ----------
function lines(test,col,w,dash){ctx.strokeStyle=col;ctx.lineWidth=w;ctx.setLineDash(dash||[]);ctx.beginPath();
 for(let i=0;i<G.e.length;i+=3){if(!test(G.e[i+2]))continue;const a=SN(G.e[i]),b=SN(G.e[i+1]);ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);}ctx.stroke();ctx.setLineDash([]);}
function draw(){const p=P(),sc=base*zoom;ctx.setTransform(devicePixelRatio||1,0,0,devicePixelRatio||1,0,0);
 ctx.fillStyle=p.bg;ctx.fillRect(0,0,W,H);ctx.lineCap='round';ctx.lineJoin='round';
 if(mode==='iso'){const g=[[GX0,GY0],[GX1,GY0],[GX1,GY1],[GX0,GY1]].map(c=>SP(c[0],c[1]));ctx.fillStyle=S.mapTheme==='dark'?'rgba(255,255,255,0.05)':'#dfe3ea';
  ctx.strokeStyle='#b8c0cc';ctx.lineWidth=1;ctx.beginPath();g.forEach((q,i)=>i?ctx.lineTo(q[0],q[1]):ctx.moveTo(q[0],q[1]));ctx.closePath();ctx.fill();ctx.stroke();}
 const hot={};TOP.forEach(([z,r])=>{if(ZI[z]!=null&&!(ZI[z] in hot))hot[ZI[z]]=r;});
 // ① HID 존 진입(실선)·진출(점선) — 레일보다 먼저, 초록 형광펜 (월드모델파생 2D 그대로)
 if(sc>=0.28&&G.lanes){const zw=clamp(2+sc*2.2,2,9),dash=clamp(2+sc*2.5,3,10);ctx.strokeStyle=p.zone;ctx.lineWidth=zw;ctx.globalAlpha=.30;
  for(const out of [0,1]){ctx.setLineDash(out?[dash,dash*.7]:[]);ctx.beginPath();for(const [a,b,,o] of G.lanes){if(o!==out)continue;const A=SN(a),B=SN(b);ctx.moveTo(A[0],A[1]);ctx.lineTo(B[0],B[1]);}ctx.stroke();}
  ctx.setLineDash([]);ctx.globalAlpha=1;}
 // ② 문제 구역 — 레일 밑에 굵은 형광펜 (2·3위 파랑, 1위 ALARM 색)
 const zs=+S.zoneScale||1,rw=clamp(.9+sc*.8,.8,2.4)*(p.railW||1)*(+S.railScale||1);
 ctx.globalAlpha=.7;[3,2].forEach(r=>lines(z=>hot[z]===r,css('--sub'),Math.max(6,rw*5)*zs));
 ctx.globalAlpha=.88;lines(z=>hot[z]===1,LVC(R.lv),Math.max(9,rw*7)*zs);ctx.globalAlpha=1;
 // ③ 레일 (검은 선, 월드모델파생 굵기 규칙)
 lines(()=>true,p.rail,rw);
 // ③' 히트맵 — 차량 **밑에** (위에 덮으면 삼각형이 묻힌다, 월드모델파생과 같음)
 if(S.heat!=='off')drawJamBlobs();
 // ④ OHT — 미보고 ✕ 먼저, 운행 · 멈춘 차는 위에
 if(D.oht){const rr=vehR();
  for(const o of D.oht){if(o[1]!==3)continue;const [x,y]=SN(o[2]);if(x<-9||y<-9||x>W+9||y>H+9)continue;const q=rr*1.05;
   ctx.strokeStyle=p.bg;ctx.lineWidth=Math.max(2.5,rr*.75);ctx.beginPath();ctx.moveTo(x-q,y-q);ctx.lineTo(x+q,y+q);ctx.moveTo(x+q,y-q);ctx.lineTo(x-q,y+q);ctx.stroke();
   ctx.strokeStyle=S.mapTheme==='dark'&&S.colorMiss==='#111827'?'#f3f4f6':S.colorMiss;ctx.lineWidth=Math.max(1.4,rr*.42);ctx.stroke();}
  for(const pass of [0,1])for(const o of D.oht){if(o[1]===3)continue;const stop=o[1]>0||[6,7,2,8,9].includes(o[4]);if(stop!==!!pass)continue;
   const [x,y]=SN(o[2]);if(x<-9||y<-9||x>W+9||y>H+9)continue;
   let ang=-Math.PI/2;if(o[5]>=0&&o[5]!==o[2]){const B=SN(o[5]);if(B[0]!==x||B[1]!==y)ang=Math.atan2(B[1]-y,B[0]-x);}
   tri(x,y,rr,ang,vcolor(o),p.vehicleStroke);dot(x,y,rr,vkind(o),ang);}}
 if(S.heat!=='off')drawJamText();
 // ⑤ 라벨 — 1·2·3위 먼저 (비켜서라도), 나머지 HID 는 확대하면 초록 상자
 const ls=+S.labelScale||1;ctx.textAlign='center';ctx.textBaseline='middle';const placed=[];
 const L=[...TOP,...(zoom>=2.5?Z.map(z=>[z.id,9]):[])];const done={};
 for(const [id,r] of L){if(done[id])continue;done[id]=1;const z=Z[ZI[id]];if(!z||z.cx==null)continue;let [x,y]=SP(z.cx,z.cy);if(x<-30||y<-30||x>W+30||y>H+30)continue;
  const big=r<=3,t=big?`${r}위 HID ${id}${z.bay?' · '+z.bay:''}${r===1&&R.lv?' · '+R.alarm:''}`:`HID ${id}`;
  ctx.font=big?`700 ${12.5*ls}px system-ui,sans-serif`:`700 ${10*ls}px system-ui,sans-serif`;
  const w=ctx.measureText(t).width+10,h=(big?20:15)*ls;x=Math.max(w/2+2,Math.min(W-w/2-2,x));if(big)y-=16*ls;
  const hit=yy=>placed.some(q=>Math.abs(q[0]-x)<(q[2]+w)/2&&Math.abs(q[1]-yy)<(q[3]+h)/2+1);
  if(hit(y)){if(!big)continue;const alt=[y+h+4,y-h-4,y+2*h+8,y-2*h-8].find(yy=>!hit(yy));if(alt==null)continue;y=alt;}
  placed.push([x,y,w,h]);
  ctx.fillStyle=big?(r===1?LVC(R.lv):css('--sub')):p.hid;ctx.fillRect(x-w/2,y-h/2,w,h);
  ctx.fillStyle=big?((r===1&&R.lv===1)?'#222':'#fff'):p.hidText;ctx.fillText(t,x,y+.5);}
 legend();}
const triSvg=c=>`<svg width="12" height="12" viewBox="-6 -6 12 12"><path d="M0,-5.5 L4.7,4 L-4.7,4 Z" fill="${c}" stroke="#0b0f14" stroke-width=".8"/></svg>`;
function legend(){const oc=D.oht?[0,1,2,3].map(c=>D.oht.filter(x=>x[1]===c).length):null;
 $('lg').innerHTML=`<b>${R.t}</b> 1위 구역:<i style="background:${LVC(1)}"></i>경계<i style="background:${LVC(2)}"></i>위험<i style="background:${LVC(3)}"></i>초위험<i style="background:${css('--sub')}"></i>2·3위<i style="background:${P().zone};opacity:.5"></i>HID 존`+
 (oc?`<br>OHT:${triSvg(S.colorEmpty)}공차${triSvg(S.colorLoaded)}적재${triSvg(S.colorObs)}OBS${triSvg(S.colorStop)}정지·HT${triSvg(S.colorJam)}JAM<b style="margin:0 3px 0 8px">✕</b>미보고`+
  ` — 보고 ${oc[0]+oc[1]+oc[2]} (JAM ${oc[1]} · HT_STOP ${oc[2]}) · 미보고 ${oc[3]}`:`<br>OHT 차량 없음 — ${D.ohtd}`)+
 (S.heat!=='off'?`<br>히트맵 (정체 무리 대수):<i style="width:90px;height:8px;background:linear-gradient(90deg,rgb(250,204,21),rgb(249,115,22),rgb(239,68,68),rgb(153,27,27))"></i>1대 → 20대 이상 · 정체 ${jamClusters().length}곳`:'');}
// ---------- ⚙ 설정 ----------
const RANGES=[['vehicleRadius','OHT 크기',1,8,.5],['railScale','레일 굵기',.4,3,.1],['zoneScale','문제 구역 굵기',.4,3,.1],['labelScale','글자 크기',.6,1.8,.1],['dotSize','점 크기',.2,1,.05]];
const COLORS=[['colorEmpty','공차'],['colorLoaded','적재'],['colorObs','OBS'],['colorStop','정지·HT'],['colorJam','JAM'],['colorMiss','미보고 ✕']];
function setPanel(){let h=`<b>⚙ 지도 설정</b> <span class="note">(월드모델파생 ⚙ 설정과 같은 값)</span>`;
 h+=`<label>테마<select id="s-mapTheme"><option value="hmi">HMI (밝게)</option><option value="dark">다크</option></select><span></span></label>`;
 for(const [k,n,a,b,st] of RANGES)h+=`<label>${n}<input type="range" id="s-${k}" min="${a}" max="${b}" step="${st}" value="${S[k]}"><span id="v-${k}">${S[k]}</span></label>`;
 h+=`<label>삼각형 안 점<select id="s-carryDot"><option value="on">켜기</option><option value="off">끄기</option></select><span></span></label>`;
 h+=`<label>히트맵<select id="s-heat"><option value="on">켜기</option><option value="off">끄기</option></select><span></span></label>`;
 h+=`<div class="note" style="margin-top:4px">정체 판정 — 12 m 안 한 무리에서 몇 대 이상이면 (0 = 안 봄, 월드모델파생 ⚙ 와 같음)</div><div class="c">`;
 for(const [k,n] of JAM_KIND)h+=`<label>${n}<input type="number" id="s-${k}" min="0" max="99" value="${S[k]}" style="width:44px"></label>`;
 h+=`</div><div class="c">`;
 for(const [k,n] of COLORS)h+=`<label>${n}<input type="color" id="s-${k}" value="${S[k]}"></label>`;
 h+=`</div><div class="btns"><button id="s-def">기본값</button><button id="s-close">닫기</button></div><div class="note" style="margin-top:6px">여기서 바꾼 값은 이 브라우저에 저장됩니다. 모든 지도의 기본값은 HID_MAP_SETTINGS.json 에서.</div>`;
 $('set').innerHTML=h;$('s-mapTheme').value=S.mapTheme;$('s-carryDot').value=S.carryDot;$('s-heat').value=S.heat;
 $('set').querySelectorAll('input,select').forEach(el=>el.oninput=el.onchange=()=>{const k=el.id.slice(2);S[k]=el.type==='range'?+el.value:el.value;
  const v=$('v-'+k);if(v)v.textContent=el.value;if(el.type==='number')S[k]=+el.value||0;_cl=null;save();applyTheme();syncHeat();draw();});
 $('s-def').onclick=()=>{S={...D.set};_cl=null;try{localStorage.removeItem(SKEY);}catch(e){}setPanel();applyTheme();syncHeat();draw();};
 $('s-close').onclick=()=>$('set').classList.remove('on');}
let applyTheme=function(){document.documentElement.dataset.theme=S.mapTheme==='dark'?'dark':'hmi';document.documentElement.style.setProperty('--lv',LVC(R.lv));
 const z1=Z[ZI[R.z1]];$('abox').innerHTML=`<span class="lv l${R.lv}">${R.alarm}</span>`+
 (R.z1&&R.z1!=='0'?`<div class="z">1위 HID ${R.z1}${z1&&z1.bay?' · '+z1.bay:''}</div><div class="s">구역 멈춘 차 ${R.zstop} · missing ${R.miss} · JAM ${R.jam} · HT ${R.ht}</div>`:'')+
 `<div class="steps">${[1,2,3].map(l=>`<span class="${l===R.lv?'on':''}" style="background:${LVC(l)};${l===1?'color:#222':''}">${LV[l]}</span>`).join('')}</div>`;};
$('bt-set').onclick=()=>$('set').classList.toggle('on');
function syncHeat(){$('bt-heat').classList.toggle('on',S.heat!=='off');if(v3d){v3d.setOptions({heat:S.heat!=='off',jamMin:jamMins()});
  const bt=$('map-3d').querySelector(S.heat!=='off'?'.o3d-btn[data-a=hot]':'.o3d-btn[data-a=all]');if(mode==='3d'&&bt)bt.click();}}
$('bt-heat').onclick=()=>{S.heat=S.heat==='off'?'on':'off';save();const el=$('s-heat');if(el)el.value=S.heat;syncHeat();if(mode!=='3d')draw();};
// ---------- 조작 ----------
let drag=null;
cv.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,px,py};cv.setPointerCapture(e.pointerId);cv.classList.add('drag');});
cv.addEventListener('pointermove',e=>{if(drag){px=drag.px+e.clientX-drag.x;py=drag.py+e.clientY-drag.y;draw();}else hover(e);});
cv.addEventListener('pointerup',()=>{drag=null;cv.classList.remove('drag');});
cv.addEventListener('wheel',e=>{e.preventDefault();const r=cv.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top,[wx,wy]=I2(mx,my);
 zoom=Math.max(.5,Math.min(80,zoom*(e.deltaY<0?1.2:1/1.2)));const [sx,sy]=S2(wx,wy);px+=mx-sx;py+=my-sy;draw();},{passive:false});
cv.addEventListener('dblclick',home);
function seg(x,y,a,b){const dx=b[0]-a[0],dy=b[1]-a[1],l=dx*dx+dy*dy;let t=l?((x-a[0])*dx+(y-a[1])*dy)/l:0;t=Math.max(0,Math.min(1,t));const qx=a[0]+t*dx-x,qy=a[1]+t*dy-y;return qx*qx+qy*qy;}
const SNAME={1:'운행',2:'정지',6:'OBS',7:'JAM',8:'HT_STOP',9:'정지'};
function hover(e){const r=cv.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top,tp=$('tip');
 const show=h=>{tp.innerHTML=h;tp.style.display='block';tp.style.left=Math.min(mx+12,W-250)+'px';tp.style.top=(my+12)+'px';};
 if(D.oht){let vb=null,vd=Math.max(8,vehR()*1.6)**2;for(const o of D.oht){const [x,y]=SN(o[2]);const d=(x-mx)**2+(y-my)**2;if(d<vd){vd=d;vb=o;}}
  if(vb){const z=ZOF[vb[2]];const st=vb[1]===3?'미보고 (끊기기 직전 위치)':vb[1]===1?'JAM':vb[1]===2?'HT_STOP':(SNAME[vb[4]]||'운행')+(vb[6]?' · 적재':' · 공차');
   return show(`<b>OHT ${vb[0]}</b> · ${st}<br>주소 ${vb[3]}${z!=null?` · HID ${Z[z].id}${Z[z].bay?' · '+Z[z].bay:''}`:''}${vb[8]>0?`<br>목적지 ${vb[8]}`:''}${vb[9]!=null&&vb[1]!==3?`<br>속도 ${vb[9]} m/min (50초 평균)`:''}`);}}
 let best=-1,bd=12*12;
 for(let i=0;i<G.e.length;i+=3){const z=G.e[i+2];if(z<0)continue;const d=seg(mx,my,SN(G.e[i]),SN(G.e[i+1]));if(d<bd){bd=d;best=z;}}
 if(best<0){tp.style.display='none';return;}const z=Z[best],rk=TOP.find(([id])=>id===z.id);
 show(`<b>HID ${z.id}</b> ${z.name||''}${z.bay?' · '+z.bay:''}${rk?` — <b>${rk[1]}위</b>`:''}${z.vmax?`<br>정원(Vehicle_Max) ${z.vmax}`:''}`);}
$('bt-all').onclick=()=>{if(mode==='3d'){if(v3d)v3d.viewAll();}else home();};$('bt-z').onclick=focusTop;
// ---------- 오른쪽 ----------
const zname=id=>{const z=Z[ZI[id]];return z?`${z.name||''}${z.bay?' · '+z.bay:''}`:'⚠ 지도에 없는 구역';};
let h=`<h2>문제 구역 (그 1분)</h2>`;
if(!TOP.length)h+=`<div class="note">${R.lv?'구역 정보 없음':'정상 — 문제 구역 없음'}</div>`;
TOP.forEach(([id,r])=>{h+=`<div class="zone r${r}" data-z="${id}"><div class="t">${r}위 · HID ${id}</div><div class="s">${zname(id)}</div>`+
 (r===1?`<div class="s">구역 안 멈춘 차 <b>${R.zstop}</b> · 구역 안 차량 <b>${R.zvhl}</b> / 정원 ${R.vmax} · 점유율 <b>${R.occ}%</b></div>`:'')+`</div>`;});
h+=`<h2>그 1분 숫자</h2><table>
<tr><td>날짜 · 시간</td><td>${R.t}</td></tr><tr><td>ALARM</td><td>${R.alarm}</td></tr>
<tr><td>HID_ZONE · section</td><td>${R.z1} · ${R.sect}</td></tr>
<tr><td>OHT_report (보고 차량)</td><td>${R.n}</td></tr><tr><td>OHT_missing (미보고)</td><td>${R.miss}</td></tr>
<tr><td>OHT_JAM</td><td>${R.jam}</td></tr><tr><td>OHT_HT_STOP</td><td>${R.ht}</td></tr>
<tr><td>ZONE_STOP (구역 멈춘 차)</td><td>${R.zstop}</td></tr><tr><td>ZONE_VHL / VHL_MAX</td><td>${R.zvhl} / ${R.vmax}</td></tr>
<tr><td>ZONE_OCC (점유율)</td><td>${R.occ}%</td></tr><tr><td>HID_ZONE_2 · 3</td><td>${R.z2} · ${R.z3}</td></tr></table>`;
h+=`<h2>판정 근거 (HID_CONFIG.json 기준)</h2>`+(D.why.length?`<ul>${D.why.map(w=>`<li>${w}</li>`).join('')}</ul>`:`<div class="note">걸린 조건 없음 — 정상</div>`);
if(D.info.diff)h+=`<div class="warn">⚠ ${D.info.diff} — HID_Zone_Master 를 확인하세요.</div>`;
if(D.info.miss.length)h+=`<div class="warn">⚠ 지도에 없는 구역: ${D.info.miss.join(', ')} — HID_Zone_Master 를 확인하세요.</div>`;
h+=`<h2>OHT 차량</h2><div class="note">${D.ohtd}<br>모양 · 색은 월드모델파생 맵과 같습니다 — 삼각형 꼭짓점 = 진행 방향, 안의 검은 점 = 들고 감 · 흰 점 = 가지러 감.</div>`;
h+=`<h2>맵</h2><div class="note">${D.info.layout} · 구역 번호 ${D.info.use}<br>${D.info.msg}<br>휠 확대 · 드래그 이동 · 더블클릭 전체 · 차량 · 구역에 마우스를 올리면 정보 · ⚙ 설정에서 OHT 크기 등</div>`;
$('side').innerHTML=h;
document.querySelectorAll('.zone[data-z]').forEach(el=>el.onclick=()=>focusZone(el.dataset.z));
setPanel();applyTheme();
// 도면 범위 (유사 3D 바닥판)
let GX0=Infinity,GY0=Infinity,GX1=-Infinity,GY1=-Infinity;for(let i=0;i<G.x.length;i++){GX0=Math.min(GX0,G.x[i]);GX1=Math.max(GX1,G.x[i]);GY0=Math.min(GY0,G.y[i]);GY1=Math.max(GY1,G.y[i]);}
// ---------- ⬢ 아이소메트리 — 월드모델파생 oht3d.js (three.js r169) 그대로, 이 파일 안에 들어 있다 ----------
let v3d=null,v3dLoading=null;
const V3D_SCALE=0.01;                                          // 도면 1 단위 = 10 mm (월드모델파생과 같음)
const zname3=z=>z.name||('HID '+z.id);
function layout3D(){const ids=G.ids,nodes=ids.map((id,i)=>({id,x:G.x[i],y:G.y[i]})),seen=new Set(),edges=[];
 for(let i=0;i<G.e.length;i+=3){const id=ids[G.e[i]]+'-'+ids[G.e[i+1]];if(seen.has(id)||G.e[i]===G.e[i+1])continue;seen.add(id);edges.push({id,from:ids[G.e[i]],to:ids[G.e[i+1]]});}
 const ze={};for(const [a,b,zi] of (G.lanes||[])){if(zi<0)continue;const id=ids[a]+'-'+ids[b];if(!seen.has(id)){seen.add(id);edges.push({id,from:ids[a],to:ids[b]});}(ze[zi]=ze[zi]||[]).push(id);}
 const zones=Object.entries(ze).map(([zi,es])=>({id:zname3(Z[zi]),edges:es}));return{nodes,edges,zones,ports:[]};}
function rows3D(){const ids=G.ids;return (D.oht||[]).map(o=>{let st=o[4];if(o[1]===3)st=2;else if(st<0)st=o[1]===1?7:o[1]===2?8:1;
 const s3=st===7||o[1]===1?3:st===6?4:(st===2||st===8||st===9||o[1]===2)?2:(o[6]?1:0);
 const stop=o[1]>0||[2,6,7,8,9].includes(st);
 /* 속도 = 앞 50초 구간 위치에서 지금 위치까지 레일을 따라 간 거리 ÷ 50초 (m/min). 멈춘 차 · 모르면 0.
    3D 히트맵(레일 원활 ↔ 정체)은 월드모델파생처럼 이 속도로 칠한다. */
 return{id:o[0],from:ids[o[2]],to:o[5]>=0?ids[o[5]]:null,ratio:0,x:G.x[o[2]],y:G.y[o[2]],speed_mpm:stop?0:(o[9]||0),state:s3,loaded:!!o[6],miss:o[1]===3,ht:o[1]===2||o[4]===8};});}
const v3dColors=()=>[S.colorEmpty,S.colorLoaded,S.colorStop,S.colorJam,S.colorObs];
function v3dFocus(id){if(!v3d)return;const zid=id||R.z1;const z=Z[ZI[zid]];if(z)try{v3d.focusZone(zname3(z));}catch(e){}}
async function open3D(){const box=$('map-3d');box.style.display='block';cv.style.display='none';
 if(!v3d){if(!v3dLoading)v3dLoading=(async()=>{
   const blob=(id)=>URL.createObjectURL(new Blob([document.getElementById(id).textContent],{type:'text/javascript'}));
   const threeUrl=blob('src-three'),mod=await import(blob('src-oht3d'));
   const inst=await mod.createOHT3D(box,{threeUrl,coordScale:V3D_SCALE,flipY:false,projection:'iso',walls:false,dark:S.mapTheme==='dark',
     colors:{state:v3dColors(),background:P().bg,accent:'#1f6feb'},sizeUI:true,panel:false,heat:S.heat!=='off',jamMin:jamMins()});
   inst.setLayout(layout3D());inst.setVehicles(rows3D(),{ts:R.t.replace(/[-: ]/g,'')+'00'});return inst;})();
  try{v3d=await v3dLoading;}catch(e){v3dLoading=null;box.innerHTML=`<div class="err"><b>아이소메트리를 못 불러왔습니다.</b><br>${String(e&&e.message||e).replace(/[<>&]/g,'')}</div>`;return;}}
 v3d.setActive(true);v3d.resize&&v3d.resize();v3d.setOptions({dark:S.mapTheme==='dark',background:P().bg,stateColors:v3dColors(),heat:S.heat!=='off',jamMin:jamMins()});
 setTimeout(()=>v3dFocus(),300);}                    // 정체 지점은 처음엔 꺼짐 — 🔥 히트맵 단추나 뷰어의 '정체 지점' 으로 켠다
function close3D(){$('map-3d').style.display='none';cv.style.display='';if(v3d)v3d.setActive(false);}
function setMode(m){if(m===mode)return;const was=mode;mode=m;document.querySelectorAll('.seg button').forEach(b=>b.classList.toggle('on',b.dataset.m===m));
 document.body.classList.toggle('m3d',m==='3d');
 if(m==='3d'){open3D();return;}if(was==='3d')close3D();setProj();fit();home();}
document.querySelectorAll('.seg button').forEach(b=>b.onclick=()=>setMode(b.dataset.m));
const _apply=applyTheme;applyTheme=function(){_apply();if(v3d)v3d.setOptions({dark:S.mapTheme==='dark',background:P().bg,stateColors:v3dColors()});};
setProj();syncHeat();
addEventListener('resize',()=>{if(mode==='3d')return;fit();home();});fit();home();
</script>
<script type="text/plain" id="src-oht3d">__OHT3D__</script>
<script type="text/plain" id="src-three">__THREE__</script>
</body></html>
"""


# ==========================================================
def main():
    ap = argparse.ArgumentParser(description="로그프레소에서 그 시각을 판정 → 문제맵(HTML)")
    ap.add_argument("fab", help=f"FAB ({' '.join(HB.FABS)})")
    ap.add_argument("when", nargs="*",
                    help="YYYYMMDDHHMM (그 1분, 여러 개 가능) 또는 YYYYMMDD (그 날 알람 난 분 전부). 없으면 지금")
    ap.add_argument("--out", help="저장할 폴더 (기본 HID_BOTTLENECK/PROBLEM_MAP)")
    a = ap.parse_args()

    fab = a.fab.upper()
    if fab not in HB.FABS:
        sys.exit(f"FAB 은 {' '.join(HB.FABS)} 중 하나")
    whens = [w.replace("-", "").replace(":", "").replace(" ", "") for w in a.when]
    if any(not re.fullmatch(r"\d{8}|\d{12}", w) for w in whens):
        sys.exit("시간은 YYYYMMDDHHMM (그 1분) 또는 YYYYMMDD (그 날 알람 난 분 전부)")

    say(f"■ {fab} 문제맵 — 로그프레소에서 판정")
    HB.load_config(first=True)
    m, err = load_map(fab)
    if not m:
        sys.exit(f"맵 없음 — {err}")
    use = HB.HID_ZONE_USE
    geo = geometry(m, use)
    have = {z["id"] for z in geo["zones"] if z["n"]}
    zbay = {z["id"]: z["bay"] for z in geo["zones"]}
    P = HB.policy(fab)
    SET = load_settings()

    jobs = []                                        # (frm, to, keep, 설명)
    if not whens:
        now = datetime.now() - timedelta(seconds=HB.LAG_SEC + 60)
        t = now.replace(second=0, microsecond=0)
        jobs.append((t, t + timedelta(minutes=1), lambda r: True, f"지금 {t:%H:%M}"))
    for w in whens:
        if len(w) == 12:
            t = datetime.strptime(w, "%Y%m%d%H%M")
            jobs.append((t, t + timedelta(minutes=1), lambda r: True, f"{t:%Y-%m-%d %H:%M}"))
        else:
            d = datetime.strptime(w, "%Y%m%d")
            jobs.append((d, d + timedelta(days=1), lambda r: r["alarm"] in LEVEL, f"{d:%Y-%m-%d} 하루 (알람 난 분만)"))

    out_base = Path(a.out) if a.out else MAP_OUT
    made = []
    for frm, to, keep, label in jobs:
        say(f"  {label} 판정 중 … (앞 {HB.FLEET_AUTO_MIN}분부터 받음)")
        try:
            res = judge(m, frm, to, keep)
        except Exception as ex:
            say(f"  ★{label} 로그프레소 조회 실패 — {str(ex)[:200]}")
            continue
        if not res:
            say(f"  {label}: 만들 분 없음")
        for r, vs, b in res:
            miss = [z for z in (r["z1"], r["z2"], r["z3"]) if z not in ("", "0") and z not in have]
            bay = zbay.get(r["z1"], "")
            diff = (f"판정 HID_section {r['sect']} ≠ 지도의 {bay} (HID {r['z1']})"
                    if r["z1"] in zbay and r["sect"] not in ("", "0") and bay and r["sect"] != bay else "")
            info = {"layout": m["layout_file"], "msg": m["msg"], "use": use, "miss": miss, "diff": diff,
                    "src": f"로그프레소 {HB.FABS[fab]['table']} ({HB.SERVERS[HB.FABS[fab]['server']]['host']})"}
            det = None
            if b is not None and vs:
                try:
                    det = fetch_detail(m["st"], b)
                except Exception as ex:
                    say(f"    (차량 방향 · 적재 못 받음 — 상태만 그림: {str(ex)[:120]})")
            oht, od = place(m, vs, r, b, det)
            day, hm = r["t"][:10].replace("-", ""), r["t"][11:].replace(":", "")
            d = out_base / f"{fab}_{day}"
            d.mkdir(parents=True, exist_ok=True)
            p = d / f"PROBLEM_MAP_{fab}_{day}_{hm}_{ALARM_EN.get(r['alarm'], 'NORMAL')}.html"
            p.write_text(build_html(fab, r, geo, info, reasons(r, P), oht, od, SET), encoding="utf-8")
            made.append(p)
            say(f"  {r['t']} {r['alarm']:3} 1위 HID {r['z1']} ({r['sect']}) · 2·3위 {r['z2']} · {r['z3']}"
                f" · missing {r['miss']} JAM {r['jam']} HT {r['ht']} · 구역 멈춘 차 {r['zstop']}"
                f"{'  ⚠지도에 없음 ' + ','.join(miss) if miss else ''}{'  ⚠' + diff if diff else ''}")
            say(f"    OHT {od}")
    say(f"  맵 {m['layout_file']} · 구역 번호 {use}")
    for d in sorted({x.parent for x in made}):
        say(f"  → {d}  ({sum(1 for x in made if x.parent == d)}개)")


if __name__ == "__main__":
    main()
