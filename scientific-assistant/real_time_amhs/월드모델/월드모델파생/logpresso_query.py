#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
logpresso_query.py — 로그프레소 OHT 조회 (시간 구간 → CSV DataFrame)

쿼리 형식: 'remote icamcslogdt01 [ ... ]' 로 감싸 원격 노드에서 조회.

쿼리가 **두 벌**이다 (QUERY_PROFILES). 지금 쓰는 것은 PROFILE 이 가리킨다.
  · "agg30" (기본) — MSG_ID=2 만 걸러 30초로 묶는다. 고객이 준 쿼리.
  · "raw"          — 예전 쿼리. 원본 그대로 다 가져온다.
바꾸는 법 — 셋 중 아무거나:
  ① 이 파일 맨 아래쪽 PROFILE = "raw"
  ② 환경변수  LP_QUERY_PROFILE=raw
  ③ /api/logpresso/load 본문에 {"profile": "raw"}  (화면이 안 보내면 ①②를 따른다)

★agg30 은 컬럼이 줄어든다 — 받는 쪽(data_loader.parse_oht_data_m14a_row)이
  읽는 것 중 이 둘이 안 온다:
      STOCK_INFO   → isFull.      없으면 **전부 공차로 보인다** (적재 색이 안 뜬다)
      DESTINATION  → destination. 없으면 목적지가 0
  (FROM_RETURN_PORT · DEST_RETURN_PORT · RETURN_PRIORITY 도 안 오지만, 이 셋은
   화면·엔진이 안 쓴다. 속도는 위치 변화로 따로 재므로 영향 없다 — velocity_tracker.)
  필요하면 stats 줄에 first(STOCK_INFO) as STOCK_INFO 를 더하면 된다.
★agg30 은 30초에 한 줄이라 재생이 그만큼 성큼성큼 간다 (raw 는 1초 단위).
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


KEY_FROM = "파일"
if not API_KEY:
    API_KEY = _borrow("LP_API_KEY", "api_key")
    KEY_FROM = "환경변수/관제 설정"
    # ★키를 관제에서 빌려 왔으면 **주소도 같은 곳에서** 빌린다.
    #   키만 빌리고 주소는 이 파일에 박힌 값(개발 10.125.173.63)을 쓰면,
    #   다른 서버 키를 개발 서버에 보내게 되어 **401** 이 난다. 실제로 났다 —
    #   관제 config.json 의 logpresso_base 는 10.40.42.167 인데 여기는 .63 이었다.
    #   _borrow 에 host/port 를 읽는 가지가 있었는데 아무도 안 부르고 있었다.
    _h = _borrow("LP_HOST", "host")
    _p = _borrow("LP_PORT", "port")
    if _h:
        HOST = _h
    if _p:
        try:
            PORT = int(_p)
        except ValueError:
            pass
# 환경변수는 언제나 이긴다 (키를 파일에 박아 두고 주소만 바꿔 쓸 수 있게)
HOST = os.environ.get("LP_HOST", "").strip() or HOST
PORT = int(os.environ.get("LP_PORT", "").strip() or PORT)

FMT = "%Y%m%d%H%M%S"
MAX_BYTES = 30 * 1024 * 1024   # 30MB


# ───────────────────────────────────────────────────────────
# 쿼리 두 벌
# ───────────────────────────────────────────────────────────
def _q_raw(from_dt: str, to_dt: str, table: str) -> str:
    """예전 쿼리 — 원본 그대로."""
    return f'table from={from_dt} to={to_dt} {table} | sort _time'


def _q_agg30(from_dt: str, to_dt: str, table: str) -> str:
    """고객이 준 쿼리 — MSG_ID=2 만, 30초로 묶어 차량당 한 줄."""
    return (
        f'table from={from_dt} to={to_dt} {table}'
        ' | search MSG_ID == "2"'
        ' | sort _time'
        ' | eval _time = datetrunc(_time, "30s")'
        ' | stats first(ADDRESS) as ADDRESS, first(DISTANCE) as DISTANCE,'
        ' first(NEXT_ADDRESS) as NEXT_ADDRESS, first(EDGE) as EDGE,'
        ' first(CARRIER) as CARRIER, first(STATUS) as STATUS,'
        ' first(OPERATION_STATUS) as OPERATION_STATUS'
        ' by VEHICLE, _time'
        ' | sort _time, VEHICLE'
    )


QUERY_PROFILES = {"agg30": _q_agg30, "raw": _q_raw}

# 지금 쓰는 쿼리. "raw" 로 바꾸면 예전 쿼리로 돌아간다.
PROFILE = os.environ.get("LP_QUERY_PROFILE", "").strip() or "agg30"


def _build_query(from_dt: str, to_dt: str, table: str, profile: str = None) -> str:
    name = (profile or PROFILE or "agg30").strip()
    fn = QUERY_PROFILES.get(name)
    if fn is None:
        raise ValueError(f"모르는 쿼리 프로필 {name!r} (가능: {sorted(QUERY_PROFILES)})")
    inner = fn(from_dt, to_dt, table)
    if REMOTE_NODE:
        return f'remote {REMOTE_NODE} [ {inner} ]'
    return inner


def _fetch(from_dt: str, to_dt: str, table: str, profile: str = None):
    if not API_KEY:
        raise RuntimeError(
            "로그프레소 API 키가 없습니다. 아래 중 하나로 넣으세요 —\n"
            "  · 환경변수 LP_API_KEY\n"
            "  · 이 폴더의 logpresso.json  {\"api_key\": \"…\"}\n"
            "  · 관제(real_time_amhs)의 config.json 또는 api_key.txt")
    q = _build_query(from_dt, to_dt, table, profile)
    encoded = urllib.parse.quote(q, safe="")
    url = f"http://{HOST}:{PORT}/logpresso/httpexport/query.csv?_apikey={API_KEY}&_q={encoded}"

    print(f"  [Q] {q}")

    resp = requests.get(url, verify=False, timeout=300)
    if resp.status_code != 200:
        body = resp.text[:500]
        # ★401 은 쿼리가 아니라 **키와 주소의 짝**이 문제다. 로그프레소는 키가
        #   안 맞으면 로그인 화면 HTML 을 돌려줘서, 얼핏 쿼리 오류로 보인다.
        hint = ""
        if resp.status_code == 401:
            hint = (f"\n  ▶ 401 = 인증 실패. 쿼리는 돌지도 않았다.\n"
                    f"     지금 주소 {HOST}:{PORT} · 키 출처 {KEY_FROM} "
                    f"(끝 4자 …{API_KEY[-4:] if len(API_KEY) >= 4 else '?'})\n"
                    f"     이 주소용 키가 맞는지 보라. 주소를 바꾸려면 "
                    f"LP_HOST/LP_PORT, 키는 LP_API_KEY.")
        raise RuntimeError(
            f"HTTP {resp.status_code} from {HOST}:{PORT}{hint}\n"
            f"  실패 쿼리: {q}\n"
            f"  응답(앞 500자): {body}"
        )

    size = len(resp.content)
    df = (pd.read_csv(StringIO(resp.text), low_memory=False, dtype=str)
          if resp.text.strip() else pd.DataFrame())
    return df, size


def query_oht_chunked(from_dt: str, to_dt: str,
                      table: str = "oht_data_m16br",
                      chunk_minutes: int = 10,
                      profile: str = None) -> pd.DataFrame:
    start = datetime.strptime(from_dt, FMT)
    end   = datetime.strptime(to_dt, FMT)
    step  = timedelta(minutes=chunk_minutes)

    used = (profile or PROFILE or "agg30").strip()
    print(f"[쿼리] 프로필 {used}  (raw 로 되돌리려면 LP_QUERY_PROFILE=raw)")
    # ★어느 서버에 어느 키로 치는지 남긴다 — 401 이 나면 여기부터 본다
    print(f"[접속] {HOST}:{PORT}  remote={REMOTE_NODE or '(없음)'}  "
          f"키 출처 {KEY_FROM} (끝 4자 …{API_KEY[-4:] if len(API_KEY) >= 4 else '?'})")

    frames = []
    cur = start

    while cur < end:
        nxt = min(cur + step, end)
        f_s = cur.strftime(FMT)
        t_s = nxt.strftime(FMT)

        df, size = _fetch(f_s, t_s, table, profile)

        if size > MAX_BYTES and (nxt - cur) > timedelta(seconds=1):
            mid = cur + (nxt - cur) / 2
            print(f"[SPLIT] {f_s}~{t_s} = {size/1024/1024:.1f}MB 초과 → 분할")
            sub = query_oht_chunked(f_s, mid.strftime(FMT), table, chunk_minutes, profile)
            sub2 = query_oht_chunked(mid.strftime(FMT), t_s, table, chunk_minutes, profile)
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
