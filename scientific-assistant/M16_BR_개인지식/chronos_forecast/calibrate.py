#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
임계값 자동 학습 (Calibration)
================================
학습기간(예: Apr1~May31)의 '정상분포'에서 신호별 임계값을 데이터로 뽑는다.
손으로 정한 상수(12.0/100/30...) 대신, 그 라인의 실제 분포에 맞춘 임계.

기존 hubroom_predictor 도 "정상분포 p95/p99 기반" 이라고 명시 — 같은 철학.
차이: 여기선 학습/평가 구간을 명확히 분리(leakage 방지)하고, 예측(Chronos)의
      경보 트리거로 쓸 수 있게 신호별로 일관되게 산출.

산출물: {signal: threshold} — 이후 guardrail.SignalConfig 에 주입.
"""
from __future__ import annotations

import json
from data_loader import SeriesData


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return float("nan")
    n = len(sorted_vals)
    idx = min(n - 1, max(0, int(round(p * (n - 1)))))
    return sorted_vals[idx]


def calibrate_thresholds(train: SeriesData, signals: list[str],
                         pct: float = 0.99) -> dict:
    """
    각 신호의 학습기간 pct 분위수를 임계값으로 채택.
    반환: {signal: {"threshold":.., "p50":.., "p95":.., "p99":.., "n":..}}
    """
    result = {}
    for sig in train.available(signals):
        vals = sorted(v for v in train.signal(sig) if v is not None)
        if not vals:
            continue
        result[sig] = {
            "threshold": round(percentile(vals, pct), 3),
            "pct": pct,
            "p50": round(percentile(vals, 0.50), 3),
            "p95": round(percentile(vals, 0.95), 3),
            "p99": round(percentile(vals, 0.99), 3),
            "p995": round(percentile(vals, 0.995), 3),
            "max": round(vals[-1], 3),
            "n": len(vals),
        }
    return result


def save(cal: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cal, f, ensure_ascii=False, indent=2)


def print_table(cal: dict, hand: dict | None = None):
    print(f"{'신호':<42}{'학습임계':>10}{'p95':>8}{'p99':>8}{'max':>8}", end="")
    if hand:
        print(f"{'손임계':>8}", end="")
    print()
    print("-" * (76 + (8 if hand else 0)))
    for sig, d in cal.items():
        short = sig.replace("M16HUB.", "").replace(".AVGTOTALTIME1MIN", ".AVGT") \
                   .replace(".MESCURRENTQCNT", ".QCNT")
        line = f"{short:<42}{d['threshold']:>10}{d['p95']:>8}{d['p99']:>8}{d['max']:>8}"
        if hand:
            hv = hand.get(sig, "-")
            line += f"{str(hv):>8}"
        print(line)


if __name__ == "__main__":
    import sys
    from data_loader import load_csv, CORE_SIGNALS
    if len(sys.argv) < 2:
        print("사용법: python3 calibrate.py <학습CSV> [pct]")
        raise SystemExit(1)
    pct = float(sys.argv[2]) if len(sys.argv) > 2 else 0.99
    sd = load_csv(sys.argv[1], CORE_SIGNALS + ["CRT_TM"])
    cal = calibrate_thresholds(sd, CORE_SIGNALS, pct=pct)
    hand = {
        "M16HUB.QUE.TIME.AVGTOTALTIME1MIN": 12.0,
        "M16HUB.QUE.M14TOM16.MESCURRENTQCNT": 100.0,
        "M16HUB.STRATE.ALL.FABSTORAGERATIO": 30.0,
        "M14.QUE.LOAD.AVGLOADTIME1MIN": 3.6,
        "M16A.QUE.LOAD.AVGLOADTIME1MIN": 3.4,
        "M16B.QUE.LOAD.AVGLOADTIME1MIN": 6.0,
    }
    print(f"\n=== 학습임계 (분위수 p{pct*100:.1f}) vs 손임계 ===")
    print_table(cal, hand)
    print("\n관찰: 손임계는 이 라인 분포와 어긋남(큐누적 100=항상초과, 저장률 30=절대미달).")
    print("      학습임계는 실제 정상분포 꼬리에 맞춰 자동 산출됨.")
