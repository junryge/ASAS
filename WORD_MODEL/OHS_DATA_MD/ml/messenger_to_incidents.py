#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
운영자 메신저 로그 → ML 학습용 사건 라벨 (라벨 B)

흐름:
    masame.txt → 운영로그_파서.py → 운영로그_파싱.csv → 본 스크립트 → incidents_B_messenger.json

핵심 사건 타입 (운영자가 실제 인지한 사건):
    - DEADLOCK_SIGNAL  정체/몰림/밀림    ★ 가장 직접적
    - BRIDGE_ERROR     Bridge OHT 이상
    - MLUD_ISSUE       MLUD 관련
    - Q_OVER           Q-OVER, T-OVER, 반송 지연
    - (선택) LIFTER_DOWN, ERROR_OCCURRED

사용:
    # 1단계: masame.txt 파싱 (기존 운영로그_파서.py)
    python 운영로그_파서.py masame.txt 운영로그.csv

    # 2단계: 사건 라벨 추출
    python messenger_to_incidents.py --csv 운영로그.csv --out incidents_B_messenger.json

    # 옵션
    python messenger_to_incidents.py --csv 운영로그.csv --out incidents_B.json \\
        --types DEADLOCK_SIGNAL,BRIDGE_ERROR,MLUD_ISSUE \\
        --before_min 30 --after_min 30 --gap_min 60

라벨 윈도우 (기본):
    incident.start = 메신저 시간 - 30분  (사건이 메시지 작성 전부터 시작됐을 것)
    incident.end   = 메신저 시간 + 30분  (조치 완료까지)
    gap 60분 이내 같은 타입 메시지는 같은 사건으로 묶음 (확장)
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta


# 사건 라벨로 쓸 event_type (운영로그_파서.py 출력 기준)
DEFAULT_INCIDENT_TYPES = [
    'DEADLOCK_SIGNAL',  # 정체/몰림/밀림 — 가장 직접적
    'BRIDGE_ERROR',     # Bridge OHT 이상
    'MLUD_ISSUE',       # MLUD
    'Q_OVER',           # Q-OVER, 반송 지연
]

# 추가 후보 (선택)
OPTIONAL_TYPES = [
    'LIFTER_DOWN',
    'ERROR_OCCURRED',
]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--csv', required=True, help='운영로그_파서.py 출력 CSV')
    p.add_argument('--out', default='incidents_B_messenger.json', help='출력 JSON')
    p.add_argument('--types', default=','.join(DEFAULT_INCIDENT_TYPES),
                   help='사건으로 볼 event_type (쉼표 구분)')
    p.add_argument('--before_min', type=int, default=30,
                   help='메시지 시간 이전 분 (사건 시작점, 기본 30)')
    p.add_argument('--after_min', type=int, default=30,
                   help='메시지 시간 이후 분 (사건 종료점, 기본 30)')
    p.add_argument('--gap_min', type=int, default=60,
                   help='gap 이내 같은 사건으로 묶음 (기본 60)')
    p.add_argument('--include_optional', action='store_true',
                   help='LIFTER_DOWN, ERROR_OCCURRED 도 포함')
    return p.parse_args()


def load_events(csv_path, allowed_types):
    """운영로그 CSV → 사건성 메시지만 추출."""
    events = []
    if not os.path.exists(csv_path):
        sys.exit(f'❌ CSV 없음: {csv_path}')

    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ev_type = (row.get('event_type') or '').strip()
            if ev_type not in allowed_types:
                continue
            dt_str = (row.get('datetime') or '').strip()
            try:
                dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
            except ValueError:
                continue
            events.append({
                'datetime': dt,
                'event_type': ev_type,
                'keyword': (row.get('keyword') or '').strip(),
                'summary': (row.get('message_summary') or '').strip(),
                'author': (row.get('author') or '').strip(),
            })

    events.sort(key=lambda e: e['datetime'])
    return events


def cluster_to_incidents(events, before_min, after_min, gap_min):
    """근접 메시지를 한 사건으로 묶음."""
    if not events:
        return []

    incidents = []
    cur_start = events[0]['datetime']
    cur_end = events[0]['datetime']
    cur_msgs = [events[0]]

    for ev in events[1:]:
        if (ev['datetime'] - cur_end).total_seconds() / 60.0 <= gap_min:
            # 같은 사건 — 확장
            cur_end = ev['datetime']
            cur_msgs.append(ev)
        else:
            # 새 사건
            incidents.append(_finalize(cur_start, cur_end, cur_msgs, before_min, after_min))
            cur_start = ev['datetime']
            cur_end = ev['datetime']
            cur_msgs = [ev]

    incidents.append(_finalize(cur_start, cur_end, cur_msgs, before_min, after_min))
    return incidents


def _finalize(cluster_start, cluster_end, msgs, before_min, after_min):
    """클러스터 → incident JSON 1건."""
    inc_start = cluster_start - timedelta(minutes=before_min)
    inc_end = cluster_end + timedelta(minutes=after_min)

    # 사건 타입 분포 (가장 많은 타입을 대표)
    type_count = {}
    for m in msgs:
        type_count[m['event_type']] = type_count.get(m['event_type'], 0) + 1
    main_type = max(type_count, key=type_count.get)

    # 첫 메시지 요약
    first_msg = msgs[0]['summary'][:60]
    n_msgs = len(msgs)

    desc = (
        f"[{main_type}] {cluster_start.strftime('%Y-%m-%d %H:%M')} "
        f"({n_msgs}건) {first_msg}"
    )

    return {
        'start': inc_start.strftime('%Y-%m-%d %H:%M:%S'),
        'end': inc_end.strftime('%Y-%m-%d %H:%M:%S'),
        'desc': desc,
        'source': 'messenger',
        'event_type': main_type,
        'message_count': n_msgs,
        'first_message_time': cluster_start.strftime('%Y-%m-%d %H:%M:%S'),
        'last_message_time': cluster_end.strftime('%Y-%m-%d %H:%M:%S'),
        'authors': sorted(set(m['author'] for m in msgs)),
    }


def main():
    args = parse_args()
    allowed = set(args.types.split(','))
    if args.include_optional:
        allowed |= set(OPTIONAL_TYPES)
    allowed = {t.strip() for t in allowed if t.strip()}

    print(f'📥 CSV: {args.csv}')
    print(f'   허용 event_type: {sorted(allowed)}')
    print(f'   윈도우: 메시지 -{args.before_min}분 ~ +{args.after_min}분')
    print(f'   클러스터링 gap: {args.gap_min}분')
    print()

    events = load_events(args.csv, allowed)
    print(f'📊 추출된 메시지: {len(events)}건')
    if not events:
        sys.exit('❌ 매칭 메시지 0건')

    # 타입별 분포
    type_dist = {}
    for ev in events:
        type_dist[ev['event_type']] = type_dist.get(ev['event_type'], 0) + 1
    for t, c in sorted(type_dist.items(), key=lambda x: -x[1]):
        print(f'   {t:<22} {c}건')

    print()
    incidents = cluster_to_incidents(events, args.before_min, args.after_min, args.gap_min)
    print(f'✅ 클러스터링 후 사건: {len(incidents)}건')

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(incidents, f, ensure_ascii=False, indent=2)
    print(f'   저장: {args.out}')

    print()
    print('첫 5건 미리보기:')
    for inc in incidents[:5]:
        print(f'  · {inc["start"]} ~ {inc["end"]}')
        print(f'    {inc["desc"]}')


if __name__ == '__main__':
    main()
