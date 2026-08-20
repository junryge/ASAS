#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chronos-Bolt 예측 어댑터 (HUBROOM 데드락 예측 PoC)
====================================================
핵심 신호를 N분 앞서 확률(q10/q50/q90) 예측한다.

설계 원칙:
  · 실제 배포에서는 amazon/chronos-bolt-base 를 로드해 zero-shot 예측.
  · 이 컨테이너/오프라인 환경에서 모델을 못 받으면 자동으로 baseline 예측기로 폴백
    (파이프라인·가드레일·평가 하네스를 모델 없이도 end-to-end 검증 가능).
  · 두 경로 모두 동일한 인터페이스를 반환 → 상위 코드는 어느 쪽인지 몰라도 됨.

반환 형식 (predict 한 번 호출):
  {
    "q10": [h개], "q50": [h개], "q90": [h개],   # 미래 h스텝 분위수
    "backend": "chronos-bolt-base" | "baseline-ewma"
  }
"""
from __future__ import annotations

import math
from collections import deque
from typing import Sequence

# 기본 예측 분위수
DEFAULT_QUANTILES = (0.1, 0.5, 0.9)


class BaselineForecaster:
    """
    모델 없이 돌아가는 경량 확률 예측기 (폴백/오프라인 검증용).

    방식:
      · center: EWMA(지수가중이동평균) + 최근 추세(선형 기울기) 외삽
      · spread: 최근 잔차 표준편차를 지평(h)에 따라 sqrt(h) 로 확장
                → 멀리 볼수록 구간이 넓어지는 자연스러운 불확실성
    이건 Chronos 대체가 아니라 '파이프라인이 도는지' 확인용 기준선이다.
    """

    def __init__(self, alpha: float = 0.35):
        self.alpha = alpha

    def predict(self, context: Sequence[float], horizon: int,
                quantiles: Sequence[float] = DEFAULT_QUANTILES) -> dict:
        ctx = [float(v) for v in context if v is not None and math.isfinite(float(v))]
        if len(ctx) < 3:
            last = ctx[-1] if ctx else 0.0
            return {"q10": [last] * horizon, "q50": [last] * horizon,
                    "q90": [last] * horizon, "backend": "baseline-ewma"}

        # EWMA level
        level = ctx[0]
        for v in ctx[1:]:
            level = self.alpha * v + (1 - self.alpha) * level

        # 최근 추세(마지막 min(len,10)개 선형 기울기)
        tail = ctx[-min(len(ctx), 10):]
        n = len(tail)
        xs = list(range(n))
        mx = sum(xs) / n
        my = sum(tail) / n
        denom = sum((x - mx) ** 2 for x in xs) or 1.0
        slope = sum((xs[i] - mx) * (tail[i] - my) for i in range(n)) / denom

        # 잔차 표준편차 (1스텝 차분 기준)
        diffs = [ctx[i] - ctx[i - 1] for i in range(1, len(ctx))]
        md = sum(diffs) / len(diffs)
        var = sum((d - md) ** 2 for d in diffs) / max(1, len(diffs) - 1)
        sigma = math.sqrt(max(var, 1e-9))

        # 정규분포 근사 z값 (분위수→z)
        z = {0.1: -1.2816, 0.5: 0.0, 0.9: 1.2816}
        out = {f"q{int(q*100)}": [] for q in quantiles}
        for h in range(1, horizon + 1):
            center = level + slope * h
            spread = sigma * math.sqrt(h)
            for q in quantiles:
                out[f"q{int(q*100)}"].append(center + z.get(q, 0.0) * spread)
        out["backend"] = "baseline-ewma"
        return out


def _resolve_model(model_path: str) -> str:
    """
    로컬에 받아둔 모델 폴더를 자동 감지.
      · model_path 가 실제 폴더면 그대로 사용 (예: ./models/chronos-2)
      · 아니면 흔한 위치(./models/chronos-2, ./chronos-2 ...) 를 탐색
      · 없으면 HF 식별자 문자열 그대로 (온라인 자동 다운로드)
    → 모델을 폴더에 '집어넣기만' 하면 자동으로 로컬본을 씀 (오프라인 OK).
    """
    import os
    if os.path.isdir(model_path):
        return model_path
    base = os.path.basename(model_path)  # 예: chronos-2
    for cand in (f"./models/{base}", f"./{base}", f"models/{base}",
                 "./models/chronos-2", "./chronos-2"):
        if os.path.isdir(cand):
            return cand
    return model_path  # HF 식별자


def _auto_device() -> str:
    """cuda > mps > cpu 순으로 사용 가능한 디바이스 자동 선택."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


class ChronosForecaster:
    """
    Chronos 예측 계층 (Forecast). 최신 Chronos-2 우선, chronos-bolt 도 지원.
    문서 구조의 1단: 과거 시계열 → 미래 quantile 분포(q10/q50/q90).
    torch/chronos 미설치 또는 모델 로드 실패 시 BaselineForecaster 로 폴백.

    모델 선택:
      · amazon/chronos-2          (최신, 120M, 다변량·covariate zero-shot 지원,
                                    GIFT-Eval SOTA, chronos-bolt 대비 90%+ 승률)  ← 기본
      · amazon/chronos-bolt-base  (2세대, 205M)
      · amazon/chronos-bolt-tiny  (2세대, 9M, CPU 실시간)

    로더는 Chronos2Pipeline(chronos>=2.0) → BaseChronosPipeline(bolt) → baseline
    순으로 시도한다. 단변량 예측 인터페이스(predict)는 세 경로 모두 동일.
    covariate(다변량) 예측은 forecaster_cov.py 의 predict_df 경로 사용.
    """

    def __init__(self, model_path: str = "amazon/chronos-2",
                 device: str | None = None, torch_dtype=None):
        self.model_path = _resolve_model(model_path)
        self.device = device or _auto_device()
        self._torch_dtype = torch_dtype
        self._pipeline = None
        self._kind = None            # "chronos2" | "bolt"
        self._fallback = BaselineForecaster()
        self._load_error = None
        self._load()

    def _load(self):
        errs = []
        # 1) 최신 Chronos-2 (chronos-forecasting >= 2.0)
        try:
            from chronos import Chronos2Pipeline
            self._pipeline = Chronos2Pipeline.from_pretrained(
                self.model_path, device_map=self.device,
            )
            self._kind = "chronos2"
            self.backend = self.model_path.split("/")[-1]
            return
        except Exception as e:
            errs.append(f"Chronos2Pipeline: {e!r}")
        # 2) chronos-bolt (BaseChronosPipeline)
        try:
            import torch
            from chronos import BaseChronosPipeline
            dtype = self._torch_dtype
            if dtype is None:
                dtype = torch.bfloat16 if self.device == "cuda" else torch.float32
            self._pipeline = BaseChronosPipeline.from_pretrained(
                self.model_path, device_map=self.device, torch_dtype=dtype,
            )
            self._kind = "bolt"
            self.backend = self.model_path.split("/")[-1]
            return
        except Exception as e:
            errs.append(f"BaseChronosPipeline: {e!r}")
        # 3) 폴백
        self._pipeline = None
        self.backend = "baseline-ewma"
        self._load_error = " | ".join(errs)

    @property
    def using_real_model(self) -> bool:
        return self._pipeline is not None

    def predict(self, context: Sequence[float], horizon: int,
                quantiles: Sequence[float] = DEFAULT_QUANTILES) -> dict:
        if self._pipeline is None:
            return self._fallback.predict(context, horizon, quantiles)
        try:
            import torch
            ctx = [float(v) for v in context
                   if v is not None and math.isfinite(float(v))]
            qs, _ = self._pipeline.predict_quantiles(
                context=torch.tensor(ctx, dtype=torch.float32),
                prediction_length=horizon,
                quantile_levels=list(quantiles),
            )
            # qs shape: [num_series=1, horizon, num_quantiles]
            arr = qs[0].tolist()
            out = {f"q{int(q*100)}": [] for q in quantiles}
            for step in arr:
                for qi, q in enumerate(quantiles):
                    out[f"q{int(q*100)}"].append(float(step[qi]))
            out["backend"] = self.backend
            return out
        except Exception:
            return self._fallback.predict(context, horizon, quantiles)


def make_forecaster(prefer_real: bool = True, **kw):
    """팩토리: 실모델 우선 시도, 실패 시 baseline."""
    if prefer_real:
        return ChronosForecaster(**kw)
    return BaselineForecaster()


if __name__ == "__main__":
    # 스모크 테스트: 상승 추세 신호에 대한 예측
    import random
    random.seed(0)
    sig = [5 + 0.05 * i + random.gauss(0, 0.3) for i in range(120)]
    f = make_forecaster(prefer_real=True, device="cpu")
    r = f.predict(sig, horizon=10)
    print(f"backend={r['backend']}")
    print("q10:", [round(x, 2) for x in r["q10"]])
    print("q50:", [round(x, 2) for x in r["q50"]])
    print("q90:", [round(x, 2) for x in r["q90"]])
