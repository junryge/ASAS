#!/usr/bin/env python3
"""
AMHS Sentinel_M16BR — 1분 단위 LLM 추론 + 사후검증 (독립)

수집 루프(1분)와 짝을 이룬다.

    로그프레소 조회 → AMOS 조인 → 20260729_TOTAL.CSV 1행 추가
                                        ↓
                              LLM 추론 (그 1분에 대해)
                                        ↓
                              20260729_LLM.CSV 1행 추가
                                        ↓
                     검증 창이 찬 과거 행 채점 → 같은 행에 판정 기록

채점은 LLM 을 다시 부르지 않는다. 저장된 TOTAL.CSV 의 분당 스코어만 읽어
'그 판단이 이후 데이터와 일치했는가' 를 본다.

  ★ 이 값은 '정탐률'이 아니라 '판단 일치율'이다.
    조치를 잘해서 빨리 회복된 케이스는 자동으로는 과다탐지로 보인다.
    그래서 운영자 조치 이력이 있으면 '조치효과'로 빼고 분모에서 제외하며,
    사람이 직접 눌러준 판정(source=human)이 있으면 그것으로 덮어쓴다.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta

from lp_client import load_config, parse_dt
from store_csv import read_day, read_llm_day, upsert_llm_rows

_busy = threading.Lock()          # 이전 추론이 안 끝났으면 그 분은 건너뛴다
STATE: dict = {"last_at": None, "last_ms": None, "skipped": 0,
               "calls": 0, "errors": 0, "last_error": None, "pending": 0}

# 자동 판정 종류 (사람 판정은 '정탐'/'오탐' 으로 따로 들어온다)
_HIT, _FP, _FN, _EFFECT, _WAIT = "적중", "과다탐지", "누락", "조치효과", ""


def pm_cfg(cfg: dict) -> dict:
    c = (cfg.get("llm", {}).get("per_minute") or {})
    return {
        "enabled": c.get("enabled", True),
        "every_min": int(c.get("every_min", 1) or 0),
        "light_below": float(c.get("light_below", 50)),
        "skip_if_busy": c.get("skip_if_busy", True),
        "max_per_cycle": int(c.get("max_per_cycle", 3) or 1),
        "backfill": c.get("backfill", True),
        "judge_max_chars": int(c.get("judge_max_chars", 200) or 200),
    }


def acc_cfg(cfg: dict) -> dict:
    c = (cfg.get("llm", {}).get("accuracy") or {})
    floor = c.get("floor")
    if floor is None:
        floor = min((b["min"] for b in cfg.get("grade", {}).get("bands", [])), default=50)
    return {
        "enabled": c.get("enabled", True),
        "window_min": int(c.get("window_min", 20)),
        "sustain_min": int(c.get("sustain_min", 5)),
        "recover_min": int(c.get("recover_min", 5)),
        "min_sample": int(c.get("min_sample", 10)),
        "floor": float(floor),
    }


def _f(v, d=0.0):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return d


# ────────────────────────────── 1분 추론 ──────────────────────────────
def judge_minute(row: dict, cfg: dict | None = None) -> dict:
    """그 1분 데이터에 대한 LLM 판단 → LLM.CSV 한 행.

    점수가 낮으면(정상 구간) 짧게, 경계 이상이면 지금까지처럼 자세히 묻는다.
    하루 1440번이라 정상 구간까지 길게 물으면 낭비다.
    """
    cfg = cfg or load_config()
    pm = pm_cfg(cfg)
    from sentinel import _score, grade, hid_zones, summarize_reason
    from llm_client import judge_snapshot

    sc = _score(row)
    g = grade(sc, cfg)
    area = (row.get("hot_area") or "").strip() or "UNKNOWN"
    light = sc < pm["light_below"]

    t0 = time.time()
    res, err = judge_snapshot(row, sc, g, area, light, cfg)
    ms = int((time.time() - t0) * 1000)

    cap = int(pm.get("judge_max_chars", 200) or 200)

    out = {
        "datetime": (row.get("datetime") or "").strip(),
        "스코어": f"{sc:.0f}", "등급": g["level"], "구역": area,
        "판정": _WAIT, "판정시각": "", "판정근거": "",
        "모델": cfg.get("llm", {}).get("model", ""),
        "추론깊이": "간단" if light else "상세",
        "소요ms": ms, "오류": (" ".join(str(err).split())[:cap] if err else ""),
    }
    if res:
        def txt(v, limit):
            """리스트는 ' / ' 로 합치고, 길면 자른다 (CSV·화면이 터지지 않게).

            ★문장 중간에서 뚝 끊지 않는다. 예전엔 그냥 limit 자에서 잘라
              "…반송시간이 6.3분까지 올" 처럼 말이 끊긴 채로 화면에 남았다.
              마침표 → 쉼표 → 띄어쓰기 순으로 물러나며 경계에서 자른다.
            """
            t = " / ".join(str(x).strip() for x in v if str(x).strip()) \
                if isinstance(v, list) else str(v or "").strip()
            t = " ".join(t.split())                 # 줄바꿈·중복공백 정리
            if len(t) <= limit:
                return t
            head = t[:limit]
            for seps in (".!?", ",;/·", " "):
                cut = max((head.rfind(ch) for ch in seps), default=-1)
                if cut >= limit * 0.6:              # 너무 짧아지면 그 경계는 버린다
                    return head[:cut + 1].rstrip(" ,;/·") + "…"
            return head.rstrip() + "…"

        # '판단' 은 사람이 읽는 본문이라 근거·조치보다 여유를 준다.
        # (프롬프트는 160자로 부탁하므로 보통은 잘릴 일이 없다 — 이건 안전망이다)
        jcap = int(pm.get("judge_text_max_chars", max(cap, 260)) or 260)
        out.update({
            "실제이상": (res.get("실제이상") or "").strip(),
            "확신도": res.get("확신도", ""),
            "판단": txt(res.get("판단"), jcap),
            "근거": txt(res.get("근거"), cap),
            "조치": txt(res.get("조치"), cap),
        })
    else:
        out.update({"실제이상": "", "확신도": "", "판단": "", "근거": "", "조치": ""})
    return out


def run_minute(rows: list[dict], cfg: dict | None = None) -> dict | None:
    """아직 판단 안 한 분들을 추론해 LLM.CSV 에 남긴다.

    '가장 최근 1분만' 하면 폴링이 한 번 밀리는 순간 그 사이 분이 영구히 빈다.
    그래서 **최신 분을 먼저** 처리하고(실시간이 최우선), 남은 자리로 **최근 과거부터
    거꾸로 메운다**. 한 번에 처리할 개수는 max_per_cycle 로 묶어 게이트웨이를
    한꺼번에 때리지 않게 한다.

    이전 추론이 안 끝났으면 건너뛴다 (수집 루프는 절대 밀리면 안 된다).
    """
    cfg = cfg or load_config()
    pm = pm_cfg(cfg)
    if not (pm["enabled"] and pm["every_min"] > 0) or not rows:
        return None

    from store_csv import llm_minutes

    # 판단 대상 후보 — 시각 있고, every_min 주기에 맞고, 아직 안 한 분
    cand = []
    done_by_day: dict[str, set] = {}
    for r in rows:
        dt = parse_dt(r.get("datetime"))
        key = (r.get("datetime") or "").strip()
        if dt is None or not key:
            continue
        if pm["every_min"] > 1 and dt.minute % pm["every_min"] != 0:
            continue
        day = dt.strftime("%Y%m%d")
        if day not in done_by_day:
            done_by_day[day] = llm_minutes(day, cfg)
        if key in done_by_day[day]:
            continue
        cand.append((dt, r))
    if not cand:
        return None

    cand.sort(key=lambda x: x[0])
    cap = max(1, pm["max_per_cycle"])
    newest = cand[-1]
    older = list(reversed(cand[:-1])) if pm["backfill"] else []
    batch = [newest] + older[:cap - 1]                 # 최신 먼저, 그 다음 최근 과거부터

    if not _busy.acquire(blocking=not pm["skip_if_busy"]):
        STATE["skipped"] += 1
        upsert_llm_rows([{"datetime": (newest[1].get("datetime") or "").strip(),
                          "스코어": f"{_f(newest[1].get('unified_risk_score')):.0f}",
                          "오류": "지연스킵"}], cfg)
        return None
    try:
        first = None
        for _dt, row in batch:
            out = judge_minute(row, cfg)
            upsert_llm_rows([out], cfg)
            STATE.update(last_at=datetime.now().isoformat(), last_ms=out["소요ms"],
                         calls=STATE["calls"] + 1)
            if out["오류"]:
                STATE.update(errors=STATE["errors"] + 1, last_error=out["오류"])
            if first is None:
                first = out
        STATE["pending"] = max(0, len(cand) - len(batch))
        return first
    finally:
        _busy.release()


def backlog(rows: list[dict], cfg: dict | None = None) -> int:
    """아직 판단 안 한 분이 몇 개 남았는지 (화면 안내용)."""
    cfg = cfg or load_config()
    from store_csv import llm_minutes
    done_by_day: dict[str, set] = {}
    n = 0
    for r in rows or []:
        dt = parse_dt(r.get("datetime"))
        key = (r.get("datetime") or "").strip()
        if dt is None or not key:
            continue
        day = dt.strftime("%Y%m%d")
        if day not in done_by_day:
            done_by_day[day] = llm_minutes(day, cfg)
        if key not in done_by_day[day]:
            n += 1
    return n


# ────────────────────────────── 사후검증 ──────────────────────────────
def _series(day: str, cfg: dict) -> list[tuple[datetime, float]]:
    out = []
    for r in read_day(day, cfg):
        t = parse_dt(r.get("datetime"))
        if t:
            out.append((t, _f(r.get("unified_risk_score"))))
    out.sort(key=lambda x: x[0])
    return out


def _verdict(t0: datetime, said_yes: bool, series, a: dict, acted: bool) -> tuple[str, str]:
    """판단 시각 t0 이후 창 안의 실제 흐름으로 채점."""
    win = [(t, v) for t, v in series if t0 < t <= t0 + timedelta(minutes=a["window_min"])]
    if not win:
        return _WAIT, ""
    floor = a["floor"]
    over = [v >= floor for _, v in win]

    # 연속 유지 최대 길이
    run = best = 0
    for x in over:
        run = run + 1 if x else 0
        best = max(best, run)
    peak = max(v for _, v in win)
    head = win[:a["recover_min"]]                      # 판단 직후 구간
    recovered = bool(head) and all(v < floor for _, v in head)

    if said_yes:
        if best >= a["sustain_min"]:
            return _HIT, f"이후 {best}분 연속 {floor:.0f}점 이상 유지 · 최고 {peak:.0f}점"
        if acted:
            return _EFFECT, f"운영자 조치 이력 있음 · {a['recover_min']}분 내 회복 (최고 {peak:.0f}점)"
        if recovered:
            return _FP, f"{a['recover_min']}분 내 {floor:.0f}점 아래로 회복 · 최고 {peak:.0f}점"
        return _HIT, f"창 안 최고 {peak:.0f}점 · 유지 {best}분"
    # 아니오 라고 했을 때
    if best >= a["sustain_min"]:
        return _FN, f"이후 {best}분 연속 {floor:.0f}점 이상 · 최고 {peak:.0f}점"
    return _HIT, f"창 안 최고 {peak:.0f}점 — 계속 {floor:.0f}점 아래"


def verify_day(day: str, cfg: dict | None = None) -> dict:
    """검증 창이 찬 행을 채점해 LLM.CSV 에 판정을 채운다."""
    cfg = cfg or load_config()
    a = acc_cfg(cfg)
    if not a["enabled"]:
        return {"scored": 0, "waiting": 0}

    rows = read_llm_day(day, cfg)
    if not rows:
        return {"scored": 0, "waiting": 0}
    series = _series(day, cfg)
    acted = _acted_minutes(day, cfg)
    now = datetime.now()

    upd, waiting = [], 0
    for r in rows:
        if (r.get("판정") or "").strip():
            continue                                   # 이미 판정됨(사람 포함)
        said = (r.get("실제이상") or "").strip()
        t0 = parse_dt(r.get("datetime"))
        if t0 is None:
            continue
        if said not in ("예", "아니오"):
            # 채점 대상이 아니다. 창이 지났으면 왜 못 하는지 못박는다
            # (그냥 넘기면 영구히 '대기' 로 남아 고장처럼 보인다)
            if now >= t0 + timedelta(minutes=a["window_min"]):
                why = ("LLM 호출 실패 — " + (r.get("오류") or "").strip()[:80]) \
                    if (r.get("오류") or "").strip() \
                    else "LLM 이 '실제이상'을 예/아니오로 답하지 않아 채점 불가"
                upd.append({"datetime": r["datetime"], "판정": "판정불가",
                            "판정시각": now.strftime("%Y-%m-%d %H:%M"), "판정근거": why})
            continue
        if now < t0 + timedelta(minutes=a["window_min"]):
            waiting += 1
            continue                                   # 창이 아직 안 참
        v, why = _verdict(t0, said == "예", series, a,
                          acted=any(t0 < t <= t0 + timedelta(minutes=a["window_min"])
                                    for t in acted))
        if not v:
            # 창은 지났는데 그 구간 데이터가 없다 (수집 공백 등) — 영구 대기로 남지 않게 못박는다
            upd.append({"datetime": r["datetime"], "판정": "판정불가",
                        "판정시각": now.strftime("%Y-%m-%d %H:%M"),
                        "판정근거": f"검증 창({a['window_min']}분) 안에 수집된 데이터가 없음"})
            continue
        upd.append({"datetime": r["datetime"], "판정": v,
                    "판정시각": now.strftime("%Y-%m-%d %H:%M"), "판정근거": why})
    if upd:
        upsert_llm_rows(upd, cfg)
    return {"scored": len(upd), "waiting": waiting}


def _acted_minutes(day: str, cfg: dict) -> set:
    """운영자 조치가 있었던 분 — 조치로 회복된 걸 과다탐지로 세지 않기 위해."""
    out = set()
    for r in read_day(day, cfg):
        mx = (r.get("maxcapa_change") or r.get("operator_action") or "").strip()
        if mx and mx not in ("0", "-", "없음"):
            t = parse_dt(r.get("datetime"))
            if t:
                out.add(t)
    return out


# ────────────────────────────── 집계 ──────────────────────────────
def summary(day: str | None = None, cfg: dict | None = None) -> dict:
    """화면 KPI 용 집계. 퍼센트는 표본이 찼을 때만 준다."""
    cfg = cfg or load_config()
    a = acc_cfg(cfg)
    day = day or datetime.now().strftime("%Y%m%d")
    rows = read_llm_day(day, cfg)

    cnt = {_HIT: 0, _FP: 0, _FN: 0, _EFFECT: 0, "판정불가": 0}
    human = {"정탐": 0, "오탐": 0}
    waiting = judged_fail = 0
    now = datetime.now()
    for r in rows:
        v = (r.get("판정") or "").strip()
        if v in cnt:
            cnt[v] += 1
        elif v in human:
            human[v] += 1
        elif (r.get("실제이상") or "").strip() in ("예", "아니오"):
            waiting += 1
        elif (r.get("오류") or "").strip():
            judged_fail += 1

    # 분모에서 '조치효과' 는 뺀다 (잘 잡았는데 조치로 풀린 건 오탐이 아니다)
    base = cnt[_HIT] + cnt[_FP] + cnt[_FN]
    rate = round(100 * cnt[_HIT] / base, 1) if base >= a["min_sample"] else None
    hbase = human["정탐"] + human["오탐"]
    hrate = round(100 * human["정탐"] / hbase, 1) if hbase else None

    # 확신도 평균 + 가장 최근 판단 (화면에 바로 보여주기 위해)
    confs = []
    latest = None
    for r in rows:
        c = r.get("확신도")
        try:
            if str(c).strip() != "":
                confs.append(max(0, min(100, int(float(c)))))
        except (TypeError, ValueError):
            pass
        # 실제 판단이 있는 행을 우선한다 (오류 행만 있으면 그거라도)
        has_j = bool((r.get("판단") or "").strip())
        has_e = bool((r.get("오류") or "").strip())
        if has_j or has_e:
            cur_j = bool((latest or {}).get("판단", "").strip()) if latest else False
            newer = latest is None or (r.get("datetime") or "") > (latest.get("datetime") or "")
            if latest is None or (has_j and not cur_j) or (has_j == cur_j and newer):
                latest = r
    conf_avg = round(sum(confs) / len(confs), 1) if confs else None

    return {
        "day": day, "rows": len(rows),
        "conf_avg": conf_avg, "conf_n": len(confs),
        "latest": ({"datetime": latest.get("datetime"), "스코어": latest.get("스코어"),
                    "등급": latest.get("등급"), "실제이상": latest.get("실제이상"),
                    "확신도": latest.get("확신도"), "판단": latest.get("판단"),
                    "근거": latest.get("근거"), "조치": latest.get("조치"),
                    "판정": latest.get("판정"), "오류": latest.get("오류")}
                   if latest else None),
        "hit": cnt[_HIT], "fp": cnt[_FP], "fn": cnt[_FN], "effect": cnt[_EFFECT],
        "nojudge": cnt["판정불가"],
        "waiting": waiting, "failed": judged_fail,
        "base": base, "min_sample": a["min_sample"],
        "match_rate": rate,                 # 자동 — 판단 일치율
        "human_ok": human["정탐"], "human_ng": human["오탐"], "human_rate": hrate,
        "window_min": a["window_min"], "sustain_min": a["sustain_min"],
        "state": dict(STATE),
    }


def set_human(day: str, dt_key: str, verdict: str, cfg: dict | None = None) -> bool:
    """운영자가 직접 누른 판정 — 자동 판정을 덮어쓴다."""
    if verdict not in ("정탐", "오탐"):
        return False
    upsert_llm_rows([{"datetime": dt_key, "판정": verdict,
                      "판정시각": datetime.now().strftime("%Y-%m-%d %H:%M"),
                      "판정근거": "운영자 확인"}], cfg)
    return True


def backfill_day(day: str, cfg: dict | None = None, limit: int = 0,
                 verbose: bool = True) -> dict:
    """그 날 TOTAL.CSV 에 있는데 아직 판단 안 한 분을 통째로 메운다.

    폴링은 최근 구간만 본다. 서버를 늦게 켰거나 오래 꺼져 있던 구간은
    이걸로 채운다. LLM 을 그만큼 부르므로 필요할 때만 쓴다.

        python accuracy.py --backfill 20260729
        python accuracy.py --backfill 20260729 --limit 100
    """
    cfg = cfg or load_config()
    pm = pm_cfg(cfg)
    from store_csv import llm_minutes
    rows = read_day(day, cfg)
    done = llm_minutes(day, cfg)

    todo = []
    for r in rows:
        dt = parse_dt(r.get("datetime"))
        key = (r.get("datetime") or "").strip()
        if dt is None or not key or key in done:
            continue
        if pm["every_min"] > 1 and dt.minute % pm["every_min"] != 0:
            continue
        todo.append((dt, r))
    todo.sort(key=lambda x: x[0])
    if limit > 0:
        todo = todo[:limit]

    if verbose:
        print(f"[메움] {day} — 수집 {len(rows)}분 · 이미 판단 {len(done)}분 · "
              f"이번에 판단 {len(todo)}분")
    ok = err = 0
    for i, (dt, r) in enumerate(todo, 1):
        out = judge_minute(r, cfg)
        upsert_llm_rows([out], cfg)
        if out["오류"]:
            err += 1
            if verbose and err <= 3:
                print(f"  ⚠️ {out['datetime']} — {out['오류']}")
        else:
            ok += 1
        if verbose and (i % 20 == 0 or i == len(todo)):
            print(f"  {i}/{len(todo)}  성공 {ok} · 실패 {err}")
    v = verify_day(day, cfg)
    if verbose:
        print(f"[메움] 끝 — 성공 {ok} · 실패 {err} · 채점 {v['scored']}건 (대기 {v['waiting']})")
    return {"day": day, "todo": len(todo), "ok": ok, "error": err, **v}


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="1분 LLM 추론 채점 / 빈 구간 메움")
    ap.add_argument("day", nargs="?", default=datetime.now().strftime("%Y%m%d"),
                    help="YYYYMMDD (기본 오늘)")
    ap.add_argument("--backfill", action="store_true",
                    help="아직 판단 안 한 분을 LLM 으로 통째로 메운다")
    ap.add_argument("--limit", type=int, default=0, help="메움 개수 제한 (0=전부)")
    a = ap.parse_args()

    cfg = load_config()
    d = "".join(ch for ch in a.day if ch.isdigit())[:8]
    if a.backfill:
        backfill_day(d, cfg, a.limit)
    else:
        print(json.dumps(verify_day(d, cfg), ensure_ascii=False))
    print(json.dumps(summary(d, cfg), ensure_ascii=False, indent=2))
