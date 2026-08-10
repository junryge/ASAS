#!/usr/bin/env python3
"""
AMHS Sentinel_M16BR — 데이터 확보 (독립 실행)

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
        # ★실패 사유를 반드시 보여준다 (조용히 끝나면 원인을 알 수 없다)
        print(f"  ❌ 조회 실패 — {err.get('reason')}")
        if err.get("query_sent"):
            print(f"     쿼리: {err['query_sent'][:200]}")
        if err.get("response_preview"):
            print(f"     응답: {err['response_preview'][:300]}")
        print(f"     → 원인 확인: python collect.py --debug")
        return {"ok": False, "error": err.get("reason"), "rows": 0, "written": 0}
    warn = err.get("reason") if err else None

    if not rows:
        print(f"  ⚠️ 조회 0행 — 그 구간에 데이터가 없습니다 "
              f"(테이블 {cfg.get('table_name')}, 구간 {from_dt}~{to_dt})")

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


def _debug(cfg: dict, date: str | None = None) -> int:
    """저장이 안 될 때 — 조회부터 저장까지 단계별로 어디서 막히는지 보여준다."""
    from lp_client import build_url, load_api_key, query_sized
    from lp_query import build
    from store_csv import append_rows, day_path

    now = datetime.now()
    d = ("".join(ch for ch in str(date) if ch.isdigit())[:8]) if date else now.strftime("%Y%m%d")
    f_s, t_s = f"{d}000000", (now.strftime(FMT) if d == now.strftime("%Y%m%d") else f"{d}235959")
    tc = cfg.get("amos", {}).get("base_time_col", "datetime")

    print(f"■ 1. 설정")
    print(f"   주소   : {cfg.get('logpresso_base')}")
    print(f"   테이블 : {cfg.get('table_name')}")
    key = load_api_key(cfg)
    print(f"   키     : {(key[:8]+'…') if key else '❌ 없음 (api_key.txt)'}")
    print(f"   구간   : {f_s} ~ {t_s}")

    lpql = build(from_dt=f_s, to_dt=t_s, sort=cfg.get("query", {}).get("sort_col") or None)
    print(f"\n■ 2. 기본 조회")
    print(f"   LPQL : {lpql}")
    print(f"   URL  : {build_url(lpql, cfg)[:150]}…")
    rows, size, err = query_sized(lpql, verbose=False)
    if err:
        print(f"   ❌ 실패 — {err.get('reason')}")
        if err.get("response_preview"):
            print(f"      응답: {err['response_preview'][:200]}")
        return 1
    print(f"   ✅ {len(rows)}행 / {size/1048576:.2f}MB")
    if not rows:
        print("   ⚠️ 0행 — 그 구간에 데이터가 없습니다 (날짜/테이블 확인)")
        return 1
    cols = list(rows[0].keys())
    print(f"   컬럼 {len(cols)}개")
    print(f"   시각 컬럼 '{tc}' → {rows[0].get(tc)!r}  (파싱: {parse_dt(rows[0].get(tc))})")
    if parse_dt(rows[0].get(tc)) is None:
        print(f"   ❌ 시각 파싱 실패 → config.amos.base_time_col 을 실제 컬럼으로 바꾸세요")
        print(f"      후보: {[c for c in cols if 'time' in c.lower() or 'date' in c.lower()]}")
        return 1

    print(f"\n■ 3. AMOS 2개 테이블")
    for which in ("bottleneck", "queue"):
        spec = cfg["amos"][which]
        q2 = build(spec["table"], from_dt=f_s, to_dt=t_s,
                   search=cfg["amos"].get("filter") or None, sort=spec.get("time_col"))
        ar, _sz, e2 = query_sized(q2, verbose=False)
        if e2:
            print(f"   ❌ {spec['table']} — {e2.get('reason')}")
            continue
        have = list(ar[0].keys()) if ar else []
        need = [spec["downward_col"], spec["upward_col"]]
        miss = [c for c in need if c not in have]
        print(f"   {'✅' if not miss else '⚠️'} {spec['table']} — {len(ar)}행"
              + (f", 컬럼 없음 {miss}" if miss else ""))
        if miss and have:
            print(f"      실제 컬럼: {have}")

    print(f"\n■ 4. 조인 + 저장")
    merged, warn = fetch_amos(from_dt=f_s, to_dt=t_s)
    if warn:
        print(f"   ⚠️ {warn.get('reason')}")
    mins = {parse_dt(r.get(tc)).strftime("%H:%M") for r in merged if parse_dt(r.get(tc))}
    print(f"   병합 {len(merged)}행 ({len(mins)}분)")
    saved = append_rows(merged, cfg)
    print(f"   저장 결과: {saved}")
    print(f"   파일: {day_path(d, cfg)}")

    import os as _os
    p = day_path(d, cfg)
    if _os.path.isfile(p):
        n = sum(1 for _ in open(p, encoding="utf-8-sig")) - 1
        print(f"   ✅ 파일 {n}행 / {_os.path.getsize(p)/1024:.1f}KB")
    else:
        print(f"   ❌ 파일이 만들어지지 않음 — 쓰기 권한 확인")
        return 1
    return 0


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
    p.add_argument("--debug", action="store_true",
                   help="★저장이 안 될 때 — 단계별로 어디서 막히는지 출력")
    a = p.parse_args(argv)

    if a.debug:
        return _debug(cfg, a.date[0] if a.date else None)

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
