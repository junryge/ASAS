#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
logpresso_query.py — 로그프레소 OHT 조회 (시간 구간 → CSV DataFrame)

요청 시간 구간을 chunk_minutes 단위로 끊어 로그프레소 HTTP export API 호출.
응답 크기가 30MB 초과하면 해당 구간을 절반으로 재귀 분할.

출력 컬럼 (oht_data_m16br 기준, 25컬럼 parsed 포맷):
  _id, _table, _time, ADDRESS, CARRIER, DESTINATION, DEST_RETURN_PORT,
  DISTANCE, E/M, EDGE, ERROR_CODE, EXECUTE_CYCLE, FROM_RETURN_PORT,
  GROUP_ID, MCP, MSG_ID, NETWORK_CONDITION, NEXT_ADDRESS, OPERATION_STATUS,
  RETURN_PRIORITY, STATUS, STOCK_INFO, VEHICLE, VEHICLE_EXECUTE_CYCLE,
  VEHICLE_MILEAGE

→ 이 CSV가 derive_from_oht.py / main.py 입력으로 그대로 사용 가능.
"""

import requests
import urllib.parse
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HOST    = "10.40.42.27"
PORT    = 8888
API_KEY = "10f12ae0-5a80-55cd-7b15-e5554f0612f3"

FMT = "%Y%m%d%H%M%S"
MAX_BYTES = 30 * 1024 * 1024   # 30MB


def _fetch(from_dt: str, to_dt: str, table: str):
    """단일 구간 조회. (df, byte_size) 반환. 실패 시 예외."""
    q = f'table from={from_dt} to={to_dt} {table} | sort _time'
    encoded = urllib.parse.quote(q, safe="")
    url = f"http://{HOST}:{PORT}/logpresso/httpexport/query.csv?_apikey={API_KEY}&_q={encoded}"

    resp = requests.get(url, verify=False, timeout=300)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")

    size = len(resp.content)
    df = pd.read_csv(StringIO(resp.text)) if resp.text.strip() else pd.DataFrame()
    return df, size


def query_oht_chunked(from_dt: str, to_dt: str,
                      table: str = "oht_data_m16br",
                      chunk_minutes: int = 10) -> pd.DataFrame:
    """
    시간 구간을 chunk_minutes 단위로 끊어서 조회 → concat.
    조회 결과가 30MB 넘으면 해당 구간을 절반으로 재분할(재귀).

    Parameters
    ----------
    from_dt, to_dt : str   "yyyyMMddHHmmss"
    table          : str
    chunk_minutes  : int   기본 분할 단위(분)
    """
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

        # 30MB 초과 시 해당 구간만 절반으로 재분할
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


# ─────────────────────────────────────────────
if __name__ == "__main__":
    df = query_oht_chunked(
        from_dt       = "20260621000000",
        to_dt         = "20260621010101",
        table         = "oht_data_m16br",
        chunk_minutes = 10,
    )
    print(df)
