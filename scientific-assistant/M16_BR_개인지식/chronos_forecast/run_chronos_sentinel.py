#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chronos-2 → TightLoop Sentinel 파이프라인 (실행 진입점)
=========================================================
문서 구조 그대로:  [예측] Chronos-2  →  [행동] TightLoop Sentinel

    과거 반송시간 시계열
          │
          ▼  (매 1분, 인과적 — 직전까지 데이터만)
    Chronos.predict(context, horizon=10)  →  q10/q50/q90 (10분 뒤 분포)
          │
          ▼
    Sentinel.step(q10,q50,q90)  →  경보단계 · 예비조정 · center · tail · lead
          │
          ▼
    "문제 예측 시각" 리스트 + 분당 액션 CSV

사용 (사내/GPU 환경, torch+chronos 설치 후):
    pip install -r requirements.txt
    python3 run_chronos_sentinel.py \
        --data  M16A_HUBROOM_PR_20260601~20260630.CSV \
        --signal M16HUB.QUE.TIME.AVGTOTALTIME1MIN \
        --horizon 10 \
        --model amazon/chronos-2 \
        --threshold 12.0 \
        --out actions_202606.csv

임계 자동학습(학습기간에서):
    # --train 으로 학습CSV 주면 그 구간 분위수로 임계 산출 (--pct, 기본 0.99)
    python3 run_chronos_sentinel.py --data JUNE.CSV --train APR_MAY.CSV --pct 0.99 ...

torch/chronos 미설치 시: baseline 예측기로 파이프라인만 동작(경고 표시).
"""
from __future__ import annotations

import argparse
import csv

from data_loader import load_csv, load_any, CORE_SIGNALS
from calibrate import percentile
from forecaster import ChronosForecaster, BaselineForecaster
from sentinel import TightLoopSentinel, SentinelConfig


def forward_fill(vals):
    out, last = [], None
    for v in vals:
        if v is not None:
            last = v
        out.append(last if last is not None else 0.0)
    return out


def main():
    ap = argparse.ArgumentParser(description="Chronos-2 → TightLoop Sentinel")
    ap.add_argument("--data", required=True, nargs="+",
                    help="대상 CSV. 파일 하나/여러 개/글롭 가능 (예: RAW/*.CSV)")
    ap.add_argument("--signal", default="M16HUB.QUE.TIME.AVGTOTALTIME1MIN")
    ap.add_argument("--horizon", type=int, default=10, help="예측 지평(분). 기본 10")
    ap.add_argument("--context", type=int, default=180, help="예측 입력 context 길이(분)")
    ap.add_argument("--stride", type=int, default=1,
                    help="백테스트 평가 간격(분). CPU에서 한 달치는 5~10 권장. 실시간은 1")
    ap.add_argument("--model", default="amazon/chronos-2",
                    help="amazon/chronos-2 (최신·기본) 또는 chronos-bolt-{tiny,base}")
    ap.add_argument("--device", default=None, help="cuda/mps/cpu (기본 자동)")
    ap.add_argument("--threshold", type=float, default=None, help="임계값(수동)")
    ap.add_argument("--train", default=None, help="임계 자동학습용 학습 CSV")
    ap.add_argument("--pct", type=float, default=0.99, help="자동학습 분위수")
    # Sentinel 튜닝
    ap.add_argument("--p-on", type=float, default=0.60)
    ap.add_argument("--p-off", type=float, default=0.35)
    ap.add_argument("--out", default=None, help="분당 액션 CSV 저장 경로")
    ap.add_argument("--no-real", action="store_true", help="baseline 예측기 강제")
    args = ap.parse_args()

    # 1) 데이터 로드 (파일/여러개/글롭 병합)
    sd = load_any(args.data, list({args.signal, *CORE_SIGNALS}) + ["CRT_TM"])
    if args.signal not in sd.columns:
        raise SystemExit(f"신호 {args.signal} 가 데이터에 없음")
    values = sd.signal(args.signal)
    filled = forward_fill(values)
    times = sd.times

    # 2) 임계값 결정 (수동 > 학습 > 대상데이터 분위수)
    if args.threshold is not None:
        threshold = args.threshold
        thr_src = "수동"
    elif args.train:
        tr = load_any(args.train, [args.signal, "CRT_TM"])
        tv = sorted(v for v in tr.signal(args.signal) if v is not None)
        threshold = round(percentile(tv, args.pct), 3)
        thr_src = f"학습CSV p{args.pct*100:.0f}"
    else:
        sv = sorted(v for v in values if v is not None)
        threshold = round(percentile(sv, args.pct), 3)
        thr_src = f"대상데이터 p{args.pct*100:.0f}(주의:leakage)"

    # 3) 예측 계층 (Chronos-Bolt)
    if args.no_real:
        f = BaselineForecaster()
        backend = "baseline-ewma"
    else:
        f = ChronosForecaster(model_path=args.model, device=args.device)
        backend = f.backend
        if not f.using_real_model:
            print(f"⚠ Chronos 모델 로드 실패 → baseline 폴백. 원인: {f._load_error}")
            print("  (torch/chronos 설치 및 모델 다운로드 가능한 환경에서 실행하세요)")

    # 4) 행동 계층 (Sentinel)
    cfg = SentinelConfig(threshold=threshold, p_on=args.p_on, p_off=args.p_off)
    sen = TightLoopSentinel(cfg)

    print("=" * 72)
    print(" Chronos-2 → TightLoop Sentinel")
    print(f" 신호: {args.signal}")
    print(f" 예측 backend: {backend} | 지평 {args.horizon}분 | 임계 {threshold} ({thr_src})")
    print(f" 데이터: {len(times)}분  {times[0]} ~ {times[-1]}")
    print("=" * 72)

    # 5) 매분 파이프라인 (인과적)
    #    --stride>1 이면 stride 간격으로만 모델 호출, 사이 분은 직전 액션 유지
    #    (CPU 백테스트 가속용. 실시간 운영은 stride=1).
    actions = []
    last_action = None
    stride = max(1, args.stride)
    for t in range(len(filled)):
        ctx = filled[max(0, t - args.context):t + 1]
        if len(ctx) < 5:
            actions.append(None)
            continue
        if t % stride == 0:
            fc = f.predict(ctx, horizon=args.horizon)
            last_action = sen.step(fc["q10"], fc["q50"], fc["q90"])
        actions.append(last_action)

    # 6) 문제 예측 시각 집계 (stage>=2 경보 구간)
    alarms, on0 = [], None
    for t, a in enumerate(actions):
        on = a is not None and a.stage >= 2
        if on and on0 is None:
            on0 = t
        elif not on and on0 is not None:
            alarms.append((on0, t - 1)); on0 = None
    if on0 is not None:
        alarms.append((on0, len(actions) - 1))

    print(f"\n■ 문제 예측 경보 {len(alarms)}건 (stage≥2):")
    if not alarms:
        print("  (경보 없음 — 정상 운영)")
    for (a, b) in alarms:
        peak = max((actions[i].exceed_prob for i in range(a, b + 1)), default=0)
        lead = next((actions[i].lead_min for i in range(a, b + 1)
                     if actions[i].lead_min is not None), None)
        rec = actions[a].recommendation
        leadtxt = f", 약 {lead}분 선제" if lead else ""
        print(f"  {times[a].strftime('%m-%d %H:%M')} ~ {times[b].strftime('%H:%M')}"
              f"  (초과확률 최대 {peak:.2f}{leadtxt}) → {rec}")

    # 7) 분당 액션 CSV 저장 (옵션)
    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8-sig") as fp:
            w = csv.writer(fp)
            w.writerow(["datetime", "signal_value", "stage", "stage_name",
                        "exceed_prob", "lead_min", "center_adjust",
                        "reserve_adjust", "tail_upper", "tail_lower",
                        "recommendation"])
            for t, a in enumerate(actions):
                if a is None:
                    continue
                w.writerow([times[t].strftime("%Y-%m-%d %H:%M:%S"),
                            values[t], a.stage, a.stage_name, a.exceed_prob,
                            a.lead_min if a.lead_min is not None else "",
                            a.center_adjust, a.reserve_adjust,
                            a.tail_upper, a.tail_lower, a.recommendation])
        print(f"\n분당 액션 저장: {args.out}")

    if backend == "baseline-ewma":
        print("\n※ 실 Chronos 모델 아님(baseline). 사내 GPU 환경에서 --model amazon/chronos-2 로 실모델 사용.")


if __name__ == "__main__":
    main()
