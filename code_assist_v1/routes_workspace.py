"""
code_assist_v1/routes_workspace.py - 워크스페이스 (user_id 없이 단일 폴더)
"""
from __future__ import annotations
import os
import shutil
from flask import request, jsonify
from werkzeug.utils import secure_filename

from code_assist_v1.config import WORKSPACE_DIR, MAX_UPLOAD_MB, ALLOWED_UPLOAD_EXT


def _safe_join(root: str, *paths: str) -> str | None:
    target = os.path.normpath(os.path.join(root, *paths))
    if not target.startswith(os.path.normpath(root)):
        return None
    return target


def register_workspace_routes(app):

    @app.route("/api/code/workspace/tree")
    def api_ws_tree():
        items = []
        for dirpath, _, filenames in os.walk(WORKSPACE_DIR):
            rel = os.path.relpath(dirpath, WORKSPACE_DIR)
            if rel == ".":
                rel = ""
            for fn in sorted(filenames):
                rel_path = os.path.join(rel, fn) if rel else fn
                full = os.path.join(dirpath, fn)
                try:
                    stat = os.stat(full)
                    items.append({
                        "path": rel_path.replace("\\", "/"),
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                    })
                except OSError:
                    continue
        return jsonify({"items": items, "root": WORKSPACE_DIR})

    @app.route("/api/code/workspace/file")
    def api_ws_file():
        rel = request.args.get("path", "").strip()
        if not rel:
            return jsonify({"error": "path 필요"}), 400
        full = _safe_join(WORKSPACE_DIR, rel)
        if not full or not os.path.isfile(full):
            return jsonify({"error": "파일 없음"}), 404
        size = os.path.getsize(full)
        if size > 5 * 1024 * 1024:
            return jsonify({"error": "5MB 초과 파일은 직접 조회 불가"}), 413
        try:
            with open(full, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(full, "r", encoding="cp949") as f:
                    content = f.read()
            except Exception:
                return jsonify({"error": "텍스트 디코딩 실패"}), 415
        return jsonify({"path": rel, "content": content, "size": size})

    @app.route("/api/code/workspace/upload", methods=["POST"])
    def api_ws_upload():
        if "file" not in request.files:
            return jsonify({"error": "file 필드 필요"}), 400
        f = request.files["file"]
        if not f.filename:
            return jsonify({"error": "filename 비어있음"}), 400
        ext = os.path.splitext(f.filename)[1].lower()
        if ext and ext not in ALLOWED_UPLOAD_EXT:
            return jsonify({"error": f"지원하지 않는 확장자: {ext}"}), 415
        f.stream.seek(0, os.SEEK_END)
        size = f.stream.tell()
        f.stream.seek(0)
        if size > MAX_UPLOAD_MB * 1024 * 1024:
            return jsonify({"error": f"파일 크기 초과 ({MAX_UPLOAD_MB}MB)"}), 413
        rel_dir = (request.form.get("dir") or "").strip().replace("\\", "/")
        target_dir = _safe_join(WORKSPACE_DIR, rel_dir) if rel_dir else WORKSPACE_DIR
        if not target_dir:
            return jsonify({"error": "잘못된 디렉토리"}), 400
        os.makedirs(target_dir, exist_ok=True)
        target_name = secure_filename(f.filename) or "uploaded"
        target_path = os.path.join(target_dir, target_name)
        f.save(target_path)
        rel_path = os.path.relpath(target_path, WORKSPACE_DIR).replace("\\", "/")
        return jsonify({"status": "uploaded", "path": rel_path, "size": size})

    @app.route("/api/code/workspace/save", methods=["POST"])
    def api_ws_save():
        data = request.get_json(force=True, silent=True) or {}
        rel = (data.get("path") or "").strip().replace("\\", "/")
        content = data.get("content", "")
        if not rel:
            return jsonify({"error": "path 필요"}), 400
        full = _safe_join(WORKSPACE_DIR, rel)
        if not full:
            return jsonify({"error": "잘못된 경로"}), 400
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return jsonify({"status": "saved", "path": rel, "size": len(content)})

    @app.route("/api/code/workspace/delete", methods=["POST"])
    def api_ws_delete():
        data = request.get_json(force=True, silent=True) or {}
        rel = (data.get("path") or "").strip().replace("\\", "/")
        if not rel:
            return jsonify({"error": "path 필요"}), 400
        full = _safe_join(WORKSPACE_DIR, rel)
        if not full or not os.path.exists(full):
            return jsonify({"error": "파일 없음"}), 404
        try:
            if os.path.isdir(full):
                shutil.rmtree(full)
            else:
                os.remove(full)
        except Exception as e:
            return jsonify({"error": f"삭제 실패: {e}"}), 500
        return jsonify({"status": "deleted", "path": rel})
