"""demos_v1/rag_client.py — RAG 서버(별도 프로세스) 호출 + BM25 무중단 폴백.

데모스의 기존 search_knowledge 호출을 이걸로 바꾸면:
  RAG 서버 살아있음 → /search 청크 결과 (반환 스키마는 search_knowledge 와 동일)
  RAG 죽음/미설치/enabled=false → 기존 knowledge.search_knowledge 로 폴백
rag 설정은 api_config.json 의 "rag" 섹션. 없으면 항상 폴백(현행 동작 100% 유지).
"""
import os
import time

import requests as _req

from demos_v1.config import _EXT_CONFIG
from demos_v1 import knowledge as _kb

_RAG = _EXT_CONFIG.get("rag", {}) or {}
_HEALTH = {"ok": None, "ts": 0.0}


def _enabled():
    return bool(_RAG.get("enabled"))


def _url():
    return (_RAG.get("url") or "http://127.0.0.1:8765").rstrip("/")


def _healthy():
    if not _enabled():
        return False
    ttl = float(_RAG.get("health_ttl_s", 30))
    now = time.time()
    if _HEALTH["ok"] is not None and (now - _HEALTH["ts"]) < ttl:
        return _HEALTH["ok"]
    try:
        r = _req.get(_url() + "/health", timeout=1.5)
        _HEALTH["ok"] = (r.status_code == 200)
    except Exception:
        _HEALTH["ok"] = False
    _HEALTH["ts"] = now
    return _HEALTH["ok"]


def _rag_to_kb(results, max_content_chars):
    """RAG 청크 결과 → search_knowledge 스키마(파일별 묶음). [{filename, content, score, ...}]"""
    byfile, order = {}, []
    for r in results:
        fn = r.get("filename", "?")
        if fn not in byfile:
            byfile[fn] = {"score": 0.0, "chunks": []}
            order.append(fn)
        hd = r.get("heading", "")
        seg = (f"[섹션: {hd}]\n" if hd else "") + (r.get("text", "") or "")
        byfile[fn]["chunks"].append(seg)
        byfile[fn]["score"] = max(byfile[fn]["score"], r.get("score", 0) or 0)
    out = []
    for fn in order:
        f = byfile[fn]
        content = "\n\n".join(f["chunks"])[: max_content_chars * 3]
        out.append({"filename": fn, "content": content,
                    "score": round(f["score"], 4), "content_length": len(content),
                    "preview": content[:160]})
    return out


def _read_files_direct(user_id, files, per=4000, total_cap=14000):
    """폴백 최후수단(개인에이전트): 선택 파일 앞부분 직접 읽기 — buildKnowledgeContext 동작 재현."""
    out, tot = [], 0
    base = os.path.join(_kb.KNOWLEDGE_DIR, str(user_id))
    for fn in files:
        p = os.path.join(base, fn)
        if not os.path.isfile(p):
            continue
        try:
            c = open(p, "r", encoding="utf-8").read()[:per]
        except Exception:
            continue
        if tot + len(c) > total_cap:
            c = c[: max(0, total_cap - tot)]
        if not c:
            break
        out.append({"filename": fn, "content": c, "score": 1.0,
                    "content_length": len(c), "preview": c[:160]})
        tot += len(c)
    return out


def read_selected(user_id, files, per_file=6000, total_cap=14000):
    """개인에이전트 전용: 선택한 지식 문서를 '그대로' 읽어 반환. 검색/자동 추천 없음.
    (자동 지식검색은 데모스 메인에서만. 에이전트는 사용자가 고른 문서만 주입.)"""
    if not user_id or not files:
        return []
    return _read_files_direct(user_id, files, per=per_file, total_cap=total_cap)


def search_knowledge_smart(query, max_results=10, max_content_chars=4000, user_id=None, files=None):
    """RAG 우선, 실패/미사용 시 기존 BM25 폴백. 반환 스키마 = search_knowledge 와 동일."""
    if user_id and _healthy():
        try:
            body = {"user_id": user_id, "query": query or "",
                    "top_k": max(max_results, 8),
                    "max_chars": max(max_content_chars * 3, 12000)}
            if files:
                body["files"] = files
            r = _req.post(_url() + "/search", json=body, timeout=float(_RAG.get("timeout_s", 4)))
            if r.status_code == 200:
                res = r.json().get("results", [])
                if res or not files:
                    return _rag_to_kb(res, max_content_chars)
        except Exception as e:
            print(f"[RAG] fallback to BM25: {e}")
            _HEALTH["ok"] = False  # 헬스 캐시 무효화 → 다음에 재확인

    # ── 폴백: 기존 BM25 ──
    out = _kb.search_knowledge(query, max_results=max_results,
                               max_content_chars=max_content_chars, user_id=user_id)
    if files:  # 개인에이전트: 선택 파일만. 못 찾으면 직접 읽기, 그래도 없으면 '아무것도 안 줌'.
        sel = set(files)
        filt = [r for r in out if r.get("filename") in sel]
        if filt:
            return filt
        # 선택 파일이 검색결과에 없으면 직접 읽기 시도. 그래도 없으면 [] (선택 안 한 문서를
        # 대신 넣지 않는다 — 예전엔 out(전체)을 반환해 엉뚱한 문서가 주입되던 버그).
        return _read_files_direct(user_id, files)
    return out
