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

from lp_client import fab_codes, load_config, parse_dt, ping, sys_cfg
from lp_query import build, query
from report import build_report, feedback_status, save_feedback
from sentinel import CaseStore, alarm_floor, grade_cuts, scan_once

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CFG = load_config()

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "static"))


# ─────────────────────── 느린 요청 로그 ───────────────────────
# "저장이 오래 걸린다" 같은 말을 숫자로 바꾸기 위한 것. 개발 PC 에서는 4ms 인
# 요청이 현장에서 느리면, 원인이 코드가 아니라 그 서버의 무언가(디스크·수집
# 스레드·백신 등)라는 뜻이다. 어느 요청이 몇 초 걸렸는지 남겨야 좁힐 수 있다.
SLOW_MS = 1000                      # 이보다 오래 걸린 요청만 남긴다
SLOW_LOG: list = []                 # 최근 50건 (화면에서 볼 수 있게)


@app.before_request
def _t_start():
    request.environ["_t0"] = time.time()


@app.after_request
def _t_end(resp):
    t0 = request.environ.get("_t0")
    if t0:
        ms = int((time.time() - t0) * 1000)
        resp.headers["X-Elapsed-ms"] = str(ms)
        if ms >= SLOW_MS and request.path.startswith("/api/"):
            rec = {"at": datetime.now().strftime("%H:%M:%S"),
                   "method": request.method, "path": request.full_path[:120],
                   "ms": ms}
            SLOW_LOG.append(rec)
            del SLOW_LOG[:-50]
            print(f"[느림] {rec['method']} {rec['path']} — {ms}ms")
    return resp


@app.route("/api/slow")
def api_slow():
    """최근 느린 요청 목록 — 현장에서 원인을 좁힐 때."""
    return jsonify({"threshold_ms": SLOW_MS, "items": list(reversed(SLOW_LOG))})


# ─────────────────────── 시스템(FAB) 별 컨텍스트 ───────────────────────
# ALL(전체 통합) + FAB 별 화면이 **한 서버**에서 같이 돈다. 케이스 저장소·
# 폴링 상태·캐시가 시스템마다 따로 있어야 M14 화면이 ALL 케이스를 보는
# 사고가 안 난다. 설정은 sys_cfg() 의 얕은 뷰라 수집 주기 같은 공유 설정은
# 전 시스템에 즉시 반영된다.
def systems() -> list[str]:
    """관제 시스템 목록 — ALL + config.source.jupyter.fabs (주피터 모드일 때만).

    FAB 별 파일은 주피터에만 있다. 로그프레소 모드면 ALL 하나다.
    """
    from sentinel import source_mode
    if source_mode(CFG) != "jupyter":
        return ["ALL"]
    return ["ALL"] + [s for s in fab_codes(CFG) if s != "ALL"]


def _blank_state() -> dict:
    """폴링 상태 (대시보드 헤더의 STREAMING · latency 표시용)."""
    return {"last_scan": None, "latency_ms": None, "connected": False,
            "error": None, "amos_warn": None,
            "source": None,            # 데이터 출처 — logpresso / jupyter
            "scans": 0,
            "forecast": None}          # 선행 감지 결과 (forecast.predict)


CTX_LOCK = threading.Lock()
CTX: dict[str, dict] = {}


def get_ctx(sys: str | None = "ALL") -> dict:
    """시스템 컨텍스트 — 없으면 만든다. 모르는 코드는 ALL 로 (화면이 죽는
    것보다 전체 화면이 낫다)."""
    s = str(sys or "ALL").strip().upper() or "ALL"
    if s not in systems():
        s = "ALL"
    with CTX_LOCK:
        if s not in CTX:
            c = sys_cfg(CFG, s)
            CTX[s] = {
                "sys": s, "cfg": c, "store": CaseStore(c),
                "state": _blank_state(),
                "watched": 0.0,        # 마지막으로 이 시스템 화면이 물어본 시각
                # 빈 구간 메움(backfill) 진행 상태
                "backfill": {"running": False, "day": None, "started": None,
                             "result": None},
                # 선행 지표 분석 캐시 — 며칠치 CSV 를 훑어서 매 요청 재계산하면 느리다
                "leading": {"at": 0.0, "data": None, "key": ""},
                # 임계 격자 탐색은 며칠치를 수십 번 되감아 몇 초 걸린다 — 짧게 캐시
                "tune": {"at": 0.0, "data": None, "key": ""},
                "cmp": {"at": 0.0, "data": None, "key": ""},
            }
        return CTX[s]


def rctx() -> dict:
    """요청의 ?sys= 로 컨텍스트를 고른다 (없으면 ALL). 화면이 보고 있다는
    표시(watched)도 여기서 남긴다 — FAB 의 분당 LLM 은 보고 있을 때만 돈다."""
    c = get_ctx(request.args.get("sys"))
    c["watched"] = time.time()
    return c


# ────────────────────────────── 폴링 루프 ──────────────────────────────
def _bootstrap_today() -> None:
    """기동 시 **모든 시스템**의 오늘 하루치를 확보한다 (00:00 ~ 현재).

    중간에 서버가 꺼져 있던 구간까지 메운다. 이미 저장된 분은 중복으로 걸러지므로
    여러 번 돌려도 안전하다. 이후 수집은 폴링 루프가 증분으로 이어간다.
    FAB 파일이 아직 없는 날(404)은 경고만 남기고 계속 간다.
    """
    from sentinel import source_mode
    now = datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day = now.strftime("%Y%m%d")
    jup = source_mode(CFG) == "jupyter"
    ss = systems()
    print(f"[기동] 오늘({day}) 00:00 ~ {now:%H:%M} 하루치 확보 중… "
          f"({'주피터 CSV' if jup else '로그프레소'} · {' '.join(ss)})")
    for sys in ss:
        ctx = get_ctx(sys)
        t0 = time.time()
        tag = f"[기동:{sys}]"
        try:
            if jup:
                # ★출처가 주피터면 여기서도 주피터로 받는다. 예전엔 이 자리에서만
                #   collect()(=로그프레소)를 불러서, 설정을 바꿔도 기동 때 한 번은
                #   로그프레소를 치고 있었다.
                from jupyter_csv import fetch_day
                jr = fetch_day(day, ctx["cfg"], verbose=False)
                r = {"ok": jr.get("ok"), "error": jr.get("error"),
                     "rows": jr.get("rows", 0), "written": jr.get("written", 0),
                     "skipped": jr.get("skipped", 0), "files": jr.get("files") or [],
                     "minutes": jr.get("rows", 0)}
            else:
                from collect import collect
                r = collect(start.strftime("%Y%m%d%H%M%S"), now.strftime("%Y%m%d%H%M%S"),
                            ctx["cfg"], verbose=False)
            if not r.get("ok"):
                print(f"{tag} ⚠️ 확보 실패 — {r.get('error')}")
                ctx["state"]["bootstrap"] = {"ok": False, "error": r.get("error")}
                continue
            print(f"{tag} ✅ {r['rows']}행({r['minutes']}분) 조회 · 신규 {r['written']}행 저장 · "
                  f"중복 {r['skipped']}"
                  + (f" → {', '.join(r['files'])}" if r.get("files") else "")
                  + f"  [{round(time.time()-t0,1)}초]")
            if r.get("warn"):
                print(f"{tag} ⚠️ {r['warn']}")
            ctx["state"]["bootstrap"] = {"ok": True, "minutes": r["minutes"],
                                         "written": r["written"],
                                         "at": datetime.now().isoformat()}
        except Exception as e:
            print(f"{tag} ⚠️ 확보 예외: {type(e).__name__}: {e}")
            ctx["state"]["bootstrap"] = {"ok": False, "error": str(e)}


def _llm_mode(sys: str) -> str:
    """이 시스템의 분당 판단 모드 — on / watched / off.

    정책 탭에서 시스템 6개를 따로 정한다 (llm.per_minute.by_sys). 지정이
    없으면 옛 전역 스위치(fab_minute)와 호환: ALL=on, FAB=fab_minute.
    """
    lc = CFG.get("llm", {})
    by = (lc.get("per_minute") or {}).get("by_sys") or {}
    mode = str((by.get(sys) or {}).get("mode", "")).strip().lower()
    if mode in ("on", "watched", "off"):
        return mode
    if sys == "ALL":
        return "on"
    return {"always": "on", "watched": "watched",
            "off": "off"}.get(str(lc.get("fab_minute", "always")).lower(), "on")


def _llm_on(ctx: dict, interval: int) -> bool:
    """이 시스템의 분당 LLM 판단을 돌릴까.

      · on(기본)  — 안 보고 있어도 돈다. 'LLM 판단 일치' 가 그 화면에 쌓인다.
        부하는 괜찮다 — 분당 판단은 accuracy._busy 락으로 **전 시스템이
        한 번에 하나씩만** 게이트웨이를 치고, 폴링 루프가 시스템마다 시작
        시차를 둔다 (4단계 병렬 분석과는 다른 가벼운 호출).
      · watched — 화면이 실제로 보고 있을 때만 (게이트웨이가 힘들 때)
      · off     — 안 돌린다
    데이터 수집·케이스 감지는 이 설정과 무관하게 전부 돈다.
    """
    mode = _llm_mode(ctx["sys"])
    if mode == "off":
        return False
    if mode == "watched":
        return (time.time() - ctx["watched"]) < max(300, interval * 3)
    return True


def _llm_work(ctx: dict, cases: list, llm_on: bool, order: int) -> None:
    """LLM 관련 후속 작업 — 수집 루프 밖에서 돈다 (수집을 절대 막지 않게)."""
    try:
        if cases:
            _auto_judge(ctx, cases)
        if llm_on:
            _minute_llm(ctx, delay=order * 4.0)
    except Exception as e:
        print(f"[LLM:{ctx['sys']}] ⚠️ 후속 작업 예외: {type(e).__name__}: {e}")


def _poll_loop() -> None:
    """수집 루프 — 매 회 모든 시스템을 돌고, 주기는 config 에서 다시 읽는다."""
    _bootstrap_today()                 # ① 하루치 먼저 확보
    while True:                        # ② 이후 증분 수집
        interval = max(5, int(CFG.get("query", {}).get("poll_interval_s", 60)))
        for i, sys in enumerate(systems()):
            ctx = get_ctx(sys)
            st = ctx["state"]
            t0 = time.time()
            try:
                res = scan_once(ctx["store"], cfg=ctx["cfg"])
                st.update(
                    last_scan=datetime.now().isoformat(),
                    latency_ms=int((time.time() - t0) * 1000),
                    connected=bool(res.get("ok")),
                    error=None if res.get("ok") else res.get("error"),
                    amos_warn=res.get("amos_warn"),
                    source=res.get("source"),
                    scans=st["scans"] + 1,
                    window=CFG.get("query", {}).get("window", "10m"),
                    last_rows=res.pop("all_rows", None) or st.get("last_rows"),
                    saved=res.get("saved"),
                    gap_min=res.get("gap_min"),
                    source_latest=res.get("latest"),   # 원본 CSV 의 최신 행 시각
                )
                sv = res.get("saved") or {}
                if st["scans"] == 1 or sv.get("written"):
                    print(f"[수집:{sys}] {res.get('rows')}행 조회 · "
                          f"신규 {sv.get('written', 0)}행 저장"
                          + (f" → {sv['files'][0]}" if sv.get("files") else ""))
                if res.get("ok"):
                    # ★데이터가 우선이다. 선행 감지는 가벼우니 바로 하고,
                    #   LLM(케이스 자동 판단·분당 판단)은 **별도 스레드**로
                    #   떼어 보낸다. 여기서 직접 부르면 게이트웨이가 느린 날
                    #   그만큼 다음 시스템 수집이 통째로 밀린다 — 화면 데이터가
                    #   몇 분씩 뒤처지는 원인이었다.
                    _update_forecast(ctx)
                    cases = res.get("cases") or []
                    llm_on = _llm_on(ctx, interval)
                    if cases or llm_on:
                        threading.Thread(
                            target=_llm_work, args=(ctx, cases, llm_on, i),
                            daemon=True).start()
            except Exception as e:
                st.update(connected=False, error=f"{type(e).__name__}: {e}",
                          last_scan=datetime.now().isoformat())

        # 주기를 나눠 자며 변경을 빠르게 반영
        slept = 0
        while slept < interval:
            time.sleep(min(2, interval - slept))
            slept += 2
            if int(CFG.get("query", {}).get("poll_interval_s", 60)) != interval:
                break                       # 주기가 바뀌면 즉시 다음 수집으로


def _minute_llm(ctx: dict, delay: float = 0.0) -> None:
    """1분 추론 + 검증 창이 찬 과거 행 채점 — 수집 루프를 막지 않게 별도 스레드.

    delay: 시스템별 시작 시차(초). 여섯 시스템이 같은 순간에 몰리면
    accuracy._busy 락(skip_if_busy)에 걸려 한 놈만 돌고 나머지는 그 주기를
    건너뛴다 — 시차를 두면 락이 비어 있을 때 도착해 매 주기 고르게 돈다.
    (건너뛰어도 다음 주기에 과거로 거슬러 메우므로 영구 공백은 없다.)
    """
    rows = ctx["state"].get("last_rows") or []
    cfg, sys = ctx["cfg"], ctx["sys"]

    def work():
        try:
            if delay > 0:
                time.sleep(delay)
            from accuracy import run_minute, verify_day
            out = run_minute(rows, cfg)
            if out and out.get("오류"):
                print(f"[LLM/1분:{sys}] ⚠️ {out['datetime']} — {out['오류']}")
            v = verify_day(datetime.now().strftime("%Y%m%d"), cfg)
            if v.get("scored"):
                print(f"[검증:{sys}] {v['scored']}건 채점 (대기 {v['waiting']}건)")
        except Exception as e:
            print(f"[LLM/1분:{sys}] ⚠️ 예외: {type(e).__name__}: {e}")

    threading.Thread(target=work, daemon=True).start()


_LEVEL_ORD = {"경계": 1, "위험": 2, "초위험": 3}


def _auto_judge(ctx: dict, case_ids: list[str]) -> None:
    """실시간 감지 즉시 LLM 이 판단하게 한다 (신규·등급상향 케이스만)."""
    store, cfg = ctx["store"], ctx["cfg"]
    lc = cfg.get("llm", {})
    if not (lc.get("enabled", True) and lc.get("auto_judge", True)):
        return
    floor = _LEVEL_ORD.get(lc.get("auto_judge_min_level", "경계"), 1)

    for cid in case_ids:
        c = store.by_id(cid)
        if not c or not c.pop("_new", False):
            continue
        if _LEVEL_ORD.get(c.get("level"), 0) < floor:
            continue

        def work(case_id=cid):
            try:
                from llm_client import judge_case
                cc = store.by_id(case_id)
                if not cc:
                    return
                res, err = judge_case(cc, cfg)
                if err:
                    print(f"[LLM:{ctx['sys']}] ⚠️ {case_id} 자동 판단 실패: {err}")
                    return
                cc["llm"] = {**res, "at": datetime.now().isoformat(), "auto": True}
                store.save()
                print(f"[LLM:{ctx['sys']}] 🤖 {case_id} 자동 판단 완료 "
                      f"(확신도 {res.get('확신도')}%)")
            except Exception as e:
                print(f"[LLM:{ctx['sys']}] ⚠️ {case_id} 자동 판단 예외: {e}")

        threading.Thread(target=work, daemon=True).start()
    store.save()


def _update_forecast(ctx: dict) -> None:
    """선행 감지 — 최근 추세로 '임계 돌파 N분 전' 을 미리 띄운다.

    수집 루프에서 매 회 부른다. 계산은 최근 20분 점수만 쓰는 가벼운 회귀라
    수집을 지연시키지 않는다. 실패해도 관제는 계속돼야 하므로 조용히 넘어간다.
    """
    st = ctx["state"]
    try:
        from forecast import predict
        fc = predict(st.get("last_rows") or [], ctx["cfg"])
        prev = st.get("forecast") or {}
        st["forecast"] = fc
        # 경보가 새로 뜬 순간만 콘솔에 한 줄 (매분 도배 방지)
        if fc.get("warn") and not prev.get("warn"):
            print(f"[선행:{ctx['sys']}] ⚠️ {fc['eta_min']}분 뒤 임계 돌파 예상 "
                  f"— 현재 {fc['current']}점, 분당 {fc['slope']:+.2f}점 "
                  f"(확신 {fc['confidence']}%)")
    except Exception as e:
        st["forecast"] = {"ok": False, "warn": False,
                          "reason": f"{type(e).__name__}: {e}"}


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
     "label": "M16HUB 리프터 정체", "unit": "회", "color": "#FF6FB5"},
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
    """오프닝(시스템 선택) → 관제 화면.

    ★캐시를 끈다. 관제 화면은 한 번 띄우면 며칠씩 그대로 떠 있고, 그 사이
      dashboard.html 을 새로 올려도 브라우저가 예전 걸 계속 쓴다. 실제로
      오프닝 화면을 추가했는데 "안 나온다" 였다 — 파일은 바뀌었는데 화면이
      옛날 것이었다. HTML 한 장(250KB)이라 매번 받아도 부담이 없다.
    """
    resp = send_from_directory(app.static_folder, "dashboard.html")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers.pop("ETag", None)
    resp.headers.pop("Last-Modified", None)
    return resp


@app.route("/api/version")
def version():
    """지금 서버가 **어느 파일**을 내보내고 있는지 — 화면이 옛날 것 같을 때
    여기부터 본다. 브라우저 캐시 문제인지, 파일을 안 덮어쓴 것인지 갈린다."""
    p = os.path.join(app.static_folder, "dashboard.html")
    try:
        st = os.stat(p)
        with open(p, encoding="utf-8") as f:
            body = f.read()
    except OSError as e:
        return jsonify({"ok": False, "error": str(e), "path": p})
    return jsonify({
        "ok": True,
        "path": p,
        "bytes": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "오프닝화면": "const SYSTEMS" in body,      # 있으면 새 파일
        "AMOS표시등": "ch-amos" in body,            # 있으면 옛날 파일
        # 정책 탭 카드가 실제로 이 파일에 들어 있는지 — "정책에 안 보인다" 확인용
        "정책_스코어카드": 'id="sprows"' in body,
        "정책_LLM카드": 'id="lprows"' in body,
        "정책_재시도": "apiRetry" in body,
        # 서버 쪽 엔드포인트도 같이 (파일만 새것이고 서버가 옛날일 수 있다)
        "API_score_policy": any(str(r) == "/api/score_policy"
                                for r in app.url_map.iter_rules()),
        "API_llm_policy": any(str(r) == "/api/llm_policy"
                              for r in app.url_map.iter_rules()),
    })


@app.route("/favicon.ico")
def favicon():
    return ("", 204)


# ────────────────────────────── 상태 ──────────────────────────────
@app.route("/api/status")
def api_status():
    C = rctx()
    return jsonify({
        "state": C["state"],
        "alarm_floor": alarm_floor(C["cfg"]),
        "poll_interval_s": C["cfg"].get("query", {}).get("poll_interval_s", 30),
        "offline": os.getenv("LP_OFFLINE") == "1",
        "table": C["cfg"].get("table_name"),
        "base": C["cfg"].get("logpresso_base"),
        "model": C["cfg"].get("llm", {}).get("model"),
        "policy": C["cfg"].get("policy", {}),
        "evaluation": C["cfg"].get("evaluation", {}),
        "server_time": datetime.now().isoformat(),
        "sys": C["sys"],
        "systems": systems(),
        # ★설정상의 출처. state.source 는 '마지막 수집이 성공했을 때' 채워지므로,
        #   실패하면 비어서 화면이 '로그프레소' 로 떨어져 거짓말을 했다.
        "source_mode": __import__("sentinel").source_mode(C["cfg"]),
        # 이 시스템의 등급 컷 — 화면(gradeOf·추이 밴드·범례)이 이 값으로 그린다
        "cuts": dict(zip(("warn", "danger", "critical"), grade_cuts(C["cfg"]))),
    })


@app.route("/api/ping")
def api_ping():
    ok, msg = ping()
    return jsonify({"ok": ok, "message": msg, "base": CFG.get("logpresso_base")})


def _persist_llm_policy() -> str:
    """지금 메모리의 분당 판단 설정을 config.json 에 그대로 적는다 → 오류 문자열.

    파일을 새로 읽어 llm 블록만 갈아끼우고 원자적으로 교체한다 — 파일에
    있는 다른 설정(사용자가 손으로 고친 것 포함)은 건드리지 않는다.
    """
    from lp_client import CONFIG_PATH
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
            disk = json.load(f)
        pm_mem = (CFG.get("llm", {}) or {}).get("per_minute") or {}
        pm = disk.setdefault("llm", {}).setdefault("per_minute", {})
        for k in ("enabled", "every_min", "max_per_cycle", "by_sys"):
            if k in pm_mem:
                pm[k] = pm_mem[k]
        tmp = CONFIG_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(disk, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, CONFIG_PATH)
        return ""
    except Exception as e:
        return f"{type(e).__name__}: {e}"


def _persist_score_policy() -> str:
    """메모리의 시스템별 등급 컷(grade.by_sys)을 config.json 에 적는다 → 오류."""
    from lp_client import CONFIG_PATH
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
            disk = json.load(f)
        mem = (CFG.get("grade", {}) or {}).get("by_sys")
        g = disk.setdefault("grade", {})
        if mem:
            g["by_sys"] = mem
        else:
            g.pop("by_sys", None)
        tmp = CONFIG_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(disk, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, CONFIG_PATH)
        return ""
    except Exception as e:
        return f"{type(e).__name__}: {e}"


@app.route("/api/score_policy", methods=["GET", "POST"])
def api_score_policy():
    """스코어 등급 컷 — **시스템 6개 각각**. FAB 마다 점수 분포가 다르다.

    POST {"by_sys": {"M14": {"warn": 55, "danger": 70, "critical": 85}
                     또는 null(기본으로 되돌리기), …},
          "save"?: true}
    warn=경계 시작 / danger=위험 시작 / critical=초위험 시작.
    1 ≤ warn < danger < critical ≤ 100. warn 미만은 정상(무알람).
    ★메모리에 먼저 적용(등급·알람·케이스·그래프가 즉시 이 컷으로 계산)하고,
      save=true 면 config.json 에도 적는다.
    """
    g = CFG.setdefault("grade", {})
    saved = None
    if request.method == "POST":
        b = request.get_json(silent=True) or {}
        if "by_sys" in b:
            if not isinstance(b["by_sys"], dict):
                return jsonify({"error": "by_sys 는 {시스템: 설정|null} 객체"}), 400
            known = set(systems())
            sets, resets = {}, []
            for s_, row in b["by_sys"].items():
                s_ = str(s_).upper()
                if s_ not in known:
                    return jsonify({"error": f"모르는 시스템 {s_} (가능: {sorted(known)})"}), 400
                if row is None:
                    resets.append(s_)
                    continue
                try:
                    w = int(row.get("warn")); d_ = int(row.get("danger")); c = int(row.get("critical"))
                except (TypeError, ValueError):
                    return jsonify({"error": f"{s_}: warn/danger/critical 은 정수(점)"}), 400
                if not (1 <= w < d_ < c <= 100):
                    return jsonify({"error": f"{s_}: 1 ≤ 경계({w}) < 위험({d_}) < "
                                             f"초위험({c}) ≤ 100 이어야 합니다"}), 400
                sets[s_] = {"warn": w, "danger": d_, "critical": c}
            # ★객체 갈아끼우기 금지 — sys_cfg 뷰들이 grade 블록을 공유한다
            by = g.setdefault("by_sys", {})
            for s_ in resets:
                by.pop(s_, None)
            by.update(sets)
            if not by:
                g.pop("by_sys", None)
        if b.get("save"):
            err = _persist_score_policy()
            saved = not err
            if err:
                return jsonify({"error": f"config.json 저장 실패 — {err} "
                                         f"(메모리에는 적용됨)", "applied": True}), 500
        rows = " · ".join(f"{s_}={'/'.join(map(str, grade_cuts(sys_cfg(CFG, s_))))}"
                          for s_ in systems())
        print(f"[정책] 스코어 컷 → {rows}" + (" · 저장됨" if saved else ""))
    by = g.get("by_sys") or {}
    out = []
    for s_ in systems():
        w, d_, c = grade_cuts(sys_cfg(CFG, s_))
        out.append({"sys": s_, "warn": w, "danger": d_, "critical": c,
                    "custom": s_ in by})
    return jsonify({"systems": out, "saved": saved})


@app.route("/api/llm_policy", methods=["GET", "POST"])
def api_llm_policy():
    """분당 LLM 판단(=LLM 판단 일치의 재료) 설정 — 정책 탭, **시스템 6개 각각**.

    느리다는 체감의 주범이 이것이다: 시스템마다 매 주기 '아직 판단 안 한 분'
    을 최대 max_per_cycle 건씩 LLM 에 물어본다 (전 시스템 직렬화라 게이트웨이
    는 한 번에 하나지만, 큐가 길면 다른 LLM 호출이 밀린다).

    POST {"enabled"?: bool,
          "by_sys"?: {"M14": {"mode": "on|watched|off",
                              "every_min": 1, "max_per_cycle": 3}, …},
          "save"?: true}
    ★메모리에 먼저 적용(다음 주기부터 바로 반영)하고, save=true 면
      config.json 에도 적는다 — 저장 버튼 하나로 '즉시 반영 + 재시작 유지'.
    """
    lc = CFG.setdefault("llm", {})
    pm = lc.setdefault("per_minute", {})
    EV, CAP = (1, 2, 5, 10, 15), (1, 2, 3, 5, 10)
    saved = None
    if request.method == "POST":
        b = request.get_json(silent=True) or {}
        if "enabled" in b:
            pm["enabled"] = bool(b["enabled"])
        if "by_sys" in b:
            if not isinstance(b["by_sys"], dict):
                return jsonify({"error": "by_sys 는 {시스템: 설정} 객체"}), 400
            known = set(systems())
            clean = {}
            for s_, row in b["by_sys"].items():
                s_ = str(s_).upper()
                if s_ not in known:
                    return jsonify({"error": f"모르는 시스템 {s_} (가능: {sorted(known)})"}), 400
                row = row or {}
                mode = str(row.get("mode", "on")).strip().lower()
                if mode not in ("on", "watched", "off"):
                    return jsonify({"error": f"{s_}.mode 는 on|watched|off"}), 400
                try:
                    ev = int(row.get("every_min", pm.get("every_min", 1)))
                    cap = int(row.get("max_per_cycle", pm.get("max_per_cycle", 3)))
                except (TypeError, ValueError):
                    return jsonify({"error": f"{s_} 의 every_min/max_per_cycle 은 정수"}), 400
                if ev not in EV:
                    return jsonify({"error": f"{s_}.every_min 은 {list(EV)} 중 하나"}), 400
                if cap not in CAP:
                    return jsonify({"error": f"{s_}.max_per_cycle 은 {list(CAP)} 중 하나"}), 400
                clean[s_] = {"mode": mode, "every_min": ev, "max_per_cycle": cap}
            # ★객체를 갈아끼우지 않고 내용만 고친다 — sys_cfg 뷰들이 같은
            #   llm 블록을 참조하므로, 통째로 바꾸면 FAB 만 옛 설정으로 돈다.
            by = pm.setdefault("by_sys", {})
            by.update(clean)
        if b.get("save"):
            err = _persist_llm_policy()
            saved = not err
            if err:
                return jsonify({"error": f"config.json 저장 실패 — {err} "
                                         f"(메모리에는 적용됨)", "applied": True}), 500
        rows = " · ".join(f"{s_}={_llm_mode(s_)}" for s_ in systems())
        print(f"[정책] LLM 판단 → 전체 {pm.get('enabled', True)} · {rows}"
              + (" · 저장됨" if saved else ""))
    by = pm.get("by_sys") or {}
    return jsonify({
        "enabled": bool(pm.get("enabled", True)),
        "every_options": list(EV), "cap_options": list(CAP),
        "systems": [{
            "sys": s_,
            "mode": _llm_mode(s_),
            "every_min": int((by.get(s_) or {}).get("every_min",
                                                    pm.get("every_min", 1)) or 1),
            "max_per_cycle": int((by.get(s_) or {}).get("max_per_cycle",
                                                        pm.get("max_per_cycle", 3)) or 3),
        } for s_ in systems()],
        "saved": saved,
    })


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
    C = rctx()
    from sentinel import (_row_dt, _score, grade, hid_zones, reason_metrics,
                          summarize_reason)

    # 오늘 쌓인 전체 데이터. 오늘이 아직 비었으면 가장 최근 날짜를 대신 보여준다.
    from store_csv import list_days, read_day
    asked = (request.args.get("day") or "").strip()   # 날짜를 콕 집어 물어본 경우
    day = asked or datetime.now().strftime("%Y%m%d")
    rows, shown_day, fallback = [], day, False
    try:
        rows = read_day(day, C["cfg"])
        if not rows and not asked:
            for d in list_days(C["cfg"]):                 # 최신순
                r2 = read_day(d["day"], C["cfg"])
                if r2:
                    rows, shown_day, fallback = r2, d["day"], True
                    break
    except Exception as e:
        print(f"[FEED] ⚠️ 읽기 실패: {e}")
    # 폴링 버퍼 폴백은 '오늘' 요청일 때만. 과거 날짜를 물었는데 없으면 없는 것이다
    # (안 그러면 7/25 를 물었는데 오늘 버퍼가 나와서 날짜가 뒤바뀐다)
    if not rows and not asked:
        rows = C["state"].get("last_rows") or []

    # 추이 그래프에서 고를 수 있는 지표 묶음 — 값을 같이 실어보낸다
    groups = metric_groups(C["cfg"])
    mkeys = sorted({m["key"] for g in groups for m in g["metrics"]})
    seen_keys = set()

    out = []
    for r in rows:
        dt, sc = _row_dt(r), _score(r)
        if dt is None:
            continue
        g = grade(sc, C["cfg"])
        area = (r.get("hot_area") or "").strip() or "UNKNOWN"
        bd = (r.get("BOTTLENECK_downward_anomaly_cols") or "").strip()
        bu = (r.get("BOTTLENECK_upward_anomaly_cols") or "").strip()
        qd = (r.get("QUEUE_downward_anomaly_cols") or "").strip()
        qu = (r.get("QUEUE_upward_anomaly_cols") or "").strip()
        bott = " ".join(x for x in (bd, bu) if x)
        items = " ".join(x for x in (qd, qu) if x).split()
        # 이 시각이 속한 케이스 찾기
        cid = None
        for c in C["store"].cases:
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
            # 원문 fallback 금지 — 요약이 비면 룰 코드·금지어가 그대로 새어
            # 나갔다. summarize_reason 이 항상 한글 한 줄을 돌려준다.
            "reason": summarize_reason(raw_reason, area),
            "reason_raw": raw_reason,
            # 한글 요약 옆 '실제지표' 칸 — 그 룰이 실제로 보는 raw 컬럼명
            "metrics": [{"raw": x["raw"], "label": x["label"]}
                        for x in reason_metrics(raw_reason, area)],
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
                    "window": C["cfg"].get("query", {}).get("window", "10m")})


@app.route("/api/collect", methods=["POST"])
def api_collect():
    """수동 확보 — 오늘 하루 다시 훑거나(기본), 지정 날짜를 확보한다.

    {"date": "YYYYMMDD"} 또는 {} (오늘 00:00~현재)
    """
    C = rctx()
    b = request.get_json(silent=True) or {}
    from sentinel import source_mode
    try:
        # 주피터 CSV 모드는 로그프레소를 안 쓴다 — 그 날짜 파일을 받아 넣는다.
        if source_mode(C["cfg"]) == "jupyter":
            from jupyter_csv import backfill, fetch_day
            if b.get("back"):                     # 과거 N일 한꺼번에
                r = backfill(None, C["cfg"], back=int(b["back"]), verbose=False)
            elif b.get("from") and b.get("to"):   # 구간
                from datetime import timedelta
                d0 = parse_dt(b["from"]) or datetime.now()
                d1 = parse_dt(b["to"]) or datetime.now()
                span = [(d0 + timedelta(days=k)).strftime("%Y%m%d")
                        for k in range((d1 - d0).days + 1)]
                r = backfill(span, C["cfg"], verbose=False)
            else:
                r = fetch_day(b.get("date") or "", C["cfg"], verbose=False)
            return (jsonify(r), 200) if r.get("ok") else (jsonify(r), 502)

        from collect import collect, collect_day
        if b.get("date"):
            r = collect_day(b["date"], C["cfg"])
        else:
            now = datetime.now()
            r = collect(now.strftime("%Y%m%d000000"), now.strftime("%Y%m%d%H%M%S"),
                        C["cfg"], verbose=False)
        return (jsonify(r), 200) if r.get("ok") else (jsonify(r), 502)
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500


@app.route("/api/graph")
def api_graph():
    """구간 그래프 SVG — 목록에서 더블클릭한 시각 기준 1시간.

    /api/graph?at=2026-07-28T08:11:00&minutes=60
    """
    C = rctx()
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
        rows.extend(read_day(d, C["cfg"]))
    if not rows:
        rows = C["state"].get("last_rows") or []

    svg = render(rows, at, minutes, cfg=C["cfg"])
    return app.response_class(svg, mimetype="image/svg+xml")


@app.route("/api/contrib")
def api_contrib():
    """스코어 기여도 추정 — 그 1분의 점수를 어느 지표가 밀어올렸나.

    /api/contrib?at=2026-07-28T08:11:00  → 구간 그래프 모달에 붙일 HTML 조각.
    점수식을 푼 값이 아니라 '평소 대비 편차' 기반 **추정**이다(화면에도 명시).
    """
    C = rctx()
    from contrib import explain_html
    from store_csv import read_day
    at = parse_dt(request.args.get("at")) or datetime.now()
    rows = read_day(at.strftime("%Y%m%d"), C["cfg"]) or C["state"].get("last_rows") or []
    try:
        return app.response_class(explain_html(rows, at, C["cfg"]), mimetype="text/html")
    except Exception as e:
        return app.response_class(
            f'<div class="empty">기여도 분해 실패 — {type(e).__name__}: {e}</div>',
            mimetype="text/html")


@app.route("/api/accuracy")
def api_accuracy():
    """1분 LLM 판단 + 사후검증 결과. ?day=YYYYMMDD (기본 오늘), ?rows=1 이면 행까지."""
    C = rctx()
    from accuracy import acc_cfg, summary, verify_day
    from store_csv import read_llm_day
    day = (request.args.get("day") or "").strip() or datetime.now().strftime("%Y%m%d")
    # 그 날짜를 열 때 채점을 한 번 돌린다 (과거 날짜도 판정이 채워지게)
    try:
        verify_day(day, C["cfg"])
    except Exception as e:
        print(f"[검증] ⚠️ {day} 채점 실패: {e}")
    out = summary(day, C["cfg"])
    out["backfill"] = dict(C["backfill"])
    try:
        from accuracy import backlog
        out["backlog"] = backlog(C["state"].get("last_rows") or [], C["cfg"])
    except Exception:
        out["backlog"] = None
    if request.args.get("rows"):
        rows = read_llm_day(day, C["cfg"])
        rows.sort(key=lambda r: r.get("datetime") or "", reverse=True)
        try:
            lim = max(1, min(2000, int(request.args.get("rows", 300))))
        except ValueError:
            lim = 300
        rows = rows[:lim]
        # 아직 판정이 안 된 행에 '몇 분 뒤에 채점되는지' 를 붙여준다
        win = acc_cfg(C["cfg"])["window_min"]
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
    C = rctx()
    b = request.get_json(silent=True) or {}
    day = "".join(ch for ch in str(b.get("date") or "") if ch.isdigit())[:8] \
        or datetime.now().strftime("%Y%m%d")
    try:
        limit = max(0, min(1500, int(b.get("limit", 0) or 0)))
    except (TypeError, ValueError):
        limit = 0

    if C["backfill"].get("running"):
        return jsonify({"ok": False, "error": "이미 메우는 중입니다", "state": C["backfill"]}), 409

    def work():
        C["backfill"].update(running=True, day=day, started=datetime.now().isoformat(), result=None)
        try:
            from accuracy import backfill_day
            C["backfill"]["result"] = backfill_day(day, C["cfg"], limit)
        except Exception as e:
            C["backfill"]["result"] = {"error": f"{type(e).__name__}: {e}"}
        finally:
            C["backfill"]["running"] = False

    threading.Thread(target=work, daemon=True).start()
    return jsonify({"ok": True, "started": True, "day": day, "limit": limit})


@app.route("/api/accuracy/backfill")
def api_accuracy_backfill_state():
    C = rctx()
    return jsonify(C["backfill"])


@app.route("/api/accuracy/verdict", methods=["POST"])
def api_accuracy_verdict():
    """운영자가 직접 누른 판정 — 자동 판정을 덮어쓴다. {datetime, verdict:정탐|오탐}"""
    C = rctx()
    from accuracy import set_human
    b = request.get_json(silent=True) or {}
    dt = (b.get("datetime") or "").strip()
    v = (b.get("verdict") or "").strip()
    if not dt or v not in ("정탐", "오탐"):
        return jsonify({"ok": False, "error": "datetime 과 verdict(정탐|오탐) 필요"}), 400
    day = "".join(ch for ch in dt if ch.isdigit())[:8]
    ok = set_human(day, dt, v, C["cfg"])
    return jsonify({"ok": ok})


@app.route("/api/data/days")
def api_data_days():
    """누적 저장된 날짜 CSV 목록 (20260727_TOTAL.CSV ...)."""
    C = rctx()
    from store_csv import data_dir, list_days
    return jsonify({"dir": data_dir(C["cfg"]), "days": list_days(C["cfg"])})


@app.route("/api/data/<day>.csv")
def api_data_csv(day):
    """저장된 날짜 CSV 원본 다운로드 — 직접 열어볼 수 있게.

    /api/data/20260729.csv      → 20260729_TOTAL.CSV (데이터)
    /api/data/20260729_LLM.csv  → 20260729_LLM.CSV   (1분 LLM 판단·판정)
    """
    C = rctx()
    from store_csv import day_path, llm_path
    d = "".join(ch for ch in day if ch.isdigit())[:8]
    want_llm = "LLM" in day.upper()
    p = llm_path(d, C["cfg"]) if want_llm else day_path(d, C["cfg"])
    if not os.path.isfile(p):
        return jsonify({"error": f"{os.path.basename(p)} 없음"}), 404
    return send_from_directory(os.path.dirname(p), os.path.basename(p),
                               as_attachment=True)


def _recur_1h(ref: datetime, C: dict) -> dict:
    """재발률 — '50점(임계) 이상이 가라앉았다가 다시 올라왔나' 를 분단위 점수로 센다.

    최근 60분 점수를 보고 임계 이상 구간(런)을 끊는다. 임계 미만으로 내려간 뒤
    다시 올라오면 그게 재발이다.
        런 1개  → 재발 0회 → 0%
        런 3개  → 재발 2회 → 67%   (2/3)
    분모는 런 수, 분자는 재발 횟수(런 수 - 1). 최근 60분에 임계 이상이 아예
    없으면 rate 는 None (0% 로 굳어 보이지 않게).
    """
    from sentinel import _row_dt, _score
    floor = alarm_floor(C["cfg"])
    rows = C["state"].get("last_rows") or []
    try:                                      # 폴링 구간이 60분보다 짧으면 저장분으로 보충
        from store_csv import read_day
        saved = read_day(ref.strftime("%Y%m%d"), C["cfg"])
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
ANALYSIS: dict = {"running": False, "progress": {}, "last_id": None,
                  "cancel": None}


@app.route("/api/analysis/run", methods=["POST"])
def api_analysis_run():
    """4-LLM 병렬 분석 시작 — 백그라운드. body: {day, start?, end?} (HH:MM)."""
    C = rctx()
    if ANALYSIS["running"]:
        return jsonify({"error": "이미 분석이 돌고 있습니다 — 끝나면 다시 시도"}), 409
    body = request.get_json(silent=True) or {}
    day = "".join(ch for ch in str(body.get("day") or "") if ch.isdigit())[:8]
    if len(day) != 8:
        return jsonify({"error": "day(YYYYMMDD) 필요"}), 400
    start = str(body.get("start") or "")[:5]
    end = str(body.get("end") or "")[:5]

    # 단계별 모델 지정 — 안 고르면 config.llm.analysis.roles 기본값을 쓴다.
    # 이번 실행에만 적용하고 config.json 은 건드리지 않는다.
    from analysis import STAGES
    picked = body.get("models") or {}
    cfg = C["cfg"]
    over = {sid: str(picked.get(sid) or "").strip()
            for sid in STAGES if str(picked.get(sid) or "").strip()}
    if over:
        import copy
        cfg = copy.deepcopy(C["cfg"])
        a_cfg = cfg.setdefault("llm", {}).setdefault("analysis", {})
        roles = a_cfg.setdefault("roles", {})
        for sid, mdl in over.items():
            roles.setdefault(sid, {})["model"] = mdl

    ANALYSIS.update(running=True, progress={"stage": "start", "done": False},
                    sys=C["sys"],
                    day=day, span=f"{start or '00:00'}~{end or '24:00'}",
                    models=over, cancel=threading.Event())

    def work():
        try:
            from analysis import run_analysis
            r = run_analysis(day, cfg, start, end, progress=ANALYSIS["progress"],
                             cancel=ANALYSIS["cancel"])
            ANALYSIS["last_id"] = r.get("id")
            if not r.get("ok"):
                ANALYSIS["progress"].update(done=True, error=r.get("error"))
        except Exception as e:
            ANALYSIS["progress"].update(done=True, error=f"{type(e).__name__}: {e}")
        finally:
            ANALYSIS["running"] = False

    threading.Thread(target=work, daemon=True).start()
    return jsonify({"ok": True, "started": True})


@app.route("/api/analysis/stop", methods=["POST"])
def api_analysis_stop():
    """분석 중지 — 다음 단계 경계에서 멈춘다.

    이미 나간 LLM 호출은 응답이 올 때까지 못 끊는다(블로킹 소켓). 그래서
    '즉시 중단' 이 아니라 '진행 중인 호출이 끝나는 대로 중단' 이다.
    그때까지 나온 단계 결과는 그대로 저장된다.
    """
    ev = ANALYSIS.get("cancel")
    if not ANALYSIS.get("running") or ev is None:
        return jsonify({"ok": True, "running": False, "msg": "돌고 있는 분석이 없습니다"})
    ev.set()
    ANALYSIS["progress"]["cancelling"] = True
    return jsonify({"ok": True, "running": True,
                    "msg": "중지 요청됨 — 진행 중인 LLM 호출이 끝나면 멈춥니다"})


@app.route("/api/analysis/status")
def api_analysis_status():
    ev = ANALYSIS.get("cancel")
    return jsonify({"running": ANALYSIS["running"], "progress": ANALYSIS["progress"],
                    "last_id": ANALYSIS["last_id"],
                    "cancelling": bool(ev is not None and ev.is_set()
                                       and ANALYSIS["running"]),
                    "day": ANALYSIS.get("day"), "span": ANALYSIS.get("span")})


@app.route("/api/analysis/models")
def api_analysis_models():
    """게이트웨이가 이 키에 허용한 모델 목록 (/v1/models).

    모델 이름이 바뀌면 400/403 으로 단계가 통째로 죽는다. 화면에서 바로
    확인할 수 있어야 config 를 고칠 수 있다.
    """
    C = rctx()
    import urllib.error
    import urllib.request
    lc = C["cfg"].get("llm", {}) or {}
    base = str(lc.get("url", "")).split("/chat/completions")[0]
    if not base:
        return jsonify({"error": "llm.url 없음"}), 400
    headers = {}
    try:
        from llm_client import _api_key
        key = _api_key(C["cfg"])
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
    C = rctx()
    try:
        from analysis import list_analyses
        return jsonify({"items": list_analyses(C["cfg"])})
    except Exception as e:
        return jsonify({"items": [], "error": f"{type(e).__name__}: {e}"})


@app.route("/api/analysis/delete", methods=["POST"])
def api_analysis_delete():
    """분석 기록 삭제 — body: {ids: [...]} (여러 건 한 번에)."""
    C = rctx()
    ids = (request.get_json(silent=True) or {}).get("ids") or []
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "ids 필요"}), 400
    try:
        from analysis import delete_analyses
        return jsonify(delete_analyses(ids, C["cfg"]))
    except Exception as e:
        return jsonify({"error": f"{type(e).__name__}: {e}"}), 500


@app.route("/api/analysis/<aid>")
def api_analysis_get(aid):
    C = rctx()
    from analysis import get_analysis
    r = get_analysis(aid, C["cfg"])
    if not r:
        return jsonify({"error": "없는 분석"}), 404
    return jsonify(r)


@app.route("/api/forecast")
def api_forecast():
    """선행 감지 — 지금 추세로 본 임계 돌파 예보.

    수집 루프가 매 회 계산해 C["state"] 에 넣어 둔 것을 그대로 준다(요청마다 재계산
    안 함). 아직 한 번도 안 돌았으면 그 자리에서 한 번 계산한다.
    """
    C = rctx()
    fc = C["state"].get("forecast")
    if fc is None:
        _update_forecast(C)
        fc = C["state"].get("forecast")
    return jsonify(fc or {"ok": False, "warn": False, "reason": "아직 수집 전"})


@app.route("/api/forecast/score")
def api_forecast_score():
    """선행 감지 사후 채점 — 낸 경보가 맞았나. ?day= 하루, 없으면 최근 여러 날.

    저장된 CSV 를 1분씩 되감아 그때 예보를 다시 돌린다(판정 규칙은 실시간과
    같은 forecast._decide 하나를 공유). 적중/오보/놓침을 세고 실제 선행분을 낸다.
    """
    C = rctx()
    from forecast import score, score_days
    day = (request.args.get("day") or "").strip()
    try:
        if day:
            return jsonify(score(day, C["cfg"]))
        limit = max(1, min(30, int(request.args.get("limit", 14) or 14)))
        return jsonify(score_days(None, C["cfg"], None, limit))
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500


@app.route("/api/forecast/compare")
def api_forecast_compare():
    """다지표 선행 감지 A/B — 기존(점수 기울기만) vs 다지표를 같은 날로 채점.

    바꿨는데 좋아졌는지 모르면 안 바꾼 것만 못하다. 자동으로 갈아타지 않고
    숫자만 보여준다 — 켜고 끄는 건 config.forecast.multi.enabled.
    """
    C = rctx()
    import time as _t
    limit = max(1, min(30, int(request.args.get("limit", 14) or 14)))
    key = f"cmp|{limit}"
    now = _t.time()
    if (C["cmp"]["data"] and C["cmp"]["key"] == key
            and now - C["cmp"]["at"] < 60):
        return jsonify({**C["cmp"]["data"], "cached": True})
    try:
        from forecast import compare
        t0 = _t.time()
        data = compare(None, C["cfg"], limit)
        data["took_s"] = round(_t.time() - t0, 1)
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500
    C["cmp"].update(at=now, data=data, key=key)
    return jsonify({**data, "cached": False})


@app.route("/api/forecast/tune")
def api_forecast_tune():
    """임계 격자 탐색 — 지금 값보다 나은 min_slope·sustain_min 이 있나.

    격자를 다 돌아야 해서 몇 초 걸린다. 60초 캐시.
    """
    C = rctx()
    import time as _t
    limit = max(1, min(30, int(request.args.get("limit", 7) or 7)))
    key = f"tune|{limit}"
    now = _t.time()
    if (C["tune"]["data"] and C["tune"]["key"] == key
            and now - C["tune"]["at"] < 60):
        return jsonify({**C["tune"]["data"], "cached": True})
    try:
        from forecast import tune
        t0 = _t.time()
        data = tune(None, C["cfg"], limit=limit)
        data["took_s"] = round(_t.time() - t0, 1)
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500
    C["tune"].update(at=now, data=data, key=key)
    return jsonify({**data, "cached": False})


@app.route("/api/forecast/leading")
def api_forecast_leading():
    """선행 지표 — 과거 사건에서 어느 지표가 몇 분 먼저 움직였나.

    저장된 날짜 CSV 를 훑으므로 60초 캐시. days= 로 날짜를 직접 줄 수 있다.
    """
    C = rctx()
    import time as _t
    days = [d for d in (request.args.get("days", "") or "").split(",") if d.strip()]
    look = max(10, min(int(request.args.get("lookback", 60) or 60), 240))
    key = f"{','.join(days)}|{look}"
    now = _t.time()
    if (C["leading"]["data"] and C["leading"]["key"] == key
            and now - C["leading"]["at"] < 60):
        return jsonify({**C["leading"]["data"], "cached": True})
    try:
        from forecast import leading
        data = leading(days or None, C["cfg"], lookback_min=look)
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500
    C["leading"].update(at=now, data=data, key=key)
    return jsonify({**data, "cached": False})


@app.route("/api/kpi")
def api_kpi():
    """상단 지표 — 실제 계산 가능한 값만. 근거 없는 수치는 null 로 둔다."""
    C = rctx()
    act = C["store"].active()

    def _dt(s):
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None

    # ★기준 시각 = '데이터의 최신 시각'. 벽시계로 재면 로그프레소가 몇 분 밀리거나
    #   과거 날짜를 재생할 때 모든 케이스가 '1시간 밖' 이 돼 재발률이 늘 0% 로 굳는다.
    seen = [d for d in (_dt(c.get("last_seen") or c.get("opened_at"))
                        for c in C["store"].cases) if d]
    ref = max(seen) if seen else datetime.now()

    def age_min(c, field="opened_at"):
        d = _dt(c.get(field) or c.get("opened_at"))
        return (ref - d).total_seconds() / 60 if d else 0

    unack = [c for c in act if not c.get("acked_at")]
    new30 = [c for c in act if age_min(c) <= 30]

    rc = _recur_1h(ref, C)

    # LLM 판단 일치 — 1분 추론의 사후검증 결과 (★정탐률이 아니다)
    try:
        from accuracy import summary as acc_summary
        acc = acc_summary(None, C["cfg"])
    except Exception as e:
        acc = {"error": f"{type(e).__name__}: {e}"}

    return jsonify({
        "active": len(act),
        "active_new_30m": len(new30),
        "unack": len(unack),
        "unack_over_5m": len([c for c in unack if age_min(c) >= 5]),
        "detect_latency_ms": C["state"].get("latency_ms"),
        "recur_rate_1h": rc["rate"],
        "recur_base": rc["runs"],
        "recur_events": rc["recur"],
        "recur_minutes": rc["minutes"],
        "recur_floor": rc["floor"],
        "recur_ref": ref.isoformat(),
        "llm_match": acc,
        "by_level": {lv: len([c for c in act if c["level"] == lv])
                     for lv in ("경계", "위험", "초위험")},
        "alarm_floor": alarm_floor(C["cfg"]),
    })


# ────────────────────────────── 케이스 ──────────────────────────────
@app.route("/api/cases")
def api_cases():
    C = rctx()
    if request.args.get("all") == "1":
        return jsonify({"cases": C["store"].cases})
    return jsonify({"cases": C["store"].active()})


@app.route("/api/cases/<cid>")
def api_case(cid):
    C = rctx()
    c = C["store"].by_id(cid)
    return (jsonify(c), 200) if c else (jsonify({"error": "없는 케이스"}), 404)


@app.route("/api/cases/<cid>/<action>", methods=["POST"])
def api_case_action(cid, action):
    """확인 처리 / 이상 없음(재확인 예약만 갱신) / 종결."""
    C = rctx()
    body = request.get_json(silent=True) or {}
    who, note = body.get("who", "운영자"), body.get("note", "")
    fn = {"ack": C["store"].ack, "normal": C["store"].mark_normal, "close": C["store"].close}.get(action)
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
    C = rctx()
    c = C["store"].by_id(cid)
    if not c:
        return jsonify({"error": "없는 케이스"}), 404
    try:
        from llm_client import judge_case
        res, err = judge_case(c, C["cfg"])
    except Exception as e:
        res, err = None, f"{type(e).__name__}: {e}"
    if err:
        return jsonify({"error": err}), 502
    c["llm"] = {**res, "at": datetime.now().isoformat()}
    C["store"].save()
    return jsonify(c["llm"])


@app.route("/api/scan", methods=["POST"])
def api_scan():
    C = rctx()
    return jsonify(scan_once(C["store"], cfg=C["cfg"]))


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
    C = rctx()
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
            return jsonify(build_day_report(d.strftime("%Y%m%d"), C["cfg"],
                                            use_llm=b.get("use_llm", True)))
        start, end = d, d.replace(hour=23, minute=59, second=59)
    else:
        end = _parse_dt(b.get("end"), datetime.now())
        start = _parse_dt(b.get("start"), end - timedelta(minutes=30))

    rep = build_report(C["store"], start, end, C["cfg"],
                       use_llm=b.get("use_llm", True),
                       source=b.get("source", "query"))
    return jsonify(rep)


@app.route("/api/report/day.html")
def api_report_day_html():
    """하루 사건 리포트를 데모스 개인 에이전트와 같은 인터랙티브 HTML 로.

    /api/report/day.html?date=20260728  (없으면 오늘)
    체크박스 표·시간 시분 분리·O/X 판정·수동 기입·저장 툴바가 들어간다.
    """
    C = rctx()
    from report import build_day_report, day_report_html, load_day_report
    d = "".join(ch for ch in (request.args.get("date") or "") if ch.isdigit())[:8] \
        or datetime.now().strftime("%Y%m%d")
    use_llm = request.args.get("llm", "1") != "0"
    # 이미 생성해 둔 보고서가 있으면 그대로 연다 (다시 뽑으면 LLM 문장이 달라지므로)
    rep = (None if request.args.get("fresh") == "1" else load_day_report(d, C["cfg"])) \
        or build_day_report(d, C["cfg"], use_llm=use_llm)
    html = day_report_html(rep, C["cfg"])
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
    C = rctx()
    d = os.path.join(BASE_DIR, C["cfg"].get("storage", {}).get("reports", "data/reports"))
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
    C = rctx()
    p = os.path.join(BASE_DIR, C["cfg"].get("storage", {}).get("reports", "data/reports"), rid + ".json")
    if not os.path.isfile(p):
        return jsonify({"error": "없는 리포트"}), 404
    with open(p, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


# ────────────────────────────── 피드백 ──────────────────────────────
@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    C = rctx()
    b = request.get_json(silent=True) or {}
    res = save_feedback(b.get("report_id", ""), b.get("verdict", ""),
                        b.get("missed", ""), b.get("comment", ""),
                        b.get("who", "운영자"), C["cfg"])
    return (jsonify(res), 400) if res.get("error") else jsonify(res)


@app.route("/api/feedback/status")
def api_feedback_status():
    C = rctx()
    return jsonify(feedback_status(C["cfg"]))


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
    from sentinel import source_mode
    if source_mode(CFG) == "jupyter":
        from jupyter_csv import cfg_of, file_url
        _jc = cfg_of(CFG)
        try:
            _ju = file_url(datetime.now().strftime("%Y%m%d"), _jc)
        except Exception as _e:
            _ju = f"(URL 설정 오류: {_e})"
        print(f"  데이터원   : 주피터 CSV (로그프레소 미사용)")
        print(f"               {_ju}")
    else:
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
