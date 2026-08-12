#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_history.py — 과거 기간 IDC 데이터를 날짜별 CSV 로 추출
============================================================
`aws_idc_realtime_collector.py` 는 실시간용이라 쿼리가 SYSDATE 기준 90분으로
고정되어 있어 과거 구간을 못 뽑는다. 이 스크립트는 같은 테이블
(AWS_IDC_DATA_HIS) 에서 **날짜 범위**를 받아 하루씩 끊어 저장한다.

출력 형식은 기존 RAW 와 동일:
    M16A_HUBROOM_PR_20260701.CSV ... 20260731.CSV   (분당 1행, CRT_TM + 컬럼들)
→ ml_v2 가 바로 먹는다.

컬럼 목록은 **기존 RAW CSV 헤더에서 그대로 읽어온다** (--columns-from).
그래야 265컬럼 구성이 학습 데이터와 100% 일치한다.

자격증명은 환경변수만 사용 (코드에 하드코딩하지 않음):
    export ORA_USER=...   ORA_PASS=...   ORA_DSN=host:port/service

사용:
    # 7월 전체 (컬럼은 기존 4~5월 CSV 에서 그대로)
    python fetch_history.py --from 2026-07-01 --to 2026-07-31 \
        --columns-from RAW/M16A_HUBROOM_PR_20260401.CSV --out RAW

    # 이미 있는 날짜는 건너뜀. 다시 받으려면 --overwrite
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import datetime, timedelta

TABLE = "AWS_IDC_DATA_HIS"
TIME_COL = "CRT_TM"


def read_columns(path: str) -> list[str]:
    """기존 CSV 헤더에서 IDC 컬럼 목록을 뽑는다 (CRT_TM 제외)."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        header = next(csv.reader(f))
    cols = [c.strip() for c in header if c.strip() and c.strip() != TIME_COL]
    if not cols:
        sys.exit(f"컬럼을 못 읽었습니다: {path}")
    return cols


def connect():
    try:
        import oracledb
    except ImportError:
        sys.exit("oracledb 필요:  pip install oracledb")
    user = os.getenv("ORA_USER")
    pw = os.getenv("ORA_PASS")
    dsn = os.getenv("ORA_DSN")
    missing = [k for k, v in (("ORA_USER", user), ("ORA_PASS", pw),
                              ("ORA_DSN", dsn)) if not v]
    if missing:
        sys.exit("환경변수 필요: " + ", ".join(missing) +
                 "\n  예) export ORA_USER=STAREAD ORA_PASS=*** "
                 "ORA_DSN=10.40.41.103:1521/ICASTARPP")
    return oracledb.connect(user=user, password=pw, dsn=dsn)


def build_sql(n_cols: int) -> str:
    """
    롱포맷(IDC_NM/IDC_VAL)으로 받아 파이썬에서 피벗한다.
    265컬럼 PIVOT 을 SQL 로 만들면 쿼리가 비대해지므로 이 방식이 안전하다.
    """
    ph = ",".join(f":c{i}" for i in range(n_cols))
    return (
        f"SELECT TO_CHAR({TIME_COL}, 'YYYY-MM-DD HH24:MI:SS') AS T, "
        f"IDC_NM, IDC_VAL "
        f"FROM {TABLE} "
        f"WHERE {TIME_COL} >= :d0 AND {TIME_COL} < :d1 "
        f"  AND IDC_NM IN ({ph}) "
        f"ORDER BY T"
    )


def fetch_range(conn, sql, cols, t0: datetime, t1: datetime) -> dict[str, dict]:
    """[t0, t1) 구간을 {시각: {컬럼: 값}} 으로."""
    binds = {"d0": t0, "d1": t1}
    binds.update({f"c{i}": nm for i, nm in enumerate(cols)})
    table: dict[str, dict[str, str]] = {}
    with conn.cursor() as cur:
        cur.arraysize = 5000
        cur.execute(sql, binds)
        for t, nm, val in cur:
            table.setdefault(t, {})[nm] = val
    return table


def write_csv(path: str, cols: list[str], table: dict) -> int:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow([TIME_COL] + cols)
        for t in sorted(table):
            row = table[t]
            w.writerow([t] + ["" if row.get(c) is None else row.get(c, "")
                              for c in cols])
    return len(table)


def main():
    ap = argparse.ArgumentParser(description="과거 IDC 데이터 → 날짜별 CSV")
    ap.add_argument("--from", dest="d_from", required=True, help="YYYY-MM-DD")
    ap.add_argument("--to", dest="d_to", required=True, help="YYYY-MM-DD (포함)")
    ap.add_argument("--columns-from", required=True,
                    help="컬럼 목록을 읽어올 기존 CSV (예: RAW/...20260401.CSV)")
    ap.add_argument("--out", default="RAW", help="저장 폴더")
    ap.add_argument("--prefix", default="M16A_HUBROOM_PR_")
    ap.add_argument("--split", choices=["day", "hour"], default="day",
                    help="파일 분할 단위. day=20260701 (기본, 기존 4~5월과 동일) / "
                         "hour=2026070101")
    ap.add_argument("--ext", default=".CSV", help="확장자 (.CSV 또는 .csv)")
    ap.add_argument("--overwrite", action="store_true", help="기존 파일도 덮어씀")
    a = ap.parse_args()
    if not a.ext.startswith("."):
        a.ext = "." + a.ext

    cols = read_columns(a.columns_from)
    d0 = datetime.strptime(a.d_from, "%Y-%m-%d")
    d1 = datetime.strptime(a.d_to, "%Y-%m-%d")
    if d1 < d0:
        sys.exit("--to 가 --from 보다 앞섭니다")
    os.makedirs(a.out, exist_ok=True)

    # 분할 단위 설정
    if a.split == "hour":
        step, dfmt, expect, unit = timedelta(hours=1), "%Y%m%d%H", 60, "시간"
    else:
        step, dfmt, expect, unit = timedelta(days=1), "%Y%m%d", 1440, "일"
    end = d1 + timedelta(days=1)          # --to 당일 포함

    print(f"컬럼 {len(cols)}개 (기준: {os.path.basename(a.columns_from)})")
    print(f"기간 {a.d_from} ~ {a.d_to}  →  {a.out}/"
          f"{a.prefix}{d0:{dfmt}}{a.ext} 형식 ({a.split} 단위)")
    sql = build_sql(len(cols))
    conn = connect()
    print(f"접속 OK: {os.getenv('ORA_DSN')}\n")

    total_rows, done, skipped = 0, 0, 0
    cur_t = d0
    while cur_t < end:
        name = f"{a.prefix}{cur_t:{dfmt}}{a.ext}"
        path = os.path.join(a.out, name)
        if os.path.exists(path) and not a.overwrite:
            print(f"  {name}  (이미 있음 — 건너뜀)")
            skipped += 1
            cur_t += step
            continue
        t_start = time.time()
        try:
            table = fetch_range(conn, sql, cols, cur_t, cur_t + step)
        except Exception as e:
            print(f"  {name}  ❌ 쿼리 실패: {e}")
            cur_t += step
            continue
        n = write_csv(path, cols, table)
        total_rows += n
        done += 1
        warn = f"  ⚠ {expect}분 미달" if n < expect * 0.97 else ""
        print(f"  {name}  {n}행  ({time.time()-t_start:.1f}s){warn}")
        cur_t += step

    conn.close()
    print(f"\n완료: {done}{unit} 저장 · {skipped}{unit} 건너뜀 · 총 {total_rows}행")
    print(f"확인:  python data.py --data \"{a.out}/*.CSV\" --window 10 --pct 0.99")


if __name__ == "__main__":
    main()
