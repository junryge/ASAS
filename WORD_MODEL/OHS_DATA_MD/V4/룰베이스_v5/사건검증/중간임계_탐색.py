#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
중간 임계 탐색 — v4.1 ~ 추천 사이에서 '재현율 유지 + FP 줄이는' 스위트스팟 찾기

v4.1 임계:  FP 많음(339), 재현율 45%  ← 시끄러움
추천 임계:  FP 적음(27),  재현율 12%  ← 너무 놓침

그 사이를 blend 비율 0~1 로 보간:
  blend=0.0 → v4.1
  blend=1.0 → 추천
각 비율마다 발동이벤트 재판정 → 사건 재구성 → 메신저 매칭 → FP/재현율 측정.
"""
import csv
import glob
import os
from datetime import datetime, timedelta

V4 = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
AREAS = ['M16HUB', 'M14', 'M14B', 'M16A', 'M16B']

# v4.1 원본 임계
V41 = {
    'RA': {'M16HUB': 9.0, 'M14': 3.3, 'M14B': 5.0, 'M16A': 3.2, 'M16B': 3.5},
    'RB30': {'M16HUB': 100, 'M14': 80, 'M14B': 150, 'M16A': 80, 'M16B': 30},
    'RC': 2, 'FAB': 25.0, 'STB': 99.0,
    'SLA': {'M16HUB': 5.0, 'M14': 25.0, 'M16A': 13.0, 'M16B': 18.0},
}
# 추천 임계
REC = {
    'RA': {'M16HUB': 12.0, 'M14': 3.6, 'M14B': 5.0, 'M16A': 3.4, 'M16B': 6.0},
    'RB30': {'M16HUB': 100, 'M14': 80, 'M14B': 150, 'M16A': 110, 'M16B': 40},
    'RC': 12, 'FAB': 30.0, 'STB': 101.0,
    'SLA': {'M16HUB': 5.0, 'M14': 28.0, 'M16A': 20.0, 'M16B': 45.0},
}


def blend(a, b, t):
    return a + (b - a) * t


def make_th(t):
    """blend 비율 t (0=v4.1, 1=추천) 로 임계 보간."""
    th = {'RA': {}, 'RB30': {}, 'SLA': {}}
    for k in V41['RA']:
        th['RA'][k] = blend(V41['RA'][k], REC['RA'][k], t)
    for k in V41['RB30']:
        th['RB30'][k] = blend(V41['RB30'][k], REC['RB30'][k], t)
    for k in V41['SLA']:
        th['SLA'][k] = blend(V41['SLA'][k], REC['SLA'][k], t)
    th['RC'] = blend(V41['RC'], REC['RC'], t)
    th['FAB'] = blend(V41['FAB'], REC['FAB'], t)
    th['STB'] = blend(V41['STB'], REC['STB'], t)
    return th


def fnum(r, k):
    v = (r.get(k) or '').strip()
    try:
        return float(v)
    except Exception:
        return None


def s3(r, th):
    any_ra = any(fnum(r, f'{a}_ra') is not None and fnum(r, f'{a}_ra') >= th['RA'][a] for a in AREAS)
    any_rb = any(fnum(r, f'{a}_rb_diff30') is not None and fnum(r, f'{a}_rb_diff30') >= th['RB30'][a] for a in AREAS)
    rev = fnum(r, 'M16HUB_rev_count'); trend = fnum(r, 'M16HUB_rc_trend')
    any_rc = (rev is not None and trend is not None and trend < 0 and rev >= th['RC'])
    fab = fnum(r, 'M16HUB_rd_fab'); stb = fnum(r, 'M16HUB_stb_util')
    any_rd = (fab is not None and fab >= th['FAB']) or (stb is not None and stb >= th['STB'])
    any_sla = any(fnum(r, f'sla_{a}') is not None and fnum(r, f'sla_{a}') >= th['SLA'][a] for a in th['SLA'])
    flow = (fnum(r, 'flow_score') or 0) >= 15
    return any_ra and (any_rd or any_sla or any_rc) and (any_rb or flow)


# 발동이벤트 전체 1회 로드 (재사용)
_ROWS = None
def load_rows():
    global _ROWS
    if _ROWS is None:
        _ROWS = []
        for fp in sorted(glob.glob(f'{V4}/AP/extracted/*_발동이벤트.csv')):
            day_rows = []
            for r in csv.DictReader(open(fp, encoding='utf-8-sig')):
                try:
                    r['_t'] = datetime.strptime(r['datetime'], '%Y-%m-%d %H:%M')
                    day_rows.append(r)
                except Exception:
                    pass
            _ROWS.append(day_rows)
    return _ROWS


def build_incidents(th, gap_min=10):
    incidents = []
    for day_rows in load_rows():
        cur = None; last = None
        for r in day_rows:
            if s3(r, th):
                sc = fnum(r, 'unified_risk_score') or 0
                if cur is None:
                    cur = {'predict': r['_t'], 'end': r['_t'], 'score': sc}
                else:
                    cur['end'] = r['_t']; cur['score'] = max(cur['score'], sc)
                last = r['_t']
            else:
                if cur and last and (r['_t'] - last).total_seconds() / 60.0 >= gap_min:
                    incidents.append(cur); cur = None
        if cur:
            incidents.append(cur)
    return incidents


def load_episodes():
    eps = []
    fp = f'{V4}/룰베이스_v5/운영로그_분석_v2/output/20260612_065558_episode.csv'
    for e in csv.DictReader(open(fp, encoding='utf-8-sig')):
        if e.get('is_orphan') == 'Y':
            continue
        try:
            eps.append({'start': datetime.strptime(e['start_time'], '%Y-%m-%d %H:%M:%S'),
                        'end': datetime.strptime(e['end_time'], '%Y-%m-%d %H:%M:%S')})
        except Exception:
            pass
    return eps


def evaluate(incidents, episodes):
    W = timedelta(minutes=30); MAX_LEAD = 120
    for i in incidents: i['m'] = False
    eps = [{'start': e['start'], 'end': e['end'], 'm': False} for e in episodes]
    leads = []
    for ep in sorted(eps, key=lambda x: x['start']):
        best = None
        for inc in incidents:
            if inc['m']: continue
            if not ((inc['predict'] - W) <= ep['end'] and (ep['start'] - W) <= inc['end']): continue
            lead = (ep['start'] - inc['predict']).total_seconds() / 60.0
            if lead > MAX_LEAD or lead < -30: continue
            g = abs(lead)
            if best is None or g < best[1]: best = (inc, g, lead)
        if best:
            best[0]['m'] = True; ep['m'] = True; leads.append(best[2])
    tp = sum(1 for i in incidents if i['m'])
    fp = len(incidents) - tp
    miss = sum(1 for e in eps if not e['m'])
    prec = tp / (tp + fp) * 100 if tp + fp else 0
    rec = tp / (tp + miss) * 100 if tp + miss else 0
    ahead = sum(1 for l in leads if l > 0)
    avg = sum(leads) / len(leads) if leads else 0
    return len(incidents), tp, fp, miss, prec, rec, ahead, len(leads), avg


def main():
    episodes = load_episodes()
    print(f"메신저 실제 장애(Episode): {len(episodes)}건\n")
    print(f"{'blend':>6} {'사건':>5} {'TP':>4} {'FP':>5} {'Miss':>5} "
          f"{'정밀도':>7} {'재현율':>7} {'사전예측':>9} {'평균리드':>8}")
    print("-" * 70)
    for t in [0.0, 0.15, 0.3, 0.45, 0.6, 0.75, 1.0]:
        th = make_th(t)
        inc = build_incidents(th)
        n, tp, fp, miss, prec, rec, ahead, nl, avg = evaluate(inc, episodes)
        tag = ' (v4.1)' if t == 0 else ' (추천)' if t == 1 else ''
        print(f"{t:>6.2f} {n:>5} {tp:>4} {fp:>5} {miss:>5} "
              f"{prec:>6.1f}% {rec:>6.1f}% {ahead:>4}/{nl:<3} {avg:>+6.0f}분{tag}")
    print("-" * 70)
    print("blend 0=v4.1, 1=추천. 재현율 유지하며 FP 줄어드는 지점이 스위트스팟.")


if __name__ == '__main__':
    main()
