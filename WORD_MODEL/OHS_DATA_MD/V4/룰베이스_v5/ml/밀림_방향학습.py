#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
밀림_방향학습 — 방향별(남측/북측/허브) 밀림 XGBoost (각 방향 집중 모델)
====================================================================
[구조] 통합모델(876피처) 대신 방향마다 그 방향 큐 6~7개 + CUSUM/델타/롤링만 학습.
       → 신호 희석 없이 "그 컨베이어 밀림"을 집중 학습. CUSUM 을 피처로 흡수(통계+ML).

방향별 입력 피처(원본, features_31.py 산출 컬럼):
   남측 = DIR_SouthCNV_Q, DIR_SouthCNVtoM14_T, DIR_M16toM14A_CNV, DIR_M16toM14B_CNV,
          DIR_M16toM14_Q, RA_M16HUB, RB_M16send
   북측 = DIR_NorthCNV_Q, DIR_NorthCNVtoM14_T, DIR_M16toM14_Q, RA_M16HUB, RB_M16send
   허브 = BR_HUB_totalQ, BR_ZT_3to6, BR_ZT_6to3, BR_dir_imbalance, RD_STK, RD_STB, RA_M16HUB
   (각 원피처에 롤링15/30/60, 델타10/30, CUSUM120 추가)

입력:
   --features  features.csv
   --labels    방향라벨.csv (밀림_방향라벨.py 산출)
   --out       모델 폴더 (기본 ./out_ml/밀림방향)

실행:
   python 밀림_방향학습.py --features .\out_ml\features.csv --labels .\out_ml\방향라벨.csv

출력: out_ml/밀림방향/model_{방향}_{pre}.json + feature_cols_{방향}.json + importance
"""
import argparse, json, os, sys

ROLL_WINS = [15, 30, 60]
DELTA_LAGS = [10, 30]
CUSUM_BASE_WIN = 120
CUSUM_K = 0.5

DIR_FEATURES = {
    '남측': ['DIR_SouthCNV_Q', 'DIR_SouthCNVtoM14_T', 'DIR_M16toM14A_CNV',
             'DIR_M16toM14B_CNV', 'DIR_M16toM14_Q', 'RA_M16HUB', 'RB_M16send'],
    '북측': ['DIR_NorthCNV_Q', 'DIR_NorthCNVtoM14_T', 'DIR_M16toM14_Q',
             'RA_M16HUB', 'RB_M16send'],
    '허브': ['BR_HUB_totalQ', 'BR_ZT_3to6', 'BR_ZT_6to3', 'BR_dir_imbalance',
             'RD_STK', 'RD_STB', 'RA_M16HUB'],
}


def _cusum(np, s, base_win=CUSUM_BASE_WIN, k=CUSUM_K):
    import pandas as pd
    x = pd.Series(s).astype(float)
    base = x.shift(1).rolling(base_win, min_periods=15).median().bfill().fillna(x.iloc[0] if len(x) else 0.0)
    sd = x.shift(1).rolling(base_win, min_periods=15).std().fillna(0.0).values
    base = base.values; xv = x.values
    C = np.zeros(len(xv)); prev = 0.0
    for i in range(len(xv)):
        prev = max(0.0, prev + (xv[i] - base[i] - k * sd[i])); C[i] = prev
    return C


def build_dir_features(df, base_cols):
    """방향 원피처 → + 롤링/델타/CUSUM (과거만, 누수없음)."""
    import numpy as np, pandas as pd
    have = [c for c in base_cols if c in df.columns]
    miss = [c for c in base_cols if c not in df.columns]
    if miss:
        print(f"   ⚠️ features.csv 에 없는 컬럼(0 처리): {miss}")
        for c in miss:
            df[c] = 0.0
    df[have] = df[have].ffill().fillna(0.0)
    new = {}
    for c in base_cols:
        s = df[c].astype(float)
        for w in ROLL_WINS:
            new[f'{c}__rmean{w}'] = s.rolling(w, min_periods=1).mean()
            new[f'{c}__rstd{w}'] = s.rolling(w, min_periods=1).std().fillna(0.0)
        new[f'{c}__rmax60'] = s.rolling(60, min_periods=1).max()
        for lag in DELTA_LAGS:
            new[f'{c}__d{lag}'] = s - s.shift(lag).fillna(s.iloc[0])
        new[f'{c}__cusum'] = _cusum(np, s.values)
    out = pd.concat([df, pd.DataFrame(new, index=df.index)], axis=1)
    return out, base_cols + list(new.keys())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', required=True)
    ap.add_argument('--labels', required=True)
    ap.add_argument('--test_ratio', type=float, default=0.25)
    ap.add_argument('--out', default='./out_ml/밀림방향')
    a = ap.parse_args()

    try:
        import numpy as np, pandas as pd, xgboost as xgb
        from sklearn.metrics import average_precision_score, precision_recall_fscore_support
    except Exception as e:
        print(f"⚠️ 라이브러리 없음: pip install xgboost pandas numpy scikit-learn ({e})"); sys.exit(2)

    os.makedirs(a.out, exist_ok=True)
    feat = pd.read_csv(a.features, encoding='utf-8-sig'); feat['datetime'] = pd.to_datetime(feat['datetime'])
    lab = pd.read_csv(a.labels, encoding='utf-8-sig'); lab['datetime'] = pd.to_datetime(lab['datetime'])
    feat = feat.sort_values('datetime').reset_index(drop=True)

    print("=" * 60 + "\n방향별 밀림 XGBoost 학습\n" + "=" * 60)
    for direction, base_cols in DIR_FEATURES.items():
        print(f"\n■ [{direction}] 피처 {base_cols}")
        df, feat_cols = build_dir_features(feat.copy(), base_cols)
        df = df.merge(lab, on='datetime', how='left')
        targets = [c for c in lab.columns if c.startswith(direction)]
        for t in targets:
            df[t] = df[t].fillna(0).astype(int)
        with open(os.path.join(a.out, f'feature_cols_{direction}.json'), 'w', encoding='utf-8') as f:
            json.dump(feat_cols, f, ensure_ascii=False)
        n = len(df); cut = int(n * (1 - a.test_ratio))
        tr, te = df.iloc[:cut], df.iloc[cut:]
        Xtr, Xte = tr[feat_cols].values, te[feat_cols].values
        for tgt in targets:
            ytr, yte = tr[tgt].values, te[tgt].values
            pos = int(ytr.sum())
            if pos == 0 or int(yte.sum()) == 0:
                print(f"   [{tgt}] 양성 부족(학습{pos}/검증{int(yte.sum())}) — 건너뜀"); continue
            spw = (ytr == 0).sum() / max(pos, 1)
            model = xgb.XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05,
                                      subsample=0.8, colsample_bytree=0.8, scale_pos_weight=spw,
                                      eval_metric='aucpr', n_jobs=4, random_state=0)
            model.fit(Xtr, ytr, eval_set=[(Xte, yte)], verbose=False)
            p = model.predict_proba(Xte)[:, 1]
            prauc = average_precision_score(yte, p)
            pr, rc, f1, _ = precision_recall_fscore_support(yte, (p >= 0.5).astype(int),
                                                            average='binary', zero_division=0)
            print(f"   [{tgt}] 양성 {int(df[tgt].sum())}분 · PR-AUC {prauc:.3f} · 정밀도 {pr:.2f} 재현율 {rc:.2f}")
            # 정밀도 등급컷
            calib = []
            for thr in [0.3, 0.5, 0.7, 0.8, 0.9]:
                yh = p >= thr; npred = int(yh.sum()); tp = int((yh & (yte == 1)).sum())
                calib.append((thr, npred, tp / npred if npred else 0))
            print("        " + " ".join(f"≥{t:.1f}:{prc*100:.0f}%({nn})" for t, nn, prc in calib))
            model.save_model(os.path.join(a.out, f'model_{tgt}.json'))
            imp = sorted(zip(feat_cols, model.feature_importances_), key=lambda x: -x[1])[:5]
            print("        top: " + ", ".join(f"{k}({v:.2f})" for k, v in imp))
    print(f"\n🎉 완료 → {a.out}/  다음: python 밀림_방향추론.py")


if __name__ == '__main__':
    main()
