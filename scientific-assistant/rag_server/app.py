#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rag_server/app.py — RAG 서버 (데모스와 별도 프로세스, 같은 PC).

실행 (윈도우):
    cd scientific-assistant\\rag_server
    python app.py

엔드포인트:
    GET  /health                      서버/임베딩 상태
    POST /search {user_id, query, top_k?, max_chars?, files?}   하이브리드 검색
    POST /reindex {user_id?, reembed?}   재인덱싱(백그라운드)

채팅 LLM 은 데모스가 API 로 받음. 이 서버는 임베딩(bge-m3 CPU)만 담당.
모델 없으면 lexical(BM25+청킹) 모드로 동작.
"""
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify  # noqa: E402

import config            # noqa: E402
import chunker           # noqa: E402
import store             # noqa: E402
import search as searcher  # noqa: E402
from embedder import build_embedder  # noqa: E402

app = Flask(__name__)

EMBEDDER = build_embedder()
_reindex_state = {"running": False, "done": 0, "total": 0}


@app.get("/health")
def health():
    st = store.stats()
    mode = "hybrid" if getattr(EMBEDDER, "available", False) else "lexical"
    return jsonify({
        "status": "ok",
        "mode": mode,
        "embed_backend": EMBEDDER.name,
        "embed_dim": getattr(EMBEDDER, "dim", 0),
        "knowledge_dir": config.KNOWLEDGE_DIR,
        "reindexing": _reindex_state["running"],
        **st,
    })


@app.post("/search")
def search():
    data = request.get_json(force=True) or {}
    user_id = (data.get("user_id") or "").strip()
    query = data.get("query") or ""
    if not user_id:
        return jsonify({"error": "user_id 필요"}), 400
    files = data.get("files") or None
    if files and isinstance(files, list):
        files = [os.path.basename(str(f)) for f in files if f]
    try:
        res = searcher.search(user_id, query, chunker, EMBEDDER,
                              top_k=data.get("top_k"), max_chars=data.get("max_chars"),
                              files=files)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e), "results": []}), 500


@app.post("/reindex")
def reindex():
    data = request.get_json(force=True) or {}
    one_user = (data.get("user_id") or "").strip() or None
    force = bool(data.get("reembed"))

    def _job():
        _reindex_state.update(running=True, done=0, total=0)
        try:
            users = [one_user] if one_user else store.list_users()
            _reindex_state["total"] = len(users)
            for u in users:
                store.sync_user(u, chunker, EMBEDDER, force=force)
                _reindex_state["done"] += 1
        finally:
            _reindex_state["running"] = False

    if _reindex_state["running"]:
        return jsonify({"message": "이미 재인덱싱 중", **_reindex_state}), 202
    threading.Thread(target=_job, daemon=True).start()
    return jsonify({"message": "재인덱싱 시작(백그라운드)", "user": one_user or "ALL", "reembed": force}), 202


if __name__ == "__main__":
    host = config.CFG.get("host", "127.0.0.1")
    port = int(config.CFG.get("port", 8765))
    mode = "hybrid(bge-m3)" if getattr(EMBEDDER, "available", False) else "lexical(BM25+청킹)"
    print(f"[RAG] http://{host}:{port}  | 모드={mode} | knowledge={config.KNOWLEDGE_DIR}")
    print(f"[RAG] 첫 검색 시 사용자별 자동 인덱싱. 전체 미리 만들려면 POST /reindex")
    # 윈도우 콘솔에서 Flask 시작 배너를 colorama 가 출력하다 'OSError: Windows error 6'
    # (잘못된 콘솔 핸들)로 죽는 문제 방지 — 배너만 끈다(서버 동작엔 영향 없음).
    try:
        import flask.cli
        flask.cli.show_server_banner = lambda *a, **k: None
    except Exception:
        pass
    app.run(host=host, port=port, threaded=True)
