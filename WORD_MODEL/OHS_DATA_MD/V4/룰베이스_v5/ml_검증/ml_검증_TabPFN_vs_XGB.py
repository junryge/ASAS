#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML 검증 PoC — TabPFN v2 (2025 Nature, 소량라벨 SOTA) vs XGBoost
================================================================================
목적: 메신저 정체 라벨(56건, 불균형 ~5%)로 "30분 사전 예측"이
      실제 학습 가능한지 두 모델로 검증. (정확도 X → PR-AUC·리드타임)

★ 이 환경(원격)엔 라이브러리가 없어 못 돌림 → 회사 PC 전용.

설치 (회사 PC):
    pip install tabpfn xgboost scikit-learn pandas numpy
    # TabPFN v2 는 GPU 권장 (CPU 도 소량이면 가능)

입력:
    --features   : 피처 원천 CSV (발동이벤트.csv 들을 합친 것, 또는 raw 265)
                   필수 컬럼: datetime  + 수치 피처들
    --episodes   : 메신저 episode.csv (라벨 원천)
    --lead_min   : 사전예측 분 (기본 30)
    --out        : 결과 폴더 (기본 ./out_검증)

실행:
    python ml_검증_TabPFN_vs_XGB.py \
        --features features_all.csv \
        --episodes 20260612_065558_episode.csv \
        --lead_min 30 --out ./out_검증

출력:
    - 비교표 (TabPFN vs XGBoost): PR-AUC / ROC-AUC / 리드타임 / 탐지율
    - feature_importance (XGBoost) + 콘솔 요약
"""
import argparse
import os
import sys
from datetime import datetime, timedelta

# ── 라이브러리 (회사 PC) ──
try:
    import numpy as np
    import pandas as pd
    from sklearn.metrics import average_precision_score, roc_auc_score
except ImportError as e:
    sys.exit(f"❌ 라이브러리 없음: {e}\n   회사 PC에서: pip install xgboost scikit-learn pandas numpy tabpfn")

# 정체 라벨로 쓸 메신저 fault_type (orphan·CAPA변경 제외)
JAM_TYPES = {'정체/병목', '리프터', 'CNV', 'MLUD', '브릿지'}


# ============================================================
# 1. 라벨 생성 — 메신저 episode → 분 단위 (t, t+lead] 양성
# ============================================================
def build_labels(episodes_csv, lead_min):
    ep = pd.read_csv(episodes_csv, encoding='utf-8-sig')
    ep['start'] = pd.to_datetime(ep['start_time'], errors='coerce')
    # 정체 + orphan 아님
    mask = (ep['is_orphan'] != 'Y') & (ep['fault_type'].isin(JAM_TYPES))
    starts = ep.loc[mask, 'start'].dropna().sort_values().tolist()
    print(f"[라벨] 메신저 정체 episode {len(starts)}건 (lead {lead_min}분)")
    return starts  # 각 시작시각 t0 → (t0-lead, t0] 구간이 양성


def label_minutes(index_dt, starts, lead_min):
    """index_dt(피처 시각 Series) 각 분에 대해 y=1 if 향후 lead분 내 정체 시작."""
    y = np.zeros(len(index_dt), dtype=int)
    starts = sorted(starts)
    idx = index_dt.values.astype('datetime64[m]')
    for t0 in starts:
        t0 = np.datetime64(t0, 'm')
        lo = t0 - np.timedelta64(lead_min, 'm')
        # (lo, t0] 구간의 피처 분들이 "30분 후 정체" → 양성
        y[(idx > lo) & (idx <= t0)] = 1
    return y


# ============================================================
# 2. 피처 엔지니어링 — 시각 t 까지만 (누수 차단)
# ============================================================
def build_features(feat_csv):
    df = pd.read_csv(feat_csv, encoding='utf-8-sig')
    # datetime 컬럼 찾기
    dtcol = 'datetime' if 'datetime' in df.columns else ('CRT_TM' if 'CRT_TM' in df.columns else df.columns[0])
    df[dtcol] = pd.to_datetime(df[dtcol], errors='coerce')
    df = df.dropna(subset=[dtcol]).sort_values(dtcol).reset_index(drop=True)

    # 수치 컬럼만 (문자/등급/이유 제외)
    num = df.select_dtypes(include=[np.number]).copy()
    # 라벨 누수 위험 컬럼 제거 (룰 등급/점수는 그 분 결과라 빼고 비교 — 옵션)
    drop_like = [c for c in num.columns if c.lower() in
                 ('unified_risk_score', 'hot_score') or c.endswith('_score')]
    base = num.drop(columns=drop_like, errors='ignore')

    feats = {}
    # 현재값
    for c in base.columns:
        feats[c] = base[c]
    # 롤링 통계 (과거만 — min_periods=1, shift 없이 rolling 은 현재 포함이라 OK: 현재까지)
    for w in (5, 10, 30, 60):
        r = base.rolling(w, min_periods=1)
        feats_mean = r.mean().add_suffix(f'_mean{w}')
        feats_std = r.std().add_suffix(f'_std{w}')
        feats_max = r.max().add_suffix(f'_max{w}')
        for fr in (feats_mean, feats_std, feats_max):
            for c in fr.columns: feats[c] = fr[c]
    # 변화량 delta (1/5/10분)
    for d in (1, 5, 10):
        dl = base.diff(d).add_suffix(f'_d{d}')
        for c in dl.columns: feats[c] = dl[c]
    # 시간 컨텍스트
    feats['hour'] = df[dtcol].dt.hour
    feats['dow'] = df[dtcol].dt.dayofweek

    X = pd.DataFrame(feats).fillna(0.0)
    print(f"[피처] {X.shape[0]}행 × {X.shape[1]}피처")
    return df[dtcol], X


# ============================================================
# 3. 시간 분할 (랜덤 금지)
# ============================================================
def time_split(dt, frac_train=0.7, frac_val=0.15):
    n = len(dt)
    i_tr = int(n * frac_train)
    i_va = int(n * (frac_train + frac_val))
    return slice(0, i_tr), slice(i_tr, i_va), slice(i_va, n)


# ============================================================
# 4. 모델 — TabPFN v2 / XGBoost
# ============================================================
def run_xgboost(Xtr, ytr, Xva, yva, Xte):
    import xgboost as xgb
    spw = max(1.0, (ytr == 0).sum() / max(1, (ytr == 1).sum()))
    clf = xgb.XGBClassifier(
        n_estimators=400, max_depth=5, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        scale_pos_weight=spw, eval_metric='aucpr',
        n_jobs=-1, early_stopping_rounds=30,
    )
    clf.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
    return clf.predict_proba(Xte)[:, 1], clf


def run_tabpfn(Xtr, ytr, Xva, yva, Xte, max_train=10000):
    """TabPFN v2 — 소량 라벨 SOTA. 샘플 많으면 양성 위주 다운샘플."""
    from tabpfn import TabPFNClassifier
    # TabPFN 권장: 학습 샘플 ≤ 10k, 피처 ≤ 500
    Xtr2, ytr2 = Xtr, ytr
    if len(Xtr) > max_train:
        pos = np.where(ytr == 1)[0]
        neg = np.where(ytr == 0)[0]
        n_neg = min(len(neg), max_train - len(pos))
        rng = np.random.default_rng(42)
        sel = np.concatenate([pos, rng.choice(neg, n_neg, replace=False)])
        sel.sort()
        Xtr2, ytr2 = Xtr.iloc[sel], ytr[sel]
        print(f"[TabPFN] 다운샘플 {len(Xtr)}→{len(Xtr2)} (양성 {len(pos)} 전부 유지)")
    if Xtr2.shape[1] > 500:
        print(f"[TabPFN] ⚠ 피처 {Xtr2.shape[1]}>500 — 상위 분산 500개로 축소")
        top = Xtr2.var().sort_values(ascending=False).head(500).index
        Xtr2, Xte = Xtr2[top], Xte[top]
    clf = TabPFNClassifier()
    clf.fit(Xtr2.values, ytr2)
    return clf.predict_proba(Xte.values)[:, 1], clf


# ============================================================
# 5. 평가 — PR-AUC / 리드타임 / 탐지율
# ============================================================
def lead_time_eval(dt_te, proba, starts, lead_min, thr=0.5):
    """ML score 가 thr 넘은 시각이 메신저 정체보다 평균 몇 분 먼저인지."""
    dt = dt_te.values.astype('datetime64[m]')
    fire = dt[proba >= thr]
    leads, hits = [], 0
    for t0 in starts:
        t0 = np.datetime64(t0, 'm')
        win = fire[(fire > t0 - np.timedelta64(lead_min, 'm')) & (fire <= t0)]
        if len(win):
            hits += 1
            leads.append((t0 - win.min()) / np.timedelta64(1, 'm'))
    det = hits / max(1, sum(1 for t0 in starts
                            if np.datetime64(t0, 'm') >= dt.min() and np.datetime64(t0, 'm') <= dt.max()))
    return (np.mean(leads) if leads else 0.0), det


def report(name, yte, proba, dt_te, starts, lead_min):
    prauc = average_precision_score(yte, proba) if yte.sum() else float('nan')
    rocauc = roc_auc_score(yte, proba) if 0 < yte.sum() < len(yte) else float('nan')
    lead, det = lead_time_eval(dt_te, proba, starts, lead_min)
    print(f"\n── {name} ──")
    print(f"  PR-AUC   : {prauc:.3f}  (목표 ≥0.4)")
    print(f"  ROC-AUC  : {rocauc:.3f}")
    print(f"  평균리드 : {lead:.1f}분  (목표 ≥25)")
    print(f"  탐지율   : {det*100:.0f}%  (목표 ≥60)")
    return dict(model=name, pr_auc=prauc, roc_auc=rocauc, lead_min=lead, detect=det)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', required=True)
    ap.add_argument('--episodes', required=True)
    ap.add_argument('--lead_min', type=int, default=30)
    ap.add_argument('--out', default='./out_검증')
    ap.add_argument('--only', choices=['xgb', 'tabpfn', 'both'], default='both')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    starts = build_labels(a.episodes, a.lead_min)
    dt, X = build_features(a.features)
    y = label_minutes(dt, starts, a.lead_min)
    print(f"[라벨] 양성 {y.sum()} / {len(y)}분 = {y.mean()*100:.1f}%  (불균형 {(y==0).sum()/max(1,y.sum()):.0f}:1)")

    tr, va, te = time_split(dt)
    Xtr, Xva, Xte = X.iloc[tr], X.iloc[va], X.iloc[te]
    ytr, yva, yte = y[tr], y[va], y[te]
    dt_te = dt.iloc[te]
    print(f"[분할] train {ytr.sum()}/{len(ytr)} · val {yva.sum()}/{len(yva)} · test {yte.sum()}/{len(yte)} (양성/전체)")
    if yte.sum() == 0:
        print("⚠️ test 구간에 양성 없음 — lead_min/분할 비율/기간 조정 필요")

    results = []
    if a.only in ('xgb', 'both'):
        try:
            p, clf = run_xgboost(Xtr, ytr, Xva, yva, Xte)
            results.append(report('XGBoost', yte, p, dt_te, starts, a.lead_min))
            imp = pd.Series(clf.feature_importances_, index=X.columns).sort_values(ascending=False)
            imp.head(30).to_csv(os.path.join(a.out, 'xgb_feature_importance.csv'), encoding='utf-8-sig')
            print(f"  → 피처중요도 top30 저장")
        except Exception as e:
            print(f"  XGBoost 실패: {e}")
    if a.only in ('tabpfn', 'both'):
        try:
            p, _ = run_tabpfn(Xtr, ytr, Xva, yva, Xte)
            results.append(report('TabPFN v2', yte, p, dt_te, starts, a.lead_min))
        except Exception as e:
            print(f"  TabPFN 실패: {e}  (pip install tabpfn / GPU 확인)")

    if results:
        pd.DataFrame(results).to_csv(os.path.join(a.out, '검증_비교.csv'),
                                     index=False, encoding='utf-8-sig')
        print(f"\n🎉 완료 → {a.out}/검증_비교.csv")
        print("\n=== 최종 비교 ===")
        print(pd.DataFrame(results).to_string(index=False))


if __name__ == '__main__':
    main()
