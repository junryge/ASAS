#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
발동이벤트_로그프레소병합 — 발동이벤트.csv 에 로그프레소 이상감지 4컬럼 추가
====================================================================
로그프레소 쿼리(둘 다 MCP_NM=="BR"):
  table from=YYYYMMDD000000 to=YYYYMMDD235959 ATLAS_BOTTLENECK_ANOMALY | search MCP_NM == "BR" | sort _time
  table from=YYYYMMDD000000 to=YYYYMMDD235959 ATLAS_QUEUE_ANOMALY      | search MCP_NM == "BR" | sort _time
→ export CSV (_id,_table,_time,EVENT_DT,FAB_ID,MCP_NM,downward_anomaly_cols,upward_anomaly_cols)

추가되는 4컬럼:
  BOTTLENECK_downward_anomaly_cols, BOTTLENECK_upward_anomaly_cols  ← ATLAS_BOTTLENECK_ANOMALY
  QUEUE_downward_anomaly_cols,      QUEUE_upward_anomaly_cols       ← ATLAS_QUEUE_ANOMALY

시간 정렬(1분 늦게):
  발동이벤트 datetime 12:54 행 ← 로그프레소 EVENT_DT 12:53 행 기입
  (로그프레소는 해당 분을 몇십초 뒤에 기록하므로, 생성 시점엔 직전 분이 확정 최신)

실행:
  python 발동이벤트_로그프레소병합.py --event .\predict_tobe\발동이벤트.csv ^
      --bottleneck .\bottleneck_20260713.csv --queue .\queue_20260713.csv ^
      --out .\predict_tobe\발동이벤트_병합.csv
  (--out 을 --event 와 같은 경로로 주면 원본에 덮어쓰기)
"""
import argparse, csv, os, sys
from datetime import datetime, timedelta

NEW_COLS = ['BOTTLENECK_downward_anomaly_cols', 'BOTTLENECK_upward_anomaly_cols',
            'QUEUE_downward_anomaly_cols', 'QUEUE_upward_anomaly_cols']


def minute_key(s):
    """'2026-07-13 12:53:00(.074+0900)' / '2026-07-13 12:53' → '2026-07-13 12:53'"""
    s = (s or '').strip()
    return s[:16] if len(s) >= 16 else ''


def load_logpresso(fp, label):
    """EVENT_DT 분단위 → (down, up). 같은 분 중복이면 나중(_id 큰) 행이 이김."""
    if not fp:
        return {}
    if not os.path.exists(fp):
        print(f'❌ {label} 파일 없음: {fp}'); sys.exit(2)
    m = {}
    with open(fp, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if (r.get('MCP_NM') or '').strip() not in ('', 'BR'):
                continue  # 쿼리에서 이미 BR 필터지만 이중 안전
            k = minute_key(r.get('EVENT_DT'))
            if k:
                m[k] = ((r.get('downward_anomaly_cols') or '').strip(),
                        (r.get('upward_anomaly_cols') or '').strip())
    print(f'[{label}] {fp} → {len(m)}분 로드 '
          f'(이상감지 있는 분: {sum(1 for v in m.values() if v[0] or v[1])}개)')
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--event', required=True, help='발동이벤트.csv')
    ap.add_argument('--bottleneck', default=None, help='ATLAS_BOTTLENECK_ANOMALY export csv')
    ap.add_argument('--queue', default=None, help='ATLAS_QUEUE_ANOMALY export csv')
    ap.add_argument('--out', default=None, help='출력 (기본: 발동이벤트_병합.csv)')
    ap.add_argument('--lag', type=int, default=1, help='로그프레소를 몇 분 전 것을 기입할지 (기본 1)')
    a = ap.parse_args()

    bt = load_logpresso(a.bottleneck, 'BOTTLENECK')
    qu = load_logpresso(a.queue, 'QUEUE')

    with open(a.event, encoding='utf-8-sig') as f:
        rd = csv.DictReader(f)
        header = list(rd.fieldnames)
        rows = list(rd)
    if 'datetime' not in header:
        print("❌ 발동이벤트에 'datetime' 컬럼 없음"); sys.exit(2)

    out_header = header + [c for c in NEW_COLS if c not in header]
    hit_b = hit_q = 0
    for r in rows:
        try:
            t = datetime.strptime(minute_key(r['datetime']), '%Y-%m-%d %H:%M')
            k = (t - timedelta(minutes=a.lag)).strftime('%Y-%m-%d %H:%M')
        except ValueError:
            k = ''
        b = bt.get(k)
        q = qu.get(k)
        r['BOTTLENECK_downward_anomaly_cols'] = b[0] if b else ''
        r['BOTTLENECK_upward_anomaly_cols'] = b[1] if b else ''
        r['QUEUE_downward_anomaly_cols'] = q[0] if q else ''
        r['QUEUE_upward_anomaly_cols'] = q[1] if q else ''
        hit_b += b is not None
        hit_q += q is not None

    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.event)), '발동이벤트_병합.csv')
    with open(out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=out_header)
        w.writeheader(); w.writerows(rows)

    n = len(rows)
    print(f'[병합] 발동이벤트 {n}행 (컬럼 {len(header)}→{len(out_header)})')
    print(f'  BOTTLENECK 매칭 {hit_b}/{n}  ·  QUEUE 매칭 {hit_q}/{n}  (미매칭=공란)')
    print(f'💾 → {out}')


if __name__ == '__main__':
    main()
