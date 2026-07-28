#!/usr/bin/env python3
"""
AMHS Sentinel — 로그프레소 쿼리 조회 도구 (독립)

LPQL 빌더 + CLI. 데모스 비의존.

원칙 (logpresso-query 스킬과 동일):
  · 테이블명·컬럼명을 절대 추측하지 않는다. 모르면 --schema 로 먼저 확인한다.
  · 요청하지 않은 필터/정렬/컬럼을 넣지 않는다.
  · 읽기 전용 (lp_client 가 쓰기 명령을 차단).

사용법:
    python lp_query.py --schema                     # 컬럼 목록 확인 (추측 금지용)
    python lp_query.py --recent 10m --limit 100     # 최근 10분 원본
    python lp_query.py --from 20260709000000 --to 20260709235959
    python lp_query.py -q "table duration=1h test_table3 | limit 5"
    python lp_query.py --recent 1h --out rows.csv   # CSV 저장
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta

from lp_client import fetch_columns, load_config, parse_dt, ping, query, query_sized


# ────────────────────────────── LPQL 빌더 ──────────────────────────────
def build(table: str | None = None, *, duration: str | None = None,
          from_dt: str | None = None, to_dt: str | None = None,
          search: str | None = None, fields: list[str] | None = None,
          sort: str | None = None, limit: int | None = None) -> str:
    """LPQL 파이프라인 생성. 지정한 절만 붙인다(추측 금지)."""
    cfg = load_config()
    table = table or cfg.get("table_name", "")
    if not table:
        raise ValueError("테이블명이 없습니다 (config.json table_name)")

    if from_dt and to_dt:
        head = f"table from={from_dt} to={to_dt} {table}"
    else:
        head = f"table duration={duration or cfg.get('query', {}).get('window', '10m')} {table}"

    parts = [head]
    if search:
        parts.append(f"search {search}")
    if fields:
        parts.append("fields " + ", ".join(fields))
    if sort:
        parts.append(f"sort {sort}")
    if limit:
        parts.append(f"limit {int(limit)}")
    return " | ".join(parts)


def recent(window: str | None = None, limit: int | None = None) -> tuple[list[dict] | None, dict | None]:
    """관제 폴링용 — 최근 구간 원본 조회."""
    cfg = load_config()
    q = cfg.get("query", {})
    return query(build(duration=window or q.get("window", "10m"),
                       limit=limit or q.get("limit", 2000)))


FMT = "%Y%m%d%H%M%S"


def query_chunked(from_dt: str, to_dt: str, table: str | None = None,
                  chunk_minutes: int | None = None, sort: str | None = "_time",
                  _depth: int = 0, verbose: bool = True):
    """긴 구간을 청크로 끊어 조회 → 합친다. (rows, err)

    · chunk_minutes 단위로 분할 조회 (기본 config.query.chunk_minutes = 10분)
    · 한 청크 응답이 max_bytes(기본 30MB)를 넘으면 그 구간만 절반으로 재귀 분할
    · 로그프레소 export 가 대용량에서 끊기는 것을 피하기 위한 검증된 방식

    from_dt/to_dt: "yyyyMMddHHmmss"
    """
    cfg = load_config()
    q = cfg.get("query", {})
    table = table or cfg.get("table_name", "")
    chunk_minutes = chunk_minutes or q.get("chunk_minutes", 10)
    max_bytes = q.get("max_bytes", 30 * 1024 * 1024)

    try:
        start, end = datetime.strptime(from_dt, FMT), datetime.strptime(to_dt, FMT)
    except ValueError as e:
        return None, {"reason": f"기간 형식 오류 (yyyyMMddHHmmss): {e}", "query_sent": ""}
    if start >= end:
        return [], None

    # 오프라인(fixture)은 청크마다 같은 파일을 돌려주므로 분할하지 않는다
    if os.getenv("LP_OFFLINE") == "1":
        rows, _sz, err = query_sized(build(table, from_dt=from_dt, to_dt=to_dt, sort=sort),
                                     verbose=False)
        return (None, err) if err else (rows, None)

    step = timedelta(minutes=chunk_minutes)
    out, cur = [], start
    bad = []

    while cur < end:
        nxt = min(cur + step, end)
        f_s, t_s = cur.strftime(FMT), nxt.strftime(FMT)
        lpql = build(table, from_dt=f_s, to_dt=t_s, sort=sort)

        rows, size, err = query_sized(lpql, verbose=False)
        if err:
            # 청크 하나가 실패해도 나머지는 계속 가져온다 (실패분만 기록)
            print(f"[LP] ❌ {f_s}~{t_s} 실패 — {err.get('reason')} → 건너뜀")
            if err.get("response_preview"):
                print(f"[LP]    응답: {err['response_preview'][:150]}")
            bad.append(f"{f_s[8:12]}~{t_s[8:12]}")
            cur = nxt
            continue

        # 30MB 초과 → 해당 구간만 절반으로 재분할 (1초 미만이면 더 못 쪼갬)
        if size > max_bytes and (nxt - cur) > timedelta(seconds=1) and _depth < 12:
            mid = cur + (nxt - cur) / 2
            if verbose:
                print(f"[LP] ✂️ {f_s}~{t_s} {size/1048576:.1f}MB 초과 → 분할")
            for a, b in ((f_s, mid.strftime(FMT)), (mid.strftime(FMT), t_s)):
                sub, serr = query_chunked(a, b, table, chunk_minutes, sort,
                                          _depth + 1, verbose)
                if serr:
                    bad.append(f"{a[8:12]}~{b[8:12]}")
                    continue
                out.extend(sub)
        else:
            if verbose and rows:
                print(f"[LP] ✅ {f_s}~{t_s}  {len(rows):>6}건  {size/1048576:5.1f}MB")
            out.extend(rows)

        cur = nxt

    if _depth == 0:
        tcol = sort or "_time"
        if out and tcol in out[0]:
            out.sort(key=lambda r: str(r.get(tcol) or ""))
        if verbose:
            print(f"[LP] 🏁 총 {len(out)}건"
                  + (f" (실패 구간 {len(bad)}개: {', '.join(bad[:6])}"
                     + ("…" if len(bad) > 6 else "") + ")" if bad else ""))
        # 전부 실패했을 때만 에러로 본다
        if bad and not out:
            return None, {"reason": f"모든 구간 조회 실패 ({len(bad)}개)",
                          "query_sent": build(table, from_dt=from_dt, to_dt=to_dt, sort=sort)}
    return out, None


def range_query(from_dt: str, to_dt: str, limit: int | None = None):
    """리포트 구간 평가용 — 절대 기간 조회 (yyyyMMddHHmmss).

    긴 구간은 청크 분할로 안전하게 가져온다. limit 은 합친 뒤 적용.
    """
    cfg = load_config()
    rows, err = query_chunked(from_dt, to_dt,
                              sort=cfg.get("query", {}).get("sort_col", "_time") or None)
    if err:
        return None, err
    return (rows[:limit] if limit else rows), None


# ────────────────────────────── AMOS 이상감지 ──────────────────────────────
def amos_columns_present(rows: list[dict]) -> list[str]:
    """행에 AMOS 4개 컬럼이 실제로 채워져 있는지 확인 (추측하지 않고 확인)."""
    if not rows:
        return []
    have = set(rows[0].keys())
    return [c for c in load_config().get("amos", {}).get("target_columns", []) if c in have]


def _minute_key(v: str) -> str:
    """시각 → '202607280801' (분 단위 조인 키).

    '2026-07-28 08:02:05+0900' / '2026-07-28 08:01' / '2026-07-27 0:00' 모두 처리.
    파싱 실패 시 빈 문자열 → 조인되지 않는다(잘못 붙는 것보다 안전).
    """
    dt = parse_dt(v)
    return dt.strftime("%Y%m%d%H%M") if dt else ""


def fetch_amos_table(which: str, duration: str | None = None,
                     from_dt: str | None = None, to_dt: str | None = None,
                     limit: int | None = None):
    """AMOS 단일 테이블 조회 (bottleneck | queue). MCP_NM 필터 + 시각 정렬."""
    cfg = load_config()
    a = cfg.get("amos", {})
    spec = a.get(which, {})
    tbl = (spec.get("table") or "").strip()
    if not tbl:
        return None, {"reason": f"config.amos.{which}.table 이 비어 있습니다 (추측하지 않음)",
                      "query_sent": ""}
    return query(build(tbl, duration=duration, from_dt=from_dt, to_dt=to_dt,
                       search=a.get("filter") or None,
                       sort=spec.get("time_col", "_time"), limit=limit))


def enrich_with_amos(rows: list[dict], duration: str | None = None,
                     from_dt: str | None = None, to_dt: str | None = None,
                     limit: int | None = None) -> tuple[list[dict], dict | None]:
    """기존 데이터(rows)에 AMOS 4개 컬럼을 시각 조인으로 추가한다.

    ATLAS_BOTTLENECK_ANOMALY → BOTTLENECK_downward/upward_anomaly_cols
    ATLAS_QUEUE_ANOMALY      → QUEUE_downward/upward_anomaly_cols

    조인 실패/미설정도 치명적이지 않다 — 컬럼을 빈 값으로 채우고 사유를 warn 으로 돌려준다.
    """
    cfg = load_config()
    a = cfg.get("amos", {})
    targets = a.get("target_columns", [])
    for r in rows:
        for c in targets:
            r.setdefault(c, "")

    if a.get("source") != "atlas_tables":
        return rows, None

    warns, base_tc = [], a.get("base_time_col", "datetime")
    for which in ("bottleneck", "queue"):
        spec = a.get(which, {})
        arows, err = fetch_amos_table(which, duration, from_dt, to_dt, limit)
        if err:
            warns.append(f"{spec.get('table', which)}: {err.get('reason')}")
            continue

        dcol, ucol = spec.get("downward_col"), spec.get("upward_col")
        if arows and (dcol not in arows[0] or ucol not in arows[0]):
            warns.append(f"{spec.get('table')}: 컬럼 {dcol}/{ucol} 없음 — "
                         f"실제 컬럼 {list(arows[0].keys())[:12]} (--schema 로 확인 후 config 수정)")
            continue
        if not arows:
            continue

        # 조인 시각 컬럼 자동 판별.
        # _time 은 '수집 시각'이라 데이터 시각(datetime)과 1분 어긋날 수 있으므로
        # 실제로 가장 많이 붙는 컬럼을 골라 쓴다 (설정값 → datetime → _time 순 후보).
        base_idx = {}
        for r in rows:
            k = _minute_key(r.get(base_tc))
            if k:
                base_idx.setdefault(k, []).append(r)

        # 후보 순서 = 의미가 같은 컬럼 우선.
        # base 가 datetime(데이터 시각)이면 ATLAS 도 datetime 으로 붙여야 한다.
        # _time 은 '수집 시각'이라 1분 밀릴 수 있으므로 마지막 후보.
        cands, seen = [], set()
        for c in (base_tc, spec.get("time_col"), "datetime", "time", "_time"):
            if c and c in arows[0] and c not in seen:
                seen.add(c)
                cands.append(c)

        best_tc, best_idx, best_hit = None, None, -1
        for c in cands:
            idx = {}
            for ar in arows:
                k = _minute_key(ar.get(c))
                if k:
                    idx.setdefault(k, ar)
            hit = sum(1 for k in idx if k in base_idx)
            if hit > best_hit:
                best_tc, best_idx, best_hit = c, idx, hit

        if best_hit <= 0:
            warns.append(f"{spec.get('table')}: {len(arows)}건 조회됐으나 시각 조인 0건 "
                         f"(기준 {base_tc}, 시도 {cands} — 시각 형식 확인)")
            continue

        for k, ar in best_idx.items():
            for r in base_idx.get(k, []):
                r[dcol] = ar.get(dcol, "") or ""
                r[ucol] = ar.get(ucol, "") or ""
        print(f"[AMOS] {spec.get('table')} — {best_tc} 기준 {best_hit}분 조인")

    return rows, ({"reason": " / ".join(warns), "warn": True} if warns else None)


def fetch_amos(duration: str | None = None, from_dt: str | None = None,
               to_dt: str | None = None, limit: int | None = None):
    """기존 데이터 + AMOS 4개 컬럼 (관제/리포트 공용 진입점)."""
    rows, err = (range_query(from_dt, to_dt, limit) if (from_dt and to_dt)
                 else recent(duration, limit))
    if err:
        return None, err
    return enrich_with_amos(rows, duration, from_dt, to_dt, limit)


# ────────────────────────────── 출력 ──────────────────────────────
def _print_table(rows: list[dict], max_rows: int = 20, max_col: int = 28) -> None:
    if not rows:
        print("(0건)")
        return
    cols = list(rows[0].keys())
    show = cols[:8]
    widths = {c: min(max(len(c), *(len(str(r.get(c, ""))) for r in rows[:max_rows])), max_col) for c in show}

    def cut(v, w):
        s = str(v)
        return s if len(s) <= w else s[: w - 1] + "…"

    print(" | ".join(cut(c, widths[c]).ljust(widths[c]) for c in show))
    print("-+-".join("-" * widths[c] for c in show))
    for r in rows[:max_rows]:
        print(" | ".join(cut(r.get(c, ""), widths[c]).ljust(widths[c]) for c in show))
    if len(cols) > len(show):
        print(f"\n... 컬럼 {len(cols)}개 중 {len(show)}개만 표시 (--json 으로 전체 확인)")
    if len(rows) > max_rows:
        print(f"... {len(rows)}건 중 {max_rows}건만 표시")


def _save_csv(rows: list[dict], path: str) -> None:
    if not rows:
        print("저장할 데이터 없음")
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"💾 {len(rows)}건 → {path}")


# ────────────────────────────── 기본 점검 ──────────────────────────────
def _check(cfg: dict) -> int:
    """★가장 먼저 돌릴 것 — 기본 3종(주소·키·테이블)이 실제로 되는지 확인.

    AMOS(ATLAS 2개)는 부가 항목이라 실패해도 관제는 돌아간다. 여기서 구분해 보여준다.
    """
    from lp_client import load_api_key
    from lp_query import fetch_amos_table

    ok_all = True
    print("━" * 58)
    print(" AMHS Sentinel 기본 점검")
    print("━" * 58)

    # 1) 설정
    base, table = cfg.get("logpresso_base"), cfg.get("table_name")
    print(f" 1. 주소   : {base}")
    print(f"    테이블 : {table}")
    key = load_api_key(cfg)
    print(f"    키     : {(key[:8] + '…(' + str(len(key)) + '자)') if key else '❌ 없음 — api_key.txt 를 채우세요'}")
    if not key:
        ok_all = False

    # 2) 접속
    ok, msg = ping()
    print(f"\n 2. 접속   : {'✅' if ok else '❌'} {msg}")
    if not ok:
        ok_all = False

    # 3) 기본 테이블 (이게 핵심)
    rows, err = recent()
    if err:
        print(f"\n 3. 기본 조회 : ❌ {err.get('reason')}")
        return 1
    print(f"\n 3. 기본 조회 : ✅ {table} {len(rows)}건")
    if rows:
        cols = list(rows[0].keys())
        print(f"    컬럼 {len(cols)}개 : {', '.join(cols[:10])}{' …' if len(cols) > 10 else ''}")
        need = {"datetime": "시각", "unified_risk_score": "점수", "hot_area": "설비"}
        miss = [f"{c}({k})" for c, k in need.items() if c not in cols]
        if miss:
            print(f"    ⚠️ 감지에 필요한 컬럼 없음 : {', '.join(miss)}")
            print(f"       → config.json 또는 sentinel.py 매핑을 실제 컬럼명으로 맞춰야 합니다")
            ok_all = False
        else:
            print(f"    ✅ 감지 필수 컬럼(시각·점수·설비) 확인")

    # 4) AMOS (부가)
    print("\n 4. AMOS (부가 — 실패해도 관제는 동작)")
    a = cfg.get("amos", {})
    for which in ("bottleneck", "queue"):
        spec = a.get(which, {})
        tbl = spec.get("table")
        arows, aerr = fetch_amos_table(which, duration=cfg.get("query", {}).get("window", "10m"), limit=5)
        if aerr:
            print(f"    ❌ {tbl} — {aerr.get('reason')}")
            continue
        have = list(arows[0].keys()) if arows else []
        want = [spec.get("downward_col"), spec.get("upward_col")]
        hit = [c for c in want if c in have]
        mark = "✅" if len(hit) == 2 else "⚠️"
        print(f"    {mark} {tbl} — {len(arows)}건, 목표 컬럼 {len(hit)}/2")
        if len(hit) != 2 and have:
            print(f"       실제 컬럼: {', '.join(have[:10])}")
            print(f"       → config.amos.{which}.downward_col/upward_col 교체 필요")

    print("\n" + "━" * 58)
    print(" 결과: " + ("✅ 기본 준비 완료 — python server.py 실행하세요"
                     if ok_all else "❌ 위 항목을 먼저 해결하세요"))
    print("━" * 58)
    return 0 if ok_all else 1


# ────────────────────────────── CLI ──────────────────────────────
def main(argv=None) -> int:
    cfg = load_config()
    p = argparse.ArgumentParser(
        description="로그프레소 쿼리 조회 (AMHS Sentinel 독립 도구)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("사용법:")[-1])
    p.add_argument("-q", "--query", help="LPQL 직접 입력")
    p.add_argument("-t", "--table", default=None, help=f"테이블명 (기본 {cfg.get('table_name')})")
    p.add_argument("--recent", metavar="DUR", help="최근 구간 (1m/10m/1h/1d)")
    p.add_argument("--from", dest="from_dt", metavar="yyyyMMddHHmmss")
    p.add_argument("--to", dest="to_dt", metavar="yyyyMMddHHmmss")
    p.add_argument("--search", help="search 절 (예: 'AREA==\"M16HUB\"')")
    p.add_argument("--fields", help="컬럼 쉼표 구분 (모르면 쓰지 말 것)")
    p.add_argument("--sort", help="정렬 (예: '-_time')")
    p.add_argument("--limit", type=int, help="건수 제한")
    p.add_argument("--chunk-minutes", type=int, dest="chunk",
                   help=f"--from/--to 구간 분할 단위(분). 기본 {cfg.get('query',{}).get('chunk_minutes',10)}")
    p.add_argument("--schema", action="store_true", help="컬럼 목록만 조회 (추측 금지용)")
    p.add_argument("--ping", action="store_true", help="접속 확인")
    p.add_argument("--check", action="store_true",
                   help="★기본 점검 — 설정·키·접속·기본 테이블 조회를 한 번에 확인")
    p.add_argument("--json", action="store_true", help="JSON 출력")
    p.add_argument("--out", metavar="FILE.csv", help="CSV 저장")
    p.add_argument("--dry-run", action="store_true", help="쿼리만 출력하고 실행 안 함")
    a = p.parse_args(argv)

    if a.ping:
        ok, msg = ping()
        print(f"{'✅' if ok else '❌'} {cfg.get('logpresso_base')} — {msg}")
        return 0 if ok else 1

    if a.check:
        return _check(cfg)

    if a.schema:
        table = a.table or cfg.get("table_name")
        cols = fetch_columns(table)
        if not cols:
            print(f"❌ 컬럼 조회 실패 — 접속/테이블명({table}) 확인")
            return 1
        print(f"📋 {table} 컬럼 {len(cols)}개")
        for i, c in enumerate(cols, 1):
            print(f"  {i:3}. {c}")
        return 0

    # --from/--to 는 청크 분할 경로 (대용량 안전). 단, 직접 쿼리·필터 지정 시엔 단발 조회.
    if a.from_dt and a.to_dt and not a.query and not a.search and not a.fields:
        cm = a.chunk or cfg.get("query", {}).get("chunk_minutes", 10)
        print(f"🔎 구간 조회 (청크 {cm}분, 30MB 초과 시 자동 분할)")
        if a.dry_run:
            print(f"   예: {build(a.table, from_dt=a.from_dt, to_dt=a.to_dt, sort=a.sort or '_time')}")
            return 0
        rows, err = query_chunked(a.from_dt, a.to_dt, a.table, cm,
                                  sort=a.sort or cfg.get("query", {}).get("sort_col", "_time") or None)
        if err:
            print(f"❌ {err.get('reason')}")
            return 1
        if a.limit:
            rows = rows[: a.limit]
        if a.out:
            _save_csv(rows, a.out)
        elif a.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2)[:20000])
        else:
            _print_table(rows)
        return 0

    if a.query:
        lpql = a.query
    else:
        lpql = build(a.table,
                     duration=a.recent,
                     from_dt=a.from_dt, to_dt=a.to_dt,
                     search=a.search,
                     fields=[f.strip() for f in a.fields.split(",")] if a.fields else None,
                     sort=a.sort,
                     limit=a.limit)

    print(f"🔎 LPQL: {lpql}")
    if a.dry_run:
        return 0

    rows, err = query(lpql)
    if err:
        print(f"❌ {err.get('reason')}")
        if err.get("response_preview"):
            print(f"   응답: {err['response_preview'][:200]}")
        return 1

    if a.out:
        _save_csv(rows, a.out)
    elif a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2)[:20000])
    else:
        _print_table(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
