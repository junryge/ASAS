#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
합성 HUBROOM 정체 시나리오 생성기 (PoC 검증용)
================================================
실제 M16 raw CSV 가 이 컨테이너에 없으므로, 정체 사건의 '모양'을 흉내낸
분당 시계열을 만든다. 목적은 성능 주장(X)이 아니라 파이프라인이
'정체를 미리 잡는가'를 검증(O)하는 것.

각 사건(episode)의 전형적 형태:
  정상 baseline → 서서히 상승(ramp) → 임계 돌파(정체 본격화, ground-truth 정체구간)
  → 완화(회복). 여기에 관측 노이즈를 얹는다.

반환:
  values : [float]  분당 신호값 (예: AVGTOTALTIME1MIN)
  labels : [0/1]    해당 분이 '실제 정체'인지 (ground truth)
"""
from __future__ import annotations

import math
import random


def make_series(n_minutes: int = 720,
                threshold: float = 12.0,
                baseline: float = 6.0,
                noise: float = 0.6,
                seed: int = 42) -> tuple[list[float], list[int]]:
    """
    n_minutes 길이의 신호 + ground-truth 정체 라벨 생성.
    임계(threshold)를 실제로 넘는 구간을 정체(1)로 라벨.
    """
    rng = random.Random(seed)
    values = [0.0] * n_minutes
    labels = [0] * n_minutes

    # 사건을 몇 개 심는다 — 최소 간격(min_gap)을 둬 pre-window 겹침 방지
    min_gap = 150
    n_episodes = max(2, n_minutes // min_gap)
    starts: list[int] = []
    guard = 0
    while len(starts) < n_episodes and guard < 1000:
        guard += 1
        cand = rng.randint(60, n_minutes - 100)
        if all(abs(cand - s) >= min_gap for s in starts):
            starts.append(cand)
    episode_starts = sorted(starts)

    # baseline: 완만한 일주기 변동 + 노이즈
    for t in range(n_minutes):
        daily = 0.8 * math.sin(2 * math.pi * t / 240.0)
        values[t] = baseline + daily + rng.gauss(0, noise)

    for start in episode_starts:
        ramp = rng.randint(15, 30)      # 상승 구간(분)
        peak = rng.randint(10, 25)      # 정체 지속(분)
        recover = rng.randint(15, 30)   # 회복 구간(분)
        peak_height = threshold + rng.uniform(1.5, 6.0)

        # ramp: baseline → peak_height 로 상승
        for i in range(ramp):
            t = start + i
            if t >= n_minutes:
                break
            frac = i / ramp
            values[t] += (peak_height - baseline) * (frac ** 1.6)
        # peak: 임계 위 유지 (정체 ground-truth)
        for i in range(peak):
            t = start + ramp + i
            if t >= n_minutes:
                break
            values[t] += (peak_height - baseline) * (0.9 + 0.1 * math.sin(i))
        # recover: 하강
        for i in range(recover):
            t = start + ramp + peak + i
            if t >= n_minutes:
                break
            frac = 1 - i / recover
            values[t] += (peak_height - baseline) * (frac ** 1.4) * 0.8

    # ground-truth 라벨: 실제로 임계 초과한 분
    for t in range(n_minutes):
        labels[t] = 1 if values[t] >= threshold else 0

    return values, labels


if __name__ == "__main__":
    v, y = make_series(seed=1)
    n_cong = sum(y)
    print(f"길이={len(v)}분, 정체분={n_cong} ({100*n_cong/len(v):.1f}%)")
    print("샘플 값:", [round(x, 1) for x in v[:20]])
