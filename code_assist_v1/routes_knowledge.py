"""
code_assist_v1/routes_knowledge.py - 도메인 지식 CRUD (user_id 없이 단일 폴더)
"""
from __future__ import annotations
import os
from flask import request, jsonify
from werkzeug.utils import secure_filename

from code_assist_v1.config import MAX_UPLOAD_MB
from code_assist_v1 import knowledge_store as ks


def _read_text_from_upload(filename: str, raw: bytes) -> str | None:
    ext = os.path.splitext(filename)[1].lower()
    if ext in (".md", ".txt", ".csv", ".tsv", ".json", ".yaml", ".yml"):
        for enc in ("utf-8", "utf-8-sig", "cp949", "euc-kr", "latin-1"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return None
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            from io import BytesIO
            reader = PdfReader(BytesIO(raw))
            return "\n\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception:
            return None
    if ext == ".docx":
        try:
            from docx import Document
            from io import BytesIO
            doc = Document(BytesIO(raw))
            return "\n\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def register_knowledge_routes(app):

    @app.route("/api/code/knowledge/list")
    def api_kb_list():
        return jsonify({"items": ks.list_files()})

    @app.route("/api/code/knowledge/view/<path:filename>")
    def api_kb_view(filename):
        info = ks.view_file(filename)
        if not info:
            return jsonify({"error": "찾을 수 없음"}), 404
        return jsonify(info)

    @app.route("/api/code/knowledge/create", methods=["POST"])
    def api_kb_create():
        data = request.get_json(force=True, silent=True) or {}
        filename = (data.get("filename") or "").strip()
        content = data.get("content") or ""
        if not filename:
            return jsonify({"error": "filename 필요"}), 400
        info = ks.save_file(filename, content)
        return jsonify({"status": "created", **info})

    @app.route("/api/code/knowledge/upload", methods=["POST"])
    def api_kb_upload():
        if "file" not in request.files:
            return jsonify({"error": "file 필드 필요"}), 400
        f = request.files["file"]
        if not f.filename:
            return jsonify({"error": "filename 비어있음"}), 400
        f.stream.seek(0, os.SEEK_END)
        size = f.stream.tell()
        f.stream.seek(0)
        if size > MAX_UPLOAD_MB * 1024 * 1024:
            return jsonify({"error": f"파일 크기 초과 ({MAX_UPLOAD_MB}MB)"}), 413
        raw = f.read()
        text = _read_text_from_upload(f.filename, raw)
        if text is None:
            return jsonify({"error": "텍스트를 추출할 수 없습니다"}), 415
        base = os.path.splitext(secure_filename(f.filename) or "uploaded")[0]
        target_name = base + ".md"
        info = ks.save_file(target_name, text)
        return jsonify({"status": "uploaded", **info, "extracted_chars": len(text)})

    @app.route("/api/code/knowledge/delete", methods=["POST"])
    def api_kb_delete():
        data = request.get_json(force=True, silent=True) or {}
        filename = (data.get("filename") or "").strip()
        if not filename:
            return jsonify({"error": "filename 필요"}), 400
        ok = ks.delete_file(filename)
        if not ok:
            return jsonify({"error": "파일 없음"}), 404
        return jsonify({"status": "deleted", "filename": filename})

    @app.route("/api/code/knowledge/search", methods=["POST"])
    def api_kb_search():
        data = request.get_json(force=True, silent=True) or {}
        query = (data.get("query") or "").strip()
        max_results = int(data.get("max_results", 5))
        max_content_chars = int(data.get("max_content_chars", 4000))
        if not query:
            return jsonify({"error": "query 필요"}), 400
        results = ks.search(query=query, max_results=max_results, max_content_chars=max_content_chars)
        return jsonify({"query": query, "results": results, "count": len(results)})

    @app.route("/api/code/knowledge/reindex", methods=["POST"])
    def api_kb_reindex():
        ks.invalidate_cache()
        return jsonify({"status": "reindexed"})
