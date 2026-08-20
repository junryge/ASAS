#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evaluate.py — 심각 정체 사건 단위 채점
=======================================
detect.py 결과(액션 CSV)를 실제 '심각 정체 사건'과 대조한다.

정답(ground truth): data.find_events()
    이동평균 ≥ 임계 AND 지속 ≥ min_duration  (블립 제외 = 큰 것만)

산출
  · recall     : 심각 사건 중 몇 % 를 잡았나 (놓치면 안 되는 것)
  · precision  : 경보 중 몇 % 가 진짜였나 (헛울림)
  · lead 분포  : ≥10분 / 5~9분 / <5분  ← '10분 전 예측' 달성도
  · 사건별 표  : 언제·몇 분 전·왜 (엑셀 보고용)
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta

from data import (load, moving_avg, learn_threshold, find_events,
                  TARGET, TIME_COL)


def read_actions(path):
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            try:
                t = datetime.strptime(r["datetime"], "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            rows.append({
                "t": t,
                "stage": int(r.get("stage", 0) or 0),
                "prob": float(r.get("prob", 0) or 0),
                "lead": r.get("lead_min", ""),
                "kind": r.get("kind", ""),
                "why": r.get("reason", ""),
            })
    rows.sort(key=lambda x: x["t"])
    return rows


def alarm_spans(actions, min_stage=2, gap=10):
    """경보(stage≥min_stage) 구간을 gap분 병합해 에피소드로."""
    spans, st, prev = [], None, None
    for a in actions:
        if a["stage"] >= min_stage:
            if st is None:
                st = a["t"]
            prev = a["t"]
        elif st is not None and prev and (a["t"] - prev) > timedelta(minutes=gap):
            spans.append((st, prev)); st = None
    if st is not None:
        spans.append((st, prev))
    return spans


def evaluate(events, spans, actions, pre=20):
    """
    사건 ↔ 경보 매칭.
    경보구간이 [사건시작-pre, 사건종료] 와 겹치면 감지로 인정.
    lead = 사건시작 - 가장 이른 경보시작.
    """
    pre_td = timedelta(minutes=pre)
    amap = {a["t"]: a for a in actions}

    def overlaps(s, e, ev):
        return s <= ev.t_end and e >= (ev.t_start - pre_td)

    detail, leads, matched = [], [], set()
    for i, ev in enumerate(events, 1):
        hits = [(s, e) for (s, e) in spans if overlaps(s, e, ev)]
        if hits:
            first = min(h[0] for h in hits)
            for h in hits:
                matched.add(h)
            lead = max(0, round((ev.t_start - first).total_seconds() / 60))
            leads.append(lead)
            a = amap.get(first, {})
            detail.append(["감지", i, ev, first, lead, a.get("why", ""),
                           a.get("prob", "")])
        else:
            detail.append(["놓침", i, ev, None, None, "", ""])

    false = []
    for (s, e) in spans:
        if (s, e) in matched:
            continue
        if any(overlaps(s, e, ev) for ev in events):
            continue
        a = amap.get(s, {})
        false.append((s, e, a.get("why", ""), a.get("prob", "")))

    n = len(events)
    caught = sum(1 for d in detail if d[0] == "감지")
    n_al = len(spans)
    return {
        "events": n, "caught": caught, "missed": n - caught,
        "alarms": n_al, "false": len(false),
        "recall": caught / n if n else 0,
        "precision": (n_al - len(false)) / n_al if n_al else 0,
        "mean_lead": round(sum(leads) / len(leads), 1) if leads else None,
        "lead10": sum(1 for l in leads if l >= 10),
        "lead5": sum(1 for l in leads if 5 <= l < 10),
        "lead0": sum(1 for l in leads if l < 5),
        "detail": detail, "false_list": false, "leads": leads,
    }


def print_report(r, label, days=None):
    print("=" * 72)
    print(f" 채점 — {label}")
    print("=" * 72)
    print(f" 심각 정체 사건 : {r['events']}건")
    print(f"   └ 감지        : {r['caught']}건")
    print(f"   └ 놓침        : {r['missed']}건")
    print(f" 경보 에피소드   : {r['alarms']}건  (헛울림 {r['false']}건"
          + (f", 하루 {r['false']/days:.1f}건)" if days else ")"))
    print("-" * 72)
    print(f" Recall    : {r['recall']:.0%}   ← 심각 정체를 얼마나 잡나")
    print(f" Precision : {r['precision']:.0%}   ← 경보가 얼마나 맞나")
    print(f" 평균 lead : {r['mean_lead']}분")
    print("-" * 72)
    print(f" ★ lead 분포 (감지 {r['caught']}건 중)")
    print(f"    ≥10분 전 : {r['lead10']}건   ← '10분 전 예측' 성공")
    print(f"    5~9분 전 : {r['lead5']}건")
    print(f"    <5분 전  : {r['lead0']}건")
    print("=" * 72)


def save_report(r, path, label):
    with open(path, "w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow([f"# {label} | 심각사건 {r['events']} | 감지 {r['caught']} "
                    f"(recall {r['recall']:.0%}) | ≥10분전 {r['lead10']}건 | "
                    f"평균lead {r['mean_lead']}분 | 헛울림 {r['false']}건"])
        w.writerow(["구분", "사건#", "정체시작", "정체종료", "지속(분)",
                    "이동평균피크", "순간최고", "감지시각", "lead(분)",
                    "lead구간", "확률", "사유"])
        for kind, i, ev, first, lead, why, prob in r["detail"]:
            band = ("" if lead is None else
                    "≥10분" if lead >= 10 else "5~9분" if lead >= 5 else "<5분")
            w.writerow([kind, i, ev.t_start.strftime("%m-%d %H:%M"),
                        ev.t_end.strftime("%H:%M"), ev.duration,
                        round(ev.peak_smoothed, 1), round(ev.peak_raw, 1),
                        first.strftime("%m-%d %H:%M") if first else "",
                        "" if lead is None else lead, band or "놓침",
                        prob, why])
        for s, e, why, prob in r["false_list"]:
            w.writerow(["헛울림", "", s.strftime("%m-%d %H:%M"),
                        e.strftime("%H:%M"), "", "", "",
                        s.strftime("%m-%d %H:%M"), "", "헛울림", prob, why])


def main():
    ap = argparse.ArgumentParser(description="심각 정체 채점")
    ap.add_argument("--actions", required=True)
    ap.add_argument("--data", required=True, nargs="+")
    ap.add_argument("--config", default=None,
                    help="학습 결과(model_config.json) — 임계·창·지속조건 재사용")
    ap.add_argument("--threshold", type=float, default=None)
    ap.add_argument("--train", nargs="+", default=None)
    ap.add_argument("--pct", type=float, default=0.99)
    ap.add_argument("--window", type=int, default=10)
    ap.add_argument("--min-duration", type=int, default=10)
    ap.add_argument("--gap", type=int, default=10)
    ap.add_argument("--pre", type=int, default=20)
    ap.add_argument("--label", default="Chronos-2 이동평균 예측")
    ap.add_argument("--out", default=None, help="사건별 표 CSV 저장")
    a = ap.parse_args()

    # 학습 결과 재사용 — 채점도 학습과 같은 정의를 써야 지표가 일관됨
    if a.config:
        from data import load_config
        cfg = load_config(a.config)
        if a.threshold is None:
            a.threshold = cfg["threshold"]
        if ap.get_default("window") == a.window:
            a.window = cfg.get("window", a.window)
        if ap.get_default("min_duration") == a.min_duration:
            a.min_duration = cfg.get("min_duration", a.min_duration)

    sd = load(a.data, [TARGET, TIME_COL])
    sm = moving_avg(sd.filled(TARGET), a.window)
    if a.threshold is not None:
        thr = a.threshold
    elif a.train:
        tr = load(a.train, [TARGET, TIME_COL])
        thr = learn_threshold(moving_avg(tr.filled(TARGET), a.window), a.pct)
    else:
        thr = learn_threshold(sm, a.pct)

    events = find_events(sd.times, sm, sd.get(TARGET), thr,
                         a.min_duration, a.gap)
    actions = read_actions(a.actions)
    spans = alarm_spans(actions, 2, a.gap)
    r = evaluate(events, spans, actions, a.pre)

    days = max(1, (sd.times[-1] - sd.times[0]).days + 1)
    print(f"임계 {thr} | {a.window}분평균 | 지속 {a.min_duration}분+ | {days}일")
    print_report(r, a.label, days)
    if a.out:
        save_report(r, a.out, a.label)
        print(f"사건별 표 저장: {a.out}")


if __name__ == "__main__":
    main()
