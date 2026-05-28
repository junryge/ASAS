#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
발동이벤트.csv → incidents.json (unified_risk_score ≥ 65 구간 라벨링)

v4.1 룰베이스 출력의 unified_risk_score 가 임계(65) 이상인 연속 분을 사건으로 묶음.
gap_min 이하면 같은 사건으로 합침.

사용법:
    # 폴더 전체 (날짜별 발동이벤트.csv 모두 합치기)
    python make_incidents_risk65.py --dir predict_tobe --out incidents_C_risk65.json

    # 단일 파일
    python make_incidents_risk65.py --csv predict_tobe/20260424_발동이벤트.csv

    # 임계/갭 조정
    python make_incidents_risk65.py --dir predict_tobe --threshold 80 --gap_min 10 --out incidents_C_risk80.json

라벨 C (위험도 65+) 의 의미:
  - A (S3 사건단위.csv) 가 놓친 짧은 위험 구간 포함
  - 약한 라벨 — ML 학습 시 가중치 낮게 또는 별도 모델
  - C 학습 시에는 features 에서 unified_risk_score / area_score_* 컬럼 drop 필요 (라벨 누수 방지)
"""

import argparse
import csv
import glob
import json
import os
import sys
from datetime import datetime, timedelta


def parse_발동이벤트_csv(csv_path, threshold=65.0, gap_min=5):
    """발동이벤트 CSV 1개 → 임계 이상 구간 사건 리스트."""
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        return []

    # 임계 이상인 분 목록 수집
    flagged_times = []
    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            dt_str = (row.get('datetime') or '').strip()
            score_str = (row.get('unified_risk_score') or '').strip()
            if not dt_str or not score_str:
                continue
            try:
                score = float(score_str)
            except ValueError:
                continue
            if score < threshold:
                continue
            # 분 단위 datetime 파싱
            t = _parse_minute(dt_str)
            if t is None:
                continue
            flagged_times.append((t, score, row))

    if not flagged_times:
        return []

    flagged_times.sort(key=lambda x: x[0])

    # gap_min 이하 연속 구간을 한 사건으로 묶음
    incidents = []
    cur_start = flagged_times[0][0]
    cur_end = flagged_times[0][0]
    cur_max_score = flagged_times[0][1]
    cur_max_row = flagged_times[0][2]

    for t, score, row in flagged_times[1:]:
        if (t - cur_end).total_seconds() / 60.0 <= gap_min:
            cur_end = t
            if score > cur_max_score:
                cur_max_score = score
                cur_max_row = row
        else:
            incidents.append(_finalize(cur_start, cur_end, cur_max_score, cur_max_row))
            cur_start = t
            cur_end = t
            cur_max_score = score
            cur_max_row = row
    incidents.append(_finalize(cur_start, cur_end, cur_max_score, cur_max_row))

    return incidents


def _parse_minute(dt_str):
    """'2026-05-28 12:13' 또는 '2026-05-28 12:13:00' → datetime (분 단위)."""
    for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M'):
        try:
            return datetime.strptime(dt_str, fmt).replace(second=0, microsecond=0)
        except ValueError:
            continue
    return None


def _finalize(start, end, max_score, max_row):
    """구간 → incidents JSON 1건."""
    # 사건 종료 시점에 1분 추가 (포함 종료)
    end_inclusive = end + timedelta(minutes=1)
    hot = (max_row.get('hot_area') or '').strip()
    level = (max_row.get('unified_risk_level') or '').strip()
    desc = (
        f"{start.strftime('%Y-%m-%d %H:%M')}~{end.strftime('%H:%M')} "
        f"max_score={max_score:.0f} level={level} hot={hot}"
    )
    return {
        'start': start.strftime('%Y-%m-%d %H:%M:%S'),
        'end': end_inclusive.strftime('%Y-%m-%d %H:%M:%S'),
        'desc': desc,
        'source': 'risk65',
        'max_score': max_score,
        'level': level,
        'hot_area': hot,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--csv', help='단일 발동이벤트 CSV 경로')
    p.add_argument('--dir', help='발동이벤트 CSV들이 있는 폴더 (예: predict_tobe)')
    p.add_argument('--threshold', type=float, default=65.0,
                   help='unified_risk_score 임계 (기본 65)')
    p.add_argument('--gap_min', type=int, default=5,
                   help='gap 이하면 한 사건으로 묶음 (기본 5분)')
    p.add_argument('--out', default='incidents_C_risk65.json', help='출력 JSON 경로')
    args = p.parse_args()

    all_incidents = []

    if args.csv:
        all_incidents = parse_발동이벤트_csv(args.csv, args.threshold, args.gap_min)
        print(f'📥 {args.csv} → {len(all_incidents)} 사건')
    elif args.dir:
        if not os.path.isdir(args.dir):
            sys.exit(f'폴더 없음: {args.dir}')
        pattern = os.path.join(args.dir, '*_발동이벤트.csv')
        files = sorted(glob.glob(pattern))
        if not files:
            sys.exit(f'발동이벤트 CSV 없음 (패턴: {pattern})')
        for f in files:
            incidents = parse_발동이벤트_csv(f, args.threshold, args.gap_min)
            if incidents:
                print(f'  {os.path.basename(f)}: {len(incidents)} 사건')
            all_incidents.extend(incidents)
    else:
        sys.exit('--csv 또는 --dir 필수')

    if not all_incidents:
        sys.exit(f'❌ 사건 0건 (임계 {args.threshold}, gap {args.gap_min}분)')

    # 중복 제거 (start+end 기준)
    seen = set()
    unique = []
    for inc in all_incidents:
        key = (inc['start'], inc['end'])
        if key not in seen:
            seen.add(key)
            unique.append(inc)
    all_incidents = sorted(unique, key=lambda x: x['start'])

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(all_incidents, f, ensure_ascii=False, indent=2)

    print(f'\n✅ 총 {len(all_incidents)} 사건 → {args.out}')
    print(f'   임계: unified_risk_score ≥ {args.threshold}, gap ≤ {args.gap_min}분')
    print(f'\n첫 3건 미리보기:')
    for inc in all_incidents[:3]:
        print(f'  · {inc["desc"]}')


if __name__ == '__main__':
    main()
