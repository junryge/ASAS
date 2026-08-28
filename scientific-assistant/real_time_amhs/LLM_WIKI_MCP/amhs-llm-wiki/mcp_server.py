# -*- coding: utf-8 -*-
"""
LLM-WIKI MCP 서버 — 위키 지식을 MCP 도구로 노출

- mcp>=1.27,<2 필요 (pip install "mcp>=1.27,<2")
- streamable-http, stateless, 기본 포트 8020 (환경변수 LLM_WIKI_MCP_PORT)
- 위키 DB(data/wiki.db)를 직접 읽는다 — 웹앱(app.py)이 꺼져 있어도 동작
- structuredContent는 camelCase, 오류는 isError 패턴

실행:
    python mcp_server.py
클라이언트 연결(streamable-http):
    http://<서버주소>:8020/mcp
"""
import os
import sys
from typing import Any

# app.py의 검색/DB 로직 재사용 (import 시 DB 초기화까지 수행)
# retrieve()는 웹앱과 동일한 하이브리드+리랭커 파이프라인을 그대로 탄다
from app import (_connect, tokenize, bm25_search, all_search_docs,  # noqa: F401
                 retrieve, retrieval_desc, app as flask_app, DB_PATH)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("mcp 패키지가 없다. 폐쇄망 반입 후: pip install \"mcp>=1.27,<2\"")
    sys.exit(1)

PORT = int(os.environ.get("LLM_WIKI_MCP_PORT", "8020"))
HOST = os.environ.get("LLM_WIKI_MCP_HOST", "0.0.0.0")

mcp = FastMCP("llm-wiki", host=HOST, port=PORT, stateless_http=True)


def _err(msg):
    return {"isError": True, "message": msg}


@mcp.tool()
def listDomains() -> dict[str, Any]:
    """담당(도메인) 목록과 페이지/소스 개수를 반환한다."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT d.*, (SELECT COUNT(*) FROM pages p WHERE p.domain_id=d.id) pcnt, "
            "(SELECT COUNT(*) FROM sources s WHERE s.domain_id=d.id) scnt "
            "FROM domains d ORDER BY d.id").fetchall()
        return {"domains": [
            {"id": r["id"], "slug": r["slug"], "name": r["name"],
             "description": r["description"], "pageCount": r["pcnt"],
             "sourceCount": r["scnt"]} for r in rows]}
    finally:
        conn.close()


@mcp.tool()
def searchWiki(query: str, topK: int = 5, domainSlug: str = "") -> dict[str, Any]:
    """위키 페이지·소스를 검색한다 (BM25, 설정에 따라 하이브리드+리랭커).
       query는 한국어/영문 자연어 또는 키워드. domainSlug로 특정 FAB만 볼 수 있다."""
    if not query.strip():
        return _err("query가 비어있다")
    with flask_app.app_context():
        did = None
        if domainSlug:
            conn = _connect()
            try:
                r = conn.execute("SELECT id FROM domains WHERE slug=?", (domainSlug,)).fetchone()
                if not r:
                    return _err(f"domainSlug '{domainSlug}' 없음")
                did = r["id"]
            finally:
                conn.close()
        results = retrieve(query, k=min(topK, 20), domain_id=did)
        desc = retrieval_desc()
    return {"query": query, "retrieval": desc, "results": [
        {"score": round(s, 3), "kind": d["kind"], "id": d["id"],
         "title": d["title"], "domain": d["domain"],
         "summary": d.get("summary", ""),
         "snippet": (d.get("chunkText") or "")[:500]} for s, d in results]}


@mcp.tool()
def readPage(pageId: int) -> dict[str, Any]:
    """위키 페이지 본문(마크다운)을 읽는다. searchWiki 결과의 kind='page' id 사용."""
    conn = _connect()
    try:
        r = conn.execute(
            "SELECT p.*, d.name dname, d.slug dslug FROM pages p "
            "JOIN domains d ON d.id=p.domain_id WHERE p.id=?", (pageId,)).fetchone()
        if not r:
            return _err(f"page {pageId} 없음")
        return {"id": r["id"], "title": r["title"], "domain": r["dname"],
                "tags": r["tags"], "summary": r["summary"], "author": r["author"],
                "updatedAt": r["updated_at"], "bodyMd": r["body_md"]}
    finally:
        conn.close()


@mcp.tool()
def listSources(domainSlug: str = "") -> dict[str, Any]:
    """업로드된 소스(원본 자료) 목록. domainSlug를 주면 해당 담당만."""
    conn = _connect()
    try:
        q = ("SELECT s.id,s.filename,s.filetype,s.description,s.created_at,d.slug dslug,d.name dname "
             "FROM sources s JOIN domains d ON d.id=s.domain_id")
        args = []
        if domainSlug:
            q += " WHERE d.slug=?"
            args.append(domainSlug)
        q += " ORDER BY s.id DESC"
        rows = conn.execute(q, args).fetchall()
        return {"sources": [
            {"id": r["id"], "filename": r["filename"], "filetype": r["filetype"],
             "description": r["description"], "domain": r["dname"],
             "createdAt": r["created_at"]} for r in rows]}
    finally:
        conn.close()


@mcp.tool()
def readSource(sourceId: int, maxChars: int = 20000) -> dict[str, Any]:
    """소스의 추출 텍스트를 읽는다 (PDF/CSV/TXT/MD는 텍스트, 이미지는 설명만)."""
    conn = _connect()
    try:
        r = conn.execute(
            "SELECT s.*, d.name dname FROM sources s "
            "JOIN domains d ON d.id=s.domain_id WHERE s.id=?", (sourceId,)).fetchone()
        if not r:
            return _err(f"source {sourceId} 없음")
        return {"id": r["id"], "filename": r["filename"], "filetype": r["filetype"],
                "domain": r["dname"], "description": r["description"],
                "createdAt": r["created_at"],
                "extractedText": (r["extracted_text"] or "")[:max(1000, maxChars)]}
    finally:
        conn.close()


if __name__ == "__main__":
    print(f"* LLM-WIKI MCP 서버: http://{HOST}:{PORT}/mcp (streamable-http, DB: {DB_PATH})")
    mcp.run(transport="streamable-http")
