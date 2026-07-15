#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실데이터 학습→평가 실행기 (Apr~May 학습 → June 평가)
=====================================================
정식 사용:
    # 학습기간에서 임계 자동 학습 → 평가기간에 선제예측 vs 룰베이스 비교
    python3 run_real.py --train "data/2026-04*.CSV" "data/2026-05*.CSV" \
                        --eval  "data/2026-06*.CSV" \
                        --signal M16HUB.QUE.TIME.AVGTOTALTIME1MIN \
                        --horizons 10 30 --pct 0.99

샘플(하루) 데모:
    # 하루를 앞(학습)/뒤(평가)로 쪼개 실데이터 파이프라인 검증
    python3 run_real.py --sample <April1.CSV> --split "16:00" --horizons 10 30

핵심:
  · 임계값은 '학습기간'에서만 산출 → 평가기간 leakage 없음
  · 예측은 인과적(직전 context만) → 미래 누수 없음
  · ground-truth 정체 = 평가기간에서 신호가 (학습)임계를 실제로 넘은 구간
    → "임계 넘기 전에 미리 잡았나(lead)" 를 실측
"""
from __future__ import annotations

import argparse
from datetime import datetime

from data_loader import load_csv, load_glob, CORE_SIGNALS, SeriesData
from calibrate import calibrate_thresholds
from forecaster import make_forecaster
from guardrail import ForecastGuardrail, SignalConfig
from run_poc import find_episodes, run_rule_based, evaluate


def run_forecast_on_signal(values: list, threshold: float, horizon: int,
                           context_len: int = 180, prefer_real: bool = True,
                           p_on: float = 0.6, p_off: float = 0.35):
    """단일 신호에 대해 매분 예측→가드레일. None 값은 마지막 유효치로 채움(포워드필)."""
    f = make_forecaster(prefer_real=prefer_real, device="cpu")
    g = ForecastGuardrail([SignalConfig("sig", threshold=threshold,
                                        p_on=p_on, p_off=p_off)])
    # 포워드필로 결측 보정 (예측기 입력용)
    filled, last = [], None
    for v in values:
        if v is not None:
            last = v
        filled.append(last if last is not None else 0.0)

    alarms = [0] * len(values)
    backend = None
    for t in range(len(filled)):
        lo = max(0, t - context_len)
        ctx = filled[lo:t + 1]
        if len(ctx) < 5:
            continue
        fc = f.predict(ctx, horizon=horizon)
        backend = fc["backend"]
        out = g.step({"sig": {"q10": fc["q10"], "q50": fc["q50"],
                              "q90": fc["q90"]}})
        alarms[t] = 1 if out["stage"] >= 2 else 0
    return alarms, {"backend": backend, "churn": g.states["sig"].churn}


def ground_truth_labels(values: list, threshold: float) -> list:
    return [1 if (v is not None and v >= threshold) else 0 for v in values]


def report(signal, threshold, cal_info, train_n, eval_n,
           rule_m, fc_results, horizons, backend):
    print("=" * 78)
    print(" 실데이터 학습→평가: 선제예측(Chronos+가드레일) vs 룰베이스")
    print(f" 대상 신호: {signal}")
    print(f" 학습 {train_n}분 → 임계 자동학습 = {threshold}"
          f"  (p95={cal_info['p95']} p99={cal_info['p99']} max={cal_info['max']})")
    print(f" 평가 {eval_n}분  |  예측 backend: {backend}")
    print("=" * 78)
    cols = ["룰베이스"] + [f"예측 h={h}분" for h in horizons]
    print(f"{'지표':<20}" + "".join(f"{c:>17}" for c in cols))
    print("-" * 78)

    def fmt(v):
        return "-" if v is None else str(v)

    def row(label, key):
        cells = [fmt(rule_m[key])] + [fmt(r[key]) for r in fc_results]
        print(f"{label:<20}" + "".join(f"{c:>17}" for c in cells))

    row("정체사건 수", "episodes")
    row("감지 사건", "detected")
    row("놓침(미탐)", "missed")
    row("평균 lead(분)", "mean_lead_min")
    row("≥10분 전 감지", "caught_10")
    row("≥30분 전 감지", "caught_30")
    row("오탐 분", "false_alarm_minutes")
    row("churn(전환수)", "churn")
    print("-" * 78)
    print(f" 사건별 lead(분)  룰: {rule_m['leads']}")
    for h, r in zip(horizons, fc_results):
        print(f"                h={h}: {r['leads']}")
    print("=" * 78)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", nargs="+", help="학습 CSV 파일/글롭 (여러 개 가능)")
    ap.add_argument("--eval", nargs="+", help="평가 CSV 파일/글롭")
    ap.add_argument("--sample", help="샘플 단일 CSV (하루 데모용)")
    ap.add_argument("--split", default="16:00", help="샘플 학습/평가 분할 시각")
    ap.add_argument("--signal", default="M16HUB.QUE.TIME.AVGTOTALTIME1MIN")
    ap.add_argument("--horizons", type=int, nargs="+", default=[10, 30])
    ap.add_argument("--pct", type=float, default=0.99, help="임계 분위수")
    ap.add_argument("--no-real", action="store_true")
    args = ap.parse_args()

    signals = list({args.signal, *CORE_SIGNALS})

    if args.sample:
        # 하루를 split 시각 기준 앞(학습)/뒤(평가)로 분리
        sd = load_csv(args.sample, CORE_SIGNALS + ["CRT_TM"])
        hh, mm = map(int, args.split.split(":"))
        cut = datetime(sd.times[0].year, sd.times[0].month, sd.times[0].day, hh, mm)
        tr_idx = [i for i, t in enumerate(sd.times) if t < cut]
        ev_idx = [i for i, t in enumerate(sd.times) if t >= cut]
        train = SeriesData([sd.times[i] for i in tr_idx],
                           {c: [v[i] for i in tr_idx] for c, v in sd.columns.items()})
        ev = SeriesData([sd.times[i] for i in ev_idx],
                        {c: [v[i] for i in ev_idx] for c, v in sd.columns.items()})
        print(f"[샘플 데모] {args.sample}")
        print(f"  학습 {train.times[0]}~{train.times[-1]} ({len(train)}분)")
        print(f"  평가 {ev.times[0]}~{ev.times[-1]} ({len(ev)}분)")
        print("  ※ 하루 한정 plumbing 데모 — 성능 주장 아님. 정식은 --train/--eval.\n")
    else:
        if not (args.train and args.eval):
            ap.error("--sample 또는 (--train 과 --eval) 필요")
        def load_many(patterns):
            import glob as _g
            parts = []
            for p in patterns:
                if _g.glob(p):
                    parts.append(load_glob(p, CORE_SIGNALS + ["CRT_TM"]))
                else:
                    parts.append(load_csv(p, CORE_SIGNALS + ["CRT_TM"]))
            # concat
            times, cols = [], {}
            for sdp in parts:
                base = len(times)
                times.extend(sdp.times)
                for c, vals in sdp.columns.items():
                    cols.setdefault(c, [None] * base)
                    cols[c].extend(vals)
                for c in cols:
                    if len(cols[c]) < len(times):
                        cols[c].extend([None] * (len(times) - len(cols[c])))
            order = sorted(range(len(times)), key=lambda i: times[i])
            return SeriesData([times[i] for i in order],
                              {c: [v[i] for i in order] for c, v in cols.items()})
        train = load_many(args.train)
        ev = load_many(args.eval)
        print(f"[정식] 학습 {len(train)}분  평가 {len(ev)}분\n")

    # 1) 학습기간에서 임계 자동 학습
    cal = calibrate_thresholds(train, signals, pct=args.pct)
    if args.signal not in cal:
        raise SystemExit(f"신호 {args.signal} 가 학습데이터에 없음")
    threshold = cal[args.signal]["threshold"]

    # 2) 평가기간: ground-truth + 룰베이스 + 예측
    ev_vals = ev.signal(args.signal)
    labels = ground_truth_labels(ev_vals, threshold)
    episodes = find_episodes(labels)
    rule_alarms = run_rule_based([v if v is not None else -1e9 for v in ev_vals],
                                 threshold)
    rule_m = evaluate(rule_alarms, labels, episodes)

    fc_results, backend = [], None
    for h in args.horizons:
        fc_alarms, meta = run_forecast_on_signal(
            ev_vals, threshold, horizon=h, prefer_real=not args.no_real)
        backend = meta["backend"]
        fc_results.append(evaluate(fc_alarms, labels, episodes))

    report(args.signal, threshold, cal[args.signal], len(train), len(ev),
           rule_m, fc_results, args.horizons, backend)
    if backend == "baseline-ewma":
        print(" ※ 실 Chronos-Bolt 미탑재 → baseline 예측기. 실모델은 먼지평 예측 강점.")


if __name__ == "__main__":
    main()
