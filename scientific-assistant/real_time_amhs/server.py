#!/usr/bin/env python3
"""
AMHS Sentinel_M16BR — 독립 관제 서버

데모스(demos_v1)와 완전 독립: 별도 프로세스, 별도 포트(기본 8989),
demos_v1 어떤 모듈도 import 하지 않는다.

실행:
    python server.py                 # 사내망 (로그프레소 실접속)
    LP_OFFLINE=1 python server.py    # 사외 (fixture 로 UI 확인)
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timedelta

from flask import Flask, jsonify, request, send_from_directory

from lp_client import load_config, parse_dt, ping
from lp_query import build, query
from report import build_report, feedback_status, save_feedback
from sentinel import CaseStore, alarm_floor, scan_once

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CFG = load_config()
STORE = CaseStore(CFG)

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "static"))

# 빈 구간 메움(backfill) 진행 상태
BACKFILL: dict = {"running": False, "day": None, "started": None, "result": None}

# 폴링 상태 (대시보드 헤더의 STREAMING · latency 표시용)
STATE = {
    "last_scan": None,
    "latency_ms": None,
    "connected": False,
    "error": None,
    "amos_warn": None,
    "scans": 0,
    "forecast": None,          # 선행 감지 결과 (forecast.predict)
}

# 선행 지표 분석 캐시 — 며칠치 CSV 를 훑어야 해서 매 요청 재계산하면 느리다
LEADING_CACHE: dict = {"at": 0.0, "data": None, "key": ""}


# ────────────────────────────── 폴링 루프 ──────────────────────────────
def _bootstrap_today() -> None:
    """기동 시 오늘 하루치를 통째로 확보한다 (00:00 ~ 현재).

    중간에 서버가 꺼져 있던 구간까지 메운다. 이미 저장된 분은 중복으로 걸러지므로
    여러 번 돌려도 안전하다. 이후 수집은 폴링 루프가 증분으로 이어간다.
    """
    now = datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day = now.strftime("%Y%m%d")
    print(f"[기동] 오늘({day}) 00:00 ~ {now:%H:%M} 하루치 확보 중…")
    t0 = time.time()
    try:
        from collect import collect
        r = collect(start.strftime("%Y%m%d%H%M%S"), now.strftime("%Y%m%d%H%M%S"),
                    CFG, verbose=False)
        if not r.get("ok"):
            print(f"[기동] ⚠️ 확보 실패 — {r.get('error')}")
            STATE["bootstrap"] = {"ok": False, "error": r.get("error")}
            return
        print(f"[기동] ✅ {r['rows']}행({r['minutes']}분) 조회 · 신규 {r['written']}행 저장 · "
              f"중복 {r['skipped']}"
              + (f" → {', '.join(r['files'])}" if r.get("files") else "")
              + f"  [{round(time.time()-t0,1)}초]")
        if r.get("warn"):
            print(f"[기동] ⚠️ {r['warn']}")
        STATE["bootstrap"] = {"ok": True, "minutes": r["minutes"],
                              "written": r["written"], "at": datetime.now().isoformat()}
    except Exception as e:
        print(f"[기동] ⚠️ 확보 예외: {type(e).__name__}: {e}")
        STATE["bootstrap"] = {"ok": False, "error": str(e)}


def _poll_loop() -> None:
    """수집 루프 — 주기·구간을 매 회 config 에서 다시 읽어 즉시 반영한다."""
    _bootstrap_today()                 # ① 하루치 먼저 확보
    while True:                        # ② 이후 증분 수집
        t0 = time.time()
        try:
            res = scan_once(STORE, cfg=CFG)
            STATE.update(
                last_scan=datetime.now().isoformat(),
                latency_ms=int((time.time() - t0) * 1000),
                connected=bool(res.get("ok")),
                error=None if res.get("ok") else res.get("error"),
                amos_warn=res.get("amos_warn"),
                scans=STATE["scans"] + 1,
                window=CFG.get("query", {}).get("window", "10m"),
                last_rows=res.pop("all_rows", None) or STATE.get("last_rows"),
                saved=res.get("saved"),
                gap_min=res.get("gap_min"),
            )
            sv = res.get("saved") or {}
            if STATE["scans"] == 1 or sv.get("written"):
                print(f"[수집] {res.get('gap_min')}분 구간 · {res.get('rows')}행 조회 · "
                      f"신규 {sv.get('written', 0)}행 저장"
                      + (f" → {sv['files'][0]}" if sv.get("files") else ""))
            if res.get("ok"):
                _auto_judge(res.get("cases") or [])
                _minute_llm(STATE.get("last_rows") or [])
                _update_forecast()
        except Exception as e:
            STATE.update(connected=False, error=f"{type(e).__name__}: {e}",
                         last_scan=datetime.now().isoformat())

        # 주기를 나눠 자며 변경을 빠르게 반영
        interval = max(5, int(CFG.get("query", {}).get("poll_interval_s", 60)))
        slept = 0
        while slept < interval:
            time.sleep(min(2, interval - slept))
            slept += 2
            if int(CFG.get("query", {}).get("poll_interval_s", 60)) != interval:
                break                       # 주기가 바뀌면 즉시 다음 수집으로


def _minute_llm(rows: list[dict]) -> None:
    """1분 추론 + 검증 창이 찬 과거 행 채점 — 수집 루프를 막지 않게 별도 스레드."""
    def work():
        try:
            from accuracy import run_minute, verify_day
            out = run_minute(rows, CFG)
            if out and out.get("오류"):
                print(f"[LLM/1분] ⚠️ {out['datetime']} — {out['오류']}")
            v = verify_day(datetime.now().strftime("%Y%m%d"), CFG)
            if v.get("scored"):
                print(f"[검증] {v['scored']}건 채점 (대기 {v['waiting']}건)")
        except Exception as e:
            print(f"[LLM/1분] ⚠️ 예외: {type(e).__name__}: {e}")

    threading.Thread(target=work, daemon=True).start()


_LEVEL_ORD = {"경계": 1, "위험": 2, "초위험": 3}


def _auto_judge(case_ids: list[str]) -> None:
    """실시간 감지 즉시 LLM 이 판단하게 한다 (신규·등급상향 케이스만)."""
    lc = CFG.get("llm", {})
    if not (lc.get("enabled", True) and lc.get("auto_judge", True)):
        return
    floor = _LEVEL_ORD.get(lc.get("auto_judge_min_level", "경계"), 1)

    for cid in case_ids:
        c = STORE.by_id(cid)
        if not c or not c.pop("_new", False):
            continue
        if _LEVEL_ORD.get(c.get("level"), 0) < floor:
            continue

        def work(case_id=cid):
            try:
                from llm_client import judge_case
                cc = STORE.by_id(case_id)
                if not cc:
                    return
                res, err = judge_case(cc, CFG)
                if err:
                    print(f"[LLM] ⚠️ {case_id} 자동 판단 실패: {err}")
                    return
                cc["llm"] = {**res, "at": datetime.now().isoformat(), "auto": True}
                STORE.save()
                print(f"[LLM] 🤖 {case_id} 자동 판단 완료 (확신도 {res.get('확신도')}%)")
            except Exception as e:
                print(f"[LLM] ⚠️ {case_id} 자동 판단 예외: {e}")

        threading.Thread(target=work, daemon=True).start()
    STORE.save()


def _update_forecast() -> None:
    """선행 감지 — 최근 추세로 '임계 돌파 N분 전' 을 미리 띄운다.

    수집 루프에서 매 회 부른다. 계산은 최근 20분 점수만 쓰는 가벼운 회귀라
    수집을 지연시키지 않는다. 실패해도 관제는 계속돼야 하므로 조용히 넘어간다.
    """
    try:
        from forecast import predict
        fc = predict(STATE.get("last_rows") or [], CFG)
        prev = STATE.get("forecast") or {}
        STATE["forecast"] = fc
        # 경보가 새로 뜬 순간만 콘솔에 한 줄 (매분 도배 방지)
        if fc.get("warn") and not prev.get("warn"):
            print(f"[선행] ⚠️ {fc['eta_min']}분 뒤 임계 돌파 예상 "
                  f"— 현재 {fc['current']}점, 분당 {fc['slope']:+.2f}점 "
                  f"(확신 {fc['confidence']}%)")
    except Exception as e:
        STATE["forecast"] = {"ok": False, "warn": False, "reason": f"{type(e).__name__}: {e}"}


# ─────────────────────── 추이 그래프 지표 목록 ───────────────────────
# 화면 위 '추이 그래프'에서 고를 수 있는 지표. config.ui.strip_metrics 로 갈아끼운다.
# 라벨·raw 컬럼명은 m16_hub_skills/발동이벤트_요약.py 와 동일하게 맞춘다.
#   key = 값이 들어있는 CSV 컬럼 / raw = 화면에 보여줄 AMOS 실제 컬럼명
_STRIP_DEFAULT = [
    {"key": "unified_risk_score", "raw": "unified_risk_score", "label": "스코어",
     "unit": "점", "color": "#3DDBE8", "max": 100, "bands": True},
    {"key": "M16HUB_ra", "raw": "M16HUB.QUE.TIME.AVGTOTALTIME1MIN",
     "label": "M16HUB 반송시간", "unit": "분", "color": "#FF6B5E"},
    {"key": "M16HUB_rd_fab", "raw": "M16HUB.STRATE.ALL.FABSTORAGERATIO",
     "label": "M16HUB FAB저장율", "unit": "%", "color": "#FFA53D", "max": 100},
    {"key": "M16HUB_stb_util", "raw": "M16HUB.STRATE.STB.3F_STORAGE_UTIL",
     "label": "M16HUB STB저장율", "unit": "%", "color": "#F2C94C", "max": 100},
    {"key": "M16HUB_rev_count", "raw": "M16HUB.QUE.LFT.3F_LFT_REVERSALCNT",
     "label": "M16HUB 리프터막힘", "unit": "회", "color": "#FF6FB5"},
]


def _clean_metrics(ms) -> list[dict]:
    out = []
    for m in ms or []:
        if isinstance(m, dict) and m.get("key"):
            out.append({"key": m["key"], "raw": m.get("raw") or m["key"],
                        "label": m.get("label") or m["key"],
                        "unit": m.get("unit") or "", "color": m.get("color") or "#3DDBE8",
                        "max": m.get("max"), "bands": bool(m.get("bands"))})
    return out


def metric_groups(cfg: dict) -> list[dict]:
    """지표 묶음 목록. config.ui.metric_groups → 없으면 ui.strip_metrics → 없으면 기본값."""
    ui = cfg.get("ui") or {}
    gs = ui.get("metric_groups")
    if isinstance(gs, list) and gs:
        out = []
        for i, g in enumerate(gs):
            if not isinstance(g, dict):
                continue
            ms = _clean_metrics(g.get("metrics"))
            if ms:
                out.append({"id": g.get("id") or f"g{i}", "name": g.get("name") or f"묶음{i+1}",
                            "desc": g.get("desc") or "", "metrics": ms})
        if out:
            return out
    ms = _clean_metrics(ui.get("strip_metrics")) or _STRIP_DEFAULT
    return [{"id": "amos", "name": "지표", "desc": "", "metrics": ms}]


def _num(v):
    try:
        s = str(v).strip()
        return float(s) if s not in ("", "-", "None", "nan", "NaN") else None
    except (TypeError, ValueError):
        return None


# ────────────────────────────── 화면 ──────────────────────────────
@app.route("/")
def index():
    # 오프닝/스플래시 없음 — 바로 관제 화면
    return send_from_directory(app.static_folder, "dashboard.html")


@app.route("/favicon.ico")
def favicon():
    return ("", 204)


# ────────────────────────────── 상태 ──────────────────────────────
@app.route("/api/status")
def api_status():
    return jsonify({
        "state": STATE,
        "alarm_floor": alarm_floor(CFG),
        "poll_interval_s": CFG.get("query", {}).get("poll_interval_s", 30),
        "offline": os.getenv("LP_OFFLINE") == "1",
        "table": CFG.get("table_name"),
        "base": CFG.get("logpresso_base"),
        "model": CFG.get("llm", {}).get("model"),
        "policy": CFG.get("policy", {}),
        "evaluation": CFG.get("evaluation", {}),
        "server_time": datetime.now().isoformat(),
    })


@app.route("/api/ping")
def api_ping():
    ok, msg = ping()
    return jsonify({"ok": ok, "message": msg, "base": CFG.get("logpresso_base")})


@app.route("/api/window", methods=["GET", "POST"])
def api_window():
    """실시간 수집 설정 조회/변경.

    · window          — 한 번에 가져올 데이터 구간 (1m ~ 60m)
    · poll_interval_s — 몇 초마다 가져올지 (수집 주기)
    둘은 별개다: '1분마다 최근 30분치' 같은 조합이 가능하다.
    """
    q = CFG.setdefault("query", {})
    wopts = q.get("window_options", ["1m", "5m", "10m", "20m", "30m", "40m", "50m", "60m"])
    popts = q.get("poll_options", [10, 30, 60, 300, 600])

    if request.method == "POST":
        b = request.get_json(silent=True) or {}
        if "window" in b:
            if b["window"] not in wopts:
                return jsonify({"error": f"window 는 {wopts} 중 하나여야 합니다"}), 400
            q["window"] = b["window"]
            print(f"[관제] 데이터 구간 → {b['window']}")
        if "poll_interval_s" in b:
            try:
                p = int(b["poll_interval_s"])
            except (TypeError, ValueError):
                return jsonify({"error": "poll_interval_s 는 정수(초)"}), 400
            if p not in popts:
                return jsonify({"error": f"poll_interval_s 는 {popts} 중 하나여야 합니다"}), 400
            q["poll_interval_s"] = p
            print(f"[관제] 수집 주기 → {p}초")
        STATE["settings_changed_at"] = datetime.now().isoformat()

    return jsonify({"window": q.get("window", "10m"), "window_options": wopts,
                    "poll_interval_s": q.get("poll_interval_s", 60), "poll_options": popts})


@app.route("/api/feed")
def api_feed():
    """수집한 전체 데이터 — 정상 포함 4등급으로 분류해서 내려준다.

    경계 이상은 케이스(case_id)와 연결되고, 정상은 데이터 행 그대로 보여준다.
    """
    from sentinel import _row_dt, _score, grade, hid_zones, summarize_reason

    # 오늘 쌓인 전체 데이터. 오늘이 아직 비었으면 가장 최근 날짜를 대신 보여준다.
    from store_csv import list_days, read_day
    asked = (request.args.get("day") or "").strip()   # 날짜를 콕 집어 물어본 경우
    day = asked or datetime.now().strftime("%Y%m%d")
    rows, shown_day, fallback = [], day, False
    try:
        rows = read_day(day, CFG)
        if not rows and not asked:
            for d in list_days(CFG):                 # 최신순
                r2 = read_day(d["day"], CFG)
                if r2:
                    rows, shown_day, fallback = r2, d["day"], True
                    break
    except Exception as e:
        print(f"[FEED] ⚠️ 읽기 실패: {e}")
    # 폴링 버퍼 폴백은 '오늘' 요청일 때만. 과거 날짜를 물었는데 없으면 없는 것이다
    # (안 그러면 7/25 를 물었는데 오늘 버퍼가 나와서 날짜가 뒤바뀐다)
    if not rows and not asked:
        rows = STATE.get("last_rows") or []

    # 추이 그래프에서 고를 수 있는 지표 묶음 — 값을 같이 실어보낸다
    groups = metric_groups(CFG)
    mkeys = sorted({m["key"] for g in groups for m in g["metrics"]})
    seen_keys = set()

    out = []
    for r in rows:
        dt, sc = _row_dt(r), _score(r)
        if dt is None:
            continue
        g = grade(sc, CFG)
        area = (r.get("hot_area") or "").strip() or "UNKNOWN"
        bd = (r.get("BOTTLENECK_downward_anomaly_cols") or "").strip()
        bu = (r.get("BOTTLENECK_upward_anomaly_cols") or "").strip()
        qd = (r.get("QUEUE_downward_anomaly_cols") or "").strip()
        qu = (r.get("QUEUE_upward_anomaly_cols") or "").strip()
        bott = " ".join(x for x in (bd, bu) if x)
        items = " ".join(x for x in (qd, qu) if x).split()
        # 이 시각이 속한 케이스 찾기
        cid = None
        for c in STORE.cases:
            if c["area"] == area and c["opened_at"] <= dt.isoformat() <= (
                    c.get("last_seen") or c["opened_at"]):
                cid = c["id"]
                break
        raw_reason = (r.get("reason") or "").strip()
        m = {}
        for k in mkeys:
            v = _num(r.get(k))
            if v is not None:
                m[k] = v
                seen_keys.add(k)
        out.append({
            "m": m,
            "at": dt.isoformat(),
            "datetime": (r.get("datetime") or dt.strftime("%Y-%m-%d %H:%M")).strip(),
            "time": dt.strftime("%H:%M"), "area": area,
            "score": sc, "level": g["level"], "emoji": g["emoji"], "severity": g["severity"],
            "reason": summarize_reason(raw_reason, area) or raw_reason,
            "reason_raw": raw_reason,
            "zones": hid_zones(bott), "items": items,
            # AMOS 4개 컬럼을 나눠서 그대로 (UI 표시용)
            "bott_down": hid_zones(bd), "bott_up": hid_zones(bu),
            "queue_down": qd.split(), "queue_up": qu.split(),
            "chain": (r.get("propagation_chain") or "").strip(),
            "case_id": cid,
        })

    out.sort(key=lambda x: x["at"], reverse=True)
    counts = {lv: sum(1 for x in out if x["level"] == lv)
              for lv in ("정상", "경계", "위험", "초위험")}
    # 기본은 하루치 전부 (1분 1행 = 1440행). 00:00 부터 다 보여야 한다.
    try:
        limit = max(1, min(5000, int(request.args.get("limit", 1500))))
    except ValueError:
        limit = 1500
    return jsonify({"rows": out[:limit], "counts": counts, "total": len(out),
                    "shown": min(limit, len(out)),
                    # 실제로 값이 있는 지표만 선택지로 준다 (CSV 에 없는 컬럼은 뺀다)
                    "groups": [dict(g, metrics=[m for m in g["metrics"] if m["key"] in seen_keys])
                               for g in groups
                               if any(m["key"] in seen_keys for m in g["metrics"])],
                    "day": shown_day, "fallback": fallback,
                    "latest": out[0]["datetime"] if out else None,
                    "earliest": out[-1]["datetime"] if out else None,
                    "window": CFG.get("query", {}).get("window", "10m")})


@app.route("/api/collect", methods=["POST"])
def api_collect():
    """수동 확보 — 오늘 하루 다시 훑거나(기본), 지정 날짜를 확보한다.

    {"date": "YYYYMMDD"} 또는 {} (오늘 00:00~현재)
    """
    b = request.get_json(silent=True) or {}
    try:
        from collect import collect, collect_day
        if b.get("date"):
            r = collect_day(b["date"], CFG)
        else:
            now = datetime.now()
            r = collect(now.strftime("%Y%m%d000000"), now.strftime("%Y%m%d%H%M%S"),
                        CFG, verbose=False)
        return (jsonify(r), 200) if r.get("ok") else (jsonify(r), 502)
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500


@app.route("/api/graph")
def api_graph():
    """구간 그래프 SVG — 목록에서 더블클릭한 시각 기준 1시간.

    /api/graph?at=2026-07-28T08:11:00&minutes=60
    """
    from graphs import render
    from store_csv import read_day

    at = parse_dt(request.args.get("at")) or datetime.now()
    try:
        minutes = max(5, min(1440, int(request.args.get("minutes", 60))))
    except ValueError:
        minutes = 60

    rows = []
    for d in {(at - timedelta(minutes=minutes)).strftime("%Y%m%d"),
              at.strftime("%Y%m%d"), (at + timedelta(minutes=minutes)).strftime("%Y%m%d")}:
        rows.extend(read_day(d, CFG))
    if not rows:
        rows = STATE.get("last_rows") or []

    svg = render(rows, at, minutes, cfg=CFG)
    return app.response_class(svg, mimetype="image/svg+xml")


@app.route("/api/accuracy")
def api_accuracy():
    """1분 LLM 판단 + 사후검증 결과. ?day=YYYYMMDD (기본 오늘), ?rows=1 이면 행까지."""
    from accuracy import acc_cfg, summary, verify_day
    from store_csv import read_llm_day
    day = (request.args.get("day") or "").strip() or datetime.now().strftime("%Y%m%d")
    # 그 날짜를 열 때 채점을 한 번 돌린다 (과거 날짜도 판정이 채워지게)
    try:
        verify_day(day, CFG)
    except Exception as e:
        print(f"[검증] ⚠️ {day} 채점 실패: {e}")
    out = summary(day, CFG)
    out["backfill"] = dict(BACKFILL)
    try:
        from accuracy import backlog
        out["backlog"] = backlog(STATE.get("last_rows") or [], CFG)
    except Exception:
        out["backlog"] = None
    if request.args.get("rows"):
        rows = read_llm_day(day, CFG)
        rows.sort(key=lambda r: r.get("datetime") or "", reverse=True)
        try:
            lim = max(1, min(2000, int(request.args.get("rows", 300))))
        except ValueError:
            lim = 300
        rows = rows[:lim]
        # 아직 판정이 안 된 행에 '몇 분 뒤에 채점되는지' 를 붙여준다
        win = acc_cfg(CFG)["window_min"]
        now = datetime.now()
        for r in rows:
            if not (r.get("판정") or "").strip() and (r.get("실제이상") or "").strip():
                t0 = parse_dt(r.get("datetime"))
                if t0:
                    left = (t0 + timedelta(minutes=win) - now).total_seconds() / 60
                    r["대기분"] = max(0, int(left + 0.999))
        out["rows_data"] = rows
    return jsonify(out)


@app.route("/api/accuracy/backfill", methods=["POST"])
def api_accuracy_backfill():
    """그 날 아직 판단 안 한 분을 LLM 으로 메운다. {date, limit?}

    폴링은 최근 구간만 본다. 서버를 늦게 켰거나 꺼져 있던 구간은 이걸로 채운다.
    """
    b = request.get_json(silent=True) or {}
    day = "".join(ch for ch in str(b.get("date") or "") if ch.isdigit())[:8] \
        or datetime.now().strftime("%Y%m%d")
    try:
        limit = max(0, min(1500, int(b.get("limit", 0) or 0)))
    except (TypeError, ValueError):
        limit = 0

    if BACKFILL.get("running"):
        return jsonify({"ok": False, "error": "이미 메우는 중입니다", "state": BACKFILL}), 409

    def work():
        BACKFILL.update(running=True, day=day, started=datetime.now().isoformat(), result=None)
        try:
            from accuracy import backfill_day
            BACKFILL["result"] = backfill_day(day, CFG, limit)
        except Exception as e:
            BACKFILL["result"] = {"error": f"{type(e).__name__}: {e}"}
        finally:
            BACKFILL["running"] = False

    threading.Thread(target=work, daemon=True).start()
    return jsonify({"ok": True, "started": True, "day": day, "limit": limit})


@app.route("/api/accuracy/backfill")
def api_accuracy_backfill_state():
    return jsonify(BACKFILL)


@app.route("/api/accuracy/verdict", methods=["POST"])
def api_accuracy_verdict():
    """운영자가 직접 누른 판정 — 자동 판정을 덮어쓴다. {datetime, verdict:정탐|오탐}"""
    from accuracy import set_human
    b = request.get_json(silent=True) or {}
    dt = (b.get("datetime") or "").strip()
    v = (b.get("verdict") or "").strip()
    if not dt or v not in ("정탐", "오탐"):
        return jsonify({"ok": False, "error": "datetime 과 verdict(정탐|오탐) 필요"}), 400
    day = "".join(ch for ch in dt if ch.isdigit())[:8]
    ok = set_human(day, dt, v, CFG)
    return jsonify({"ok": ok})


@app.route("/api/data/days")
def api_data_days():
    """누적 저장된 날짜 CSV 목록 (20260727_TOTAL.CSV ...)."""
    from store_csv import data_dir, list_days
    return jsonify({"dir": data_dir(CFG), "days": list_days(CFG)})


@app.route("/api/data/<day>.csv")
def api_data_csv(day):
    """저장된 날짜 CSV 원본 다운로드 — 직접 열어볼 수 있게.

    /api/data/20260729.csv      → 20260729_TOTAL.CSV (데이터)
    /api/data/20260729_LLM.csv  → 20260729_LLM.CSV   (1분 LLM 판단·판정)
    """
    from store_csv import day_path, llm_path
    d = "".join(ch for ch in day if ch.isdigit())[:8]
    want_llm = "LLM" in day.upper()
    p = llm_path(d, CFG) if want_llm else day_path(d, CFG)
    if not os.path.isfile(p):
        return jsonify({"error": f"{os.path.basename(p)} 없음"}), 404
    return send_from_directory(os.path.dirname(p), os.path.basename(p),
                               as_attachment=True)


def _recur_1h(ref: datetime) -> dict:
    """재발률 — '50점(임계) 이상이 가라앉았다가 다시 올라왔나' 를 분단위 점수로 센다.

    최근 60분 점수를 보고 임계 이상 구간(런)을 끊는다. 임계 미만으로 내려간 뒤
    다시 올라오면 그게 재발이다.
        런 1개  → 재발 0회 → 0%
        런 3개  → 재발 2회 → 67%   (2/3)
    분모는 런 수, 분자는 재발 횟수(런 수 - 1). 최근 60분에 임계 이상이 아예
    없으면 rate 는 None (0% 로 굳어 보이지 않게).
    """
    from sentinel import _row_dt, _score
    floor = alarm_floor(CFG)
    rows = STATE.get("last_rows") or []
    try:                                      # 폴링 구간이 60분보다 짧으면 저장분으로 보충
        from store_csv import read_day
        saved = read_day(ref.strftime("%Y%m%d"), CFG)
        if saved:
            seen_dt = {(r.get("datetime") or "") for r in rows}
            rows = list(rows) + [r for r in saved
                                 if (r.get("datetime") or "") not in seen_dt]
    except Exception:
        pass

    win = []
    for r in rows:
        d = _row_dt(r)
        if d and 0 <= (ref - d).total_seconds() / 60 <= 60:
            win.append((d, _score(r)))
    win.sort(key=lambda x: x[0])

    runs, over, minutes = 0, False, 0
    for _, s in win:
        if s >= floor:
            minutes += 1
            if not over:
                runs += 1                     # 임계 아래에서 위로 올라온 순간 = 런 시작
            over = True
        else:
            over = False
    recur = max(0, runs - 1)
    return {"rate": round(100 * recur / runs, 1) if runs else None,
            "runs": runs, "recur": recur, "minutes": minutes, "floor": floor}


# ── 🧪 4-LLM 병렬 분석 (분석 탭) ──
# 실행은 스레드 1개만 — 4-LLM 호출이 겹치면 게이트웨이에 부담이라 동시 1건 제한.
ANALYSIS: dict = {"running": False, "progress": {}, "last_id": None}


@app.route("/api/analysis/run", methods=["POST"])
def api_analysis_run():
    """4-LLM 병렬 분석 시작 — 백그라운드. body: {day, start?, end?} (HH:MM)."""
    if ANALYSIS["running"]:
        return jsonify({"error": "이미 분석이 돌고 있습니다 — 끝나면 다시 시도"}), 409
    body = request.get_json(silent=True) or {}
    day = "".join(ch for ch in str(body.get("day") or "") if ch.isdigit())[:8]
    if len(day) != 8:
        return jsonify({"error": "day(YYYYMMDD) 필요"}), 400
    start = str(body.get("start") or "")[:5]
    end = str(body.get("end") or "")[:5]

    ANALYSIS.update(running=True, progress={"stage": "start", "done": False},
                    day=day, span=f"{start or '00:00'}~{end or '24:00'}")

    def work():
        try:
            from analysis import run_analysis
            r = run_analysis(day, CFG, start, end, progress=ANALYSIS["progress"])
            ANALYSIS["last_id"] = r.get("id")
            if not r.get("ok"):
                ANALYSIS["progress"].update(done=True, error=r.get("error"))
        except Exception as e:
            ANALYSIS["progress"].update(done=True, error=f"{type(e).__name__}: {e}")
        finally:
            ANALYSIS["running"] = False

    threading.Thread(target=work, daemon=True).start()
    return jsonify({"ok": True, "started": True})


@app.route("/api/analysis/status")
def api_analysis_status():
    return jsonify({"running": ANALYSIS["running"], "progress": ANALYSIS["progress"],
                    "last_id": ANALYSIS["last_id"],
                    "day": ANALYSIS.get("day"), "span": ANALYSIS.get("span")})


@app.route("/api/analysis/models")
def api_analysis_models():
    """게이트웨이가 이 키에 허용한 모델 목록 (/v1/models).

    모델 이름이 바뀌면 400/403 으로 단계가 통째로 죽는다. 화면에서 바로
    확인할 수 있어야 config 를 고칠 수 있다.
    """
    import urllib.error
    import urllib.request
    lc = CFG.get("llm", {}) or {}
    base = str(lc.get("url", "")).split("/chat/completions")[0]
    if not base:
        return jsonify({"error": "llm.url 없음"}), 400
    headers = {}
    try:
        from llm_client import _api_key
        key = _api_key(CFG)
        if key:
            headers["Authorization"] = f"Bearer {key}"
    except Exception:
        pass
    try:
        req = urllib.request.Request(base + "/models", headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return jsonify({"error": f"HTTP {e.code}",
                        "detail": e.read()[:400].decode("utf-8", "replace")}), 502
    except Exception as e:
        return jsonify({"error": f"{type(e).__name__}: {e}"}), 502
    ids = [m.get("id") for m in (data.get("data") or []) if m.get("id")]
    used = {sid: (((lc.get("analysis") or {}).get("roles") or {}).get(sid) or {}).get("model")
            for sid in ("p1", "p2", "p3", "final")}
    return jsonify({"models": ids, "gaia": [m for m in ids if str(m).lower().startswith("gaia")],
                    "used": used,
                    "missing": [f"{k}={v}" for k, v in used.items() if v and v not in ids]})


@app.route("/api/analysis/list")
def api_analysis_list():
    try:
        from analysis import list_analyses
        return jsonify({"items": list_analyses(CFG)})
    except Exception as e:
        return jsonify({"items": [], "error": f"{type(e).__name__}: {e}"})


@app.route("/api/analysis/<aid>")
def api_analysis_get(aid):
    from analysis import get_analysis
    r = get_analysis(aid, CFG)
    if not r:
        return jsonify({"error": "없는 분석"}), 404
    return jsonify(r)


@app.route("/api/forecast")
def api_forecast():
    """선행 감지 — 지금 추세로 본 임계 돌파 예보.

    수집 루프가 매 회 계산해 STATE 에 넣어 둔 것을 그대로 준다(요청마다 재계산
    안 함). 아직 한 번도 안 돌았으면 그 자리에서 한 번 계산한다.
    """
    fc = STATE.get("forecast")
    if fc is None:
        _update_forecast()
        fc = STATE.get("forecast")
    return jsonify(fc or {"ok": False, "warn": False, "reason": "아직 수집 전"})


@app.route("/api/forecast/leading")
def api_forecast_leading():
    """선행 지표 — 과거 사건에서 어느 지표가 몇 분 먼저 움직였나.

    저장된 날짜 CSV 를 훑으므로 60초 캐시. days= 로 날짜를 직접 줄 수 있다.
    """
    import time as _t
    days = [d for d in (request.args.get("days", "") or "").split(",") if d.strip()]
    look = max(10, min(int(request.args.get("lookback", 60) or 60), 240))
    key = f"{','.join(days)}|{look}"
    now = _t.time()
    if (LEADING_CACHE["data"] and LEADING_CACHE["key"] == key
            and now - LEADING_CACHE["at"] < 60):
        return jsonify({**LEADING_CACHE["data"], "cached": True})
    try:
        from forecast import leading
        data = leading(days or None, CFG, lookback_min=look)
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500
    LEADING_CACHE.update(at=now, data=data, key=key)
    return jsonify({**data, "cached": False})


@app.route("/api/kpi")
def api_kpi():
    """상단 지표 — 실제 계산 가능한 값만. 근거 없는 수치는 null 로 둔다."""
    act = STORE.active()

    def _dt(s):
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None

    # ★기준 시각 = '데이터의 최신 시각'. 벽시계로 재면 로그프레소가 몇 분 밀리거나
    #   과거 날짜를 재생할 때 모든 케이스가 '1시간 밖' 이 돼 재발률이 늘 0% 로 굳는다.
    seen = [d for d in (_dt(c.get("last_seen") or c.get("opened_at"))
                        for c in STORE.cases) if d]
    ref = max(seen) if seen else datetime.now()

    def age_min(c, field="opened_at"):
        d = _dt(c.get(field) or c.get("opened_at"))
        return (ref - d).total_seconds() / 60 if d else 0

    unack = [c for c in act if not c.get("acked_at")]
    new30 = [c for c in act if age_min(c) <= 30]

    rc = _recur_1h(ref)

    # LLM 판단 일치 — 1분 추론의 사후검증 결과 (★정탐률이 아니다)
    try:
        from accuracy import summary as acc_summary
        acc = acc_summary(None, CFG)
    except Exception as e:
        acc = {"error": f"{type(e).__name__}: {e}"}

    return jsonify({
        "active": len(act),
        "active_new_30m": len(new30),
        "unack": len(unack),
        "unack_over_5m": len([c for c in unack if age_min(c) >= 5]),
        "detect_latency_ms": STATE.get("latency_ms"),
        "recur_rate_1h": rc["rate"],
        "recur_base": rc["runs"],
        "recur_events": rc["recur"],
        "recur_minutes": rc["minutes"],
        "recur_floor": rc["floor"],
        "recur_ref": ref.isoformat(),
        "llm_match": acc,
        "by_level": {lv: len([c for c in act if c["level"] == lv])
                     for lv in ("경계", "위험", "초위험")},
        "alarm_floor": alarm_floor(CFG),
    })


# ────────────────────────────── 케이스 ──────────────────────────────
@app.route("/api/cases")
def api_cases():
    if request.args.get("all") == "1":
        return jsonify({"cases": STORE.cases})
    return jsonify({"cases": STORE.active()})


@app.route("/api/cases/<cid>")
def api_case(cid):
    c = STORE.by_id(cid)
    return (jsonify(c), 200) if c else (jsonify({"error": "없는 케이스"}), 404)


@app.route("/api/cases/<cid>/<action>", methods=["POST"])
def api_case_action(cid, action):
    """확인 처리 / 이상 없음(재확인 예약만 갱신) / 종결."""
    body = request.get_json(silent=True) or {}
    who, note = body.get("who", "운영자"), body.get("note", "")
    fn = {"ack": STORE.ack, "normal": STORE.mark_normal, "close": STORE.close}.get(action)
    if not fn:
        return jsonify({"error": "ack | normal | close 만 가능"}), 400
    c = fn(cid, who, note)
    if c is None:
        return jsonify({"error": "없는 케이스"}), 404
    if isinstance(c, dict) and c.get("error"):
        return jsonify(c), 409
    return jsonify(c)


@app.route("/api/cases/<cid>/judge", methods=["POST"])
def api_case_judge(cid):
    """LLM 판단 (스킬 4종 기반)."""
    c = STORE.by_id(cid)
    if not c:
        return jsonify({"error": "없는 케이스"}), 404
    try:
        from llm_client import judge_case
        res, err = judge_case(c, CFG)
    except Exception as e:
        res, err = None, f"{type(e).__name__}: {e}"
    if err:
        return jsonify({"error": err}), 502
    c["llm"] = {**res, "at": datetime.now().isoformat()}
    STORE.save()
    return jsonify(c["llm"])


@app.route("/api/scan", methods=["POST"])
def api_scan():
    return jsonify(scan_once(STORE, cfg=CFG))


# ────────────────────────────── 리포트 ──────────────────────────────
def _parse_dt(s: str | None, default: datetime) -> datetime:
    if not s:
        return default
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return default


@app.route("/api/report", methods=["POST"])
def api_report():
    """구간 지정 → 평가 실행."""
    """구간 리포트 — 기본은 로그프레소를 날짜로 직접 조회(관제와 분리).

    {"date": "2026-07-27"}                      → 그 날 하루 전체
    {"start": "...", "end": "..."}              → 지정 구간
    {"source": "store"}                         → 실시간 케이스 저장소 기준
    """
    b = request.get_json(silent=True) or {}
    if b.get("date"):
        try:
            d = datetime.strptime(b["date"][:10], "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "date 형식은 YYYY-MM-DD"}), 400
        # ★ 날짜 지정 = 하루 사건 리포트 (데모스 개인 에이전트 '사건발생 보고서' 와 같은 5섹션)
        if b.get("kind", "day") == "day":
            from report import build_day_report
            return jsonify(build_day_report(d.strftime("%Y%m%d"), CFG,
                                            use_llm=b.get("use_llm", True)))
        start, end = d, d.replace(hour=23, minute=59, second=59)
    else:
        end = _parse_dt(b.get("end"), datetime.now())
        start = _parse_dt(b.get("start"), end - timedelta(minutes=30))

    rep = build_report(STORE, start, end, CFG,
                       use_llm=b.get("use_llm", True),
                       source=b.get("source", "query"))
    return jsonify(rep)


@app.route("/api/report/day.html")
def api_report_day_html():
    """하루 사건 리포트를 데모스 개인 에이전트와 같은 인터랙티브 HTML 로.

    /api/report/day.html?date=20260728  (없으면 오늘)
    체크박스 표·시간 시분 분리·O/X 판정·수동 기입·저장 툴바가 들어간다.
    """
    from report import build_day_report, day_report_html, load_day_report
    d = "".join(ch for ch in (request.args.get("date") or "") if ch.isdigit())[:8] \
        or datetime.now().strftime("%Y%m%d")
    use_llm = request.args.get("llm", "1") != "0"
    # 이미 생성해 둔 보고서가 있으면 그대로 연다 (다시 뽑으면 LLM 문장이 달라지므로)
    rep = (None if request.args.get("fresh") == "1" else load_day_report(d, CFG)) \
        or build_day_report(d, CFG, use_llm=use_llm)
    html = day_report_html(rep, CFG)
    resp = app.response_class(html, mimetype="text/html; charset=utf-8")
    if request.args.get("download") == "1":
        # ★파일명에 한글을 쓰려면 RFC 5987 인코딩 — HTTP 헤더는 latin-1 만 담긴다
        from urllib.parse import quote as _q
        name = f"M16BR_사건발생보고서_{d}.html"
        resp.headers["Content-Disposition"] = (
            f'attachment; filename="M16BR_report_{d}.html"; '
            f"filename*=UTF-8''{_q(name)}")
    return resp


@app.route("/api/reports")
def api_reports():
    d = os.path.join(BASE_DIR, CFG.get("storage", {}).get("reports", "data/reports"))
    if not os.path.isdir(d):
        return jsonify({"reports": []})
    out = []
    for fn in sorted(os.listdir(d), reverse=True)[:30]:
        if fn.endswith(".json"):
            try:
                with open(os.path.join(d, fn), "r", encoding="utf-8") as f:
                    r = json.load(f)
                s = r.get("summary") or {}
                out.append({"id": r["id"], "generated_at": r["generated_at"],
                            "kind": r.get("kind", "span"), "day": s.get("day", ""),
                            "span": s.get("span", ""), "count": s.get("count", 0)})
            except Exception:
                continue
    out.sort(key=lambda r: r.get("generated_at", ""), reverse=True)
    return jsonify({"reports": out})


@app.route("/api/reports/<rid>")
def api_report_get(rid):
    p = os.path.join(BASE_DIR, CFG.get("storage", {}).get("reports", "data/reports"), rid + ".json")
    if not os.path.isfile(p):
        return jsonify({"error": "없는 리포트"}), 404
    with open(p, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


# ────────────────────────────── 피드백 ──────────────────────────────
@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    b = request.get_json(silent=True) or {}
    res = save_feedback(b.get("report_id", ""), b.get("verdict", ""),
                        b.get("missed", ""), b.get("comment", ""),
                        b.get("who", "운영자"), CFG)
    return (jsonify(res), 400) if res.get("error") else jsonify(res)


@app.route("/api/feedback/status")
def api_feedback_status():
    return jsonify(feedback_status(CFG))


# ────────────────────────────── 로그프레소 조회 ──────────────────────────────
@app.route("/api/query", methods=["POST"])
def api_query():
    """대시보드에서 직접 LPQL 조회 (읽기 전용 — lp_client 가 강제)."""
    b = request.get_json(silent=True) or {}
    lpql = (b.get("lpql") or "").strip()
    if not lpql:
        lpql = build(b.get("table"), duration=b.get("duration"),
                     from_dt=b.get("from"), to_dt=b.get("to"),
                     search=b.get("search"), limit=b.get("limit") or 100)
    rows, err = query(lpql)
    if err:
        return jsonify({"error": err.get("reason"), "lpql": lpql,
                        "preview": err.get("response_preview")}), 502
    return jsonify({"lpql": lpql, "count": len(rows), "rows": rows[: int(b.get("limit") or 100)]})


def _open_browser(url: str, delay: float = 1.2) -> None:
    """서버가 뜬 직후 대시보드를 브라우저로 자동 실행."""
    def go():
        time.sleep(delay)
        try:
            import webbrowser
            if webbrowser.open(url):
                print(f"  🌐 브라우저 실행: {url}")
                return
        except Exception:
            pass
        # 브라우저가 없는 환경(서버/원격) — 주소만 안내
        print(f"  ℹ️ 브라우저 자동 실행 실패 — 직접 여세요: {url}")
    threading.Thread(target=go, daemon=True).start()


def _lan_ips() -> list[str]:
    """이 PC 의 사내망 IP 목록 (외부에서 접속할 주소 안내용)."""
    import socket
    ips = set()
    try:
        # 기본 경로로 나가는 인터페이스의 IP (실제로 밖에서 보이는 주소)
        sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sk.connect(("8.8.8.8", 80))
            ips.add(sk.getsockname()[0])
        finally:
            sk.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


if __name__ == "__main__":
    s = CFG.get("server", {})
    threading.Thread(target=_poll_loop, daemon=True).start()
    print("=" * 62)
    print("  AMHS Sentinel_M16BR — 독립 LLM 관제 시스템 (데모스 비의존)")
    print(f"  로그프레소 : {CFG.get('logpresso_base')}  table={CFG.get('table_name')}")
    print(f"  AMOS      : {CFG['amos']['bottleneck']['table']} + {CFG['amos']['queue']['table']}")
    print(f"  모델       : {CFG.get('llm', {}).get('model')}")
    print(f"  폴링       : {CFG.get('query', {}).get('poll_interval_s')}초"
          + ("   [OFFLINE fixture 모드]" if os.getenv("LP_OFFLINE") == "1" else ""))
    host = s.get("host", "0.0.0.0")
    port = s.get("port", 8989)
    url = f"http://localhost:{port}/"
    print(f"  대시보드   : {url}")
    if host in ("0.0.0.0", "::"):
        # 외부(사내망)에서 접속할 주소를 그대로 알려준다 — 그냥 나눠주면 된다
        for ip in _lan_ips():
            print(f"             : http://{ip}:{port}/   ← 외부 접속용")
        print(f"  ℹ️ 외부에서 안 열리면 방화벽에서 TCP {port} 인바운드를 열어야 합니다")
    else:
        print(f"  ⚠️ host={host} — 이 PC 에서만 열립니다. 외부 공개는 config.server.host=0.0.0.0")
    print("=" * 62)

    # 실행하면 대시보드가 바로 뜨게 (config.server.auto_open=false 로 끌 수 있음)
    if s.get("auto_open", True) and os.getenv("NO_BROWSER") != "1":
        _open_browser(url)

    app.run(host=s.get("host", "0.0.0.0"), port=port, threaded=True, debug=False)
