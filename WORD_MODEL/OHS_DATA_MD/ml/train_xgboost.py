#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XGBoost 학습 — 30분 사전 정체 예측 모델

사용법:
    python3 train_xgboost.py \\
        --features features.csv \\
        --incidents incidents.json \\
        --out model.json \\
        --lead_min 30

incidents.json 형식:
    [
      {"start": "2026-04-21 13:50:00", "end": "2026-04-21 13:50:00"},
      {"start": "2026-04-21 14:12:00", "end": "2026-04-21 14:16:00"},
      {"start": "2026-05-06 09:35:00", "end": "2026-05-06 10:09:00"},
      {"start": "2026-05-07 07:32:00", "end": "2026-05-07 07:38:00"}
    ]

라벨 규칙: 시점 t에서 t + lead_min 분 후가 사건 구간이면 1, 아니면 0.

출력:
    · model.json (XGBoost 모델)
    · model_report.txt (검증 지표, 피처 중요도)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta


def _parse_dt(s):
    s = s.strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f'시각 파싱 실패: {s}')


def load_features(features_csv):
    """피처 CSV 로드 → pandas DataFrame"""
    import pandas as pd
    df = pd.read_csv(features_csv)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def load_incidents(incidents_json):
    """사건 라벨 JSON 로드"""
    with open(incidents_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [(_parse_dt(d['start']), _parse_dt(d['end'])) for d in data]


def make_labels(df, incidents, lead_min=30):
    """t + lead_min 분 시점이 사건 구간이면 1, 아니면 0"""
    import pandas as pd
    labels = []
    delta = pd.Timedelta(minutes=lead_min)
    for ts in df['timestamp']:
        future = ts + delta
        label = 0
        for s, e in incidents:
            if s <= future <= e:
                label = 1
                break
        labels.append(label)
    df['label'] = labels
    return df


def train(features_csv, incidents_json, out_path, lead_min=30):
    import pandas as pd
    import numpy as np
    import xgboost as xgb
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import (
        roc_auc_score, average_precision_score,
        precision_recall_fscore_support, confusion_matrix,
    )

    print(f'📥 피처: {features_csv}')
    print(f'📥 사건: {incidents_json}')
    print(f'📅 lead: {lead_min} 분 사전 예측')
    print()

    df = load_features(features_csv)
    incidents = load_incidents(incidents_json)
    df = make_labels(df, incidents, lead_min)

    print(f'데이터: {len(df):,} 행')
    print(f'사건: {len(incidents)} 건')
    print(f'라벨 분포: 0={sum(df["label"]==0):,}, 1={sum(df["label"]==1):,}')
    print(f'불균형 비율 (정상:정체): {(df["label"]==0).sum() / max((df["label"]==1).sum(), 1):.1f}:1')
    print()

    # 피처/라벨 분리
    drop_cols = ['timestamp', 'label', '_rule_s1', '_rule_s2', '_rule_s3']
    feature_cols = [c for c in df.columns if c not in drop_cols]
    X = df[feature_cols].values
    y = df['label'].values

    # 불균형 보정 (정상:정체 비율)
    pos_count = (y == 1).sum()
    neg_count = (y == 0).sum()
    scale_pos_weight = neg_count / max(pos_count, 1)

    # ── 시계열 분할 검증 ──
    tscv = TimeSeriesSplit(n_splits=5)
    cv_scores = []
    print('── 시계열 5-Fold 검증 ──')
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
        if (y[train_idx] == 1).sum() == 0 or (y[val_idx] == 1).sum() == 0:
            print(f'  Fold {fold}: 학습/검증에 positive 없음 — skip')
            continue

        model = xgb.XGBClassifier(
            objective='binary:logistic',
            n_estimators=300,
            max_depth=4,
            learning_rate=0.05,
            scale_pos_weight=scale_pos_weight,
            eval_metric='aucpr',
            early_stopping_rounds=20,
            verbosity=0,
        )
        model.fit(
            X[train_idx], y[train_idx],
            eval_set=[(X[val_idx], y[val_idx])],
            verbose=False,
        )
        y_pred = model.predict_proba(X[val_idx])[:, 1]
        pr_auc = average_precision_score(y[val_idx], y_pred)
        roc_auc = roc_auc_score(y[val_idx], y_pred) if len((set(y[val_idx]))) > 1 else 0.0
        cv_scores.append((pr_auc, roc_auc))
        print(f'  Fold {fold}: PR-AUC={pr_auc:.3f}, ROC-AUC={roc_auc:.3f}')

    if cv_scores:
        mean_pr = sum(s[0] for s in cv_scores) / len(cv_scores)
        mean_roc = sum(s[1] for s in cv_scores) / len(cv_scores)
        print(f'  평균: PR-AUC={mean_pr:.3f}, ROC-AUC={mean_roc:.3f}')
    print()

    # ── 전체 데이터로 최종 학습 ──
    print('── 전체 데이터 최종 학습 ──')
    final_model = xgb.XGBClassifier(
        objective='binary:logistic',
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        scale_pos_weight=scale_pos_weight,
        eval_metric='aucpr',
        verbosity=0,
    )
    final_model.fit(X, y, verbose=False)

    # ── 평가 (in-sample) ──
    y_pred_proba = final_model.predict_proba(X)[:, 1]
    y_pred = (y_pred_proba >= 0.5).astype(int)

    pr_auc = average_precision_score(y, y_pred_proba)
    roc_auc = roc_auc_score(y, y_pred_proba) if len(set(y)) > 1 else 0.0
    p, r, f1, _ = precision_recall_fscore_support(y, y_pred, average='binary', zero_division=0)
    cm = confusion_matrix(y, y_pred)

    print(f'  In-sample PR-AUC:  {pr_auc:.3f}')
    print(f'  In-sample ROC-AUC: {roc_auc:.3f}')
    print(f'  Precision: {p:.3f}, Recall: {r:.3f}, F1: {f1:.3f}')
    print(f'  Confusion Matrix:\n  {cm}')
    print()

    # ── 모델 저장 ──
    final_model.save_model(out_path)
    print(f'💾 모델 → {out_path}')

    # 피처명 저장 (예측 시 사용)
    feature_names_path = out_path.replace('.json', '_features.json').replace('.bin', '_features.json')
    with open(feature_names_path, 'w', encoding='utf-8') as f:
        json.dump(feature_cols, f, ensure_ascii=False, indent=2)
    print(f'💾 피처명 → {feature_names_path}')

    # ── 피처 중요도 ──
    importances = final_model.feature_importances_
    feat_imp = sorted(zip(feature_cols, importances), key=lambda x: -x[1])
    print('\n── 피처 중요도 TOP 15 ──')
    for name, imp in feat_imp[:15]:
        bar = '█' * int(imp * 200)
        print(f'  {name:<35} {imp:.4f} {bar}')

    # 리포트 저장
    report_path = out_path.replace('.json', '_report.txt').replace('.bin', '_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f'XGBoost 학습 리포트\n')
        f.write(f'====================\n')
        f.write(f'입력 피처: {features_csv}\n')
        f.write(f'사건 JSON: {incidents_json}\n')
        f.write(f'lead_min: {lead_min}\n\n')
        f.write(f'데이터: {len(df):,} 행 (positive {pos_count}, negative {neg_count})\n')
        f.write(f'scale_pos_weight: {scale_pos_weight:.2f}\n\n')
        f.write(f'In-sample 지표:\n')
        f.write(f'  PR-AUC:  {pr_auc:.3f}\n')
        f.write(f'  ROC-AUC: {roc_auc:.3f}\n')
        f.write(f'  Precision: {p:.3f}, Recall: {r:.3f}, F1: {f1:.3f}\n\n')
        f.write(f'Confusion Matrix:\n{cm}\n\n')
        f.write(f'피처 중요도 TOP 20:\n')
        for name, imp in feat_imp[:20]:
            f.write(f'  {name:<35} {imp:.4f}\n')
    print(f'💾 리포트 → {report_path}')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--features', required=True, help='피처 CSV (feature_builder 출력)')
    p.add_argument('--incidents', required=True, help='사건 JSON')
    p.add_argument('--out', default='model.json', help='모델 저장 경로')
    p.add_argument('--lead_min', type=int, default=30, help='사전 예측 시간 (분)')
    args = p.parse_args()

    if not os.path.exists(args.features):
        sys.exit(f'파일 없음: {args.features}')
    if not os.path.exists(args.incidents):
        sys.exit(f'파일 없음: {args.incidents}')

    train(args.features, args.incidents, args.out, args.lead_min)


if __name__ == '__main__':
    main()
