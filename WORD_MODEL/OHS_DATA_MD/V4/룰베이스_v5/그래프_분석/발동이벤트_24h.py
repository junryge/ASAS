#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
발동이벤트 24시간 통합 그래프
  ① 상단: unified_risk_score 24h 추이 + 등급 배경 + 최고점 마커
  ② 하단: 최고점 reason 발동 컬럼들의 24시간 시계열 (원본 컬럼명 표시)

사용:
  python 발동이벤트_24h.py <발동이벤트.csv> [-o <출력폴더>]
"""
import csv
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svg_lib import make_24h_combined_svg, COL_MAP_RAW_TO_EVT


def parse_reason_evt_cols(reason):
    """발동이벤트 reason (축약형) → 발동이벤트 컬럼명 직접 매핑.
       reason 예: "M16HUB[R-A'(AVGTOTALTIME1MIN=6.34분),R-D(FAB저장=0.0%,STB=100.0%)]; M16B[R-D(OHT=98.7%),SLA(47.7%4분초과)]"
    """
    cols = []
    def add(c):
        if c not in cols: cols.append(c)
    for m in re.finditer(r'(M16HUB|M14B|M14|M16A|M16B|M16_PKT|M16_WT|M16)\[([^\]]+)\]', reason or ''):
        area, body = m.group(1), m.group(2)
        if 'AVGTOTALTIME1MIN' in body or 'AVGLOADTIME1MIN' in body or "R-A'" in body or 'R-A_sus' in body:
            add(f'{area}_ra')
        if 'FAB저장' in body and area == 'M16HUB':
            add('M16HUB_rd_fab')
        if 'STB=' in body and area == 'M16HUB':
            add('M16HUB_stb_util')
        if 'OHT=' in body or 'OHTUTIL' in body:
            if area in ('M14','M14B','M16A','M16B'):
                add(f'{area}_rd_oht')
        if 'SLA(' in body or 'TRANSPORT4MIN' in body:
            add(f'sla_{area}')
        if 'Sorter(' in body or 'SORTERWAIT' in body:
            add(f'sorter_{area}')
        if '역증가' in body and area == 'M16HUB':
            add('M16HUB_rev_count')
    return cols


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    evt_path = sys.argv[1]
    out_dir = '.'
    for i, a in enumerate(sys.argv):
        if a == '-o' and i+1 < len(sys.argv):
            out_dir = sys.argv[i+1]
    os.makedirs(out_dir, exist_ok=True)

    # 점수 데이터 + 매분 행 보관
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
        print("⚠️ 데이터 없음"); return

    day = score_data[0]['t'].strftime('%Y-%m-%d')

    # 최고점 (그 분의 reason 으로 컬럼 결정)
    peak_i = max(range(len(score_data)), key=lambda i: score_data[i]['score'])
    peak_row = rows_keep[peak_i][1]
    peak = {**score_data[peak_i], 'reason': peak_row.get('reason', '')}

    # 최고점 reason → 발동이벤트 컬럼 추출
    cols = parse_reason_evt_cols(peak['reason'])
    print(f"📂 {evt_path}")
    print(f"   {len(score_data)} 분, 최고 {peak['score']:.0f}점 [{peak['level']}] "
          f"@ {peak['t'].strftime('%H:%M')} hot={peak['hot']}")
    print(f"   reason 발동 컬럼 {len(cols)}개: {cols}")

    # 24h 시계열 (해당 컬럼들)
    raw_series = {c: [] for c in cols}
    for t, r in rows_keep:
        for c in cols:
            v = (r.get(c) or '').strip()
            if not v: continue
            try: raw_series[c].append((t, float(v)))
            except: pass
    # 빈 컬럼 제거
    raw_series = {c: pts for c, pts in raw_series.items() if pts}

    svg = make_24h_combined_svg(day, score_data, peak, raw_series)
    fname = day.replace('-','') + '_발동이벤트_24h.svg'
    out_path = os.path.join(out_dir, fname)
    open(out_path, 'w', encoding='utf-8').write(svg)
    print(f"✅ 생성: {out_path}  (점수 추이 + raw 컬럼 {len(raw_series)}개)")


if __name__ == '__main__':
    main()
