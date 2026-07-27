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


def _fix_console_encoding() -> None:
    """Windows 콘솔(cp949)에서 이모지 출력 시 UnicodeEncodeError 로 죽는 것을 막는다.

    ✅ ❌ ⚠ 같은 문자는 cp949 에 없어서, 첫 print 에서 프로그램이 즉시 종료된다.
    stdout/stderr 를 UTF-8(errors='replace')로 바꿔 어떤 콘솔에서도 안 죽게 한다.
    """
    import sys
    for stream in (sys.stdout, sys.stderr):
        try:
            enc = (getattr(stream, "encoding", "") or "").lower()
            if enc.replace("-", "") not in ("utf8", "utf8mb4") and hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_fix_console_encoding()      # import 시점에 한 번 — 모든 진입점이 lp_client 를 import 한다

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
    """로그프레소 API 키.

    우선순위: config.json 의 api_key → api_key_file → 환경변수 LP_API_KEY
    (스크립트처럼 config 에 바로 박아 써도 된다.)
    """
    cfg = cfg or load_config()

    direct = str(cfg.get("api_key") or "").strip()
    if direct and not direct.startswith("<"):        # <여기에...> 플레이스홀더 무시
        return direct

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


def parse_dt(value):
    """로그프레소/CSV 의 여러 시각 표기를 datetime 으로. 실패 시 None.

    실제로 들어오는 형태들:
      '2026-07-28 08:02:05+0900'   ← _time (타임존 포함)
      '2026-07-28 08:01'           ← datetime
      '2026-07-27 0:00'            ← 한 자리 시
      '2026-07-28T08:01:00'
    ※ 숫자만 뽑아 자르는 방식은 '0:00' 에서 자릿수가 어긋나므로 쓰지 않는다.
    """
    from datetime import datetime as _dt
    s = str(value or "").strip()
    if not s:
        return None
    s = s.replace("T", " ")
    # 끝의 타임존(+0900 / +09:00 / Z) 제거 — 로그프레소는 KST 로 내려준다
    import re as _re
    s = _re.sub(r"\s*(?:Z|[+-]\d{2}:?\d{2})$", "", s).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M",
                "%Y%m%d%H%M%S", "%Y-%m-%d"):
        try:
            return _dt.strptime(s, fmt)
        except ValueError:
            continue
    return None


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
    """CSV 텍스트 → list[dict] (pandas 비의존).

    응답이 중간에 끊긴 경우 마지막 줄이 잘려 컬럼 수가 모자랄 수 있다.
    DictReader 는 모자란 필드를 None 으로 채우므로, 그런 행은 버린다.
    """
    rows, dropped = [], 0
    for r in csv.DictReader(io.StringIO(text)):
        if None in r.values() or None in r:      # 잘린 행 / 여분 필드
            dropped += 1
            continue
        rows.append(dict(r))
    if dropped:
        print(f"[LP] ⚠️ 잘린 행 {dropped}건 제외")
    return rows


def _offline_rows(lpql: str):
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
                body = f.read()
            rows = _parse_csv(body)
            print(f"[LP] 🔌 OFFLINE — {cand} {len(rows)}건 (fixture 원본)")
            return rows, len(body.encode("utf-8")), None

    return None, 0, {"reason": f"오프라인 모드인데 fixture 없음: {fxdir}", "query_sent": lpql}


_requests = None
_requests_checked = False


def _get_requests():
    """requests 가 있으면 그걸 쓴다 (사내에서 검증된 방식).

    로그프레소 export 는 Content-Length 를 다 채우지 않고 연결을 끊는 경우가 있어
    urllib 은 IncompleteRead 로 죽지만, requests/urllib3 은 이를 견딘다.
    """
    global _requests, _requests_checked
    if not _requests_checked:
        _requests_checked = True
        try:
            import requests as _r
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except Exception:
                pass
            _requests = _r
        except ImportError:
            _requests = None
    return _requests


def _http_get(url: str, timeout: int, cfg: dict) -> tuple[int, bytes]:
    """CSV 본문을 가져온다. (status, bytes)

    ① requests 우선 — 회사 스크립트와 동일한 경로
    ② 없으면 urllib. 이때 IncompleteRead 는 받은 만큼 살려서 쓴다
       (마지막 잘린 줄은 파싱 단계에서 버려진다)
    """
    rq = _get_requests()
    if rq is not None:
        resp = rq.get(url, verify=False, timeout=timeout)
        return resp.status_code, resp.content

    import http.client
    if cfg.get("query", {}).get("use_proxy", False):
        opener = urllib.request.build_opener()
    else:
        # Windows urllib 은 시스템 프록시(IE 설정)를 자동으로 타므로 기본 우회
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    req = urllib.request.Request(url, headers={"Accept": "text/csv"})
    with opener.open(req, timeout=timeout) as resp:
        code = resp.getcode()
        try:
            raw = resp.read()
        except http.client.IncompleteRead as e:
            raw = e.partial                      # 받은 만큼이라도 살린다
            print(f"[LP] ⚠️ 응답이 중간에 끊김 — 받은 {len(raw)}바이트로 진행")
    return code, raw


def query_sized(lpql: str, timeout: int | None = None,
                cfg: dict | None = None, verbose: bool = True,
                retries: int | None = None):
    """LPQL 실행 → (rows, 응답바이트, err).

    응답 크기를 함께 돌려준다 — 대용량 구간을 청크로 쪼갤 때 판단 기준이 된다.
    """
    cfg = cfg or load_config()
    qcfg = cfg.get("query", {})
    timeout = timeout or qcfg.get("timeout_s", 300)
    retries = retries if retries is not None else qcfg.get("max_retries", 3)

    clean = " ".join(lpql.split())
    bad = validate_readonly(clean)
    if bad:
        return None, 0, {"reason": bad, "query_sent": clean}

    if os.getenv("LP_OFFLINE") == "1":
        return _offline_rows(clean)

    # 키가 없으면 빈 _apikey= 로 나가서 조용히 실패한다 → 먼저 막고 알려준다
    if not load_api_key(cfg):
        kf = cfg.get("api_key_file", "api_key.txt")
        return None, 0, {
            "reason": f"로그프레소 API 키가 없습니다 — {kf} 를 만들거나 "
                      f"config.json 의 \"api_key\" 에 직접 넣으세요 "
                      f"(경로: {os.path.join(BASE_DIR, kf)})",
            "query_sent": clean}

    url = build_url(clean, cfg)
    if verbose:
        print(f"[LP] ▶ {clean[:200]}")

    last = None
    for attempt in range(retries):
        try:
            code, raw = _http_get(url, timeout, cfg)
            body = raw.decode("utf-8", errors="replace")
            size = len(raw)

            if code == 200 and body.strip():
                if body.lstrip().startswith("<!"):
                    return None, size, {"reason": "HTTP 200 (HTML 에러 페이지)",
                                        "response_preview": body[:500], "query_sent": clean}
                rows = _parse_csv(body)
                if verbose:
                    print(f"[LP] ✅ {len(rows)}건 {size/1048576:.1f}MB"
                          + (f" (재시도 {attempt})" if attempt else ""))
                return rows, size, None

            reason = f"HTTP {code}" + (" (빈 응답)" if not body.strip() else "")
            return None, size, {"reason": reason, "response_preview": body[:500], "query_sent": clean}

        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            if attempt < retries - 1:
                wait = 2 * (attempt + 1)
                if verbose:
                    print(f"[LP] ⚠️ {last} → {wait}초 후 재시도 ({attempt+1}/{retries})")
                time.sleep(wait)
                continue

    return None, 0, {"reason": f"재시도 {retries}회 실패 ({last})", "query_sent": clean}


def query(lpql: str, timeout: int | None = None,
          cfg: dict | None = None, verbose: bool = True,
          retries: int | None = None):
    """LPQL 실행 → (rows, None) 또는 (None, err).

    rows   : list[dict]  — CSV 헤더를 키로 하는 레코드 목록
    err    : {"reason", "query_sent", ...}
    retries: None 이면 config 값. 헬스체크처럼 즉시 실패가 나은 곳은 1 을 준다.
    """
    rows, _size, err = query_sized(lpql, timeout, cfg, verbose, retries)
    return rows, err


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
