#!/usr/bin/env python3
"""
real_time_amhs/jupyter_csv.py — 주피터 파일서버에서 발동이벤트 CSV 받아오기

왜
    예측 결과가 주피터 공유 폴더에 날짜별 CSV 로 떨어진다.
        …/predict_tobe/20260811_발동이벤트.csv
    로그프레소를 거치지 않고 이걸 바로 받아 data/YYYYMMDD_TOTAL.CSV 로 넣는다.

인증
    주피터는 보통 비밀번호 로그인이다. 브라우저에서 복사한 URL 의 `_xsrf=…`
    는 그 세션 것이라 금방 만료된다. 그래서 **매번 로그인해서 쿠키를 딴다**.
        GET  /login            → _xsrf 쿠키 확보
        POST /login            → _xsrf + password → 세션 쿠키
        GET  /files/…csv       → 그 쿠키로 내려받기
    토큰 방식(?token=…)만 쓰는 서버면 config 에 token 을 넣으면 그걸 쓴다.

    비밀번호는 세 곳 중 아무 데나 — config.source.jupyter.password (편함) /
    이 폴더의 jupyter_password.txt (.gitignore 됨) / 환경변수 JUPYTER_PASSWORD.
    config.json 은 깃에 올라가니 저장소를 공유하면 뒤 두 개를 쓰는 게 안전하다.

받은 뒤
    통째로 받아서 store_csv.append_rows() 로 넣는다. 이미 있는 시각은
    건너뛰므로 몇 번을 다시 받아도 중복이 안 쌓인다(= 증분 수집이 공짜).

단독 실행
    python jupyter_csv.py                 # 오늘
    python jupyter_csv.py 20260811        # 날짜 지정
    python jupyter_csv.py --check         # 접속·로그인만 확인 (저장 안 함)
    python jupyter_csv.py --raw 20260811  # 원본 그대로 data/raw 에만 저장
    python jupyter_csv.py --list          # 서버에 어느 날짜가 있는지 먼저 본다
    python jupyter_csv.py --backfill all  # 있는 날짜 전부
    python jupyter_csv.py --backfill 30   # 과거 30일 한꺼번에
    python jupyter_csv.py --backfill 20260801 20260811   # 그 구간
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from http.cookiejar import CookieJar

from lp_client import load_config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULTS = {
    "enabled": False,
    "base_url": "",          # 예: http://aiu-amhas-prediction-que.aipp01.skhynix.com
    "path": "",              # 예: /files/pjt_shared_pool/job/…/predict_tobe/{day}_발동이벤트.csv
    "password": "",          # config 에 바로 넣어도 된다 (config.json 은 깃에 올라감)
    "password_file": "jupyter_password.txt",   # 또는 이 파일에 (.gitignore 됨)
    "password_env": "JUPYTER_PASSWORD",        # 또는 환경변수
    "token": "",             # 토큰 방식 서버면 여기에 (?token=)
    "timeout_s": 60,
    "encoding": "utf-8-sig",
    "save_raw": True,        # 받은 원본을 data/raw/ 에 그대로 남긴다
    "verify_min_rows": 1,
}


def cfg_of(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    c = dict(DEFAULTS)
    c.update((cfg.get("source") or {}).get("jupyter") or {})
    return c


# ────────────────────────────── 비밀번호 ──────────────────────────────
def _password(c: dict) -> str:
    """config → 폴더 안 파일 → 환경변수 순.

    config.source.jupyter.password 에 바로 넣어도 된다(운영 편의).
    다만 config.json 은 깃에 올라가므로, 저장소를 공유한다면
    jupyter_password.txt(.gitignore 됨) 나 환경변수 쪽이 안전하다.
    """
    if str(c.get("password") or "").strip():
        return str(c["password"]).strip()
    p = c.get("password_file") or "jupyter_password.txt"
    if not os.path.isabs(p):
        p = os.path.join(BASE_DIR, p)
    # 폴더 밖 경로는 거부 (키 파일과 같은 규칙)
    if os.path.commonpath([os.path.abspath(p), BASE_DIR]) != BASE_DIR:
        print(f"[주피터] ⚠️ password_file 이 폴더 밖을 가리킴 — 무시: {p}")
    elif os.path.isfile(p):
        try:
            with open(p, "r", encoding="utf-8-sig") as f:
                v = f.read().strip()
            if v:
                return v
        except Exception as e:
            print(f"[주피터] ⚠️ 비밀번호 파일 읽기 실패: {e}")
    return os.getenv(c.get("password_env") or "JUPYTER_PASSWORD", "").strip()


# ────────────────────────────── URL ──────────────────────────────
def file_url(day: str, c: dict) -> str:
    """날짜 → 내려받을 URL. path 의 {day} 를 치환하고 한글 파일명을 인코딩한다."""
    base = str(c.get("base_url") or "").rstrip("/")
    path = str(c.get("path") or "")
    if not base or not path:
        raise ValueError("config.source.jupyter 의 base_url / path 가 비어 있습니다")
    path = path.replace("{day}", day)
    # 파일명에 한글이 있으면 그대로 못 보낸다 (경로 구분자 '/' 는 남긴다)
    head, _, qs = path.partition("?")
    head = urllib.parse.quote(head, safe="/%")
    url = base + ("" if head.startswith("/") else "/") + head
    parts = []
    if qs:
        parts.append(qs)
    if c.get("token"):
        parts.append("token=" + urllib.parse.quote(str(c["token"])))
    return url + ("?" + "&".join(parts) if parts else "")


def split_url(url: str) -> tuple[str, str]:
    """브라우저에서 복사한 전체 URL → (base_url, path). 설정 도우미.

    _xsrf 는 그 세션 것이라 떼어낸다 (우리는 매번 로그인해서 새로 딴다).
    날짜(YYYYMMDD)는 {day} 로 바꿔 준다.
    """
    u = urllib.parse.urlsplit(url)
    base = f"{u.scheme}://{u.netloc}"
    path = urllib.parse.unquote(u.path)
    q = [(k, v) for k, v in urllib.parse.parse_qsl(u.query) if k != "_xsrf"]
    path = re.sub(r"\d{8}(?=[^/]*$)", "{day}", path)
    if q:
        path += "?" + urllib.parse.urlencode(q)
    return base, path


# ────────────────────────────── 로그인 ──────────────────────────────
class _Session:
    """쿠키를 들고 다니는 최소 세션."""

    def __init__(self, timeout: int = 60):
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))
        self.timeout = timeout

    def get(self, url: str, headers: dict | None = None):
        req = urllib.request.Request(url, headers=headers or {})
        return self.opener.open(req, timeout=self.timeout)

    def post(self, url: str, data: dict, headers: dict | None = None):
        body = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers=headers or {})
        return self.opener.open(req, timeout=self.timeout)

    def cookie(self, name: str) -> str:
        for ck in self.jar:
            if ck.name == name:
                return ck.value or ""
        return ""


# ── 로그인 세션 재사용 ────────────────────────────────────────────────
# ★기동 한 번에 파일을 일곱 개 받는다(ALL + FAB 다섯 + ML). 그때마다 login()
#   을 다시 부르면 **왕복 두 번**(GET /login 으로 _xsrf, POST /login)이 파일마다
#   붙어서, 내려받기 전에 왕복 열네 번을 먼저 한다. 쿠키는 한 번 받으면 그대로
#   쓸 수 있으니 세션을 들고 있는다.
# ★쿠키는 만료되고 서버가 재시작되기도 한다. 그래서 '캐시가 있으면 끝' 이 아니라
#   **쓰다가 막히면 버리고 다시 로그인**한다(_drop_session). 캐시만 두고 갱신을
#   안 두면, 만료된 순간부터 영영 실패한다.
_SESS: dict = {}
_SESS_TTL = 600          # 10분. 주피터 쿠키보다 짧게 잡아 먼저 갈아 끼운다
_SESS_LOCK = threading.Lock()


def _sess_key(c: dict) -> str:
    """서버 주소 + 자격증명까지 열쇠에 넣는다.

    ★주소만으로 묶었더니, 비밀번호를 고친 뒤에도 **틀린 비밀번호로 만든 세션**
      을 그대로 썼다(거꾸로도 마찬가지 — 틀린 비밀번호인데 예전 세션으로
      받아졌다). 자격증명이 바뀌면 다른 세션이어야 한다.
    ★비밀번호를 그대로 열쇠에 넣지 않는다 — 어딘가 찍히면 그대로 샌다.
    """
    import hashlib
    base = str(c.get("base_url") or "").rstrip("/")
    if not base:
        return ""
    cred = (_password(c) or "") + "\x00" + str(c.get("token") or "")
    return base + "#" + hashlib.sha256(cred.encode()).hexdigest()[:16]


def _drop_session(c: dict) -> None:
    """이 서버의 세션을 버린다 — 다음 호출이 새로 로그인한다."""
    with _SESS_LOCK:
        _SESS.pop(_sess_key(c), None)


def login(c: dict, fresh: bool = False) -> tuple["_Session | None", str]:
    """로그인 세션 — 캐시가 살아 있으면 그대로 쓴다.

    ★락을 **로그인 전체**에 건다 (예전엔 dict 를 만질 때만 걸었다).
      여섯 시스템을 동시에 받기 시작하면서, 캐시가 비어 있는 순간 여섯
      스레드가 각자 로그인을 하러 갔다 — 왕복 두 번짜리가 여섯 벌이다.
      한 놈이 하는 동안 나머지는 기다렸다가 그 결과를 같이 쓴다.
    """
    key = _sess_key(c)
    with _SESS_LOCK:
        if not fresh:
            hit = _SESS.get(key)
            if hit and (time.time() - hit[1]) < _SESS_TTL:
                return hit[0], ""
        s, err = _login_fresh(c)
        if err:
            return None, err
        _SESS[key] = (s, time.time())
        return s, ""


def _login_fresh(c: dict) -> tuple["_Session | None", str]:
    s = _Session(int(c.get("timeout_s", 60)))
    base = str(c.get("base_url") or "").rstrip("/")
    if not base:
        return None, "config.source.jupyter.base_url 이 비어 있습니다"

    pw = _password(c)
    if not pw:
        # 토큰만으로 되는 서버도 있다 — 일단 그대로 진행하고 받아보며 판단
        return s, ""

    try:
        s.get(base + "/login")                       # _xsrf 쿠키 받기
    except urllib.error.HTTPError as e:
        if e.code not in (403, 404):                  # 로그인 페이지가 없을 수도
            return None, f"로그인 페이지 접속 실패 HTTP {e.code}"
    except Exception as e:
        return None, f"접속 실패: {type(e).__name__}: {e}"

    xsrf = s.cookie("_xsrf")
    data = {"password": pw}
    if xsrf:
        data["_xsrf"] = xsrf
    try:
        r = s.post(base + "/login", data,
                   {"Content-Type": "application/x-www-form-urlencoded",
                    "X-XSRFToken": xsrf} if xsrf else
                   {"Content-Type": "application/x-www-form-urlencoded"})
        body = r.read(4000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return None, f"로그인 실패 HTTP {e.code}"
    except Exception as e:
        return None, f"로그인 실패: {type(e).__name__}: {e}"

    # 주피터는 비밀번호가 틀려도 200 + 로그인 폼을 다시 준다
    if "password" in body.lower() and "invalid" in body.lower():
        return None, "비밀번호가 틀립니다"
    return s, ""


# ────────────────────────────── 내려받기 ──────────────────────────────
# ── 하루치 파일은 **덧붙기만 한다** — 그러니 꼬리만 받는다 ────────────────
# ★이게 '데이터가 느리다' 의 진짜 원인이었다. 예측 잡이 1분에 한 줄을 덧붙이는
#   파일을, 우리는 매 주기마다 **처음부터 끝까지** 다시 받고 있었다. 오후가
#   되면 한 파일이 1.5MB 쯤 되는데 시스템이 여섯이라 1분에 9MB 를 받아 새 줄
#   여섯 개를 얻었다. 하루로 치면 13GB 다.
# ★그래서 Range 로 **마지막으로 받은 자리부터** 달라고 한다. 다만 그냥 이어
#   붙이면 위험하다 — 예측 잡이 파일을 통째로 다시 썼다면 앞부분이 달라져
#   있는데 우리는 모르고 꿰맨다. 그래서 **이미 가진 꼬리 512바이트를 같이**
#   받아서, 그 자리가 똑같은지 확인하고 이어 붙인다. 하나라도 어긋나면 그냥
#   전체를 다시 받는다 (틀린 데이터보다 느린 게 낫다).
# ★이어 붙인 결과는 전체를 받은 것과 **바이트까지 같다.** 그래서 파싱·저장·
#   원본보관 등 아래 모든 것이 하나도 안 달라진다 — 줄어드는 건 통신량뿐이다.
# ★겹침 검사만으로는 부족하다. 시험을 쓰다가 잡았다 —
#   파일을 **같은 길이로** 다시 쓰면서 앞부분 값만 바꾸면(44→45), 꼬리는
#   그대로라 검사를 통과하고 우리는 옛 본문을 그대로 들고 있게 된다.
#   조용히 틀린 데이터가 된다. 그래서 두 가지를 더 건다:
#     ① **자랐을 때만** 이어 붙인다 (Content-Range 의 전체 크기로 판단).
#        덧붙기가 아니면 이어 붙일 근거가 없다 — 전체를 다시 받는다.
#     ② 그래도 '자라면서 앞부분도 바뀐' 경우가 남는다. 매번 확인할 길이
#        없으니 **몇 번에 한 번은 전체를 다시 읽어** 맞춰 놓는다.
#        어긋나 있어도 그 몇 분 안에 제자리로 돌아온다.
_TAIL_OVERLAP = 512          # 이어 붙이는 자리를 검사할 겹침
_TAIL_FULL_EVERY = 10        # 이만큼마다 한 번은 전체를 받는다 (config 로 덮음)
_BODY: dict = {}             # {세션키: (day, 마지막으로 받은 전체 원문, 이어붙인 횟수)}
_BODY_LOCK = threading.Lock()
_CR_RE = re.compile(r"bytes\s+(\d+)-(\d+)/(\d+)")
# 마지막 한 번이 실제로 몇 바이트를 받았나 (로그가 '꼬리 12KB/1.5MB' 라고 말한다)
_LAST_WIRE: dict = {}


def _body_get(key: str, day: str) -> tuple[bytes, int]:
    """(마지막으로 받은 전체 원문, 이어 붙인 횟수) — 날짜가 다르면 빈 것."""
    with _BODY_LOCK:
        d, raw, n = _BODY.get(key) or ("", b"", 0)
    return (raw, n) if d == day else (b"", 0)


def _body_put(key: str, day: str, raw: bytes, n: int = 0) -> None:
    # 날짜마다 쌓아 두지 않는다 — 시스템당 한 벌(오늘치)만 들고 있는다
    with _BODY_LOCK:
        _BODY[key] = (day, raw, n)


def _body_drop(key: str) -> None:
    with _BODY_LOCK:
        _BODY.pop(key, None)


def wire_bytes(c: dict | None = None) -> tuple[int, int]:
    """마지막 내려받기의 (실제 통신 바이트, 전체 파일 바이트)."""
    return _LAST_WIRE.get(_sess_key(c or {}), (0, 0))


def download(day: str, cfg: dict | None = None) -> tuple[bytes | None, str]:
    """그 날짜 CSV 원문 → (bytes, 오류).

    ★세션은 재사용한다(login 캐시). 쿠키가 만료되면 403 이 오거나 CSV 대신
      로그인 HTML 이 오는데, 그때는 **버리고 한 번 다시 로그인**해서 재시도한다.
    """
    cfg = cfg or load_config()
    c = cfg_of(cfg)
    return _download_once(day, c, fresh=False)


def _download_once(day: str, c: dict, fresh: bool,
                   full: bool = False) -> tuple[bytes | None, str]:
    s, err = login(c, fresh=fresh)
    if err:
        return None, err
    url = file_url(day, c)
    key = _sess_key(c)
    every = int(c.get("tail_full_every", _TAIL_FULL_EVERY) or 0)
    have, spliced = _body_get(key, day)
    # every=3 이면 '세 번 받을 때 한 번은 전체' — 이어 붙이기는 연달아 두 번까지
    if full or not c.get("tail_fetch", True) or (every and spliced >= every - 1):
        have, spliced = b"", 0       # 전체로 받는다 (주기적 맞춤 포함)
    hdr, at = {}, 0
    if len(have) > _TAIL_OVERLAP:
        at = len(have) - _TAIL_OVERLAP
        hdr["Range"] = f"bytes={at}-"
    try:
        r = s.get(url, hdr or None)
        raw = r.read()
        code = getattr(r, "status", None) or r.getcode()
        if at and code == 206:
            cr = _CR_RE.search(r.headers.get("Content-Range") or "")
            total = int(cr.group(3)) if cr else 0
            # ★'덧붙었는가' 와 '이은 자리가 같은가' 를 **둘 다** 본다.
            #   자라지 않았는데 이어 붙이면, 같은 길이로 다시 쓴 파일을
            #   옛 내용 그대로 들고 있게 된다 (실제로 시험이 잡았다).
            if total <= len(have) or raw[:_TAIL_OVERLAP] != have[at:]:
                _body_drop(key)
                return _download_once(day, c, fresh, full=True)
            _LAST_WIRE[key] = (len(raw), total)
            raw = have + raw[_TAIL_OVERLAP:]
            spliced += 1
        else:
            # 206 이 아니면 서버가 Range 를 무시하고 전체를 준 것이다 — 그대로 쓴다
            _LAST_WIRE[key] = (len(raw), len(raw))
            spliced = 0
    except urllib.error.HTTPError as e:
        if e.code == 416 and at:        # 파일이 줄었다 (다시 쓰는 중) — 전체로
            _body_drop(key)
            return _download_once(day, c, fresh, full=True)
        body = e.read(300).decode("utf-8", "replace")
        hint = ""
        if e.code in (403, 302):
            if not fresh:                  # 쿠키가 만료됐을 수 있다 — 한 번만
                _drop_session(c)
                return _download_once(day, c, fresh=True, full=full)
            hint = " — 로그인이 안 됐을 수 있습니다 (비밀번호 파일 확인)"
        elif e.code == 404:
            hint = " — 그 날짜 파일이 아직 없을 수 있습니다"
        return None, f"HTTP {e.code}{hint}: {body[:200]}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

    # 로그인 실패면 CSV 대신 HTML 로그인 페이지가 온다 — 조용히 넘기면 안 된다
    head = raw[:400].lstrip().lower()
    if head.startswith(b"<!doctype html") or head.startswith(b"<html"):
        if not fresh:                      # 쿠키 만료 → 로그인 폼이 온 것
            _drop_session(c)
            _body_drop(key)
            return _download_once(day, c, fresh=True, full=True)
        _body_drop(key)
        return None, "CSV 가 아니라 HTML 이 왔습니다 — 로그인 실패로 보입니다"
    _body_put(key, day, raw, spliced)
    return raw, ""


def parse_csv(raw: bytes, c: dict) -> list[dict]:
    """CSV bytes → 행 목록. 인코딩은 설정 → utf-8-sig → cp949 순으로 시도."""
    encs = [c.get("encoding") or "utf-8-sig", "utf-8-sig", "utf-8", "cp949"]
    text = None
    for e in encs:
        try:
            text = raw.decode(e)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if text is None:
        text = raw.decode("utf-8", "replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    # 헤더 앞 BOM 잔재 제거 (엑셀로 만든 파일에서 흔하다)
    return [{(k or "").lstrip("﻿").strip(): v for k, v in r.items()} for r in rows]


def _fab_rows(rows: list[dict], sys: str) -> list[dict]:
    """FAB 파일의 행을 **받는 순간** 공통 형태로 정규화한다.

    FAB 파일에는 전체 시스템 점수(unified_risk_score=전체, hot_area=전체 기준)
    가 그대로 들어 있고, 그 FAB 자신의 점수는 **area_score / area_level** 이다.
    여기서 안 바꾸면 M14 화면이 전체 점수로 등급을 매기고, 케이스 area 가
    M16HUB 로 찍힌다 — 화면 전체가 남의 데이터를 보게 된다.

    한 번만, 여기서만 바꾼다. 그러면 그래프·예보·기여도·리포트·정확도 등
    unified_risk_score / hot_area 를 읽는 **모든 하위 모듈이 수정 없이** 그대로
    동작한다 (기여도는 {sys}_pts_* 컬럼을 hot_area 로 찾는데, 정규화된
    hot_area=sys 라 FAB 파일의 자기 컬럼과 정확히 맞아떨어진다).

    원본은 all_* 로 남긴다 — 전체 대비 얼마나 다른지 비교할 수 있게.

    ★area_score 가 **비어 있으면 그 행을 버린다**. 예전엔 "0" 으로 채웠는데,
      그러면 모르는 분이 화면에 **0점 정상**으로 뜬다 — 모르는 것과 괜찮은
      것은 다르다(fab_score 도 같은 이유로 근거 없는 FAB 은 아예 안 넣는다).
      버린 수는 세어서 돌려준다 — 조용히 사라지면 그게 더 나쁘다.
    ★area_score **컬럼 자체가 없으면** 전체 점수가 그대로 남아 M14 화면에
      M16HUB 점수가 뜬다. 그건 0 보다 나쁘다 — 그 파일은 통째로 안 쓴다.
    """
    if rows and "area_score" not in rows[0]:
        return []                      # 부른 쪽이 '행 0개' 로 알아채고 알린다
    kept, dropped = [], 0
    for r in rows:
        if str(r.get("area_score") or "").strip() == "":
            dropped += 1
            continue
        r["all_hot_area"] = r.get("hot_area") or ""
        r["hot_area"] = sys
        r["all_score"] = r.get("unified_risk_score") or ""
        r["unified_risk_score"] = str(r["area_score"]).strip()
        if "area_level" in r:
            r["all_level"] = r.get("unified_risk_level") or ""
            r["unified_risk_level"] = r.get("area_level") or ""
        kept.append(r)
    _fab_rows.dropped = dropped        # fetch_day 가 읽어 경고로 올린다
    return kept


_fab_rows.dropped = 0


def _save_raw(day: str, raw: bytes, cfg: dict) -> str:
    from store_csv import data_dir
    d = os.path.join(data_dir(cfg), "raw")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{day}_발동이벤트.csv")
    with open(p, "wb") as f:
        f.write(raw)
    return p


def fetch_day(day: str = "", cfg: dict | None = None,
              verbose: bool = True) -> dict:
    """그 날짜 CSV 를 받아 data/YYYYMMDD_TOTAL.CSV 에 누적.

    통째로 받아서 넣지만 이미 있는 시각은 append_rows 가 건너뛰므로
    몇 번을 다시 돌려도 중복이 안 쌓인다 (증분 수집이 공짜로 된다).
    """
    cfg = cfg or load_config()
    c = cfg_of(cfg)
    day = "".join(ch for ch in str(day or "") if ch.isdigit())[:8] \
        or datetime.now().strftime("%Y%m%d")

    if verbose:
        print(f"📥 주피터에서 {day} 발동이벤트 CSV 받는 중…")
    raw, err = download(day, cfg)
    if err:
        if verbose:
            print(f"  ❌ {err}")
        return {"ok": False, "day": day, "error": err, "rows": 0, "written": 0}

    raw_path = _save_raw(day, raw, cfg) if c.get("save_raw", True) else ""
    rows = parse_csv(raw, c)
    fab = str(cfg.get("_sys") or "").strip().upper()
    warn = ""
    if fab and fab != "ALL":
        n0 = len(rows)
        _fab_rows.dropped = 0
        rows = _fab_rows(rows, fab)        # ★FAB 파일은 여기서 정규화된다
        if n0 and not rows and not _fab_rows.dropped:
            msg = (f"{fab} 파일에 area_score 컬럼이 없습니다 — 그대로 쓰면 "
                   f"{fab} 화면에 **전체 점수**가 뜹니다. 예측기 쪽 컬럼을 "
                   f"확인해 주세요")
            if verbose:
                print(f"  ❌ {msg}")
            return {"ok": False, "day": day, "error": msg,
                    "rows": 0, "written": 0, "raw_path": raw_path}
        if _fab_rows.dropped:
            warn = (f"{fab} area_score 가 빈 {_fab_rows.dropped}행을 건너뛰었습니다 "
                    f"(0 으로 채우면 화면에 '0점 정상' 으로 뜹니다)")
            if verbose:
                print(f"  ⚠️ {warn}")
    if len(rows) < int(c.get("verify_min_rows", 1)):
        msg = f"내려받았지만 행이 {len(rows)}개뿐입니다 ({len(raw)}바이트)"
        if verbose:
            print(f"  ⚠️ {msg}")
        return {"ok": False, "day": day, "error": msg,
                "rows": len(rows), "written": 0, "raw_path": raw_path}

    from store_csv import append_rows
    saved = append_rows(rows, cfg)
    out = {"ok": True, "day": day, "bytes": len(raw), "rows": len(rows),
           "warn": warn or None,
           "written": saved["written"], "skipped": saved["skipped"],
           "files": saved.get("files") or [], "raw_path": raw_path,
           # 파싱한 행을 그대로 넘긴다 — 호출부가 CSV 를 다시 읽을 필요가 없고,
           # 파일명 날짜와 행의 날짜가 어긋나도(자정 전후·전날 꼬리 포함) 안전하다.
           "data": rows,
           "at": datetime.now().isoformat(timespec="seconds")}
    if verbose:
        print(f"  ✅ {len(rows)}행 수신 · 새로 {saved['written']}행 저장 "
              f"· 중복 {saved['skipped']}행 건너뜀"
              + (f" → {', '.join(out['files'])}" if out["files"] else ""))
        if raw_path:
            print(f"     원본: {os.path.relpath(raw_path, BASE_DIR)}")
    return out


def list_days(cfg: dict | None = None) -> tuple[list[dict], str]:
    """서버에 실제로 있는 날짜 파일 목록 → ([{day, name, size, mtime}], 오류).

    주피터의 목록 API 를 쓴다: GET /api/contents/<폴더>?content=1
    과거를 받기 전에 **어느 날짜가 있는지** 먼저 봐야 헛돌지 않는다
    (예측 잡이 오래된 파일을 지우는 경우가 흔하다).
    """
    cfg = cfg or load_config()
    c = cfg_of(cfg)
    base = str(c.get("base_url") or "").rstrip("/")
    path = str(c.get("path") or "")
    if not base or not path:
        return [], "config.source.jupyter 의 base_url / path 가 비어 있습니다"

    # path 에서 폴더만 떼어낸다. '/files/' 접두는 목록 API 에선 안 쓴다.
    folder = path.partition("?")[0].rsplit("/", 1)[0]
    for pre in ("/files/", "/lab/tree/", "/tree/", "/view/"):
        if folder.startswith(pre):
            folder = "/" + folder[len(pre):]
            break
    api = base + "/api/contents" + urllib.parse.quote(folder, safe="/%") + "?content=1"

    s, err = login(c)
    if err:
        return [], err
    try:
        raw = s.get(api, {"Accept": "application/json"}).read()
        data = json.loads(raw.decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return [], (f"목록 조회 실패 HTTP {e.code} — 이 서버는 목록 API 를 "
                    f"막아 뒀을 수 있습니다. 날짜를 직접 지정해 받으세요")
    except Exception as e:
        return [], f"목록 조회 실패: {type(e).__name__}: {e}"

    items = data.get("content")
    if not isinstance(items, list):
        return [], "목록 응답 형식이 예상과 다릅니다"
    out = []
    for it in items:
        name = str(it.get("name") or "")
        m = re.match(r"(\d{8})", name)
        if m and name.lower().endswith(".csv"):
            out.append({"day": m.group(1), "name": name,
                        "size": it.get("size"),
                        "mtime": (it.get("last_modified") or "")[:19]})
    out.sort(key=lambda d: d["day"])
    return out, ""


def backfill(days: list[str] | None = None, cfg: dict | None = None,
             back: int = 0, verbose: bool = True) -> dict:
    """과거 날짜를 한꺼번에 받아 채운다.

    days 를 주면 그 날짜들, 없으면 오늘부터 back 일 전까지.
    이미 저장된 날도 다시 받는다 — 같은 시각은 건너뛰지만, 컬럼이 모자란
    옛 파일은 append_rows 가 헤더를 넓혀 주므로 이 참에 정리된다.
    없는 날짜(404)는 건너뛰고 계속한다 — 중간에 멈추면 안 된다.
    """
    from datetime import timedelta
    cfg = cfg or load_config()
    if not days:
        n = max(1, int(back or 7))
        today = datetime.now()
        days = [(today - timedelta(days=i)).strftime("%Y%m%d")
                for i in range(n)][::-1]
    days = ["".join(ch for ch in str(d) if ch.isdigit())[:8] for d in days]

    ok, miss, fail, written = [], [], [], 0
    for d in days:
        r = fetch_day(d, cfg, verbose=False)
        if r.get("ok"):
            ok.append(d)
            written += r["written"]
            if verbose:
                print(f"  ✅ {d}  {r['rows']}행 · 신규 {r['written']} · "
                      f"중복 {r['skipped']}")
        elif "404" in str(r.get("error")):
            miss.append(d)
            if verbose:
                print(f"  ·  {d}  (파일 없음 — 건너뜀)")
        else:
            fail.append({"day": d, "error": r.get("error")})
            if verbose:
                print(f"  ❌ {d}  {str(r.get('error'))[:80]}")
    if verbose:
        print(f"\n받음 {len(ok)}일 · 신규 {written}행 · 없음 {len(miss)}일 "
              f"· 실패 {len(fail)}일")
    return {"ok": not fail, "days": ok, "missing": miss, "failed": fail,
            "written": written}


def check(cfg: dict | None = None) -> dict:
    """접속·로그인·URL 만 확인 (저장 안 함) — 설정 맞췄는지 볼 때."""
    cfg = cfg or load_config()
    c = cfg_of(cfg)
    day = datetime.now().strftime("%Y%m%d")
    out = {"enabled": bool(c.get("enabled")), "base_url": c.get("base_url"),
           "url": "", "password": bool(_password(c)), "login": "", "download": ""}
    try:
        out["url"] = file_url(day, c)
    except Exception as e:
        out["url"] = f"(URL 조립 실패: {e})"
        return out
    s, err = login(c)
    out["login"] = err or "ok"
    if err:
        return out
    raw, err2 = download(day, cfg)
    out["download"] = err2 or f"ok ({len(raw)}바이트)"
    return out


if __name__ == "__main__":
    import sys
    args = [a for a in sys.argv[1:]]
    # --sys M14 → 그 FAB 의 파일(fab분리 폴더)·저장 폴더(data/M14)로 동작.
    #   과거 데이터를 FAB 별로 채울 때: python jupyter_csv.py --backfill all --sys M14
    CLI_CFG = load_config()
    if "--sys" in args:
        i = args.index("--sys")
        from lp_client import sys_cfg
        CLI_CFG = sys_cfg(CLI_CFG, args[i + 1])
        del args[i:i + 2]
        if CLI_CFG.get("_sys"):
            print(f"[시스템] {CLI_CFG['_sys']} — 저장: "
                  f"{CLI_CFG['storage']['daily_csv_dir']}/")
    if "--help" in args or "-h" in args:
        print(__doc__)
        raise SystemExit(0)
    if "--check" in args:
        print(json.dumps(check(CLI_CFG), ensure_ascii=False, indent=2))
        raise SystemExit(0)
    if "--url" in args:                      # 브라우저 URL → config 값 뽑아주기
        i = args.index("--url")
        b, p = split_url(args[i + 1])
        print(json.dumps({"base_url": b, "path": p}, ensure_ascii=False, indent=2))
        raise SystemExit(0)
    if "--list" in args:
        items, err = list_days(CLI_CFG)
        if err:
            print("❌", err)
            raise SystemExit(1)
        print(f"서버에 있는 날짜 파일 {len(items)}개")
        for it in items:
            sz = it["size"]
            print(f"  {it['day']}  {it['name']}"
                  + (f"  {sz/1024:.0f}KB" if isinstance(sz, (int, float)) else "")
                  + (f"  {it['mtime']}" if it["mtime"] else ""))
        raise SystemExit(0)
    if "--backfill" in args:
        i = args.index("--backfill")
        if "all" in args[i + 1:i + 2]:
            items, err = list_days(CLI_CFG)
            if err:
                print("❌", err)
                raise SystemExit(1)
            ds = [it["day"] for it in items]
            print(f"📥 서버에 있는 {len(ds)}일 전부 받는 중…")
            r = backfill(ds, CLI_CFG)
            raise SystemExit(0 if r["ok"] else 1)
        rest = [a for a in args[i + 1:] if a.isdigit()]
        if len(rest) >= 2 and len(rest[0]) == 8 and len(rest[1]) == 8:
            from datetime import timedelta
            d0 = datetime.strptime(rest[0], "%Y%m%d")
            d1 = datetime.strptime(rest[1], "%Y%m%d")
            span = [(d0 + timedelta(days=k)).strftime("%Y%m%d")
                    for k in range((d1 - d0).days + 1)]
            print(f"📥 {rest[0]}~{rest[1]} {len(span)}일 받는 중…")
            r = backfill(span, CLI_CFG)
        else:
            n = int(rest[0]) if rest else 7
            print(f"📥 최근 {n}일 받는 중…")
            r = backfill(None, CLI_CFG, back=n)
        raise SystemExit(0 if r["ok"] else 1)
    day = next((a for a in args if a.isdigit()), "")
    if "--raw" in args:
        cfg = CLI_CFG
        d = "".join(ch for ch in (day or datetime.now().strftime("%Y%m%d"))
                    if ch.isdigit())[:8]
        raw, err = download(d, cfg)
        print(err or f"{len(raw)}바이트 → {_save_raw(d, raw, cfg)}")
    else:
        r = fetch_day(day, CLI_CFG)
        raise SystemExit(0 if r.get("ok") else 1)
