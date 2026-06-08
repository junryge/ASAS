#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hidinout_1min.py - LOGPRESSO_HID_INOUT 파일만으로 'HID별 1분당 차량수' 집계

입력: LOGPRESSO_HID_INOUT_20260421.csv  (이 파일 하나만 사용)
규칙: 1분 단위 / HID별 / 차량(VHL_ID) 중복제거
      IN  = TO_HIDID   (그 HID 로 들어온 차량)
      OUT = FROM_HIDID (그 HID 에서 나간 차량)

사용법:
  python hidinout_1min.py LOGPRESSO_HID_INOUT_20260421.csv [출력.csv]
  # 특정 분만:
  python hidinout_1min.py LOGPRESSO_HID_INOUT_20260421.csv --at "2026-04-21 14:04"
  # 특정 HID만 (쉼표구분):
  python hidinout_1min.py LOGPRESSO_HID_INOUT_20260421.csv --hid 33,34,3
"""
import sys, os, csv
from collections import defaultdict


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    inout = sys.argv[1]
    at = None; hid_filter = None; out = "HID_1분_차량수.csv"
    if "--at" in sys.argv:
        at = sys.argv[sys.argv.index("--at") + 1]
    if "--hid" in sys.argv:
        hid_filter = set(x.strip() for x in sys.argv[sys.argv.index("--hid") + 1].split(","))
    for a in sys.argv[2:]:
        if a.endswith(".csv"):
            out = a

    in_veh = defaultdict(set)    # (minute, HID) -> {VHL}  진입
    out_veh = defaultdict(set)   # (minute, HID) -> {VHL}  진출
    with open(inout, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            minute = r["_time"][:16]
            if at and minute != at:
                continue
            to = r["TO_HIDID"].strip(); fr = r["FROM_HIDID"].strip(); v = r["VHL_ID"]
            if not hid_filter or to in hid_filter:
                in_veh[(minute, to)].add(v)
            if not hid_filter or fr in hid_filter:
                out_veh[(minute, fr)].add(v)

    keys = sorted(set(in_veh) | set(out_veh))
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["시각", "HID", "IN_차량수", "OUT_차량수"])
        for m, hid in keys:
            w.writerow([m, hid, len(in_veh.get((m, hid), ())), len(out_veh.get((m, hid), ()))])

    if at:
        print(f"=== {at} · HID별 차량수 (IN=진입, 중복제거) ===")
        rows = sorted(set(h for (mm, h) in keys if mm == at),
                      key=lambda h: -len(in_veh.get((at, h), ())))
        for h in rows:
            print(f"  HID{h:4} IN {len(in_veh.get((at,h),())):3}대  OUT {len(out_veh.get((at,h),())):3}대")
    else:
        mins = sorted(set(m for m, _ in keys))
        print(f"분 구간 {len(mins)}개 ({mins[0]} ~ {mins[-1]}) · HID {len(set(h for _,h in keys))}종")
    print(f"\n저장: {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
