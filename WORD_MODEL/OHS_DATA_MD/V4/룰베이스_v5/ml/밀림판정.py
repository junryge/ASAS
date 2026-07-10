#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
밀림판정 — 실시간 구간표(밀림경보요약_실시간.csv)에 판정/근거메시지 채우기 (월말 평가)
====================================================================
실시간 운영 중엔 미래 메시지를 알 수 없어 판정이 공란 → 월말에 메신저 episode 와
대조해서 각 경보를 예측/오탐 으로 채움. (6월 검증: 수동판정 45건과 100% 일치한 기준)

판정 기준:
  예측 = 경보 종료 후 4시간 내 메신저 사건 발생(사전예고)
         OR 같은 날 경보 전에 이미 사건 있었음(여파, 12시간 내)
  오탐 = 매칭되는 메시지 없음

실행:
  ① 메신저 txt → episode :  python 운영로그_파서_v2.5.py 7월.txt --out .\ep7
  ② 판정 채우기          :  python 밀림판정.py --summary .\밀림예측\밀림경보요약_실시간.csv ^
                                --episodes .\ep7\생긴episode.csv --out .\밀림_월말평가.csv
"""
import argparse, csv, os, sys
from datetime import datetime, timedelta


def pdt(s):
    for f in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return datetime.strptime((s or '').strip()[:19 if len((s or '').strip()) > 16 else 16], f)
        except ValueError:
            continue
    return None


def load_events(paths):
    ev = []
    for fp in [p.strip() for p in paths.split(',') if p.strip()]:
        if not os.path.exists(fp):
            print(f"❌ episode 없음: {fp}"); sys.exit(2)
        for r in csv.DictReader(open(fp, encoding='utf-8-sig')):
            if (r.get('is_orphan') or '').strip().upper() == 'Y':
                continue
            t = pdt(r.get('start_time') or r.get('t0'))
            if t:
                desc = ' '.join(x for x in [r.get('equipment', ''), r.get('fault_type', '')] if x)
                ev.append((t, desc or '사건'))
    ev.sort()
    return ev


def judge(st, en, events):
    best = None
    for e, d in events:
        if e >= st and (e - en) <= timedelta(hours=4):
            cand = ('예측', f"{e.strftime('%m/%d %H:%M')} {d}", abs((e - st).total_seconds()))
        elif e < st and e.date() == st.date() and (st - e) <= timedelta(hours=12):
            cand = ('예측', f"{e.strftime('%m/%d %H:%M')} {d} (사건후 여파)",
                    (st - e).total_seconds() + 10**6)
        else:
            continue
        if best is None or cand[2] < best[2]:
            best = cand
    return best[:2] if best else ('오탐', '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--summary', required=True, help='밀림경보요약_실시간.csv (경보시작/경보종료 구간표)')
    ap.add_argument('--episodes', required=True, help='메신저 episode.csv (쉼표로 여러개)')
    ap.add_argument('--out', default='./밀림_월말평가.csv')
    a = ap.parse_args()

    events = load_events(a.episodes)
    print(f"[메신저] 판정근거 사건 {len(events)}건")
    rows = list(csv.DictReader(open(a.summary, encoding='utf-8-sig')))
    n = {'예측': 0, '오탐': 0}
    for r in rows:
        st = pdt(r['경보시작'])
        en = pdt(r['경보시작'][:11] + r['경보종료'])
        if en and st and en < st:
            en += timedelta(days=1)
        v, basis = judge(st, en, events)
        r['판정'] = v; r['근거메시지'] = basis
        n[v] += 1
    with open(a.out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    tot = len(rows)
    print(f"[완료] 경보 {tot}구간 → 예측 {n['예측']} / 오탐 {n['오탐']} ({n['예측']/max(tot,1)*100:.0f}% 정탐) → {a.out}")


if __name__ == '__main__':
    main()
