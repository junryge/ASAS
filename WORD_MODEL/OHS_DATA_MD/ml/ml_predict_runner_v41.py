#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML 실시간 예측기 v4.1 — 3개 모델 (15/30/60분) 동시 추론 + Logpresso 적재

v3 ml_predict_runner.py 와 차이:
  - v3: feature_builder.py + 단일 모델 (model.json)
  - v4.1: feature_builder_v41.py + 3 lead time 모델 (model_v41_15m/30m/60m.json)
  - v4.1: 입력 = raw CSV + 발동이벤트.csv join (룰 컨텍스트 포함)
  - v4.1: 출력 + Logpresso 적재 (ML_LO 모듈, test_table4)

입력:
  - predict/M16A_HUBROOM_PR.csv (수집기, 90분 윈도우)
  - predict_tobe/{YYYYMMDD}_발동이벤트.csv (룰베이스 v4.1, 같은 분)

출력:
  - ml_predict/{YYYYMMDD}_predictions.csv (날짜별 append, 1분 1행)
  - Logpresso test_table4 (ML_LO 통해)

출력 헤더:
  datetime, prediction_for_15m, prediction_for_30m, prediction_for_60m,
  ml_score_15m, ml_score_30m, ml_score_60m,
  ml_level_15m, ml_level_30m, ml_level_60m

사용:
    import ml_predict_runner_v41 as ml_runner
    ml_runner.run_watch()

    # 또는 CLI
    python ml_predict_runner_v41.py --input predict/M16A_HUBROOM_PR.csv \\
        --events_dir ../Rulebase_prediction/predict_tobe \\
        --out_dir ml_predict \\
        --model_15m model_v41_15m.json \\
        --model_30m model_v41_30m.json \\
        --model_60m model_v41_60m.json
"""

import argparse
import csv
import os
import sys
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

# v4.1 피처 빌더 (raw + 발동이벤트 join)
from feature_builder_v41 import (
    build_features_row, iter_raw_rows, load_events_dict,
    KEY_NUMERIC_COLS, EVENT_NUMERIC_COLS, WINDOW_MIN,
    _safe_float,
)
from ml_predictor import MLPredictor


# ============================================================
# 기본 경로 (run_ml.py 에서 override 가능)
# ============================================================
BASE_DIR = _HERE.parent / 'Rulebase_prediction'  # ml/ 와 같은 레벨

DEFAULT_INPUT_CSV   = BASE_DIR / 'predict' / 'M16A_HUBROOM_PR.csv'
DEFAULT_EVENTS_DIR  = BASE_DIR / 'predict_tobe'
DEFAULT_OUTPUT_DIR  = _HERE / 'ml_predict'
DEFAULT_MODEL_15M   = _HERE / 'model_v41_15m.json'
DEFAULT_MODEL_30M   = _HERE / 'model_v41_30m.json'
DEFAULT_MODEL_60M   = _HERE / 'model_v41_60m.json'
DEFAULT_INTERVAL    = 60
SYNC_OFFSET_SEC     = 10   # 룰베이스(05초) 다음 5초


# ============================================================
# 출력 헤더
# ============================================================
OUT_HEADER = [
    'datetime',
    'prediction_for_15m', 'prediction_for_30m', 'prediction_for_60m',
    'ml_score_15m', 'ml_score_30m', 'ml_score_60m',
    'ml_level_15m', 'ml_level_30m', 'ml_level_60m',
]


# ============================================================
# 모델 로드 (3개)
# ============================================================
class TripleModel:
    """3 lead time 모델 묶음 (15m/30m/60m)."""

    def __init__(self, paths):
        """paths = {'15m': Path, '30m': Path, '60m': Path}"""
        self.models = {}
        for lead, p in paths.items():
            if not os.path.exists(p):
                print(f'⚠ 모델 없음: {p} → {lead} 비활성')
                self.models[lead] = None
                continue
            try:
                self.models[lead] = MLPredictor(str(p))
                print(f'✅ {lead} 모델 로드: {p}')
            except Exception as e:
                print(f'❌ {lead} 모델 로드 실패: {e}')
                self.models[lead] = None

    def predict(self, feat_dict):
        """피처 → {15m: score, 30m: score, 60m: score} (없는 모델은 None)."""
        out = {}
        for lead, m in self.models.items():
            if m is None:
                out[lead] = None
            else:
                try:
                    out[lead] = float(m.predict(feat_dict))
                except Exception as e:
                    print(f'  {lead} 예측 오류: {e}')
                    out[lead] = None
        return out

    def levels(self, scores):
        """score → level. v3 ml_predictor.level() 호출."""
        out = {}
        for lead, s in scores.items():
            if s is None or self.models.get(lead) is None:
                out[lead] = ''
            else:
                try:
                    out[lead] = self.models[lead].level(s)
                except Exception:
                    out[lead] = ''
        return out


# ============================================================
# 단일 예측 사이클 (매분 호출)
# ============================================================
def predict_one(input_csv, events_dir, triple_model, sliding_state, last_t,
                logger=None):
    """raw CSV 전체 읽고 sliding_state 갱신 → 마지막 분 예측.

    반환: (new_last_t, prediction_row dict or None)
    """
    if not os.path.exists(input_csv):
        if logger:
            logger(f'⚠ 입력 CSV 없음: {input_csv}')
        return last_t, None

    # raw CSV 전체 순회 (90분 윈도우)
    latest_t = None
    latest_raw = None
    for t, raw_row in iter_raw_rows(str(input_csv)):
        # sliding_state 누적
        for col in KEY_NUMERIC_COLS:
            sliding_state[col].append(_safe_float(raw_row.get(col), default=None))
        latest_t = t
        latest_raw = raw_row

    if latest_t is None or latest_raw is None:
        if logger:
            logger('⚠ raw CSV 행 0')
        return last_t, None

    # 같은 분 중복 처리 방지
    if last_t is not None and latest_t <= last_t:
        return last_t, None

    # 30분 워밍업
    if len(sliding_state[KEY_NUMERIC_COLS[0]]) < 31:
        if logger:
            logger(f'  워밍업 ({len(sliding_state[KEY_NUMERIC_COLS[0]])}/31)')
        return latest_t, None

    # 발동이벤트.csv 같은 분 찾기 (날짜별 파일)
    ymd = latest_t.strftime('%Y%m%d')
    event_csv = Path(events_dir) / f'{ymd}_발동이벤트.csv'
    event_row = None
    if event_csv.exists():
        # 마지막 분만 lookup (효율: 파일 끝쪽 우선)
        target_str = latest_t.strftime('%Y-%m-%d %H:%M')
        try:
            with open(event_csv, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    dt = (row.get('datetime') or '').strip()
                    if dt == target_str or dt.startswith(target_str):
                        event_row = row
                        # 같은 분이 여러 개여도 마지막 것 사용 (덮어쓰기)
        except Exception as e:
            if logger:
                logger(f'  발동이벤트 읽기 오류: {e}')

    # 피처 추출
    feat = build_features_row(latest_t, latest_raw, event_row, sliding_state)
    # timestamp 제거 (모델 입력은 timestamp 빼고)
    feat_for_model = {k: v for k, v in feat.items() if k != 'timestamp'}

    # 3 모델 예측
    scores = triple_model.predict(feat_for_model)
    levels = triple_model.levels(scores)

    # 출력 행
    pred_15 = (latest_t + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
    pred_30 = (latest_t + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
    pred_60 = (latest_t + timedelta(minutes=60)).strftime('%Y-%m-%d %H:%M:%S')

    row = {
        'datetime': latest_t.strftime('%Y-%m-%d %H:%M:%S'),
        'prediction_for_15m': pred_15,
        'prediction_for_30m': pred_30,
        'prediction_for_60m': pred_60,
        'ml_score_15m': f'{scores["15m"]:.4f}' if scores["15m"] is not None else '',
        'ml_score_30m': f'{scores["30m"]:.4f}' if scores["30m"] is not None else '',
        'ml_score_60m': f'{scores["60m"]:.4f}' if scores["60m"] is not None else '',
        'ml_level_15m': levels.get('15m', ''),
        'ml_level_30m': levels.get('30m', ''),
        'ml_level_60m': levels.get('60m', ''),
    }
    return latest_t, row


# ============================================================
# CSV append (날짜별 자동 분할)
# ============================================================
def append_pred_row(out_dir, row):
    ymd = row['datetime'][:10].replace('-', '')
    path = Path(out_dir) / f'{ymd}_predictions.csv'
    new_file = not path.exists() or path.stat().st_size == 0
    with open(path, 'a', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=OUT_HEADER)
        if new_file:
            writer.writeheader()
        writer.writerow(row)
    return path


# ============================================================
# 동기 sleep
# ============================================================
def sleep_until_next_minute(offset_sec=SYNC_OFFSET_SEC):
    now = time.time()
    sec = now % 60
    wait = (60 - sec) + offset_sec
    if wait > 60:
        wait -= 60
    if wait < 0.05:
        wait += 60
    time.sleep(wait)


# ============================================================
# 외부 API — run_watch
# ============================================================
def run_watch(input_csv=None, events_dir=None, out_dir=None,
              model_15m=None, model_30m=None, model_60m=None,
              interval=DEFAULT_INTERVAL):
    """매분 동기 ML 추론. run_ml.py 의 스레드 진입점."""
    input_csv = Path(input_csv or DEFAULT_INPUT_CSV)
    events_dir = Path(events_dir or DEFAULT_EVENTS_DIR)
    out_dir = Path(out_dir or DEFAULT_OUTPUT_DIR)
    model_15m = Path(model_15m or DEFAULT_MODEL_15M)
    model_30m = Path(model_30m or DEFAULT_MODEL_30M)
    model_60m = Path(model_60m or DEFAULT_MODEL_60M)

    out_dir.mkdir(parents=True, exist_ok=True)

    def _log(msg):
        ts = datetime.now().strftime('%H:%M:%S')
        print(f'[ML_v41 {ts}] {msg}')

    _log('=' * 60)
    _log('🤖 ML 예측기 v4.1 시작')
    _log(f'  입력: {input_csv}')
    _log(f'  발동이벤트: {events_dir}')
    _log(f'  출력: {out_dir}')
    _log(f'  모델 15m: {model_15m}')
    _log(f'  모델 30m: {model_30m}')
    _log(f'  모델 60m: {model_60m}')
    _log('=' * 60)

    # 모델 로드
    triple = TripleModel({
        '15m': model_15m,
        '30m': model_30m,
        '60m': model_60m,
    })
    if all(m is None for m in triple.models.values()):
        _log('❌ 모든 모델 로드 실패 — 종료')
        return

    # Logpresso 적재 시작 (선택 — 없으면 자동 스킵)
    try:
        sys.path.insert(0, str(BASE_DIR))
        import ML_LO
        ML_LO.start()
        _log('✅ ML_LO 활성화')
    except Exception as e:
        _log(f'⚠ ML_LO 로드 실패 (CSV 적재만): {e}')
        ML_LO = None

    # sliding state 초기화
    sliding_state = {col: deque(maxlen=WINDOW_MIN) for col in KEY_NUMERIC_COLS}
    last_t = None

    _log('[INIT] 첫 사이클 시작...')

    try:
        while True:
            cycle_start = time.time()
            try:
                last_t, row = predict_one(
                    str(input_csv), str(events_dir), triple,
                    sliding_state, last_t, logger=_log
                )
                if row is not None:
                    path = append_pred_row(out_dir, row)
                    if ML_LO is not None:
                        ML_LO.upload(OUT_HEADER, [row[k] for k in OUT_HEADER])
                    _log(f'  ✅ {row["datetime"]} score30m={row["ml_score_30m"]} → {path.name}')
            except Exception as e:
                _log(f'  ❌ 사이클 오류: {type(e).__name__}: {e}')

            elapsed = time.time() - cycle_start
            _log(f'  cycle {elapsed:.2f}s')
            sleep_until_next_minute(SYNC_OFFSET_SEC)

    except KeyboardInterrupt:
        _log('사용자 중단 (Ctrl+C)')
        if ML_LO is not None:
            try:
                ML_LO.stop()
            except Exception:
                pass


# ============================================================
# CLI
# ============================================================
def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', default=str(DEFAULT_INPUT_CSV))
    p.add_argument('--events_dir', default=str(DEFAULT_EVENTS_DIR))
    p.add_argument('--out_dir', default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument('--model_15m', default=str(DEFAULT_MODEL_15M))
    p.add_argument('--model_30m', default=str(DEFAULT_MODEL_30M))
    p.add_argument('--model_60m', default=str(DEFAULT_MODEL_60M))
    p.add_argument('--interval', type=int, default=DEFAULT_INTERVAL)
    args = p.parse_args()

    run_watch(
        input_csv=args.input,
        events_dir=args.events_dir,
        out_dir=args.out_dir,
        model_15m=args.model_15m,
        model_30m=args.model_30m,
        model_60m=args.model_60m,
        interval=args.interval,
    )


if __name__ == '__main__':
    main()
