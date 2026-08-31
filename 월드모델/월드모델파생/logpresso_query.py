#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
logpresso_query.py — 로그프레소 OHT 조회 (시간 구간 → CSV DataFrame)

쿼리 형식: 'remote icamcslogdt01 [ ... ]' 로 감싸 원격 노드에서 조회.
"""

import requests
import urllib.parse
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ───────────────────────────────────────────────────────────
# 접속 설정 — 운영/개발 둘 중 하나만 활성화
# ───────────────────────────────────────────────────────────

# [운영]
#HOST    = "10.40.42.27"
#PORT    = 8888
#API_KEY = "10f12ae0-5a80-55cd-7b15-e5554f0612f3"

# [개발]  http://10.125.173.63/
HOST    = "10.125.173.63"
PORT    = 8888
API_KEY = "db1d2335-49cf-e859-3519-1ca132922e38"

# 원격 노드명. 비우면 remote 감싸지 않음.
REMOTE_NODE = "icamcslogdt01"

FMT = "%Y%m%d%H%M%S"
MAX_BYTES = 30 * 1024 * 1024   # 30MB


def _build_query(from_dt: str, to_dt: str, table: str) -> str:
    inner = f'table from={from_dt} to={to_dt} {table} | sort _time'
    if REMOTE_NODE:
        return f'remote {REMOTE_NODE} [ {inner} ]'
    return inner


def _fetch(from_dt: str, to_dt: str, table: str):
    q = _build_query(from_dt, to_dt, table)
    encoded = urllib.parse.quote(q, safe="")
    url = f"http://{HOST}:{PORT}/logpresso/httpexport/query.csv?_apikey={API_KEY}&_q={encoded}"

    print(f"  [Q] {q}")

    resp = requests.get(url, verify=False, timeout=300)
    if resp.status_code != 200:
        body = resp.text[:500]
        raise RuntimeError(
            f"HTTP {resp.status_code} from {HOST}:{PORT}\n"
            f"  실패 쿼리: {q}\n"
            f"  응답(앞 500자): {body}"
        )

    size = len(resp.content)
    df = (pd.read_csv(StringIO(resp.text), low_memory=False, dtype=str)
          if resp.text.strip() else pd.DataFrame())
    return df, size


def query_oht_chunked(from_dt: str, to_dt: str,
                      table: str = "oht_data_m16br",
                      chunk_minutes: int = 10) -> pd.DataFrame:
    start = datetime.strptime(from_dt, FMT)
    end   = datetime.strptime(to_dt, FMT)
    step  = timedelta(minutes=chunk_minutes)

    frames = []
    cur = start

    while cur < end:
        nxt = min(cur + step, end)
        f_s = cur.strftime(FMT)
        t_s = nxt.strftime(FMT)

        df, size = _fetch(f_s, t_s, table)

        if size > MAX_BYTES and (nxt - cur) > timedelta(seconds=1):
            mid = cur + (nxt - cur) / 2
            print(f"[SPLIT] {f_s}~{t_s} = {size/1024/1024:.1f}MB 초과 → 분할")
            sub = query_oht_chunked(f_s, mid.strftime(FMT), table, chunk_minutes)
            sub2 = query_oht_chunked(mid.strftime(FMT), t_s, table, chunk_minutes)
            frames.extend([sub, sub2])
        else:
            print(f"[OK] {f_s}~{t_s}  {len(df):>6}건  {size/1024/1024:5.1f}MB")
            if not df.empty:
                frames.append(df)

        cur = nxt

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    if "_time" in result.columns:
        result = result.sort_values("_time").reset_index(drop=True)
    print(f"[DONE] 총 {len(result)}건")
    return result


if __name__ == "__main__":
    print(f"[설정] HOST={HOST}:{PORT}  REMOTE={REMOTE_NODE}")
    df = query_oht_chunked(
        from_dt       = "20260621000000",
        to_dt         = "20260621010101",
        table         = "oht_data_m16br",
        chunk_minutes = 10,
    )
    print(df)
