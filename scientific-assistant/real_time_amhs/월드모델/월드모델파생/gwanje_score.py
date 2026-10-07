#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gwanje_score.py — 실시간 모드 오른쪽 '스코어' 탭: 관제(real_time_amhs)가 매긴 그 FAB 의 스코어를 받아 온다.

고객 2026-10-06: "실시간에 이제 기존 스코어 점수랑 그런 데이터들이 들어가야 돼. 스코어 표랑 그런 거
볼 수 있게" · "HID_JAM, RET(레포트) 더블클릭하면 그래프 정보도 실시간에 전부 다 표시돼야 돼".

★점수를 여기서 다시 계산하지 않는다 — 다시 계산하면 관제 표와 숫자가 어긋난다. 관제가 매긴 점수 ·
  등급(정책 컷) · 알람 카운터 · 발동 룰 · 실제지표 · HID_JAM · RET 를 그대로 넘긴다.
★지도 → 관제 시스템 (관제 world_link.MAP 의 반대 방향). FAB 화면이라 그 FAB 것만 묻는다.
★관제 주소 — 환경변수 GWANJE_URL > 화면 스코어 탭에서 저장한 주소(관제_주소.json, 이 PC 에만) >
  이 PC 의 관제 (real_time_amhs/config.json 의 server.port, 기본 8989). 관제가 다른 서버에 있으면
  탭의 '관제 주소' 에서 그 서버 주소로 바꾼다. 관제가 꺼져 있어도 OHT 실시간은 그대로 돈다 —
  탭에 "관제에 닿지 않습니다" 만 뜬다.
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


# ★관제 주소는 이 PC 에만 둔다 — 화면 스코어 탭 '관제 주소' 에서 바꾸면 여기 적힌다.
#   고객(2026-10-07): "실시간관제 외부에서 접속하게 해야지 127.0.0.1 하면 안 되지" ·
#   "실시간에서 다른 서버에서 접속하는데 경계가 있어야 하는데 없네". 관제가 다른 서버에
#   떠 있으면 127.0.0.1 로는 그 관제에 닿지 않는다 (이 PC 의 다른 관제 · 빈 관제를 본다).
#   저장소에는 안 올린다 (.gitignore) — 서버마다 다르다.
ADDR_FILE = os.path.join(_ROOT, "관제_주소.json")
_ADDR_RE = __import__("re").compile(r"^https?://[A-Za-z0-9._\-]+(:\d{1,5})?$")


def _default_base() -> str:
    """이 PC 의 관제 (real_time_amhs/config.json 의 server.port, 기본 8989)."""
    port = 8989
    try:
        with open(os.path.join(_ROOT, "..", "..", "config.json"), encoding="utf-8-sig") as f:
            port = int(((json.load(f) or {}).get("server") or {}).get("port") or 8989)
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return f"http://127.0.0.1:{port}"


def _saved_base() -> str:
    try:
        with open(ADDR_FILE, encoding="utf-8-sig") as f:
            u = str((json.load(f) or {}).get("url") or "").strip().rstrip("/")
        return u if _ADDR_RE.match(u) else ""
    except (OSError, ValueError, TypeError, AttributeError):
        return ""


def addr() -> dict:
    """지금 묻는 관제 주소와 그 출처 — env(환경변수) · file(화면에서 저장) · default(이 PC)."""
    env = os.environ.get("GWANJE_URL", "").strip()
    if env:
        return {"url": env.rstrip("/"), "src": "env"}
    saved = _saved_base()
    if saved:
        return {"url": saved, "src": "file"}
    return {"url": _default_base(), "src": "default"}


def base() -> str:
    """관제 주소 — 환경변수 GWANJE_URL > 화면에서 저장한 주소(관제_주소.json) > 이 PC 의 관제."""
    return addr()["url"]


def norm_addr(url: str) -> str:
    """'10.1.2.3:8989' · 'http://10.1.2.3:8989/' → 'http://10.1.2.3:8989'. 틀리면 ValueError."""
    u = str(url or "").strip().rstrip("/")
    if u and "://" not in u:
        u = "http://" + u
    if u and not _ADDR_RE.match(u):
        raise ValueError("관제 주소는 http://주소:포트 모양이어야 합니다 (예: http://10.1.2.3:8989)")
    return u


def set_addr(url: str) -> dict:
    """화면에서 관제 주소를 바꾼다. 빈 값이면 지우고 이 PC 의 관제로 돌아간다."""
    u = norm_addr(url)
    if u:
        tmp = ADDR_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"url": u}, f, ensure_ascii=False)
        os.replace(tmp, ADDR_FILE)
    else:
        try:
            os.remove(ADDR_FILE)
        except OSError:
            pass
    with _CL:
        _CACHE.clear()                     # 옛 주소로 받아 둔 답을 쓰지 않는다
    return addr()


def check() -> dict:
    """그 주소의 관제가 답하나 — 화면이 주소를 바꾼 뒤 바로 알려 준다."""
    a = addr()
    try:
        # ★/api/ping 은 관제가 로그프레소를 찔러 보는 길이라 느리고, 로그프레소가 죽으면 관제가
        #   멀쩡해도 실패한다. 관제 자체가 답하는지는 /api/status 로 본다.
        st, _ct, body, _cd = get("/api/status", {"sys": "ALL"}, timeout=4)
    except OSError as e:
        return dict(a, ok=False, error=f"관제({a['url']})에 닿지 않습니다 — {e}")
    if st != 200:
        return dict(a, ok=False, error=f"관제({a['url']})가 HTTP {st} 로 답했습니다")
    return dict(a, ok=True)


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
        return {"ok": False, "sys": sysname, "gwanje": where, "gwanje_src": addr()["src"],
                "error": f"관제({where})에 닿지 않습니다 — 관제 서버가 켜져 있는지, "
                         f"관제 주소가 맞는지 보세요 ({e})"}
    if st != 200:
        return {"ok": False, "sys": sysname, "gwanje": where,
                "error": f"관제가 HTTP {st} 로 답했습니다 — 관제를 새 판으로 바꿨는지 보세요"}
    try:
        d = json.loads(body.decode("utf-8"))
    except ValueError:
        return {"ok": False, "sys": sysname, "gwanje": where, "error": "관제 답을 못 읽었습니다"}
    rows = [{k: r[k] for k in _ROW_KEYS if k in r} for r in (d.get("rows") or [])[:limit]]
    cuts = dict(d.get("fab_cuts") or {})
    if not (cuts.get(sysname) or {}).get("warn"):
        # ★FAB 점수표 계산이 실패하면 관제가 fab_cuts 를 비워 보낸다 — 그러면 탭의 경계선 ·
        #   '경계 60 · 위험 …' 글자가 통째로 사라졌다. 그 시스템 등급 컷(/api/status)으로 채운다.
        try:
            st2, _c2, b2, _d2 = get("/api/status", {"sys": sysname}, ttl=60, timeout=4)
            c2 = (json.loads(b2.decode("utf-8")) or {}).get("cuts") if st2 == 200 else None
            if c2 and c2.get("warn") is not None:
                cuts[sysname] = c2
        except (OSError, ValueError):
            pass
    return {"ok": True, "sys": sysname, "gwanje": where, "gwanje_src": addr()["src"], "rows": rows,
            "day": d.get("day"), "fallback": d.get("fallback"), "latest": d.get("latest"),
            "alarm_now": d.get("alarm_now"), "fab_cuts": cuts}


def passthrough(fab: str, prefix: str, which: str, q: dict):
    """관제가 그린 것을 그대로 — which: graph(구간 그래프 SVG) · graph1(그 칸 하나 크게)
    · cause(그 분 룰 원인) · report(RET 내려받기). → (상태, Content-Type, 본문, 덧붙일 헤더).
    ★기여도(contrib)는 뺐다 (2026-10-07 고객: "기여도 추정 삭제해라 필요없어").
    ★graph1 · cause (2026-10-07 고객: "그래프 더블클릭하면 1개 크게" · "그래프 클릭하면
      원인 내용 적어 주라") — 관제 화면과 같은 것을 그대로 넘긴다."""
    sysname = sys_for(fab, prefix)
    if not sysname:
        return 404, "application/json", json.dumps(
            {"error": "이 지도는 관제 시스템과 짝이 없습니다"}, ensure_ascii=False).encode("utf-8"), {}
    one = lambda k: str(q.get(k) or "")                              # noqa: E731
    if which == "graph":
        src, params, ttl = "/api/graph", {"at": one("at"), "minutes": one("minutes") or "60",
                                          "theme": one("theme") or "dark"}, 30
    elif which == "graph1":
        src, params, ttl = "/api/graph1", {"at": one("at"), "minutes": one("minutes") or "60",
                                           "theme": one("theme") or "dark",
                                           "name": one("name")}, 30
    elif which == "cause":
        src, params, ttl = "/api/cause", {"at": one("at")}, 30
    elif which == "report":
        src, params, ttl = "/api/oht_map/report", {"day": one("day"), "name": one("name")}, 0
    else:
        # 모르는 것은 관제에 묻지 않는다 — 예전엔 나머지가 전부 '레포트' 로 흘러갔다
        return 404, "application/json", json.dumps(
            {"error": f"모르는 요청입니다: {which}"}, ensure_ascii=False).encode("utf-8"), {}
    params["sys"] = sysname
    try:
        st, ct, body, cd = get(src, params, ttl=ttl, timeout=20)
    except OSError as e:
        return 502, "application/json", json.dumps(
            {"error": f"관제({base()})에 닿지 않습니다 — {e}"}, ensure_ascii=False).encode("utf-8"), {}
    return st, ct or "application/octet-stream", body, ({"Content-Disposition": cd} if cd else {})
