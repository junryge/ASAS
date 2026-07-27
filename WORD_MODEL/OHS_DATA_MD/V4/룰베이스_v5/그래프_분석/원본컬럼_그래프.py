#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
원본컬럼_그래프 — raw CSV (M16A_HUBROOM_PR.csv) 의 풀네임 컬럼 직접 추출해서 그래프
=========================================================================================
- 발동이벤트.csv reason → 어느 raw 컬럼이 원인인지 식별 (단서로만 사용)
- 실제 시계열 데이터는 **M16A_HUBROOM_PR.csv 의 raw 풀네임 컬럼에서 직접** 가져옴
- 발동이벤트.csv 축약값 안 씀

기존 (발동이벤트_24h.py / 위험사건_그래프.py) 와 별도. 고객에게 보여줄 때 원본 컬럼 그대로.

사용:
  python 원본컬럼_그래프.py <raw_CSV> <발동이벤트.csv> [-o <출력폴더>]

예:
  python 원본컬럼_그래프.py 20260609DATA/M16A_HUBROOM_PR.CSV 데이터들/.../20260609_발동이벤트.csv

raw CSV 형식 (aws_idc_realtime_collector.py 가 저장):
  CRT_TM, M16HUB.CNV.SENDFAB...., M16HUB.LFT...., ... (265개 컬럼)
"""
import csv
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svg_lib import make_incident_svg
from raw_columns import parse_reason_pairs, friendly_label


def parse_dt(s):
    s = (s or '').strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M:%S'):
        try: return datetime.strptime(s, fmt)
        except: continue
    return None


def load_raw_csv(raw_path):
    """raw CSV → (시간 정렬된 행 리스트, 컬럼명 리스트).
       매 분 단위로 정규화. 컬럼은 raw 풀네임 그대로 유지.
    """
    rows = []
    cols = []
    with open(raw_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        cols = [c for c in reader.fieldnames if c and c != 'CRT_TM']
        for r in reader:
            t = parse_dt(r.get('CRT_TM', ''))
            if not t: continue
            # 분 단위 정규화
            t = t.replace(second=0, microsecond=0)
            rows.append((t, r))
    rows.sort(key=lambda x: x[0])
    return rows, cols


def extract_series(rows, raw_full_col):
    """raw 풀네임 컬럼 → [(t, float_val)] 시계열."""
    pts = []
    for t, r in rows:
        v = (r.get(raw_full_col) or '').strip()
        if not v: continue
        try: pts.append((t, float(v)))
        except: pass
    return pts


def main():
    if len(sys.argv) < 3:
        print(__doc__); return
    raw_path = sys.argv[1]
    evt_path = sys.argv[2]
    out_dir = '.'
    for i, a in enumerate(sys.argv):
        if a == '-o' and i+1 < len(sys.argv):
            out_dir = sys.argv[i+1]
    os.makedirs(out_dir, exist_ok=True)

    # ── raw CSV 로드 ──
    print(f"📂 raw CSV: {raw_path}")
    rows, cols = load_raw_csv(raw_path)
    if not rows:
        print("⚠️ raw 데이터 없음"); return
    t_first, t_last = rows[0][0], rows[-1][0]
    print(f"   {len(rows)}분, {t_first.strftime('%Y-%m-%d %H:%M')} ~ {t_last.strftime('%H:%M')} "
          f"({len(cols)} 컬럼)")

    # ── 발동이벤트 로드 (raw CSV 시간 범위 안의 행만) ──
    evt_rows = []
    for r in csv.DictReader(open(evt_path, encoding='utf-8-sig')):
        try:
            t = datetime.strptime(r['datetime'][:16], '%Y-%m-%d %H:%M')
        except: continue
        if t_first <= t <= t_last:
            evt_rows.append({'t': t, 'score': float(r.get('unified_risk_score') or 0),
                             'level': r.get('unified_risk_level','정상'),
                             'hot': r.get('hot_area',''),
                             'reason': r.get('reason','')})
    if not evt_rows:
        print("⚠️ raw 시간 범위 안에 발동이벤트 없음"); return
    print(f"📂 발동이벤트 (raw 범위 내): {len(evt_rows)}분")

    # ── 최고점 reason 으로 컬럼 식별 ──
    peak = max(evt_rows, key=lambda e: e['score'])
    pairs = parse_reason_pairs(peak['reason'])
    if not pairs:
        # 최고점 reason 비어있으면 — 모든 발동시점 reason 합쳐서
        all_reason = '; '.join(e['reason'] for e in evt_rows if e['reason'])
        pairs = parse_reason_pairs(all_reason)

    print(f"🔥 최고 {peak['score']:.0f}점 [{peak['level']}] @ {peak['t'].strftime('%H:%M')} hot={peak['hot']}")
    print(f"   reason → raw 발동 컬럼 {len(pairs)}개:")
    for evt_col, raw_full, area, rule in pairs:
        in_raw = "✓" if raw_full in cols else "✗(raw CSV에 없음)"
        print(f"      [{area} {rule}] {raw_full}  {in_raw}")

    # ── raw CSV 에서 해당 컬럼 시계열 직접 추출 ──
    series = {}
    friendly = {}
    missing = []
    for evt_col, raw_full, _area, _rule in pairs:
        if raw_full not in cols:
            missing.append(raw_full); continue
        pts = extract_series(rows, raw_full)
        if pts:
            series[raw_full] = pts
            friendly[raw_full] = friendly_label(evt_col)
    if missing:
        print(f"⚠️ raw CSV 에 없는 컬럼 {len(missing)}개 — 그래프 제외")
    if not series:
        print("⚠️ raw 시계열 추출 실패"); return

    # ── 사건 단위로 그릴 사건 정보 구성 (raw 윈도우 전체) ──
    incident = {
        'day':     t_first.strftime('%Y-%m-%d'),
        'predict': peak['t'],
        'start':   peak['t'],
        'end':     peak['t'],
        't0':      t_first,
        't1':      t_last,
        'level':   peak['level'],
        'score':   int(peak['score']),
        'hot':     peak['hot'],
    }
    score_series = [(e['t'], e['score']) for e in evt_rows]

    svg = make_incident_svg(incident, series, score_series, friendly_map=friendly)
    fname = (t_first.strftime('%Y%m%d_%H%M') + '_원본raw_'
             + (peak['hot'] or 'NA') + '.svg')
    out_path = os.path.join(out_dir, fname)
    open(out_path, 'w', encoding='utf-8').write(svg)
    print(f"✅ 생성: {out_path}  (raw 풀네임 {len(series)}개)")


if __name__ == '__main__':
    main()
