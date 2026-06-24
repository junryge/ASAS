#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
발동이벤트 24시간 통합 그래프 — 원본 raw CSV 버전 ★
==========================================================
  ① 상단: 발동이벤트.csv 의 unified_risk_score 24h 추이 + 등급 배경 + 최고점 마커
  ② 하단: 최고점 reason 발동 컬럼들의 24h 시계열
           → **raw CSV (M16A_HUBROOM_PR.CSV) 의 풀네임 컬럼에서 직접 추출**
           → 발동이벤트.csv 축약값 안 씀 (고객 보고용)

기존 발동이벤트_24h.py 와 별도. 데이터 소스만 다름.

사용:
  python 발동이벤트_24h_원본raw.py <발동이벤트.csv> <raw_CSV> [-o <출력폴더>]

예:
  python 발동이벤트_24h_원본raw.py predict_tobe\20260623_발동이벤트.csv raw\M16A_HUBROOM_PR.CSV -o ./out

입력:
  - 발동이벤트.csv  → 점수 추이 + reason (어느 raw 컬럼이 원인인지 식별)
  - raw CSV (M16A_HUBROOM_PR.CSV, 24시간) → 그래프 데이터 (raw 풀네임 컬럼)
"""
import csv
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svg_lib import make_24h_combined_svg
from raw_columns import parse_reason_pairs, friendly_label


def parse_dt(s):
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
            t = parse_dt(r.get('CRT_TM', ''))
            if not t: continue
            t = t.replace(second=0, microsecond=0)
            for c in cols_set:
                v = (r.get(c) or '').strip()
                if not v: continue
                try: series_map[c][t] = float(v)
                except: pass
    return series_map, cols_set


def main():
    if len(sys.argv) < 3:
        print(__doc__); return
    evt_path = sys.argv[1]
    raw_path = sys.argv[2]
    out_dir = '.'
    for i, a in enumerate(sys.argv):
        if a == '-o' and i+1 < len(sys.argv):
            out_dir = sys.argv[i+1]
    os.makedirs(out_dir, exist_ok=True)

    # ── 발동이벤트 로드 (점수 추이 + reason) ──
    score_data = []
    rows_keep = []
    for r in csv.DictReader(open(evt_path, encoding='utf-8-sig')):
        try:
            t = datetime.strptime(r['datetime'][:16], '%Y-%m-%d %H:%M')
            score_data.append({'t': t, 'score': float(r['unified_risk_score'] or 0),
                               'level': r['unified_risk_level'], 'hot': r['hot_area']})
            rows_keep.append((t, r))
        except Exception:
            pass
    if not score_data:
        print("⚠️ 발동이벤트 데이터 없음"); return
    day = score_data[0]['t'].strftime('%Y-%m-%d')

    # ── 최고점 → reason 파싱 ──
    peak_i = max(range(len(score_data)), key=lambda i: score_data[i]['score'])
    peak_row = rows_keep[peak_i][1]
    peak = {**score_data[peak_i], 'reason': peak_row.get('reason', '')}
    pairs = parse_reason_pairs(peak['reason'])

    print(f"📂 발동이벤트: {evt_path}")
    print(f"   {len(score_data)}분, 최고 {peak['score']:.0f}점 [{peak['level']}] "
          f"@ {peak['t'].strftime('%H:%M')} hot={peak['hot']}")
    print(f"   reason 발동 컬럼 {len(pairs)}개:")
    for evt_col, raw_full, area, rule in pairs:
        print(f"      [{area} {rule}] {raw_full}")

    # ── raw CSV 로드 ──
    print(f"📂 raw CSV: {raw_path}")
    raw_map, raw_cols_set = load_raw_csv(raw_path)
    n_minutes = max((len(v) for v in raw_map.values()), default=0)
    print(f"   raw {len(raw_cols_set)}컬럼 / 최대 {n_minutes}분")

    # ── ★ raw CSV 의 풀네임 컬럼에서 직접 시계열 추출 ──
    raw_series = {}
    friendly = {}
    missing = []
    for evt_col, raw_full, _area, _rule in pairs:
        if raw_full not in raw_cols_set:
            missing.append(raw_full); continue
        d = raw_map[raw_full]
        if d:
            raw_series[raw_full] = sorted(d.items())
            friendly[raw_full] = friendly_label(evt_col)
    if missing:
        print(f"⚠️ raw CSV 에 없는 컬럼 {len(missing)}개 — 제외:")
        for m in missing: print(f"     - {m}")
    if not raw_series:
        print("⚠️ raw 시계열 추출 실패"); return

    svg = make_24h_combined_svg(day, score_data, peak, raw_series, friendly_map=friendly)
    fname = day.replace('-','') + '_발동이벤트_24h_원본raw.svg'
    out_path = os.path.join(out_dir, fname)
    open(out_path, 'w', encoding='utf-8').write(svg)
    print(f"✅ 생성: {out_path}  (raw 풀네임 {len(raw_series)}개)")


if __name__ == '__main__':
    main()
