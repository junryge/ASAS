#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
피처병합_발동이벤트 — hubroom 발동이벤트의 전문가 신호를 features.csv 에 입력피처로 병합
====================================================================================
[역할] 발동이벤트는 '라벨'로는 못 쓰지만(국소 밀림을 정상으로 봄), 그 안의 전문가
계산 신호(영역점수·ra_count·rb_diff·리프터역증가 등)는 훌륭한 '입력(X)'이다.
→ features.csv(원신호 43) + 발동이벤트 전문가 30컬럼 = 확장 피처 73개.
   이후 xgb_비정상_train 이 롤링/델타/CUSUM 파생까지 자동 생성.

입력:
    --features  features_31 산출 features.csv (datetime 그리드 기준)
    --events    발동이벤트 폴더(*발동이벤트*.csv) 또는 단일 csv
    --out       확장 피처 출력 (기본 <features>_확장.csv)

실행:
    python 피처병합_발동이벤트.py --features ./out_ml/features.csv --events ./predict_tobe --out ./out_ml/features_확장.csv

★ 학습(4~5월)과 추론(6월) 양쪽 다 이 스크립트로 병합해야 피처 스키마가 일치함.
★ 발동이벤트 없는 분은 공란 → 학습/추론에서 ffill→0 처리 (기존 로직 그대로).
★ 표준 라이브러리만 사용.
"""
import argparse
import csv
import glob
import os
import sys
from datetime import datetime

# 발동이벤트에서 가져올 전문가 컬럼 30개 (매분 숫자 신호만 — 문자열/사유 컬럼 제외)
EXPERT_COLS = [
    'unified_risk_score', 'hot_score',
    'M16HUB_score', 'M14_score', 'M14B_score', 'M16A_score', 'M16B_score',
    'M16HUB_ra_count', 'M14_ra_count', 'M14B_ra_count', 'M16A_ra_count', 'M16B_ra_count',
    'M16HUB_rb_diff10', 'M14_rb_diff10', 'M14B_rb_diff10', 'M16A_rb_diff10', 'M16B_rb_diff10',
    'M16HUB_rb_diff30', 'M14_rb_diff30', 'M14B_rb_diff30', 'M16A_rb_diff30', 'M16B_rb_diff30',
    'M16HUB_rc_trend', 'M14_cnv_skew', 'M16HUB_rev_count',
    'M16HUB_score_raw', 'M14_score_raw', 'M14B_score_raw', 'M16A_score_raw', 'M16B_score_raw',
]


def parse_dt(s):
    s = (s or '').strip()
    try:
        return datetime.strptime(s[:16], '%Y-%m-%d %H:%M')
    except ValueError:
        return None


def load_events(path):
    """발동이벤트 파일들 → {분: {expert_col: 값}}"""
    if os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, '*발동이벤트*.csv')))
        if not files:                                   # 파일명 다르면 헤더로 판별
            files = sorted(glob.glob(os.path.join(path, '*.csv')))
    else:
        files = [path]
    grid = {}
    used = 0
    for fp in files:
        with open(fp, encoding='utf-8-sig', newline='') as f:
            rd = csv.DictReader(f)
            cols = rd.fieldnames or []
            if 'unified_risk_score' not in cols or 'datetime' not in cols:
                continue                                # 사건단위 등 다른 파일 스킵
            used += 1
            present = [c for c in EXPERT_COLS if c in cols]
            for x in rd:
                t = parse_dt(x.get('datetime'))
                if not t:
                    continue
                cell = grid.setdefault(t, {})
                for c in present:
                    v = (x.get(c) or '').strip()
                    if v == '':
                        continue
                    try:
                        cell[c] = float(v)
                    except ValueError:
                        pass
    if not used:
        print('⚠️ 발동이벤트 형식 파일을 못 찾음 (datetime + unified_risk_score 헤더 필요)')
        sys.exit(2)
    print(f'[발동이벤트] 파일 {used}개 → {len(grid)}분 로드')
    return grid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', required=True)
    ap.add_argument('--events', required=True)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    out = a.out or a.features.replace('.csv', '_확장.csv')

    grid = load_events(a.events)

    n = matched = 0
    with open(a.features, encoding='utf-8-sig', newline='') as fin, \
         open(out, 'w', newline='', encoding='utf-8-sig') as fout:
        rd = csv.DictReader(fin)
        base = rd.fieldnames or []
        dup = [c for c in EXPERT_COLS if c in base]
        add = [c for c in EXPERT_COLS if c not in base]
        if dup:
            print(f'[주의] features 에 이미 있는 컬럼 {len(dup)}개는 건너뜀: {dup[:3]}...')
        w = csv.writer(fout)
        w.writerow(base + add)
        for x in rd:
            t = parse_dt(x.get('datetime'))
            cell = grid.get(t, {}) if t else {}
            if cell:
                matched += 1
            row = [x.get(c, '') for c in base]
            row += ['' if c not in cell else f'{cell[c]:g}' for c in add]
            w.writerow(row)
            n += 1

    print(f'[완료] {n}분 × (원 {len(base) - 1} + 전문가 {len(add)}) → {out}')
    print(f'       발동이벤트 매칭 {matched}분 ({matched / max(1, n) * 100:.1f}%) — 공란은 학습시 ffill→0')
    if matched / max(1, n) < 0.5:
        print('⚠️ 매칭률 50% 미만 — 발동이벤트 기간이 features 기간과 맞는지 확인')
    print('다음: xgb_라벨_통합.py → xgb_비정상_train.py (이 확장 피처 사용)')


if __name__ == '__main__':
    main()
