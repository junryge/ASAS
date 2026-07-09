#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
밀림_방향추론 — 방향별 밀림 확률 + "어느 컨베이어가 밀리는지" 판정
====================================================================
6개 모델(남측/북측/허브 × 10분/30분) 로 매분 방향별 밀림확률 산출.
룰베이스와 병행: 룰이 조용한데 여기서 방향 밀림이 뜨면 = 국소밀림(룰 사각지대).

출력 컬럼:
   datetime |
   남측_10분%·30분%·등급 | 북측_... | 허브_... |
   밀림방향(최고등급 방향: 남측 4AFC3201 / 북측 4AFC3301 / 허브) | 밀림등급

등급(정밀도 기준, 방향 공통): 경계 p≥0.5 / 위험 p≥0.7 / 초위험 p≥0.85
게이트(오탐컷): 초위험=밤낮 항상 / 위험=주간(08~19시)만 / 경계=참고

입력:
   --features  features_june.csv (또는 실시간 창)
   --model     ./out_ml/밀림방향
   --out       ./out_ml/밀림방향_결과.csv

실행:
   python 밀림_방향추론.py --features .\out_ml_june\features.csv --model .\out_ml\밀림방향
"""
import argparse, json, os, sys

# 학습과 동일해야 함
ROLL_WINS = [15, 30, 60]
DELTA_LAGS = [10, 30]
CUSUM_BASE_WIN = 120
CUSUM_K = 0.5
DIR_LABEL = {'남측': '남측(4AFC3201)', '북측': '북측(4AFC3301)', '허브': '허브(몰림/저장)'}
GRADE_ORD = {'': 0, '경계': 1, '위험': 2, '초위험': 3}


def grade_of(p):
    return '초위험' if p >= 0.85 else '위험' if p >= 0.70 else '경계' if p >= 0.50 else ''


def gated(grade, hour):
    """초위험=항상 / 위험=주간만 / 경계=버림(참고표시 안함)."""
    if grade == '초위험':
        return grade
    if grade == '위험' and 8 <= hour <= 19:
        return grade
    return ''


def _cusum(np, s):
    import pandas as pd
    x = pd.Series(s).astype(float)
    base = x.shift(1).rolling(CUSUM_BASE_WIN, min_periods=15).median().bfill().fillna(x.iloc[0] if len(x) else 0.0)
    sd = x.shift(1).rolling(CUSUM_BASE_WIN, min_periods=15).std().fillna(0.0).values
    base = base.values; xv = x.values
    C = np.zeros(len(xv)); prev = 0.0
    for i in range(len(xv)):
        prev = max(0.0, prev + (xv[i] - base[i] - CUSUM_K * sd[i])); C[i] = prev
    return C


def build(df, base_cols):
    import numpy as np, pandas as pd
    for c in base_cols:
        if c not in df.columns:
            df[c] = 0.0
    df[base_cols] = df[base_cols].ffill().fillna(0.0)
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
    return pd.concat([df, pd.DataFrame(new, index=df.index)], axis=1)


def main():
    global np
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', required=True)
    ap.add_argument('--model', default='./out_ml/밀림방향')
    ap.add_argument('--out', default='./out_ml/밀림방향_결과.csv')
    a = ap.parse_args()
    try:
        import numpy, pandas as pd, xgboost as xgb
        np = numpy
    except Exception as e:
        print(f"⚠️ 라이브러리 없음 ({e})"); sys.exit(2)

    feat = pd.read_csv(a.features, encoding='utf-8-sig'); feat['datetime'] = pd.to_datetime(feat['datetime'])
    feat = feat.sort_values('datetime').reset_index(drop=True)
    dirs = ['남측', '북측', '허브']
    probs = {}   # (dir,pre) -> array
    for d in dirs:
        fc_path = os.path.join(a.model, f'feature_cols_{d}.json')
        if not os.path.exists(fc_path):
            print(f"⚠️ {d} 피처파일 없음 — 건너뜀"); continue
        feat_cols = json.load(open(fc_path, encoding='utf-8'))
        base_cols = [c for c in feat_cols if '__' not in c]
        dfb = build(feat.copy(), base_cols)
        for pre in [10, 30]:
            mp = os.path.join(a.model, f'model_{d}_pre{pre}.json')
            if not os.path.exists(mp):
                probs[(d, pre)] = np.zeros(len(dfb)); continue
            m = xgb.XGBClassifier(); m.load_model(mp)
            probs[(d, pre)] = m.predict_proba(dfb[feat_cols].values)[:, 1]
    print(f"[모델] {len([k for k in probs])} 개 로드 · {len(feat)}분 추론")

    hours = feat['datetime'].dt.hour.values
    rows = []
    n_alarm = {d: 0 for d in dirs}
    for i, t in enumerate(feat['datetime']):
        rec = {'datetime': t.strftime('%Y-%m-%d %H:%M')}
        best_dir, best_grade = '', ''
        for d in dirs:
            p10 = probs.get((d, 10), np.zeros(len(feat)))[i]
            p30 = probs.get((d, 30), np.zeros(len(feat)))[i]
            g = grade_of(max(p10, p30))
            gg = gated(g, hours[i])
            rec[f'{d}_10분%'] = f'{p10*100:.1f}'
            rec[f'{d}_30분%'] = f'{p30*100:.1f}'
            rec[f'{d}_등급'] = gg
            if gg and GRADE_ORD[gg] > GRADE_ORD[best_grade]:
                best_grade, best_dir = gg, d
        rec['밀림방향'] = DIR_LABEL[best_dir] if best_dir else ''
        rec['밀림등급'] = best_grade
        if best_dir:
            n_alarm[best_dir] += 1
        rows.append(rec)

    cols = ['datetime'] + [f'{d}_{h}' for d in dirs for h in ('10분%', '30분%', '등급')] + ['밀림방향', '밀림등급']
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    import csv as _csv
    with open(a.out, 'w', newline='', encoding='utf-8-sig') as f:
        w = _csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    tot = sum(n_alarm.values())
    print(f"[완료] {len(feat)}분 → {a.out}")
    print(f"       밀림경보(게이트후): 남측 {n_alarm['남측']} / 북측 {n_alarm['북측']} / 허브 {n_alarm['허브']}  (총 {tot}분, {tot/len(feat)*100:.1f}%)")
    print("       룰베이스와 병행: 룰 조용(50미만)한데 여기 밀림방향 뜨면 = 국소밀림")


if __name__ == '__main__':
    main()
