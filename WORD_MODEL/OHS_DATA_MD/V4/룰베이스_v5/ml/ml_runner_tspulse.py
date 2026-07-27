#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ml_runner_tspulse — 실시간 독립 추론기 (Phase 5)  ★회사 PC 전용
====================================================================
매분 최신 raw 를 읽어 → 핵심31피처 과거창 → TSPulse 이상점수 → CSV 적재.
룰베이스(test_table3)와 **병행만**. 하이브리드 융합 X (계획서 8절).

동작:
    · 최근 context(기본 512분) raw 를 읽어 마지막 분의 anomaly_score 계산
    · out: ml_predict/YYYYMMDD_anomaly.csv 에 append (datetime, anomaly_score, ml_level)
    · --loop 지정 시 60초 간격 반복 (운영), 미지정 시 1회 (배치/테스트)

전제: tspulse_train.py 로 만든 model + scaler.json 필요.
      pip install "granite-tsfm[notebooks]" torch pandas numpy

입력:
    --raw     실시간 raw CSV (누적 파일 또는 최근 파일. CRT_TM 최신순 포함)
    --model   out_ml/tspulse (model/ + scaler.json)
    --outdir  적재 폴더 (기본 ./ml_predict)
    --loop    지정 시 매분 반복

실행(배치 1회):
    python ml_runner_tspulse.py --raw ./predict/M16A_HUBROOM_PR.csv --model ./out_ml/tspulse
실행(운영 반복):
    python ml_runner_tspulse.py --raw ... --model ... --loop
"""
import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime


def _need():
    try:
        import numpy, pandas, torch  # noqa
        from tsfm_public.models.tspulse import TSPulseForReconstruction  # noqa
        return True
    except Exception as e:
        print("⚠️ 추론 라이브러리 없음 — 회사 PC 전용")
        print("   pip install \"granite-tsfm[notebooks]\" torch pandas numpy")
        print(f"   ({type(e).__name__}: {e})")
        return False


def level(s):
    return '위험' if s >= 0.7 else '경계' if s >= 0.5 else '관심' if s >= 0.3 else '안전'


class Runner:
    def __init__(self, model_dir):
        import torch
        from tsfm_public.models.tspulse import TSPulseForReconstruction
        sc = json.load(open(os.path.join(model_dir, 'scaler.json'), encoding='utf-8'))
        self.cols = sc['features']
        self.stats = sc['stats']
        self.C = sc['context']
        # 점수 스케일(정상 오차 median/MAD) — train_meta 있으면 사용, 없으면 추론중 보정
        meta_fp = os.path.join(model_dir, 'score_scale.json')
        self.med, self.mad = (0.0, 1.0)
        if os.path.exists(meta_fp):
            m = json.load(open(meta_fp, encoding='utf-8'))
            self.med, self.mad = m['median'], m['mad']
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = TSPulseForReconstruction.from_pretrained(
            os.path.join(model_dir, 'model')).to(self.device)
        self.model.eval()

    def score_latest(self, raw_fp):
        """raw 에서 최근 context 창 → 마지막 분 anomaly_score. (t까지 과거만)"""
        import numpy as np
        import pandas as pd
        import torch
        # 최근 context*2 분만 읽어 성능 확보 (전체 안 읽음)
        df = pd.read_csv(raw_fp, encoding='utf-8-sig')
        tcol = 'CRT_TM' if 'CRT_TM' in df.columns else df.columns[0]
        df[tcol] = pd.to_datetime(df[tcol].astype(str).str[:16], errors='coerce')
        df = df.dropna(subset=[tcol]).sort_values(tcol)
        # 분 단위 마지막 context 구간
        df = df.drop_duplicates(subset=[tcol], keep='last').tail(self.C)
        if len(df) < self.C:
            return None, None, f"창 부족 ({len(df)}/{self.C}분)"
        for c in self.cols:
            if c not in df.columns:
                df[c] = np.nan
        X = df[self.cols].apply(pd.to_numeric, errors='coerce').ffill().fillna(0.0)
        Xn = np.zeros((self.C, len(self.cols)), dtype='float32')
        for j, c in enumerate(self.cols):
            s = self.stats[c]
            Xn[:, j] = (X[c].values - s['median']) / s['iqr']
        with torch.no_grad():
            xb = torch.tensor(Xn[None, :, :]).to(self.device)   # (1,C,ch)
            out = self.model(past_values=xb)
            recon = out.reconstruction_outputs if hasattr(out, 'reconstruction_outputs') else out[1]
            err = float(((recon[0, -1, :] - xb[0, -1, :]) ** 2).mean().cpu())
        z = (err - self.med) / (1.4826 * self.mad) if self.mad else err
        score = 1.0 / (1.0 + pow(2.718281828, -z))
        t_last = df[tcol].iloc[-1]
        return t_last, score, None


def append_row(outdir, t, score):
    os.makedirs(outdir, exist_ok=True)
    fp = os.path.join(outdir, f"{t.strftime('%Y%m%d')}_anomaly.csv")
    new = not os.path.exists(fp)
    with open(fp, 'a', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        if new:
            w.writerow(['datetime', 'anomaly_score', 'ml_level'])
        w.writerow([t.strftime('%Y-%m-%d %H:%M'), f'{score:.4f}', level(score)])
    return fp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', required=True)
    ap.add_argument('--model', default='./out_ml/tspulse')
    ap.add_argument('--outdir', default='./ml_predict')
    ap.add_argument('--loop', action='store_true')
    ap.add_argument('--interval', type=int, default=60)
    a = ap.parse_args()

    print("=" * 60)
    print("ml_runner_tspulse — 실시간 이상점수 (룰베이스 병행)")
    print("=" * 60)
    if not _need():
        sys.exit(2)

    runner = Runner(a.model)
    print(f"[모델] context {runner.C}분 · {len(runner.cols)}피처 · device {runner.device}")

    def once():
        t, score, err = runner.score_latest(a.raw)
        if err:
            print(f"  ⚠️ {err}")
            return
        fp = append_row(a.outdir, t, score)
        print(f"  {t.strftime('%m-%d %H:%M')}  score {score:.3f} [{level(score)}]  → {os.path.basename(fp)}")

    if a.loop:
        print(f"[운영] {a.interval}초 간격 반복 (Ctrl+C 종료)")
        while True:
            try:
                once()
                time.sleep(a.interval)
            except KeyboardInterrupt:
                print("\n종료."); break
            except Exception as e:
                print(f"  ⚠️ 오류(계속): {e}")
                time.sleep(a.interval)
    else:
        once()
        print("🎉 1회 완료 (운영 반복은 --loop)")


if __name__ == '__main__':
    main()
