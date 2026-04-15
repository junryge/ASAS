#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OHT 1차 결합 분석 스크립트
- M14_OHT (VHL 상태) + 스타 (운영 지표) + HID_INOUT (구간 흐름) + RAIL_CUT (레일 차단)
- Usage: python analyze_combined.py
"""

import csv
import sys
import statistics
from collections import Counter, defaultdict
from datetime import datetime

# ============================================================
# Enum 매핑
# ============================================================
VHL_STATE_MAP = {
    "1": "RUN", "2": "STOP", "3": "ABNORMAL", "4": "MANUAL",
    "5": "REMOVING", "6": "OBS_BZ_STOP", "7": "JAM",
    "8": "HT_STOP", "9": "E84_TIMEOUT",
}
RUN_CYCLE_MAP = {
    "0": "NONE", "1": "POSITION_DETECT", "2": "MOVING",
    "3": "ACQUIRE", "4": "DEPOSIT", "5": "SAMPLING",
}
VHL_CYCLE_MAP = {
    "0": "NONE", "1": "MOVING", "2": "ACQUIRE_MOVING",
    "3": "ACQUIRING", "4": "DEPOSIT_MOVING", "5": "DEPOSITING",
    "6": "MAINT_MOVING", "7": "WAITING",
}
VHL_DET_STATE_MAP = {
    "0": "NONE", "1": "WAIT", "2": "STAGE_WAIT",
    "101": "MOVING", "103": "STAGE_MOVING", "105": "BALANCE_MOVING",
}


def parse_time(t):
    try:
        return datetime.strptime(t[:19], '%Y-%m-%d %H:%M:%S')
    except:
        return None


def to_minute_key(t):
    """시간을 분 단위 키로 변환 (HH:MM)"""
    try:
        parts = t.split(' ')[1].split(':')
        return f"{parts[0]}:{parts[1]}"
    except:
        return None


# ============================================================
# 1. 데이터 로드
# ============================================================
def load_m14_oht(path):
    """M14_OHT 데이터 로드 (Type 2만)"""
    print("[1/4] M14_OHT 로드 중...")
    records = []
    with open(path, 'r') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) > 4:
                parts = row[4].split(',')
                if parts[0] == '2' and len(parts) == 21:
                    records.append({
                        'time': row[3],
                        'minute': to_minute_key(row[3]),
                        'vid': parts[2],
                        'state': parts[3],
                        'loaded': parts[4],
                        'cur_addr': parts[7],
                        'distance': parts[8],
                        'next_addr': parts[9],
                        'run_cycle': parts[10],
                        'vhl_cycle': parts[11],
                        'carrier': parts[12],
                        'source': parts[16],
                        'dest': parts[17],
                        'speed': parts[18],
                        'det_state': parts[19],
                    })
    print(f"  {len(records):,}건 로드")
    return records


def load_quwa(path):
    """스타 데이터 로드"""
    print("[2/4] 스타 로드 중...")
    records = []
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mk = to_minute_key(row['CRT_TM'])
            records.append({
                'time': row['CRT_TM'],
                'minute': mk,
                'queue_cnt': int(row['M14.QUE.ALL.CURRENTQCNT']) if row['M14.QUE.ALL.CURRENTQCNT'] else None,
                'completed': int(row['M14.QUE.ALL.CURRENTQCOMPLETED']) if row['M14.QUE.ALL.CURRENTQCOMPLETED'] else None,
                'oht_queue': int(row['M14.QUE.OHT.CURRENTOHTQCNT']) if row['M14.QUE.OHT.CURRENTOHTQCNT'] else None,
                'avg_load_time': float(row['M14.QUE.LOAD.AVGLOADTIME']) if row['M14.QUE.LOAD.AVGLOADTIME'] else None,
                'delay_cnt': int(row['M14.QUE.ALL.TRANSPORT4MINOVERCNT']) if row['M14.QUE.ALL.TRANSPORT4MINOVERCNT'] else None,
                'driving': int(row['M14.OHT.STATECNT.DRIVING']) if row['M14.OHT.STATECNT.DRIVING'] else None,
                'obs_stop': int(row['M14.OHT.STATECNT.OBSANDBZSTOP']) if row['M14.OHT.STATECNT.OBSANDBZSTOP'] else None,
                'congested': int(row['M14.OHT.STATECNT.CONGESTED']) if row['M14.OHT.STATECNT.CONGESTED'] else None,
                'pause': int(row['M14.OHT.STATECNT.PAUSE']) if row['M14.OHT.STATECNT.PAUSE'] else None,
                'timeout': int(row['M14.OHT.STATECNT.TIMEOUT']) if row['M14.OHT.STATECNT.TIMEOUT'] else None,
            })
    print(f"  {len(records):,}건 로드")
    return records


def load_hid_inout(path):
    """HID_INOUT 데이터 로드"""
    print("[3/4] HID_INOUT 로드 중...")
    records = []
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append({
                'time': row['EVENT_DT'],
                'minute': to_minute_key(row['EVENT_DT']),
                'vid': row['VHL_ID'],
                'from_hid': row['FROM_HIDID'],
                'to_hid': row['TO_HIDID'],
                'speed': float(row['FREE_FLOW_SPEED']) if row['FREE_FLOW_SPEED'] else 0,
                'vhl_limit': int(row['VHL_COUNT_LIMIT']) if row['VHL_COUNT_LIMIT'] else 0,
                'vhl_precaution': int(row['VHL_PRECAUTION']) if row['VHL_PRECAUTION'] else 0,
                'trans_cnt': int(row['TRANS_CNT']) if row['TRANS_CNT'] else 0,
                'hid_value': row.get('HID_VALUE', ''),
            })
    print(f"  {len(records):,}건 로드")
    return records


def load_rail_cut(path):
    """RAIL_CUT 데이터 로드"""
    print("[4/4] RAIL_CUT 로드 중...")
    records = []
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            affected = row['AFFECT_ADDR_LST'].split(',') if row['AFFECT_ADDR_LST'] else []
            records.append({
                'time': row['EVENT_DT'],
                'from_addr': row['FROM_ADDR'],
                'to_addr': row['TO_ADDR'],
                'state': row['STATE'],
                'affected_count': len(affected),
                'affected_addrs': row['AFFECT_ADDR_LST'],
            })
    print(f"  {len(records):,}건 로드")
    return records


# ============================================================
# 2. 분석 함수들
# ============================================================
def analyze_data_overview(m14, quwa, hid, rail):
    lines = []
    lines.append("## 1. 데이터 개요\n")
    lines.append("| 데이터 | 건수 | 시간범위 | 설명 |")
    lines.append("|--------|------|---------|------|")
    lines.append(f"| M14_OHT | {len(m14):,} | 08:30~17:00 | VHL 개별 상태 (위치, 속도, 적재) |")
    lines.append(f"| 스타 | {len(quwa):,} | 08:30~17:00 | 반송 큐, 가동률, 상태 집계 (1분) |")
    lines.append(f"| HID_INOUT | {len(hid):,} | 08:30~17:00 | HID 구간별 차량 진입/이탈 |")
    lines.append(f"| RAIL_CUT | {len(rail):,} | 09:00:28 | 레일 차단 이벤트 |")
    lines.append("")
    return '\n'.join(lines)


def analyze_quwa_trends(quwa):
    """스타 시간대별 추이 분석"""
    lines = []
    lines.append("## 2. 스타 운영 지표 추이\n")

    # 시간대별 평균
    hourly = defaultdict(lambda: defaultdict(list))
    for r in quwa:
        if r['minute'] is None:
            continue
        h = r['minute'].split(':')[0]
        if r['queue_cnt'] is not None:
            hourly[h]['queue'].append(r['queue_cnt'])
        if r['completed'] is not None:
            hourly[h]['completed'].append(r['completed'])
        if r['driving'] is not None:
            hourly[h]['driving'].append(r['driving'])
        if r['obs_stop'] is not None:
            hourly[h]['obs'].append(r['obs_stop'])
        if r['avg_load_time'] is not None:
            hourly[h]['load_time'].append(r['avg_load_time'])
        if r['delay_cnt'] is not None:
            hourly[h]['delay'].append(r['delay_cnt'])

    lines.append("### 시간대별 주요 지표 평균\n")
    lines.append("| 시간 | 반송큐 | 10분완료 | 평균반송시간 | 운전중 | OBS정지 | 4분초과 |")
    lines.append("|------|--------|---------|------------|--------|---------|--------|")
    for h in sorted(hourly.keys()):
        d = hourly[h]
        q = f"{statistics.mean(d['queue']):.0f}" if d['queue'] else "-"
        c = f"{statistics.mean(d['completed']):.0f}" if d['completed'] else "-"
        lt = f"{statistics.mean(d['load_time']):.2f}분" if d['load_time'] else "-"
        dr = f"{statistics.mean(d['driving']):.0f}" if d['driving'] else "-"
        obs = f"{statistics.mean(d['obs']):.0f}" if d['obs'] else "-"
        dl = f"{statistics.mean(d['delay']):.0f}" if d['delay'] else "-"
        lines.append(f"| {h}:00 | {q} | {c} | {lt} | {dr} | {obs} | {dl} |")

    # 큐 vs OBS 상관관계
    lines.append("\n### 반송큐 구간별 OBS_BZ_STOP 평균\n")
    lines.append("| 반송큐 구간 | 평균 OBS정지 | 평균 반송시간 | 건수 |")
    lines.append("|-----------|------------|------------|------|")
    brackets = [(1000, 1200), (1200, 1400), (1400, 1600), (1600, 1800), (1800, 2000)]
    for lo, hi in brackets:
        obs_vals = []
        lt_vals = []
        cnt = 0
        for r in quwa:
            if r['queue_cnt'] is not None and lo <= r['queue_cnt'] < hi:
                if r['obs_stop'] is not None:
                    obs_vals.append(r['obs_stop'])
                if r['avg_load_time'] is not None:
                    lt_vals.append(r['avg_load_time'])
                cnt += 1
        if obs_vals:
            lines.append(f"| {lo}~{hi} | {statistics.mean(obs_vals):.1f}대 | {statistics.mean(lt_vals):.2f}분 | {cnt} |")

    lines.append("")
    return '\n'.join(lines)


def analyze_m14_quwa_correlation(m14, quwa):
    """M14_OHT와 스타 결합 분석"""
    lines = []
    lines.append("## 3. M14_OHT + 스타 결합 분석\n")

    # 분 단위로 M14_OHT 집계
    m14_minute = defaultdict(lambda: {
        'total': 0, 'run': 0, 'obs': 0, 'loaded': 0,
        'speed_0': 0, 'speed_50': 0, 'speed_80plus': 0,
    })
    for r in m14:
        mk = r['minute']
        if mk is None:
            continue
        m14_minute[mk]['total'] += 1
        if r['state'] == '1':
            m14_minute[mk]['run'] += 1
        if r['state'] == '6':
            m14_minute[mk]['obs'] += 1
        if r['loaded'] == '1':
            m14_minute[mk]['loaded'] += 1
        if r['speed'] == '0':
            m14_minute[mk]['speed_0'] += 1
        elif r['speed'] == '50':
            m14_minute[mk]['speed_50'] += 1
        elif r['speed'] in ('80', '90', '99'):
            m14_minute[mk]['speed_80plus'] += 1

    # 스타와 매칭
    quwa_map = {r['minute']: r for r in quwa if r['minute']}

    lines.append("### 스타 반송큐 vs M14_OHT 상태 상관관계\n")
    lines.append("| 반송큐 구간 | M14 OBS비율 | M14 적재율 | M14 속도0 비율 | 스타 OBS정지 |")
    lines.append("|-----------|-----------|----------|-------------|------------|")

    brackets = [(1000, 1200), (1200, 1400), (1400, 1600), (1600, 1800), (1800, 2000)]
    for lo, hi in brackets:
        obs_ratios = []
        load_ratios = []
        speed0_ratios = []
        quwa_obs = []
        for mk, qr in quwa_map.items():
            if qr['queue_cnt'] is not None and lo <= qr['queue_cnt'] < hi:
                m = m14_minute.get(mk)
                if m and m['total'] > 0:
                    obs_ratios.append(m['obs'] / m['total'] * 100)
                    load_ratios.append(m['loaded'] / m['total'] * 100)
                    speed0_ratios.append(m['speed_0'] / m['total'] * 100)
                if qr['obs_stop'] is not None:
                    quwa_obs.append(qr['obs_stop'])
        if obs_ratios:
            lines.append(f"| {lo}~{hi} | {statistics.mean(obs_ratios):.1f}% | {statistics.mean(load_ratios):.1f}% | {statistics.mean(speed0_ratios):.1f}% | {statistics.mean(quwa_obs):.0f}대 |")

    lines.append("")
    return '\n'.join(lines)


def analyze_hid_flow(hid):
    """HID 구간별 흐름 분석"""
    lines = []
    lines.append("## 4. HID 구간 흐름 분석\n")

    # HID별 통계
    hid_stats = defaultdict(lambda: {'count': 0, 'speeds': [], 'vhls': set()})
    hourly_flow = defaultdict(lambda: defaultdict(int))

    for r in hid:
        fh = r['from_hid']
        hid_stats[fh]['count'] += 1
        hid_stats[fh]['speeds'].append(r['speed'])
        hid_stats[fh]['vhls'].add(r['vid'])
        if r['minute']:
            h = r['minute'].split(':')[0]
            hourly_flow[h][fh] += 1

    lines.append(f"- 총 HID 구간: {len(hid_stats)}개")
    lines.append(f"- 총 이벤트: {len(hid):,}건")
    lines.append(f"- 고유 차량: {len(set(r['vid'] for r in hid)):,}대\n")

    # Top 20 혼잡 HID
    lines.append("### Top 20 통과량 HID 구간\n")
    lines.append("| HID | 통과 건수 | 평균 속도 | 최저 속도 | 고유 차량 |")
    lines.append("|-----|----------|----------|----------|----------|")
    for hid_id, stats in sorted(hid_stats.items(), key=lambda x: -x[1]['count'])[:20]:
        avg_spd = statistics.mean(stats['speeds'])
        min_spd = min(stats['speeds'])
        lines.append(f"| {hid_id} | {stats['count']:,} | {avg_spd:.1f} | {min_spd:.1f} | {len(stats['vhls'])} |")

    # 속도 분포
    all_speeds = [r['speed'] for r in hid]
    lines.append("\n### 전체 FREE_FLOW_SPEED 분포\n")
    lines.append("| 구간 | 건수 | 비율 |")
    lines.append("|------|------|------|")
    spd_brackets = [(50, 70), (70, 80), (80, 90), (90, 100), (100, 110), (110, 135)]
    for lo, hi in spd_brackets:
        cnt = sum(1 for s in all_speeds if lo <= s < hi)
        lines.append(f"| {lo}~{hi} | {cnt:,} | {cnt/len(all_speeds)*100:.1f}% |")

    # HID별 혼잡도 (속도 낮은 구간)
    lines.append("\n### 저속 구간 Top 10 (평균 속도 낮은 HID)\n")
    lines.append("| HID | 평균 속도 | 통과 건수 | VHL 한계 |")
    lines.append("|-----|----------|----------|---------|")
    slow_hids = [(hid_id, statistics.mean(stats['speeds']), stats['count'])
                 for hid_id, stats in hid_stats.items() if stats['count'] >= 100]
    for hid_id, avg_spd, cnt in sorted(slow_hids, key=lambda x: x[1])[:10]:
        limit = 0
        for r in hid:
            if r['from_hid'] == hid_id:
                limit = r['vhl_limit']
                break
        lines.append(f"| {hid_id} | {avg_spd:.1f} | {cnt:,} | {limit} |")

    # 시간대별 총 흐름
    lines.append("\n### 시간대별 HID 통과량\n")
    lines.append("| 시간 | 총 통과 건수 | 분당 평균 |")
    lines.append("|------|-----------|----------|")
    for h in sorted(hourly_flow.keys()):
        total = sum(hourly_flow[h].values())
        lines.append(f"| {h}:00 | {total:,} | {total/60:.0f} |")

    lines.append("")
    return '\n'.join(lines)


def analyze_hid_quwa_correlation(hid, quwa):
    """HID 흐름 + 스타 결합"""
    lines = []
    lines.append("## 5. HID 흐름 + 스타 결합 분석\n")

    # 분 단위 HID 집계
    hid_minute = defaultdict(lambda: {'count': 0, 'speeds': []})
    for r in hid:
        mk = r['minute']
        if mk:
            hid_minute[mk]['count'] += 1
            hid_minute[mk]['speeds'].append(r['speed'])

    quwa_map = {r['minute']: r for r in quwa if r['minute']}

    # 큐 vs HID 속도
    lines.append("### 반송큐 구간별 HID 평균 속도\n")
    lines.append("| 반송큐 구간 | HID 평균 속도 | HID 분당 통과 | 건수 |")
    lines.append("|-----------|-------------|-------------|------|")
    brackets = [(1000, 1200), (1200, 1400), (1400, 1600), (1600, 1800), (1800, 2000)]
    for lo, hi in brackets:
        speeds = []
        flows = []
        cnt = 0
        for mk, qr in quwa_map.items():
            if qr['queue_cnt'] is not None and lo <= qr['queue_cnt'] < hi:
                hm = hid_minute.get(mk)
                if hm and hm['speeds']:
                    speeds.extend(hm['speeds'])
                    flows.append(hm['count'])
                    cnt += 1
        if speeds:
            lines.append(f"| {lo}~{hi} | {statistics.mean(speeds):.1f} | {statistics.mean(flows):.0f} | {cnt} |")

    lines.append("")
    return '\n'.join(lines)


def analyze_rail_cut(rail):
    """RAIL_CUT 분석"""
    lines = []
    lines.append("## 6. RAIL_CUT (레일 차단) 분석\n")
    lines.append(f"- 총 {len(rail)}건 (중복 포함)")

    # 중복 제거
    unique = {}
    for r in rail:
        key = f"{r['from_addr']}_{r['to_addr']}"
        unique[key] = r

    lines.append(f"- 고유 차단 구간: {len(unique)}개")
    lines.append(f"- 발생 시각: {rail[0]['time'] if rail else 'N/A'}\n")

    lines.append("| 구간 | 상태 | 영향 엣지 수 |")
    lines.append("|------|------|------------|")
    for key, r in unique.items():
        lines.append(f"| {r['from_addr']}→{r['to_addr']} | {r['state']} | {r['affected_count']}개 |")

    total_affected = sum(r['affected_count'] for r in unique.values())
    lines.append(f"\n- 총 영향받는 엣지: {total_affected}개")
    lines.append("")
    return '\n'.join(lines)


def analyze_world_model_params(m14, quwa, hid):
    """월드 모델 파라미터 추출"""
    lines = []
    lines.append("## 7. 월드 모델 파라미터 (결합 데이터 기반)\n")

    # 1. 속도 프로파일 (HID 기준 - 실제 구간 속도)
    lines.append("### 7.1 구간 속도 프로파일 (HID_INOUT 기준)\n")
    all_speeds = [r['speed'] for r in hid]
    lines.append("| 지표 | 값 |")
    lines.append("|------|-----|")
    lines.append(f"| 평균 | {statistics.mean(all_speeds):.1f} |")
    lines.append(f"| 중앙값 | {statistics.median(all_speeds):.1f} |")
    lines.append(f"| 최소 | {min(all_speeds):.1f} |")
    lines.append(f"| 최대 | {max(all_speeds):.1f} |")
    lines.append(f"| 표준편차 | {statistics.stdev(all_speeds):.1f} |")

    # 2. 큐 패턴
    lines.append("\n### 7.2 반송큐 패턴 (스타 기준)\n")
    queues = [r['queue_cnt'] for r in quwa if r['queue_cnt'] is not None]
    completed = [r['completed'] for r in quwa if r['completed'] is not None]
    lines.append("| 지표 | 반송큐 | 10분 완료 |")
    lines.append("|------|--------|---------|")
    lines.append(f"| 평균 | {statistics.mean(queues):.0f} | {statistics.mean(completed):.0f} |")
    lines.append(f"| 중앙값 | {statistics.median(queues):.0f} | {statistics.median(completed):.0f} |")
    lines.append(f"| 최소 | {min(queues)} | {min(completed)} |")
    lines.append(f"| 최대 | {max(queues)} | {max(completed)} |")

    # 3. OBS 발생률 vs 큐
    lines.append("\n### 7.3 핵심 상관관계 요약\n")
    lines.append("| 현상 | 데이터 근거 |")
    lines.append("|------|-----------|")

    # 큐 높을 때 OBS 증가?
    high_q_obs = [r['obs_stop'] for r in quwa if r['queue_cnt'] and r['queue_cnt'] > 1600 and r['obs_stop'] is not None]
    low_q_obs = [r['obs_stop'] for r in quwa if r['queue_cnt'] and r['queue_cnt'] < 1300 and r['obs_stop'] is not None]
    if high_q_obs and low_q_obs:
        lines.append(f"| 큐 높을 때(>1600) OBS 평균 | {statistics.mean(high_q_obs):.0f}대 |")
        lines.append(f"| 큐 낮을 때(<1300) OBS 평균 | {statistics.mean(low_q_obs):.0f}대 |")

    # 큐 높을 때 반송시간 증가?
    high_q_lt = [r['avg_load_time'] for r in quwa if r['queue_cnt'] and r['queue_cnt'] > 1600 and r['avg_load_time'] is not None]
    low_q_lt = [r['avg_load_time'] for r in quwa if r['queue_cnt'] and r['queue_cnt'] < 1300 and r['avg_load_time'] is not None]
    if high_q_lt and low_q_lt:
        lines.append(f"| 큐 높을 때(>1600) 평균 반송시간 | {statistics.mean(high_q_lt):.2f}분 |")
        lines.append(f"| 큐 낮을 때(<1300) 평균 반송시간 | {statistics.mean(low_q_lt):.2f}분 |")

    # HID 수용 한계
    limits = [r['vhl_limit'] for r in hid if r['vhl_limit'] > 0]
    precautions = [r['vhl_precaution'] for r in hid if r['vhl_precaution'] > 0]
    if limits:
        lines.append(f"| HID 구간 평균 수용 한계 | {statistics.mean(limits):.0f}대 |")
    if precautions:
        lines.append(f"| HID 구간 평균 주의 기준 | {statistics.mean(precautions):.0f}대 |")

    lines.append("")
    return '\n'.join(lines)


def analyze_bottleneck(quwa):
    """병목 여부 판단"""
    lines = []
    lines.append("## 8. 병목 여부 판단\n")

    # 시간대별 큐 평균
    hourly_q = defaultdict(list)
    hourly_obs = defaultdict(list)
    hourly_lt = defaultdict(list)
    hourly_spd_placeholder = defaultdict(list)
    for r in quwa:
        if r['minute'] is None:
            continue
        h = r['minute'].split(':')[0]
        if r['queue_cnt'] is not None:
            hourly_q[h].append(r['queue_cnt'])
        if r['obs_stop'] is not None:
            hourly_obs[h].append(r['obs_stop'])
        if r['avg_load_time'] is not None:
            hourly_lt[h].append(r['avg_load_time'])

    # 큐 최대 시간대 찾기
    peak_hour = max(hourly_q.keys(), key=lambda h: statistics.mean(hourly_q[h])) if hourly_q else None
    if peak_hour:
        peak_q = statistics.mean(hourly_q[peak_hour])
        avg_q = statistics.mean([v for vals in hourly_q.values() for v in vals])
        peak_obs = statistics.mean(hourly_obs.get(peak_hour, [0]))
        avg_obs = statistics.mean([v for vals in hourly_obs.values() for v in vals])
        peak_lt = statistics.mean(hourly_lt.get(peak_hour, [0]))
        avg_lt = statistics.mean([v for vals in hourly_lt.values() for v in vals])

        lines.append(f"큐 최대 시간대: **{peak_hour}시** (평균 {peak_q:.0f}개)\n")
        lines.append("| 지표 | 큐 최대 시간대 | 전체 평균 | 판단 |")
        lines.append("|------|-------------|----------|------|")

        lt_diff = abs(peak_lt - avg_lt) / avg_lt * 100
        obs_diff = abs(peak_obs - avg_obs) / avg_obs * 100 if avg_obs > 0 else 0

        lt_judge = "차이 미미" if lt_diff < 5 else ("주의" if lt_diff < 15 else "병목 징후")
        obs_judge = "차이 없음" if obs_diff < 5 else ("주의" if obs_diff < 15 else "병목 징후")

        lines.append(f"| 반송시간 | {peak_lt:.2f}분 | {avg_lt:.2f}분 | {lt_judge} |")
        lines.append(f"| OBS 정지 | {peak_obs:.0f}대 | {avg_obs:.0f}대 | {obs_judge} |")

        is_bottleneck = lt_diff >= 15 or obs_diff >= 15
        if is_bottleneck:
            lines.append(f"\n> **병목 징후가 관측되었습니다.** 큐 급증 시 반송시간/OBS 정지가 유의미하게 증가합니다.")
        else:
            lines.append(f"\n> **병목 없이 정상 운영된 것으로 판단됩니다.**")
            lines.append(f"> 시스템이 큐 증가를 충분히 소화하고 있으며, 병목 징후(반송시간 급증, OBS 폭증)는 관측되지 않았습니다.")
            lines.append(f"> 병목을 확인하려면 큐 2,000 이상 또는 이상 이벤트 발생 날의 데이터가 필요합니다.")

    lines.append("")
    return '\n'.join(lines)


def analyze_prediction_feasibility(m14, quwa):
    """예측 가능 여부 판단"""
    lines = []
    lines.append("## 9. 예측 가능 여부\n")

    dates = set(r.get('date', r['time'][:10]) for r in quwa if r.get('time'))
    num_days = len(dates)

    lines.append(f"현재 데이터: **{num_days}일치**\n")

    if num_days < 5:
        lines.append("```")
        lines.append("  1일치 데이터 → \"이 날은 이랬다\" (사실 확인)")
        lines.append("  예측을 하려면 → \"내일도 이럴 것이다\" (패턴 반복 확인 필요)")
        lines.append("```\n")
        lines.append("| 항목 | 현재 (1일) | 5일치 이상 확보 시 |")
        lines.append("|------|-----------|------------------|")
        lines.append("| 시간대별 큐 패턴 | 이 날만 그런지 모름 | 매일 반복이면 → 예측 가능 |")
        lines.append("| 반송시간 평균 | 이 날 기준 | 일별 비교 → 정상 범위 확정 |")
        lines.append("| HID 저속 구간 | 우연인지 모름 | 매일 느리면 → 구조적 병목 확정 |")
        lines.append("| 요일별 물동량 | 알 수 없음 | 요일별 패턴 → 예측 가능 |")
        lines.append(f"\n> **결론: 현재 {num_days}일치 데이터로는 '분석'까지만 가능하며, '예측'은 최소 5일치 데이터가 필요합니다.**")
    else:
        lines.append(f"> {num_days}일치 데이터로 패턴 반복 여부를 확인할 수 있습니다.")

    lines.append("")
    return '\n'.join(lines)


def analyze_summary(m14, quwa, hid, rail):
    """2차 분석 방향 및 데이터 출처"""
    lines = []
    lines.append("## 10. 2차 분석 방향\n")

    lines.append("### 2차 분석에 필요한 추가 데이터\n")
    lines.append("| # | 데이터 | 이유 |")
    lines.append("|---|--------|------|")
    lines.append("| 1 | CommandId (23필드 전체) | 개별 차량 작업 매칭 |")
    lines.append("| 2 | layout.xml | 노드/엣지 공간 관계 |")
    lines.append("| 3 | **최소 5일치 동일 데이터** | 일간 패턴 비교 → 예측 가능 여부 확인 |")
    lines.append("| 4 | HIDOFF 이벤트 (발생 시) | 구간 장애 분석 |")

    lines.append("\n### 2차 분석 코드 (준비 완료)\n")
    lines.append("| 파일 | 설명 |")
    lines.append("|------|------|")
    lines.append("| `analyze_phase1_inject.py` | 새 데이터 투입 시 재사용 가능한 분석 코드 |")
    lines.append("")
    lines.append("2차 분석에서 추가되는 항목:")
    lines.append("- **CommandId 분석**: 23필드 수집 후 차량별 작업 매칭, 시간대별 작업/Idle 비율")
    lines.append("- **다일자 비교**: 수 일치 데이터로 일간 패턴 반복 여부 확인")
    lines.append("- **HID 혼잡 패턴 심화**: 시간대별 속도 변동 구간, 큐 vs 특정 HID 속도 상관")
    lines.append("- **차량별 운행 패턴**: OBS 빈번 차량, idle 비율 높은 차량 식별")

    lines.append("\n---\n")
    lines.append("## 11. 데이터 출처 및 분석 코드\n")
    lines.append("### 데이터 출처\n")
    lines.append("| 데이터 | 출처 시스템 | 파일 |")
    lines.append("|--------|-----------|------|")
    lines.append("| M14_OHT | XSOHS (OHT 실시간 수집) | `OHS/XSOHS_extracted/raw.csv` |")
    lines.append("| 스타 | 스타 (FAB 운영 지표) | `OHS/OHT_컬럼수집_DATA.CSV` |")
    lines.append("| HID_INOUT | 로그프레소 | `OHS/LOGPRESSO_extracted/M14A_ATLAS_HID_INOUT_*.csv` |")
    lines.append("| RAIL_CUT | 로그프레소 | `OHS/LOGPRESSO_extracted/ATLAS_OHT_RAIL_CUT_*.csv` |")
    lines.append("\n### 분석 코드\n")
    lines.append("| 코드 | 용도 | 실행 방법 |")
    lines.append("|------|------|----------|")
    lines.append("| `analyze_combined.py` | **1차 결합 분석** (이 리포트 생성) | `python OHS/analyze_combined.py` |")
    lines.append("| `analyze_phase1_inject.py` | **2차 분석** (다일자/CommandId 대응) | `python OHS/analyze_phase1_inject.py` |")
    lines.append("| `analyze_oht_xsohs.py` | M14_OHT 단독 분석 | `python OHS/analyze_oht_xsohs.py` |")
    lines.append("")
    lines.append("> XSOHS(스타), 로그프레소 데이터를 동일 시간대로 수집하여 위 코드에 투입하면")
    lines.append("> 동일한 결합 분석 결과를 재현할 수 있습니다.")

    lines.append("")
    return '\n'.join(lines)


# ============================================================
# 3. 리포트 생성
# ============================================================
def generate_report(m14_path, quwa_path, hid_path, rail_path, output_path):
    m14 = load_m14_oht(m14_path)
    quwa = load_quwa(quwa_path)
    hid = load_hid_inout(hid_path)
    rail = load_rail_cut(rail_path)

    report = []
    report.append("# OHT 1차 결합 분석 리포트\n")
    report.append(f"> 분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"> 데이터 기간: 2026-04-14 08:30 ~ 17:00")
    report.append(f"> 데이터: M14_OHT({len(m14):,}) + 스타({len(quwa):,}) + HID_INOUT({len(hid):,}) + RAIL_CUT({len(rail)})\n")
    report.append("---\n")

    sections = [
        ("데이터 개요", lambda: analyze_data_overview(m14, quwa, hid, rail)),
        ("스타 추이", lambda: analyze_quwa_trends(quwa)),
        ("M14+스타 결합", lambda: analyze_m14_quwa_correlation(m14, quwa)),
        ("HID 흐름", lambda: analyze_hid_flow(hid)),
        ("HID+스타 결합", lambda: analyze_hid_quwa_correlation(hid, quwa)),
        ("RAIL_CUT", lambda: analyze_rail_cut(rail)),
        ("월드 모델 파라미터", lambda: analyze_world_model_params(m14, quwa, hid)),
        ("병목 판단", lambda: analyze_bottleneck(quwa)),
        ("예측 가능 여부", lambda: analyze_prediction_feasibility(m14, quwa)),
        ("결론", lambda: analyze_summary(m14, quwa, hid, rail)),
    ]

    for name, fn in sections:
        print(f"  분석 중: {name}...")
        report.append(fn())

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    print(f"\n리포트 생성 완료: {output_path}")


if __name__ == '__main__':
    generate_report(
        m14_path='OHS/XSOHS_extracted/raw.csv',
        quwa_path='OHS/OHT_컬럼수집_DATA.CSV',
        hid_path='OHS/LOGPRESSO_extracted/M14A_ATLAS_HID_INOUT_202604140830_1700.csv',
        rail_path='OHS/LOGPRESSO_extracted/ATLAS_OHT_RAIL_CUT_202604140830_202604141700.csv',
        output_path='OHS/OHT_1차_결합분석_리포트.md',
    )
