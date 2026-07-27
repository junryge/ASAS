#!/usr/bin/env python3
"""
AMHS Sentinel — 로그프레소 조회 클라이언트 (독립)

데모스(demos_v1)와 완전 독립. 어떤 데모스 모듈도 import 하지 않는다.
검증된 HTTP 방식(httpexport/query.csv)만 그대로 사용한다.

    from lp_client import query, load_config
    rows, err = query("table duration=10m test_table3 | limit 100")

사내망 밖(개발 PC/클라우드)에서는 로그프레소에 닿지 않으므로
환경변수 LP_OFFLINE=1 이면 fixtures/*.csv 를 대신 읽는다.
"""
from __future__ import annotations

import csv
import io
import json
import os
import time
import urllib.parse
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# 읽기 전용 강제 — 관제 시스템은 절대 쓰기 쿼리를 보내지 않는다
_BLOCKED = ("drop", "delete", "insert", "import", "create",
            "grant", "revoke", "update", "truncate")

_config_cache = None


def load_config(reload: bool = False) -> dict:
    """config.json 로드 (캐시)."""
    global _config_cache
    if _config_cache is None or reload:
        with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
            _config_cache = json.load(f)
    return _config_cache


def load_api_key(cfg: dict | None = None) -> str:
    """api_key_file 에서 로그프레소 API 키를 읽는다. 없으면 환경변수 LP_API_KEY."""
    cfg = cfg or load_config()
    path = cfg.get("api_key_file", "api_key.txt")
    if not os.path.isabs(path):
        path = os.path.join(BASE_DIR, path)
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                key = f.read().strip()
            if key:
                try:                       # 한글 플레이스홀더 방어
                    key.encode("ascii")
                    return key
                except UnicodeEncodeError:
                    print(f"[LP] ⚠️ {path} 에 비영문 문자 — 실제 키로 교체하세요")
        except Exception as e:
            print(f"[LP] ⚠️ api_key_file 읽기 실패: {e}")
    return os.getenv("LP_API_KEY", "").strip()


def validate_readonly(lpql: str) -> str | None:
    """쓰기 계열 명령이 섞이면 사유 문자열 반환, 안전하면 None."""
    low = " " + " ".join(lpql.split()).lower() + " "
    for cmd in _BLOCKED:
        if f" {cmd} " in low or low.startswith(f" {cmd} "):
            return f"읽기 전용 위반: '{cmd}' 명령 차단"
    return None


def build_url(lpql: str, cfg: dict | None = None) -> str:
    """조회 URL 생성 — {base}/httpexport/query.csv?_apikey=..&_q=.."""
    cfg = cfg or load_config()
    base = cfg.get("logpresso_base", "").rstrip("/")
    key = load_api_key(cfg)
    q = urllib.parse.quote(" ".join(lpql.split()), safe="")
    return f"{base}/httpexport/query.csv?_apikey={key}&_q={q}"


def _parse_csv(text: str) -> list[dict]:
    """CSV 텍스트 → list[dict] (pandas 비의존)."""
    return [dict(r) for r in csv.DictReader(io.StringIO(text))]


def _offline_rows(lpql: str) -> tuple[list[dict] | None, dict | None]:
    """LP_OFFLINE=1 일 때 fixtures 에서 읽어 동작 검증.

    쿼리의 테이블명과 같은 이름의 fixture(fixtures/<TABLE>.csv)가 있으면 그것을,
    없으면 sample_rows.csv 를 쓴다.
    """
    fxdir = os.path.join(BASE_DIR, "fixtures")
    toks = lpql.split()
    table = ""
    for i, t in enumerate(toks):                       # 'table [opts] <name>' 에서 테이블명 추출
        if t == "table":
            for nxt in toks[i + 1:]:
                if "=" in nxt:
                    continue
                table = nxt.strip("|")
                break
            break

    for cand in ([f"{table}.csv"] if table else []) + ["sample_rows.csv"]:
        fx = os.path.join(fxdir, cand)
        if os.path.isfile(fx):
            with open(fx, "r", encoding="utf-8-sig") as f:
                rows = _parse_csv(f.read())
            print(f"[LP] 🔌 OFFLINE — {cand} {len(rows)}건")
            return rows, None

    return None, {"reason": f"오프라인 모드인데 fixture 없음: {fxdir}", "query_sent": lpql}


def query(lpql: str, timeout: int | None = None,
          cfg: dict | None = None, verbose: bool = True,
          retries: int | None = None):
    """LPQL 실행 → (rows, None) 또는 (None, err).

    rows   : list[dict]  — CSV 헤더를 키로 하는 레코드 목록
    err    : {"reason", "query_sent", ...}
    retries: None 이면 config 값. 헬스체크처럼 즉시 실패가 나은 곳은 1 을 준다.
    """
    cfg = cfg or load_config()
    qcfg = cfg.get("query", {})
    timeout = timeout or qcfg.get("timeout_s", 60)
    retries = retries if retries is not None else qcfg.get("max_retries", 3)

    clean = " ".join(lpql.split())
    bad = validate_readonly(clean)
    if bad:
        return None, {"reason": bad, "query_sent": clean}

    if os.getenv("LP_OFFLINE") == "1":
        return _offline_rows(clean)

    url = build_url(clean, cfg)
    if verbose:
        print(f"[LP] ▶ {clean[:200]}")

    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "text/csv"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                code = resp.getcode()

            if code == 200 and body.strip():
                if body.lstrip().startswith("<!"):
                    return None, {"reason": "HTTP 200 (HTML 에러 페이지)",
                                  "response_preview": body[:500], "query_sent": clean}
                rows = _parse_csv(body)
                if verbose:
                    print(f"[LP] ✅ {len(rows)}건" + (f" (재시도 {attempt})" if attempt else ""))
                return rows, None

            reason = f"HTTP {code}" + (" (빈 응답)" if not body.strip() else "")
            return None, {"reason": reason, "response_preview": body[:500], "query_sent": clean}

        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            if attempt < retries - 1:
                wait = 2 * (attempt + 1)
                if verbose:
                    print(f"[LP] ⚠️ {last} → {wait}초 후 재시도 ({attempt+1}/{retries})")
                time.sleep(wait)
                continue

    return None, {"reason": f"재시도 {retries}회 실패 ({last})", "query_sent": clean}


def fetch_columns(table: str | None = None, timeout: int = 10) -> list[str]:
    """테이블 컬럼 목록 조회 (샘플 1건). 컬럼을 추측하지 않기 위한 사전 조회용."""
    cfg = load_config()
    table = table or cfg.get("table_name", "")
    rows, err = query(f"table duration=1d {table} | limit 1", timeout=timeout, verbose=False)
    if rows:
        return list(rows[0].keys())
    if err:
        print(f"[LP] ℹ️ 컬럼 조회 실패: {err.get('reason')}")
    return []


def ping(timeout: int = 5) -> tuple[bool, str]:
    """로그프레소 접속 확인 (헬스체크 — 재시도 없이 즉시 판정)."""
    rows, err = query("system tables | limit 1", timeout=timeout,
                      verbose=False, retries=1)
    if rows is not None:
        return True, "접속 정상"
    return False, (err or {}).get("reason", "알 수 없음")


if __name__ == "__main__":
    cfg = load_config()
    print(f"base    : {cfg.get('logpresso_base')}")
    print(f"table   : {cfg.get('table_name')}")
    key = load_api_key(cfg)
    print(f"api_key : {(key[:8] + '…') if key else '(없음 — api_key.txt 를 채우세요)'}")
    ok, msg = ping()
    print(f"ping    : {'✅' if ok else '❌'} {msg}")
