#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
logpresso_query.py — 로그프레소 OHT 조회 (시간 구간 → CSV DataFrame)

쿼리 형식: 'remote icamcslogdt01 [ ... ]' 로 감싸 원격 노드에서 조회.
"""

import os
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
#API_KEY = ""

# [개발]  http://10.125.173.63/
HOST    = "10.125.173.63"
PORT    = 8888
API_KEY = ""          # ★키를 여기에 적으세요

# ★저장소에 올릴 때는 반드시 다시 비우세요.
#   전에 운영·개발 키가 이 자리에 박힌 채로 올라갔고, 관제의 보안 시험
#   (tests/test_secrets.py)이 잡았습니다. 한 번 올라간 키는 파일에서 지워도
#   이력에 남습니다 — 그때는 키를 새로 발급받는 것이 진짜 조치입니다.

# 원격 노드명. 비우면 remote 감싸지 않음.
REMOTE_NODE = "icamcslogdt01"


# 위를 비워 두면 아래 순서로 찾는다 (그냥 두고 써도 되게).
#   ① 환경변수 LP_API_KEY / LP_HOST / LP_PORT
#   ② 관제(real_time_amhs)의 config.json · api_key.txt — 같은 로그프레소다
def _borrow(name, key):
    import json as _json
    v = os.environ.get(name)
    if v:
        return v.strip()
    # 월드모델은 real_time_amhs/월드모델/월드모델파생/ 이라 두 단계 위다
    base = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", ".."))
    try:
        with open(os.path.join(base, "config.json"), encoding="utf-8-sig") as f:
            c = _json.load(f) or {}
        if key == "api_key":
            k = str(c.get("api_key") or "").strip()
            if k and not k.startswith("<"):
                return k
        elif key in ("host", "port"):
            b = str(c.get("logpresso_base") or "")
            if "//" in b:
                hp = b.split("//", 1)[1].split("/", 1)[0]
                return hp.split(":")[0] if key == "host" else (
                    hp.split(":")[1] if ":" in hp else "")
    except Exception:
        pass
    if key == "api_key":
        try:
            with open(os.path.join(base, "api_key.txt"), encoding="utf-8-sig") as f:
                return f.read().strip()
        except Exception:
            pass
    return ""


if not API_KEY:
    API_KEY = _borrow("LP_API_KEY", "api_key")
HOST = os.environ.get("LP_HOST", "").strip() or HOST
PORT = int(os.environ.get("LP_PORT", "").strip() or PORT)

FMT = "%Y%m%d%H%M%S"
MAX_BYTES = 30 * 1024 * 1024   # 30MB


def _build_query(from_dt: str, to_dt: str, table: str) -> str:
    inner = f'table from={from_dt} to={to_dt} {table} | sort _time'
    if REMOTE_NODE:
        return f'remote {REMOTE_NODE} [ {inner} ]'
    return inner


def _fetch(from_dt: str, to_dt: str, table: str):
    if not API_KEY:
        raise RuntimeError(
            "로그프레소 API 키가 없습니다. 아래 중 하나로 넣으세요 —\n"
            "  · 환경변수 LP_API_KEY\n"
            "  · 이 폴더의 logpresso.json  {\"api_key\": \"…\"}\n"
            "  · 관제(real_time_amhs)의 config.json 또는 api_key.txt")
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
