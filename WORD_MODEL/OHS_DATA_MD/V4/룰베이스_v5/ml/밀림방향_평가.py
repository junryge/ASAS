#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
밀림방향_평가 — 6월 방향별 밀림 ML 결과를 실제사건과 대조해 평가표 출력
====================================================================
추론 결과(밀림방향_결과.csv)를 고객확인 4개 사건 + (옵션)메신저 episode 와 대조.
"사건 커버 / 방향정확 / 리드타임 / 오탐율" 을 자동 산출.

입력:
   --result   밀림방향_결과.csv (밀림_방향추론.py 산출)
   --episodes (옵션) 6월 episode.csv — 메신저 확인사건 전체로 오탐 판정
   --out      (옵션) 평가표 CSV

실행:
   python 밀림방향_평가.py --result .\out_ml\밀림방향_결과.csv ^
       --episodes ..\운영로그_분석_v2\output\6월_episode.csv
"""
import argparse, csv, os
from datetime import datetime, timedelta

# 고객확인 4개 사건 + 기대방향 (메신저 장비 근거)
EVENTS = [
    ('2026-06-11 10:18', '북측'),   # 4AFC3301
    ('2026-06-22 11:11', '남측'),   # 4AFC3201
    ('2026-06-24 11:58', '남측'),   # 4AFC3201
    ('2026-06-29 18:07', '허브'),   # M14 HUB VHL 몰림
]
GRADE_ORD = {'': 0, '경계': 1, '위험': 2, '초위험': 3}


def pdt(s):
    for f in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return datetime.strptime((s or '').strip()[:19], f)
        except ValueError:
            continue
    return None


def dir_of(label):
    """'남측(4AFC3201)' → '남측'."""
    for d in ('남측', '북측', '허브'):
        if label.startswith(d):
            return d
    return ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--result', required=True)
    ap.add_argument('--episodes', default=None)
    ap.add_argument('--pre', type=int, default=60, help='사건 몇분전까지 경보 인정')
    ap.add_argument('--out', default=None)
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.result, encoding='utf-8-sig')))
    alarms = []   # (t, dir, grade)
    for r in rows:
        t = pdt(r['datetime']); g = (r.get('밀림등급') or '').strip()
        if t and g:
            alarms.append((t, dir_of(r.get('밀림방향', '')), g))

    print("=" * 60 + "\n  6월 방향별 밀림 ML 평가\n" + "=" * 60)
    print(f"\n■ 사건 커버 ({len(EVENTS)}개 고객확인)")
    print(f"  {'사건':^16}{'기대방향':^8}{'ML판정':^10}{'리드':^7}{'등급':^7}{'방향맞음'}")
    cover = 0; dir_ok = 0
    ev_windows = []
    for ts, exp in EVENTS:
        ev = pdt(ts); ev_windows.append(ev)
        lo, hi = ev - timedelta(minutes=a.pre), ev + timedelta(minutes=5)
        cand = [x for x in alarms if lo <= x[0] <= hi]
        if cand:
            # 가장 이른 경보
            first = min(cand, key=lambda x: x[0])
            lead = int((ev - first[0]).total_seconds() // 60)
            match = '✅' if first[1] == exp else f'✗({first[1]})'
            cover += 1; dir_ok += (first[1] == exp)
            print(f"  {ts[5:]:^16}{exp:^8}{first[1]:^10}{lead:>4}분전 {first[2]:^7}{match}")
        else:
            print(f"  {ts[5:]:^16}{exp:^8}{'✗못잡음':^10}{'-':^7}{'-':^7}✗")
    print(f"  → 사건 {cover}/{len(EVENTS)} 커버 · 방향정확 {dir_ok}/{len(EVENTS)}")

    # 오탐: 실제사건(4개 + episode) 근처 아닌 경보구간
    real = list(ev_windows)
    if a.episodes and os.path.exists(a.episodes):
        for r in csv.DictReader(open(a.episodes, encoding='utf-8-sig')):
            if (r.get('is_orphan') or '') == 'Y':
                continue
            if r.get('fault_type') in ('정체/병목', 'CNV', '브릿지'):
                t = pdt(r.get('start_time'))
                if t:
                    real.append(t)

    def near_real(t):
        return any(e - timedelta(minutes=a.pre) <= t <= e + timedelta(minutes=20) for e in real)

    # 경보구간 병합(연속) 후 오탐 판정
    segs = []
    alarms.sort()
    for t, d, g in alarms:
        if segs and (t - segs[-1][1]).total_seconds() <= 300 and segs[-1][2] == d:
            segs[-1][1] = t
            if GRADE_ORD[g] > GRADE_ORD[segs[-1][3]]:
                segs[-1][3] = g
        else:
            segs.append([t, t, d, g])
    fp = sum(1 for s in segs if not near_real(s[0]))
    print(f"\n■ 오탐 (실제사건 무관 경보)")
    print(f"  경보구간 {len(segs)} 중 오탐 {fp} ({fp/max(len(segs),1)*100:.0f}%)")
    from collections import Counter
    fpc = Counter(s[2] for s in segs if not near_real(s[0]))
    print(f"  방향별 오탐: " + " / ".join(f"{d} {fpc.get(d,0)}" for d in ('남측', '북측', '허브')))

    if a.out:
        with open(a.out, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f); w.writerow(['경보시작', '경보종료', '방향', '최고등급', '오탐여부'])
            for s in segs:
                w.writerow([s[0].strftime('%m/%d %H:%M'), s[1].strftime('%H:%M'), s[2], s[3],
                            '오탐' if not near_real(s[0]) else '적중'])
        print(f"\n  경보구간 상세 → {a.out}")


if __name__ == '__main__':
    main()
