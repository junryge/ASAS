#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
count_1min.py - 리프터 근방 HID 차량수 (1분 단위, 리프터별, 차량 중복제거)

입력: 리프터근방_진입이벤트_BR_*.csv  (296MB OHT로그에서 추출한 작은 파일)
      리프터_HID.csv                  (리프터 -> 근방 HID 매핑)

규칙:
  - 1분 단위로 집계
  - 한 리프터의 여러 HID에 같은 차량이 들어와도 그 분(分)에 1대로 계산 (중복제거)

사용법:
  python count_1min.py 리프터근방_진입이벤트_BR_20260421.csv 리프터_HID.csv [출력.csv]
  # 특정 분만 보고 싶으면:
  python count_1min.py ... 리프터_HID.csv --at "2026-04-21 14:04"
"""
import sys, os, csv
from collections import defaultdict


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    ev_csv, map_csv = sys.argv[1], sys.argv[2]
    at = None
    out = "리프터근방_차량수_1분.csv"
    if "--at" in sys.argv:
        at = sys.argv[sys.argv.index("--at") + 1]
    elif len(sys.argv) > 3 and not sys.argv[3].startswith("--"):
        out = sys.argv[3]

    # 리프터 -> 근방 HID, HID -> 리프터들
    hid_lifters = defaultdict(set)
    lifters = []
    with open(map_csv, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            lifters.append(r["Lifter"])
            for h in r["근방HID_Zone번호"].split(";"):
                h = h.strip()
                if h: hid_lifters[h].add(r["Lifter"])

    # 진입 이벤트 -> (분, 리프터) 별 차량 집합 (중복제거)
    bucket = defaultdict(set)   # (minute, lifter) -> {VHL}
    with open(ev_csv, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            minute = r["_time"][:16]              # 'YYYY-MM-DD HH:MM'
            if at and minute != at:
                continue
            for lf in hid_lifters.get(r["HID"].strip(), ()):
                bucket[(minute, lf)].add(r["VEHICLE"])

    minutes = sorted(set(m for m, _ in bucket))
    fab = lambda lf: "M16" if lf[0] == "6" else ("M14" if lf[0] == "4" else "?")

    # 출력
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["시각", "Lifter", "FAB", "근방차량수"])
        for m in minutes:
            for lf in sorted(lifters):
                w.writerow([m, lf, fab(lf), len(bucket.get((m, lf), ()))])

    if at:
        print(f"=== {at} · 리프터 근방 차량수 (중복제거) ===")
        rows = [(lf, len(bucket.get((at, lf), ()))) for lf in lifters]
        for lf, c in sorted(rows, key=lambda x: -x[1]):
            print(f"  {lf:10} {c:3}대")
    else:
        print(f"분 구간: {len(minutes)}개  ({minutes[0]} ~ {minutes[-1]})")
    print(f"\n저장: {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
