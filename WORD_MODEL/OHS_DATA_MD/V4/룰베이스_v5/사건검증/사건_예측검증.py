#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사건 예측 검증 — 룰베이스가 메신저 실제 장애를 얼마나 '먼저' 예측했나

핵심 질문: 룰베이스 예측 시각(predict_time)이 메신저 실제 장애보다 빠른가?

입력:
  1) 룰베이스 사건단위.csv (predict_time/start_time/end_time/score/hot_area)
     - predict_time: 룰베이스가 위험 신호를 처음 감지한 시각
     - start_time:   S3 확정 시각 (predict + lead_min)
  2) 메신저 Episode.csv (start_time = 운영자 인지/실제 발생)

매칭 + 리드타임:
  - 시간축 겹침으로 TP/FP/Miss 판정
  - TP 마다 리드타임 = 메신저_발생 - 룰베이스_predict_time
    · 양수(+) = 룰베이스가 먼저 예측 (목표!)
    · 음수(-) = 룰베이스가 늦음

출력:
  - prediction_match.csv : 매칭된 사건별 리드타임
  - summary.txt          : 사전 예측률 / 평균 리드타임 / 유형별
"""
import csv
import glob
import os
import sys
from datetime import datetime, timedelta
from collections import Counter, defaultdict


def load_csv(path):
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def parse_hm(day_str, hm_str):
    """'2026-05-08' + '00:22' → datetime. 자정 넘김 보정 호출측에서."""
    return datetime.strptime(f"{day_str} {hm_str}", '%Y-%m-%d %H:%M')


def load_incidents(incident_glob):
    """룰베이스 사건단위 — 여러 일자 파일 합치기."""
    incidents = []
    for fp in sorted(glob.glob(incident_glob)):
        day8 = os.path.basename(fp)[:8]
        day = f"{day8[:4]}-{day8[4:6]}-{day8[6:]}"
        for r in load_csv(fp):
            try:
                predict = parse_hm(day, r['predict_time'])
                start = parse_hm(day, r['start_time'])
                end = parse_hm(day, r['end_time'])
                # 자정 넘김 보정
                if start < predict:
                    start += timedelta(days=1)
                if end < start:
                    end += timedelta(days=1)
                incidents.append({
                    'day': day,
                    'predict': predict,      # 룰베이스 첫 예측 신호
                    'start': start,          # S3 확정
                    'end': end,
                    'score': int(r.get('max_risk_score', 0) or 0),
                    'level': r.get('max_risk_level', ''),
                    'hot_area': r.get('hot_area', ''),
                    'matched': False,
                })
            except Exception:
                continue
    return incidents


def load_episodes(episode_path):
    """메신저 Episode — 실제 발생 (orphan 제외)."""
    episodes = []
    for e in load_csv(episode_path):
        if e.get('is_orphan') == 'Y':
            continue
        try:
            st = datetime.strptime(e['start_time'], '%Y-%m-%d %H:%M:%S')
            et = datetime.strptime(e['end_time'], '%Y-%m-%d %H:%M:%S')
            episodes.append({
                'start': st, 'end': et,
                'equipment': e.get('equipment', ''),
                'type': e.get('fault_type', ''),
                'matched': False,
            })
        except Exception:
            continue
    return episodes


def overlap(a_s, a_e, b_s, b_e, window):
    """시간 구간 겹침 (window 여유)."""
    return (a_s - window) <= b_e and (b_s - window) <= a_e


def match(incidents, episodes, window_min):
    """매칭 + 리드타임 계산.
    매칭 기준: 룰베이스 사건의 [predict ~ end] 와 메신저 Episode 시간 겹침.
    리드타임 = 메신저 발생(start) - 룰베이스 예측(predict).
    """
    W = timedelta(minutes=window_min)
    for inc in incidents:
        inc['matched'] = False
        inc['lead_min'] = None
    for ep in episodes:
        ep['matched'] = False

    matches = []
    for ep in episodes:
        best = None
        for inc in incidents:
            # 같은 날 근방만
            if abs((inc['predict'] - ep['start']).total_seconds()) > 86400 * 1.5:
                continue
            # 룰베이스 신호 구간 [predict ~ end] 와 메신저 장애 [start ~ end] 겹침
            if overlap(inc['predict'], inc['end'], ep['start'], ep['end'], W):
                lead = (ep['start'] - inc['predict']).total_seconds() / 60.0
                # 가장 리드타임 긴(=가장 먼저 예측한) 사건 선택
                if best is None or lead > best[1]:
                    best = (inc, lead)
        if best is not None:
            inc, lead = best
            inc['matched'] = True
            inc['lead_min'] = lead
            ep['matched'] = True
            matches.append({'episode': ep, 'incident': inc, 'lead_min': lead})
    return matches


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    v4 = os.path.abspath(os.path.join(base, '..', '..'))

    incident_glob = os.path.join(v4, 'AP', 'extracted', '*_사건단위.csv')
    episode_path = os.path.join(
        v4, '룰베이스_v5', '운영로그_분석_v2', 'output',
        '20260612_065558_episode.csv')

    if len(sys.argv) >= 2:
        incident_glob = sys.argv[1]
    if len(sys.argv) >= 3:
        episode_path = sys.argv[2]

    incidents = load_incidents(incident_glob)
    episodes = load_episodes(episode_path)
    print(f"룰베이스 사건: {len(incidents)}건")
    print(f"메신저 실제 장애(Episode, orphan제외): {len(episodes)}건")
    print()

    # window 민감도 분석
    print("=" * 64)
    print("  [1] 매칭 민감도 — window 별 TP/FP/Miss")
    print("=" * 64)
    print(f"  {'window':>8} | {'TP':>4} | {'FP':>5} | {'Miss':>5} | {'정밀도':>7} | {'재현율':>7}")
    for w in (0, 10, 30, 60):
        matches = match(incidents, episodes, w)
        tp = sum(1 for i in incidents if i['matched'])
        fp = len(incidents) - tp
        miss = sum(1 for e in episodes if not e['matched'])
        prec = tp / (tp + fp) * 100 if (tp + fp) else 0
        rec = tp / (tp + miss) * 100 if (tp + miss) else 0
        print(f"  {w:>6}분 | {tp:>4} | {fp:>5} | {miss:>5} | {prec:>6.1f}% | {rec:>6.1f}%")

    # 기준 window = 30분 으로 리드타임 분석
    W = 30
    matches = match(incidents, episodes, W)
    print()
    print("=" * 64)
    print(f"  [2] 사전 예측 리드타임 (window {W}분 기준) ★ 핵심")
    print("=" * 64)
    leads = [m['lead_min'] for m in matches]
    if leads:
        ahead = [l for l in leads if l > 0]      # 룰베이스가 먼저
        behind = [l for l in leads if l <= 0]    # 룰베이스가 늦음
        print(f"  매칭된 실제 장애: {len(matches)}건")
        print(f"  └ 룰베이스가 먼저 예측 (리드 > 0): {len(ahead)}건 ({len(ahead)/len(leads)*100:.0f}%)")
        print(f"  └ 룰베이스가 늦거나 동시 (≤ 0)   : {len(behind)}건")
        print()
        leads_sorted = sorted(leads, reverse=True)
        print(f"  평균 리드타임: {sum(leads)/len(leads):+.0f}분")
        print(f"  최대(가장 먼저): {max(leads):+.0f}분")
        print(f"  중앙값: {leads_sorted[len(leads_sorted)//2]:+.0f}분")
        print(f"  30분 이상 사전 예측: {sum(1 for l in leads if l >= 30)}건 "
              f"({sum(1 for l in leads if l >= 30)/len(leads)*100:.0f}%)")
        print()
        print("  [리드타임 TOP 8 — 가장 먼저 예측한 사건]")
        for m in sorted(matches, key=lambda x: -x['lead_min'])[:8]:
            ep = m['episode']
            inc = m['incident']
            print(f"    {ep['start'].strftime('%m-%d %H:%M')} [{ep['type'] or ep['equipment']:10s}] "
                  f"실제발생 ← 룰베이스 {inc['predict'].strftime('%H:%M')} 예측 "
                  f"(리드 {m['lead_min']:+.0f}분, score {inc['score']})")

    # 유형별 매칭
    print()
    print("=" * 64)
    print("  [3] 장애 유형별 — 룰베이스가 잡았나")
    print("=" * 64)
    type_total = Counter(e['type'] or '(미상)' for e in episodes)
    type_matched = Counter(e['type'] or '(미상)' for e in episodes if e['matched'])
    for t in type_total:
        tot = type_total[t]
        mat = type_matched.get(t, 0)
        print(f"    {t:12s}: {mat}/{tot} 매칭 ({mat/tot*100:.0f}%)")

    # FP score 분포 (과대발동 진단)
    print()
    print("=" * 64)
    print("  [4] FP(메신저 없는 룰베이스 사건) score 분포 — 과대발동 진단")
    print("=" * 64)
    fps = [i for i in incidents if not i['matched']]
    print(f"    FP 총 {len(fps)}건")
    buckets = {'65~79(경계)': 0, '80~149(주의)': 0, '150~249(위험)': 0, '250+(매우위험)': 0}
    for i in fps:
        s = i['score']
        if s < 80: buckets['65~79(경계)'] += 1
        elif s < 150: buckets['80~149(주의)'] += 1
        elif s < 250: buckets['150~249(위험)'] += 1
        else: buckets['250+(매우위험)'] += 1
    for k, v in buckets.items():
        print(f"      {k:16s}: {v}건")
    print(f"    → score 낮은 FP(경계/주의) 비율이 높으면 = 임계 낮아 과대발동")

    # CSV 저장
    out_dir = os.path.join(base, 'output')
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_csv = os.path.join(out_dir, f'{stamp}_prediction_match.csv')
    with open(out_csv, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['episode_start', 'episode_type', 'episode_equip',
                    'rule_predict_time', 'rule_start_time', 'rule_score',
                    'lead_min', 'ahead'])
        for m in sorted(matches, key=lambda x: x['episode']['start']):
            ep, inc = m['episode'], m['incident']
            w.writerow([
                ep['start'].strftime('%Y-%m-%d %H:%M'), ep['type'], ep['equipment'],
                inc['predict'].strftime('%Y-%m-%d %H:%M'),
                inc['start'].strftime('%Y-%m-%d %H:%M'), inc['score'],
                f"{m['lead_min']:.0f}", 'Y' if m['lead_min'] > 0 else 'N',
            ])
    print()
    print(f"✅ 저장: {out_csv}")


if __name__ == '__main__':
    main()
