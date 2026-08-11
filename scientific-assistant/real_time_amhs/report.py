#!/usr/bin/env python3
"""
AMHS Sentinel_M16BR — 구간 리포트 + 피드백 (독립)

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
from sentinel import CaseStore, _row_dt, _score, alarm_floor, grade, summarize_reason

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
    warn = None

    # ① 저장된 날짜 CSV 우선 (1분마다 쌓아둔 것) — 재조회 불필요
    rows = []
    try:
        from store_csv import read_range
        rows = read_range(from_dt, to_dt, cfg)
    except Exception as e:
        print(f"[CSV] ⚠️ 읽기 실패: {e}")

    # ② 저장분이 없으면 로그프레소에서 그 날짜로 직접 조회
    if not rows:
        from lp_query import fetch_amos
        rows, err = fetch_amos(from_dt=from_dt, to_dt=to_dt)
        if err and not err.get("warn"):
            return None, err
        warn = err.get("reason") if err else None
        src = "로그프레소 직접 조회"
    else:
        src = f"저장 CSV {len(rows)}행"
    print(f"[리포트] {from_dt}~{to_dt} — {src}")

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


def build_day_report(day: str, cfg: dict | None = None, use_llm: bool = True) -> dict:
    """★하루 사건 리포트 — 데모스 개인 에이전트 '사건발생 보고서' 와 같은 5섹션.

    저장된 날짜 CSV 에서 ③ 사건목록 · ④ AMOS 표를 만들고 (daily.py — 스킬
    발동이벤트_요약 과 같은 규칙), 그 두 표만 근거로 LLM 이 보고서를 쓴다.
    """
    cfg = cfg or load_config()
    from daily import day_material

    day = "".join(ch for ch in str(day) if ch.isdigit())[:8]
    mat = day_material(day, cfg)
    fetch_warn = None

    # 저장분이 없으면 그 날짜를 로그프레소에서 확보한 뒤 다시 만든다
    if not mat["minutes"]:
        try:
            from collect import collect_day
            r = collect_day(day, cfg, verbose=False)
            if not r.get("ok"):
                fetch_warn = r.get("error") or "그 날짜 데이터를 확보하지 못했습니다"
            mat = day_material(day, cfg)
        except Exception as e:
            fetch_warn = f"{type(e).__name__}: {e}"

    pk = mat.get("peak") or {}
    summary = {
        "span": mat["date_ko"],
        "day": day,
        "start": f"{day[:4]}-{day[4:6]}-{day[6:8]}T00:00:00",
        "end": f"{day[:4]}-{day[4:6]}-{day[6:8]}T23:59:59",
        "count": len(mat["incidents"]),
        "top_score": pk.get("score", 0),
        "top_level": pk.get("level", "정상"),
        "top_emoji": pk.get("emoji", "🟢"),
        "alarm_floor": alarm_floor(cfg),
        "minutes": mat["minutes"],
        "risk_minutes": mat["risk_minutes"],
        "by_level": mat.get("by_level") or {},
        "busy": mat.get("busy"),
    }
    incidents = [{
        "no": r["번호"], "time": r["시각"], "span": r["구간"], "dur": r["지속분"],
        "area": r["시작영역"], "score": r["최고점수"], "level": r["최고등급"],
        # reason 은 **원문 그대로** 둔다 — report_graphs.parse_reason_metrics 가
        # 이걸 파싱해 어떤 지표가 실제로 발동했는지 고른다.
        # 사람에게 보여줄 때는 reason_kr(한글 요약)만 쓴다. 원문을 그대로 찍으면
        # 룰 코드와 금지어('역증가')가 화면에 노출된다.
        "reason": r.get("발동사유", ""),
        "reason_kr": summarize_reason(r.get("발동사유", ""), r.get("시작영역", "")),
    } for r in mat["incidents"]]

    body, llm_err = "", None
    if use_llm and cfg.get("llm", {}).get("enabled", True):
        try:
            from llm_client import make_day_report
            body, llm_err = make_day_report(mat, cfg)
        except Exception as e:
            llm_err = f"{type(e).__name__}: {e}"
    if not body:
        body = _fallback_day_body(mat)

    rep = {
        "id": f"D{day}",
        "kind": "day",
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "incidents": incidents,
        "amos": mat["amos"],
        "body": body,
        "llm_error": llm_err,
        "fetch_warn": fetch_warn,
        "feedback_applied": _applied_summary(cfg),
    }
    path = os.path.join(_dir(cfg, "reports", "data/reports"), rep["id"] + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    rep["path"] = path
    return rep


def load_day_report(day: str, cfg: dict | None = None) -> dict | None:
    """이미 생성해 둔 하루 리포트를 그대로 읽어온다 (없으면 None).

    '사건 보고서 생성' 이 만들어 둔 것을 'HTML 열기'·'내려받기' 가 다시 쓰도록 —
    열 때마다 LLM 을 다시 돌려 문장이 달라지는 일을 막는다.
    """
    cfg = cfg or load_config()
    day = "".join(ch for ch in str(day) if ch.isdigit())[:8]
    p = os.path.join(_dir(cfg, "reports", "data/reports"), f"D{day}.json")
    if not os.path.isfile(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            rep = json.load(f)
        return rep if rep.get("kind") == "day" else None
    except Exception:
        return None


def day_report_html(rep: dict, cfg: dict | None = None) -> str:
    """하루 사건 리포트 → 데모스 개인 에이전트와 같은 인터랙티브 HTML.

    마크다운 본문을 표까지 살려 HTML 로 바꾸고, amos_block(데모스 amos_report 의
    독립 복사본)이 체크박스 표·수동 기입·저장 툴바를 주입한다.
    """
    cfg = cfg or load_config()
    md_text = rep.get("body") or ""

    # ★ 그래프를 제목(# ) 바로 밑에 마크다운 그대로 끼운다
    #   — 데모스 GraphStreamInjector.feed 와 같은 위치. amos_block 이 뒤에서
    #     '위험 이벤트 상세' 헤딩 아래로 옮긴다.
    g = day_report_graph(rep, cfg)
    if g:
        import re as _re
        m = _re.search(r"(?m)^#\s+.+?\n", md_text + "\n")
        md_text = (md_text[:m.end()] + g + md_text[m.end():]) if m else (g + md_text)

    body = _md_to_html(md_text)

    title = ""
    for line in md_text.split("\n"):
        s = line.strip()
        if s.startswith("# ") and not s.startswith("## "):
            title = s.lstrip("# ").strip()
            break
    if not title:
        day = (rep.get("summary") or {}).get("day", "")
        title = f"{day} M16 BR 반송 이벤트 발생 확인건"
    import html as _html
    title = _html.escape(title)

    css = toolbar = js = ""
    maxw = "900px"
    try:
        from amos_block import AMOS_CSS, AMOS_JS, TOOLBAR_HTML, amosify
        body, has_amos = amosify(body)
        if has_amos:
            css, toolbar, js = AMOS_CSS, TOOLBAR_HTML, AMOS_JS
            maxw = "1120px"
    except Exception as e:
        print(f"[리포트] ⚠️ 인터랙티브 블록 주입 실패: {e}")

    # ↓ 데모스 개인 에이전트(/api/generate_html) 의 문서 골격·CSS 그대로
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
  body {{ font-family: 'Pretendard','Noto Sans KR',sans-serif; max-width: {maxw}; margin: 2rem auto; padding: 0 1.5rem; color: #1a1a2e; line-height: 1.7; }}
  h1,h2,h3 {{ color: #16213e; border-bottom: 2px solid #e2e8f0; padding-bottom: .3em; }}
  h1 {{ font-size: 1.45rem; }} h2 {{ font-size: 1.15rem; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1em 0; font-size: .86em; }}
  th,td {{ border: 1px solid #cbd5e1; padding: .4em .55em; text-align: left; vertical-align: top; word-break: keep-all; overflow-wrap: anywhere; }}
  th {{ background: #f1f5f9; font-weight: 700; white-space: nowrap; }}
  code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: .9em; }}
  pre {{ background: #1e293b; color: #e2e8f0; padding: 1em; border-radius: 8px; overflow-x: auto; }}
  pre code {{ background: none; color: inherit; padding: 0; }}
  blockquote {{ border-left: 4px solid #6366f1; margin: 1em 0; padding: .5em 1em; background: #f8fafc; }}
  a {{ color: #6366f1; }}
  img {{ max-width: 100%; border-radius: 8px; }}
{css}
</style>
</head>
<body>
{toolbar}
{body}
{js}
</body>
</html>"""


def day_report_graph(rep: dict, cfg: dict | None = None) -> str:
    """하루 리포트 그래프 — ★데모스 개인 에이전트와 완전히 동일.

    `report_graphs.build_report_graph` (demos_v1/report_graphs.py 독립 복사본) 를
    '사건단위' 질의로 부른다. 그러면 개인 에이전트 보고서와 같은 경로를 타서
    사건들을 한 그래프에 담고 사건 구간 음영·라벨까지 같게 그린다.

    `<div class="hub-report-graph">` 로 감싸져 나오므로 amos_block 이
    '위험 이벤트 상세' 헤딩 아래로 옮긴다 (데모스와 같은 흐름).
    """
    cfg = cfg or load_config()
    day = (rep.get("summary") or {}).get("day") or ""
    if not day:
        return ""
    try:
        from report_graphs import build_report_graph
        from store_csv import read_day

        rows = read_day(day, cfg)
        if not rows:
            return ""
        headers = list(rows[0].keys())
        # '사건발생' 키워드 → 개인 에이전트 '사건발생 보고서' 와 같은 통합 그래프 경로
        return build_report_graph(headers, rows, query="사건발생 보고서") or ""
    except Exception as e:
        print(f"[리포트] ⚠️ 그래프 생성 실패: {e}")
        return ""


def _ensure_table_blanklines(md: str) -> str:
    """표 앞 빈 줄 + 헤더 직후 구분선(|---|) 자동 보정 — 데모스와 같은 전처리.
    LLM 이 구분선을 빼먹으면 표가 '| 점수 |' 글자로 깨지기 때문."""
    import re as _re
    lines = str(md or "").split("\n")
    out: list[str] = []
    for i, ln in enumerate(lines):
        is_row = ln.lstrip().startswith("|")
        prev_row = bool(out) and out[-1].lstrip().startswith("|")
        if is_row and out and out[-1].strip() and not prev_row:
            out.append("")                      # 표 앞 빈 줄
        out.append(ln)
        if is_row and not prev_row:             # 표 첫 행(헤더)
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if nxt.lstrip().startswith("|") and "---" not in nxt:
                ncol = max(1, ln.count("|") - 1)
                out.append("|" + "|".join(["---"] * ncol) + "|")
    return "\n".join(out)


def _md_to_html(md: str) -> str:
    """리포트 마크다운 → HTML. ★데모스 개인 에이전트와 같은 변환기·확장(python-markdown).
    markdown 이 없는 환경에서만 아래 자체 변환기로 내려간다."""
    md = _ensure_table_blanklines(md)
    try:
        import markdown as _mdlib
        return _mdlib.markdown(md, extensions=[
            "tables", "fenced_code", "codehilite", "toc",
            "nl2br", "sane_lists", "smarty"])
    except Exception as e:
        print(f"[리포트] ⚠️ markdown 라이브러리 없음 — 자체 변환기 사용 ({e})")
        return _md_to_html_min(md)


def _md_to_html_min(md: str) -> str:
    """폴백 변환기 (헤딩·파이프 표·목록·강조만 — 외부 라이브러리 없이)."""
    import html as _h
    import re as _re

    def inline(t):
        t = _h.escape(t, quote=False)
        t = t.replace("&lt;br&gt;", "<br>")          # 표 셀 줄바꿈은 살린다
        t = _re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
        t = _re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
        return t

    out, tbl, ul = [], [], []

    def flush_tbl():
        if not tbl:
            return
        rows = [r for r in tbl if not _re.fullmatch(r"\s*\|[\s\-:|]+\|\s*", r)]
        cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
        if cells:
            out.append("<table><thead><tr>"
                       + "".join(f"<th>{inline(c)}</th>" for c in cells[0])
                       + "</tr></thead><tbody>")
            for row in cells[1:]:
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>")
            out.append("</tbody></table>")
        tbl.clear()

    def flush_ul():
        if not ul:
            return
        out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in ul) + "</ul>")
        ul.clear()

    for line in str(md or "").splitlines():
        ln = line.rstrip()
        if ln.lstrip().startswith("|"):
            flush_ul()
            tbl.append(ln)
            continue
        flush_tbl()
        m = _re.match(r"^(#{1,4})\s+(.*)$", ln)
        if m:
            flush_ul()
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            continue
        if _re.match(r"^\s*[-*]\s+", ln):
            ul.append(_re.sub(r"^\s*[-*]\s+", "", ln))
            continue
        flush_ul()
        if ln.strip():
            out.append(f"<p>{inline(ln)}</p>")
    flush_tbl()
    flush_ul()
    return "\n".join(out)


def _fallback_day_body(mat: dict) -> str:
    """LLM 실패·미사용 시의 본문 — ★골격은 LLM 성공 때와 완전히 같은 것을 쓴다.

    llm_client.assemble_day_report(mat, {}) 가 5섹션(제목·총평·AMOS 표·실제 이상
    발생내역 안내·상세·제안)을 통계만으로 채워 준다. 골격을 한 곳에서만 만들어
    LLM 유무에 따라 보고서 모양이 달라지지 않게 한다.
    """
    from llm_client import assemble_day_report
    return assemble_day_report(mat, {})


def _fallback_body(incidents: list[dict], summary: dict) -> str:
    """LLM 미사용/실패 시의 통계 기반 본문 (관제가 멈추면 안 되므로)."""
    if not incidents:
        return ("## 주요 발견\n"
                f"이 구간에 임계 {summary['alarm_floor']}점 이상 사건이 없었습니다 (정상 운영).\n\n"
                "## 다음 구간 예측 · 선제 조치 제안\n특이 추세 없음. 현행 감시 유지.\n")
    lines = ["## 주요 발견"]
    for i in incidents:
        lines.append(f"- {i['time']} {i['area']} {i['emoji']} {i['level']} {i['score']:.0f}점"
                     + (f" — {i['reason_kr']}" if i.get("reason_kr") else "")
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
    import argparse
    from datetime import timedelta

    ap = argparse.ArgumentParser(
        description="하루 사건 리포트 생성 (데모스 개인 에이전트 '사건발생 보고서' 와 같은 형식)")
    ap.add_argument("day", nargs="?", default=datetime.now().strftime("%Y%m%d"),
                    help="YYYYMMDD (기본 오늘)")
    ap.add_argument("--html", metavar="파일",
                    help="인터랙티브 HTML 로 저장 (체크박스 표·그래프·저장 툴바 포함)")
    ap.add_argument("--no-llm", action="store_true", help="LLM 없이 통계만")
    a = ap.parse_args()

    cfg = load_config()
    d = "".join(ch for ch in a.day if ch.isdigit())[:8]
    print(f"[리포트] {d} 하루 사건 리포트 생성 중…")
    rep = build_day_report(d, cfg, use_llm=not a.no_llm)

    sm = rep["summary"]
    print(f"  사건 {sm['count']}건 · 수집 {sm['minutes']}분 · 정체 {sm['risk_minutes']}분 "
          f"· 최고 {sm['top_emoji']} {sm['top_level']} {sm['top_score']:.0f}점")
    if rep.get("fetch_warn"):
        print(f"  ⚠️ {rep['fetch_warn']}")
    if rep.get("llm_error"):
        print(f"  ⚠️ LLM: {rep['llm_error']}  → 통계 요약으로 대체")
    print(f"  JSON: {rep['path']}")

    if a.html:
        html = day_report_html(rep, cfg)
        with open(a.html, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  HTML: {a.html}  ({len(html):,}자)  ← 브라우저로 열면 체크박스·그래프 동작")
    else:
        print()
        print(rep["body"])
