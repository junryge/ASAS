#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RA 완화 + CAPA 제외 검증 — 추천 다듬기 효과 측정

변경점 2가지:
  ① CAPA변경 episode 제외 (운영자 조치, 장애 아님)
  ② RA 임계만 v4.1 원본으로 (나머지 blend 0.15 유지)

비교: 현재(blend 0.15) vs ①만 vs ①+② vs v4.1전체복귀
"""
import csv
import glob
import os
from datetime import datetime, timedelta

V4 = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DATA_DIR = os.path.join(V4, '룰베이스_v5', '데이터들', 'extracted')
AREAS = ['M16HUB', 'M14', 'M14B', 'M16A', 'M16B']

# 임계 프리셋 4종
# 현재 blend 0.15
BLEND15 = {
    'RA': {'M16HUB': 9.45, 'M14': 3.35, 'M14B': 5.0, 'M16A': 3.23, 'M16B': 3.88},
    'RB30': {'M16HUB': 100, 'M14': 80, 'M14B': 150, 'M16A': 84, 'M16B': 32},
    'RC': 4, 'FAB': 25.75, 'STB': 99.3,
    'SLA': {'M16HUB': 5.0, 'M14': 25.45, 'M16A': 14.05, 'M16B': 22.05},
}
# v4.1 원본
V41 = {
    'RA': {'M16HUB': 9.0, 'M14': 3.3, 'M14B': 5.0, 'M16A': 3.2, 'M16B': 3.5},
    'RB30': {'M16HUB': 100, 'M14': 80, 'M14B': 150, 'M16A': 80, 'M16B': 30},
    'RC': 2, 'FAB': 25.0, 'STB': 99.0,
    'SLA': {'M16HUB': 5.0, 'M14': 25.0, 'M16A': 13.0, 'M16B': 18.0},
}
# ★ 추천 — RA만 v4.1, 나머지 blend 0.15 유지
RA_ONLY = {
    'RA': V41['RA'],
    'RB30': BLEND15['RB30'],
    'RC': BLEND15['RC'],
    'FAB': BLEND15['FAB'],
    'STB': BLEND15['STB'],
    'SLA': BLEND15['SLA'],
}


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


_ROWS = None
def load_rows():
    global _ROWS
    if _ROWS is None:
        _ROWS = []
        for fp in sorted(glob.glob(f'{DATA_DIR}/predict_tobe/*_발동이벤트.csv')):
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


def load_episodes(exclude_capa=False):
    """Episode 로드. exclude_capa=True 면 CAPA변경 제외 (운영자 조치)."""
    eps = []
    fp = glob.glob(f'{DATA_DIR}/episode_out/*_episode.csv')
    if not fp:
        # fallback: 운영로그_분석_v2 output
        fp = glob.glob(f'{V4}/룰베이스_v5/운영로그_분석_v2/output/*_episode.csv')
    fp = sorted(fp)[-1]
    for e in csv.DictReader(open(fp, encoding='utf-8-sig')):
        if e.get('is_orphan') == 'Y':
            continue
        if exclude_capa and e.get('fault_type') == 'CAPA변경':
            continue
        try:
            eps.append({'start': datetime.strptime(e['start_time'], '%Y-%m-%d %H:%M:%S'),
                        'end': datetime.strptime(e['end_time'], '%Y-%m-%d %H:%M:%S'),
                        'type': e.get('fault_type', '')})
        except Exception:
            pass
    return eps


def evaluate(incidents, episodes):
    W = timedelta(minutes=30); MAX_LEAD = 120
    incs = [dict(i, m=False) for i in incidents]
    eps = [dict(e, m=False) for e in episodes]
    leads = []
    for ep in sorted(eps, key=lambda x: x['start']):
        best = None
        for inc in incs:
            if inc['m']: continue
            if not ((inc['predict'] - W) <= ep['end'] and (ep['start'] - W) <= inc['end']): continue
            lead = (ep['start'] - inc['predict']).total_seconds() / 60.0
            if lead > MAX_LEAD or lead < -30: continue
            g = abs(lead)
            if best is None or g < best[1]: best = (inc, g, lead, ep)
        if best:
            best[0]['m'] = True; best[3]['m'] = True; leads.append(best[2])
    tp = sum(1 for i in incs if i['m'])
    fp = len(incs) - tp
    miss = sum(1 for e in eps if not e['m'])
    prec = tp / (tp + fp) * 100 if tp + fp else 0
    rec = tp / (tp + miss) * 100 if tp + miss else 0
    ahead = sum(1 for l in leads if l > 0)
    avg = sum(leads) / len(leads) if leads else 0
    return len(incs), tp, fp, miss, prec, rec, ahead, len(leads), avg


def main():
    eps_full = load_episodes(exclude_capa=False)
    eps_noCAPA = load_episodes(exclude_capa=True)
    print(f"Episode 전체: {len(eps_full)}건")
    print(f"Episode CAPA변경 제외: {len(eps_noCAPA)}건")
    print()
    print(f"{'시나리오':<35} {'사건':>5} {'TP':>4} {'FP':>5} {'Miss':>5} {'정밀':>5} {'재현':>5} {'사전':>6} {'평균리드':>8}")
    print('-' * 95)

    scenarios = [
        ('A. 현재 blend 0.15 (full)',     BLEND15, eps_full),
        ('B. 현재 + CAPA 제외',           BLEND15, eps_noCAPA),
        ('C. ★ RA만 v4.1 + CAPA 제외',    RA_ONLY, eps_noCAPA),
        ('D. v4.1 전체복귀 + CAPA 제외',  V41,     eps_noCAPA),
    ]
    results = []
    for name, th, eps in scenarios:
        incs = build_incidents(th)
        n, tp, fp, miss, prec, rec, ahead, nl, avg = evaluate(incs, eps)
        print(f"{name:<35} {n:>5} {tp:>4} {fp:>5} {miss:>5} "
              f"{prec:>4.0f}% {rec:>4.0f}% {ahead:>3}/{nl:<2} {avg:>+6.0f}분")
        results.append((name, n, tp, fp, miss, prec, rec, avg))

    print('-' * 95)
    print()
    print("=== 핵심 비교 ===")
    A = results[0]; B = results[1]; C = results[2]
    print(f"  A → B (CAPA 제외만): 재현율 {A[6]:.0f}% → {B[6]:.0f}% (정의 정정 효과)")
    print(f"  B → C (+RA 완화):    재현율 {B[6]:.0f}% → {C[6]:.0f}%, FP {B[3]} → {C[3]}")
    print(f"  C → D (전체복귀):    재현율 {C[6]:.0f}% → {results[3][6]:.0f}%, FP {C[3]} → {results[3][3]}")
    print()
    print("→ C (★) 가 정밀/재현 균형 좋으면 채택")


if __name__ == '__main__':
    main()
