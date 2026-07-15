#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
학습(Calibration) — Apr~May 에서 임계·covariate 를 데이터로 맞춰 config 저장
============================================================================
※ Chronos-2 는 zero-shot 이라 '신경망 가중치 학습'은 하지 않는다(그게 강점).
   여기서 '학습' = 이 시스템이 학습기간 데이터에서 배우는 것:
     (1) 정상분포 임계값 (손으로 안 정하고 p-분위수로)
     (2) 선행지표 covariate (미래 정체와 상관 높은 컬럼 자동선택)
   결과를 fit_config.json 으로 저장 → 평가(6월) 때 그대로 사용(leakage 없음).

사용:
    python3 fit.py --train "RAW/M16A_HUBROOM_PR_20260401~20260531.CSV" \
                   --signal M16HUB.QUE.TIME.AVGTOTALTIME1MIN \
                   --horizon 10 --pct 0.99 --k-cov 8 \
                   --out fit_config.json

    # RAW 폴더 통째로(여러 파일 병합)도 가능:
    python3 fit.py --train "RAW/*.CSV" --out fit_config.json
"""
from __future__ import annotations

import argparse
import json
import math

from data_loader import load_any, CORE_SIGNALS
from calibrate import percentile


def _ffill(vals):
    out, last = [], None
    for v in vals:
        if v is not None:
            last = v
        out.append(last if last is not None else 0.0)
    return out


def corr_future(x, tgt, lead):
    xs, ys = [], []
    N = len(tgt)
    for t in range(N - lead):
        xs.append(x[t]); ys.append(tgt[t + lead])
    if len(xs) < 30:
        return 0.0
    mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
    sx = math.sqrt(sum((a - mx) ** 2 for a in xs))
    sy = math.sqrt(sum((b - my) ** 2 for b in ys))
    if sx < 1e-9 or sy < 1e-9:
        return 0.0
    return sum((xs[i] - mx) * (ys[i] - my) for i in range(len(xs))) / (sx * sy)


def main():
    ap = argparse.ArgumentParser(description="학습(캘리브레이션): 임계+covariate")
    ap.add_argument("--train", required=True, nargs="+",
                    help="학습 CSV (Apr~May). 파일/여러개/글롭 (예: RAW/*.CSV)")
    ap.add_argument("--signal", default="M16HUB.QUE.TIME.AVGTOTALTIME1MIN")
    ap.add_argument("--horizon", type=int, default=10)
    ap.add_argument("--pct", type=float, default=0.99, help="임계 분위수")
    ap.add_argument("--k-cov", type=int, default=8, help="covariate 개수")
    ap.add_argument("--p-on", type=float, default=0.60)
    ap.add_argument("--p-off", type=float, default=0.35)
    ap.add_argument("--out", default="fit_config.json")
    args = ap.parse_args()

    # 전체 컬럼 로드 (covariate 탐색 위해 wanted=None)
    sd = load_any(args.train, wanted=None)
    if args.signal not in sd.columns:
        raise SystemExit(f"타깃 {args.signal} 가 학습데이터에 없음")
    N = len(sd)
    span = f"{sd.times[0]} ~ {sd.times[-1]} ({N}분)"
    print(f"[학습데이터] {span}")
    if N < 3000:
        print("⚠ 학습 구간이 짧음(<~2일). 정식 학습은 Apr~May 전체 권장.")

    tgt = _ffill(sd.signal(args.signal))

    # (1) 임계 학습 (정상분포 분위수)
    tv = sorted(v for v in sd.signal(args.signal) if v is not None)
    threshold = round(percentile(tv, args.pct), 3)
    print(f"\n[1] 임계 학습: p{args.pct*100:.1f} = {threshold}"
          f"  (p50={percentile(tv,0.5):.2f} p95={percentile(tv,0.95):.2f} max={tv[-1]:.2f})")

    # (2) covariate 학습 (미래 정체와 상관 상위 k)
    scored = []
    for c in sd.columns:
        if c == args.signal:
            continue
        vals = [v for v in sd.signal(c) if v is not None]
        if len(vals) < N * 0.5 or len(set(vals)) < 4:
            continue
        r = corr_future(_ffill(sd.signal(c)), tgt, args.horizon)
        scored.append((abs(r), r, c))
    scored.sort(reverse=True)
    top = scored[:args.k_cov]
    covariates = [c for _, _, c in top]
    print(f"\n[2] 선행지표 covariate 학습 (미래+{args.horizon}분 정체와 상관 상위 {args.k_cov}):")
    for _, r, c in top:
        print(f"    {r:+.2f}  {c}")

    # 자기상관(참고)
    self_corr = corr_future(tgt, tgt, args.horizon)
    print(f"\n    참고: 타깃 자기상관(+{args.horizon}분) = {self_corr:+.2f}")

    # 저장
    config = {
        "signal": args.signal,
        "horizon": args.horizon,
        "threshold": threshold,
        "pct": args.pct,
        "p_on": args.p_on,
        "p_off": args.p_off,
        "covariates": covariates,
        "covariate_corr": {c: round(r, 3) for _, r, c in top},
        "target_autocorr": round(self_corr, 3),
        "train_span": span,
        "train_rows": N,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 학습 완료 → {args.out}")
    print("   평가(6월): python3 run_chronos_sentinel.py --config "
          f"{args.out} --data RAW/JUNE.CSV --device cpu")


if __name__ == "__main__":
    main()
