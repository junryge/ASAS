"""
code_assist_v1/knowledge_store.py - 도메인 지식 저장·BM25 검색 (user_id 기반)

- 루트 KNOWLEDGE_DIR (= demos_v1 공유 knowledge/) 안의 사용자별 폴더 구조:
    knowledge/<user_id>/*.md
- demos_v1과 같은 폴더 레이아웃을 사용해 데이터 일치.
- user_id가 None/빈 값이면 KNOWLEDGE_DIR 루트(legacy 평면 구조)를 본다.
- BM25 인덱스 캐시는 user_id 별로 분리.
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


# ── 사용자 폴더 / 캐시 ──
def _scope_dir(user_id: Optional[str]) -> str:
    """user_id 있으면 KNOWLEDGE_DIR/<user_id>, 없으면 KNOWLEDGE_DIR 루트."""
    if user_id:
        d = os.path.join(KNOWLEDGE_DIR, user_id)
        os.makedirs(d, exist_ok=True)
        return d
    return KNOWLEDGE_DIR


def _scope_key(user_id: Optional[str]) -> str:
    return user_id or "__root__"


# 인덱스 캐시: scope_key → {index, df, n, avg_dl, mtimes}
_INDEX_CACHE: dict[str, dict] = {}


def _scan_files(target_dir: str) -> dict[str, float]:
    out: dict[str, float] = {}
    if not os.path.isdir(target_dir):
        return out
    for fname in os.listdir(target_dir):
        if fname.endswith(".md"):
            try:
                out[fname] = os.path.getmtime(os.path.join(target_dir, fname))
            except OSError:
                out[fname] = 0
    return out


def _build_index(user_id: Optional[str]) -> dict:
    target_dir = _scope_dir(user_id)
    index: dict = {}
    df: dict[str, int] = {}
    total_tokens = 0
    mtimes: dict[str, float] = {}

    if os.path.isdir(target_dir):
        for fname in os.listdir(target_dir):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(target_dir, fname)
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
    snapshot = {
        "index": index,
        "df": df,
        "n": n,
        "avg_dl": (total_tokens / n) if n else 1,
        "mtimes": mtimes,
    }
    _INDEX_CACHE[_scope_key(user_id)] = snapshot
    return snapshot


def _ensure_fresh(user_id: Optional[str]) -> dict:
    """파일 mtime 변동 감지 → 재빌드. 항상 유효한 인덱스 dict 반환."""
    target_dir = _scope_dir(user_id)
    cur = _scan_files(target_dir)
    cached = _INDEX_CACHE.get(_scope_key(user_id))
    # 캐시 miss(None) 또는 mtime 변동 시 재빌드
    # 빈 폴더 케이스(cur={})에서도 첫 호출엔 cached=None이라 build 호출됨
    if cached is None or cur != cached.get("mtimes", {}):
        return _build_index(user_id)
    return cached


def _bm25(query_tokens: list[str], doc_tf: dict, doc_len: int, idx: dict) -> float:
    score = 0.0
    n = idx["n"]
    avg_dl = idx["avg_dl"]
    df = idx["df"]
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
    user_id: Optional[str] = None,
    max_results: int = 5,
    max_content_chars: int = 4000,
) -> list[dict]:
    """지식 검색 — demos_v1의 search_knowledge에 위임 (통합 모드).

    demos_v1 알고리즘은 컬럼 패턴/FAB 접두사/frontmatter 태그·FAB·카테고리·description/
    날짜 매칭/BM25/부분문자열 TF/구문 일치/한글 유사 문자 등 정교한 점수 체계 사용.
    [KNOWLEDGE DEBUG] 로그도 demos_v1과 동일하게 출력됨.

    실패 시(단독 실행 모드) 자체 BM25로 폴백.
    """
    # 1) demos_v1의 search_knowledge 우선 호출 (통합 모드)
    try:
        from demos_v1.knowledge import search_knowledge as _demos_search
        _results = _demos_search(
            query=query,
            max_results=max_results,
            max_content_chars=max_content_chars,
            user_id=user_id,
        )
        # demos_v1 결과 형식 → code_assist_v1 형식으로 매핑
        out = []
        for r in _results:
            preview = r.get("preview") or []
            snippet = preview[0] if preview else (r.get("content") or "")[:300]
            out.append({
                "filename": r.get("filename", ""),
                "score": r.get("score", 0),
                "content": r.get("content", ""),
                "path": "",  # demos_v1엔 path 필드 없음
                "snippet": snippet,
            })
        return out
    except ImportError:
        pass

    # 2) 폴백: 자체 BM25 (단독 실행 호환)
    idx = _ensure_fresh(user_id)
    if idx["n"] == 0:
        return []
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []

    results: list[dict] = []
    for fname, info in idx["index"].items():
        score = _bm25(q_tokens, info["tf"], info["len"], idx)
        fname_low = fname.lower()
        for tok in q_tokens:
            if tok in fname_low:
                score += 5
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


def list_files(user_id: Optional[str] = None) -> list[dict]:
    target_dir = _scope_dir(user_id)
    out = []
    if not os.path.isdir(target_dir):
        return out
    for fname in sorted(os.listdir(target_dir)):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(target_dir, fname)
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


def view_file(filename: str, user_id: Optional[str] = None) -> Optional[dict]:
    fname = _safe_filename(filename)
    path = os.path.join(_scope_dir(user_id), fname)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return {"filename": fname, "content": f.read(), "path": path}


def save_file(filename: str, content: str, user_id: Optional[str] = None) -> dict:
    fname = _safe_filename(filename)
    path = os.path.join(_scope_dir(user_id), fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    invalidate_cache(user_id)
    return {"filename": fname, "path": path, "size": len(content)}


def delete_file(filename: str, user_id: Optional[str] = None) -> bool:
    fname = _safe_filename(filename)
    path = os.path.join(_scope_dir(user_id), fname)
    if os.path.isfile(path):
        os.remove(path)
        invalidate_cache(user_id)
        return True
    return False


def invalidate_cache(user_id: Optional[str] = None) -> None:
    """user_id 지정 시 해당 사용자 인덱스만, None이면 전체 무효화."""
    if user_id is None:
        _INDEX_CACHE.clear()
    else:
        _INDEX_CACHE.pop(_scope_key(user_id), None)
