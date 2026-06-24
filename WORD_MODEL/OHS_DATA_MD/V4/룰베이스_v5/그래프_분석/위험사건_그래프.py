#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
위험사건(주의/경계/위험/발동) ±60분 그래프 — 사건단위.csv 의 각 사건마다 1개씩

사용:
  python 위험사건_그래프.py <사건단위.csv> <발동이벤트.csv> [-o <출력폴더>] [-l <최소등급>]

예:
  python 위험사건_그래프.py predict_tobe/20260525_사건단위.csv predict_tobe/20260525_발동이벤트.csv -o ./out
  python 위험사건_그래프.py predict_tobe/20260525_사건단위.csv predict_tobe/20260525_발동이벤트.csv -l 위험

- 발동이벤트.csv 의 raw 컬럼 (M16HUB_ra, sla_*, sorter_*, rd_oht 등) 을 사용
- raw DB 접속 안 함
"""
import csv
import os
import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svg_lib import make_incident_svg, COL_MAP_RAW_TO_EVT

# 등급 우선순위 (필터용)
LEVEL_ORDER = {'정상':0, '관심':1, '주의':2, '경계':3, '위험':4, '발동':5}
DEFAULT_MIN = '주의'


def parse_relation(rel):
    """relation 텍스트 → [발동이벤트 컬럼명] 추출."""
    cols = []
    # 정규식: [영역 룰] ... 컬럼=값 (기준 ...)
    for m in re.finditer(r'\[([^\]]+)\]\s*([^|]+?)(?=\s*\||$)', rel or ''):
        body = m.group(2)
        # 원본 컬럼명 패턴
        for raw_col in re.findall(r'([A-Z][A-Z0-9_]+(?:\.[A-Z0-9_]+){2,})', body):
            evt_col = COL_MAP_RAW_TO_EVT.get(raw_col)
            if evt_col and evt_col not in cols:
                cols.append(evt_col)
        # 리프터 역증가는 한글
        if '리프터' in body and '역증가' in body:
            if 'M16HUB_rev_count' not in cols:
                cols.append('M16HUB_rev_count')
    return cols


def parse_dt(day, s):
    try: return datetime.strptime(f"{day} {s}", '%Y-%m-%d %H:%M')
    except: return None


def main():
    if len(sys.argv) < 3:
        print(__doc__); return
    inc_path = sys.argv[1]
    evt_path = sys.argv[2]
    out_dir = '.'
    min_level = DEFAULT_MIN
    for i, a in enumerate(sys.argv):
        if a == '-o' and i+1 < len(sys.argv): out_dir = sys.argv[i+1]
        if a == '-l' and i+1 < len(sys.argv): min_level = sys.argv[i+1]
    os.makedirs(out_dir, exist_ok=True)
    min_lv_n = LEVEL_ORDER.get(min_level, 2)

    # ── 사건 로드 ──
    base = os.path.basename(inc_path)
    m = re.match(r'(\d{8})', base)
    day_default = f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}" if m else None
    incidents = []
    for r in csv.DictReader(open(inc_path, encoding='utf-8-sig')):
        lv = (r.get('max_risk_level') or '').strip()
        if LEVEL_ORDER.get(lv, 0) < min_lv_n: continue
        day = r.get('date') or day_default
        if not day: continue
        predict = parse_dt(day, r['predict_time'])
        start = parse_dt(day, r['start_time'])
        end = parse_dt(day, r['end_time'])
        if start and predict and start < predict: start += timedelta(days=1)
        if start and end and end < start: end += timedelta(days=1)
        if not (predict and start and end): continue
        cols = parse_relation(r.get('relation',''))
        if not cols: continue
        t0 = start - timedelta(minutes=60)
        t1 = end + timedelta(minutes=60)
        incidents.append({
            'day': day, 'predict':predict, 'start':start, 'end':end,
            't0':t0, 't1':t1,
            'level':lv, 'score':int(r.get('max_risk_score',0)),
            'hot':r.get('hot_area',''), 'cols':cols,
        })

    print(f"📂 사건 (≥{min_level}): {len(incidents)}건")
    if not incidents: return

    # ── 발동이벤트 로드 ──
    evt = []
    for r in csv.DictReader(open(evt_path, encoding='utf-8-sig')):
        try:
            t = datetime.strptime(r['datetime'][:16], '%Y-%m-%d %H:%M')
        except: continue
        evt.append({'t':t, 'score': float(r.get('unified_risk_score') or 0), 'r':r})

    # ── 각 사건마다 그래프 ──
    for inc in incidents:
        # 사건 ±60분 윈도우 발동이벤트
        window = [e for e in evt if inc['t0'] <= e['t'] <= inc['t1']]
        score_series = [(e['t'], e['score']) for e in window]

        # raw 컬럼 시계열
        series = {}
        for col in inc['cols']:
            pts = []
            for e in window:
                v = (e['r'].get(col) or '').strip()
                if not v: continue
                try: pts.append((e['t'], float(v)))
                except: pass
            if pts: series[col] = pts

        if not series:
            print(f"⏭️  {inc['start'].strftime('%H:%M')} {inc['level']} — 데이터 없음"); continue

        svg = make_incident_svg(inc, series, score_series)
        hh = inc['start'].strftime('%H%M')
        fname = inc['day'].replace('-','') + f'_{hh}_{inc["level"]}_{inc["hot"] or "NA"}.svg'
        out_path = os.path.join(out_dir, fname)
        open(out_path, 'w', encoding='utf-8').write(svg)
        print(f"✅ {fname}  (컬럼 {len(series)}개, 사건 ±60분 {len(window)}분)")


if __name__ == '__main__':
    main()
