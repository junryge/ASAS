#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
count_capacity.py - 리프터 근처 HID 구간 '용량(capacity) / 혼잡도' (1분 단위)

HID_INOUT 로그의 IN(TO_HIDID)/OUT(FROM_HIDID) 으로 각 HID 의 '현재 점유 차량수'를
시간순으로 추적하고, HID 용량(Vehicle_Max) 대비 혼잡도(%)를 1분 단위로 산출.

입력:
  LOGPRESSO_HID_INOUT_*.csv      (FROM_HIDID/TO_HIDID/VHL_ID/_time)
  리프터_근처HID4.csv             (Lifter -> 근처HID4)
  HID_Zone_Master_*.csv          (Zone_ID -> Vehicle_Max, Vehicle_Precaution)

규칙:
  점유 = 그 HID 에 들어와서(IN) 아직 안 나간(OUT) 차량 수 (차량 단위, 중복없음)
  분당값 = 그 분 동안의 '최대 점유'(peak)
  혼잡도% = peak / Vehicle_Max * 100

사용법:
  python count_capacity.py LOGPRESSO_HID_INOUT_*.csv 리프터_근처HID4.csv HID_Zone_Master_M16A_BR.csv 용량.csv
  python count_capacity.py ... HID_Zone_Master_M16A_BR.csv --at "2026-04-21 14:04"
"""
import sys, os, csv
from collections import defaultdict


def main():
    if len(sys.argv) < 4:
        print(__doc__); sys.exit(1)
    inout, map_csv, hid_master = sys.argv[1:4]
    at = None; out = "용량_혼잡도_1분.csv"
    if "--at" in sys.argv:
        at = sys.argv[sys.argv.index("--at") + 1]
    elif len(sys.argv) > 4 and not sys.argv[4].startswith("--"):
        out = sys.argv[4]

    # 리프터 -> HID, 경계mm
    lifter_zone = {}; lifter_mm = {}
    with open(map_csv, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            lifter_zone[r["Lifter"]] = r["근처HID4"].strip()
            lifter_mm[r["Lifter"]] = (r.get("경계mm") or "").strip()

    # HID -> 용량(Vehicle_Max), 주의(Vehicle_Precaution)
    zmax = {}; zpre = {}
    with open(hid_master, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            z = r["Zone_ID"].strip()
            try: zmax[z] = int(r.get("Vehicle_Max") or 0)
            except ValueError: pass
            try: zpre[z] = int(r.get("Vehicle_Precaution") or 0)
            except ValueError: pass

    # 이벤트 시간순 -> HID별 점유 추적, 분당 peak
    events = []
    with open(inout, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            events.append((r["_time"], r["FROM_HIDID"].strip(), r["TO_HIDID"].strip(), r["VHL_ID"]))
    events.sort()

    occ = defaultdict(set)                  # hid -> 현재 점유 차량
    peak = defaultdict(lambda: defaultdict(int))   # minute -> hid -> peak 점유
    for t, fr, to, v in events:
        m = t[:16]
        if fr: occ[fr].discard(v)
        if to: occ[to].add(v)
        for hid in (fr, to):
            if hid:
                c = len(occ[hid])
                if c > peak[m][hid]:
                    peak[m][hid] = c

    minutes = sorted(peak)
    fab = lambda lf: "M16" if lf[0] == "6" else ("M14" if lf[0] == "4" else "?")

    def ratio(c, z):
        mx = zmax.get(z, 0)
        return round(100.0 * c / mx, 1) if mx else ""

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["시각", "Lifter", "FAB", "근처HID", "경계mm", "점유차량수", "용량Max", "혼잡도%"])
        for m in minutes:
            for lf in sorted(lifter_zone):
                z = lifter_zone[lf]
                c = peak[m].get(z, 0)
                w.writerow([m, lf, fab(lf), z, lifter_mm.get(lf, ""), c, zmax.get(z, ""), ratio(c, z)])

    if at:
        print(f"=== {at} · 리프터 근처 HID 용량/혼잡도 (peak 점유) ===")
        rows = [(lf, lifter_zone[lf], peak.get(at, {}).get(lifter_zone[lf], 0)) for lf in lifter_zone]
        for lf, z, c in sorted(rows, key=lambda x: -x[2]):
            print(f"  {lf:10} HID{z:3}  점유 {c:3}/{zmax.get(z,'?')}  ({ratio(c,z)}%)")
    else:
        print(f"분 구간 {len(minutes)}개 ({minutes[0]} ~ {minutes[-1]}) · 리프터 {len(lifter_zone)}기")
    print(f"\n저장: {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
