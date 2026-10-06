#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gwanje_score.py — 실시간 모드 오른쪽 '스코어' 탭: 관제(real_time_amhs)가 매긴 그 FAB 의 스코어를 받아 온다.

고객 2026-10-06: "실시간에 이제 기존 스코어 점수랑 그런 데이터들이 들어가야 돼. 스코어 표랑 그런 거
볼 수 있게" · "HID_JAM, RET(레포트) 더블클릭하면 그래프 정보도 실시간에 전부 다 표시돼야 돼".

★점수를 여기서 다시 계산하지 않는다 — 다시 계산하면 관제 표와 숫자가 어긋난다. 관제가 매긴 점수 ·
  등급(정책 컷) · 알람 카운터 · 발동 룰 · 실제지표 · HID_JAM · RET 를 그대로 넘긴다.
★지도 → 관제 시스템 (관제 world_link.MAP 의 반대 방향). FAB 화면이라 그 FAB 것만 묻는다.
★관제 주소 — 환경변수 GWANJE_URL, 없으면 이 PC 의 관제 (real_time_amhs/config.json 의 server.port,
  기본 8989). 관제가 꺼져 있어도 OHT 실시간은 그대로 돈다 — 탭에 "관제에 닿지 않습니다" 만 뜬다.
★관제가 그 FAB 을 '보는 중' 으로 세는 것은 관제 화면을 연 것과 같다 (관제 rctx).
"""

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    from app_paths import runtime_dir
    _ROOT = str(runtime_dir())
except ImportError:                                   # 이 파일만 따로 쓸 때
    _ROOT = os.path.dirname(os.path.abspath(__file__))

GW_SYS = {("M14A", "A"): "M14", ("M14B", "A"): "M14B", ("M16A", "A"): "M16A",
          ("M16B", "B"): "M16B", ("M16A", "BR"): "M16HUB"}
# 화면에 필요한 칸만 넘긴다 (관제 행에는 AMOS 원본 지표 값까지 실려 무겁다)
_ROW_KEYS = ("at", "datetime", "time", "score", "level", "emoji", "area", "reason", "metrics",
             "alm", "hi_fab", "fab", "fab_lv", "hid", "case_id")
_CACHE: dict = {}
_CL = threading.Lock()


def sys_for(fab: str, prefix: str) -> str:
    """지도 → 관제 시스템 이름 (짝이 없으면 '')."""
    return GW_SYS.get((fab, prefix), "")


def base() -> str:
    """관제 주소 — 환경변수 GWANJE_URL, 없으면 이 PC 의 관제(real_time_amhs/config.json 의 포트)."""
    env = os.environ.get("GWANJE_URL", "").strip()
    if env:
        return env.rstrip("/")
    port = 8989
    try:
        with open(os.path.join(_ROOT, "..", "..", "config.json"), encoding="utf-8-sig") as f:
            port = int(((json.load(f) or {}).get("server") or {}).get("port") or 8989)
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return f"http://127.0.0.1:{port}"


def get(path: str, params: dict, ttl: float = 0.0, timeout: float = 8.0):
    """관제에 GET → (상태, Content-Type, 본문, Content-Disposition). ttl 초 동안은 같은 답을 쓴다
    (여럿이 보고 있어도 관제에는 한 번만 묻는다). 닿지 않으면 OSError."""
    url = base() + path + "?" + urllib.parse.urlencode(params)
    now = time.time()
    if ttl:
        with _CL:
            hit = _CACHE.get(url)
        if hit and now - hit[0] < ttl:
            return hit[1]
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            out = (r.status, r.headers.get("Content-Type") or "", r.read(),
                   r.headers.get("Content-Disposition") or "")
    except urllib.error.HTTPError as e:
        out = (e.code, e.headers.get("Content-Type") or "", e.read(), "")
    if ttl and out[0] == 200:
        with _CL:
            _CACHE[url] = (now, out)
            for k in [k for k, v in _CACHE.items() if now - v[0] > 300]:
                _CACHE.pop(k, None)
    return out


def feed(fab: str, prefix: str, limit: int) -> dict:
    """그 FAB 의 관제 표 — 최근 limit 분 (최신이 위)."""
    sysname = sys_for(fab, prefix)
    where = base()
    if not sysname:
        return {"ok": False, "error": f"이 지도({fab}/{prefix})는 관제 시스템과 짝이 없습니다"}
    try:
        st, _ct, body, _cd = get("/api/feed", {"sys": sysname, "limit": limit}, ttl=5)
    except OSError as e:
        return {"ok": False, "sys": sysname, "gwanje": where,
                "error": f"관제({where})에 닿지 않습니다 — 관제 서버가 켜져 있는지 보세요 ({e})"}
    if st != 200:
        return {"ok": False, "sys": sysname, "gwanje": where,
                "error": f"관제가 HTTP {st} 로 답했습니다 — 관제를 새 판으로 바꿨는지 보세요"}
    try:
        d = json.loads(body.decode("utf-8"))
    except ValueError:
        return {"ok": False, "sys": sysname, "gwanje": where, "error": "관제 답을 못 읽었습니다"}
    rows = [{k: r[k] for k in _ROW_KEYS if k in r} for r in (d.get("rows") or [])[:limit]]
    return {"ok": True, "sys": sysname, "gwanje": where, "rows": rows,
            "day": d.get("day"), "fallback": d.get("fallback"), "latest": d.get("latest"),
            "alarm_now": d.get("alarm_now"), "fab_cuts": d.get("fab_cuts") or {}}


def passthrough(fab: str, prefix: str, which: str, q: dict):
    """관제가 그린 것을 그대로 — which: graph(구간 그래프 SVG) · contrib(기여도 HTML) · report(RET 내려받기).
    → (상태, Content-Type, 본문, 덧붙일 헤더)."""
    sysname = sys_for(fab, prefix)
    if not sysname:
        return 404, "application/json", json.dumps(
            {"error": "이 지도는 관제 시스템과 짝이 없습니다"}, ensure_ascii=False).encode("utf-8"), {}
    one = lambda k: str(q.get(k) or "")                              # noqa: E731
    if which == "graph":
        src, params, ttl = "/api/graph", {"at": one("at"), "minutes": one("minutes") or "60",
                                          "theme": one("theme") or "dark"}, 30
    elif which == "contrib":
        src, params, ttl = "/api/contrib", {"at": one("at")}, 30
    else:
        src, params, ttl = "/api/oht_map/report", {"day": one("day"), "name": one("name")}, 0
    params["sys"] = sysname
    try:
        st, ct, body, cd = get(src, params, ttl=ttl, timeout=20)
    except OSError as e:
        return 502, "application/json", json.dumps(
            {"error": f"관제({base()})에 닿지 않습니다 — {e}"}, ensure_ascii=False).encode("utf-8"), {}
    return st, ct or "application/octet-stream", body, ({"Content-Disposition": cd} if cd else {})
