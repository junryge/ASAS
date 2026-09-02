#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PIO_10분집계 — 발동이벤트.csv 의 PIO 12컬럼(1분 건수)을 10분 단위로 묶어 본다 (보기용, 원본 무변경)
# ====================================================================
# 발동이벤트의 {경로}_PIOERROR_DEPOSITED 12컬럼은 1분 건수 그대로 둔다 (PIO_DATA_MAKE).
# 고객이 "10분에 몇 개 정도 나는지" 보고 싶다고 해서, 읽어서 묶기만 하는 도구.
#
#   python PIO_10분집계.py .\predict_tobe\20260826_발동이벤트.csv
#   python PIO_10분집계.py .\predict_tobe            ← 폴더면 그 안의 발동이벤트 전부
#   옵션: --bucket 10  (묶는 분, 기본 10)  · -o 출력폴더 (기본 입력 옆)
#
# 출력
#   ① {날짜}_PIO_10분.csv — 10분 구간(시작 시각) × 12경로 합계 + 12경로 총합
#   ② 화면 — 경로별 10분 합 분포 (평균 · 최대 · p95 · p99) 와 총합 상위 구간
#      → 나중에 점수 임계 잡을 때 그대로 쓰는 숫자
import argparse, csv, glob, os, re, sys
from datetime import datetime

MARK = '_PIOERROR_DEPOSITED'


def parse_dt(s):
    s = (s or '').strip()
    try:
        d, t = s.split(' ', 1)
        y, mo, dd = [int(x) for x in d.replace('/', '-').split('-')]
        hm = t.split(':')
        return datetime(y, mo, dd, int(hm[0]), int(hm[1]))
    except (ValueError, IndexError):
        return None


def pct(v, q):
    v = sorted(v)
    if not v:
        return 0
    k = (len(v) - 1) * q / 100
    lo = int(k); hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def one_file(fp, out_dir, bucket):
    with open(fp, encoding='utf-8-sig') as f:
        rd = csv.DictReader(f)
        cols = [c for c in (rd.fieldnames or []) if c.endswith(MARK)]
        if not cols:
            print(f'  ⚠️ PIO 컬럼 없음: {os.path.basename(fp)}')
            return None
        rows = list(rd)
    paths = [c[:-len(MARK)] for c in cols]

    agg = {}                      # 구간 시작 → {경로: 합}
    n_blank = 0
    for r in rows:
        t = parse_dt(r.get('datetime'))
        if not t:
            continue
        b = t.replace(minute=(t.minute // bucket) * bucket)
        e = agg.setdefault(b, {p: 0 for p in paths})
        for p, c in zip(paths, cols):
            v = (r.get(c) or '').strip()
            if v == '':
                n_blank += 1
                continue
            try:
                e[p] += int(float(v))
            except ValueError:
                pass

    if not agg:
        print(f'  ⚠️ 시간 파싱 실패: {os.path.basename(fp)}')
        return None

    base = os.path.basename(fp)
    stem = base[:-4] if base.lower().endswith('.csv') else base
    m = re.search(r'(\d{8})', stem)
    op = os.path.join(out_dir, f'{m.group(1) if m else stem}_PIO_{bucket}분.csv')
    with open(op, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['구간시작'] + paths + ['총합'])
        for b in sorted(agg):
            vals = [agg[b][p] for p in paths]
            w.writerow([b.strftime('%Y-%m-%d %H:%M')] + vals + [sum(vals)])

    # 화면 요약
    nb = len(agg)
    print(f'\n  {base} — {len(rows)}행 → {bucket}분 구간 {nb}개'
          + (f' (공란 {n_blank}칸은 0 취급 안 함·제외)' if n_blank else ''))
    print(f"     {'경로':<14}{'평균':>6}{'최대':>6}{'p95':>6}{'p99':>6}   {'0인 구간':>8}")
    for p in paths:
        v = [agg[b][p] for b in agg]
        print(f"     {p:<14}{sum(v)/nb:>6.1f}{max(v):>6}{pct(v,95):>6.0f}{pct(v,99):>6.0f}   "
              f"{sum(1 for x in v if x == 0)/nb*100:>7.0f}%")
    tot = {b: sum(agg[b].values()) for b in agg}
    print(f"     {'12경로 총합':<14}{sum(tot.values())/nb:>6.1f}{max(tot.values()):>6}"
          f"{pct(list(tot.values()),95):>6.0f}{pct(list(tot.values()),99):>6.0f}")
    top = sorted(tot.items(), key=lambda x: -x[1])[:5]
    if top and top[0][1] > 0:
        print('     총합 상위 구간:')
        for b, s in top:
            if s == 0:
                break
            hit = ' · '.join(f'{p}={agg[b][p]}' for p in paths if agg[b][p])
            print(f'       {b:%m/%d %H:%M}~  {s:>3}건   {hit}')
    print(f'  → {op}')
    return op


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inputs', nargs='+', help='발동이벤트 CSV 또는 폴더')
    ap.add_argument('-o', '--out', default=None, help='출력 폴더 (기본: 입력 파일 옆)')
    ap.add_argument('--bucket', type=int, default=10, help='묶는 분 (기본 10)')
    a = ap.parse_args()

    files = []
    for x in a.inputs:
        if os.path.isdir(x):
            files += sorted(f for f in glob.glob(os.path.join(x, '*발동이벤트*.csv'))
                            if '_M1' not in os.path.basename(f))
        else:
            files += sorted(glob.glob(x)) or [x]
    files = [f for f in files if os.path.exists(f)]
    if not files:
        print('❌ 입력 파일 없음'); sys.exit(2)

    print('=' * 60)
    print(f'PIO 12컬럼 {a.bucket}분 집계 (보기용 — 원본 안 건드림)')
    print('=' * 60)
    made = 0
    for fp in files:
        out_dir = a.out or os.path.dirname(os.path.abspath(fp))
        os.makedirs(out_dir, exist_ok=True)
        if one_file(fp, out_dir, max(1, a.bucket)):
            made += 1
    print(f'\n🎉 완료 — {made}개 파일')


if __name__ == '__main__':
    main()
