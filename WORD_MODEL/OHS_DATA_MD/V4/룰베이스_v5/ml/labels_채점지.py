#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
labels_채점지 — 메신저 Episode → 30분 채점 윈도우 (Phase 1)
====================================================================
★ 라벨은 '학습' 이 아니라 '채점지'.  TSPulse 는 정상만 학습하고,
  이 라벨은 이상점수가 정체 30분 전에 올랐는지 채점/평가에만 사용.
★ XGBoost 지도 백업에서는 이 라벨을 정답(y)으로 사용.

정체 episode 시작시각 t0 → (t0-lead, t0] 구간 = "정체 lead분 전" 양성(1).
정상 구간 정의(TSPulse 학습용) = 정체 ±guard분 을 뺀 나머지.

★ 표준 라이브러리만 사용.

입력:
    --episode  episode.csv (운영로그_분석_v2/output/*_episode.csv)
    --features features.csv (features_31.py 산출 — 시간 그리드 기준)
    --lead     사전예측 창 분 (기본 30)
    --guard    정상구간에서 제외할 정체 전후 여유 분 (기본 60)
    --out      출력 폴더 (기본 ./out_ml)

정체로 인정하는 fault_type (orphan='Y' 제외):
    정체/병목, 리프터, CNV, MLUD, 브릿지

실행:
    python labels_채점지.py --episode ..._episode.csv --features ./out_ml/features.csv

출력:
    labels.csv         — datetime, y_pre30(양성), is_normal(정상구간), episode_id
    episodes_jam.csv   — 채점 대상 정체 사건 목록 (t0, fault_type, duration)
"""
import argparse
import csv
import os
from datetime import datetime, timedelta

# 정체로 채점하는 fault_type (CAPA변경=조치, 기타/공란=모호 → 제외)
JAM_TYPES = {'정체/병목', '리프터', 'CNV', 'MLUD', '브릿지'}


def parse_dt(s):
    s = (s or '').strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def load_episodes(fp):
    """episode.csv → 정체 사건 [(t0, fault_type, dur, episode_id)]."""
    jams = []
    for enc in ('utf-8-sig', 'utf-8', 'cp949'):
        try:
            rows = list(csv.DictReader(open(fp, encoding=enc)))
            break
        except UnicodeDecodeError:
            continue
    else:
        raise SystemExit(f"⚠️ episode 읽기 실패: {fp}")
    for r in rows:
        if (r.get('is_orphan') or '').strip().upper() == 'Y':
            continue
        ft = (r.get('fault_type') or '').strip()
        if ft not in JAM_TYPES:
            continue
        t0 = parse_dt(r.get('start_time'))
        if t0 is None:
            continue
        t0 = t0.replace(second=0)
        dur = (r.get('duration_min') or '').strip()
        jams.append((t0, ft, dur, (r.get('episode_id') or '').strip()))
    jams.sort()
    return jams


def load_feature_times(fp):
    """features.csv 의 datetime 그리드만 로드."""
    times = []
    for enc in ('utf-8-sig', 'utf-8', 'cp949'):
        try:
            rd = csv.DictReader(open(fp, encoding=enc))
            for row in rd:
                t = parse_dt(row.get('datetime'))
                if t:
                    times.append(t)
            break
        except UnicodeDecodeError:
            continue
    return sorted(times)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--episode', required=True)
    ap.add_argument('--features', required=True)
    ap.add_argument('--lead', type=int, default=30)
    ap.add_argument('--guard', type=int, default=60)
    ap.add_argument('--out', default='./out_ml')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    print("=" * 60)
    print(f"labels_채점지 — lead {a.lead}분 / guard ±{a.guard}분")
    print("=" * 60)

    jams = load_episodes(a.episode)
    times = load_feature_times(a.features)
    if not times:
        raise SystemExit("⚠️ features.csv 시간 그리드 없음 — features_31.py 먼저 실행")
    t_lo, t_hi = times[0], times[-1]

    # features 범위 안의 정체만 채점 대상
    jams_in = [j for j in jams if t_lo <= j[0] <= t_hi]
    print(f"[정체] 전체 {len(jams)}건 중 features 범위 내 {len(jams_in)}건 채점 대상")

    # 각 분 → 양성창(어느 정체든 t0-lead < t <= t0) / 정상(어느 정체든 ±guard 밖)
    pre_ranges = [(t0 - timedelta(minutes=a.lead), t0, eid) for t0, _, _, eid in jams_in]
    guard_ranges = [(t0 - timedelta(minutes=a.guard), t0 + timedelta(minutes=a.guard))
                    for t0, _, _, _ in jams_in]

    n_pos = n_normal = 0
    with open(os.path.join(a.out, 'labels.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['datetime', 'y_pre30', 'is_normal', 'episode_id'])
        for t in times:
            eid = ''
            y = 0
            for lo, hi, e in pre_ranges:
                if lo < t <= hi:
                    y = 1
                    eid = e
                    break
            in_guard = any(g0 <= t <= g1 for g0, g1 in guard_ranges)
            is_normal = 0 if in_guard else 1
            n_pos += y
            n_normal += is_normal
            w.writerow([t.strftime('%Y-%m-%d %H:%M'), y, is_normal, eid])

    with open(os.path.join(a.out, 'episodes_jam.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['t0', 'fault_type', 'duration_min', 'episode_id'])
        for t0, ft, dur, eid in jams_in:
            w.writerow([t0.strftime('%Y-%m-%d %H:%M'), ft, dur, eid])

    n = len(times)
    print(f"[라벨] {n}분 중 양성(정체 {a.lead}분전) {n_pos}분 "
          f"({n_pos/n*100:.1f}%) · 정상구간 {n_normal}분 ({n_normal/n*100:.1f}%)")
    print(f"       불균형비 ≈ 1:{(n-n_pos)/max(n_pos,1):.0f}  (XGBoost scale_pos_weight 참고)")
    print(f"🎉 → {a.out}/labels.csv · episodes_jam.csv")
    print("다음: tspulse_train.py (is_normal=1 구간만 학습)")


if __name__ == '__main__':
    main()
