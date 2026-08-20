#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data.py — 수집기 CSV 로딩 · 이동평균 · 사건(라벨) 정의
=====================================================
설계 근거: RAW/FINDINGS_RAW분석.md
  순간값 임계초과의 78%가 1분 블립(예측 불가 노이즈) → 이동평균으로 전환.
  10분 이동평균 기준 정체는 61일간 34건(월 17건), 평균 30분, 최장 156분.

핵심 개념 3개
  · signal    : 원본 분당 값 (M16HUB 반송시간 등)
  · smoothed  : 이동평균 (예측 타깃 · 판정 기준) — 블립 제거
  · event     : 큰 정체 = smoothed >= 임계 AND 지속 >= min_dur

표준 라이브러리만 사용 (pandas 불필요).
"""
from __future__ import annotations

import csv
import glob
import math
from collections import deque
from dataclasses import dataclass
from datetime import datetime

TIME_COL = "CRT_TM"
TIME_FMT = "%Y-%m-%d %H:%M:%S"

# 기본 타깃 = HUB 평균 반송시간
TARGET = "M16HUB.QUE.TIME.AVGTOTALTIME1MIN"

# 선행지표(원인 지표) — 보조 감지·covariate 용
LEADING = [
    "M14.QUE.CNV.SOUTHCURRENTQCNT",        # 남측 컨베이어 큐
    "M14.QUE.CNV.NORTHCURRENTQCNT",        # 북측 컨베이어 큐
    "M16HUB.STRATE.ALL.FABSTORAGERATIO",   # FAB 저장률
    "M16HUB.QUE.ALL.CURRENTQCOMPLETED",    # 완료 반송량 (줄면 적체)
    "M16HUB.QUE.M14TOM16.MESCURRENTQCNT",  # M14→M16 큐
]


def _to_float(s):
    if s is None:
        return None
    s = s.strip()
    if not s or s.lower() in ("nan", "inf", "-inf", "null", "none"):
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    return f if math.isfinite(f) else None


# ──────────────────────────────────────────────────────────────
# 시계열 컨테이너
# ──────────────────────────────────────────────────────────────
class Series:
    """시각 정렬된 다신호 시계열."""

    def __init__(self, times: list[datetime], cols: dict[str, list]):
        self.times = times
        self.cols = cols

    def __len__(self):
        return len(self.times)

    def get(self, name) -> list:
        return self.cols.get(name, [None] * len(self.times))

    def has(self, name) -> bool:
        return name in self.cols

    def filled(self, name) -> list[float]:
        """포워드필 (결측을 직전 값으로) — 모델 입력용."""
        out, last = [], None
        for v in self.get(name):
            if v is not None:
                last = v
            out.append(last if last is not None else 0.0)
        return out

    def slice_dates(self, start: str, end: str) -> "Series":
        """'YYYY-MM-DD' 양끝 포함으로 자른다 (학습/평가 분리)."""
        s = datetime.strptime(start, "%Y-%m-%d")
        e = datetime.strptime(end, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        idx = [i for i, t in enumerate(self.times) if s <= t <= e]
        return Series([self.times[i] for i in idx],
                      {c: [v[i] for i in idx] for c, v in self.cols.items()})


def load(patterns, want: list[str] | None = None) -> Series:
    """
    CSV 여러 개(글롭 포함)를 시각순 병합 로드.
      load(["RAW_APRMAY/*.CSV"])            → 전체 컬럼
      load(["RAW6/*.CSV"], [TARGET, ...])   → 지정 컬럼만 (빠름)
    """
    if isinstance(patterns, str):
        patterns = [patterns]
    files = []
    for p in patterns:
        m = sorted(glob.glob(p))
        files.extend(m if m else [p])
    if not files:
        raise FileNotFoundError(f"CSV 없음: {patterns}")

    times: list[datetime] = []
    cols: dict[str, list] = {}
    for path in files:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rd = csv.DictReader(f)
            fields = rd.fieldnames or []
            keep = [c for c in (want or fields) if c in fields and c != TIME_COL]
            base = len(times)
            for c in keep:
                cols.setdefault(c, [None] * base)
            local = {c: [] for c in keep}
            n_local = 0
            for row in rd:
                try:
                    dt = datetime.strptime(row.get(TIME_COL, "").strip(), TIME_FMT)
                except ValueError:
                    continue
                times.append(dt)
                n_local += 1
                for c in keep:
                    local[c].append(_to_float(row.get(c)))
            for c in keep:
                cols[c].extend(local[c])
            # 이 파일에 없던 기존 컬럼은 결측으로 길이 맞춤
            for c in cols:
                if len(cols[c]) < len(times):
                    cols[c].extend([None] * (len(times) - len(cols[c])))

    order = sorted(range(len(times)), key=lambda i: times[i])
    return Series([times[i] for i in order],
                  {c: [v[i] for i in order] for c, v in cols.items()})


# ──────────────────────────────────────────────────────────────
# 이동평균 — 예측 타깃 & 판정 기준
# ──────────────────────────────────────────────────────────────
def moving_avg(x: list[float], window: int) -> list[float]:
    """과거만 보는 이동평균 (인과적, 미래 누수 없음)."""
    out, dq, s = [], deque(), 0.0
    for v in x:
        dq.append(v); s += v
        if len(dq) > window:
            s -= dq.popleft()
        out.append(s / len(dq))
    return out


def percentile(vals: list[float], q: float) -> float:
    s = sorted(v for v in vals if v is not None)
    if not s:
        return float("nan")
    return s[min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))]


# ──────────────────────────────────────────────────────────────
# 사건(라벨) — "큰 정체"만
# ──────────────────────────────────────────────────────────────
@dataclass
class Event:
    start: int          # 인덱스
    end: int
    t_start: datetime
    t_end: datetime
    duration: int       # 분
    peak_smoothed: float
    peak_raw: float


def find_events(times, smoothed, raw, threshold: float,
                min_duration: int = 10, gap: int = 10) -> list[Event]:
    """
    큰 정체 사건 추출.
      · smoothed >= threshold 인 구간
      · gap 분 이내 간격은 같은 사건으로 병합
      · 지속 min_duration 분 미만은 버림 (블립 제거)
    """
    spans, st, prev = [], None, None
    for i, v in enumerate(smoothed):
        if v >= threshold:
            if st is None:
                st = i
            prev = i
        elif st is not None and (i - prev) > gap:
            spans.append((st, prev)); st = None
    if st is not None:
        spans.append((st, prev))

    events = []
    for b, e in spans:
        dur = e - b + 1
        if dur < min_duration:
            continue
        events.append(Event(
            start=b, end=e, t_start=times[b], t_end=times[e], duration=dur,
            peak_smoothed=max(smoothed[b:e + 1]),
            peak_raw=max((raw[i] for i in range(b, e + 1)
                          if raw[i] is not None), default=float("nan")),
        ))
    return events


def learn_threshold(smoothed: list[float], pct: float = 0.99) -> float:
    """학습기간 smoothed 분위수를 임계로 채택 (손으로 정하지 않음)."""
    return round(percentile(smoothed, pct), 3)


# ──────────────────────────────────────────────────────────────
# 학습 결과 저장/로드 — 한 번 학습해 두고 계속 재사용
# ──────────────────────────────────────────────────────────────
CONFIG_NAME = "model_config.json"


def learn(patterns, window=10, pct=0.99, min_duration=10, gap=10) -> dict:
    """
    학습기간에서 판정 기준을 산출한다 (Chronos-2 는 zero-shot 이라 가중치 학습 없음).
    산출: 임계 · 분포통계 · 학습기간 심각사건 요약 → dict (그대로 저장해 재사용)
    """
    sd = load(patterns, [TARGET] + LEADING + [TIME_COL])
    sm = moving_avg(sd.filled(TARGET), window)
    thr = learn_threshold(sm, pct)
    evs = find_events(sd.times, sm, sd.get(TARGET), thr, min_duration, gap)
    durs = [e.duration for e in evs]
    days = max(1, (sd.times[-1] - sd.times[0]).days + 1)
    return {
        "target": TARGET,
        "window": window,
        "pct": pct,
        "min_duration": min_duration,
        "gap": gap,
        "threshold": thr,
        "smoothed_p50": round(percentile(sm, 0.50), 3),
        "smoothed_p95": round(percentile(sm, 0.95), 3),
        "smoothed_p99": round(percentile(sm, 0.99), 3),
        "smoothed_max": round(max(sm), 3),
        "train_span": f"{sd.times[0]:%Y-%m-%d} ~ {sd.times[-1]:%Y-%m-%d}",
        "train_rows": len(sd),
        "train_days": days,
        "train_events": len(evs),
        "train_events_per_month": round(len(evs) / max(1, days / 30.0), 1),
        "train_event_mean_duration": round(sum(durs) / len(durs), 1) if durs else 0,
        "train_event_max_duration": max(durs) if durs else 0,
        "leading_available": [c for c in LEADING if sd.has(c)],
    }


def save_config(cfg: dict, path: str = CONFIG_NAME):
    import json
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_config(path: str = CONFIG_NAME) -> dict:
    import json
    with open(path, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="데이터·사건 구조 확인")
    ap.add_argument("--data", required=True, nargs="+")
    ap.add_argument("--window", type=int, default=10)
    ap.add_argument("--pct", type=float, default=0.99)
    ap.add_argument("--min-duration", type=int, default=10)
    a = ap.parse_args()

    sd = load(a.data, [TARGET] + LEADING + [TIME_COL])
    raw = sd.get(TARGET)
    sm = moving_avg(sd.filled(TARGET), a.window)
    thr = learn_threshold(sm, a.pct)
    evs = find_events(sd.times, sm, raw, thr, a.min_duration)

    print(f"데이터 {len(sd)}분  {sd.times[0]} ~ {sd.times[-1]}")
    print(f"{a.window}분 이동평균 p{a.pct*100:.1f} 임계 = {thr}")
    print(f"큰 정체 사건: {len(evs)}건 (지속 {a.min_duration}분+)")
    if evs:
        durs = [e.duration for e in evs]
        print(f"  평균 {sum(durs)/len(durs):.0f}분 · 최장 {max(durs)}분")
        print("  상위 10건 (피크순):")
        for e in sorted(evs, key=lambda x: -x.peak_smoothed)[:10]:
            print(f"    {e.t_start:%m-%d %H:%M}~{e.t_end:%H:%M} "
                  f"({e.duration:3d}분) 평균피크 {e.peak_smoothed:.1f} "
                  f"순간최고 {e.peak_raw:.1f}")
    print(f"\n선행지표 사용가능: {[c for c in LEADING if sd.has(c)]}")
