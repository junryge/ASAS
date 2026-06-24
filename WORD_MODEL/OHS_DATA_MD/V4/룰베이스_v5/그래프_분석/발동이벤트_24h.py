#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
발동이벤트 24시간 분석 그래프 — unified_risk_score 추이 + 등급 배경

사용:
  python 발동이벤트_24h.py <발동이벤트.csv> [-o <출력폴더>]

예:
  python 발동이벤트_24h.py predict_tobe/20260525_발동이벤트.csv -o ./out
"""
import csv
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svg_lib import make_24h_score_svg


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    evt_path = sys.argv[1]
    out_dir = '.'
    for i, a in enumerate(sys.argv):
        if a == '-o' and i+1 < len(sys.argv):
            out_dir = sys.argv[i+1]
    os.makedirs(out_dir, exist_ok=True)

    data = []
    for r in csv.DictReader(open(evt_path, encoding='utf-8-sig')):
        try:
            t = datetime.strptime(r['datetime'][:16], '%Y-%m-%d %H:%M')
            data.append({'t': t, 'score': float(r['unified_risk_score'] or 0),
                         'level': r['unified_risk_level'], 'hot': r['hot_area']})
        except Exception:
            pass
    if not data:
        print("⚠️ 데이터 없음"); return

    day = data[0]['t'].strftime('%Y-%m-%d')
    peak = max(data, key=lambda x: x['score'])
    print(f"📂 {evt_path}")
    print(f"   {len(data)} 분, 최고 {peak['score']:.0f}점 [{peak['level']}] @ {peak['t'].strftime('%H:%M')} hot={peak['hot']}")

    svg = make_24h_score_svg(day, data, peak)
    fname = day.replace('-','') + '_발동이벤트_24h.svg'
    out_path = os.path.join(out_dir, fname)
    open(out_path, 'w', encoding='utf-8').write(svg)
    print(f"✅ 생성: {out_path}")


if __name__ == '__main__':
    main()
