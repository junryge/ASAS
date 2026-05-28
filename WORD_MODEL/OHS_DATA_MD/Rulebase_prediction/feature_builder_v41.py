#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML 피처 빌더 v4.1 — raw 265컬럼 + 발동이벤트 50컬럼 join 방식

v3 feature_builder.py 와 차이:
  - v3: 룰엔진 함수 (iter_star_rows, evaluate_rules) 의존 → v4.1 비호환
  - v4.1: predict_tobe/*_발동이벤트.csv 를 timestamp 로 join (룰 재실행 불요)

피처 구성:
  1. raw 265 현재값                                            ≈ 265
  2. raw 핵심 수치 컬럼 × 5/10/30분 sliding (max/mean/std)    ≈ 80×9 = 720
  3. raw 핵심 수치 × 5/10/30분 delta                          ≈ 80×3 = 240
  4. 발동이벤트 30 수치 컬럼 (룰 컨텍스트)                    ≈ 30
  ─────────────────────────────────────────────────────────────────────
  합계: ~1250 피처 (필요시 --topk N 으로 선별)

사용:
  python feature_builder_v41.py \\
      --raw C:\\rawdata\\2026_01_05_all.csv \\
      --events_dir ..\\Rulebase_prediction\\predict_tobe \\
      --out features_v41.csv

옵션:
  --topk 400         : feature_importance 기준 상위만 (사후 적용, 일단 전체)
  --from 2026-03-24  : 학습 데이터 시작일 (1~3월 NULL 회피)
  --to 2026-05-31    : 학습 데이터 종료일
  --float32          : 메모리 절감 (1GB → 500MB)
"""

import argparse
import csv
import glob
import os
import sys
from collections import deque
from datetime import datetime, timedelta
from statistics import mean, stdev

WINDOW_MIN = 90   # 슬라이딩 윈도우 (룰베이스 v4.1 과 동일)


# ============================================================
# 핵심 수치 컬럼 — 시계열 통계 + delta 계산 대상 (~80개)
# ============================================================
# 영역별 ra (시간) — 영역별 컬럼명 다름!
RA_COLS = [
    'M16HUB.QUE.TIME.AVGTOTALTIME1MIN',
    'M14B.QUE.TIME.AVGTOTALTIME1MIN',
    'M16_PKT.QUE.TIME.AVGTOTALTIME1MIN',
    'M16_WT.QUE.TIME.AVGTOTALTIME1MIN',
    'M14.QUE.LOAD.AVGLOADTIME1MIN',
    'M16A.QUE.LOAD.AVGLOADTIME1MIN',
    'M16B.QUE.LOAD.AVGLOADTIME1MIN',
]

# 영역별 RB (인플로 큐)
RB_COLS = [
    'M16HUB.QUE.M14TOM16.MESCURRENTQCNT',
    'M14.QUE.ALL.3F_TO_HUB_JOB',
    'M14B.QUE.ALL.7F_TO_HUB_JOB',
    'M16A.QUE.ALL.6F_TO_HUB_JOB',
    'M16A.QUE.ALL.2F_TO_HUB_JOB',
    'M16B.QUE.ALL.10F_TO_HUB_JOB',
    'M16.QUE.SFAB.SENDQUEUETOTAL',
]

# M16HUB 리프터 10대
LFT_HUB_COLS = [
    f'M16HUB.LFT.{lid}.TOTAL_CURRENTQCNT' for lid in
    ['6ABL6011', '6ABL6012', '6ABL6021', '6ABL6022', '6ABL6031', '6ABL6032',
     '6ABL0111', '6ABL0112', '6ABL0121', '6ABL0122']
]

# M14B 리프터 6대
LFT_M14B_COLS = [
    f'M14B.LFT.4ABLD{n}.TOTAL_CURRENTQCNT' for n in
    ['111', '112', '121', '122', '131', '132']
]

# OHT 가동률 (영역별)
OHTUTIL_COLS = [
    'M16HUB.QUE.OHT.OHTUTIL',
    'M14.QUE.OHT.OHTUTIL',
    'M14B.QUE.OHT.OHTUTIL',
    'M16A.QUE.OHT.OHTUTIL',
    'M16B.QUE.OHT.OHTUTIL',
    'M16_PKT.QUE.OHT.OHTUTIL',
    'M16_WT.QUE.OHT.OHTUTIL',
]

# R-D 공간
RD_COLS = [
    'M16HUB.STRATE.ALL.FABSTORAGERATIO',
    'M16HUB.STRATE.STB.3F_STORAGE_UTIL',
]

# SLA
SLA_COLS = [
    'M16HUB.QUE.ALL.TRANSPORT4MINOVERRATIO',
    'M14.QUE.ALL.TRANSPORT4MINOVERRATIO',
    'M16A.QUE.ALL.TRANSPORT4MINOVERRATIO',
    'M16B.QUE.ALL.TRANSPORT4MINOVERRATIO',
    'M16HUB.QUE.ALL.TRANSPORT4MINOVERCNT',
    'M14.QUE.ALL.TRANSPORT4MINOVERCNT',
    'M16A.QUE.ALL.TRANSPORT4MINOVERCNT',
    'M16B.QUE.ALL.TRANSPORT4MINOVERCNT',
]

# Sorter
SORTER_COLS = [
    'M14.SORTER.ABN.SORTERWAITCOUNTOVER',
    'M14B.SORTER.ABN.SORTERWAITCOUNTOVER',
    'M16A.SORTER.ABN.SORTERWAITCOUNTOVER',
    'M16B.SORTER.ABN.SORTERWAITCOUNTOVER',
]

# OHT 상태 (M14)
M14_STATE_COLS = [
    'M14.OHT.STATECNT.HTSTOP',
    'M14.OHT.STATECNT.CONGESTED',
    'M14.OHT.STATECNT.ABNORMAL',
]

# 모든 핵심 수치 컬럼 (시계열 통계 + delta 대상)
KEY_NUMERIC_COLS = (
    RA_COLS + RB_COLS + LFT_HUB_COLS + LFT_M14B_COLS +
    OHTUTIL_COLS + RD_COLS + SLA_COLS + SORTER_COLS + M14_STATE_COLS
)


# ============================================================
# 발동이벤트.csv 의 수치 컬럼 (룰 컨텍스트 — 직접 피처)
# ============================================================
EVENT_NUMERIC_COLS = [
    'stage', 'unified_risk_score',
    'M16HUB_score', 'M14_score', 'M14B_score', 'M16A_score', 'M16B_score',
    'M16_score', 'M16_PKT_score', 'M16_WT_score',
    'M16HUB_ra', 'M14_ra', 'M14B_ra', 'M16A_ra', 'M16B_ra',
    'M16HUB_rb_diff30', 'M14_rb_diff30', 'M14B_rb_diff30', 'M16A_rb_diff30',
    'M16HUB_rd_fab', 'M16HUB_stb_util', 'M16HUB_rev_count',
    'sla_M14', 'sla_M16A', 'sla_M16B', 'sla_M16HUB',
    'sorter_M14', 'sorter_M14B', 'sorter_M16A', 'sorter_M16B',
]


# ============================================================
# 유틸
# ============================================================
def _safe_float(v, default=None):
    try:
        if v is None or v == '':
            return default
        return float(v)
    except (ValueError, TypeError):
        return default


def _safe_max(seq, default=0):
    vals = [v for v in seq if v is not None]
    return max(vals) if vals else default


def _safe_mean(seq, default=0):
    vals = [v for v in seq if v is not None]
    return mean(vals) if vals else default


def _safe_std(seq, default=0):
    vals = [v for v in seq if v is not None]
    return stdev(vals) if len(vals) >= 2 else default


def _safe_delta(seq, k, default=0):
    if len(seq) < k:
        return default
    a, b = seq[-1], seq[-k]
    if a is None or b is None:
        return default
    return a - b


def _parse_time(s):
    if not s:
        return None
    s = s.strip().strip('"').strip("'")
    if 'T' in s:
        s = s.split('+')[0]
    if '.' in s:
        s = s.split('.')[0]
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d %H:%M'):
        try:
            t = datetime.strptime(s, fmt)
            return t.replace(second=0, microsecond=0)
        except ValueError:
            continue
    return None


def _open_with_encoding(path):
    """utf-8-sig → utf-8 → cp949 폴백."""
    for enc in ('utf-8-sig', 'utf-8', 'cp949'):
        try:
            f = open(path, 'r', encoding=enc, newline='')
            f.readline()  # 첫 줄 시도
            f.seek(0)
            return f
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f'인코딩 감지 실패: {path}')


# ============================================================
# 1) 발동이벤트.csv → timestamp 인덱싱 dict
# ============================================================
def load_events_dict(events_dir):
    """predict_tobe/*_발동이벤트.csv → { datetime_minute: row_dict }"""
    pattern = os.path.join(events_dir, '*_발동이벤트.csv')
    files = sorted(glob.glob(pattern))
    if not files:
        print(f'⚠ 발동이벤트 CSV 없음: {pattern}')
        return {}

    events = {}
    total = 0
    for fp in files:
        with _open_with_encoding(fp) as f:
            reader = csv.DictReader(f)
            for row in reader:
                t = _parse_time(row.get('datetime') or '')
                if t is None:
                    continue
                events[t] = row
                total += 1
    print(f'📥 발동이벤트 로드: {total:,}행 ({len(files)}개 파일)')
    return events


# ============================================================
# 2) raw CSV iter → 피처 추출 (sliding window)
# ============================================================
def iter_raw_rows(raw_csv):
    """raw CSV → (datetime_minute, row_dict) generator."""
    with _open_with_encoding(raw_csv) as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = _parse_time(row.get('CRT_TM') or '')
            if t is None:
                continue
            yield t, row


def build_features_row(t, raw_row, event_row, sliding_state):
    """1 시점 피처 dict."""
    f = {'timestamp': t.strftime('%Y-%m-%d %H:%M:%S')}

    # ── (1) raw 265 현재값 ──
    for col, val_str in raw_row.items():
        if col == 'CRT_TM':
            continue
        # 모든 컬럼 raw 현재값으로 (수치형 시도, 안 되면 0)
        f[f'raw__{col}'] = _safe_float(val_str, default=0) or 0

    # ── (2) raw 핵심 수치 슬라이딩 통계 + delta ──
    for col in KEY_NUMERIC_COLS:
        seq = list(sliding_state.get(col, []))
        # 5/10/30분 통계
        f[f'{col}__max_5m']  = _safe_max(seq[-5:])
        f[f'{col}__max_10m'] = _safe_max(seq[-10:])
        f[f'{col}__max_30m'] = _safe_max(seq[-30:])
        f[f'{col}__mean_30m'] = _safe_mean(seq[-30:])
        f[f'{col}__std_30m']  = _safe_std(seq[-30:])
        # delta
        f[f'{col}__delta_5m']  = _safe_delta(seq, 5)
        f[f'{col}__delta_10m'] = _safe_delta(seq, 10)
        f[f'{col}__delta_30m'] = _safe_delta(seq, 30)

    # ── (3) 발동이벤트 30 수치 컬럼 (룰 컨텍스트) ──
    if event_row:
        for col in EVENT_NUMERIC_COLS:
            v = event_row.get(col, '')
            f[f'event__{col}'] = _safe_float(v, default=0) or 0
    else:
        for col in EVENT_NUMERIC_COLS:
            f[f'event__{col}'] = 0

    return f


# ============================================================
# 메인 처리
# ============================================================
def process(raw_csv, events_dir, out_path,
            start_date=None, end_date=None,
            use_float32=False, drop_rule_context=False):
    """raw + events join → 피처 CSV."""
    # 발동이벤트 로드
    events = load_events_dict(events_dir)

    # 필터 날짜 파싱
    start_dt = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
    end_dt = datetime.strptime(end_date + ' 23:59', '%Y-%m-%d %H:%M') if end_date else None

    # 슬라이딩 윈도우 (key column 별 deque)
    sliding_state = {col: deque(maxlen=WINDOW_MIN) for col in KEY_NUMERIC_COLS}

    out_rows = []
    header = None
    skipped = 0
    total = 0

    for t, raw_row in iter_raw_rows(raw_csv):
        # 날짜 필터
        if start_dt and t < start_dt:
            continue
        if end_dt and t > end_dt:
            break

        # 슬라이딩 윈도우 갱신
        for col in KEY_NUMERIC_COLS:
            sliding_state[col].append(_safe_float(raw_row.get(col), default=None))

        # 30분 워밍업
        if len(sliding_state[KEY_NUMERIC_COLS[0]]) < 31:
            continue

        # 발동이벤트 매칭
        event_row = events.get(t)
        if event_row is None:
            # 발동이벤트 미생성 분 — 룰 컨텍스트는 0
            pass

        feat = build_features_row(t, raw_row, event_row, sliding_state)

        # 라벨 누수 방지 옵션
        if drop_rule_context:
            for col in EVENT_NUMERIC_COLS:
                feat.pop(f'event__{col}', None)

        if header is None:
            header = list(feat.keys())
            out_rows.append(feat)
        else:
            out_rows.append(feat)

        total += 1
        if total % 10000 == 0:
            print(f'  처리 {total:,}행...')

    if not out_rows:
        sys.exit('❌ 출력 행 0 — 입력/필터 확인')

    # CSV 저장
    with open(out_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for r in out_rows:
            if use_float32:
                r = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}
            writer.writerow(r)

    print(f'\n✅ {total:,}행 × {len(header)}컬럼 → {out_path}')
    print(f'   raw 현재값: ~{len([k for k in header if k.startswith("raw__")])}')
    print(f'   sliding 통계+delta: ~{len([k for k in header if "__max_" in k or "__mean_" in k or "__std_" in k or "__delta_" in k])}')
    print(f'   event 룰 컨텍스트: ~{len([k for k in header if k.startswith("event__")])}')
    if skipped:
        print(f'   스킵: {skipped}')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--raw', required=True, help='raw 265컬럼 CSV (수집기 출력)')
    p.add_argument('--events_dir', required=True, help='발동이벤트.csv 폴더 (predict_tobe)')
    p.add_argument('--out', default='features_v41.csv', help='출력 피처 CSV')
    p.add_argument('--from', dest='start_date', help='시작일 YYYY-MM-DD')
    p.add_argument('--to', dest='end_date', help='종료일 YYYY-MM-DD')
    p.add_argument('--float32', action='store_true', help='메모리 절감 모드')
    p.add_argument('--drop_rule_context', action='store_true',
                   help='event__ 컬럼 제외 (C 라벨 학습 시 누수 방지)')
    args = p.parse_args()

    process(
        raw_csv=args.raw,
        events_dir=args.events_dir,
        out_path=args.out,
        start_date=args.start_date,
        end_date=args.end_date,
        use_float32=args.float32,
        drop_rule_context=args.drop_rule_context,
    )


if __name__ == '__main__':
    main()
