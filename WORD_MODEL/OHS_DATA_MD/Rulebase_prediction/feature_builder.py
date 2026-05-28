#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML 피처 추출기 — 90min.csv → 피처 데이터프레임

사용법:
    python3 feature_builder.py --csv ../DATA/90min.csv --out features.csv

피처 그룹:
  · 현재값 (4가지 핵심 컬럼)
  · 슬라이딩 통계 (5/10/30분 max/mean/std)
  · 변화율 (5/10/30분 delta) — 모멘텀
  · 가속도 (변화의 변화)
  · 룰 컨텍스트 (R-A'/R-B/R-C'/R-D flag와 값)
  · 조합 피처 (interaction)

출력: features.csv (timestamp + 피처들)
"""

import argparse
import csv
import os
import sys
from collections import deque
from datetime import datetime
from statistics import mean, stdev


# 부모 디렉터리 추가하여 룰 엔진 재사용
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from importlib import import_module
import importlib.util

# 룰 엔진 파일 위치 자동 탐색 (운영본 hubroom_predictor.py 우선)
# (같은 폴더 → 상위 폴더 → Rulebase_prediction 폴더 → 현재 작업 디렉터리)
_this_dir = os.path.dirname(os.path.abspath(__file__))
_NAMES = ['hubroom_predictor.py', '3DO_PRETIME.py', '3단계_룰베이스_사건단위.py']  # 운영본 우선
_BASE_DIRS = [_this_dir,
              os.path.join(_this_dir, '..'),
              os.path.join(_this_dir, '..', 'Rulebase_prediction'),
              os.path.join(_this_dir, '..', '..', 'Rulebase_prediction'),
              os.getcwd(),
              os.path.join(os.getcwd(), '..')]
_candidates = [os.path.join(b, n) for b in _BASE_DIRS for n in _NAMES]

_rule_path = None
for _p in _candidates:
    if os.path.exists(_p):
        _rule_path = _p
        break

if _rule_path is None:
    raise FileNotFoundError(
        f"룰 엔진 파일(3DO_PRETIME.py 또는 3단계_룰베이스_사건단위.py)을 찾을 수 없습니다.\n"
        f"다음 위치 중 하나에 두세요:\n" + '\n'.join(f"  - {p}" for p in _candidates)
    )

_spec = importlib.util.spec_from_file_location('rule_engine', _rule_path)
_rule_engine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rule_engine)

iter_star_rows = _rule_engine.iter_star_rows
evaluate_rules = _rule_engine.evaluate_rules
WINDOW_MIN = _rule_engine.WINDOW_MIN


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
    """seq[-1] - seq[-k] (둘 다 not None)"""
    if len(seq) < k:
        return default
    a, b = seq[-1], seq[-k]
    if a is None or b is None:
        return default
    return a - b


def _v3_field(v3_window, key):
    """v3 윈도우의 최신 값"""
    if not v3_window:
        return 0
    latest = v3_window[-1]
    return latest.get(key) or 0


def _v3_series(v3_window, key, n):
    """v3 윈도우 최근 n개에서 key 값 시퀀스"""
    return [(d.get(key) or 0) for d in list(v3_window)[-n:]]


def build_features(t1_window, m14_window, lft_window, v3_window, rule_ctx):
    """1 시점 피처 dict 생성. 룰과 같은 윈도우 공유."""
    f = {}

    # ──────────────────── 1. 현재값 ────────────────────
    f['1min_now']           = (t1_window[-1] or 0) if t1_window else 0
    f['m14_now']            = (m14_window[-1] or 0) if m14_window else 0
    f['fabstorage_now']     = _v3_field(v3_window, 'fabstorage_ratio')
    f['m14b_oht_util']      = _v3_field(v3_window, 'm14b_oht_util')
    f['m14b_4abld122']      = _v3_field(v3_window, 'm14b_4abld122')
    f['m14b_7f_to_hub']     = _v3_field(v3_window, 'm14b_7f_to_hub')
    f['m14b_7f_to_hub_alt'] = _v3_field(v3_window, 'm14b_7f_to_hub_alt')
    # ★ v3.1 신규 현재값
    f['hub_storage_util']   = _v3_field(v3_window, 'hub_storage_util')
    f['m14_inflow']         = _v3_field(v3_window, 'm14_inflow')
    f['m16a_2f_inflow']     = _v3_field(v3_window, 'm16a_2f_inflow')
    f['m16a_6f_inflow']     = _v3_field(v3_window, 'm16a_6f_inflow')
    f['m16b_10f_inflow']    = _v3_field(v3_window, 'm16b_10f_inflow')
    f['inflow_total_now']   = (f['m14_inflow'] + f['m16a_2f_inflow']
                               + f['m16a_6f_inflow'] + f['m16b_10f_inflow']
                               + _v3_field(v3_window, 'm14b_7f_to_hub'))

    # 리프터 합/std (현재)
    lft_now = lft_window[-1] if lft_window else {}
    lft_vals = list(lft_now.values()) if lft_now else [0]
    f['lft_sum_now']    = sum(lft_vals)
    f['lft_max_now']    = max(lft_vals) if lft_vals else 0
    f['lft_std_now']    = stdev(lft_vals) if len(lft_vals) >= 2 else 0

    # ──────────────────── 2. 슬라이딩 통계 ────────────────────
    t1_list  = list(t1_window)
    m14_list = list(m14_window)

    f['1min_max_5m']    = _safe_max(t1_list[-5:])
    f['1min_max_10m']   = _safe_max(t1_list[-10:])
    f['1min_max_30m']   = _safe_max(t1_list[-30:])
    f['1min_mean_30m']  = _safe_mean(t1_list[-30:])
    f['1min_std_30m']   = _safe_std(t1_list[-30:])

    f['m14_max_30m']    = _safe_max(m14_list[-30:])
    f['m14_mean_30m']   = _safe_mean(m14_list[-30:])

    fab30 = _v3_series(v3_window, 'fabstorage_ratio', 30)
    f['fabstorage_max_30m']  = max(fab30) if fab30 else 0
    f['fabstorage_mean_30m'] = mean(fab30) if fab30 else 0
    f['fabstorage_std_30m']  = stdev(fab30) if len(fab30) >= 2 else 0

    # ──────────────────── 3. 변화율 (모멘텀) ★ ────────────────────
    f['1min_delta_5m']  = _safe_delta(t1_list, 5)
    f['1min_delta_10m'] = _safe_delta(t1_list, 10)
    f['1min_delta_30m'] = _safe_delta(t1_list, 30)

    f['m14_delta_10m']  = _safe_delta(m14_list, 11)
    f['m14_delta_30m']  = _safe_delta(m14_list, 31)

    fab10 = _v3_series(v3_window, 'fabstorage_ratio', 11)
    fab30s = _v3_series(v3_window, 'fabstorage_ratio', 31)
    f['fabstorage_delta_10m'] = (fab10[-1] - fab10[0]) if len(fab10) >= 2 else 0
    f['fabstorage_delta_30m'] = (fab30s[-1] - fab30s[0]) if len(fab30s) >= 2 else 0

    util30 = _v3_series(v3_window, 'm14b_oht_util', 31)
    f['m14b_util_delta_30m'] = (util30[-1] - util30[0]) if len(util30) >= 2 else 0

    abld122_30 = _v3_series(v3_window, 'm14b_4abld122', 31)
    f['m14b_4abld122_delta_30m'] = (abld122_30[-1] - abld122_30[0]) if len(abld122_30) >= 2 else 0

    # ★ v3.1 신규 변화율 피처 (가장 가치 있는 시그널)
    hub_st_30 = _v3_series(v3_window, 'hub_storage_util', 31)
    f['hub_storage_max_30m']   = max(hub_st_30) if hub_st_30 else 0
    f['hub_storage_min_30m']   = min(hub_st_30) if hub_st_30 else 0
    f['hub_storage_delta_30m'] = (hub_st_30[-1] - hub_st_30[0]) if len(hub_st_30) >= 2 else 0

    # 인플로 통합 변화율
    m14_in_30 = _v3_series(v3_window, 'm14_inflow', 31)
    f['m14_inflow_delta_30m']   = (m14_in_30[-1] - m14_in_30[0]) if len(m14_in_30) >= 2 else 0
    m14_in_10 = _v3_series(v3_window, 'm14_inflow', 11)
    f['m14_inflow_delta_10m']   = (m14_in_10[-1] - m14_in_10[0]) if len(m14_in_10) >= 2 else 0

    # 인플로 합계 시계열 (5개 합) — 10분 변화 / 30분 변화
    def _inflow_sum_at(idx):
        if not v3_window or len(v3_window) <= abs(idx):
            return 0
        d = list(v3_window)[idx]
        return ((d.get('m14_inflow') or 0) + (d.get('m16a_2f_inflow') or 0)
                + (d.get('m16a_6f_inflow') or 0) + (d.get('m16b_10f_inflow') or 0)
                + (d.get('m14b_7f_to_hub') or 0))
    inflow_now = _inflow_sum_at(-1)
    inflow_10 = _inflow_sum_at(-11) if len(v3_window) >= 11 else inflow_now
    inflow_30 = _inflow_sum_at(-31) if len(v3_window) >= 31 else inflow_now
    f['inflow_total_delta_10m'] = inflow_now - inflow_10
    f['inflow_total_delta_30m'] = inflow_now - inflow_30

    # ──────────────────── 4. 가속도 (변화의 변화) ────────────────────
    if len(t1_list) >= 11:
        d1 = (t1_list[-1] or 0) - (t1_list[-6] or 0)
        d2 = (t1_list[-6] or 0) - (t1_list[-11] or 0)
        f['1min_accel_5m'] = d1 - d2
    else:
        f['1min_accel_5m'] = 0

    if len(fab30s) >= 11:
        d1 = fab30s[-1] - fab30s[-6]
        d2 = fab30s[-6] - fab30s[-11]
        f['fabstorage_accel_5m'] = d1 - d2
    else:
        f['fabstorage_accel_5m'] = 0

    # ──────────────────── 5. 룰 컨텍스트 ────────────────────
    f['rule_ra_count']      = rule_ctx.get('ra_count', 0)
    f['rule_ra_value']      = rule_ctx.get('ra_value') or 0
    f['rule_ra_sustained']  = int(rule_ctx.get('ra_sustained', False))
    f['rule_ra_trig']       = int(rule_ctx.get('ra_trig', False))
    f['rule_rb_diff']       = rule_ctx.get('rb_diff', 0)
    f['rule_rb_diff_10']    = rule_ctx.get('rb_diff_10', 0)
    f['rule_rb_trig']       = int(rule_ctx.get('rb_trig', False))
    f['rule_rb_fast']       = int(rule_ctx.get('rb_fast', False))
    f['rule_rc_trend']      = rule_ctx.get('rc_trend', 0)
    f['rule_rev_count']     = rule_ctx.get('rev_count', 0)
    f['rule_rc_trig']       = int(rule_ctx.get('rc_trig', False))
    f['rule_rd_fabstorage'] = rule_ctx.get('rd_fabstorage', 0)
    f['rule_rd_trig']       = int(rule_ctx.get('rd_trig', False))
    # ★ v3.1 신규 룰 컨텍스트
    f['rule_re_trig']       = int(rule_ctx.get('re_trig', False))
    f['rule_rf_trig']       = int(rule_ctx.get('rf_trig', False))
    f['rule_rf_fast']       = int(rule_ctx.get('rf_fast', False))
    f['rule_inflow_total']  = rule_ctx.get('inflow_total', 0)
    # ★★★ 위험도 점수 — 룰베이스 종합 평가 (강한 ML 피처)
    f['risk_score']         = rule_ctx.get('risk_score', 0)

    # ──────────────────── 6. 조합 (interaction) ────────────────────
    f['1min_x_fabstorage']   = f['1min_now'] * f['fabstorage_now']
    f['1min_x_revcount']     = f['1min_now'] * f['rule_rev_count']
    f['m14_x_fabstorage']    = f['m14_now'] * f['fabstorage_now']
    f['m14b_util_x_fab']     = f['m14b_oht_util'] * f['fabstorage_now']
    f['fab_x_revcount']      = f['fabstorage_now'] * f['rule_rev_count']
    # ★ v3.1 신규 조합
    f['1min_x_inflow']       = f['1min_now'] * f['inflow_total_now']
    f['fab_x_hub_storage']   = f['fabstorage_now'] * (100 - f['hub_storage_util'])  # 저장압박
    f['risk_x_inflow']       = f['risk_score'] * f['inflow_total_now']

    return f


def process_csv(csv_path, out_path):
    """CSV 전체 처리 → 피처 데이터프레임 저장"""
    t1_window  = deque(maxlen=WINDOW_MIN)
    m14_window = deque(maxlen=WINDOW_MIN)
    lft_window = deque(maxlen=WINDOW_MIN)
    v3_window  = deque(maxlen=WINDOW_MIN)

    feature_rows = []

    for t, star, _ in iter_star_rows(csv_path):
        t1_window.append(star.get('avgtotal1min'))
        m14_window.append(star.get('m14_to_m16'))
        lft_window.append(star.get('lft_list') or {})
        v3_window.append({k: star.get(k) for k in (
            'fabstorage_ratio',
            'm14b_aotransdelay', 'm14b_oht_util', 'm14b_4abld122',
            'm14b_avgtotal1min', 'm14b_7f_to_hub', 'm14b_7f_to_hub_alt',
            'm14_htstop', 'm14_congested', 'm14_abnormal',
            'm16pkt_aotransdelay', 'm16wt_aotransdelay',
            # ★ v3.1 신규 5개 컬럼
            'hub_storage_util', 'm14_inflow',
            'm16a_2f_inflow', 'm16a_6f_inflow', 'm16b_10f_inflow',
        )})

        # 윈도우 31개 미만이면 룰 평가 보류
        if len(t1_window) < 31:
            continue

        s1, s2, s3, ctx = evaluate_rules(t1_window, m14_window, lft_window, v3_window)
        features = build_features(t1_window, m14_window, lft_window, v3_window, ctx)
        features['timestamp'] = t.strftime('%Y-%m-%d %H:%M:%S')
        features['_rule_s1'] = int(s1)
        features['_rule_s2'] = int(s2)
        features['_rule_s3'] = int(s3)

        feature_rows.append(features)

    if not feature_rows:
        print('❌ 피처 0건')
        return

    fieldnames = ['timestamp'] + [k for k in feature_rows[0].keys() if k != 'timestamp']
    with open(out_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(feature_rows)

    print(f'✅ {len(feature_rows):,} 행 → {out_path}')


def _resolve_csv_path(user_path):
    """CSV 경로 자동 탐색 — 절대경로/상대경로/여러 위치 시도."""
    if os.path.exists(user_path):
        return os.path.abspath(user_path)

    # 파일명만 추출
    basename = os.path.basename(user_path)
    cwd = os.getcwd()
    this_dir = os.path.dirname(os.path.abspath(__file__))

    # 시도할 위치들
    candidates = [
        user_path,
        os.path.abspath(user_path),
        os.path.join(cwd, basename),
        os.path.join(cwd, 'DATA', basename),
        os.path.join(cwd, '..', 'DATA', basename),
        os.path.join(cwd, '..', '..', 'DATA', basename),
        os.path.join(this_dir, basename),
        os.path.join(this_dir, '..', 'DATA', basename),
        os.path.join(this_dir, 'DATA', basename),
    ]

    # 대소문자 변형도 시도 (윈도우는 대개 무시하지만 명시적으로)
    if not basename.endswith('.csv') and not basename.endswith('.CSV'):
        pass
    else:
        for v in [basename.lower(), basename.upper(),
                  basename.replace('.csv', '.CSV'),
                  basename.replace('.CSV', '.csv')]:
            candidates.append(os.path.join(cwd, v))
            candidates.append(os.path.join(cwd, '..', 'DATA', v))
            candidates.append(os.path.join(cwd, 'DATA', v))

    for c in candidates:
        if os.path.exists(c):
            print(f'✅ CSV 찾음: {c}')
            return os.path.abspath(c)

    # 못 찾았으면 디버그 정보 출력
    print(f'❌ CSV 파일을 찾을 수 없습니다: {user_path}')
    print(f'   현재 폴더: {cwd}')
    print(f'   스크립트 폴더: {this_dir}')
    print(f'\n다음 위치들을 시도했습니다:')
    for c in candidates:
        print(f'   - {os.path.abspath(c)}')
    print(f'\n현재 폴더({cwd}) 내용:')
    try:
        for item in sorted(os.listdir(cwd)):
            full = os.path.join(cwd, item)
            mark = '[D]' if os.path.isdir(full) else '   '
            print(f'   {mark} {item}')
    except Exception as e:
        print(f'   (디렉터리 읽기 실패: {e})')

    parent = os.path.dirname(cwd)
    if os.path.exists(parent):
        print(f'\n상위 폴더({parent}) 내용:')
        try:
            for item in sorted(os.listdir(parent)):
                full = os.path.join(parent, item)
                mark = '[D]' if os.path.isdir(full) else '   '
                print(f'   {mark} {item}')
        except Exception as e:
            print(f'   (디렉터리 읽기 실패: {e})')

    sys.exit(1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--csv', required=True, help='입력 CSV 경로 (자동 탐색 지원)')
    p.add_argument('--out', default='features.csv', help='출력 피처 CSV 경로')
    args = p.parse_args()

    csv_path = _resolve_csv_path(args.csv)
    process_csv(csv_path, args.out)


if __name__ == '__main__':
    main()
