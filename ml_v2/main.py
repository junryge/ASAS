#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py — 학습 → 감지 → 채점 한 번에
=====================================
    python main.py all --train "RAW_APRMAY/*.CSV" --eval "RAW6/*.CSV" \
                       --model chronos_2 --device cuda

개별 단계는 각 모듈 CLI 로도 실행 가능:
    python data.py     --data ...      # 사건 구조 확인
    python detect.py   --data ...      # 감지 → 액션 CSV
    python evaluate.py --actions ...   # 채점
"""
from __future__ import annotations

import argparse
import os

from data import (load, moving_avg, learn_threshold, find_events,
                  learn as D_learn, save_config, load_config,
                  TARGET, TIME_COL)
import detect as D
import evaluate as E


def _print_learned(cfg):
    print(f"   기간   : {cfg['train_span']}  ({cfg['train_rows']}분 / {cfg['train_days']}일)")
    print(f"   임계   : {cfg['threshold']}   ({cfg['window']}분 이동평균 "
          f"p{cfg['pct']*100:.1f})")
    print(f"   분포   : p50 {cfg['smoothed_p50']} · p95 {cfg['smoothed_p95']} "
          f"· p99 {cfg['smoothed_p99']} · max {cfg['smoothed_max']}")
    print(f"   심각사건: {cfg['train_events']}건 (월 {cfg['train_events_per_month']}건) "
          f"· 평균 {cfg['train_event_mean_duration']}분 · 최장 "
          f"{cfg['train_event_max_duration']}분")


def cmd_learn(a):
    """학습만 — 4~7월 등 긴 기간에서 판정 기준을 뽑아 파일로 저장(재사용)."""
    print("=" * 72)
    print("[학습] 판정 기준 산출  (Chronos-2 는 zero-shot — 가중치 학습 없음)")
    cfg = D_learn(a.train, a.window, a.pct, a.min_duration, a.gap)
    _print_learned(cfg)
    save_config(cfg, a.out_config)
    print("=" * 72)
    print(f"저장: {a.out_config}   ← 이후 --config {a.out_config} 로 재사용")


def cmd_all(a):
    # 1) 학습 — 임계는 학습기간에서만 (leakage 방지). 있으면 config 재사용.
    print("=" * 72)
    if a.config:
        cfg = load_config(a.config)
        print(f"[1/3 학습] 저장된 학습 결과 재사용: {a.config}")
    else:
        print("[1/3 학습] 판정 기준 산출")
        cfg = D_learn(a.train, a.window, a.pct, a.min_duration, a.gap)
        save_config(cfg, a.out_config)
    _print_learned(cfg)
    thr = cfg["threshold"]
    a.window = cfg["window"]
    a.min_duration = cfg["min_duration"]

    # 2) 감지 — 평가기간에 예측
    ev = load(a.eval, [TARGET, TIME_COL])
    print("=" * 72)
    print(f"[2/3 감지] {len(ev)}분  {ev.times[0]:%Y-%m-%d} ~ {ev.times[-1]:%Y-%m-%d}")
    rows, backend = D.run(ev, thr, a.window, a.horizon, a.context,
                          a.p_on, a.p_off, a.stride, a.model, a.device,
                          verbose=True, batch=a.batch)
    acts = a.out_actions or "actions.csv"
    D.save(rows, acts)
    print(f"   액션 저장: {acts}")

    # 3) 채점 — 같은 정의로
    ev_sm = moving_avg(ev.filled(TARGET), a.window)
    events = find_events(ev.times, ev_sm, ev.get(TARGET), thr,
                         a.min_duration, a.gap)
    actions = E.read_actions(acts)
    spans = E.alarm_spans(actions, 2, a.gap)
    r = E.evaluate(events, spans, actions, a.pre)
    days = max(1, (ev.times[-1] - ev.times[0]).days + 1)
    print("=" * 72)
    print(f"[3/3 채점]")
    E.print_report(r, f"Chronos-2 이동평균 예측 (backend={backend})", days)
    if a.out_report:
        E.save_report(r, a.out_report, f"backend={backend} 임계={thr}")
        print(f"사건별 표: {a.out_report}")
    if backend == "baseline":
        print("※ baseline 폴백 — 실 Chronos-2 환경에서 다시 돌리세요.")


def cmd_sweep(a):
    """
    p_on 스윕 — 모델은 한 번만 돌린다.
    p_on/p_off 는 예측 이후의 문턱값이라 확률 곡선을 재사용하면
    값마다 재예측할 필요가 없다 (스윕이 사실상 공짜).
    """
    cfg = load_config(a.config)
    print("=" * 72)
    print(f"[1/3 학습] 저장된 학습 결과 재사용: {a.config}")
    _print_learned(cfg)
    thr = cfg["threshold"]
    window = cfg["window"]
    min_dur = cfg["min_duration"]

    ev = load(a.eval, [TARGET, TIME_COL])
    print("=" * 72)
    print(f"[2/3 감지] {len(ev)}분  {ev.times[0]:%Y-%m-%d} ~ {ev.times[-1]:%Y-%m-%d}")
    print("  ※ 모델은 한 번만 호출하고, p_on 값들은 그 결과로 평가합니다.")
    pre = D.predict_curves(ev, thr, window, a.horizon, a.context,
                           a.stride, a.model, a.device, True, a.batch)

    ev_sm = moving_avg(ev.filled(TARGET), window)
    events = find_events(ev.times, ev_sm, ev.get(TARGET), thr, min_dur, a.gap)
    days = max(1, (ev.times[-1] - ev.times[0]).days + 1)

    print("=" * 72)
    print(f"[3/3 채점] backend={pre['backend']} · 심각 사건 {len(events)}건 · {days}일")
    print("=" * 72)
    hdr = (f"{'p_on':>6}{'Recall':>9}{'Precis':>8}{'평균lead':>9}"
           f"{'≥10분':>7}{'5~9분':>7}{'<5분':>6}{'헛울림':>7}{'/일':>6}")
    print(hdr)
    print("-" * len(hdr))
    best = None
    for p_on in a.p_on_list:
        p_off = min(p_on - 0.05, a.p_off) if a.p_off >= p_on else a.p_off
        rows = D.decide(pre, p_on, max(0.05, p_off))
        actions = [{"t": r[0], "stage": r[2], "prob": r[3],
                    "lead": r[4], "kind": r[5], "why": r[6]} for r in rows]
        spans = E.alarm_spans(actions, 2, a.gap)
        r = E.evaluate(events, spans, actions, a.pre)
        print(f"{p_on:>6.2f}{r['recall']:>8.0%}{r['precision']:>8.0%}"
              f"{(r['mean_lead'] if r['mean_lead'] is not None else 0):>9.1f}"
              f"{r['lead10']:>7}{r['lead5']:>7}{r['lead0']:>6}"
              f"{r['false']:>7}{r['false']/days:>6.1f}")
        # 저장용: recall 우선, 그다음 lead
        score = (r["recall"], r["lead10"], r["mean_lead"] or 0)
        if best is None or score > best[0]:
            best = (score, p_on, rows, r)
    print("-" * len(hdr))
    if best and a.out_actions:
        _, p_on, rows, r = best
        D.save(rows, a.out_actions)
        print(f"최고(recall→≥10분전 기준) p_on={p_on:.2f} 결과 저장: {a.out_actions}")
        if a.out_report:
            E.save_report(r, a.out_report, f"p_on={p_on} backend={pre['backend']}")
            print(f"사건별 표: {a.out_report}")
    if pre["backend"] == "baseline":
        print("※ baseline 폴백 — 실 Chronos-2 환경에서 다시 돌리세요.")


def main():
    ap = argparse.ArgumentParser(description="심각 정체 예측 파이프라인")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # ── 학습만 (4~7월 등 긴 기간 → model_config.json 저장) ──
    q = sub.add_parser("learn", help="학습만 — 판정기준 산출해 config 저장")
    q.add_argument("--train", required=True, nargs="+",
                   help="학습 CSV(글롭). 예: \"RAW/*.CSV\" (4~7월 전부)")
    q.add_argument("--window", type=int, default=10, help="이동평균 창(분)")
    q.add_argument("--pct", type=float, default=0.99, help="임계 분위수")
    q.add_argument("--min-duration", type=int, default=10, help="심각 사건 최소 지속(분)")
    q.add_argument("--gap", type=int, default=10)
    q.add_argument("--out-config", default="model_config.json")
    q.set_defaults(func=cmd_learn)

    p = sub.add_parser("all", help="학습→감지→채점")
    p.add_argument("--train", nargs="+", help="학습 CSV(글롭). --config 있으면 생략 가능")
    p.add_argument("--config", default=None,
                   help="저장된 학습 결과 재사용 (learn 산출물)")
    p.add_argument("--eval", required=True, nargs="+", help="평가 CSV(글롭)")
    p.add_argument("--window", type=int, default=10, help="이동평균 창(분)")
    p.add_argument("--pct", type=float, default=0.99, help="임계 분위수")
    p.add_argument("--min-duration", type=int, default=10, help="심각 사건 최소 지속(분)")
    p.add_argument("--horizon", type=int, default=15, help="예측 지평(분)")
    p.add_argument("--context", type=int, default=90,
                   help="모델이 보는 직전 이력(분). 기본 90분")
    p.add_argument("--p-on", type=float, default=0.6)
    p.add_argument("--p-off", type=float, default=0.4)
    p.add_argument("--stride", type=int, default=1)
    p.add_argument("--batch", type=int, default=256,
                   help="모델 호출당 묶을 시점 수 (클수록 빠름, GPU 메모리↑)")
    p.add_argument("--gap", type=int, default=10)
    p.add_argument("--pre", type=int, default=20, help="사전감지 인정 창(분)")
    p.add_argument("--model", default="chronos_2")
    p.add_argument("--device", default=None)
    p.add_argument("--out-actions", default="actions.csv")
    p.add_argument("--out-report", default="report.csv")
    p.set_defaults(func=cmd_all)

    # ── p_on 스윕 (모델 1회 호출) ──
    w = sub.add_parser("sweep", help="p_on 여러 값을 한 번의 모델 실행으로 비교")
    w.add_argument("--config", required=True, help="learn 산출물")
    w.add_argument("--eval", required=True, nargs="+", help="평가 CSV(글롭)")
    w.add_argument("--p-on-list", type=float, nargs="+",
                   default=[0.3, 0.4, 0.5, 0.6, 0.7],
                   help="비교할 p_on 값들 (기본 0.3~0.7)")
    w.add_argument("--p-off", type=float, default=0.4)
    w.add_argument("--horizon", type=int, default=30, help="예측 지평(분)")
    w.add_argument("--context", type=int, default=90)
    w.add_argument("--stride", type=int, default=1)
    w.add_argument("--batch", type=int, default=256)
    w.add_argument("--gap", type=int, default=10)
    w.add_argument("--pre", type=int, default=35, help="사전감지 인정 창(분)")
    w.add_argument("--model", default="chronos_2")
    w.add_argument("--device", default=None)
    w.add_argument("--out-actions", default="actions_best.csv")
    w.add_argument("--out-report", default="report_best.csv")
    w.set_defaults(func=cmd_sweep)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
