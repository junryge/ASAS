#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py — 월드모델파생_실시간 서버 (기본 http://localhost:10006)

    python main.py

월드모델파생(재생판)과 **같은 화면**을 띄우되, 재생 대신 로그프레소의 '지금' 을 흘려준다.
  · 화면 파일은 옆 폴더 월드모델파생/dashboard.html **그대로**다 — 이 서버가 내줄 때 조각 둘만
    끼운다 (live_ws.js: 웹소켓 → 1초마다 HTTP · live_ui.js: 재생 단추 숨김 + 실시간 상태줄).
    그래서 월드모델파생 화면을 고치면 실시간판에도 그대로 들어온다.
  · 데이터는 live_engine.py — FAB(지도)마다 피드 하나를 보는 사람이 같이 쓴다.
  · ★표준 파이썬만 쓴다 (FastAPI · uvicorn 없이 뜬다). 웹소켓 대신 1초 HTTP 라
    한 사람이 초당 스냅샷 하나(차 수백 대 ≈ 100KB)를 받는다 — 사내망에서는 가볍다.
  · 월드모델파생(10005)과 포트가 달라 둘을 같이 띄워도 된다.

환경변수 — LIVE_PORT(10006) · LIVE_FAB(M16A/BR 처럼 처음 지도) · LIVE_POLL_SEC(5) ·
  LIVE_BUFFER_SEC(8) · LIVE_WARM_SEC(300) · 그 밖은 live_engine.py 머리말.
주소에 ?fab=M16A&prefix=BR 를 붙이면 그 지도로 연다 (관제에서 바로 열 때).
"""

import http.server
import json
import mimetypes
import os
import secrets
import socketserver
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import live_engine as LE                      # noqa: E402  (월드모델파생 경로도 여기서 잡힌다)

PORT = int(os.environ.get("LIVE_PORT", "10006") or 10006)
HOST = os.environ.get("LIVE_HOST", "0.0.0.0")
COOKIE = "oht_live_sid"
SESSION_TTL_SEC = 3600
SESSION_MAX = 64
DASH = os.path.join(LE.WM_DIR, "dashboard.html")
STATIC = os.path.join(LE.WM_DIR, "static")

# ── 사람마다 고른 지도 (쿠키 한 줄). 데이터(피드)는 지도마다 하나를 같이 쓴다 ──
SESS: dict = {}
_SL = threading.Lock()


def _session(sid):
    """(sid, 세션, 새로 만들었나)."""
    now = time.time()
    with _SL:
        s = SESS.get(sid) if sid else None
        fresh = s is None
        if fresh:
            sid = secrets.token_urlsafe(16)
            fab, pre = LE.default_fab()
            # playing — 이 화면이 [▶ 실시간 PLAY] 중인 지도 (없으면 None)
            s = SESS[sid] = {"fab": fab, "prefix": pre, "sid": sid, "playing": None}
        s["seen"] = now
        dead = [k for k, v in SESS.items() if now - v["seen"] > SESSION_TTL_SEC]
        live = sorted((v["seen"], k) for k, v in SESS.items() if k not in dead)
        dead += [k for _, k in live[:max(0, len(live) - SESSION_MAX)]]
        for k in dead:
            if k != sid:
                SESS.pop(k, None)
    return sid, s, fresh


def _others_playing(key, sid) -> bool:
    """이 화면 말고도 그 지도를 PLAY 중인 화면이 있나."""
    with _SL:
        return any(v.get("playing") == key for k, v in SESS.items() if k != sid)


def play(s, why=""):
    """이 화면이 보는 지도를 PLAY. 앞에 PLAY 하던 다른 지도는 (다른 화면이 안 보면) 멈춘다
    — 보는 FAB 하나만 묻는다 (고객: "전부 다 조회하면 안 되니까")."""
    key = (s["fab"], s["prefix"])
    old = s.get("playing")
    if old and old != key and not _others_playing(old, s["sid"]):
        with LE._FL:
            f_old = LE._FEEDS.get(old)
        if f_old:
            f_old.stop(f"화면이 {key[0]}/{key[1]} 로 옮김")
    s["playing"] = key
    LE.feed_for(*key).play(why)


def stop(s):
    """이 화면이 보는 지도를 정지 — ★그 지도를 PLAY 중인 다른 화면이 있으면 그 화면 것은 그대로 돈다."""
    key = (s["fab"], s["prefix"])
    s["playing"] = None
    if not _others_playing(key, s["sid"]):
        LE.feed_for(*key).stop("■ 정지")


def _known(fab, prefix) -> bool:
    return any((e["fab"], e["prefix"]) == (fab, prefix) for e in LE.catalog())


# ── 화면 — 월드모델파생 dashboard.html + 조각 둘 ──────────────────────────
def _read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


def page_html() -> str:
    with open(DASH, encoding="utf-8") as f:
        h = f.read()
    head = "<script>\n" + _read("live_ws.js") + "\n</script>\n"
    tail = "<script>\n" + _read("live_ui.js") + "\n</script>\n"
    i = h.find("<head>")
    h = (h[:i + 6] + "\n" + head + h[i + 6:]) if i >= 0 else head + h
    j = h.rfind("</body>")
    return (h[:j] + tail + h[j:]) if j >= 0 else h + tail


def layout_graph(fab, prefix) -> dict:
    """맵 배경 — 월드모델파생 /api/layout-graph 와 같은 모양 (화면이 그 모양을 그린다)."""
    lay, hz = LE.layout_for(fab, prefix)
    nodes = {str(n): [round(c[0], 1), round(c[1], 1)] for n, c in lay.nodes.items()}
    edges = [[a, b] for (a, b) in lay.edge_dist.keys()]
    zones = []
    for zid, z in hz.zones.items():
        ins = [{"from": a, "to": b} for (a, b), x in hz.in_lane_to_zone.items()
               if x == zid and a in lay.nodes and b in lay.nodes]
        outs = [{"from": a, "to": b} for (a, b), x in hz.out_lane_to_zone.items()
                if x == zid and a in lay.nodes and b in lay.nodes]
        ns = {l["from"] for l in ins + outs} | {l["to"] for l in ins + outs}
        xs = [lay.nodes[n][0] for n in ns]
        ys = [lay.nodes[n][1] for n in ns]
        if not xs:
            continue
        zones.append({"id": zid, "name": z.get("fullName", f"Zone-{zid}"), "bay": z.get("bayZone", ""),
                      "hid": z.get("hidNo", ""), "max": z.get("vehicleMax", 37),
                      "inLanes": ins, "outLanes": outs,
                      "cx": round(sum(xs) / len(xs), 1), "cy": round(sum(ys) / len(ys), 1)})
    return {"nodes": nodes, "edges": edges, "bounds": lay.bounds, "zones": zones,
            "schema": getattr(lay, "schema", 1),
            "meta": {str(k): v for k, v in getattr(lay, "meta", {}).items()},
            "stations": getattr(lay, "stations", []), "labels": getattr(lay, "labels", []),
            "sensors": getattr(lay, "sensors", [])}


def live_snapshot(fab, prefix) -> dict:
    """화면 한 장 — 재생판 웹소켓이 보내던 것과 같은 모양 + 'live' (상태줄)."""
    f = LE.feed_for(fab, prefix)
    t, snap = f.current()
    out = dict(snap) if snap else {
        "time": "", "time_short": "--:--:--", "frame": 0, "totalFrames": 0, "state": "playing",
        "speed": 1, "date": "LIVE", "vehicleStats": {"total": 0}, "vehicles": [], "star": None,
        "prediction": {}, "hidSpeeds": {}, "railCuts": [], "zoneCounts": {}, "hotspots": []}
    out["live"] = dict(f.info(t), warm_sec=LE.WARM_SEC)
    return out


def live_snapshot_for(s) -> dict:
    out = live_snapshot(s["fab"], s["prefix"])
    out["live"]["me_playing"] = s.get("playing") == (s["fab"], s["prefix"])
    return out


# ── 관제(real_time_amhs) 스코어 — 점수를 다시 계산하지 않고 관제에 묻는다 ─────────
# ★관제가 매긴 점수 · 등급(정책 컷) · 알람 카운터 · 발동 룰 · 실제지표 · HID_JAM · RET 를
#   그대로 받아 온다. 여기서 다시 계산하면 관제 표와 숫자가 어긋난다.
# ★지도 → 관제 시스템 (관제 world_link.MAP 의 반대 방향). FAB 화면이라 그 FAB 것만 묻는다.
GW_SYS = {("M14A", "A"): "M14", ("M14B", "A"): "M14B", ("M16A", "A"): "M16A",
          ("M16B", "B"): "M16B", ("M16A", "BR"): "M16HUB"}
# 화면에 필요한 칸만 넘긴다 (관제 행에는 AMOS 원본 지표 값까지 실려 무겁다)
_ROW_KEYS = ("at", "datetime", "time", "score", "level", "emoji", "area", "reason", "metrics",
             "alm", "hi_fab", "fab", "fab_lv", "hid", "case_id")
_GW_CACHE: dict = {}
_GWL = threading.Lock()


def gwanje_base() -> str:
    """관제 주소 — 환경변수 GWANJE_URL, 없으면 이 PC 의 관제(real_time_amhs/config.json 의 포트)."""
    env = os.environ.get("GWANJE_URL", "").strip()
    if env:
        return env.rstrip("/")
    port = 8989
    try:
        with open(os.path.join(HERE, "..", "..", "config.json"), encoding="utf-8-sig") as f:
            port = int(((json.load(f) or {}).get("server") or {}).get("port") or 8989)
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return f"http://127.0.0.1:{port}"


def gw_get(path: str, params: dict, ttl: float = 0.0, timeout: float = 8.0):
    """관제에 GET → (상태, Content-Type, 본문, Content-Disposition). ttl 초 동안은 같은 답을 쓴다
    (여럿이 보고 있어도 관제에는 한 번만 묻는다)."""
    url = gwanje_base() + path + "?" + urllib.parse.urlencode(params)
    now = time.time()
    if ttl:
        with _GWL:
            hit = _GW_CACHE.get(url)
        if hit and now - hit[0] < ttl:
            return hit[1]
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            out = (r.status, r.headers.get("Content-Type") or "", r.read(),
                   r.headers.get("Content-Disposition") or "")
    except urllib.error.HTTPError as e:
        out = (e.code, e.headers.get("Content-Type") or "", e.read(), "")
    if ttl and out[0] == 200:
        with _GWL:
            _GW_CACHE[url] = (now, out)
            for k in [k for k, v in _GW_CACHE.items() if now - v[0] > 300]:
                _GW_CACHE.pop(k, None)
    return out


def _gw_sys(s) -> str:
    return GW_SYS.get((s["fab"], s["prefix"]), "")


def score_feed(s, limit: int) -> dict:
    """그 FAB 의 관제 표 — 최근 limit 분 (최신이 위)."""
    sysname = _gw_sys(s)
    base = gwanje_base()
    if not sysname:
        return {"ok": False, "error": f"이 지도({s['fab']}/{s['prefix']})는 관제 시스템과 짝이 없습니다"}
    try:
        st, _ct, body, _cd = gw_get("/api/feed", {"sys": sysname, "limit": limit}, ttl=5)
    except OSError as e:
        return {"ok": False, "sys": sysname, "gwanje": base,
                "error": f"관제({base})에 닿지 않습니다 — 관제 서버가 켜져 있는지 보세요 ({e})"}
    if st != 200:
        return {"ok": False, "sys": sysname, "gwanje": base,
                "error": f"관제가 HTTP {st} 로 답했습니다 — 관제를 새 판으로 바꿨는지 보세요"}
    try:
        d = json.loads(body.decode("utf-8"))
    except ValueError:
        return {"ok": False, "sys": sysname, "gwanje": base, "error": "관제 답을 못 읽었습니다"}
    rows = [{k: r[k] for k in _ROW_KEYS if k in r} for r in (d.get("rows") or [])[:limit]]
    return {"ok": True, "sys": sysname, "gwanje": base, "rows": rows,
            "day": d.get("day"), "fallback": d.get("fallback"), "latest": d.get("latest"),
            "alarm_now": d.get("alarm_now"), "fab_cuts": d.get("fab_cuts") or {}}


# 재생판에만 있는 것 — 화면이 불러도 깨지지 않게 빈 값을 준다
EMPTY_GET = {"/api/star-history": [], "/api/obs-jam-history": [], "/api/hid-speeds": {},
             "/api/bottleneck-analysis": {}, "/api/dates": [], "/api/predict": {},
             "/api/correlations": {}, "/api/hotspot-history": [], "/api/ts-events": []}
NO_REPLAY = {"live": True, "cancelled": True,
             "error": "실시간 화면에는 구간 조회·재생이 없습니다 — 월드모델파생(10005)에서 하세요"}


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "OHTLive/1.0"

    def log_message(self, fmt, *args):          # 1초마다 오는 요청을 다 찍으면 창이 넘친다
        if args and str(args[1] if len(args) > 1 else "").startswith(("4", "5")):
            sys.stderr.write("[요청] %s - %s\n" % (self.address_string(), fmt % args))

    # ── 공통 ──
    def _sess(self):
        c = self.headers.get("Cookie") or ""
        sid = None
        for part in c.split(";"):
            k, _, v = part.strip().partition("=")
            if k == COOKIE:
                sid = v
        sid, s, fresh = _session(sid)
        self._new_sid = sid if fresh else None
        return s

    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False, default=str)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        if getattr(self, "_new_sid", None):
            self.send_header("Set-Cookie", f"{COOKIE}={self._new_sid}; Path=/; HttpOnly; SameSite=Lax; "
                                           f"Max-Age={SESSION_TTL_SEC}")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json_body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        try:
            b = json.loads(self.rfile.read(n) or b"{}") if n else {}
        except ValueError:
            b = {}
        return b if isinstance(b, dict) else {}

    # ── GET ──
    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        path, q = u.path, urllib.parse.parse_qs(u.query)
        try:
            if path.startswith("/static/"):
                return self._static(path[len("/static/"):])
            s = self._sess()
            if path in ("/", "/index.html"):
                fab, pre = (q.get("fab") or [""])[0].strip(), (q.get("prefix") or [""])[0].strip()
                if fab and pre and _known(fab, pre):
                    s["fab"], s["prefix"] = fab, pre       # 관제에서 바로 열 때 — 그 지도로
                return self._send(200, page_html(), "text/html; charset=utf-8")
            if path == "/api/live/snapshot":
                return self._send(200, live_snapshot_for(s))
            if path == "/api/live/status":
                with LE._FL:
                    feeds = list(LE._FEEDS.values())
                return self._send(200, {"feeds": [f.info() for f in feeds],
                                        "sessions": len(SESS), "wm_dir": LE.WM_DIR})
            if path == "/api/fabs":
                return self._send(200, {
                    "catalog": [{"fab": e["fab"], "prefix": e["prefix"], "has_data": True, "dates": [],
                                 "table": e["table"]} for e in LE.catalog()],
                    "current": {"fab": s["fab"], "prefix": s["prefix"]}})
            if path == "/api/layout-graph":
                return self._send(200, layout_graph(s["fab"], s["prefix"]))
            if path == "/api/layout-bounds":
                return self._send(200, LE.layout_for(s["fab"], s["prefix"])[0].bounds)
            if path == "/api/status":
                snap = live_snapshot(s["fab"], s["prefix"])
                snap.pop("vehicles", None)
                return self._send(200, snap)
            if path == "/api/hid-zones":
                return self._send(200, LE.feed_for(s["fab"], s["prefix"]).world.get_zone_status())
            if path == "/api/score/feed":
                try:
                    n = max(1, min(240, int((q.get("limit") or ["90"])[0])))
                except ValueError:
                    n = 90
                return self._send(200, score_feed(s, n))
            if path in ("/api/score/graph", "/api/score/contrib", "/api/score/report"):
                return self._gw_pass(s, path, q)
            if path in EMPTY_GET:
                return self._send(200, EMPTY_GET[path])
            if path == "/favicon.ico":
                return self._send(204, b"", "image/x-icon")
            return self._send(404, {"error": f"없는 주소: {path}"})
        except Exception as e:                                   # noqa: BLE001
            print(f"[서버] {path} 실패: {type(e).__name__}: {e}")
            return self._send(500, {"error": f"{type(e).__name__}: {e}"})

    do_HEAD = do_GET

    # ── POST ──
    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        try:
            s = self._sess()
            b = self._json_body()
            if path == "/api/fab/select":
                fab, pre = str(b.get("fab") or "").strip(), str(b.get("prefix") or "").strip()
                if not _known(fab, pre):
                    return self._send(400, {"error": f"모르는 지도입니다: {fab}/{pre}"})
                changed = (fab, pre) != (s["fab"], s["prefix"])
                lay, hz = LE.layout_for(fab, pre)
                was = s.get("playing")
                s["fab"], s["prefix"] = fab, pre
                if was:                                    # PLAY 중이었으면 새 지도로 옮겨 PLAY
                    play(s, "지도 바꿈")
                else:
                    LE.feed_for(fab, pre)
                return self._send(200, {"fab": fab, "prefix": pre, "changed": changed,
                                        "bounds": lay.bounds, "nodes": len(lay.nodes),
                                        "edges": len(lay.edge_dist), "zones": len(hz.zones),
                                        "table": LE.table_for(fab, pre)})
            if path == "/api/live/cmd":
                act = str(b.get("action") or "")
                if act == "play":
                    play(s, "화면에서 PLAY")
                elif act == "stop":
                    stop(s)
                else:
                    return self._send(400, {"error": f"모르는 명령: {act}"})
                return self._send(200, live_snapshot_for(s)["live"])
            if path.startswith(("/api/logpresso/", "/api/replay/")):
                return self._send(200, NO_REPLAY)
            return self._send(404, {"error": f"없는 주소: {path}"})
        except Exception as e:                                   # noqa: BLE001
            print(f"[서버] {path} 실패: {type(e).__name__}: {e}")
            return self._send(500, {"error": f"{type(e).__name__}: {e}"})

    # ── 관제 그래프 · 기여도 · RET(레포트) — 관제가 그린 것을 그대로 넘긴다 ──
    def _gw_pass(self, s, path, q):
        sysname = _gw_sys(s)
        if not sysname:
            return self._send(404, {"error": "이 지도는 관제 시스템과 짝이 없습니다"})
        one = lambda k: (q.get(k) or [""])[0]                       # noqa: E731
        if path == "/api/score/graph":
            src, params, ttl = "/api/graph", {"at": one("at"), "minutes": one("minutes") or "60",
                                              "theme": one("theme") or "dark"}, 30
        elif path == "/api/score/contrib":
            src, params, ttl = "/api/contrib", {"at": one("at")}, 30
        else:
            src, params, ttl = "/api/oht_map/report", {"day": one("day"), "name": one("name")}, 0
        params["sys"] = sysname
        try:
            st, ct, body, cd = gw_get(src, params, ttl=ttl, timeout=20)
        except OSError as e:
            return self._send(502, {"error": f"관제({gwanje_base()})에 닿지 않습니다 — {e}"})
        extra = {"Content-Disposition": cd} if cd else None
        return self._send(st, body, ct or "application/octet-stream", extra)

    # ── 정적 파일 — 월드모델파생/static (아이소메트리 3D 의 three.js 등) ──
    def _static(self, rel):
        rel = urllib.parse.unquote(rel)
        p = os.path.realpath(os.path.join(STATIC, rel))
        if not p.startswith(os.path.realpath(STATIC) + os.sep) or not os.path.isfile(p):
            return self._send(404, {"error": "없는 파일"})
        ctype = mimetypes.guess_type(p)[0] or "application/octet-stream"
        if p.endswith((".js", ".mjs")):
            ctype = "text/javascript"            # ★윈도는 .js 를 text/plain 으로 알려 주기도 한다 — 모듈이 안 뜬다
        with open(p, "rb") as f:
            data = f.read()
        self._new_sid = None
        return self._send(200, data, ctype + ("; charset=utf-8" if ctype.startswith("text/") else ""))


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    # ★윈도 콘솔 출력을 파일로 돌리면 cp949 라 못 찍는 글자에서 멈춘다 — 못 찍는 글자는 ? 로
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    cat = LE.catalog()
    print("=" * 64)
    print("  OHT 월드모델 - 실시간 (월드모델파생_실시간)")
    print(f"  http://localhost:{PORT}")
    print("=" * 64)
    print(f"  월드모델파생 폴더 : {LE.WM_DIR}")
    print(f"  지도             : " + " · ".join(f"{e['fab']}/{e['prefix']}→{e['table']}" for e in cat))
    print(f"  처음 지도        : {'/'.join(LE.default_fab())}")
    print(f"  조회             : {LE.POLL_SEC:g}초마다 · 처음 {LE.WARM_SEC}초치 · 화면은 {LE.BUFFER_SEC:g}초 늦춰 부드럽게")
    print(f"  로그프레소 키    : {LE.key_tail()}")
    print(f"  관제 (스코어)    : {gwanje_base()}  (GWANJE_URL 로 바꾼다)")
    print("=" * 64)
    if not cat:
        print("  [주의] 지도가 없습니다 - 월드모델파생/OHT_MAP (MAP/*.layout.zip 또는 cache/*.json) 을 확인하세요")
    srv = Server((HOST, PORT), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[실시간] 끝냅니다")


if __name__ == "__main__":
    main()
