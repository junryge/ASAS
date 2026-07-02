#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xgb_비정상_infer — XGBoost 비정상 모델로 매분 정체확률 생성
====================================================================
학습된 XGBoost(xgb_비정상_train) 로 매분 jam_probability 를 뽑아
하이브리드 판정의 '비정상 확인관' 입력으로 사용.

★ 롤링/델타 피처는 학습과 100% 동일하게 생성 (아래 상수/함수 train 과 일치해야 함).
★ 누수 없음: 롤링/델타는 과거만 사용.

입력:
    --features  features.csv
    --model     out_ml/xgb (model.json + feature_cols.json)
    --out       기본 ./out_ml/jam_prob.csv

실행:
    python xgb_비정상_infer.py --features ./out_ml/features.csv --model ./out_ml/xgb

출력:
    jam_prob.csv — datetime, jam_probability[0~1], jam_level
    jam_level: 안전<0.3 / 관심 / 경계0.5~ / 정체≥0.7
"""
import argparse
import csv
import json
import os
import sys

# ★ train 과 반드시 동일
ROLL_WINS = [15, 30]
DELTA_LAGS = [15, 30]


def _need():
    try:
        import numpy, pandas, xgboost  # noqa
        return True
    except Exception as e:
        print("⚠️ XGBoost 라이브러리 없음 — pip install xgboost pandas numpy")
        print(f"   ({type(e).__name__}: {e})")
        return False


def build_features(feat_df, base_cols):
    import pandas as pd
    df = feat_df.sort_values('datetime').reset_index(drop=True)
    df[base_cols] = df[base_cols].ffill().fillna(0.0)
    new = {}
    for c in base_cols:
        s = df[c].astype(float)
        for w in ROLL_WINS:
            new[f'{c}__rmean{w}'] = s.rolling(w, min_periods=1).mean()
            new[f'{c}__rstd{w}'] = s.rolling(w, min_periods=1).std().fillna(0.0)
        for lag in DELTA_LAGS:
            new[f'{c}__d{lag}'] = s - s.shift(lag).fillna(s.iloc[0])
    df = pd.concat([df, pd.DataFrame(new, index=df.index)], axis=1)
    return df


def level(p):
    return '정체' if p >= 0.7 else '경계' if p >= 0.5 else '관심' if p >= 0.3 else '안전'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', required=True)
    ap.add_argument('--model', default='./out_ml/xgb')
    ap.add_argument('--out', default='./out_ml/jam_prob.csv')
    a = ap.parse_args()

    print("=" * 60)
    print("XGBoost 비정상 추론 — 매분 정체확률")
    print("=" * 60)
    if not _need():
        sys.exit(2)

    import pandas as pd
    import xgboost as xgb

    feat_cols = json.load(open(os.path.join(a.model, 'feature_cols.json'), encoding='utf-8'))
    model = xgb.XGBClassifier()
    model.load_model(os.path.join(a.model, 'model.json'))

    feat = pd.read_csv(a.features, encoding='utf-8-sig')
    feat['datetime'] = pd.to_datetime(feat['datetime'])
    base_cols = [c for c in feat.columns if c != 'datetime']
    df = build_features(feat, base_cols)

    missing = [c for c in feat_cols if c not in df.columns]
    if missing:
        print(f"⚠️ 피처 불일치 {len(missing)}개 (train/infer 상수 확인): {missing[:5]}...")
        sys.exit(3)
    p = model.predict_proba(df[feat_cols].values)[:, 1]

    with open(a.out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['datetime', 'jam_probability', 'jam_level'])
        for t, prob in zip(df['datetime'], p):
            w.writerow([t.strftime('%Y-%m-%d %H:%M'), f'{prob:.4f}', level(float(prob))])

    hi = int((p >= 0.7).sum())
    print(f"[완료] {len(p)}분 정체확률 (정체≥0.7 {hi}분, {hi/len(p)*100:.1f}%) → {a.out}")
    print("다음: 하이브리드_판정.py 에서 룰·정상TSPulse·이 확률 종합")


if __name__ == '__main__':
    main()
