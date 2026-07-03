#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tspulse_baseline — 학습된 모델의 '정상 재구성오차' 기준선 고정 (재학습 X)  ★회사 PC 전용
====================================================================================
[왜 필요한가] tspulse_infer 는 점수를 낼 때 '입력 데이터 자신의' 오차 median/MAD 로
시그모이드 정규화한다. 그래서 어떤 구간을 넣든 절반은 0.5 위(=경계+), 상당수가 0.7 위(=위험)로
찍힌다(자기참조 정규화 = 과탐지의 근본원인). 6월 예측에서 매일 위험 20~60% 가 나온 이유.

[해결] 학습에 쓴 '정상' 데이터로 재구성오차 분포를 한 번 계산해 그 median/MAD 를
scaler.json 에 '고정(frozen baseline)' 으로 저장한다. 이후 tspulse_infer 는 이 고정값으로
정규화 → 진짜 정상 분(minute)은 낮게, 급증(정체 전조)만 높게 나온다.
★ 재학습 아님: 학습된 모델로 순전파 1회만. (가중치·scaler stats 안 건드림, 항목만 추가)

입력:
    --features   학습에 쓴 features.csv (정상 raw 기반)  ← tspulse_train 과 동일 파일
    --model      out_ml/tspulse (model/ + scaler.json)
    --labels     (옵션) is_normal 마스크. 없으면 features 전체를 정상으로 간주
실행:
    python tspulse_baseline.py --features ./out_ml/features.csv --model ./out_ml/tspulse
결과:
    scaler.json 에 err_median / err_mad / baseline_n 추가.
    → 이후 tspulse_infer.py 가 자동으로 고정 기준선 사용.
"""
import argparse
import json
import os
import sys


def _need():
    try:
        import numpy, pandas, torch  # noqa
        from tsfm_public.models.tspulse import TSPulseForReconstruction  # noqa
        return True
    except Exception as e:
        print("⚠️ 라이브러리 없음 — 회사 PC 전용")
        print(f"   ({type(e).__name__}: {e})")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', required=True)
    ap.add_argument('--model', default='./out_ml/tspulse')
    ap.add_argument('--labels', default=None)
    ap.add_argument('--batch', type=int, default=128)
    ap.add_argument('--stride', type=int, default=1,
                    help='기준선 계산 창 간격(분). 1=매분(정확), 크게주면 빠름')
    a = ap.parse_args()

    print("=" * 60)
    print("TSPulse R1 정상 기준선 고정 (frozen baseline) — 재학습 아님")
    print("=" * 60)
    if not _need():
        sys.exit(2)

    import numpy as np
    import pandas as pd
    import torch
    from tsfm_public.models.tspulse import TSPulseForReconstruction

    sc_fp = os.path.join(a.model, 'scaler.json')
    scaler = json.load(open(sc_fp, encoding='utf-8'))
    cols, stats, C = scaler['features'], scaler['stats'], scaler['context']

    feat = pd.read_csv(a.features, encoding='utf-8-sig')
    feat['datetime'] = pd.to_datetime(feat['datetime'])
    feat = feat.sort_values('datetime').reset_index(drop=True)
    feat[cols] = feat[cols].ffill().fillna(0.0)

    # 정상 마스크 + 1분 연속 세그먼트 (학습창과 동일 규칙: 시간 구멍 안 넘음)
    if a.labels and os.path.exists(a.labels):
        lab = pd.read_csv(a.labels, encoding='utf-8-sig')
        lab['datetime'] = pd.to_datetime(lab['datetime'])
        m = feat.merge(lab[['datetime', 'is_normal']], on='datetime', how='left')
        isn = m['is_normal'].fillna(0).astype(int).values
    else:
        isn = np.ones(len(feat), dtype=int)
    tmin = feat['datetime'].values.astype('datetime64[m]').astype('int64')

    Xn = np.zeros((len(feat), len(cols)), dtype='float32')
    for j, c in enumerate(cols):
        Xn[:, j] = (feat[c].astype(float).values - stats[c]['median']) / stats[c]['iqr']

    # 연속 정상 세그먼트 안에서만 창 생성
    segs, i, n = [], 0, len(Xn)
    while i < n:
        if isn[i] != 1:
            i += 1; continue
        j = i
        while j + 1 < n and isn[j + 1] == 1 and (tmin[j + 1] - tmin[j]) == 1:
            j += 1
        segs.append((i, j)); i = j + 1
    idxs = []
    for s, e in segs:
        for k in range(s + C - 1, e + 1, a.stride):   # 창 마지막 시점 t = k
            idxs.append(k)
    if not idxs:
        print("⚠️ 정상 창 0개 — features/labels 확인"); sys.exit(3)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = TSPulseForReconstruction.from_pretrained(os.path.join(a.model, 'model')).to(device)
    model.eval()
    print(f"[기준선] 정상 창 {len(idxs)}개 순전파 (device={device}, stride={a.stride})", flush=True)

    errs = np.empty(len(idxs), dtype='float64')
    with torch.no_grad():
        buf_i, buf_x = [], []
        pos = [0]

        def flush():
            if not buf_x:
                return
            xb = torch.tensor(np.stack(buf_x)).to(device)
            out = model(past_values=xb)
            recon = out.reconstruction_outputs if hasattr(out, 'reconstruction_outputs') else out[1]
            e = ((recon[:, -1, :] - xb[:, -1, :]) ** 2).mean(dim=1).cpu().numpy()
            for v in e:
                errs[pos[0]] = float(v); pos[0] += 1
            buf_i.clear(); buf_x.clear()

        for c, t in enumerate(idxs, 1):
            buf_i.append(t); buf_x.append(Xn[t - C + 1:t + 1])
            if len(buf_x) >= a.batch:
                flush()
            if c % (a.batch * 20) == 0:
                print(f"    {c}/{len(idxs)} ({c/len(idxs)*100:.0f}%)", flush=True)
        flush()

    med = float(np.median(errs))
    mad = float(np.median(np.abs(errs - med))) or 1e-9
    scaler['err_median'] = med
    scaler['err_mad'] = mad
    scaler['baseline_n'] = len(idxs)
    json.dump(scaler, open(sc_fp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    print(f"[완료] 정상 재구성오차  median={med:.6f}  MAD={mad:.6f}  (n={len(idxs)})")
    print(f"       → {sc_fp} 에 고정 저장")
    print("       이제 tspulse_infer 는 이 기준선으로 정규화 (정상=낮음, 급증=높음)")


if __name__ == '__main__':
    main()
