#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2 — ML이 선행지표를 예측하고, CUSUM을 미래로 투영한다
=======================================================
구버전 실패 원인: Chronos-2 가 '반송시간'(급변하는 결과지표)을 예측 → lead 1분.
새 설계: Chronos-2 가 '선행지표'(완만한 원인지표)를 예측 → CUSUM 미래 투영 → lead↑

    [선행지표 이력]  ──Chronos-2──▶  [선행지표 미래 H분]
           │                              │
           ▼                              ▼
    CUSUM 현재값 C_now  ────────▶  C_future(h) = 미래 h분의 CUSUM
                                          │
                                          ▼
                            "h분 뒤 CUSUM 임계 돌파 예상" = lead h분 경보

왜 되는가:
  1. 선행지표(컨베이어·리프터 큐)는 완만 → ML 예측 잘 됨
  2. 선행지표 자체가 이미 10분 앞섬 (EDA corr +0.43 @ t+10)
  3. CUSUM 자체 lead(8.4분) + ML 예측분(H분) 이 더해짐

경보 단계:
  3 = 현재 CUSUM 이 이미 임계 초과 (지금 위험)
  2 = 미래 CUSUM 이 h분 내 임계 돌파 예상 (선제 경보, lead=h)
  0 = 없음

사용:
  python v2_forecast_cusum.py --data "RAW6/*.CSV" --model chronos_2 --device cuda \
      --horizon 10 --stride 1 --out act_v2.csv
  python score.py --actions act_v2.csv --data "RAW6/*.CSV" --threshold 16.7 --pre 20 --gap 10
"""
from __future__ import annotations

import argparse
import csv
import math

from data_loader import load_any

# ── 선행지표 = CUSUM 감지기 대상 (원인지표) ──
#   각 항목: (컬럼, CUSUM임계, 라벨)
INDICATORS = [
    ("M14.QUE.CNV.SOUTHCURRENTQCNT", 600.0, "남측"),
    ("M14.QUE.CNV.NORTHCURRENTQCNT", 600.0, "북측"),
    ("M16HUB.STRATE.ALL.FABSTORAGERATIO", 300.0, "허브"),
    ("M16HUB.QUE.TIME.AVGTOTALTIME1MIN", 40.0, "브릿지"),
]
TARGET = "M16HUB.QUE.TIME.AVGTOTALTIME1MIN"   # 기록용(실제 반송시간)

BASE_WIN = 120      # 기준선 창(분)
K = 0.5             # 여유계수
MIN_PERIODS = 15


# ──────────────────────────────────────────────────────────────
# 예측기 (배치) — Chronos-2 는 여러 시계열을 한 번에 예측 가능
# ──────────────────────────────────────────────────────────────
class BatchForecaster:
    """선행지표 여러 개를 한 번의 호출로 예측. 실패 시 baseline 폴백."""

    def __init__(self, model_path="chronos_2", device=None):
        self.pipe = None
        self.backend = "baseline-ewma"
        self._err = None
        try:
            from chronos import Chronos2Pipeline
            from forecaster import _resolve_model, _auto_device
            mp = _resolve_model(model_path)
            dev = device or _auto_device()
            self.pipe = Chronos2Pipeline.from_pretrained(mp, device_map=dev)
            self.backend = mp.split("/")[-1].rstrip("/")
            self.device = dev
        except Exception as e:
            self._err = repr(e)
            from forecaster import BaselineForecaster
            self._fb = BaselineForecaster()

    def predict_batch(self, contexts, horizon):
        """contexts: [[float...], ...] → [{'q10':[..],'q50':[..],'q90':[..]}, ...]"""
        if self.pipe is None:
            return [self._fb.predict(c, horizon) for c in contexts]
        try:
            import torch
            # 길이 통일 (뒤쪽 정렬)
            L = min(len(c) for c in contexts)
            ctx = torch.tensor([c[-L:] for c in contexts], dtype=torch.float32)
            qs, _ = self.pipe.predict_quantiles(
                context=ctx, prediction_length=horizon,
                quantile_levels=[0.1, 0.5, 0.9])
            out = []
            for s in range(qs.shape[0]):
                arr = qs[s].tolist()          # [horizon][3]
                out.append({"q10": [float(r[0]) for r in arr],
                            "q50": [float(r[1]) for r in arr],
                            "q90": [float(r[2]) for r in arr]})
            return out
        except Exception as e:
            self._err = repr(e)
            from forecaster import BaselineForecaster
            fb = BaselineForecaster()
            return [fb.predict(c, horizon) for c in contexts]


# ──────────────────────────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────────────────────────
def ffill(vals):
    out, last = [], None
    for v in vals:
        if v is not None and math.isfinite(v):
            last = v
        out.append(last if last is not None else 0.0)
    return out


def med_sd(window):
    n = len(window)
    if n == 0:
        return 0.0, 0.0
    s = sorted(window)
    med = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    m = sum(window) / n
    sd = (sum((v - m) ** 2 for v in window) / n) ** 0.5 if n > 1 else 0.0
    return med, sd


def grade(ratio):
    if ratio < 1.0:
        return ""
    return "초위험" if ratio >= 2.5 else "위험" if ratio >= 1.5 else "경계"


# ──────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="V2: ML 선행지표 예측 + CUSUM 미래투영")
    ap.add_argument("--data", required=True, nargs="+")
    ap.add_argument("--model", default="chronos_2")
    ap.add_argument("--device", default=None)
    ap.add_argument("--horizon", type=int, default=10, help="ML 예측 지평(분)")
    ap.add_argument("--stride", type=int, default=1, help="평가 간격(분)")
    ap.add_argument("--context", type=int, default=180, help="예측 입력 길이(분)")
    ap.add_argument("--k", type=float, default=K, help="CUSUM 여유계수")
    ap.add_argument("--scale", type=float, default=1.0,
                    help="CUSUM 임계 배율 (낮추면 민감=lead↑, 헛울림↑)")
    ap.add_argument("--gate-daytime", action="store_true",
                    help="경계 등급은 주간(08~19)만 인정 (헛울림↓)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cols = [c for c, _, _ in INDICATORS]
    sd = load_any(args.data, cols + [TARGET, "CRT_TM"])
    times = sd.times
    N = len(times)
    series = {c: ffill(sd.signal(c)) for c in cols}
    tgt = sd.signal(TARGET)

    f = BatchForecaster(args.model, args.device)
    print("=" * 70)
    print(" V2 — Chronos-2 선행지표 예측 → CUSUM 미래투영")
    print(f" backend: {f.backend} | 지평 {args.horizon}분 | stride {args.stride}")
    print(f" 선행지표 {len(INDICATORS)}개: {[lab for _,_,lab in INDICATORS]}")
    print(f" 데이터 {N}분  {times[0]} ~ {times[-1]}")
    if f.pipe is None:
        print(f" ⚠ 실모델 로드 실패 → baseline 폴백: {f._err}")
    print("=" * 70)

    # CUSUM 현재값을 증분으로 유지 (전 이력 누적)
    C = {c: 0.0 for c in cols}
    rows = []
    n_pred_alarm = n_now_alarm = 0

    for t in range(N):
        # 1) 현재 CUSUM 갱신 (과거 창으로 기준선)
        stats = {}
        for c in cols:
            past = series[c][max(0, t - BASE_WIN):t]
            if len(past) >= MIN_PERIODS:
                base, s = med_sd(past)
            else:
                base, s = series[c][t], 0.0
            stats[c] = (base, s)
            C[c] = max(0.0, C[c] + (series[c][t] - base - args.k * s))

        # 2) 현재 이미 초과? (stage 3)
        now_hit = []
        for (c, thr, lab) in INDICATORS:
            r = C[c] / (thr * args.scale)
            g = grade(r)
            if g:
                if args.gate_daytime and g == "경계" and not (8 <= times[t].hour <= 19):
                    continue
                now_hit.append((lab, g, r))

        # 3) ML 예측 → CUSUM 미래 투영 (stage 2, lead 확보)
        pred_hit = []
        if t % max(1, args.stride) == 0 and t >= 10:
            lo = max(0, t - args.context)
            ctxs = [series[c][lo:t + 1] for c in cols]
            fcs = f.predict_batch(ctxs, args.horizon)
            for idx, (c, thr, lab) in enumerate(INDICATORS):
                base, s = stats[c]
                thr_eff = thr * args.scale
                # q50(중앙) 경로로 투영 — 보수적으로 q90 도 함께 볼 수 있음
                cf = C[c]
                for h, v in enumerate(fcs[idx]["q50"], start=1):
                    cf = max(0.0, cf + (v - base - args.k * s))
                    if cf >= thr_eff:
                        pred_hit.append((lab, h, cf / thr_eff))
                        break

        # 4) 단계 판정
        if now_hit:
            now_hit.sort(key=lambda z: z[2], reverse=True)
            lab, g, r = now_hit[0]
            stage, lead, prob = 3, "", min(1.0, r / 2.5)
            rec = f"현재 CUSUM {lab} {g}(x{r:.2f})"
            dirn = lab
            n_now_alarm += 1
        elif pred_hit:
            pred_hit.sort(key=lambda z: z[1])       # 가장 이른 돌파
            lab, h, r = pred_hit[0]
            stage, lead, prob = 2, h, min(1.0, 0.5 + 0.5 * min(1.0, r - 1.0))
            rec = f"ML예측: {lab} CUSUM {h}분 뒤 돌파 예상"
            dirn = lab
            n_pred_alarm += 1
        else:
            stage, lead, prob, rec, dirn = 0, "", 0.0, "정상", ""

        rows.append([times[t].strftime("%Y-%m-%d %H:%M:%S"),
                     tgt[t] if tgt[t] is not None else "",
                     stage, f"{stage}단계", round(prob, 3), lead,
                     "", "", "", "", dirn, rec])

        if t % 5000 == 0:
            print(f"  진행 {t}/{N} ...")

    with open(args.out, "w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["datetime", "signal_value", "stage", "stage_name",
                    "exceed_prob", "lead_min", "center_adjust", "reserve_adjust",
                    "tail_upper", "tail_lower", "dir", "recommendation"])
        w.writerows(rows)

    print(f"\n■ 저장: {args.out}")
    print(f"   ML예측 선제경보(stage2) {n_pred_alarm}분 | 현재초과(stage3) {n_now_alarm}분")
    if f.pipe is None:
        print("   ※ baseline 폴백 결과 — 실모델로 다시 돌리세요.")


if __name__ == "__main__":
    main()
