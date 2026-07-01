#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
count_lifter_inout.py - 리프터 근처 HID 구역의 '근처차량수' (1분 단위, 17기)

각 리프터의 근처 HID4 구역에 대해, 1분 동안 그 구역을 거친(진입 TO 또는 진출 FROM)
고유 차량 수를 집계한다. 개수만 본다 — 포화도/용량은 카파시 스킬(count_capacity.py).

입력:
  LOGPRESSO_HID_INOUT_*.csv   (_time / FROM_HIDID / TO_HIDID / VHL_ID)
  리프터_근처HID4.csv          (Lifter -> 근처HID4, 경계mm)

출력 컬럼:
  시각, Lifter, FAB, 근처HID, 경계mm, 근처차량수
   - 근처차량수 = 그 1분에 그 HID4 구역을 거친(FROM 또는 TO 가 그 HID) 고유 차량(VHL_ID) 수
   - 같은 HID4 를 근처로 두는 리프터는 같은 값.

사용법:
  python count_lifter_inout.py LOGPRESSO_HID_INOUT_*.csv 리프터_근처HID4.csv 결과.csv
  python count_lifter_inout.py LOGPRESSO_HID_INOUT_*.csv 리프터_근처HID4.csv --at "2026-04-21 14:04"
"""
import sys, os, csv
from collections import defaultdict


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    inout, map_csv = sys.argv[1:3]
    at = None; out = "결과.csv"
    if "--at" in sys.argv:
        at = sys.argv[sys.argv.index("--at") + 1]
    elif len(sys.argv) > 3 and not sys.argv[3].startswith("--"):
        out = sys.argv[3]

    # 리프터 -> 근처HID, 경계mm
    lifter_zone = {}; lifter_mm = {}
    with open(map_csv, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            lifter_zone[r["Lifter"]] = r["근처HID4"].strip()
            lifter_mm[r["Lifter"]] = (r.get("경계mm") or "").strip()

    # (분, HID) -> 그 분에 그 HID 를 거친 고유 차량 집합 (FROM 또는 TO)
    near = defaultdict(set)
    with open(inout, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            m = (r.get("_time") or "")[:16]          # 'YYYY-MM-DD HH:MM'
            if not m:
                continue
            v = (r.get("VHL_ID") or "").strip()
            fr = (r.get("FROM_HIDID") or "").strip()
            to = (r.get("TO_HIDID") or "").strip()
            if fr:
                near[(m, fr)].add(v)
            if to:
                near[(m, to)].add(v)

    minutes = sorted(set(m for m, _ in near))
    fab = lambda lf: "M16" if lf[:1] == "6" else ("M14" if lf[:1] == "4" else "?")

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["시각", "Lifter", "FAB", "근처HID", "경계mm", "근처차량수"])
        for m in minutes:
            for lf in sorted(lifter_zone):
                z = lifter_zone[lf]
                n = len(near.get((m, z), ()))
                w.writerow([m, lf, fab(lf), z, lifter_mm.get(lf, ""), n])

    if at:
        print(f"=== {at} · 리프터 근처 HID 근처차량수 ===")
        rows = [(lf, lifter_zone[lf], len(near.get((at, lifter_zone[lf]), ()))) for lf in lifter_zone]
        for lf, z, n in sorted(rows, key=lambda x: -x[2]):
            print(f"  {lf:10} HID{z:>3}  근처차량 {n:3}대")
    else:
        span = f" ({minutes[0]} ~ {minutes[-1]})" if minutes else ""
        print(f"분 구간 {len(minutes)}개{span} · 리프터 {len(lifter_zone)}기")
    print(f"\n저장: {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
