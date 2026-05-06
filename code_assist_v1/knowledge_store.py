"""
code_assist_v1/knowledge_store.py - 도메인 지식 저장·BM25 검색 (단일 KNOWLEDGE_DIR)

- code_assist_v1/knowledge/ 평면 구조 (.md 파일들).
- user_id 폴더 분리 없음. legacy 공유 없음. 사용자가 직접 등록.
- BM25 알고리즘 자체 구현.
"""
from __future__ import annotations
import math
import os
import re
from typing import Optional

from code_assist_v1.config import KNOWLEDGE_DIR

_BM25_K1 = 1.5
_BM25_B = 0.75


def _tokenize(text: str) -> list[str]:
    """한국어 2글자+, 영문/숫자 2글자+ 단위."""
    return re.findall(r'[가-힯]{2,}|[a-z0-9_]{2,}', text.lower())


# ── 인덱스 캐시 ──
_INDEX: dict = {"index": {}, "df": {}, "n": 0, "avg_dl": 1, "mtimes": {}}


def _scan_files() -> dict[str, float]:
    out: dict[str, float] = {}
    if not os.path.isdir(KNOWLEDGE_DIR):
        return out
    for fname in os.listdir(KNOWLEDGE_DIR):
        if fname.endswith(".md"):
            try:
                out[fname] = os.path.getmtime(os.path.join(KNOWLEDGE_DIR, fname))
            except OSError:
                out[fname] = 0
    return out


def _build_index() -> None:
    global _INDEX
    index: dict = {}
    df: dict[str, int] = {}
    total_tokens = 0
    mtimes: dict[str, float] = {}

    if os.path.isdir(KNOWLEDGE_DIR):
        for fname in os.listdir(KNOWLEDGE_DIR):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(KNOWLEDGE_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                mtime = os.path.getmtime(fpath)
            except Exception:
                continue
            tokens = _tokenize(content)
            tf: dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            index[fname] = {
                "tf": tf,
                "len": len(tokens),
                "content": content,
                "path": fpath,
                "mtime": mtime,
            }
            for t in set(tokens):
                df[t] = df.get(t, 0) + 1
            total_tokens += len(tokens)
            mtimes[fname] = mtime

    n = len(index)
    _INDEX = {
        "index": index,
        "df": df,
        "n": n,
        "avg_dl": (total_tokens / n) if n else 1,
        "mtimes": mtimes,
    }


def _ensure_fresh() -> None:
    """파일 mtime 변동 감지 → 재빌드."""
    cur = _scan_files()
    if cur != _INDEX.get("mtimes", {}):
        _build_index()


def _bm25(query_tokens: list[str], doc_tf: dict, doc_len: int) -> float:
    score = 0.0
    n = _INDEX["n"]
    avg_dl = _INDEX["avg_dl"]
    df = _INDEX["df"]
    for qt in query_tokens:
        if qt not in df:
            continue
        n_qi = df[qt]
        idf = math.log((n - n_qi + 0.5) / (n_qi + 0.5) + 1)
        tf = doc_tf.get(qt, 0)
        num = tf * (_BM25_K1 + 1)
        den = tf + _BM25_K1 * (1 - _BM25_B + _BM25_B * doc_len / max(avg_dl, 1))
        score += idf * (num / den)
    return score


def search(
    query: str,
    max_results: int = 5,
    max_content_chars: int = 4000,
) -> list[dict]:
    _ensure_fresh()
    if _INDEX["n"] == 0:
        return []
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []

    results: list[dict] = []
    for fname, info in _INDEX["index"].items():
        score = _bm25(q_tokens, info["tf"], info["len"])
        # 파일명 부분일치 보너스
        fname_low = fname.lower()
        for tok in q_tokens:
            if tok in fname_low:
                score += 5
        # 본문 부분일치 보너스
        content_low = info["content"][:4000].lower()
        for tok in q_tokens:
            if tok in content_low:
                score += 0.5
        if score <= 0:
            continue
        snippet = info["content"][:300].replace("\n", " ")
        results.append({
            "filename": fname,
            "score": round(score, 2),
            "content": info["content"][:max_content_chars],
            "path": info["path"],
            "snippet": snippet,
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    if not results:
        return []
    cutoff = results[0]["score"] * 0.3
    results = [r for r in results if r["score"] >= cutoff]
    return results[:max_results]


# ── CRUD ──
_VALID_FILENAME_RE = re.compile(r"^[\w\-가-힯\.\s]+$")


def _safe_filename(name: str) -> str:
    base = name.strip()
    if not base.endswith(".md"):
        base += ".md"
    base = base.replace("..", "").replace("/", "_").replace("\\", "_")
    if not _VALID_FILENAME_RE.match(base):
        base = re.sub(r"[^\w\-가-힯\.\s]", "_", base)
    return base[:200]


def list_files() -> list[dict]:
    out = []
    if not os.path.isdir(KNOWLEDGE_DIR):
        return out
    for fname in sorted(os.listdir(KNOWLEDGE_DIR)):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(KNOWLEDGE_DIR, fname)
        try:
            stat = os.stat(path)
            out.append({
                "filename": fname,
                "size": stat.st_size,
                "mtime": stat.st_mtime,
            })
        except OSError:
            continue
    return out


def view_file(filename: str) -> Optional[dict]:
    fname = _safe_filename(filename)
    path = os.path.join(KNOWLEDGE_DIR, fname)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return {"filename": fname, "content": f.read(), "path": path}


def save_file(filename: str, content: str) -> dict:
    fname = _safe_filename(filename)
    path = os.path.join(KNOWLEDGE_DIR, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    invalidate_cache()
    return {"filename": fname, "path": path, "size": len(content)}


def delete_file(filename: str) -> bool:
    fname = _safe_filename(filename)
    path = os.path.join(KNOWLEDGE_DIR, fname)
    if os.path.isfile(path):
        os.remove(path)
        invalidate_cache()
        return True
    return False


def invalidate_cache() -> None:
    global _INDEX
    _INDEX = {"index": {}, "df": {}, "n": 0, "avg_dl": 1, "mtimes": {}}
