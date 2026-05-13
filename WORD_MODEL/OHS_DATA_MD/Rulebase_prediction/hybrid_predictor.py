#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
하이브리드 예측기 — 룰(S1/S2/S3) × ML(0~1) 양방향 매트릭스 융합

입력:  ../ml/ml_predict/<YYYYMMDD>_predictions.csv  (ml_predict_runner.py 출력)
출력:  ../hybrid_predict/<YYYYMMDD>_hybrid.csv     (날짜별 append, 1분당 1행)

핵심 등급:
    위험-확정 : S3 발동 (이미 늦음, 사후 기록)
    위험-예측 : S2/S1 + ML≥0.85 (★ 사전 알람 — 하이브리드 핵심 가치)
    경보      : S2+ML중간 / 룰OFF+ML강함 / S1+ML중간
    주의      : S2+ML약 / S1+ML약 / 룰OFF+ML중간
    관심      : 단독 약신호
    정상      : 그 외

사용법:
    # 모듈로 (run_ml.py에서 import)
    import hybrid_predictor
    hybrid_predictor.run_watch()

    # 단독 실행
    python hybrid_predictor.py [--input_dir PATH] [--out_dir PATH] [--interval SECONDS]
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path


_HERE = Path(__file__).resolve().parent

# 기본 경로 (run_ml.py에서 override 가능)
DEFAULT_INPUT_DIR  = _HERE.parent / 'ml' / 'ml_predict'
DEFAULT_OUTPUT_DIR = _HERE.parent / 'hybrid_predict'
DEFAULT_INTERVAL   = 60  # 초

# 임계값 (운영 튜닝 포인트)
ML_STRONG = 0.85
ML_MID    = 0.70
ML_LOW    = 0.30


def _rule_level(s1, s2, s3):
    """0=OFF, 1=S1, 2=S2, 3=S3"""
    if int(s3): return 3
    if int(s2): return 2
    if int(s1): return 1
    return 0


def _ml_level(score):
    """0=낮음, 1=중간, 2=높음, 3=강함"""
    if score >= ML_STRONG: return 3
    if score >= ML_MID:    return 2
    if score >= ML_LOW:    return 1
    return 0


def fuse(s1, s2, s3, ml_score):
    """양방향 매트릭스 융합 → (level, agreement, direction, reason)"""
    r = _rule_level(s1, s2, s3)
    m = _ml_level(ml_score)

    # 일치도
    if r > 0 and m > 0:
        agreement = 'both'
    elif r > 0:
        agreement = 'rule_only'
    elif m > 0:
        agreement = 'ml_only'
    else:
        agreement = 'none'

    # 방향 (단일 분 기준 — 시간축 lead-time은 별도 분석)
    if r == 0 and m >= 2:
        direction = 'ml→rule(예측)'
    elif r >= 2 and m == 0:
        direction = 'rule→?(ML미동의)'
    elif r > 0 and m > 0:
        direction = 'sync(양합치)'
    else:
        direction = '-'

    # 등급 (매트릭스)
    if r == 3:
        level = '위험-확정'
        why = f'S3 발동, 이미 사건진행 ml={ml_score:.2f}'
    elif r == 2 and m == 3:
        level = '위험-예측'
        why = f'★ S2+ML강 → 30분내 S3 진행예상 ml={ml_score:.2f}'
    elif r == 1 and m == 3:
        level = '위험-예측'
        why = f'S1+ML강 → 조기 진행신호 ml={ml_score:.2f}'
    elif r == 2 and m == 2:
        level = '경보'
        why = f'S2+ML중 → 위험가능 ml={ml_score:.2f}'
    elif r == 0 and m == 3:
        level = '경보'
        why = f'ML 단독강 → 룰 곧 발동가능 ml={ml_score:.2f}'
    elif r == 1 and m == 2:
        level = '경보'
        why = f'S1+ML중 ml={ml_score:.2f}'
    elif r == 2 and m == 1:
        level = '주의'
        why = f'S2 일반 (ml 약 {ml_score:.2f})'
    elif r == 1 and m == 1:
        level = '주의'
        why = f'S1+ML약 ml={ml_score:.2f}'
    elif r == 0 and m == 2:
        level = '주의'
        why = f'ML 조기경보 중 (룰OFF) ml={ml_score:.2f}'
    elif r == 2 and m == 0:
        level = '관심'
        why = f'S2 단발성 추정 (ml 낮음 {ml_score:.2f})'
    elif r == 1 and m == 0:
        level = '관심'
        why = f'S1 단독 (ml 낮음 {ml_score:.2f})'
    elif r == 0 and m == 1:
        level = '관심'
        why = f'ML 약신호 ml={ml_score:.2f}'
    else:
        level = '정상'
        why = ''

    return level, agreement, direction, why


# CSV 컬럼
OUT_COLUMNS = [
    'datetime', 'prediction_for',
    'ml_score', 'ml_level', 'ml_level_kr',
    'rule_s1', 'rule_s2', 'rule_s3',
    'final_level', 'agreement', 'direction', 'final_reason',
]


def _parse_dt(s):
    try:
        return datetime.strptime(s.strip(), '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None


def _read_csv_rows(path):
    """utf-8-sig → utf-8 → cp949 폴백 (수집기 BOM 대응)"""
    for enc in ('utf-8-sig', 'utf-8', 'cp949'):
        try:
            with open(path, 'r', encoding=enc, newline='') as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f'인코딩 감지 실패: {path}')


def _append_hybrid(out_path, row_dict):
    new_file = (not out_path.exists()) or out_path.stat().st_size == 0
    with open(out_path, 'a', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLUMNS)
        if new_file:
            w.writeheader()
        w.writerow(row_dict)


def _today_str():
    return datetime.now().strftime('%Y%m%d')


def _process_ml_csv(ml_csv, out_csv, last_t, log_fn=None):
    """ml_predict CSV에서 last_t 이후 신규 행만 fuse → hybrid CSV append"""
    if not ml_csv.exists():
        return last_t, 0

    rows = _read_csv_rows(ml_csv)
    written = 0
    new_last_t = last_t

    for row in rows:
        dt = _parse_dt(row.get('datetime', ''))
        if dt is None:
            continue
        if last_t is not None and dt <= last_t:
            continue

        try:
            ml_score = float(row.get('ml_score', 0) or 0)
        except (ValueError, TypeError):
            ml_score = 0.0
        s1 = int(row.get('rule_s1', 0) or 0)
        s2 = int(row.get('rule_s2', 0) or 0)
        s3 = int(row.get('rule_s3', 0) or 0)

        level, agreement, direction, why = fuse(s1, s2, s3, ml_score)

        out_row = {
            'datetime':       row.get('datetime', ''),
            'prediction_for': row.get('prediction_for', ''),
            'ml_score':       f'{ml_score:.4f}',
            'ml_level':       row.get('ml_level', ''),
            'ml_level_kr':    row.get('ml_level_kr', ''),
            'rule_s1':        s1,
            'rule_s2':        s2,
            'rule_s3':        s3,
            'final_level':    level,
            'agreement':      agreement,
            'direction':      direction,
            'final_reason':   why,
        }
        _append_hybrid(out_csv, out_row)
        written += 1
        new_last_t = dt

        # 경보 이상만 콘솔 로그
        if log_fn and level in ('위험-예측', '위험-확정', '경보'):
            log_fn(f'  [{dt.strftime("%H:%M")}] {level} | {agreement} | {direction} | {why}')

    return new_last_t, written


def run_watch(input_dir=None, out_dir=None, interval=DEFAULT_INTERVAL, logger=None):
    """폴링 루프 — run_ml.py에서 데몬 스레드로 호출"""
    input_dir = Path(input_dir) if input_dir else DEFAULT_INPUT_DIR
    out_dir   = Path(out_dir)   if out_dir   else DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    def _log(msg):
        if logger:
            logger.info(msg)
        else:
            print(msg, flush=True)

    _log('🔀 하이브리드 예측기 시작')
    _log(f'   입력: {input_dir}')
    _log(f'   출력: {out_dir}')
    _log(f'   임계값: STRONG={ML_STRONG} MID={ML_MID} LOW={ML_LOW}')
    _log(f'   폴링: {interval}초')

    last_t = None
    last_date = None
    last_size = -1

    while True:
        try:
            today = _today_str()
            ml_csv  = input_dir / f'{today}_predictions.csv'
            out_csv = out_dir   / f'{today}_hybrid.csv'

            # 자정 넘어가면 last_t 리셋
            if last_date is not None and last_date != today:
                _log(f'📅 날짜 변경 ({last_date} → {today}) — 새 hybrid 파일 시작')
                last_t = None
                last_size = -1
            last_date = today

            if ml_csv.exists():
                cur_size = ml_csv.stat().st_size
                if cur_size != last_size:
                    last_t, written = _process_ml_csv(ml_csv, out_csv, last_t, log_fn=_log)
                    if written > 0:
                        _log(f'  💾 hybrid {written}건 → {out_csv.name}')
                    last_size = cur_size
            else:
                _log(f'⚠ 입력 대기: {ml_csv} (ML 예측기 출력 기다리는 중)')

            time.sleep(interval)
        except KeyboardInterrupt:
            _log('🛑 하이브리드 예측기 종료')
            break
        except Exception as e:
            import traceback
            _log(f'⚠ 하이브리드 예측기 오류: {e}\n{traceback.format_exc()}')
            time.sleep(interval)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input_dir', default=str(DEFAULT_INPUT_DIR),
                   help='ml_predict 폴더 (YYYYMMDD_predictions.csv 입력)')
    p.add_argument('--out_dir',   default=str(DEFAULT_OUTPUT_DIR),
                   help='hybrid_predict 폴더 (YYYYMMDD_hybrid.csv 출력)')
    p.add_argument('--interval', type=int, default=DEFAULT_INTERVAL, help='폴링 간격(초)')
    args = p.parse_args()

    run_watch(args.input_dir, args.out_dir, args.interval)


if __name__ == '__main__':
    main()
