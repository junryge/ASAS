# -*- coding: utf-8 -*-
"""화면이 느린 세 가지 원인을 한자리에서 막는다 — 같은 것을 두 번 만들지 않기.

★왜 만들었나 (2026-09-18 현장 로그 · 실제로 재 본 숫자)
  개발 PC 에서 하루치(1440행)를 놓고 쟀다:
    · /api/feed 한 번 만드는 데 ~300ms, 그 응답이 **1.5MB**
    · 화면은 **3초마다** 묻는데 데이터는 **60초에 한 번** 바뀐다
    · 관제 화면이 셋 붙어 있으면, 파일이 바뀌는 그 순간 셋이 **동시에**
      같은 것을 만든다 (캐시 우르르 — stampede)
  그래서 현장에서 feed 7~17초, fab/compare 18~20초가 찍혔다. 계산이 느린 게
  아니라 **같은 계산을 여러 번, 여러 스레드가 겹쳐서** 한 것이다.

★세 가지
  ① 다 만든 **글자(bytes)** 를 들고 있는다. 예전엔 dict 를 캐시해 두고 적중해도
     jsonify 가 매번 1.5MB 를 다시 만들었다 (그것만 23ms + GIL 점유).
  ② **ETag / 304** — 원본이 그대로면 브라우저에 "그대로다" 한 줄만 보낸다.
     3초마다 묻지만 60초에 한 번만 실제로 내려간다 (스무 번 중 열아홉 번은 공짜).
  ③ **단일 실행(single-flight)** — 같은 것을 동시에 요청하면 하나만 만들고
     나머지는 그 결과를 나눠 쓴다.
  덤으로 gzip 을 한 번만 눌러 같이 들고 있는다 (1.5MB → 100KB 대).

★점수·등급·판정은 하나도 안 건드린다. 만든 것을 **어떻게 들고 있다가
  어떻게 내주느냐** 만 다룬다.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import threading
import time

GZIP_MIN = 8 * 1024          # 이보다 작으면 눌러도 의미가 없다
GZIP_LEVEL = 6               # 속도/크기 절충 (9 는 CPU 만 먹고 몇 % 못 줄인다)


def dumps(obj) -> bytes:
    """응답 본문 만들기 — 한글을 그대로 둔다.

    ★ensure_ascii=True 면 한글 한 글자가 \\uXXXX 여섯 자가 된다. 같은 내용이
      2~3배로 부푼다 — 1.5MB 짜리 응답에서는 그게 그대로 전송 시간이다.
      Content-Type 에 charset=utf-8 을 붙여 내보내므로 브라우저는 그대로 읽는다.
    """
    # ★이미 바이트면 그대로 — HTML 한 장처럼 JSON 이 아닌 응답도 같은 캐시
    #   (지문·304·gzip·한 번만 만들기)를 쓰려고 열어 둔다.
    if isinstance(obj, (bytes, bytearray)):
        return bytes(obj)
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def etag_of(body: bytes) -> str:
    """본문 지문. 약한 해시로 충분하다 — 보안이 아니라 '같은가' 만 본다."""
    return 'W/"%s"' % hashlib.blake2b(body, digest_size=16).hexdigest()


def gzipped(body: bytes) -> bytes:
    return gzip.compress(body, GZIP_LEVEL)


class Entry:
    """한 번 만든 응답 — 원문·gzip·지문·만든 시각."""

    __slots__ = ("sig", "body", "etag", "at", "_gz")

    def __init__(self, sig, body: bytes):
        self.sig = sig
        self.body = body
        self.etag = etag_of(body)
        self.at = time.time()
        self._gz = None

    def gz(self) -> bytes | None:
        """gzip 본문 — 처음 물을 때 한 번만 누른다 (그 뒤로는 공짜)."""
        if len(self.body) < GZIP_MIN:
            return None
        if self._gz is None:
            self._gz = gzipped(self.body)
        return self._gz


class JsonCache:
    """키마다 마지막 응답 하나. 지문(sig)이 같으면 그대로 내준다.

    sig 는 '원본이 그대로인가' 를 말하는 아무 값이나 된다 — 보통 파일의
    (mtime, size) 와 설정 지문을 묶은 튜플이다. sig 가 None 이면 캐시를
    쓰지 않는다 (원본을 못 읽은 상황 — 옛 값을 새 값인 척 내면 안 된다).
    """

    def __init__(self, name: str = ""):
        self.name = name
        self._e: dict[str, Entry] = {}
        self._lock = threading.Lock()              # _e 를 지키는 짧은 락
        self._build: dict[str, threading.Lock] = {}   # 키마다 '만드는 중' 락
        self.hits = self.misses = self.joined = 0

    def peek(self, key: str, sig):
        with self._lock:
            e = self._e.get(key)
        return e if (e is not None and sig is not None and e.sig == sig) else None

    def get_or_build(self, key: str, sig, build) -> Entry:
        """지문이 같으면 그대로, 아니면 만든다. **같은 키는 한 번만 만든다.**

        build() 는 파이썬 객체를 돌려주면 된다 (여기서 bytes 로 바꾼다).
        """
        e = self.peek(key, sig)
        if e is not None:
            self.hits += 1
            return e
        if sig is None:                            # 캐시 못 씀 — 그냥 만든다
            self.misses += 1
            return Entry(None, dumps(build()))

        with self._lock:
            bl = self._build.get(key)
            if bl is None:
                bl = self._build[key] = threading.Lock()
        first = bl.acquire(blocking=False)
        if not first:
            # 다른 스레드가 같은 것을 만들고 있다 — 기다렸다 그 결과를 쓴다
            bl.acquire()
            try:
                e = self.peek(key, sig)
                if e is not None:
                    self.joined += 1
                    return e
            finally:
                bl.release()
            # 그새 원본이 또 바뀌었다 — 내가 만든다
            return self.get_or_build(key, sig, build)
        try:
            e = self.peek(key, sig)                # 기다리는 동안 누가 만들었나
            if e is not None:
                self.hits += 1
                return e
            self.misses += 1
            e = Entry(sig, dumps(build()))
            with self._lock:
                self._e[key] = e
            return e
        finally:
            bl.release()

    def stats(self) -> dict:
        tot = self.hits + self.misses + self.joined
        return {"name": self.name, "keys": len(self._e), "hits": self.hits,
                "misses": self.misses, "joined": self.joined,
                "hit_rate": round((self.hits + self.joined) / tot, 3) if tot else 0.0}


def negotiate(entry: Entry, if_none_match: str | None,
              accept_encoding: str | None) -> tuple[int, bytes, dict]:
    """(상태코드, 본문, 헤더) — 브라우저가 이미 같은 것을 갖고 있으면 304.

    ★304 는 본문이 없다. 3초마다 묻는 화면에서 이게 제일 크게 듣는다.
    """
    h = {"ETag": entry.etag,
         # no-cache = '쓰기 전에 물어봐라' (안 쓰겠다는 뜻이 아니다).
         # 그래야 브라우저가 If-None-Match 를 들고 와서 304 를 받는다.
         "Cache-Control": "no-cache",
         "Content-Type": "application/json; charset=utf-8"}
    if if_none_match and entry.etag in [t.strip() for t in if_none_match.split(",")]:
        return 304, b"", h
    body = entry.body
    if "gzip" in (accept_encoding or "").lower():
        gz = entry.gz()
        if gz is not None and len(gz) < len(body):
            body, h["Content-Encoding"] = gz, "gzip"
            h["Vary"] = "Accept-Encoding"
    h["Content-Length"] = str(len(body))
    return 200, body, h
