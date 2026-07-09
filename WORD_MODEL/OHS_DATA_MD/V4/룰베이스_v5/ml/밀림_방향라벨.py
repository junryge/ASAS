#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
밀림_방향라벨 — 메신저 episode → 방향별(남측/북측/허브) 밀림 라벨
====================================================================
[왜] 통합 XGBoost(876피처)는 방향 신호가 희석돼 밀림을 못 배웠음(55건 중 2번만 발동).
→ 방향별로 쪼개서 각 컨베이어의 밀림을 집중 학습 (남측 4AFC3201 / 북측 4AFC3301 / 허브).

[방향 배정] episode 의 equipment/line 으로:
   4AFC3201 / M16TOM14A·B  → 남측
   4AFC3301               → 북측
   그 외(ZT·OHT·리프터·HUB·VHL) → 허브

[라벨] 각 방향마다:
   {방향}_pre10 = t+1~t+10분 안에 그 방향 사건 시작 있으면 1
   {방향}_pre30 = t+1~t+30분 안에 그 방향 사건 시작 있으면 1

입력:
   --features   features.csv (시간 그리드)
   --episodes   1~5월 episode.csv (쉼표로 여러개 가능)
   --types      대상 유형 (기본 '정체/병목,CNV,브릿지')
   --out        방향라벨.csv

실행:
   python 밀림_방향라벨.py --features .\out_ml\features.csv ^
       --episodes ..\운영로그_분석_v2\output\생긴episode.csv --out .\out_ml\방향라벨.csv
"""
import argparse, csv, os, sys
from datetime import datetime, timedelta

DIRS = ['남측', '북측', '허브']


def pdt(s):
    for f in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M'):
        try:
            return datetime.strptime((s or '').strip()[:19], f).replace(second=0)
        except ValueError:
            continue
    return None


def route(eq, line):
    """장비/라인 → 방향. 4AFC3201=남측, 4AFC3301=북측, 나머지=허브."""
    s = (eq or '') + ' ' + (line or '')
    if '4AFC3201' in s or 'M16TOM14A' in s or 'M16TOM14B' in s:
        return '남측'
    if '4AFC3301' in s:
        return '북측'
    return '허브'


def load_episodes(fp, types, maxdur=60):
    """episode.csv → 방향별 사건 분(minute) 집합 dict."""
    mins = {d: set() for d in DIRS}
    cnt = {d: 0 for d in DIRS}
    tkeys = [t.strip() for t in types.split(',') if t.strip()]
    with open(fp, encoding='utf-8-sig', newline='') as f:
        for x in csv.DictReader(f):
            if (x.get('is_orphan') or '').strip().upper() == 'Y':
                continue
            ft = (x.get('fault_type') or '').strip()
            if tkeys and not any(k in ft for k in tkeys):
                continue
            t = pdt(x.get('start_time') or x.get('t0'))
            if not t:
                continue
            te = pdt(x.get('end_time'))
            span = min(maxdur, int((te - t).total_seconds() // 60) + 1) if te and te > t else 10
            span = max(1, span)
            d = route(x.get('equipment'), x.get('line'))
            for k in range(span):
                mins[d].add(t + timedelta(minutes=k))
            cnt[d] += 1
    return mins, cnt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', required=True)
    ap.add_argument('--episodes', required=True, help='쉼표로 여러 파일')
    ap.add_argument('--types', default='정체/병목,CNV,브릿지')
    ap.add_argument('--pre', default='10,30')
    ap.add_argument('--out', default='./out_ml/방향라벨.csv')
    a = ap.parse_args()

    ep_files = [p.strip() for p in a.episodes.split(',') if p.strip()]
    for p in ep_files:
        if not os.path.exists(p):
            print(f"❌ episode 경로 없음: {p}"); sys.exit(2)

    jam = {d: set() for d in DIRS}
    tot = {d: 0 for d in DIRS}
    for fp in ep_files:
        m, c = load_episodes(fp, a.types)
        for d in DIRS:
            jam[d] |= m[d]; tot[d] += c[d]
        print(f"[메신저] {os.path.basename(fp)}: 남측 {c['남측']} / 북측 {c['북측']} / 허브 {c['허브']}")
    print(f"[합계] 남측 {tot['남측']} / 북측 {tot['북측']} / 허브 {tot['허브']}건")
    if sum(tot.values()) == 0:
        print("❌ 사건 0건 — types/파일 확인"); sys.exit(2)

    pres = [int(x) for x in a.pre.split(',') if x.strip()]

    times = []
    with open(a.features, encoding='utf-8-sig', newline='') as f:
        for x in csv.DictReader(f):
            t = pdt(x.get('datetime'))
            if t:
                times.append(t)
    times.sort()

    cols = [f'{d}_pre{p}' for d in DIRS for p in pres]
    npos = {c: 0 for c in cols}
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    with open(a.out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['datetime'] + cols)
        for t in times:
            row = [t.strftime('%Y-%m-%d %H:%M')]
            for d in DIRS:
                for p in pres:
                    y = int(any((t + timedelta(minutes=k)) in jam[d] for k in range(1, p + 1)))
                    row.append(y); npos[f'{d}_pre{p}'] += y
            w.writerow(row)

    n = len(times)
    print(f"[완료] {n}분 → {a.out}")
    for c in cols:
        print(f"       {c} = 1 : {npos[c]}분 ({npos[c]/n*100:.2f}%)")
    print("다음: python 밀림_방향학습.py --features <features.csv> --labels " + a.out)


if __name__ == '__main__':
    main()
