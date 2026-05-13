#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML 모델 실측 평가 — 사건별 사전 인지 시간 분석

사용법:
    python evaluate.py --features features.csv --model model.json --incidents incidents.json

출력:
  1. 사건별 사전 인지 시간 (ML score 0.7 넘은 시각 vs 실제 사건 시작)
  2. 사건 시작 -30분 / -15분 / 0분 시점의 ML score
  3. 전체 통계 (사건 평균 사전 인지 분, 위양성률 등)
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta


def parse_dt(s):
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f'시각 파싱 실패: {s}')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--features', required=True, help='피처 CSV')
    p.add_argument('--model', required=True, help='학습된 모델')
    p.add_argument('--incidents', required=True, help='사건 라벨 JSON')
    p.add_argument('--threshold', type=float, default=0.7, help='경보 임계값 (기본 0.7)')
    p.add_argument('--lookback', type=int, default=60, help='사건 전 몇 분 검사 (기본 60)')
    args = p.parse_args()

    # 1. 모델 로드 + 예측
    print(f'📥 모델 로드: {args.model}')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from ml_predictor import MLPredictor
    ml = MLPredictor(args.model)

    # 2. 피처 + 예측 (한 번에)
    print(f'📥 피처: {args.features}')
    timestamps = []
    scores = []
    with open(args.features, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = parse_dt(row['timestamp'])
            features = {}
            for k, v in row.items():
                if k == 'timestamp':
                    continue
                try:
                    features[k] = float(v) if v not in ('', None) else 0
                except (ValueError, TypeError):
                    features[k] = 0
            score = ml.predict(features)
            timestamps.append(ts)
            scores.append(score)

    print(f'   {len(scores):,} 분 예측 완료\n')

    # 3. 사건 로드
    with open(args.incidents, 'r', encoding='utf-8') as f:
        incidents_raw = json.load(f)
    incidents = []
    for inc in incidents_raw:
        incidents.append({
            'start': parse_dt(inc['start']),
            'end': parse_dt(inc['end']),
            'desc': inc.get('desc', ''),
        })

    print(f'📋 사건 {len(incidents)} 건 검증\n')
    print('=' * 100)

    # 4. 사건별 평가
    ts_to_idx = {t: i for i, t in enumerate(timestamps)}
    lead_times = []   # 사전 인지 분 (각 사건마다)
    missed = 0        # ML이 못 잡은 사건 (score 0.7 미달)

    for n, inc in enumerate(incidents, 1):
        start = inc['start']

        # 사건 시작 lookback분 전 ~ 사건 시작 시점 score 추출
        window_scores = []
        for i, t in enumerate(timestamps):
            diff = (start - t).total_seconds() / 60.0  # 양수 = 사건 전
            if 0 <= diff <= args.lookback:
                window_scores.append((t, scores[i], diff))

        if not window_scores:
            print(f'  [{n}] {start} {inc["desc"]}')
            print(f'      ⚠ 사건 전 데이터 없음 (피처에 누락)')
            continue

        window_scores.sort(key=lambda x: x[2])  # 최근 데이터 먼저

        # 임계값 처음 넘은 시각
        first_alert = None
        for t, sc, diff in window_scores:
            if sc >= args.threshold:
                first_alert = (t, sc, diff)
                break

        # 핵심 시점 score
        score_at_30m  = next((sc for t, sc, d in window_scores if 28 <= d <= 32), None)
        score_at_15m  = next((sc for t, sc, d in window_scores if 13 <= d <= 17), None)
        score_at_5m   = next((sc for t, sc, d in window_scores if 3  <= d <= 7),  None)
        score_at_0m   = next((sc for t, sc, d in window_scores if d <= 1), None)

        print(f'\n  [{n}] {start.strftime("%Y-%m-%d %H:%M")} — {inc["desc"]}')
        print(f'      ML 점수:  -30분={fmt(score_at_30m)}  -15분={fmt(score_at_15m)}  '
              f'-5분={fmt(score_at_5m)}  0분={fmt(score_at_0m)}')

        if first_alert:
            t, sc, diff = first_alert
            print(f'      ✅ {int(diff)}분 전 경보 (score={sc:.3f} @ {t.strftime("%H:%M")})')
            lead_times.append(diff)
        else:
            print(f'      ❌ {args.lookback}분 내 임계값 {args.threshold} 넘지 못함')
            missed += 1

    # 5. 전체 통계
    print('\n' + '=' * 100)
    print('📊 종합 평가')
    print('=' * 100)
    detected = len(lead_times)
    total = len(incidents)
    print(f'  사건 탐지율:    {detected}/{total} ({detected/total*100:.1f}%)')
    print(f'  놓친 사건:      {missed}/{total}')
    if lead_times:
        avg = sum(lead_times) / len(lead_times)
        print(f'  평균 사전인지:  {avg:.1f}분 전')
        print(f'  최대 사전인지:  {max(lead_times):.0f}분 전')
        print(f'  최소 사전인지:  {min(lead_times):.0f}분 전')

    # 6. 위양성 분석 (사건 구간 밖에서 score 높은 시각)
    incident_minutes = set()
    for inc in incidents:
        t = inc['start']
        while t <= inc['end']:
            incident_minutes.add(t)
            t += timedelta(minutes=1)

    high_score_outside = 0
    for t, sc in zip(timestamps, scores):
        if sc >= args.threshold and t not in incident_minutes:
            # 사건 30분 전 구간도 정상으로 봄 (사전 인지는 OK)
            in_lookback = False
            for inc in incidents:
                if 0 <= (inc['start'] - t).total_seconds() / 60.0 <= args.lookback:
                    in_lookback = True
                    break
            if not in_lookback:
                high_score_outside += 1

    print(f'\n  위양성 (정상시간에 score>={args.threshold}): {high_score_outside}분')
    if timestamps:
        normal_minutes = len(timestamps) - len(incident_minutes)
        print(f'  위양성률:       {high_score_outside / max(normal_minutes, 1) * 100:.2f}% (정상 분 대비)')
    print('=' * 100)


def fmt(v):
    if v is None:
        return '  -  '
    return f'{v:.3f}'


if __name__ == '__main__':
    main()
