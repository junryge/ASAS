#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EVENT_FIELDS / INCIDENT_FIELDS 누락 자동 점검

검사 항목:
  1. eval_area_rules 가 계산하는 모든 영역별 키 → EVENT_FIELDS 에 노출되는가
  2. IncidentTracker 가 추적하는 모든 영역별 키 → INCIDENT_FIELDS 에 노출되는가
  3. 영역 점수 9 룰 (RA/RA_sus/RB/RB_fast/RC/RD/SLA/SORT/MAXCAPA) 가 모두 분해되는가
  4. 룰베이스가 평가하지만 출력 안 되는 컬럼 (sorter_fail, oht_cmd 등)
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREDICTOR = HERE / 'hubroom_predictor.py'

src = PREDICTOR.read_text(encoding='utf-8')

# 1. eval_area_rules 의 out['*'] = ... 형태로 설정되는 모든 키
out_keys = set(re.findall(r"out\['(\w+)'\]\s*=", src))
print(f'eval_area_rules 가 계산하는 영역별 키: {len(out_keys)}')
for k in sorted(out_keys):
    print(f'  - {k}')

print()

# 2. EVENT_FIELDS 에서 사용 가능한 영역별 키 패턴 매칭
# {area}_{key} 형태 추출
event_match = re.search(r'EVENT_FIELDS\s*=\s*\[(.*?)\n\]', src, re.S)
event_text = event_match.group(1) if event_match else ''
event_fields = re.findall(r"'([^']+)'", event_text)
print(f'EVENT_FIELDS 총 컬럼: {len(event_fields)}')

# 영역별 키 추출
AREAS = ['M16HUB', 'M14B', 'M14', 'M16A', 'M16B', 'M16_PKT', 'M16_WT', 'M16']
area_field_keys = {}  # {area: set of keys}
for area in AREAS:
    keys = set()
    for f in event_fields:
        if f.startswith(area + '_'):
            keys.add(f[len(area)+1:])
        elif f.endswith('_' + area):
            keys.add(f[:-(len(area)+1)] + '_PREFIX')
    area_field_keys[area] = keys

print()
print('영역별 EVENT_FIELDS 노출 키:')
for area, keys in area_field_keys.items():
    print(f'  {area:10s}: {sorted(keys)}')

print()

# 3. event_to_row 가 실제로 영역별로 매핑하는 키 추출
e2r_pattern = re.compile(r"A\('(\w+)',\s*'(\w+)'")
e2r_keys = set()
e2r_by_area = {}
for m in e2r_pattern.finditer(src):
    area, key = m.groups()
    e2r_keys.add((area, key))
    e2r_by_area.setdefault(area, set()).add(key)

print(f'event_to_row 에서 영역별로 가져오는 키: {len(e2r_keys)}')
for area in sorted(e2r_by_area):
    print(f'  {area}: {sorted(e2r_by_area[area])}')

print()
print('=' * 60)
print('누락 분석')
print('=' * 60)

# 4. out_keys 중 EVENT_FIELDS / event_to_row 에 노출 안 되는 키
expose_score_keys = {  # 통합 영역의 출력 키 패턴
    'M16HUB': {'score', 'signals', 'ra', 'rb_diff30', 'rd_fab', 'stb_util', 'rev_count', 'rev_lids',
               'pts_RA', 'pts_RA_sus', 'pts_RB', 'pts_RB_fast', 'pts_RC', 'pts_RD'},
    'M14':    {'score', 'signals', 'ra', 'rb_diff30',
               'pts_RA', 'pts_RA_sus', 'pts_RB', 'pts_RB_fast', 'pts_RC', 'pts_RD'},
    'M14B':   {'score', 'signals', 'ra', 'rb_diff30',
               'pts_RA', 'pts_RA_sus', 'pts_RB', 'pts_RB_fast', 'pts_RC', 'pts_RD'},
    'M16A':   {'score', 'signals', 'ra', 'rb_diff30',
               'pts_RA', 'pts_RA_sus', 'pts_RB', 'pts_RB_fast', 'pts_RC', 'pts_RD'},
    'M16B':   {'score', 'signals', 'ra',
               'pts_RA', 'pts_RA_sus', 'pts_RB', 'pts_RB_fast', 'pts_RC', 'pts_RD'},
    'M16':     {'score'},
    'M16_PKT': {'score'},
    'M16_WT':  {'score'},
}

# eval_area_rules out 키 = 모든 영역에 공통 (영역마다 같은 dict 키)
ALL_OUT_KEYS = sorted(out_keys)
print(f'\n[1] 모든 영역의 out dict 키 ({len(ALL_OUT_KEYS)}개):')
for k in ALL_OUT_KEYS:
    print(f'   - {k}')

# 5. 평가는 하는데 출력 안 되는 키 (누락 후보)
# 각 영역마다 expose_score_keys 에 없는 out_key 들
print()
print('[2] 각 영역에서 평가하지만 출력 안 되는 키 (잠재 누락):')
for area, exposed in expose_score_keys.items():
    not_exposed = []
    for k in ALL_OUT_KEYS:
        # 출력 키 매핑: area_score → score, area_signals → signals 등
        canonical = k
        if k == 'area_score':   canonical = 'score'
        elif k == 'area_signals': canonical = 'signals'
        elif k == 'ra_value':   canonical = 'ra'
        elif k == 'rb_diff_30': canonical = 'rb_diff30'
        elif k == 'rd_fab':     canonical = 'rd_fab'
        elif k == 'hub_stb_util': canonical = 'stb_util'
        elif k == 'rev_count':  canonical = 'rev_count'
        elif k == 'rev_lids':   canonical = 'rev_lids'
        elif k.startswith('pts_'): canonical = k  # 그대로
        else:
            # 출력 안 되는 내부 키
            canonical = None

        if canonical is None:
            not_exposed.append(k + ' (내부키)')
        elif canonical not in exposed:
            not_exposed.append(k + f' → {canonical}')

    if not_exposed:
        print(f'  {area}:')
        for k in not_exposed:
            print(f'    ❌ {k}')

# 6. SLA/SORT/MAXCAPA 영역별 분해 누락 확인
print()
print('[3] 영역 점수 9 룰 중 영역별 pts 분해 빠진 룰:')
for area in ['M16HUB', 'M14', 'M14B', 'M16A', 'M16B']:
    missing = []
    for rule in ['RA', 'RA_sus', 'RB', 'RB_fast', 'RC', 'RD', 'SLA', 'SORT', 'MAXCAPA']:
        col = f'{area}_pts_{rule}'
        if col not in event_fields:
            missing.append(col)
    if missing:
        print(f'  {area}: 누락 {missing}')

# 7. 영역별 비대칭 (있어야 하는데 빠진 컬럼)
print()
print('[4] 영역별 비대칭 (대칭 깨진 컬럼):')
print('  rb_diff30 컬럼:')
for area in ['M16HUB', 'M14', 'M14B', 'M16A', 'M16B']:
    col = f'{area}_rb_diff30'
    status = '✓' if col in event_fields else '❌'
    print(f'    {status} {col}')

print('  sla_ 컬럼:')
for area in ['M16HUB', 'M14', 'M14B', 'M16A', 'M16B']:
    col = f'sla_{area}'
    status = '✓' if col in event_fields else '❌'
    print(f'    {status} {col}')

print('  sorter_ 컬럼:')
for area in ['M16HUB', 'M14', 'M14B', 'M16A', 'M16B']:
    col = f'sorter_{area}'
    status = '✓' if col in event_fields else '❌'
    print(f'    {status} {col}')

# 8. 평가 결과로 채워지는데 EVENT_FIELDS 에 없는 영역별 내부 키
print()
print('[5] eval_area_rules 의 영역별 평가 결과 중 출력 안 되는 키:')
internal_only = {
    'ra_trig', 'ra_sustained', 'ra_count',
    'rb_trig', 'rb_fast', 'rb_diff_10',
    'rc_trig', 'rc_trend',
    'rd_trig', 'rd_oht',
    'sla_trig', 'sla_cnt',
    'sorter_trig', 'sorter_val',
    'sorter_fail_trig', 'sorter_fail_val',
    'maxcapa_changed', 'maxcapa_changed_n',
    'area_score_raw', 'cnv_skew',
    'pts_SLA', 'pts_SORT', 'pts_MAXCAPA',
}
for k in sorted(internal_only & out_keys):
    print(f'  ⚠ {k} — 평가 결과 있지만 EVENT_FIELDS 에 영역별 노출 없음')
