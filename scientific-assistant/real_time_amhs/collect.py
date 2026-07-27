#!/usr/bin/env python3
"""
AMHS Sentinel — 데이터 확보 (독립 실행)

로그프레소에서 실제 데이터를 가져와 날짜별 CSV 에 1분 한 줄씩 쌓는다.
관제 서버(server.py) 없이 이것만 돌려도 데이터는 확보된다.

    data/20260727_TOTAL.CSV        ← 기본 데이터 + AMOS 4컬럼

사용법:
    python collect.py                      # 오늘 00:00 ~ 현재까지 확보 (기본)
    python collect.py --date 20260727      # 그 날 하루치 전체
    python collect.py --from 20260727000000 --to 20260727120000
    python collect.py --loop               # 1분마다 계속 수집 (관제 없이 수집만)
    python collect.py --date 20260725 --date 20260726   # 여러 날
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta

from lp_client import load_config, parse_dt
from lp_query import fetch_amos
from store_csv import day_path, last_time, list_days

FMT = "%Y%m%d%H%M%S"


def collect(from_dt: str, to_dt: str, cfg: dict | None = None,
            verbose: bool = True) -> dict:
    """구간 데이터를 가져와 날짜 CSV 에 누적. (확보 결과 dict)"""
    cfg = cfg or load_config()
    t0 = time.time()

    rows, err = fetch_amos(from_dt=from_dt, to_dt=to_dt)
    if err and not err.get("warn"):
        return {"ok": False, "error": err.get("reason"), "rows": 0, "written": 0}
    warn = err.get("reason") if err else None

    from store_csv import append_rows
    saved = append_rows(rows or [], cfg)

    # 실제로 몇 분이 채워졌는지 (1분 한 줄 기준)
    tc = cfg.get("amos", {}).get("base_time_col", "datetime")
    minutes = {parse_dt(r.get(tc)).strftime("%Y%m%d%H%M")
               for r in (rows or []) if parse_dt(r.get(tc))}

    res = {"ok": True, "rows": len(rows or []), "minutes": len(minutes),
           "written": saved["written"], "skipped": saved["skipped"],
           "files": saved["files"], "warn": warn,
           "elapsed_s": round(time.time() - t0, 1)}
    if verbose:
        print(f"  조회 {res['rows']}행 ({res['minutes']}분) · "
              f"신규 {res['written']}행 저장 · 중복 {res['skipped']}"
              + (f" → {', '.join(res['files'])}" if res["files"] else "")
              + f"  [{res['elapsed_s']}초]")
        if warn:
            print(f"  ⚠️ {warn}")
    return res


def collect_day(day: str, cfg: dict | None = None) -> dict:
    """하루치 확보. 오늘이면 현재 시각까지만."""
    d = "".join(ch for ch in str(day) if ch.isdigit())[:8]
    start = datetime.strptime(d, "%Y%m%d")
    now = datetime.now()
    end = min(start.replace(hour=23, minute=59, second=59), now)
    if start > now:
        return {"ok": False, "error": f"{d} 는 미래 날짜", "rows": 0, "written": 0}
    print(f"[{d}] {start:%H:%M} ~ {end:%H:%M} 확보 중…")
    return collect(start.strftime(FMT), end.strftime(FMT), cfg)


def collect_today_catchup(cfg: dict | None = None) -> dict:
    """오늘 — 마지막 저장 시각부터 현재까지만 (없으면 00:00부터)."""
    cfg = cfg or load_config()
    now = datetime.now()
    day = now.strftime("%Y%m%d")
    last = last_time(day, cfg)
    start = last if last else now.replace(hour=0, minute=0, second=0, microsecond=0)
    gap = int((now - start).total_seconds() // 60)
    print(f"[{day}] {start:%H:%M} ~ {now:%H:%M} ({gap}분) 확보 중…")
    return collect(start.strftime(FMT), now.strftime(FMT), cfg)


def main(argv=None) -> int:
    cfg = load_config()
    p = argparse.ArgumentParser(
        description="로그프레소 데이터 확보 → 날짜별 CSV 누적",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("사용법:")[-1])
    p.add_argument("--date", action="append", metavar="YYYYMMDD",
                   help="그 날 하루치 (여러 번 지정 가능)")
    p.add_argument("--from", dest="from_dt", metavar="yyyyMMddHHmmss")
    p.add_argument("--to", dest="to_dt", metavar="yyyyMMddHHmmss")
    p.add_argument("--loop", action="store_true",
                   help="계속 수집 (수집 주기마다, Ctrl+C 로 중단)")
    p.add_argument("--interval", type=int,
                   default=cfg.get("query", {}).get("poll_interval_s", 60),
                   help="--loop 주기(초). 기본 60 = 1분")
    p.add_argument("--list", action="store_true", help="확보된 날짜 파일 목록")
    a = p.parse_args(argv)

    print(f"로그프레소 : {cfg.get('logpresso_base')}  ({cfg.get('table_name')})")
    print(f"AMOS      : {cfg['amos']['bottleneck']['table']} + {cfg['amos']['queue']['table']}")
    print(f"저장 위치  : {day_path(datetime.now().strftime('%Y%m%d'), cfg)}")
    print("─" * 62)

    if a.list:
        days = list_days(cfg)
        if not days:
            print("확보된 데이터 없음")
            return 0
        total = 0
        for d in days:
            print(f"  {d['file']}  {d['rows']:>6}행  {d['bytes']/1024:8.1f}KB")
            total += d["rows"]
        print(f"  {'합계':<22} {total:>6}행")
        return 0

    if a.from_dt and a.to_dt:
        return 0 if collect(a.from_dt, a.to_dt, cfg).get("ok") else 1

    if a.date:
        ok = True
        for d in a.date:
            ok &= bool(collect_day(d, cfg).get("ok"))
        return 0 if ok else 1

    if a.loop:
        print(f"1회 {a.interval}초 주기로 계속 수집합니다 (Ctrl+C 중단)\n")
        try:
            while True:
                collect_today_catchup(cfg)
                time.sleep(a.interval)
        except KeyboardInterrupt:
            print("\n중단됨")
            return 0

    return 0 if collect_today_catchup(cfg).get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
