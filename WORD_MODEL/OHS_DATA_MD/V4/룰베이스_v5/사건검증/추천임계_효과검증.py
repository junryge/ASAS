#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
추천 임계 효과 검증 — 발동이벤트를 추천 임계로 재판정 → 사건 재구성 → 메신저 매칭

목적: "추천 임계 적용하면 FP 줄고 TP(실제 장애 탐지)는 유지되나?" 확인.
      hubroom_predictor.py 안 돌리고, 이미 생성된 발동이벤트의 raw 메트릭으로
      추천 임계 기준 S3 를 재판정.

비교: v4.1 임계 사건 vs 추천 임계 사건 → 각각 메신저 Episode 매칭.
"""
import csv
import glob
import os
import sys
from datetime import datetime, timedelta
from collections import Counter

V4 = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# ── 추천 임계 ───────────────────────────────────────────
TH_RA = {'M16HUB': 12.0, 'M14': 3.6, 'M14B': 5.0, 'M16A': 3.4, 'M16B': 6.0}
TH_RB30 = {'M16HUB': 100, 'M14': 80, 'M14B': 150, 'M16A': 110, 'M16B': 40}
TH_RC = 12
TH_FAB = 30.0
TH_STB = 101.0
TH_SLA = {'M16HUB': 5.0, 'M14': 28.0, 'M16A': 20.0, 'M16B': 45.0}
AREAS = ['M16HUB', 'M14', 'M14B', 'M16A', 'M16B']


def fnum(r, k):
    v = (r.get(k) or '').strip()
    try:
        return float(v)
    except Exception:
        return None


def s3_by_recommended(r):
    """발동이벤트 한 행을 추천 임계로 S3 판정.
    S3 = any_ra AND (any_rd_or_sla OR any_rc) AND (any_rb OR flow_severe)
    """
    any_ra = False
    for a in AREAS:
        v = fnum(r, f'{a}_ra')
        if v is not None and a in TH_RA and v >= TH_RA[a]:
            any_ra = True
    any_rb = False
    for a in AREAS:
        v = fnum(r, f'{a}_rb_diff30')
        if v is not None and a in TH_RB30 and v >= TH_RB30[a]:
            any_rb = True
    rev = fnum(r, 'M16HUB_rev_count')
    trend = fnum(r, 'M16HUB_rc_trend')
    any_rc = (rev is not None and trend is not None and trend < 0 and rev >= TH_RC)
    fab = fnum(r, 'M16HUB_rd_fab')
    stb = fnum(r, 'M16HUB_stb_util')
    any_rd = (fab is not None and fab >= TH_FAB) or (stb is not None and stb >= TH_STB)
    any_sla = False
    for a, th in TH_SLA.items():
        v = fnum(r, f'sla_{a}')
        if v is not None and v >= th:
            any_sla = True
    fscore = fnum(r, 'flow_score') or 0
    flow_severe = fscore >= 15
    return any_ra and (any_rd or any_sla or any_rc) and (any_rb or flow_severe)


def build_incidents_recommended(gap_min=10):
    """발동이벤트 → 추천 임계 S3 연속 구간 → 사건 재구성."""
    incidents = []
    for fp in sorted(glob.glob(f'{V4}/AP/extracted/*_발동이벤트.csv')):
        rows = list(csv.DictReader(open(fp, encoding='utf-8-sig')))
        cur = None
        last_s3 = None
        for r in rows:
            try:
                t = datetime.strptime(r['datetime'], '%Y-%m-%d %H:%M')
            except Exception:
                continue
            if s3_by_recommended(r):
                score = fnum(r, 'unified_risk_score') or 0
                if cur is None:
                    cur = {'predict': t, 'start': t, 'end': t, 'score': score}
                else:
                    cur['end'] = t
                    cur['score'] = max(cur['score'], score)
                last_s3 = t
            else:
                if cur is not None and last_s3 is not None:
                    if (t - last_s3).total_seconds() / 60.0 >= gap_min:
                        incidents.append(cur)
                        cur = None
        if cur is not None:
            incidents.append(cur)
    return incidents


def load_v41_incidents():
    """기존 v4.1 사건단위 (이미 생성된 것)."""
    incidents = []
    for fp in sorted(glob.glob(f'{V4}/AP/extracted/*_사건단위.csv')):
        day8 = os.path.basename(fp)[:8]
        day = f"{day8[:4]}-{day8[4:6]}-{day8[6:]}"
        for r in csv.DictReader(open(fp, encoding='utf-8-sig')):
            try:
                predict = datetime.strptime(f"{day} {r['predict_time']}", '%Y-%m-%d %H:%M')
                start = datetime.strptime(f"{day} {r['start_time']}", '%Y-%m-%d %H:%M')
                end = datetime.strptime(f"{day} {r['end_time']}", '%Y-%m-%d %H:%M')
                if start < predict: start += timedelta(days=1)
                if end < start: end += timedelta(days=1)
                incidents.append({'predict': predict, 'start': start, 'end': end,
                                  'score': int(r.get('max_risk_score', 0) or 0)})
            except Exception:
                continue
    return incidents


def load_episodes():
    eps = []
    fp = f'{V4}/룰베이스_v5/운영로그_분석_v2/output/20260612_065558_episode.csv'
    for e in csv.DictReader(open(fp, encoding='utf-8-sig')):
        if e.get('is_orphan') == 'Y':
            continue
        try:
            eps.append({
                'start': datetime.strptime(e['start_time'], '%Y-%m-%d %H:%M:%S'),
                'end': datetime.strptime(e['end_time'], '%Y-%m-%d %H:%M:%S'),
                'type': e.get('fault_type', ''),
            })
        except Exception:
            continue
    return eps


def match_and_report(incidents, episodes, label):
    """1:1 최근접 매칭 (사건_예측검증 동일 로직)."""
    W = timedelta(minutes=30)
    MAX_LEAD = 120
    for i in incidents:
        i['matched'] = False
    for e in episodes:
        e['matched'] = False
    matches = []
    for ep in sorted(episodes, key=lambda x: x['start']):
        best = None
        for inc in incidents:
            if inc['matched']:
                continue
            if not ((inc['predict'] - W) <= ep['end'] and (ep['start'] - W) <= inc['end']):
                continue
            lead = (ep['start'] - inc['predict']).total_seconds() / 60.0
            if lead > MAX_LEAD or lead < -30:
                continue
            gap = abs(lead)
            if best is None or gap < best[2]:
                best = (inc, lead, gap)
        if best:
            inc, lead, _ = best
            inc['matched'] = True
            ep['matched'] = True
            matches.append({'lead': lead, 'ep': ep})
    tp = sum(1 for i in incidents if i['matched'])
    fp = len(incidents) - tp
    miss = sum(1 for e in episodes if not e['matched'])
    prec = tp / (tp + fp) * 100 if (tp + fp) else 0
    rec = tp / (tp + miss) * 100 if (tp + miss) else 0
    leads = [m['lead'] for m in matches]
    ahead = sum(1 for l in leads if l > 0)
    avg_lead = sum(leads) / len(leads) if leads else 0

    print(f"\n{'='*60}")
    print(f"  [{label}]")
    print(f"{'='*60}")
    print(f"  룰베이스 사건: {len(incidents)}건")
    print(f"  TP(실제장애 매칭): {tp} | FP(오탐): {fp} | Miss(놓침): {miss}")
    print(f"  정밀도: {prec:.1f}% | 재현율: {rec:.1f}%")
    print(f"  사전예측: {ahead}/{len(leads)}건 | 평균 리드: {avg_lead:+.0f}분")
    return {'n': len(incidents), 'tp': tp, 'fp': fp, 'miss': miss,
            'prec': prec, 'rec': rec, 'avg_lead': avg_lead}


def main():
    episodes = load_episodes()
    print(f"메신저 실제 장애(Episode): {len(episodes)}건")

    v41 = load_v41_incidents()
    rec = build_incidents_recommended()

    r1 = match_and_report(v41, load_episodes(), "v4.1 임계 (현재)")
    r2 = match_and_report(rec, load_episodes(), "추천 임계 (적용 시)")

    print(f"\n{'='*60}")
    print("  [비교 — 추천 임계 적용 효과]")
    print(f"{'='*60}")
    print(f"  {'지표':12s} {'v4.1':>10s} {'추천':>10s} {'변화':>12s}")
    print(f"  {'사건 수':10s} {r1['n']:>10} {r2['n']:>10} {r2['n']-r1['n']:>+12}")
    print(f"  {'FP(오탐)':9s} {r1['fp']:>10} {r2['fp']:>10} {r2['fp']-r1['fp']:>+12}")
    print(f"  {'TP(탐지)':9s} {r1['tp']:>10} {r2['tp']:>10} {r2['tp']-r1['tp']:>+12}")
    print(f"  {'Miss(놓침)':8s} {r1['miss']:>10} {r2['miss']:>10} {r2['miss']-r1['miss']:>+12}")
    print(f"  {'정밀도':11s} {r1['prec']:>9.1f}% {r2['prec']:>9.1f}% {r2['prec']-r1['prec']:>+11.1f}%")
    print(f"  {'재현율':11s} {r1['rec']:>9.1f}% {r2['rec']:>9.1f}% {r2['rec']-r1['rec']:>+11.1f}%")


if __name__ == '__main__':
    main()
