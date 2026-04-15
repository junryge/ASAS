#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OHT 2차 분석용 코드
- 1차 분석 데이터 + 추가 데이터(CommandId, 다일자, layout 등)를 결합 분석
- 새 데이터가 들어올 때 재사용 가능한 구조
- Usage: python analyze_phase2.py --config config.json
         python analyze_phase2.py (기본 경로 사용)
"""

import csv
import json
import sys
import os
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


# ============================================================
# 설정
# ============================================================
DEFAULT_CONFIG = {
    "m14_oht_paths": ["OHS/XSOHS_extracted/raw.csv"],
    "quwa_paths": ["OHS/OHT_컬럼수집_DATA.CSV"],
    "hid_inout_paths": ["OHS/LOGPRESSO_extracted/M14A_ATLAS_HID_INOUT_202604140830_1700.csv"],
    "rail_cut_paths": ["OHS/LOGPRESSO_extracted/ATLAS_OHT_RAIL_CUT_202604140830_202604141700.csv"],
    "hidoff_paths": [],
    "output_dir": "OHS/phase2_output",
    "field_count": 21,  # 21 또는 23 (CommandId 포함 시 23)
}

# Enum 매핑
VHL_STATE_MAP = {
    "1": "RUN", "2": "STOP", "3": "ABNORMAL", "4": "MANUAL",
    "5": "REMOVING", "6": "OBS_BZ_STOP", "7": "JAM",
    "8": "HT_STOP", "9": "E84_TIMEOUT",
}


def to_minute_key(t):
    try:
        parts = t.split(' ')[1].split(':')
        return f"{parts[0]}:{parts[1]}"
    except:
        return None


def to_date_key(t):
    try:
        return t.split(' ')[0]
    except:
        return None


# ============================================================
# 데이터 로더 (다일자 지원)
# ============================================================
class DataLoader:
    """여러 파일을 통합 로드하는 클래스"""

    @staticmethod
    def load_m14_oht(paths, field_count=21):
        """M14_OHT 로드 (21필드 또는 23필드)"""
        records = []
        for path in paths:
            if not os.path.exists(path):
                print(f"  [경고] 파일 없음: {path}")
                continue
            print(f"  로드: {path}")
            with open(path, 'r') as f:
                reader = csv.reader(f)
                next(reader)
                for row in reader:
                    if len(row) <= 4:
                        continue
                    parts = row[4].split(',')
                    if parts[0] != '2':
                        continue
                    if len(parts) < 21:
                        continue
                    rec = {
                        'time': row[3],
                        'date': to_date_key(row[3]),
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
                        'run_distance': parts[20] if len(parts) > 20 else '0',
                    }
                    # 23필드: CommandId, BayName 추가
                    if len(parts) >= 22:
                        rec['command_id'] = parts[21]
                    if len(parts) >= 23:
                        rec['bay_name'] = parts[22]
                    records.append(rec)
        print(f"  M14_OHT 총 {len(records):,}건")
        return records

    @staticmethod
    def load_quwa(paths):
        """스타 로드"""
        records = []
        for path in paths:
            if not os.path.exists(path):
                print(f"  [경고] 파일 없음: {path}")
                continue
            print(f"  로드: {path}")
            with open(path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append({
                        'time': row['CRT_TM'],
                        'date': to_date_key(row['CRT_TM']),
                        'minute': to_minute_key(row['CRT_TM']),
                        'queue_cnt': int(row['M14.QUE.ALL.CURRENTQCNT']) if row.get('M14.QUE.ALL.CURRENTQCNT') else None,
                        'completed': int(row['M14.QUE.ALL.CURRENTQCOMPLETED']) if row.get('M14.QUE.ALL.CURRENTQCOMPLETED') else None,
                        'oht_queue': int(row['M14.QUE.OHT.CURRENTOHTQCNT']) if row.get('M14.QUE.OHT.CURRENTOHTQCNT') else None,
                        'avg_load_time': float(row['M14.QUE.LOAD.AVGLOADTIME']) if row.get('M14.QUE.LOAD.AVGLOADTIME') else None,
                        'delay_cnt': int(row['M14.QUE.ALL.TRANSPORT4MINOVERCNT']) if row.get('M14.QUE.ALL.TRANSPORT4MINOVERCNT') else None,
                        'driving': int(row['M14.OHT.STATECNT.DRIVING']) if row.get('M14.OHT.STATECNT.DRIVING') else None,
                        'obs_stop': int(row['M14.OHT.STATECNT.OBSANDBZSTOP']) if row.get('M14.OHT.STATECNT.OBSANDBZSTOP') else None,
                    })
        print(f"  스타 총 {len(records):,}건")
        return records

    @staticmethod
    def load_hid_inout(paths):
        """HID_INOUT 로드"""
        records = []
        for path in paths:
            if not os.path.exists(path):
                print(f"  [경고] 파일 없음: {path}")
                continue
            print(f"  로드: {path}")
            with open(path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append({
                        'time': row['EVENT_DT'],
                        'date': to_date_key(row['EVENT_DT']),
                        'minute': to_minute_key(row['EVENT_DT']),
                        'vid': row['VHL_ID'],
                        'from_hid': row['FROM_HIDID'],
                        'to_hid': row['TO_HIDID'],
                        'speed': float(row['FREE_FLOW_SPEED']) if row.get('FREE_FLOW_SPEED') else 0,
                        'vhl_limit': int(row['VHL_COUNT_LIMIT']) if row.get('VHL_COUNT_LIMIT') else 0,
                        'vhl_precaution': int(row['VHL_PRECAUTION']) if row.get('VHL_PRECAUTION') else 0,
                    })
        print(f"  HID_INOUT 총 {len(records):,}건")
        return records

    @staticmethod
    def load_rail_cut(paths):
        """RAIL_CUT 로드"""
        records = []
        for path in paths:
            if not os.path.exists(path):
                continue
            with open(path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append({
                        'time': row['EVENT_DT'],
                        'from_addr': row['FROM_ADDR'],
                        'to_addr': row['TO_ADDR'],
                        'state': row['STATE'],
                        'affected': row.get('AFFECT_ADDR_LST', ''),
                    })
        print(f"  RAIL_CUT 총 {len(records):,}건")
        return records


# ============================================================
# 2차 분석 함수들
# ============================================================
class Phase2Analyzer:

    def __init__(self, m14, quwa, hid, rail):
        self.m14 = m14
        self.quwa = quwa
        self.hid = hid
        self.rail = rail

    def analyze_command_id(self):
        """CommandId 분석 (23필드 데이터가 있을 때)"""
        has_cmd = [r for r in self.m14 if r.get('command_id')]
        no_cmd = [r for r in self.m14 if not r.get('command_id', '')]

        lines = []
        lines.append("## CommandId 분석\n")

        if not has_cmd:
            lines.append("CommandId 데이터 없음 (21필드). 23필드 수집 후 재분석 필요.\n")
            return '\n'.join(lines)

        lines.append(f"- CommandId 있음: {len(has_cmd):,}건 ({len(has_cmd)/len(self.m14)*100:.1f}%)")
        lines.append(f"- CommandId 없음 (idle): {len(no_cmd):,}건 ({len(no_cmd)/len(self.m14)*100:.1f}%)")

        # 시간대별 작업/idle 비율
        hourly_cmd = defaultdict(lambda: {'cmd': 0, 'idle': 0})
        for r in self.m14:
            if r['minute']:
                h = r['minute'].split(':')[0]
                if r.get('command_id'):
                    hourly_cmd[h]['cmd'] += 1
                else:
                    hourly_cmd[h]['idle'] += 1

        lines.append("\n### 시간대별 작업/Idle 비율\n")
        lines.append("| 시간 | 작업 중 | Idle | 작업 비율 |")
        lines.append("|------|--------|------|----------|")
        for h in sorted(hourly_cmd.keys()):
            d = hourly_cmd[h]
            total = d['cmd'] + d['idle']
            lines.append(f"| {h}:00 | {d['cmd']:,} | {d['idle']:,} | {d['cmd']/total*100:.1f}% |")

        # 고유 CommandId 수 → 작업 발생 빈도
        cmd_ids = Counter(r['command_id'] for r in has_cmd)
        lines.append(f"\n- 고유 CommandId 수: {len(cmd_ids):,}")
        lines.append(f"- CommandId당 평균 리포트 수: {statistics.mean(cmd_ids.values()):.1f}")

        lines.append("")
        return '\n'.join(lines)

    def analyze_multi_day(self):
        """다일자 비교 분석"""
        dates = set(r['date'] for r in self.m14 if r['date'])

        lines = []
        lines.append("## 다일자 비교 분석\n")

        if len(dates) <= 1:
            lines.append(f"단일 일자({dates.pop() if dates else 'N/A'}) 데이터. 다일자 수집 후 재분석 필요.\n")
            return '\n'.join(lines)

        lines.append(f"분석 일자: {sorted(dates)}\n")

        # 일자별 기본 통계
        lines.append("### 일자별 기본 통계\n")
        lines.append("| 일자 | M14_OHT 건수 | 고유 차량 | OBS 비율 |")
        lines.append("|------|------------|---------|---------|")
        for d in sorted(dates):
            day_records = [r for r in self.m14 if r['date'] == d]
            vhls = set(r['vid'] for r in day_records)
            obs = sum(1 for r in day_records if r['state'] == '6')
            lines.append(f"| {d} | {len(day_records):,} | {len(vhls)} | {obs/len(day_records)*100:.1f}% |")

        # 스타 일자별
        quwa_dates = set(r['date'] for r in self.quwa if r['date'])
        if len(quwa_dates) > 1:
            lines.append("\n### 스타 일자별 평균\n")
            lines.append("| 일자 | 평균 큐 | 평균 완료 | 평균 반송시간 |")
            lines.append("|------|--------|---------|------------|")
            for d in sorted(quwa_dates):
                day_q = [r for r in self.quwa if r['date'] == d]
                queues = [r['queue_cnt'] for r in day_q if r['queue_cnt'] is not None]
                comps = [r['completed'] for r in day_q if r['completed'] is not None]
                lts = [r['avg_load_time'] for r in day_q if r['avg_load_time'] is not None]
                if queues:
                    lines.append(f"| {d} | {statistics.mean(queues):.0f} | {statistics.mean(comps):.0f} | {statistics.mean(lts):.2f}분 |")

        lines.append("")
        return '\n'.join(lines)

    def analyze_hid_congestion_pattern(self):
        """HID 구간 혼잡 패턴 심화 분석"""
        lines = []
        lines.append("## HID 혼잡 패턴 심화 분석\n")

        # HID별 시간대별 속도 변화
        hid_hourly_speed = defaultdict(lambda: defaultdict(list))
        for r in self.hid:
            if r['minute']:
                h = r['minute'].split(':')[0]
                hid_hourly_speed[r['from_hid']][h].append(r['speed'])

        # 속도 변동이 큰 HID (시간대별 표준편차 큰 구간)
        hid_variability = []
        for hid_id, hourly in hid_hourly_speed.items():
            hourly_means = [statistics.mean(speeds) for speeds in hourly.values() if len(speeds) >= 5]
            if len(hourly_means) >= 3:
                hid_variability.append((hid_id, statistics.stdev(hourly_means), statistics.mean(hourly_means)))

        lines.append("### 시간대별 속도 변동이 큰 HID (불안정 구간)\n")
        lines.append("| HID | 속도 변동(표준편차) | 평균 속도 |")
        lines.append("|-----|-----------------|----------|")
        for hid_id, std, mean_spd in sorted(hid_variability, key=lambda x: -x[1])[:15]:
            lines.append(f"| {hid_id} | {std:.1f} | {mean_spd:.1f} |")

        # 스타 큐와 특정 HID 속도 상관
        quwa_map = {r['minute']: r for r in self.quwa if r['minute']}
        hid_minute_speed = defaultdict(lambda: defaultdict(list))
        for r in self.hid:
            if r['minute']:
                hid_minute_speed[r['from_hid']][r['minute']].append(r['speed'])

        # Top 5 혼잡 HID의 큐 상관관계
        top_busy = sorted(hid_variability, key=lambda x: -x[1])[:5]
        if top_busy:
            lines.append("\n### 혼잡 HID 구간의 큐 vs 속도 상관\n")
            for hid_id, _, _ in top_busy:
                high_q_speeds = []
                low_q_speeds = []
                for mk, qr in quwa_map.items():
                    if qr['queue_cnt'] is None:
                        continue
                    spds = hid_minute_speed[hid_id].get(mk, [])
                    if spds:
                        avg = statistics.mean(spds)
                        if qr['queue_cnt'] > 1500:
                            high_q_speeds.append(avg)
                        elif qr['queue_cnt'] < 1300:
                            low_q_speeds.append(avg)
                if high_q_speeds and low_q_speeds:
                    lines.append(f"- **HID {hid_id}**: 큐 높을때 속도 {statistics.mean(high_q_speeds):.1f} / 큐 낮을때 속도 {statistics.mean(low_q_speeds):.1f}")

        lines.append("")
        return '\n'.join(lines)

    def analyze_vehicle_patterns(self):
        """차량별 패턴 분석"""
        lines = []
        lines.append("## 차량별 운행 패턴 분석\n")

        # 차량별 통계
        vhl_stats = defaultdict(lambda: {
            'total': 0, 'obs': 0, 'loaded': 0, 'idle': 0,
            'sources': Counter(), 'dests': Counter(),
        })
        for r in self.m14:
            vid = r['vid']
            if not vid.startswith('V'):
                continue
            vhl_stats[vid]['total'] += 1
            if r['state'] == '6':
                vhl_stats[vid]['obs'] += 1
            if r['loaded'] == '1':
                vhl_stats[vid]['loaded'] += 1
            if r['det_state'] in ('101', '105'):
                vhl_stats[vid]['idle'] += 1
            if r['source']:
                vhl_stats[vid]['sources'][r['source']] += 1
            if r['dest']:
                vhl_stats[vid]['dests'][r['dest']] += 1

        # OBS 비율 높은 차량 (정체 자주 겪는 차량)
        obs_rates = [(vid, s['obs']/s['total']*100, s['total'])
                     for vid, s in vhl_stats.items() if s['total'] >= 100]

        lines.append("### OBS_BZ_STOP 비율 높은 차량 Top 15\n")
        lines.append("| 차량 | OBS 비율 | 총 건수 | 주요 출발지 |")
        lines.append("|------|---------|--------|-----------|")
        for vid, obs_rate, total in sorted(obs_rates, key=lambda x: -x[1])[:15]:
            top_src = vhl_stats[vid]['sources'].most_common(1)
            src = top_src[0][0] if top_src else "-"
            lines.append(f"| {vid} | {obs_rate:.1f}% | {total} | {src} |")

        # Idle 비율 높은 차량 (놀고 있는 차량)
        idle_rates = [(vid, s['idle']/s['total']*100, s['total'])
                      for vid, s in vhl_stats.items() if s['total'] >= 100]

        lines.append("\n### Idle 비율 높은 차량 Top 15\n")
        lines.append("| 차량 | Idle 비율 | 총 건수 |")
        lines.append("|------|---------|--------|")
        for vid, idle_rate, total in sorted(idle_rates, key=lambda x: -x[1])[:15]:
            lines.append(f"| {vid} | {idle_rate:.1f}% | {total} |")

        lines.append("")
        return '\n'.join(lines)

    def generate_report(self, output_path):
        """2차 분석 리포트 생성"""
        report = []
        report.append("# OHT 2차 분석 리포트\n")
        report.append(f"> 분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"> M14_OHT: {len(self.m14):,}건 / 스타: {len(self.quwa):,}건 / HID: {len(self.hid):,}건 / RAIL_CUT: {len(self.rail):,}건\n")
        report.append("---\n")

        sections = [
            ("CommandId 분석", self.analyze_command_id),
            ("다일자 비교", self.analyze_multi_day),
            ("HID 혼잡 패턴", self.analyze_hid_congestion_pattern),
            ("차량별 패턴", self.analyze_vehicle_patterns),
        ]

        for name, fn in sections:
            print(f"  분석: {name}...")
            report.append(fn())

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        print(f"\n2차 리포트 생성 완료: {output_path}")


# ============================================================
# 메인
# ============================================================
def main():
    # 설정 로드
    config = DEFAULT_CONFIG.copy()
    if len(sys.argv) > 1 and sys.argv[1] == '--config':
        with open(sys.argv[2], 'r') as f:
            config.update(json.load(f))

    # 출력 디렉토리 생성
    os.makedirs(config['output_dir'], exist_ok=True)

    # 데이터 로드
    print("=== 데이터 로드 ===")
    loader = DataLoader()
    m14 = loader.load_m14_oht(config['m14_oht_paths'], config['field_count'])
    quwa = loader.load_quwa(config['quwa_paths'])
    hid = loader.load_hid_inout(config['hid_inout_paths'])
    rail = loader.load_rail_cut(config['rail_cut_paths'])

    # 분석 실행
    print("\n=== 2차 분석 ===")
    analyzer = Phase2Analyzer(m14, quwa, hid, rail)
    output_path = os.path.join(config['output_dir'], 'OHT_2차_분석_리포트.md')
    analyzer.generate_report(output_path)


if __name__ == '__main__':
    main()
