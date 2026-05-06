#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
🚀 실시간 예측 시스템 - V10.4 (XGB 회귀 + LGBM 분류 + 투표)
   8.3.1 데이터 방식 + 10.4 모델 아키텍처 + UI 급증/상태 로직
   시퀀스: 280분, 예측: 10분 후
================================================================================
"""

import os
import pickle
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

# ============================================================================
# 설정
# ============================================================================
CONFIG = {
    'model_file': 'models/v10_4_m14_model.pkl',
    'csv_file': 'data/2025_DATA.CSV',
    'sequence_length': 280,
    'prediction_offset': 10,
    'limit_value': 1700,
    'target_column': 'TOTALCNT',
}

# ============================================================================
# 급증 분석 컬럼 (UI main.py 동일)
# ============================================================================
ANALYSIS_COLS = [
    'M14AM10A', 'M10AM14A', 'M14AM10ASUM',
    'M14AM14B', 'M14BM14A', 'M14AM14BSUM',
    'M14AM16', 'M16M14A', 'M14AM16SUM',
    'M14.QUE.ALL.CURRENTQCREATED',
    'M14.QUE.ALL.CURRENTQCOMPLETED',
    'M14.QUE.OHT.OHTUTIL',
    'M14.QUE.ALL.TRANSPORT4MINOVERCNT',
    'M14B.QUE.SENDFAB.VERTICALQUEUECOUNT',
]

# 임계값이 다른 컬럼 (warning=60, danger=70)
THRESHOLD_60_COLS = [
    'M14.QUE.ALL.CURRENTQCREATED',
    'M14.QUE.ALL.CURRENTQCOMPLETED',
]

# ============================================================================
# Feature 생성 함수 (10.4 평가 방식)
# ============================================================================
def create_sequence_features(df, feature_cols, seq_len, idx, limit_val=1700):
    """시퀀스 피처 생성 - 10.4 평가와 동일"""
    features = []
    for col in feature_cols:
        seq = df[col].iloc[idx - seq_len:idx].values
        current_val = seq[-1]
        features.extend([
            np.mean(seq), np.std(seq), np.min(seq), np.max(seq), current_val,
            seq[-1] - seq[0],
            np.percentile(seq, 25), np.percentile(seq, 75),
            np.mean(seq[-10:]) - np.mean(seq[:10]),
            np.max(seq[-30:]) if len(seq) >= 30 else np.max(seq),
            seq[-1] - seq[-10] if len(seq) >= 10 else 0,
            seq[-1] - seq[-30] if len(seq) >= 30 else 0,
            seq[-1] - seq[-60] if len(seq) >= 60 else 0,
            (seq[-1] - seq[-10]) / 10 if len(seq) >= 10 else 0,
            (seq[-1] - seq[-30]) / 30 if len(seq) >= 30 else 0,
            np.max(seq[-10:]) - np.min(seq[-10:]) if len(seq) >= 10 else 0,
            np.max(seq[-30:]) - np.min(seq[-30:]) if len(seq) >= 30 else 0,
            limit_val - current_val,
            1 if current_val >= 1500 else 0,
            1 if current_val >= 1600 else 0,
        ])
    return features

# ============================================================================
# 급증 컬럼 분석 (UI main.py 동일)
# ============================================================================
def analyze_spike_columns(df):
    """
    최근 10분 대비 급증 컬럼 분석
    Returns: spike_columns, warning_count, danger_count
    """
    spike_columns = []
    warning_count = 0
    danger_count = 0

    if len(df) < 11:
        return spike_columns, warning_count, danger_count

    current_row = df.iloc[-1]
    prev_row = df.iloc[-11]  # 10분 전

    for col in ANALYSIS_COLS:
        if col not in df.columns:
            continue

        curr_val = current_row.get(col, 0)
        prev_val = prev_row.get(col, 0)

        if pd.notna(curr_val) and pd.notna(prev_val):
            change = float(curr_val) - float(prev_val)

            # 컬럼별 임계값
            if col in THRESHOLD_60_COLS:
                warn_threshold, danger_threshold = 60, 70
            else:
                warn_threshold, danger_threshold = 50, 60

            if change >= warn_threshold:
                level = 'danger' if change >= danger_threshold else 'warning'
                spike_columns.append({
                    'column': col,
                    'change': int(change),
                    'current': int(curr_val),
                    'previous': int(prev_val),
                    'level': level,
                })
                if level == 'danger':
                    danger_count += 1
                else:
                    warning_count += 1

    # 변화량 기준 정렬
    spike_columns.sort(key=lambda x: x['change'], reverse=True)

    return spike_columns, warning_count, danger_count

# ============================================================================
# 기존 상태 판정 (10.4평가 방식 - 투표 + 규칙 기반)
# ============================================================================
def get_status_v10_4(final_pred_danger, ensemble_pred, vote_sum, total_votes, prob_lgb_important, current_total):
    """
    V10.4 투표/규칙 기반 상태 판정
    - CRITICAL: 최종판정 위험(1) = 투표+규칙으로 1700+ 돌파 예측
    - CAUTION: 위험은 아니지만 앙상블 예측 1600+ 또는 투표 2+
    - NORMAL: 일반 상태
    - LOW: 낮은 상태
    """
    if final_pred_danger == 1:
        return 'CRITICAL'
    elif ensemble_pred >= 1600 or (current_total >= 1500 and vote_sum >= 2):
        return 'CAUTION'
    elif ensemble_pred >= 900:
        return 'NORMAL'
    else:
        return 'LOW'

# ============================================================================
# 상태 판정 (UI main.py 로직 - 10분 예측만)
# ============================================================================
def get_status_with_spike(current_total, predict_10_val, danger_count):
    """
    UI 상태 판정 로직 (관찰/병목예상/위험예상/양호예상 + 예측 기반)
    30분 예측 없이 10분 예측만 사용
    한글 + 영문 둘 다 반환
    """
    # 1단계: 현재값 + 급증 기반 상태
    if current_total >= 1650 and danger_count >= 3:
        status_kr = '병목예상'
        status_en = 'BOTTLENECK_EXPECTED'
    elif current_total >= 1550 and danger_count >= 2:
        status_kr = '위험예상'
        status_en = 'DANGER_EXPECTED'
    elif current_total < 1550 and danger_count >= 2:
        status_kr = '관찰'
        status_en = 'OBSERVATION'
    else:
        status_kr = '양호예상'
        status_en = 'NORMAL'

    # 2단계: 양호예상일 때 예측값 추가 체크 (10분만)
    if status_kr == '양호예상':
        if predict_10_val >= 1700:
            status_kr = '병목(1700예측-10분)'
            status_en = 'BOTTLENECK(1700_PREDICT-10min)'
        elif predict_10_val >= 1650:
            status_kr = '병목예상'
            status_en = 'BOTTLENECK_EXPECTED'

    return status_kr, status_en

# ============================================================================
# 실시간 예측 함수
# ============================================================================
def predict_latest():
    """
    가장 최근 280분 데이터로 10분 후 예측
    V10.4 모델 (XGB 회귀 + LGBM 분류 + 투표) + UI 급증/상태 로직
    """

    # 1. 모델 로드
    model_file = CONFIG['model_file']

    try:
        with open(model_file, 'rb') as f:
            model_data = pickle.load(f)
    except Exception as e:
        print(f"❌ Model file error: {e}")
        return {
            'prediction': 0,
            'status': 'Model operation failure',
            'prediction_time': '',
            'danger_probability': 0,
            'spike_info': '',
            'danger_count': 0,
            'warning_count': 0,
            'error_message': f'No model file: {model_file}'
        }

    models = model_data['models']
    scalers = model_data['scalers']
    FEATURE_GROUPS = model_data['feature_groups']

    # 2. CSV 파일 확인
    csv_file = CONFIG['csv_file']
    if not os.path.exists(csv_file):
        print(f"❌ No CSV file: {csv_file}")
        return {
            'prediction': 0,
            'status': 'No data',
            'prediction_time': '',
            'danger_probability': 0,
            'spike_info': '',
            'danger_count': 0,
            'warning_count': 0,
            'error_message': f'No data: {csv_file}'
        }

    # 3. 데이터 로드
    try:
        df = pd.read_csv(csv_file, on_bad_lines='skip', dtype={'CURRTIME': str})
    except Exception as e:
        print(f"❌ Data Load Error: {e}")
        return {
            'prediction': 0,
            'status': 'No data',
            'prediction_time': '',
            'danger_probability': 0,
            'spike_info': '',
            'danger_count': 0,
            'warning_count': 0,
            'error_message': f'Failed to load data: {e}'
        }

    # 4. 데이터가 비어있는 경우
    if len(df) == 0:
        print(f"❌ No data: CSV file empty")
        return {
            'prediction': 0,
            'status': 'No data',
            'prediction_time': '',
            'danger_probability': 0,
            'spike_info': '',
            'danger_count': 0,
            'warning_count': 0,
            'error_message': 'CSV file is empty'
        }

    # 5. CURRTIME 파싱
    if 'CURRTIME' in df.columns:
        try:
            df['CURRTIME'] = df['CURRTIME'].astype(str).str.strip()
            df = df[df['CURRTIME'].str.len() == 12].copy()
            if len(df) == 0:
                raise ValueError("유효한 CURRTIME 없음")
            df['CURRTIME'] = pd.to_datetime(df['CURRTIME'], format='%Y%m%d%H%M', errors='coerce')
            df = df.dropna(subset=['CURRTIME']).sort_values('CURRTIME').reset_index(drop=True)
        except Exception as e:
            base_time = datetime.now()
            df['CURRTIME'] = [base_time - timedelta(minutes=len(df)-1-i) for i in range(len(df))]
    else:
        base_time = datetime.now()
        df['CURRTIME'] = [base_time - timedelta(minutes=len(df)-1-i) for i in range(len(df))]

    # 6. QUEUE_GAP 파생 변수 생성
    if 'M14.QUE.ALL.CURRENTQCREATED' in df.columns and 'M14.QUE.ALL.CURRENTQCOMPLETED' in df.columns:
        df['QUEUE_GAP'] = df['M14.QUE.ALL.CURRENTQCREATED'] - df['M14.QUE.ALL.CURRENTQCOMPLETED']

    # 7. 없는 컬럼 0으로 처리 (10.4실시간 방식) - 모델 피처 + 급증 분석 컬럼
    all_cols = []
    for group in FEATURE_GROUPS.values():
        all_cols.extend(group)
    # 급증 분석 컬럼도 추가
    all_cols.extend(ANALYSIS_COLS)
    for col in list(set(all_cols)):
        if col not in df.columns:
            print(f"  ⚠ 컬럼 없음 → 0으로 생성: {col}")
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 8. 데이터 부족 체크
    seq_len = CONFIG['sequence_length']
    if len(df) < seq_len:
        print(f"❌ Lack of data: {len(df)}EA (Minimum {seq_len} EA pieces)")
        return {
            'prediction': 0,
            'status': 'Lack of data',
            'prediction_time': '',
            'danger_probability': 0,
            'spike_info': '',
            'danger_count': 0,
            'warning_count': 0,
            'error_message': f'Lack of data: {len(df)}EA (Minimum {seq_len} EA pieces)'
        }

    # 9. Feature 추출 및 예측
    try:
        limit_val = CONFIG['limit_value']
        idx = len(df)  # 마지막 인덱스 + 1

        # 시간 정보
        current_time = df['CURRTIME'].iloc[-1]
        if pd.isna(current_time):
            current_time = datetime.now()
        prediction_time = current_time + timedelta(minutes=CONFIG['prediction_offset'])

        # 현재 TOTALCNT
        current_total = float(df['TOTALCNT'].iloc[-1]) if 'TOTALCNT' in df.columns else 0

        # ============================================
        # 급증 컬럼 분석 (UI 로직)
        # ============================================
        spike_columns, warning_count, danger_count = analyze_spike_columns(df)

        # spike_info 문자열 생성
        spike_info_parts = []
        for s in spike_columns:
            level_tag = 'D' if s['level'] == 'danger' else 'W'
            spike_info_parts.append(f"{level_tag}:{s['column']} +{s['change']}")
        spike_info = ', '.join(spike_info_parts) if spike_info_parts else '없음'

        # Feature 생성 (10.4 평가와 동일)
        feat_target = create_sequence_features(df, FEATURE_GROUPS['target'], seq_len, idx, limit_val)
        feat_important = create_sequence_features(df, FEATURE_GROUPS['important'], seq_len, idx, limit_val)
        feat_auxiliary = create_sequence_features(df, FEATURE_GROUPS['auxiliary'], seq_len, idx, limit_val)

        # 스케일링
        X_target = scalers['target'].transform([feat_target])
        X_important = scalers['important'].transform([feat_important])
        X_auxiliary = scalers['auxiliary'].transform([feat_auxiliary])

        # XGBoost 회귀 예측
        pred_xgb_target = models['xgb_target'].predict(X_target)[0]
        pred_xgb_important = models['xgb_important'].predict(X_important)[0]
        pred_xgb_auxiliary = models['xgb_auxiliary'].predict(X_auxiliary)[0]

        # LightGBM 분류 예측
        pred_lgb_target = models['lgb_target'].predict(X_target)[0]
        pred_lgb_important = models['lgb_important'].predict(X_important)[0]
        pred_lgb_auxiliary = models['lgb_auxiliary'].predict(X_auxiliary)[0]

        # 확률
        prob_lgb_target = models['lgb_target'].predict_proba(X_target)[0][1]
        prob_lgb_important = models['lgb_important'].predict_proba(X_important)[0][1]
        prob_lgb_auxiliary = models['lgb_auxiliary'].predict_proba(X_auxiliary)[0][1]

        # PDT 모델 (있으면)
        pred_xgb_pdt = None
        pred_lgb_pdt = None
        prob_lgb_pdt = None
        if 'xgb_pdt_new' in models and 'pdt_new' in scalers:
            feat_pdt = create_sequence_features(df, FEATURE_GROUPS.get('pdt_new', []), seq_len, idx, limit_val)
            if feat_pdt:
                X_pdt = scalers['pdt_new'].transform([feat_pdt])
                pred_xgb_pdt = models['xgb_pdt_new'].predict(X_pdt)[0]
                pred_lgb_pdt = models['lgb_pdt_new'].predict(X_pdt)[0]
                prob_lgb_pdt = models['lgb_pdt_new'].predict_proba(X_pdt)[0][1]

        # ============================================
        # 투표 (V10.3 방식)
        # ============================================
        votes = [
            1 if pred_xgb_target >= limit_val else 0,
            1 if pred_xgb_important >= limit_val else 0,
            1 if pred_xgb_auxiliary >= limit_val else 0,
            pred_lgb_target,
            pred_lgb_important,
            pred_lgb_auxiliary,
        ]

        if pred_xgb_pdt is not None:
            votes.append(1 if pred_xgb_pdt >= limit_val else 0)
            votes.append(pred_lgb_pdt)

        vote_sum = sum(votes)
        total_votes = len(votes)

        # ============================================
        # 최종 판정 규칙 (V10.3 방식)
        # ============================================
        rule1 = vote_sum >= 3
        rule2 = (prob_lgb_important >= 0.50) and (current_total >= 1450)
        rule3 = (pred_xgb_important >= 1680) and (current_total >= 1500)
        rule4 = (current_total >= 1600) and (vote_sum >= 2)
        rule5 = (pred_xgb_important >= 1700)

        final_pred_danger = 1 if (rule1 or rule2 or rule3 or rule4 or rule5) else 0

        # 앙상블 평균 (회귀값)
        if pred_xgb_pdt is not None:
            ensemble_pred = (pred_xgb_target + pred_xgb_important + pred_xgb_auxiliary + pred_xgb_pdt) / 4
        else:
            ensemble_pred = (pred_xgb_target + pred_xgb_important + pred_xgb_auxiliary) / 3

        # ============================================
        # 기존 상태 판정 (10.4평가 방식 - 투표 + 규칙 기반)
        # ============================================
        base_status = get_status_v10_4(final_pred_danger, ensemble_pred, vote_sum, total_votes, prob_lgb_important, current_total)

        # ============================================
        # 상태 판정 (UI 급증 로직 - 10분 예측만)
        # ============================================
        pred_status_kr, pred_status_en = get_status_with_spike(current_total, ensemble_pred, danger_count)

        # ============================================
        # 1700+ 위험 확률 계산 (투표 + 확률 기반)
        # ============================================
        danger_prob = 0

        # 기본: 앙상블 예측값 기반
        if ensemble_pred >= 1750:
            danger_prob = 100
        elif ensemble_pred >= 1700:
            danger_prob = 95
        elif ensemble_pred >= 1680:
            danger_prob = 75
        elif ensemble_pred >= 1650:
            danger_prob = 50
        elif ensemble_pred >= 1620:
            danger_prob = 30
        elif ensemble_pred >= 1600:
            danger_prob = 15
        else:
            danger_prob = 5

        # 투표 보정
        vote_ratio = vote_sum / total_votes
        if vote_ratio >= 0.75:
            danger_prob = min(100, danger_prob + 25)
        elif vote_ratio >= 0.50:
            danger_prob = min(100, danger_prob + 15)
        elif vote_ratio >= 0.30:
            danger_prob = min(100, danger_prob + 5)

        # LGBM 확률 보정
        if prob_lgb_important >= 0.80:
            danger_prob = min(100, danger_prob + 20)
        elif prob_lgb_important >= 0.60:
            danger_prob = min(100, danger_prob + 15)
        elif prob_lgb_important >= 0.50:
            danger_prob = min(100, danger_prob + 10)

        # 최종 판정이 위험이면 최소 80%
        if final_pred_danger == 1:
            danger_prob = max(danger_prob, 80)

        # 현재값 보정
        if current_total >= 1700:
            danger_prob = max(danger_prob, 85)
        elif current_total >= 1650:
            danger_prob = max(danger_prob, 60)
        elif current_total >= 1600:
            danger_prob = max(danger_prob, 30)

        # 급증 상태(status) 보정
        if pred_status_en == 'BOTTLENECK(1700_PREDICT-10min)':
            danger_prob = max(danger_prob, 90)
        elif pred_status_en == 'BOTTLENECK_EXPECTED':
            danger_prob = max(danger_prob, 70)
        elif pred_status_en == 'DANGER_EXPECTED':
            danger_prob = max(danger_prob, 55)
        elif pred_status_en == 'OBSERVATION':
            danger_prob = max(danger_prob, 30)

        danger_prob = max(0, min(100, danger_prob))

        # 정상 결과 반환
        result = {
            'prediction': int(round(ensemble_pred)),
            'status': base_status,
            'status_Th': pred_status_en,
            'prediction_time': prediction_time.strftime('%Y-%m-%d %H:%M'),
            'danger_probability': danger_prob,
            'spike_info': spike_info,
            'danger_count': danger_count,
            'warning_count': warning_count,
        }

        return result

    except Exception as e:
        print(f"❌ Predictive execution error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'prediction': 0,
            'status': 'Model operation failure',
            'prediction_time': '',
            'danger_probability': 0,
            'spike_info': '',
            'danger_count': 0,
            'warning_count': 0,
            'error_message': f'Model operation failure: {e}'
        }


if __name__ == '__main__':
    result = predict_latest()

    if result is not None:
        print(f"prediction: {result['prediction']:,}")
        print(f"status: {result['status']}")
        print(f"status_Th: {result['status_Th']}")
        print(f"prediction_time: {result['prediction_time']}")
        print(f"1700+ danger_probability: {result['danger_probability']}%")
        print(f"spike_info: {result['spike_info']}")
        print(f"danger_count: {result['danger_count']}, warning_count: {result['warning_count']}")
