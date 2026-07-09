#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
밀림요약 — 밀림CUSUM_결과.csv(매분 43200줄) → 경보 뜬 구간만 압축 (사람이 볼 표)
====================================================================
'예측' 인 분만 골라 연속구간으로 묶음. 정상(미예측)은 전부 버림.
예측시각·방향·CUSUM·사건적중까지 한 줄로.

입력:
   --result  밀림CUSUM_결과.csv (밀림_방향_CUSUM.py 산출)
   --gap     연속으로 볼 간격(분, 기본 10) — 이 안에 끊겨도 같은 구간
   --out     밀림_경보요약.csv

실행:
   python 밀림요약.py --result .\out_ml\밀림CUSUM_결과.csv --out .\out_ml\밀림_경보요약.csv
"""
import argparse, csv
from datetime import datetime, timedelta

# 고객확인 4개 사건 (사건적중 표시용)
EVENTS = [datetime(2026, 6, 11, 10, 18), datetime(2026, 6, 22, 11, 11),
          datetime(2026, 6, 24, 11, 58), datetime(2026, 6, 29, 18, 7)]
GRADE_ORD = {'': 0, '경계': 1, '위험': 2, '초위험': 3}


def pdt(s):
    try:
        return datetime.strptime((s or '').strip()[:16], '%Y-%m-%d %H:%M')
    except ValueError:
        return None


def cusum_of(r):
    """밀림방향에 해당하는 CUSUM 값 뽑기."""
    d = r.get('밀림방향', '')
    if '남측' in d:
        return float(r.get('남큐CUSUM') or 0)
    if '북측' in d:
        return float(r.get('북큐CUSUM') or 0)
    if '허브' in d:
        return float(r.get('저장CUSUM') or 0)
    return 0.0


def grade_of(r):
    """사유 안 배수로 등급 추정 (없으면 경계)."""
    why = r.get('사유', '')
    import re
    m = re.search(r'([\d.]+)배', why)
    ratio = float(m.group(1)) if m else 1.0
    return '초위험' if ratio >= 2.5 else '위험' if ratio >= 1.5 else '경계'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--result', required=True)
    ap.add_argument('--gap', type=int, default=10)
    ap.add_argument('--out', default='./out_ml/밀림_경보요약.csv')
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.result, encoding='utf-8-sig')))
    segs = []
    for r in rows:
        if (r.get('예측결과') or '').strip() != '예측':
            continue
        t = pdt(r['datetime'])
        d = r.get('밀림방향', '')
        cu = cusum_of(r)
        g = grade_of(r)
        if (segs and segs[-1]['방향'] == d
                and (t - segs[-1]['end']).total_seconds() <= a.gap * 60):
            s = segs[-1]
            s['end'] = t
            if cu > s['최고CUSUM']:
                s['최고CUSUM'] = cu; s['사유'] = r.get('사유', '')
            if GRADE_ORD[g] > GRADE_ORD[s['최고등급']]:
                s['최고등급'] = g
        else:
            segs.append({'start': t, 'end': t, '방향': d, '최고등급': g,
                         '최고CUSUM': cu, '사유': r.get('사유', '')})

    def hit(s):
        return any(s['start'] - timedelta(minutes=60) <= e <= s['end'] + timedelta(minutes=20)
                   for e in EVENTS)

    def kind(s):
        """예측종류: 컨베이어밀림(남/북) / 허브저장Full / 허브몰림."""
        d = s['방향']
        if '남측' in d:
            return '컨베이어밀림(남측)'
        if '북측' in d:
            return '컨베이어밀림(북측)'
        if '저장Full' in s['사유'] or 'STK' in s['사유']:
            return '허브 저장Full'
        return '허브 몰림/저장'

    with open(a.out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['경보시작', '경보종료', '지속(분)', '예측종류', '밀림방향', '최고등급',
                    '예측시각(10분후)', '예측시각(30분후)', '최고CUSUM', '사건적중', '사유'])
        for s in segs:
            dur = int((s['end'] - s['start']).total_seconds() // 60) + 1
            w.writerow([
                s['start'].strftime('%Y-%m-%d %H:%M'),
                s['end'].strftime('%H:%M'), dur, kind(s), s['방향'], s['최고등급'],
                (s['start'] + timedelta(minutes=10)).strftime('%m-%d %H:%M'),
                (s['start'] + timedelta(minutes=30)).strftime('%m-%d %H:%M'),
                f"{s['최고CUSUM']:.0f}",
                '★사건' if hit(s) else '', s['사유'],
            ])

    n_hit = sum(1 for s in segs if hit(s))
    print(f"[완료] {len(rows)}줄 → 경보구간 {len(segs)}줄  → {a.out}")
    print(f"       ★사건 적중 {n_hit}구간 / 오탐 {len(segs) - n_hit}구간")
    print("       ※ 이 표만 보면 됨 (정상 미예측은 전부 생략)")


if __name__ == '__main__':
    main()
