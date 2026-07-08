#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xgb_라벨_통합 — 메신저(episode) + hubroom(발동이벤트) + 수동 이벤트 → 통합 라벨
====================================================================================
[왜] hubroom 라벨만 쓰면 국소 밀림(6/11·22·24·29형)은 hubroom이 정상(12~47점)으로
봐서 ML이 영원히 못 배움 (6월 발동이벤트로 확정). 진짜 정답 = 메신저(고객 확인 사건).
→ 세 소스를 합쳐 라벨: ①메신저 episode(밀림·국소) ∪ ②hubroom≥thr(큰 정체) ∪ ③수동.

[라벨 정의]
  y_pre10(t)=1 : t+1~t+10분 안에 '사건 순간'이 있음 (10분 전 예측 정답)
  y_pre30(t)=1 : t+1~t+30분 안에 '사건 순간'이 있음
  is_normal(t)=1 : ±guard분 내 어떤 사건도 없음 (확실한 정상)
  '사건 순간' = 메신저 episode 시작시각(부터 dur분) ∪ hubroom 점수≥thr 분 ∪ 수동 시각(부터 dur분)

입력:
    --features   features.csv (시간 그리드 기준 — 이 파일의 매분에 라벨 부여)
    --episodes   (옵션) 메신저 episode.csv — start_time|t0 [, fault_type, orphan]
    --events     (옵션) hubroom predict_tobe 폴더(*발동이벤트*.csv) — unified_risk_score
    --manual     (옵션) 수동 이벤트 csv — datetime[,type] 한 줄에 하나 (예: 2026-05-11 10:18)
    --thr        hubroom 점수 임계 (기본 50)
    --dur        점 이벤트(메신저·수동)의 사건 지속 간주(분, 기본 10)
    --pre        선행 지평선(분, 쉼표) 기본 10,30
    --guard      정상 가드(분) 기본 60
    --out        labels.csv

실행 (4~5월 학습 라벨):
    python xgb_라벨_통합.py --features ./out_ml/features.csv ^
        --episodes ./episode.csv --events ./predict_tobe --out ./out_ml/labels_통합.csv

★ 시간 방향: 피처는 t까지, 라벨은 t 이후 → 누수 없음.
★ 표준 라이브러리만 사용.
"""
import argparse
import csv
import glob
import os
import sys
from datetime import datetime, timedelta


def parse_dt(s):
    s = (s or '').strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M', '%Y-%m-%dT%H:%M'):
        try:
            return datetime.strptime(s[:19], fmt).replace(second=0)
        except ValueError:
            continue
    return None


def load_episodes(fp, dur):
    """메신저 episode.csv → 사건 분(minute) 집합. start_time|t0 부터 dur분."""
    mins = set()
    n = 0
    with open(fp, encoding='utf-8-sig', newline='') as f:
        rd = csv.DictReader(f)
        cols = rd.fieldnames or []
        tcol = 't0' if 't0' in cols else ('start_time' if 'start_time' in cols else None)
        if not tcol:
            print(f"⚠️ episode.csv 에 t0/start_time 없음 (컬럼: {cols[:8]})"); return mins, 0
        for x in rd:
            if (x.get('orphan') or '').strip().upper() == 'Y':
                continue                                  # 고아(원인불명) 제외
            t = parse_dt(x.get(tcol))
            if not t:
                continue
            for k in range(dur):
                mins.add(t + timedelta(minutes=k))
            n += 1
    return mins, n


def load_hubroom(path, thr):
    """발동이벤트 폴더/파일 → 점수≥thr 분 집합."""
    files = []
    if os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, '*발동이벤트*.csv'))) or \
                sorted(glob.glob(os.path.join(path, '*.csv')))
    else:
        files = [path]
    mins = set()
    for fp in files:
        with open(fp, encoding='utf-8-sig', newline='') as f:
            rd = csv.DictReader(f)
            if 'unified_risk_score' not in (rd.fieldnames or []):
                continue
            for x in rd:
                t = parse_dt(x.get('datetime') or (x.get('date', '') + ' ' + x.get('time', '')))
                if not t:
                    continue
                try:
                    if float(x.get('unified_risk_score') or 0) >= thr:
                        mins.add(t)
                except ValueError:
                    pass
    return mins, len(files)


def load_manual(fp, dur):
    """수동 이벤트 csv (datetime[,type]) → 사건 분 집합."""
    mins = set()
    n = 0
    with open(fp, encoding='utf-8-sig', newline='') as f:
        for row in csv.reader(f):
            if not row:
                continue
            t = parse_dt(row[0])
            if not t:
                continue                                  # 헤더 등은 자동 스킵
            for k in range(dur):
                mins.add(t + timedelta(minutes=k))
            n += 1
    return mins, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', required=True)
    ap.add_argument('--episodes', default=None)
    ap.add_argument('--events', default=None)
    ap.add_argument('--manual', default=None)
    ap.add_argument('--thr', type=float, default=50)
    ap.add_argument('--dur', type=int, default=10)
    ap.add_argument('--pre', default='10,30')
    ap.add_argument('--guard', type=int, default=60)
    ap.add_argument('--out', default='./out_ml/labels_통합.csv')
    a = ap.parse_args()

    if not (a.episodes or a.events or a.manual):
        print("⚠️ --episodes / --events / --manual 중 최소 하나 필요"); sys.exit(2)

    # 사건 분 집합 (합집합) + 소스별 통계
    jam = set()
    if a.episodes and os.path.exists(a.episodes):
        m, n = load_episodes(a.episodes, a.dur)
        jam |= m
        print(f"[메신저] episode {n}건 → 사건 분 {len(m)}")
    if a.events and os.path.exists(a.events):
        m, n = load_hubroom(a.events, a.thr)
        jam |= m
        print(f"[hubroom] 파일 {n}개, 점수≥{a.thr:.0f} → 사건 분 {len(m)}")
    if a.manual and os.path.exists(a.manual):
        m, n = load_manual(a.manual, a.dur)
        jam |= m
        print(f"[수동] 이벤트 {n}건 → 사건 분 {len(m)}")
    if not jam:
        print("⚠️ 사건 분 0 — 입력 확인"); sys.exit(3)
    print(f"[통합] 사건 분 합집합 {len(jam)}")

    pres = [int(x) for x in str(a.pre).split(',') if x.strip()]

    # features 시간 그리드에 라벨 부여
    times = []
    with open(a.features, encoding='utf-8-sig', newline='') as f:
        rd = csv.DictReader(f)
        for x in rd:
            t = parse_dt(x.get('datetime'))
            if t:
                times.append(t)
    times.sort()

    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    npos = {p: 0 for p in pres}
    nnorm = 0
    with open(a.out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['datetime'] + [f'y_pre{p}' for p in pres] + ['is_normal'])
        for t in times:
            ys = []
            for p in pres:
                y = int(any((t + timedelta(minutes=k)) in jam for k in range(1, p + 1)))
                ys.append(y)
                npos[p] += y
            isn = int(not any((t + timedelta(minutes=k)) in jam
                              for k in range(-a.guard, a.guard + 1)))
            nnorm += isn
            w.writerow([t.strftime('%Y-%m-%d %H:%M')] + ys + [isn])

    n = len(times)
    print(f"[완료] {n}분 → {a.out}")
    for p in pres:
        print(f"       y_pre{p}=1 : {npos[p]}분 ({npos[p]/n*100:.1f}%)")
    print(f"       is_normal=1 : {nnorm}분 ({nnorm/n*100:.1f}%)")
    print("다음: python xgb_비정상_train.py --features <features.csv> --labels " + a.out)


if __name__ == '__main__':
    main()
