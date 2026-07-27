#!/usr/bin/env python3
"""
AMHS Sentinel — 구간 리포트 + 피드백 (독립)

  · 구간 지정 → 평가 실행 → 주요 발견 / 다음 구간 예측·선제 조치
  · 리포트 피드백 → feedback.jsonl → 다음 리포트의 임계치·요약 방식에 반영
    (임계 보정은 sentinel.alarm_floor 가 읽어 적용)
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime

from lp_client import load_config
from sentinel import CaseStore, _row_dt, _score, alarm_floor, grade

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _dir(cfg: dict, key: str, default: str) -> str:
    p = os.path.join(BASE_DIR, cfg.get("storage", {}).get(key, default))
    os.makedirs(p, exist_ok=True)
    return p


def cases_from_query(from_dt: str, to_dt: str, cfg: dict | None = None):
    """★리포트 전용 — 로그프레소를 날짜로 직접 조회해 그 구간의 사건을 뽑는다.

    실시간 관제(케이스 저장소)와 분리된 경로다. 관제가 안 돌던 시간대도
    날짜만 지정하면 그대로 분석할 수 있다.

    from_dt/to_dt: "yyyyMMddHHmmss"
    반환 (cases, err)
    """
    cfg = cfg or load_config()
    from lp_query import fetch_amos

    rows, err = fetch_amos(from_dt=from_dt, to_dt=to_dt)
    if err and not err.get("warn"):
        return None, err
    warn = err.get("reason") if err else None

    # 조회 결과만으로 케이스를 새로 구성 (실시간 저장소를 건드리지 않는다)
    tmp = CaseStore.__new__(CaseStore)
    tmp.cfg, tmp.cases = cfg, []
    tmp._lock = threading.Lock()
    tmp.path = os.path.join(BASE_DIR, "data", ".report_tmp.json")
    tmp.save = lambda: None                    # 임시 — 디스크에 쓰지 않는다

    floor = alarm_floor(cfg)
    for row in rows or []:
        dt, sc = _row_dt(row), _score(row)
        if dt is None or sc < floor:
            continue
        tmp.ingest((row.get("hot_area") or "").strip() or "UNKNOWN", dt, sc, row)

    return sorted(tmp.cases, key=lambda c: c["peak_at"]), ({"warn": warn} if warn else None)


def cases_in_span(store: CaseStore, start: datetime, end: datetime) -> list[dict]:
    """구간에 최고점이 포함된 케이스."""
    out = []
    for c in store.cases:
        try:
            pk = datetime.fromisoformat(c["peak_at"])
        except Exception:
            continue
        if start <= pk <= end:
            out.append(c)
    return sorted(out, key=lambda c: c["peak_at"])


def build_report(store: CaseStore | None, start: datetime, end: datetime,
                 cfg: dict | None = None, use_llm: bool = True,
                 source: str = "query") -> dict:
    """구간 리포트 생성. LLM 실패해도 통계 리포트는 반드시 나온다.

    source="query" (기본) — 로그프레소를 날짜로 직접 조회 (관제와 분리)
    source="store"        — 실시간 케이스 저장소에서 추출
    """
    cfg = cfg or load_config()
    fetch_warn = None

    if source == "query":
        cs, werr = cases_from_query(start.strftime("%Y%m%d%H%M%S"),
                                    end.strftime("%Y%m%d%H%M%S"), cfg)
        if cs is None:
            cs, fetch_warn = [], (werr or {}).get("reason", "조회 실패")
        elif werr:
            fetch_warn = werr.get("warn")
    else:
        cs = cases_in_span(store, start, end) if store else []

    span = f"{start.strftime('%Y-%m-%d %H:%M')} ~ {end.strftime('%H:%M')}"

    top = max(cs, key=lambda c: c["peak_score"], default=None)
    summary = {
        "span": span,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "count": len(cs),
        "top_score": top["peak_score"] if top else 0,
        "top_level": top["level"] if top else "정상",
        "top_emoji": top["emoji"] if top else "🟢",
        "alarm_floor": alarm_floor(cfg),
        "by_level": {},
    }
    for c in cs:
        summary["by_level"][c["level"]] = summary["by_level"].get(c["level"], 0) + 1

    incidents = [{
        "no": i,
        "time": c["peak_at"][11:16],
        "area": c["area"],
        "score": c["peak_score"],
        "level": c["level"],
        "emoji": c["emoji"],
        "severity": c["severity"],
        "zones": c["evidence"].get("zones", []),
        "items": c["evidence"].get("items", []),
        "reason": c["evidence"].get("reason", ""),
        "status": c["status"],
        "case_id": c["id"],
    } for i, c in enumerate(cs, 1)]

    body, llm_err = "", None
    if use_llm and cfg.get("llm", {}).get("enabled", True):
        try:
            from llm_client import make_report
            body, llm_err = make_report(cs, span, cfg)
        except Exception as e:
            llm_err = f"{type(e).__name__}: {e}"
    if not body:
        body = _fallback_body(incidents, summary)

    rep = {
        "id": f"R{start.strftime('%Y%m%d%H%M')}-{end.strftime('%H%M')}",
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "incidents": incidents,
        "body": body,
        "llm_error": llm_err,
        "feedback_applied": _applied_summary(cfg),
    }
    path = os.path.join(_dir(cfg, "reports", "data/reports"), rep["id"] + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    rep["path"] = path
    return rep


def _fallback_body(incidents: list[dict], summary: dict) -> str:
    """LLM 미사용/실패 시의 통계 기반 본문 (관제가 멈추면 안 되므로)."""
    if not incidents:
        return ("## 주요 발견\n"
                f"이 구간에 임계 {summary['alarm_floor']}점 이상 사건이 없었습니다 (정상 운영).\n\n"
                "## 다음 구간 예측 · 선제 조치 제안\n특이 추세 없음. 현행 감시 유지.\n")
    lines = ["## 주요 발견"]
    for i in incidents:
        lines.append(f"- {i['time']} {i['area']} {i['emoji']} {i['level']} {i['score']:.0f}점"
                     + (f" — {i['reason']}" if i["reason"] else "")
                     + (f" (구간 {', '.join(i['zones'][:4])})" if i["zones"] else ""))
    lines += ["", "## 다음 구간 예측 · 선제 조치 제안",
              f"- 이 구간 최고 {summary['top_emoji']} {summary['top_level']} "
              f"{summary['top_score']:.0f}점. 동일 구간 재발 여부를 다음 주기에 확인 필요.",
              "- (LLM 미연결 — 통계 요약만 제공)"]
    return "\n".join(lines)


# ────────────────────────────── 피드백 ──────────────────────────────
_VERDICTS = ("정확", "과다탐지", "누락", "보통")


def save_feedback(report_id: str, verdict: str, missed: str = "",
                  comment: str = "", who: str = "운영자",
                  cfg: dict | None = None) -> dict:
    """리포트 피드백 저장 → 다음 리포트 임계치/요약에 반영."""
    cfg = cfg or load_config()
    if verdict not in _VERDICTS:
        return {"error": f"verdict 는 {_VERDICTS} 중 하나여야 합니다"}
    rec = {
        "at": datetime.now().isoformat(),
        "report_id": report_id,
        "verdict": verdict,
        "missed": missed.strip(),
        "comment": comment.strip(),
        "who": who,
    }
    path = os.path.join(BASE_DIR, cfg.get("feedback", {}).get("store", "data/feedback.jsonl"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    rec["applied"] = _applied_summary(cfg)
    return rec


def _applied_summary(cfg: dict) -> dict:
    """학습 반영 현황 — 피드백이 임계치를 얼마나 움직였는지."""
    fb = cfg.get("feedback", {})
    path = os.path.join(BASE_DIR, fb.get("store", "data/feedback.jsonl"))
    recs = []
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                recs = [json.loads(l) for l in f.read().splitlines() if l.strip()]
        except Exception:
            recs = []
    n = fb.get("apply_last_n", 20)
    recent = recs[-n:]
    base = min((b["min"] for b in cfg.get("grade", {}).get("bands", [])), default=50)
    counts = {v: sum(1 for r in recent if r.get("verdict") == v) for v in _VERDICTS}
    return {
        "total": len(recs),
        "applied_window": len(recent),
        "counts": counts,
        "base_floor": base,
        "current_floor": alarm_floor(cfg),
        "nudge": alarm_floor(cfg) - base,
        "missed_notes": [r["missed"] for r in recent if r.get("missed")][-5:],
    }


def feedback_status(cfg: dict | None = None) -> dict:
    return _applied_summary(cfg or load_config())


if __name__ == "__main__":
    from datetime import timedelta
    cfg = load_config()
    st = CaseStore(cfg)
    if not st.cases:
        print("케이스 없음 — 먼저 'LP_OFFLINE=1 python3 sentinel.py' 실행")
        raise SystemExit(0)
    peaks = [datetime.fromisoformat(c["peak_at"]) for c in st.cases]
    rep = build_report(st, min(peaks) - timedelta(minutes=1),
                       max(peaks) + timedelta(minutes=1), cfg, use_llm=False)
    print(f"리포트 {rep['id']}  구간 {rep['summary']['span']}  {rep['summary']['count']}건")
    for i in rep["incidents"]:
        print(f"  {i['no']}. {i['time']} {i['emoji']} {i['severity']} {i['score']:.0f}점 "
              f"| {', '.join(i['zones'][:4])}")
    print("\n" + rep["body"])
    print("학습 반영 현황:", json.dumps(rep["feedback_applied"], ensure_ascii=False))
