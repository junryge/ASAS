"""
demos_v1/hermes/sessions.py — 세션 로그 + 회상 (LLM 없이 파일 검색)

- sessions/YYYY-MM-DD.jsonl : 1줄 = 1메시지 {ts, role, content, session_id}
- 30일 로테이션 (오래된 파일 삭제)
- search(query): BM25 매칭 + 앞뒤 ±5 메시지 + 세션 첫/끝 3 메시지
"""
from __future__ import annotations
import os
import json
import math
import time
import re
from datetime import datetime, timedelta

from demos_v1.hermes import store

ROTATE_DAYS = 30
CONTEXT_WINDOW = 5      # 매칭 앞뒤 ±N
EDGE_MESSAGES = 3       # 세션 첫/끝 N


def _sessions_dir(user_id: str) -> str:
    d = os.path.join(store.user_dir(user_id), "sessions")
    os.makedirs(d, exist_ok=True)
    return d


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[가-힣]{2,}|[a-z0-9_]{2,}", (text or "").lower())


def append_message(user_id: str, role: str, content: str, session_id: str = "") -> None:
    """메시지 1건을 오늘 jsonl 에 append (원자성보다 append 성능 우선)."""
    if not isinstance(content, str) or not content.strip():
        return
    d = _sessions_dir(user_id)
    path = os.path.join(d, f"{_today()}.jsonl")
    rec = {"ts": time.time(), "role": role, "content": content, "session_id": session_id or ""}
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass
    rotate(user_id)


def rotate(user_id: str) -> int:
    """ROTATE_DAYS 보다 오래된 일자 파일 삭제. 삭제 수 반환."""
    d = _sessions_dir(user_id)
    cutoff = (datetime.now() - timedelta(days=ROTATE_DAYS)).strftime("%Y-%m-%d")
    removed = 0
    for name in os.listdir(d):
        if not name.endswith(".jsonl"):
            continue
        date = name[:-6]
        if date < cutoff:
            try:
                os.remove(os.path.join(d, name))
                removed += 1
            except OSError:
                pass
    return removed


def _load_all(user_id: str) -> list[dict]:
    """모든 메시지를 시간순으로. 각 항목에 date/idx 부여."""
    d = _sessions_dir(user_id)
    if not os.path.isdir(d):
        return []
    out: list[dict] = []
    for name in sorted(os.listdir(d)):
        if not name.endswith(".jsonl"):
            continue
        date = name[:-6]
        try:
            with open(os.path.join(d, name), "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    rec["date"] = date
                    rec["idx"] = i
                    out.append(rec)
        except OSError:
            continue
    return out


def list_recent(user_id: str, limit: int = 10) -> list[dict]:
    """최근 세션 요약 (session_id별 첫 user 메시지)."""
    msgs = _load_all(user_id)
    sessions: dict[str, dict] = {}
    for m in msgs:
        sid = m.get("session_id") or m.get("date")
        s = sessions.setdefault(sid, {"session_id": sid, "date": m.get("date"),
                                       "first_user": "", "count": 0, "last_ts": 0})
        s["count"] += 1
        s["last_ts"] = max(s["last_ts"], m.get("ts", 0))
        if not s["first_user"] and m.get("role") == "user":
            s["first_user"] = (m.get("content") or "")[:80]
    out = list(sessions.values())
    out.sort(key=lambda s: s["last_ts"], reverse=True)
    return out[:limit]


def search(user_id: str, query: str, max_hits: int = 3) -> list[dict]:
    """BM25 로 메시지 검색. 각 히트에 앞뒤 ±CONTEXT_WINDOW + 세션 가장자리 포함."""
    msgs = _load_all(user_id)
    if not msgs or not (query or "").strip():
        return []
    q_terms = _tokenize(query)
    if not q_terms:
        return []

    docs = [_tokenize(m.get("content", "")) for m in msgs]
    N = len(docs)
    avgdl = sum(len(d) for d in docs) / max(1, N)
    df: dict[str, int] = {}
    for d in docs:
        for t in set(d):
            df[t] = df.get(t, 0) + 1

    k1, b = 1.5, 0.75
    scores = []
    for i, d in enumerate(docs):
        if not d:
            scores.append(0.0)
            continue
        tf: dict[str, int] = {}
        for t in d:
            tf[t] = tf.get(t, 0) + 1
        s = 0.0
        dl = len(d)
        for t in q_terms:
            if t not in tf:
                continue
            idf = math.log(1 + (N - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))
            s += idf * (tf[t] * (k1 + 1)) / (tf[t] + k1 * (1 - b + b * dl / avgdl))
        scores.append(s)

    ranked = sorted(range(N), key=lambda i: scores[i], reverse=True)
    hits = []
    used_ranges = []
    for i in ranked:
        if scores[i] <= 0:
            break
        if len(hits) >= max_hits:
            break
        # 같은 구간 중복 방지
        if any(abs(i - u) <= CONTEXT_WINDOW for u in used_ranges):
            continue
        used_ranges.append(i)
        lo = max(0, i - CONTEXT_WINDOW)
        hi = min(N, i + CONTEXT_WINDOW + 1)
        context = [{"role": msgs[j].get("role"), "content": msgs[j].get("content"),
                    "match": j == i} for j in range(lo, hi)]
        hits.append({
            "score": round(scores[i], 3),
            "date": msgs[i].get("date"),
            "session_id": msgs[i].get("session_id"),
            "match": msgs[i].get("content"),
            "context": context,
        })
    return hits
