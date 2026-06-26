#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
위험사건 ±60분 그래프 — 원본 raw CSV 버전 ★
==========================================================
사건단위.csv 의 각 사건마다 1개씩 ±60분 그래프 생성.
시계열 데이터는 **raw CSV (M16A_HUBROOM_PR.CSV) 의 풀네임 컬럼에서 직접 추출**.
발동이벤트.csv 의 축약값 안 씀 — 고객 보고용.

기존 위험사건_그래프.py 와 별도. 데이터 소스만 다름.

사용:
  python 위험사건_그래프_원본raw.py <사건단위.csv> <발동이벤트.csv> <raw_CSV> [-o <출력폴더>] [-l <최소등급>]

예:
  python 위험사건_그래프_원본raw.py predict_tobe\20260623_사건단위.csv predict_tobe\20260623_발동이벤트.csv raw\M16A_HUBROOM_PR.CSV -o ./out
  python 위험사건_그래프_원본raw.py predict_tobe\20260623_사건단위.csv predict_tobe\20260623_발동이벤트.csv raw\M16A_HUBROOM_PR.CSV -l 위험

입력:
  - 사건단위.csv → 사건 목록 + relation (어느 raw 컬럼이 원인인지 식별)
  - 발동이벤트.csv → 점수 추이 (상단)
  - raw CSV (M16A_HUBROOM_PR.CSV, 24시간) → 하단 시계열 (raw 풀네임 컬럼)
"""
import csv
import os
import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svg_lib import make_incident_svg
from raw_columns import parse_relation_pairs, friendly_label

LEVEL_ORDER = {'정상':0, '관심':1, '주의':2, '경계':3, '위험':4, '초위험':5}
DEFAULT_MIN = '주의'


def parse_dt(day, s):
    try: return datetime.strptime(f"{day} {s}", '%Y-%m-%d %H:%M')
    except: return None


def parse_dt_full(s):
    s = (s or '').strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M:%S'):
        try: return datetime.strptime(s, fmt)
        except: continue
    return None


def load_raw_csv(raw_path):
    """raw CSV → {풀네임: {datetime: float}}. 분 단위 정규화."""
    series_map = {}
    cols_set = set()
    with open(raw_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for c in reader.fieldnames:
            if c and c != 'CRT_TM':
                cols_set.add(c); series_map[c] = {}
        for r in reader:
            t = parse_dt_full(r.get('CRT_TM', ''))
            if not t: continue
            t = t.replace(second=0, microsecond=0)
            for c in cols_set:
                v = (r.get(c) or '').strip()
                if not v: continue
                try: series_map[c][t] = float(v)
                except: pass
    return series_map, cols_set


def main():
    if len(sys.argv) < 4:
        print(__doc__); return
    inc_path = sys.argv[1]
    evt_path = sys.argv[2]
    raw_path = sys.argv[3]
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
        pairs = parse_relation_pairs(r.get('relation', ''))
        if not pairs: continue
        t0 = start - timedelta(minutes=60)
        t1 = end + timedelta(minutes=60)
        incidents.append({
            'day': day, 'predict':predict, 'start':start, 'end':end,
            't0':t0, 't1':t1,
            'level':lv, 'score':int(r.get('max_risk_score',0)),
            'hot':r.get('hot_area',''),
            'pairs': pairs,
        })

    print(f"📂 사건 (≥{min_level}): {len(incidents)}건")
    if not incidents: return

    # ── 발동이벤트 점수 추이 ──
    evt = []
    for r in csv.DictReader(open(evt_path, encoding='utf-8-sig')):
        try:
            t = datetime.strptime(r['datetime'][:16], '%Y-%m-%d %H:%M')
        except: continue
        evt.append({'t':t, 'score': float(r.get('unified_risk_score') or 0)})
    print(f"📂 발동이벤트: {len(evt)}분")

    # ── raw CSV 로드 ──
    print(f"📂 raw CSV: {raw_path}")
    raw_map, raw_cols_set = load_raw_csv(raw_path)
    n_minutes = max((len(v) for v in raw_map.values()), default=0)
    print(f"   raw {len(raw_cols_set)}컬럼 / 최대 {n_minutes}분")

    # ── 사건마다 그래프 ──
    for inc in incidents:
        window_evt = [e for e in evt if inc['t0'] <= e['t'] <= inc['t1']]
        score_series = [(e['t'], e['score']) for e in window_evt]

        # ★ raw CSV 의 풀네임 컬럼에서 직접 시계열 추출 (사건 ±60분 윈도우)
        series = {}
        friendly = {}
        missing = []
        for evt_col, raw_full, _area, _rule in inc['pairs']:
            if raw_full not in raw_cols_set:
                missing.append(raw_full); continue
            d = raw_map[raw_full]
            pts = [(t, v) for t, v in sorted(d.items()) if inc['t0'] <= t <= inc['t1']]
            if pts:
                series[raw_full] = pts
                friendly[raw_full] = friendly_label(evt_col)

        if not series:
            print(f"⏭️  {inc['start'].strftime('%H:%M')} {inc['level']} — raw 데이터 없음"
                  f" (제외 {len(missing)}개)")
            continue

        svg = make_incident_svg(inc, series, score_series, friendly_map=friendly)
        hh = inc['start'].strftime('%H%M')
        fname = inc['day'].replace('-','') + f'_{hh}_{inc["level"]}_{inc["hot"] or "NA"}_원본raw.svg'
        out_path = os.path.join(out_dir, fname)
        open(out_path, 'w', encoding='utf-8').write(svg)
        miss_note = f" (raw 미존재 {len(missing)}개)" if missing else ""
        print(f"✅ {fname}  (raw 컬럼 {len(series)}개{miss_note})")


if __name__ == '__main__':
    main()
