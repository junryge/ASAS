#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xgb_비정상_train — XGBoost 비정상(정체) 판별 모델 (비정상 TSPulse 백업)
====================================================================
하이브리드 판정의 '비정상 확인관'을 XGBoost 로 구현.
비정상 TSPulse 가 정체 데이터 파편화(56건·종류 제각각)로 잘 안 될 때의 백업.

★ 판별(discriminative) 방식: 정체 vs 정상 '경계'만 학습 → 적은·파편 데이터에 강함.
★ 라벨 = 메신저 정체 30분전 윈도우 (y_pre30) → 30분 사전예측 목표와 일치.
★ XGBoost 는 시계열 네이티브 아님 → 롤링/델타 피처를 만들어 넣음 (누수 없이 과거만).

전제(회사 PC): pip install xgboost pandas numpy scikit-learn   (torch 불필요 = 경량)

입력:
    --features  features.csv (features_31.py 산출: datetime + 31피처)
    --labels    labels.csv   (labels_채점지.py 산출: y_pre30, is_normal)
    --out       모델/리포트 폴더 (기본 ./out_ml/xgb)

실행:
    python xgb_비정상_train.py --features ./out_ml/features.csv --labels ./out_ml/labels.csv

출력:
    out_ml/xgb/model.json        학습된 XGBoost
    out_ml/xgb/feature_cols.json 피처 순서(롤링/델타 포함)
    out_ml/xgb/importance.csv    피처 중요도
    콘솔: PR-AUC · 정밀도/재현율 (시간분할 검증)
"""
import argparse
import json
import os
import sys

ROLL_WINS = [15, 30]        # 롤링 평균/표준편차 창(분)
DELTA_LAGS = [15, 30]       # 델타(현재 − N분전)


def _need():
    try:
        import numpy, pandas, xgboost, sklearn  # noqa
        return True
    except Exception as e:
        print("=" * 60)
        print("⚠️ XGBoost 라이브러리 없음 — 회사 PC 에서:")
        print("   pip install xgboost pandas numpy scikit-learn")
        print(f"   ({type(e).__name__}: {e})")
        print("=" * 60)
        return False


def build_features(feat_df, base_cols):
    """31 원피처 → + 롤링평균/표준편차 + 델타 (전부 과거만 → 누수 없음)."""
    import pandas as pd  # noqa
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
    import pandas as pd
    df = pd.concat([df, pd.DataFrame(new, index=df.index)], axis=1)
    feat_cols = list(base_cols) + list(new.keys())
    return df, feat_cols


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', required=True)
    ap.add_argument('--labels', required=True)
    ap.add_argument('--test_ratio', type=float, default=0.25,
                    help='뒤쪽 비율을 시간분할 검증셋으로 (기본 0.25)')
    ap.add_argument('--out', default='./out_ml/xgb')
    a = ap.parse_args()

    print("=" * 60)
    print("XGBoost 비정상(정체) 판별 모델 학습")
    print("=" * 60)
    if not _need():
        sys.exit(2)

    import numpy as np
    import pandas as pd
    import xgboost as xgb
    from sklearn.metrics import average_precision_score, precision_recall_fscore_support

    os.makedirs(a.out, exist_ok=True)
    feat = pd.read_csv(a.features, encoding='utf-8-sig')
    lab = pd.read_csv(a.labels, encoding='utf-8-sig')
    feat['datetime'] = pd.to_datetime(feat['datetime'])
    lab['datetime'] = pd.to_datetime(lab['datetime'])
    base_cols = [c for c in feat.columns if c != 'datetime']

    # 롤링/델타 피처
    df, feat_cols = build_features(feat, base_cols)
    df = df.merge(lab[['datetime', 'y_pre30']], on='datetime', how='left')
    df['y_pre30'] = df['y_pre30'].fillna(0).astype(int)
    print(f"[데이터] {len(df)}분 × {len(feat_cols)}피처 (원 {len(base_cols)} + 롤링/델타)")
    print(f"[라벨] 양성(정체30분전) {int(df['y_pre30'].sum())}분 "
          f"({df['y_pre30'].mean()*100:.1f}%)")

    # 시간분할 (뒤쪽 = 검증) — 누수 차단
    n = len(df)
    cut = int(n * (1 - a.test_ratio))
    tr, te = df.iloc[:cut], df.iloc[cut:]
    Xtr, ytr = tr[feat_cols].values, tr['y_pre30'].values
    Xte, yte = te[feat_cols].values, te['y_pre30'].values
    pos, neg = int(ytr.sum()), int((ytr == 0).sum())
    spw = neg / max(pos, 1)
    print(f"[분할] 학습 {len(tr)}분(양성{pos}) / 검증 {len(te)}분(양성{int(yte.sum())}) "
          f"· scale_pos_weight={spw:.1f}")
    if pos == 0 or int(yte.sum()) == 0:
        print("⚠️ 학습/검증에 양성 0 — labels 확인 또는 test_ratio 조정"); sys.exit(3)

    model = xgb.XGBClassifier(
        n_estimators=400, max_depth=5, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, scale_pos_weight=spw,
        eval_metric='aucpr', n_jobs=4, random_state=0,
    )
    model.fit(Xtr, ytr, eval_set=[(Xte, yte)], verbose=False)

    # 검증 성능
    p = model.predict_proba(Xte)[:, 1]
    prauc = average_precision_score(yte, p)
    yhat = (p >= 0.5).astype(int)
    pr, rc, f1, _ = precision_recall_fscore_support(yte, yhat, average='binary', zero_division=0)
    print("\n" + "-" * 60)
    print(f"[검증] PR-AUC {prauc:.3f} · 정밀도 {pr:.2f} · 재현율 {rc:.2f} · F1 {f1:.2f}")
    print("  (PR-AUC 높을수록 정체 잘 분리. 임계 0.5 기준 정밀/재현)")

    # 저장
    model.save_model(os.path.join(a.out, 'model.json'))
    with open(os.path.join(a.out, 'feature_cols.json'), 'w', encoding='utf-8') as f:
        json.dump(feat_cols, f, ensure_ascii=False)
    imp = sorted(zip(feat_cols, model.feature_importances_), key=lambda x: -x[1])
    with open(os.path.join(a.out, 'importance.csv'), 'w', encoding='utf-8-sig') as f:
        f.write('feature,importance\n')
        for name, v in imp:
            f.write(f'{name},{v:.5f}\n')
    print("\n▶ 중요 피처 top10:")
    for name, v in imp[:10]:
        print(f"    {name:<32}{v:.4f}")
    print(f"\n🎉 → {a.out}/model.json  (importance.csv 포함)")
    print("다음: xgb_비정상_infer.py 로 jam_probability 생성 → 하이브리드 판정")


if __name__ == '__main__':
    main()
