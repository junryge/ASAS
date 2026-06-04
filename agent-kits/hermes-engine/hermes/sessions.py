"""
hermes/sessions.py — 세션 로그 + 회상 (LLM 없이 파일 BM25)

- sessions/YYYY-MM-DD.jsonl : 1줄 = 1메시지, 30일 로테이션
- search(query): BM25 매칭 + 앞뒤 ±5 메시지
"""
from __future__ import annotations
import os
import json
import math
import time
import re
from datetime import datetime, timedelta

from . import store

ROTATE_DAYS = 30
CONTEXT_WINDOW = 5


def _dir(user_id: str) -> str:
    d = os.path.join(store.user_dir(user_id), "sessions")
    os.makedirs(d, exist_ok=True)
    return d


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _tok(text: str) -> list[str]:
    return re.findall(r"[가-힣]{2,}|[a-z0-9_]{2,}", (text or "").lower())


def append_message(user_id: str, role: str, content: str, session_id: str = "") -> None:
    if not isinstance(content, str) or not content.strip():
        return
    path = os.path.join(_dir(user_id), f"{_today()}.jsonl")
    rec = {"ts": time.time(), "role": role, "content": content, "session_id": session_id or ""}
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass
    rotate(user_id)


def rotate(user_id: str) -> int:
    d = _dir(user_id)
    cutoff = (datetime.now() - timedelta(days=ROTATE_DAYS)).strftime("%Y-%m-%d")
    removed = 0
    for name in os.listdir(d):
        if name.endswith(".jsonl") and name[:-6] < cutoff:
            try:
                os.remove(os.path.join(d, name))
                removed += 1
            except OSError:
                pass
    return removed


def _load_all(user_id: str) -> list[dict]:
    d = _dir(user_id)
    out = []
    for name in sorted(os.listdir(d)):
        if not name.endswith(".jsonl"):
            continue
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
                    rec["date"] = name[:-6]
                    rec["idx"] = i
                    out.append(rec)
        except OSError:
            continue
    return out


def list_recent(user_id: str, limit: int = 10) -> list[dict]:
    msgs = _load_all(user_id)
    sess: dict[str, dict] = {}
    for m in msgs:
        sid = m.get("session_id") or m.get("date")
        s = sess.setdefault(sid, {"session_id": sid, "date": m.get("date"),
                                  "first_user": "", "count": 0, "last_ts": 0})
        s["count"] += 1
        s["last_ts"] = max(s["last_ts"], m.get("ts", 0))
        if not s["first_user"] and m.get("role") == "user":
            s["first_user"] = (m.get("content") or "")[:80]
    out = list(sess.values())
    out.sort(key=lambda s: s["last_ts"], reverse=True)
    return out[:limit]


def search(user_id: str, query: str, max_hits: int = 3) -> list[dict]:
    msgs = _load_all(user_id)
    q_terms = _tok(query)
    if not msgs or not q_terms:
        return []
    docs = [_tok(m.get("content", "")) for m in msgs]
    N = len(docs)
    avgdl = sum(len(d) for d in docs) / max(1, N)
    df: dict[str, int] = {}
    for d in docs:
        for t in set(d):
            df[t] = df.get(t, 0) + 1
    k1, b = 1.5, 0.75
    scores = []
    for d in docs:
        if not d:
            scores.append(0.0)
            continue
        tf: dict[str, int] = {}
        for t in d:
            tf[t] = tf.get(t, 0) + 1
        s, dl = 0.0, len(d)
        for t in q_terms:
            if t in tf:
                idf = math.log(1 + (N - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))
                s += idf * (tf[t] * (k1 + 1)) / (tf[t] + k1 * (1 - b + b * dl / avgdl))
        scores.append(s)
    ranked = sorted(range(N), key=lambda i: scores[i], reverse=True)
    hits, used = [], []
    for i in ranked:
        if scores[i] <= 0 or len(hits) >= max_hits:
            break
        if any(abs(i - u) <= CONTEXT_WINDOW for u in used):
            continue
        used.append(i)
        lo, hi = max(0, i - CONTEXT_WINDOW), min(N, i + CONTEXT_WINDOW + 1)
        ctx = [{"role": msgs[j].get("role"), "content": msgs[j].get("content"),
                "match": j == i} for j in range(lo, hi)]
        hits.append({"score": round(scores[i], 3), "date": msgs[i].get("date"),
                     "session_id": msgs[i].get("session_id"),
                     "match": msgs[i].get("content"), "context": ctx})
    return hits
