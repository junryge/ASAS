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
    day = (request.args.get("day") or "").strip() or datetime.now().strftime("%Y%m%d")
    rows, shown_day, fallback = [], day, False
    try:
        rows = read_day(day, CFG)
        if not rows and not request.args.get("day"):
            for d in list_days(CFG):                 # 최신순
                r2 = read_day(d["day"], CFG)
                if r2:
                    rows, shown_day, fallback = r2, d["day"], True
                    break
    except Exception as e:
        print(f"[FEED] ⚠️ 읽기 실패: {e}")
    if not rows:
        rows = STATE.get("last_rows") or []
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
        out.append({
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
    try:
        limit = max(1, min(2000, int(request.args.get("limit", 400))))
    except ValueError:
        limit = 400
    return jsonify({"rows": out[:limit], "counts": counts, "total": len(out),
                    "shown": min(limit, len(out)),
                    "day": shown_day, "fallback": fallback,
                    "latest": out[0]["datetime"] if out else None,
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


@app.route("/api/data/days")
def api_data_days():
    """누적 저장된 날짜 CSV 목록 (20260727_TOTAL.CSV ...)."""
    from store_csv import data_dir, list_days
    return jsonify({"dir": data_dir(CFG), "days": list_days(CFG)})


@app.route("/api/data/<day>.csv")
def api_data_csv(day):
    """저장된 날짜 CSV 원본 다운로드 — 직접 열어볼 수 있게."""
    from store_csv import day_path
    d = "".join(ch for ch in day if ch.isdigit())[:8]
    p = day_path(d, CFG)
    if not os.path.isfile(p):
        return jsonify({"error": f"{d}_TOTAL.CSV 없음"}), 404
    return send_from_directory(os.path.dirname(p), os.path.basename(p),
                               as_attachment=True)


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
        start, end = d, d.replace(hour=23, minute=59, second=59)
    else:
        end = _parse_dt(b.get("end"), datetime.now())
        start = _parse_dt(b.get("start"), end - timedelta(minutes=30))

    rep = build_report(STORE, start, end, CFG,
                       use_llm=b.get("use_llm", True),
                       source=b.get("source", "query"))
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
