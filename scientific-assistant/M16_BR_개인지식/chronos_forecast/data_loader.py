#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실 수집기 CSV 로더 (M16 HUBROOM raw)
=====================================
수집기가 매분 뱉는 raw CSV (265 메트릭 + CRT_TM 시각) 를 읽어
신호별 시계열로 정렬한다.

특징:
  · CRT_TM 파싱 (예: "2026-04-01 00:00:00")
  · null/빈칸/non-finite(NaN,inf) → None 으로 정규화 (하류에서 스킵)
  · 여러 날 CSV 를 이어붙여 학습(Apr~May)/평가(June) 구간 슬라이스 지원
  · 표준 라이브러리만 사용 (pandas 불필요)
"""
from __future__ import annotations

import csv
import glob
import math
import os
from datetime import datetime


TIME_COL = "CRT_TM"
TIME_FMT = "%Y-%m-%d %H:%M:%S"


def _to_float(s):
    if s is None:
        return None
    s = s.strip()
    if s == "" or s.lower() in ("nan", "inf", "-inf", "null", "none"):
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    return f if math.isfinite(f) else None


class SeriesData:
    """시각 정렬된 다신호 시계열 컨테이너."""

    def __init__(self, times: list[datetime], columns: dict[str, list]):
        self.times = times
        self.columns = columns  # {col_name: [float|None, ...]}

    def __len__(self):
        return len(self.times)

    def signal(self, name: str) -> list:
        return self.columns.get(name, [None] * len(self.times))

    def available(self, names: list[str]) -> list[str]:
        return [n for n in names if n in self.columns]

    def slice_by_date(self, start: str, end: str) -> "SeriesData":
        """
        start/end: "YYYY-MM-DD" (양끝 포함, end는 그 날 23:59 까지).
        학습/평가 구간 나누기에 사용.
        """
        s = datetime.strptime(start, "%Y-%m-%d")
        e = datetime.strptime(end, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        idx = [i for i, t in enumerate(self.times) if s <= t <= e]
        times = [self.times[i] for i in idx]
        cols = {c: [v[i] for i in idx] for c, v in self.columns.items()}
        return SeriesData(times, cols)


def load_csv(path: str, wanted: list[str] | None = None) -> SeriesData:
    """
    단일 CSV 로드. wanted=None 이면 전체 컬럼, 아니면 지정 신호만.
    """
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        keep = None
        if wanted is not None:
            keep = [c for c in wanted if c in fields]
        times: list[datetime] = []
        cols: dict[str, list] = {c: [] for c in (keep if keep else fields) if c != TIME_COL}
        for row in reader:
            t = row.get(TIME_COL, "").strip()
            try:
                dt = datetime.strptime(t, TIME_FMT)
            except ValueError:
                continue
            times.append(dt)
            for c in cols:
                cols[c].append(_to_float(row.get(c)))
    return SeriesData(times, cols)


def load_glob(pattern: str, wanted: list[str] | None = None) -> SeriesData:
    """
    여러 CSV(예: 날짜별 파일)를 시각순으로 이어붙여 로드.
    pattern 예: "data/2026*.CSV"
    """
    paths = sorted(glob.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"매칭되는 CSV 없음: {pattern}")
    merged_times: list[datetime] = []
    merged_cols: dict[str, list] = {}
    for p in paths:
        sd = load_csv(p, wanted)
        for c, vals in sd.columns.items():
            merged_cols.setdefault(c, [])
            # 이전 파일 컬럼 길이 맞추기 (컬럼이 파일마다 다를 때 안전)
        # 길이 정렬을 위해 재구성
        base = len(merged_times)
        merged_times.extend(sd.times)
        allcols = set(merged_cols) | set(sd.columns)
        for c in allcols:
            merged_cols.setdefault(c, [None] * base)
            add = sd.columns.get(c, [None] * len(sd.times))
            merged_cols[c].extend(add)
        # 이번에 없던 기존 컬럼도 길이 맞춤
        for c in merged_cols:
            if len(merged_cols[c]) < len(merged_times):
                merged_cols[c].extend([None] * (len(merged_times) - len(merged_cols[c])))
    # 시각순 정렬
    order = sorted(range(len(merged_times)), key=lambda i: merged_times[i])
    times = [merged_times[i] for i in order]
    cols = {c: [v[i] for i in order] for c, v in merged_cols.items()}
    return SeriesData(times, cols)


# HUBROOM 핵심 신호 (04_임계값.md 근거)
CORE_SIGNALS = [
    "M16HUB.QUE.TIME.AVGTOTALTIME1MIN",
    "M16HUB.QUE.M14TOM16.MESCURRENTQCNT",
    "M16HUB.STRATE.ALL.FABSTORAGERATIO",
    "M14.QUE.LOAD.AVGLOADTIME1MIN",
    "M16A.QUE.LOAD.AVGLOADTIME1MIN",
    "M16B.QUE.LOAD.AVGLOADTIME1MIN",
]


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("사용법: python3 data_loader.py <CSV경로>")
        raise SystemExit(1)
    sd = load_csv(path, CORE_SIGNALS + ["CRT_TM"])
    print(f"로드 {len(sd)}행  {sd.times[0]} ~ {sd.times[-1]}")
    print(f"사용 가능 신호: {sd.available(CORE_SIGNALS)}")
    for c in sd.available(CORE_SIGNALS):
        vals = [v for v in sd.signal(c) if v is not None]
        if vals:
            vs = sorted(vals)
            n = len(vs)
            print(f"  {c}: n={n} p50={vs[n//2]:.2f} p95={vs[int(n*0.95)]:.2f} p99={vs[min(n-1,int(n*0.99))]:.2f} max={max(vs):.2f}")
