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
import re
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
_ADDR_RE = re.compile(r"^https?://[A-Za-z0-9._\-]+(:\d{1,5})?$")


# ★관제에 물을 때 **사내 프록시를 타지 않는다**. 그냥 urlopen 은 윈도우 IE 프록시를 타서, 관제
#   (같은 PC 든 사내 IP 든)에 닿지 못하고 프록시가 대신 답했다 — 관제 쪽도 같은 일을 겪어
#   config.query.use_proxy=false 가 기본이다. 실시간 스코어 탭에 경계가 안 보인 원인으로 본다.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
# 화면이 들어온 길에서 본 관제 후보 — 관제 화면에서 넘어온 주소(?gw= · referrer) · 이 서버 주소
_HINTS: list = []
# 마지막으로 찾은 관제 {url, src, ok, at, key}
_RES: dict = {"url": "", "src": "", "ok": False, "at": 0.0, "key": None}
_RL = threading.Lock()


def _gw_server() -> dict:
    """관제 설정 real_time_amhs/config.json 의 server 칸 (읽기만 한다)."""
    try:
        with open(os.path.join(_ROOT, "..", "..", "config.json"), encoding="utf-8-sig") as f:
            s = (json.load(f) or {}).get("server") or {}
        return s if isinstance(s, dict) else {}
    except (OSError, ValueError, TypeError, AttributeError):
        return {}


def port() -> int:
    """관제 포트 — real_time_amhs/config.json 의 server.port (기본 8989)."""
    try:
        return int(_gw_server().get("port") or 8989)
    except (ValueError, TypeError):
        return 8989


def _default_base() -> str:
    """이 PC 의 관제 (real_time_amhs/config.json 의 server.port, 기본 8989)."""
    return f"http://127.0.0.1:{port()}"


def _conf_base() -> str:
    """관제 설정이 host 를 사내 IP 하나로 박아 두면(0.0.0.0 이 아니면) 127.0.0.1 로는 안 열린다 —
    그 IP 도 후보로 (사람이 넣을 것 없이)."""
    h = str(_gw_server().get("host") or "").strip()
    if not h or h in ("0.0.0.0", "::", "127.0.0.1", "localhost") or not re.match(r"^[A-Za-z0-9.\-]+$", h):
        return ""
    return f"http://{h}:{port()}"


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


def note_hints(*urls) -> None:
    """화면이 들어온 길에서 본 관제 후보를 적어 둔다 — 관제가 다른 서버에 있어도 스스로 찾게.

    ★고객(2026-10-07): "관제 주소를 왜 바꾸는데 — 처음부터 보이게 하면 되지". 사람이 주소를
      넣지 않아도 관제 화면에서 넘어온 주소 · 이 서버 주소로 찾아간다 (resolve).
    """
    with _RL:
        added = False
        for u in urls:
            try:
                u = norm_addr(u)
            except ValueError:
                continue
            if u and u not in _HINTS:
                _HINTS.insert(0, u)
                added = True
        del _HINTS[8:]
        if added and not _RES["ok"]:
            _RES["at"] = 0.0                   # 못 찾고 있었다 — 새 후보로 바로 다시


def _candidates() -> list:
    """찾아볼 차례 — 정한 주소(환경변수 · 화면 저장) → 이 PC → 관제 설정의 IP → 화면이 들어온 길."""
    a = addr()
    out = [(a["url"], a["src"])]
    if a["src"] == "env":
        return out                             # 환경변수로 박았으면 그것만 본다
    with _RL:
        hints = list(_HINTS)
    for u in [_default_base(), _conf_base()] + hints:
        if u and u not in [x for x, _s in out]:
            out.append((u, "auto"))
    return out


def _probe(u: str, timeout: float = 2.5) -> bool:
    """그 주소에 **관제**가 답하나 (다른 프로그램이 같은 포트를 쓰는 것과 가른다)."""
    try:
        with _OPENER.open(u + "/api/status?sys=ALL", timeout=timeout) as r:
            if r.status != 200:
                return False
            d = json.loads(r.read().decode("utf-8", "replace") or "{}")
        return isinstance(d, dict) and "systems" in d
    except Exception:                                   # noqa: BLE001
        return False


def resolve(force: bool = False) -> dict:
    """지금 답하는 관제 {url, src, ok}. 찾은 것은 5분, 못 찾은 것은 20초 기억한다."""
    cands = _candidates()
    key = tuple(u for u, _s in cands)
    now = time.time()
    with _RL:
        r = dict(_RES)
    if not force and r["key"] == key and r["url"] and now - r["at"] < (300 if r["ok"] else 20):
        return {"url": r["url"], "src": r["src"], "ok": r["ok"]}
    found = None
    for u, src in cands:
        if _probe(u):
            found = {"url": u, "src": src, "ok": True}
            break
    if found is None:                          # 아무도 답하지 않는다 — 정한 주소로 묻고 오류를 보인다
        found = {"url": cands[0][0], "src": cands[0][1], "ok": False}
    elif found["src"] == "auto" and found["url"] != _default_base():
        # 스스로 찾은 다른 서버의 관제 — 이 PC 에 적어 두면 다시 띄워도 처음부터 그 관제를 본다
        try:
            _save_file(found["url"])
            key = tuple(u for u, _s in _candidates())
        except OSError:
            pass
    with _RL:
        _RES.update(found, at=now, key=key)
    return found


def base() -> str:
    """관제 주소 — 정한 주소(환경변수 · 화면 저장) · 이 PC · 화면이 들어온 길 중 **답하는 곳**."""
    return resolve()["url"]


def norm_addr(url: str) -> str:
    """'10.1.2.3:8989' · 'http://10.1.2.3:8989/' → 'http://10.1.2.3:8989'. 틀리면 ValueError."""
    u = str(url or "").strip().rstrip("/")
    if u and "://" not in u:
        u = "http://" + u
    if u and not _ADDR_RE.match(u):
        raise ValueError("관제 주소는 http://주소:포트 모양이어야 합니다 (예: http://10.1.2.3:8989)")
    return u


def _save_file(u: str) -> None:
    tmp = ADDR_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"url": u}, f, ensure_ascii=False)
    os.replace(tmp, ADDR_FILE)


def set_addr(url: str) -> dict:
    """화면에서 관제 주소를 바꾼다. 빈 값이면 지우고 이 PC 의 관제로 돌아간다."""
    u = norm_addr(url)
    if u:
        _save_file(u)
    else:
        try:
            os.remove(ADDR_FILE)
        except OSError:
            pass
    with _CL:
        _CACHE.clear()                     # 옛 주소로 받아 둔 답을 쓰지 않는다
    with _RL:
        _RES.update(at=0.0, key=None)      # 다시 찾는다
    return addr()


def check() -> dict:
    """지금 답하는 관제가 있나 — 화면이 주소를 바꾼 뒤 바로 알려 준다.
    ★/api/ping 은 관제가 로그프레소를 찔러 보는 길이라 느리고, 로그프레소가 죽으면 관제가 멀쩡해도
      실패한다. 관제 자체가 답하는지는 /api/status 로 본다 (_probe)."""
    r = resolve(force=True)
    if r["ok"]:
        return r
    return dict(r, error=f"관제({r['url']})에 닿지 않습니다 — 관제 서버가 켜져 있는지 보세요")


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
        with _OPENER.open(url, timeout=timeout) as r:           # 사내 프록시를 타지 않는다
            out = (r.status, r.headers.get("Content-Type") or "", r.read(),
                   r.headers.get("Content-Disposition") or "")
    except urllib.error.HTTPError as e:
        out = (e.code, e.headers.get("Content-Type") or "", e.read(), "")
    except OSError:
        with _RL:
            _RES.update(at=0.0)            # 닿던 관제가 꺼졌다 — 다음에 다시 찾는다
        raise
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
        return {"ok": False, "sys": sysname, "gwanje": where, "gwanje_src": resolve()["src"],
                "error": f"관제에 닿지 않습니다 — 이 PC({_default_base()})와 관제 화면에서 넘어온 주소를 "
                         f"다 찾아봤습니다. 관제 서버가 켜져 있는지 보세요 ({e})"}
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
    return {"ok": True, "sys": sysname, "gwanje": where, "gwanje_src": resolve()["src"], "rows": rows,
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
