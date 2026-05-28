#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사건단위 CSV → incidents.json 자동 변환

사용법:
    # 단일 파일
    python make_incidents.py --csv out/20260507_사건단위.csv

    # 폴더 전체 (날짜별 사건단위.csv 모두 합치기)
    python make_incidents.py --dir out

    # 출력 경로 지정
    python make_incidents.py --dir out --out incidents.json
"""

import argparse
import csv
import glob
import json
import os
import sys


def parse_사건단위_csv(csv_path):
    """사건단위 CSV 1개 → [(start_dt_str, end_dt_str, desc), ...]"""
    incidents = []
    if not os.path.exists(csv_path):
        return incidents
    if os.path.getsize(csv_path) == 0:
        return incidents

    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = (row.get('date') or '').strip()
            start_t = (row.get('start_time') or '').strip()
            end_t = (row.get('end_time') or '').strip()
            severity = (row.get('severity') or '').strip() or '?'
            if not (date and start_t and end_t):
                continue
            start_dt = f'{date} {start_t}:00'
            end_dt = f'{date} {end_t}:00'
            desc = f"{date} {start_t}~{end_t} [{severity}]"
            incidents.append({
                'start': start_dt,
                'end': end_dt,
                'desc': desc,
            })
    return incidents


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--csv', help='단일 사건단위 CSV 경로')
    p.add_argument('--dir', help='사건단위 CSV들이 있는 폴더 (예: out)')
    p.add_argument('--out', default='incidents.json', help='출력 JSON 경로')
    args = p.parse_args()

    all_incidents = []

    if args.csv:
        all_incidents = parse_사건단위_csv(args.csv)
        print(f'📥 {args.csv} → {len(all_incidents)} 사건')
    elif args.dir:
        if not os.path.isdir(args.dir):
            sys.exit(f'폴더 없음: {args.dir}')
        pattern = os.path.join(args.dir, '*_사건단위.csv')
        files = sorted(glob.glob(pattern))
        if not files:
            sys.exit(f'사건단위 CSV가 없습니다 (패턴: {pattern})')
        for f in files:
            incidents = parse_사건단위_csv(f)
            print(f'  {os.path.basename(f)}: {len(incidents)} 사건')
            all_incidents.extend(incidents)
    else:
        sys.exit('--csv 또는 --dir 중 하나 필수')

    if not all_incidents:
        sys.exit('❌ 사건 0건 — incidents.json 안 만듦')

    # 중복 제거 (start+end 키 기준)
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
    print(f'\n첫 3건 미리보기:')
    for inc in all_incidents[:3]:
        print(f'  · {inc["start"]} ~ {inc["end"]}  ({inc.get("desc", "")})')


if __name__ == '__main__':
    main()
