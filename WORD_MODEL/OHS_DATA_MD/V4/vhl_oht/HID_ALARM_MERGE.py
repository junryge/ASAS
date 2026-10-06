#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HID_ALARM_MERGE.py — 날짜별로 나뉜 과거 판정 결과를 한 파일로 합치기 (과거 데이터 평가용)

  읽기   HID_BOTTLENECK/PAST/{FAB}/HID_BOTTLENECK_{FAB}_YYYYMMDD.csv   (HID_VHL_OHT.py FAB 날짜 날짜 로 만든 파일)
  저장   HID_BOTTLENECK/PAST/{FAB}/HID_BOTTLENECK_{FAB}_{시작}_{끝}_MERGED.csv ★FAB 마다 — 뽑은 CSV 와 칸 똑같이 날짜만 이어 붙임
         HID_BOTTLENECK/PAST/MERGED_{FAB|ALL}_{시작}_{끝}.csv         ★평가용 — 전체 분 (정상 포함), FAB 모두 한 표
           칸은 아래 알람합침과 같다
         HID_BOTTLENECK/PAST/ALARM_MERGED_{FAB|ALL}_{시작}_{끝}.csv     경계 · 위험 · 초위험 줄만
           FAB, 날짜, 시간, ALARM_KR, ALARM_EN, HID_ZONE, HID_section, OHT_report, OHT_missing, OHT_JAM,
           ZONE_STOP, ZONE_VHL, VHL_MAX, ZONE_OCC, HID_ZONE_2, HID_ZONE_3
           (FAB 마다 다른 칸 이름 {FAB}_OHT_missing 등을 OHT_missing 으로 맞추고 FAB 칸을 붙인다)
         HID_BOTTLENECK/PAST/ALARM_EVENTS_{FAB|ALL}_{시작}_{끝}.csv
           알람이 이어진 분들을 사건 하나로 묶은 것 (참고용)
           FAB, 시작, 끝, 분, 최고 ALARM_KR, 최고 ALARM_EN, 경계 분, 위험 분, 초위험 분, 시작 HID_ZONE, 가장 많은 HID_ZONE,
           최대 missing, 최대 JAM   (★HT_STOP 은 숨김 — 칸 없음)

  실행
    python HID_ALARM_MERGE.py                              전부 (FAB 5개 · 있는 날짜 다)
    python HID_ALARM_MERGE.py M16HUB                       FAB 하나 · 있는 날짜 다
    python HID_ALARM_MERGE.py M16HUB 20260912 20260929     FAB · 날짜 구간
    python HID_ALARM_MERGE.py ALL 20260912 20260929        FAB 5개 · 날짜 구간
    python HID_ALARM_MERGE.py ALL 20260929                 하루

  ALARM 이 정상인 줄은 빼고, 시간 순(FAB → 날짜 → 시간)으로 정렬한다. 다른 .py 필요 없음.
"""
import csv
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAST_DIR = HERE / "HID_BOTTLENECK" / "PAST"     # HID_VHL_OHT.py 과거 판정 결과 폴더
FABS = ["M14", "M14B", "M16A", "M16B", "M16HUB"]
ALARMS = ["경계", "위험", "초위험"]
GAP_MIN = 1                     # 알람 사이가 이 분보다 벌어지면 다른 사건 (1 = 바로 이어진 분만 한 사건)

ALARM_EN_OF = {"정상": "NORMAL", "경계": "WARNING", "위험": "DANGER", "초위험": "CRITICAL"}
OUT_COLS = ["FAB", "날짜", "시간", "ALARM_KR", "ALARM_EN", "HID_ZONE", "HID_section",
            "OHT_report", "OHT_missing", "OHT_JAM",
            "ZONE_STOP", "ZONE_VHL", "VHL_MAX", "ZONE_OCC", "HID_ZONE_2", "HID_ZONE_3"]


def usage(msg=""):
    if msg:
        print(msg)
    print("사용법: python HID_ALARM_MERGE.py [FAB|ALL] [시작날짜 YYYYMMDD] [끝날짜 YYYYMMDD]")
    sys.exit(1)


def parse_args(argv):
    fabs, days = FABS, []
    toks = list(argv)
    if toks and not toks[0].replace("-", "").isdigit():
        f0 = toks.pop(0).upper()
        if f0 not in ("ALL", "전체"):
            fabs = [x.strip() for x in f0.split(",") if x.strip()]
            bad = [x for x in fabs if x not in FABS]
            if bad:
                usage(f"모르는 FAB {bad} — 가능: {' '.join(FABS)} 또는 ALL")
    if len(toks) > 2:
        usage()
    for t in toks:
        try:
            days.append(datetime.strptime(t.replace("-", ""), "%Y%m%d"))
        except ValueError:
            usage(f"날짜 형식 오류: {t} (YYYYMMDD)")
    d0 = min(days) if days else None
    d1 = max(days) if days else None
    return fabs, d0, d1


def merge_raw(fab, d0, d1):
    """그 FAB 날짜별 CSV 를 칸 그대로 이어 붙인다 → (헤더, 줄, 파일 수)"""
    d = PAST_DIR / fab
    if not d.exists():
        return None, [], 0
    head, rows, n = None, [], 0
    for p in sorted(d.glob(f"HID_BOTTLENECK_{fab}_*.csv")):
        m = re.fullmatch(rf"HID_BOTTLENECK_{fab}_(\d{{8}})\.csv", p.name)
        if not m:
            continue
        day = datetime.strptime(m.group(1), "%Y%m%d")
        if (d0 and day < d0) or (d1 and day > d1):
            continue
        with open(p, encoding="utf-8-sig") as f:
            rd = csv.reader(f)
            h = next(rd, None)
            if not h:
                continue
            if head is None:
                head = h
            elif h != head:                         # 예전 형식 파일 (칸 다름) 은 건너뜀
                print(f"  {p.name}: 칸이 달라 건너뜀 (예전 형식 — 다시 뽑아 주세요)")
                continue
            rows += list(rd)
            n += 1
    rows.sort(key=lambda r: (r[0], r[1]))
    return head, rows, n


def read_fab(fab, d0, d1):
    """그 FAB 의 날짜별 파일 → 모든 줄 (공통 칸 이름)"""
    d = PAST_DIR / fab
    if not d.exists():
        return [], 0
    out, nfile = [], 0
    for p in sorted(d.glob(f"HID_BOTTLENECK_{fab}_*.csv")):
        m = re.fullmatch(rf"HID_BOTTLENECK_{fab}_(\d{{8}})\.csv", p.name)       # 날짜 파일만 (분 단위 --range 파일 제외)
        if not m:
            continue
        day = datetime.strptime(m.group(1), "%Y%m%d")
        if (d0 and day < d0) or (d1 and day > d1):
            continue
        nfile += 1
        with open(p, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                g = lambda k: (r.get(k) or "").strip()
                out.append({
                    "FAB": fab, "날짜": g("날짜"), "시간": g("시간"),
                    "ALARM": g("ALARM_KR") or g("ALARM"),            # 예전 파일(ALARM 한 칸)도 읽는다
                    "HID_ZONE": g("HID_ZONE"), "HID_section": g("HID_section"),
                    "OHT_report": g(f"{fab}_OHT_report"), "OHT_missing": g(f"{fab}_OHT_missing"),
                    "OHT_JAM": g(f"{fab}_OHT_JAM"),
                    "ZONE_STOP": g("ZONE_STOP"), "ZONE_VHL": g("ZONE_VHL"), "VHL_MAX": g("VHL_MAX"),
                    "ZONE_OCC": g("ZONE_OCC"), "HID_ZONE_2": g("HID_ZONE_2"), "HID_ZONE_3": g("HID_ZONE_3"),
                })
    return out, nfile


def _out(r):
    """줄 → 저장 칸 (ALARM 을 ALARM_KR · ALARM_EN 두 칸으로)"""
    return {**r, "ALARM_KR": r["ALARM"], "ALARM_EN": ALARM_EN_OF.get(r["ALARM"], "NORMAL")}


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def events(rows):
    """이어진 알람 분들을 사건 하나로"""
    out, cur = [], None
    for r in rows:
        t = datetime.strptime(f"{r['날짜']} {r['시간']}", "%Y-%m-%d %H:%M")
        if cur and cur["FAB"] == r["FAB"] and (t - cur["끝t"]) <= timedelta(minutes=GAP_MIN):
            cur["끝t"] = t
            cur["rows"].append(r)
        else:
            if cur:
                out.append(cur)
            cur = {"FAB": r["FAB"], "시작t": t, "끝t": t, "rows": [r]}
    if cur:
        out.append(cur)
    res = []
    for e in out:
        rs = e["rows"]
        cnt = Counter(x["ALARM"] for x in rs)
        top = max(rs, key=lambda x: ALARMS.index(x["ALARM"]))["ALARM"]
        zones = Counter(x["HID_ZONE"] for x in rs if x["HID_ZONE"] not in ("", "0"))
        res.append([e["FAB"], f"{e['시작t']:%Y-%m-%d %H:%M}", f"{e['끝t']:%Y-%m-%d %H:%M}", len(rs), top, ALARM_EN_OF[top],
                    cnt.get("경계", 0), cnt.get("위험", 0), cnt.get("초위험", 0),
                    rs[0]["HID_ZONE"] or 0, zones.most_common(1)[0][0] if zones else 0,
                    max(_int(x["OHT_missing"]) for x in rs), max(_int(x["OHT_JAM"]) for x in rs)])
    return res


def main():
    fabs, d0, d1 = parse_args(sys.argv[1:])
    if not PAST_DIR.exists():
        sys.exit(f"과거 판정 폴더(PAST)가 없습니다: {PAST_DIR}\n"
                 f"먼저  python HID_VHL_OHT.py <FAB|ALL> <시작날짜> [끝날짜]  로 과거 판정을 만드세요.")
    allrows, files = [], 0
    for fab in fabs:
        r, n = read_fab(fab, d0, d1)
        allrows += r
        files += n
        na = sum(1 for x in r if x["ALARM"] in ALARMS)
        print(f"  {fab:6} 파일 {n}개 · {len(r)}분 · 알람 {na}분")
    allrows.sort(key=lambda r: (FABS.index(r["FAB"]), r["날짜"], r["시간"]))
    rows = [r for r in allrows if r["ALARM"] in ALARMS]
    if not files:
        sys.exit("합칠 파일이 없습니다 — FAB · 날짜를 확인하세요.")

    days = sorted({r["날짜"] for r in allrows})
    s = (d0.strftime("%Y%m%d") if d0 else (days[0].replace("-", "") if days else "전체"))
    e = (d1.strftime("%Y%m%d") if d1 else (days[-1].replace("-", "") if days else "전체"))
    who = fabs[0] if len(fabs) == 1 else ("ALL" if fabs == FABS else "_".join(fabs))
    tag = f"{who}_{s}_{e}"

    p0 = PAST_DIR / f"MERGED_{tag}.csv"                      # ★평가용 — 전체 분
    with open(p0, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(_out(r) for r in allrows)

    p1 = PAST_DIR / f"ALARM_MERGED_{tag}.csv"
    with open(p1, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(_out(r) for r in rows)

    ev = events(rows)
    p2 = PAST_DIR / f"ALARM_EVENTS_{tag}.csv"
    with open(p2, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["FAB", "시작", "끝", "분", "최고 ALARM_KR", "최고 ALARM_EN", "경계 분", "위험 분", "초위험 분",
                    "시작 HID_ZONE", "가장 많은 HID_ZONE", "최대 missing", "최대 JAM"])
        w.writerows(ev)

    cnt = Counter(r["ALARM"] for r in rows)
    print(f"  합계: 경계 {cnt.get('경계', 0)} · 위험 {cnt.get('위험', 0)} · 초위험 {cnt.get('초위험', 0)}분 "
          f"· 사건 {len(ev)}개")
    print(f"  → {p0}   (전체 {len(allrows)}분 — 평가용, FAB 모두 한 표)")
    for fab in fabs:                                 # FAB 마다 — 뽑은 CSV 와 칸 똑같이 한 파일
        head, raw, n = merge_raw(fab, d0, d1)
        if not n:
            continue
        pf = PAST_DIR / fab / f"HID_BOTTLENECK_{fab}_{s}_{e}_MERGED.csv"
        with open(pf, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(head)
            w.writerows(raw)
        print(f"  → {pf}   ({fab} 날짜 {n}개 · {len(raw)}분, 칸 그대로)")
    print(f"  → {p1}")
    print(f"  → {p2}")


if __name__ == "__main__":
    main()
