#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PoC 비교 하네스: 룰베이스(반응형) vs Chronos+가드레일(선제형)
==============================================================
동일한 합성 시계열에 두 방식을 돌려 운영지표를 나란히 비교한다.

  · 룰베이스 대조군 : "현재값 >= 임계" 면 경보 (기존 predictor의 핵심 판정 방식 축약)
  · 제안 방식       : 매 분 최근 context 로 Chronos 예측 → 가드레일 판정 (인과적)

측정 지표 (DESIGN.md 6장):
  · lead_min     : 각 정체 사건을 몇 분 미리 잡았나 (클수록 좋음)
  · 미탐(놓친 사건 수)
  · 오탐 분      : 실제 정체 아닌데 경보 켜진 분 수
  · churn        : 경보 on/off 전환 횟수 (알람 피로 대리지표)

주의: 합성 데이터라 절대 수치는 의미 없음. '선제 감지가 되는가 / 오탐이
      늘지 않는가'의 방향성만 본다. 실 데이터·실 모델은 사내에서 붙인다.
"""
from __future__ import annotations

import argparse

from forecaster import make_forecaster
from guardrail import ForecastGuardrail, SignalConfig
from scenario import make_series


# ---------------------------------------------------------------------------
# 사건(episode) 라벨 → 사건 경계 리스트로 변환
# ---------------------------------------------------------------------------
def find_episodes(labels: list[int]) -> list[tuple[int, int]]:
    """연속된 1 구간을 (start, end) 로 묶는다."""
    eps, s = [], None
    for t, y in enumerate(labels):
        if y and s is None:
            s = t
        elif not y and s is not None:
            eps.append((s, t - 1))
            s = None
    if s is not None:
        eps.append((s, len(labels) - 1))
    return eps


# ---------------------------------------------------------------------------
# 룰베이스 대조군: 현재값 >= 임계 → 경보
# ---------------------------------------------------------------------------
def run_rule_based(values: list[float], threshold: float) -> list[int]:
    return [1 if v >= threshold else 0 for v in values]


# ---------------------------------------------------------------------------
# 제안 방식: 매 분 예측 → 가드레일. 인과적(직전까지 context만 사용)
# ---------------------------------------------------------------------------
def run_forecast_guardrail(values: list[float], threshold: float,
                           context_len: int = 120, horizon: int = 10,
                           prefer_real: bool = True) -> tuple[list[int], dict]:
    f = make_forecaster(prefer_real=prefer_real, device="cpu")
    cfg = SignalConfig("sig", threshold=threshold, weight=1.0)
    g = ForecastGuardrail([cfg])

    alarms = [0] * len(values)
    backend = None
    for t in range(len(values)):
        # 인과적: t 시점 판정에 t까지의 관측만 사용 (미래 누수 없음)
        lo = max(0, t - context_len)
        ctx = values[lo:t + 1]
        if len(ctx) < 5:
            continue
        fc = f.predict(ctx, horizon=horizon)
        backend = fc["backend"]
        out = g.step({"sig": {"q10": fc["q10"], "q50": fc["q50"],
                              "q90": fc["q90"]}})
        # stage>=2(주의보 이상)면 경보로 간주
        alarms[t] = 1 if out["stage"] >= 2 else 0
    return alarms, {"backend": backend, "churn": g.states["sig"].churn}


# ---------------------------------------------------------------------------
# 지표 계산
# ---------------------------------------------------------------------------
def evaluate(alarms: list[int], labels: list[int],
             episodes: list[tuple[int, int]],
             pre_window: int = 45) -> dict:
    # lead: 사건 시작 전(또는 시작 시점)에 경보가 처음 켜진 시각과의 차이
    leads, missed = [], 0
    caught_10 = caught_30 = 0   # 10분/30분 이상 미리 잡은 사건 수
    for (s, e) in episodes:
        # 사건 시작 pre_window분 전부터 사건 종료까지 사이의 첫 경보
        win_start = max(0, s - pre_window)
        fire = None
        for t in range(win_start, e + 1):
            if alarms[t]:
                fire = t
                break
        if fire is None:
            missed += 1
        else:
            lead = s - fire  # +면 미리, 0이면 시작 순간, -면 늦음
            leads.append(lead)
            if lead >= 10:
                caught_10 += 1
            if lead >= 30:
                caught_30 += 1

    # 오탐 분: 실제 정체(및 그 30분 전 예열구간) 밖에서 켜진 경보
    in_event = [0] * len(labels)
    for (s, e) in episodes:
        for t in range(max(0, s - 30), min(len(labels), e + 1)):
            in_event[t] = 1
    false_minutes = sum(1 for t in range(len(alarms))
                        if alarms[t] and not in_event[t])

    # churn: 경보 on/off 전환 수
    churn = sum(1 for t in range(1, len(alarms)) if alarms[t] != alarms[t - 1])

    return {
        "episodes": len(episodes),
        "detected": len(episodes) - missed,
        "missed": missed,
        "mean_lead_min": round(sum(leads) / len(leads), 1) if leads else None,
        "caught_10": caught_10,   # ≥10분 전 감지
        "caught_30": caught_30,   # ≥30분 전 감지
        "leads": leads,
        "false_alarm_minutes": false_minutes,
        "churn": churn,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=int, default=1440)
    ap.add_argument("--threshold", type=float, default=12.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--horizons", type=int, nargs="+", default=[10, 30],
                    help="예측 지평(분) 목록. 기본 10분/30분 전 예측 비교")
    ap.add_argument("--no-real", action="store_true",
                    help="실모델 시도 안 하고 baseline 예측기만 사용")
    args = ap.parse_args()

    values, labels = make_series(n_minutes=args.minutes,
                                 threshold=args.threshold, seed=args.seed)
    episodes = find_episodes(labels)

    # 룰베이스는 지평 개념이 없음(현재값만 봄) → 한 번만 계산
    rule_alarms = run_rule_based(values, args.threshold)
    rule_m = evaluate(rule_alarms, labels, episodes)

    print("=" * 74)
    print(" HUBROOM 데드락 예측 PoC — '몇 분 전에 잡나' (10분 전 vs 30분 전)")
    print(f" 시나리오: {len(values)}분, 사건 {len(episodes)}건, 임계 {args.threshold}")
    print("=" * 74)

    def fmt(v):
        return "-" if v is None else str(v)

    # 헤더: 룰베이스 + 각 지평
    cols = ["룰베이스"] + [f"예측 h={h}분" for h in args.horizons]
    print(f"{'지표':<20}" + "".join(f"{c:>17}" for c in cols))
    print("-" * 74)

    fc_results = []
    backend = None
    for h in args.horizons:
        fc_alarms, meta = run_forecast_guardrail(
            values, args.threshold, horizon=h, prefer_real=not args.no_real)
        backend = meta["backend"]
        fc_results.append(evaluate(fc_alarms, labels, episodes))

    def row(label, key):
        cells = [fmt(rule_m[key])] + [fmt(r[key]) for r in fc_results]
        print(f"{label:<20}" + "".join(f"{c:>17}" for c in cells))

    row("감지 사건", "detected")
    row("놓침(미탐)", "missed")
    row("평균 lead(분)", "mean_lead_min")
    row("≥10분 전 감지", "caught_10")
    row("≥30분 전 감지", "caught_30")
    row("오탐 분", "false_alarm_minutes")
    row("churn(전환수)", "churn")
    print("-" * 74)
    print(f" 사건별 lead(분)  룰: {rule_m['leads']}")
    for h, r in zip(args.horizons, fc_results):
        print(f"                h={h}: {r['leads']}")
    print("=" * 74)
    print(" 읽는 법: 지평(h)을 늘릴수록 '더 미리' 잡지만(≥30분 전 감지↑),")
    print("          먼 미래라 불확실→오탐 분이 늘 수 있다. 이 균형점을 고르는 게 튜닝.")
    if backend == "baseline-ewma":
        print(" ※ 실 Chronos-Bolt 미탑재 → baseline 예측기로 파이프라인만 검증.")
        print("   실모델은 먼 지평(30분) 예측이 훨씬 정확 → 30분 전 감지 신뢰도↑ 기대.")


if __name__ == "__main__":
    main()
