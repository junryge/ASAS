#!/usr/bin/env python3
"""
AMHS Sentinel — 독립 관제 서버

데모스(demos_v1)와 완전 독립: 별도 프로세스, 별도 포트(기본 8700),
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

from lp_client import load_config, ping
from lp_query import build, query
from report import build_report, feedback_status, save_feedback
from sentinel import CaseStore, alarm_floor, scan_once

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CFG = load_config()
STORE = CaseStore(CFG)

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "static"))

# 폴링 상태 (대시보드 헤더의 STREAMING · latency 표시용)
STATE = {
    "last_scan": None,
    "latency_ms": None,
    "connected": False,
    "error": None,
    "amos_warn": None,
    "scans": 0,
}


# ────────────────────────────── 폴링 루프 ──────────────────────────────
def _poll_loop() -> None:
    interval = CFG.get("query", {}).get("poll_interval_s", 30)
    while True:
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
            )
        except Exception as e:
            STATE.update(connected=False, error=f"{type(e).__name__}: {e}",
                         last_scan=datetime.now().isoformat())
        time.sleep(interval)


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


@app.route("/api/kpi")
def api_kpi():
    """상단 지표 — 실제 계산 가능한 값만. 근거 없는 수치는 null 로 둔다."""
    now = datetime.now()
    act = STORE.active()

    def age_min(c):
        try:
            return (now - datetime.fromisoformat(c["opened_at"])).total_seconds() / 60
        except Exception:
            return 0

    unack = [c for c in act if not c.get("acked_at")]
    new30 = [c for c in act if age_min(c) <= 30]

    # 재발률 — 최근 1시간 케이스 중 억제 창 재발(재발/자동종결 후 재개)이 있던 비율
    recent = [c for c in STORE.cases if age_min(c) <= 60]
    reopened = [c for c in recent
                if any(t["kind"] == "재발" for t in c.get("timeline", []))]

    # LLM 정탐률 — 리포트 피드백이 있을 때만
    fb = feedback_status(CFG)
    judged = sum(fb["counts"].get(v, 0) for v in ("정확", "보통", "과다탐지", "누락"))
    acc = round(100 * fb["counts"].get("정확", 0) / judged, 1) if judged else None

    return jsonify({
        "active": len(act),
        "active_new_30m": len(new30),
        "unack": len(unack),
        "unack_over_5m": len([c for c in unack if age_min(c) >= 5]),
        "detect_latency_ms": STATE.get("latency_ms"),
        "recur_rate_1h": round(100 * len(reopened) / len(recent), 1) if recent else 0,
        "recur_base": len(recent),
        "llm_accuracy": acc,
        "llm_sample": judged,
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
    b = request.get_json(silent=True) or {}
    end = _parse_dt(b.get("end"), datetime.now())
    start = _parse_dt(b.get("start"), end - timedelta(minutes=30))
    rep = build_report(STORE, start, end, CFG, use_llm=b.get("use_llm", True))
    return jsonify(rep)


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
                out.append({"id": r["id"], "generated_at": r["generated_at"],
                            "span": r["summary"]["span"], "count": r["summary"]["count"]})
            except Exception:
                continue
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


if __name__ == "__main__":
    s = CFG.get("server", {})
    threading.Thread(target=_poll_loop, daemon=True).start()
    print("=" * 62)
    print("  AMHS Sentinel — 독립 LLM 관제 시스템 (데모스 비의존)")
    print(f"  로그프레소 : {CFG.get('logpresso_base')}  table={CFG.get('table_name')}")
    print(f"  AMOS      : {CFG['amos']['bottleneck']['table']} + {CFG['amos']['queue']['table']}")
    print(f"  모델       : {CFG.get('llm', {}).get('model')}")
    print(f"  폴링       : {CFG.get('query', {}).get('poll_interval_s')}초"
          + ("   [OFFLINE fixture 모드]" if os.getenv("LP_OFFLINE") == "1" else ""))
    port = s.get("port", 8700)
    url = f"http://localhost:{port}/"
    print(f"  대시보드   : {url}")
    print("=" * 62)

    # 실행하면 대시보드가 바로 뜨게 (config.server.auto_open=false 로 끌 수 있음)
    if s.get("auto_open", True) and os.getenv("NO_BROWSER") != "1":
        _open_browser(url)

    app.run(host=s.get("host", "0.0.0.0"), port=port, threaded=True, debug=False)
