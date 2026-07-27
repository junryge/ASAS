#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
발동이벤트 24시간 통합 그래프
  ① 상단: unified_risk_score 24h 추이 + 등급 배경 + 최고점 마커
  ② 하단: 최고점 reason 발동 컬럼들의 24h 시계열
     - 좌측 라벨: 한글 친화 (예: M16HUB 반송시간 (분))
     - 좌측 모노스페이스: raw 풀네임 (예: M16HUB.QUE.TIME.AVGTOTALTIME1MIN)
     - raw 풀네임은 aws_idc_realtime_collector.py 의 265 컬럼 매핑 사용

사용:
  python 발동이벤트_24h.py <발동이벤트.csv> [-o <출력폴더>]
"""
import csv
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svg_lib import make_24h_combined_svg
from raw_columns import parse_reason_pairs, EVT_TO_RAW, friendly_label


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

    # ★ reason → (evt_col, raw_full, area, rule) pairs
    pairs = parse_reason_pairs(peak['reason'])
    print(f"📂 {evt_path}")
    print(f"   {len(score_data)}분, 최고 {peak['score']:.0f}점 [{peak['level']}] "
          f"@ {peak['t'].strftime('%H:%M')} hot={peak['hot']}")
    print(f"   reason 발동 컬럼 {len(pairs)}개:")
    for evt_col, raw_full, area, rule in pairs:
        print(f"      [{area} {rule}] {evt_col} ← {raw_full}")

    # ★ 24h 시계열 — key 는 raw 풀네임 (CSV 에선 evt_col 로 값 조회)
    raw_series = {}
    friendly = {}
    for evt_col, raw_full, _area, _rule in pairs:
        pts = []
        for t, r in rows_keep:
            v = (r.get(evt_col) or '').strip()
            if not v: continue
            try: pts.append((t, float(v)))
            except: pass
        if pts:
            raw_series[raw_full] = pts
            friendly[raw_full] = friendly_label(evt_col)

    svg = make_24h_combined_svg(day, score_data, peak, raw_series, friendly_map=friendly)
    fname = day.replace('-','') + '_발동이벤트_24h.svg'
    out_path = os.path.join(out_dir, fname)
    open(out_path, 'w', encoding='utf-8').write(svg)
    print(f"✅ 생성: {out_path}  (raw 풀네임 {len(raw_series)}개)")


if __name__ == '__main__':
    main()
