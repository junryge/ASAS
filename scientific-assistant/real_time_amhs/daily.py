#!/usr/bin/env python3
"""
AMHS Sentinel_M16BR — 하루 사건 리포트 자료 (독립)

데모스 개인 에이전트의 '사건발생 보고서' 와 **같은 자료**를 만든다.
`m16_hub_skills/발동이벤트_요약.py` 의 ③ 사건목록 · ④ AMOS 이상감지 표를
저장된 날짜 CSV 에서 그대로 재현한다 (스킬을 import 하지 않고 같은 규칙만 따른다).

  ③ 이벤트목록    임계(경계 시작점) 이상 구간을 이벤트로 (간격 60분), 시각 = 최고점 시각
  ④ AMOS 이상감지 사건 구간의 HID 구간 + 심각도 + 발동 지표(raw 컬럼)

이 두 표가 리포트 프롬프트의 유일한 근거다. 페르소나가 요구하는 5섹션 형식은
스킬(페르소나_통합.txt)에 이미 있으므로 여기서 다시 쓰지 않는다.
"""
from __future__ import annotations

import re

from lp_client import load_config, parse_dt

# 등급 → 심각도 표기 (스킬과 동일)
_SEV = {"경계": "경계/주의(확인필요)",
        "위험": "위험/경고(모니터링 필요)",
        "초위험": "초위험/심각(조치필요)"}

GAP_MIN = 60                         # 스킬과 동일 — 간격 60분
MIN_SCORE = 60                       # 폴백 기본값. 실제로는 아래 _floor() 가
                                     # config(정책 탭에서 시스템별로 저장)를 읽는다.


def _floor(cfg: dict | None = None) -> int:
    """이벤트 판정 임계 — **이 시스템의** 경계 시작점.

    ★상수로 박아 두면 안 된다. 경계 하한을 50→60 으로 올렸을 때 여기가
      50 인 채로 남아, 화면 등급은 60 기준인데 이벤트 목록·일일통계는
      50 기준으로 세는 상태가 됐다 (LLM 프롬프트에도 그대로 들어갔다).
    """
    try:
        from sentinel import grade_cuts
        return grade_cuts(cfg)[0]
    except Exception:
        return MIN_SCORE


def _minutes(rows: list[dict], cfg: dict) -> list[dict]:
    """날짜 CSV → 분 단위 레코드 (시각·점수·등급·구역·reason·AMOS 4컬럼)."""
    from sentinel import _score, grade

    out = []
    for r in rows:
        dt = parse_dt(r.get("datetime"))
        if dt is None:
            continue
        sc = _score(r)
        g = grade(sc, cfg)
        out.append({
            "dt": dt, "time": dt.strftime("%H:%M"), "score": sc,
            "level": g["level"], "emoji": g["emoji"],
            "hot_area": (r.get("hot_area") or "").strip() or "UNKNOWN",
            "reason": (r.get("reason") or "").strip(),
            "chain": (r.get("propagation_chain") or "").strip(),
            "bott": " ".join(x for x in (
                (r.get("BOTTLENECK_downward_anomaly_cols") or "").strip(),
                (r.get("BOTTLENECK_upward_anomaly_cols") or "").strip()) if x),
            "queue": " ".join(x for x in (
                (r.get("QUEUE_downward_anomaly_cols") or "").strip(),
                (r.get("QUEUE_upward_anomaly_cols") or "").strip()) if x),
        })
    out.sort(key=lambda m: m["dt"])
    return out


def incidents(mins: list[dict], cfg: dict | None = None) -> list[dict]:
    """③ 이벤트 목록 — 임계 이상 구간을 이벤트로 묶는다 (간격 60분).

    시각은 구간의 **최고점 시각**이다 (스킬·predictor 와 동일).
    임계는 그 시스템의 경계 시작점 (정책 탭에서 FAB 마다 다르게 잡는다).
    """
    floor = _floor(cfg)
    incs, cur = [], None
    for m in mins:
        alarm = m["score"] >= floor
        if cur is None:
            if alarm:
                cur = {"s": m, "e": m, "last": m["dt"], "peak": m}
        elif alarm:
            cur["e"] = m
            cur["last"] = m["dt"]
            if m["score"] > cur["peak"]["score"]:
                cur["peak"] = m
        elif (m["dt"] - cur["last"]).total_seconds() / 60.0 >= GAP_MIN:
            incs.append(cur)
            cur = None
    if cur:
        incs.append(cur)
    return [c for c in incs if c["peak"]["score"] >= floor]


def incident_rows(incs: list[dict]) -> list[dict]:
    out = []
    for i, c in enumerate(incs, 1):
        pk = c["peak"]
        dur = int((c["e"]["dt"] - c["s"]["dt"]).total_seconds() / 60) + 1
        out.append({
            "번호": i,
            "시각": pk["time"],
            "구간": f'{c["s"]["time"]}~{c["e"]["time"]}',
            "지속분": dur,
            "최고등급": pk["level"],
            "최고점수": int(pk["score"]),
            "시작영역": pk["hot_area"],
            "발동사유": pk["reason"],
        })
    return out


def amos_rows(incs: list[dict], mins: list[dict]) -> list[dict]:
    """④ AMOS 이상감지 — 사건 구간의 HID 구간 + 심각도 + 발동 지표(raw 컬럼)."""
    from graphs import parse_reason_metrics
    from sentinel import hid_zones

    out = []
    for i, c in enumerate(incs, 1):
        w0, w1 = c["s"]["dt"], c["e"]["dt"]
        bott, queue = [], []
        for m in mins:
            if w0 <= m["dt"] <= w1:
                if m["bott"]:
                    bott.append(m["bott"])
                if m["queue"]:
                    queue.append(m["queue"])
        zones = hid_zones(" ".join(bott))

        items, seen = [], set()
        for md in parse_reason_metrics(c["peak"]["reason"]):
            raw = md["raw"]
            if raw not in seen:
                seen.add(raw)
                items.append(raw)
        for q in " ".join(queue).replace(",", " ").split():
            base = re.sub(r"_[A-Z]$", "", q.strip())
            if base and base not in seen:
                seen.add(base)
                items.append(base)

        pk = c["peak"]
        # 구간이 길면 4개마다 줄바꿈 (스킬과 동일 — 표 셀 가독성)
        zone_str = "<br>".join(", ".join(zones[k:k + 4])
                               for k in range(0, len(zones), 4)) if zones else "-"
        out.append({
            "번호": i,
            "이상감지 시간": pk["time"],
            "이상감지 구간": zone_str,
            "심각도": _SEV.get(pk["level"], "경계/주의(확인필요)"),
            "이상감지 항목": "<br>".join(items) if items else "-",
        })
    return out


def day_material(day: str, cfg: dict | None = None) -> dict:
    """하루치 리포트 자료 — ③ 사건목록 + ④ AMOS 표 + 하루 통계.

    저장된 `data/YYYYMMDD_TOTAL.CSV` 를 읽는다. 없으면 rows 0 으로 돌려주고
    호출부(리포트)가 로그프레소 재조회를 판단한다.
    """
    cfg = cfg or load_config()
    from store_csv import read_day

    day = "".join(ch for ch in str(day) if ch.isdigit())[:8]
    rows = read_day(day, cfg)
    mins = _minutes(rows, cfg)
    incs = incidents(mins, cfg)

    lv = {}
    for m in mins:
        lv[m["level"]] = lv.get(m["level"], 0) + 1
    peak = max(mins, key=lambda m: m["score"], default=None)
    floor = _floor(cfg)
    risk_min = sum(1 for m in mins if m["score"] >= floor)

    # 정체 집중 시간대 (시간별 임계 이상 분수)
    by_hour: dict[int, int] = {}
    for m in mins:
        if m["score"] >= floor:
            by_hour[m["dt"].hour] = by_hour.get(m["dt"].hour, 0) + 1
    busy = ", ".join(f"{h:02d}시 {n}분" for h, n in
                     sorted(by_hour.items(), key=lambda x: -x[1])[:5]) or "없음"

    return {
        "day": day,
        "date_ko": f"{day[:4]}년 {int(day[4:6])}월 {int(day[6:8])}일" if len(day) == 8 else day,
        "minutes": len(mins),
        "risk_minutes": risk_min,
        "by_level": lv,
        "peak": ({"time": peak["time"], "score": int(peak["score"]),
                  "level": peak["level"], "emoji": peak["emoji"],
                  "area": peak["hot_area"]} if peak else None),
        "busy": busy,
        "incidents": incident_rows(incs),
        "amos": amos_rows(incs, mins),
        "_incs": incs,
        "_mins": mins,
    }


if __name__ == "__main__":
    import json
    import sys
    from datetime import datetime

    cfg = load_config()
    d = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d")
    m = day_material(d, cfg)
    print(f"[{m['date_ko']}] 총 {m['minutes']}분 · 임계↑ {m['risk_minutes']}분 · "
          f"사건 {len(m['incidents'])}건")
    if m["peak"]:
        p = m["peak"]
        print(f"  하루 최고: {p['time']} {p['emoji']} {p['level']} {p['score']}점 ({p['area']})")
    print(f"  정체집중: {m['busy']}")
    print()
    print("③ 사건목록")
    for r in m["incidents"]:
        print(f"  {r['번호']}. {r['시각']}  {r['구간']}  {r['지속분']}분  "
              f"{r['최고등급']} {r['최고점수']}점  {r['시작영역']}")
    print()
    print("④ AMOS 이상감지")
    for r in m["amos"]:
        print(f"  {r['번호']}. {r['이상감지 시간']}  {r['심각도']}")
        print(f"     구간: {r['이상감지 구간'].replace('<br>', ' / ')}")
        print(f"     항목: {r['이상감지 항목'].replace('<br>', ' / ')}")
