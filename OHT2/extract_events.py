#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_events.py - 큰 OHT 위치로그(296MB)에서 '리프터 근방 진입 이벤트'만 추출 -> 작은 CSV

296MB 를 딱 1회 스캔해서 리프터 근방 HID 진입 이벤트만 남긴다 (수 MB로 축소).
그 다음부턴 count_1min.py 로 가볍게 1분 집계.

사용법:
  python extract_events.py <oht_data.zip|csv> <HID_Zone_Master.csv> <리프터_HID.csv> [출력.csv]

예:
  python extract_events.py 20260421.zip HID_Zone_Master_M16A_BR.csv 리프터_HID.csv 리프터근방_진입이벤트_BR_20260421.csv
"""
import sys, os, re, csv, zipfile, io
from collections import defaultdict


def open_oht(path):
    if path.endswith(".zip"):
        zf = zipfile.ZipFile(path)
        cands = [n for n in zf.namelist() if "oht_data" in n.lower() and n.endswith(".csv")]
        name = None
        for n in cands:
            if "EDGE" in io.TextIOWrapper(zf.open(n), "utf-8").readline():
                name = n; break
        name = name or (cands[0] if cands else None)
        if not name:
            raise FileNotFoundError("zip 안에 oht_data csv 없음")
        return csv.reader(io.TextIOWrapper(zf.open(name), "utf-8"))
    return csv.reader(open(path, encoding="utf-8", errors="replace"))


def main():
    if len(sys.argv) < 4:
        print(__doc__); sys.exit(1)
    oht, hid_master, lifter_csv = sys.argv[1:4]
    out = sys.argv[4] if len(sys.argv) > 4 else "리프터근방_진입이벤트.csv"

    # HID 진입 lane edge -> HID
    edges = defaultdict(set)
    with open(hid_master, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            zid = r["Zone_ID"].strip()
            for seg in (r.get("IN_Lanes") or "").split(";"):
                m = re.match(r'\s*(\d+)\s*→\s*(\d+)', seg)
                if m: edges[f"{m.group(1)}_{m.group(2)}"].add(zid)

    # 리프터 근방 HID 집합
    lifter_hids = set()
    with open(lifter_csv, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            for h in r["근방HID_Zone번호"].split(";"):
                if h.strip(): lifter_hids.add(h.strip())

    target = {e: (hs & lifter_hids) for e, hs in edges.items() if (hs & lifter_hids)}
    print(f"대상 진입 엣지: {len(target)}개")

    of = open(out, "w", newline="", encoding="utf-8-sig")
    w = csv.writer(of); w.writerow(["_time", "VEHICLE", "HID"])
    r = open_oht(oht); h = next(r)
    ie, it, iv = h.index("EDGE"), h.index("_time"), h.index("VEHICLE")
    kept = total = 0
    for row in r:
        total += 1
        if len(row) <= ie: continue
        hs = target.get(row[ie])
        if hs:
            for hid in hs:
                w.writerow([row[it], row[iv], hid]); kept += 1
    of.close()
    print(f"원본 {total:,}행 -> 추출 {kept:,}행")
    print(f"저장: {os.path.abspath(out)} ({os.path.getsize(out):,} bytes)")


if __name__ == "__main__":
    main()
