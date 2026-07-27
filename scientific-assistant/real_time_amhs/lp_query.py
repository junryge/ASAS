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
import sys

from lp_client import fetch_columns, load_config, ping, query


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


def range_query(from_dt: str, to_dt: str, limit: int | None = None):
    """리포트 구간 평가용 — 절대 기간 조회 (yyyyMMddHHmmss)."""
    return query(build(from_dt=from_dt, to_dt=to_dt, limit=limit))


# ────────────────────────────── AMOS 이상감지 ──────────────────────────────
def amos_columns_present(rows: list[dict]) -> list[str]:
    """행에 AMOS 4개 컬럼이 실제로 채워져 있는지 확인 (추측하지 않고 확인)."""
    if not rows:
        return []
    have = set(rows[0].keys())
    return [c for c in load_config().get("amos", {}).get("target_columns", []) if c in have]


def _minute_key(v: str) -> str:
    """'2026-07-11 10:27:33' / '2026-07-11T10:27' → '202607111027' (분 단위 키)."""
    d = "".join(ch for ch in str(v or "") if ch.isdigit())
    return d[:12] if len(d) >= 12 else d


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

        tc = spec.get("time_col", "_time")
        dcol, ucol = spec.get("downward_col"), spec.get("upward_col")
        if arows and (dcol not in arows[0] or ucol not in arows[0]):
            warns.append(f"{spec.get('table')}: 컬럼 {dcol}/{ucol} 없음 — "
                         f"실제 컬럼 {list(arows[0].keys())[:12]} (--schema 로 확인 후 config 수정)")
            continue

        idx = {}
        for ar in arows or []:
            idx.setdefault(_minute_key(ar.get(tc)), ar)

        hit = 0
        for r in rows:
            ar = idx.get(_minute_key(r.get(base_tc)))
            if not ar:
                continue
            hit += 1
            r[dcol] = ar.get(dcol, "") or ""
            r[ucol] = ar.get(ucol, "") or ""
        if arows and not hit:
            warns.append(f"{spec.get('table')}: {len(arows)}건 조회됐으나 시각 조인 0건 "
                         f"(base_time_col={base_tc}, time_col={tc} 형식 확인)")

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
    p.add_argument("--schema", action="store_true", help="컬럼 목록만 조회 (추측 금지용)")
    p.add_argument("--ping", action="store_true", help="접속 확인")
    p.add_argument("--json", action="store_true", help="JSON 출력")
    p.add_argument("--out", metavar="FILE.csv", help="CSV 저장")
    p.add_argument("--dry-run", action="store_true", help="쿼리만 출력하고 실행 안 함")
    a = p.parse_args(argv)

    if a.ping:
        ok, msg = ping()
        print(f"{'✅' if ok else '❌'} {cfg.get('logpresso_base')} — {msg}")
        return 0 if ok else 1

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
