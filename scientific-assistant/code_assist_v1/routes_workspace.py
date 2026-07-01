"""
code_assist_v1/routes_workspace.py - 워크스페이스 (★데모스 user_id 별로 분리)

각 엔드포인트는 요청에서 user_id 를 받아 WORKSPACE_DIR/<user_id>/ 안에서만 작업한다.
user_id 가 비어 있으면 WORKSPACE_DIR 루트(legacy 평면 구조)를 본다.
  - GET  : query string ?user_id=...
  - POST(JSON)      : body 의 "user_id"
  - POST(multipart) : form 의 "user_id"
"""
from __future__ import annotations
import os
import re
import shutil
from flask import request, jsonify
from werkzeug.utils import secure_filename

from code_assist_v1.config import WORKSPACE_DIR, MAX_UPLOAD_MB, ALLOWED_UPLOAD_EXT

# 파일 직접 조회(읽기) 상한 — 업로드 상한과 동일하게 둠(전엔 5MB 고정이라 좁았음).
MAX_VIEW_MB = MAX_UPLOAD_MB


def _safe_join(root: str, *paths: str) -> str | None:
    target = os.path.normpath(os.path.join(root, *paths))
    if not target.startswith(os.path.normpath(root)):
        return None
    return target


_BAD_NAME_CHARS = re.compile(r'[\x00-\x1f\x7f<>:"|?*\\/]')
_BAD_UID = re.compile(r'[^A-Za-z0-9_.\-]')


def _safe_name_unicode(name: str) -> str:
    """secure_filename 대체: 한글·공백 등 유니코드는 보존하고
    경로 구분자·NUL·제어문자·OS 금지 문자만 _ 로 치환.
    빈 문자열·점만 있으면 'uploaded' 로 폴백.
    """
    name = (name or "").strip()
    name = _BAD_NAME_CHARS.sub("_", name)
    if not name or name in (".", ".."):
        return "uploaded"
    return name


def _get_uid() -> str:
    """요청에서 user_id 추출 (form > json > query). 안전한 문자만 남긴다."""
    uid = ""
    try:
        uid = (request.form.get("user_id") or "").strip()
    except Exception:
        uid = ""
    if not uid:
        data = request.get_json(silent=True) or {}
        uid = (data.get("user_id") or "").strip() if isinstance(data, dict) else ""
    if not uid:
        uid = (request.args.get("user_id") or "").strip()
    uid = _BAD_UID.sub("", uid)
    return uid


def _ws_root(uid: str) -> str:
    """user_id 있으면 WORKSPACE_DIR/<uid>, 없으면 WORKSPACE_DIR 루트(legacy)."""
    root = os.path.join(WORKSPACE_DIR, uid) if uid else WORKSPACE_DIR
    os.makedirs(root, exist_ok=True)
    return root


def register_workspace_routes(app):

    @app.route("/api/code/workspace/tree")
    def api_ws_tree():
        root = _ws_root(_get_uid())
        items = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".DS_Store")]
            rel = os.path.relpath(dirpath, root)
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
        return jsonify({"items": items, "count": len(items), "root": root})

    @app.route("/api/code/workspace/file")
    def api_ws_file():
        root = _ws_root(_get_uid())
        rel = request.args.get("path", "").strip()
        if not rel:
            return jsonify({"error": "path 필요"}), 400
        full = _safe_join(root, rel)
        if not full or not os.path.isfile(full):
            return jsonify({"error": "파일 없음"}), 404
        size = os.path.getsize(full)
        if size > MAX_VIEW_MB * 1024 * 1024:
            return jsonify({"error": f"{MAX_VIEW_MB}MB 초과 파일은 직접 조회 불가"}), 413
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
        root = _ws_root(_get_uid())
        if "file" not in request.files:
            return jsonify({"error": "file 필드 필요"}), 400
        f = request.files["file"]
        if not f.filename:
            return jsonify({"error": "filename 비어있음"}), 400

        relpath = (request.form.get("relpath") or "").strip().replace("\\", "/")
        rel_dir_form = (request.form.get("dir") or "").strip().replace("\\", "/")
        is_folder_upload = bool(relpath)

        ext = os.path.splitext(f.filename)[1].lower()
        if not is_folder_upload and ext and ext not in ALLOWED_UPLOAD_EXT:
            return jsonify({"error": f"지원하지 않는 확장자: {ext}"}), 415

        f.stream.seek(0, os.SEEK_END)
        size = f.stream.tell()
        f.stream.seek(0)
        if size > MAX_UPLOAD_MB * 1024 * 1024:
            if is_folder_upload:
                return jsonify({"status": "skipped", "reason": f"크기 초과 ({MAX_UPLOAD_MB}MB)", "path": relpath}), 200
            return jsonify({"error": f"파일 크기 초과 ({MAX_UPLOAD_MB}MB)"}), 413

        if relpath:
            parts = [p for p in relpath.split("/") if p and p not in (".", "..")]
            if not parts:
                return jsonify({"error": "잘못된 relpath"}), 400
            safe_parts = [_safe_name_unicode(p) for p in parts[:-1]]
            target_name = _safe_name_unicode(parts[-1])
            target_dir = _safe_join(root, *safe_parts) if safe_parts else root
        else:
            target_dir = _safe_join(root, rel_dir_form) if rel_dir_form else root
            target_name = _safe_name_unicode(f.filename)

        if not target_dir:
            return jsonify({"error": "잘못된 디렉토리"}), 400
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, target_name)
        try:
            f.save(target_path)
        except Exception as e:
            print(f"[ws] f.save 실패: {target_path} → {e}")
            if is_folder_upload:
                return jsonify({"status": "skipped", "reason": f"저장 실패: {e}", "path": relpath}), 200
            return jsonify({"error": f"저장 실패: {e}"}), 500
        rel_path = os.path.relpath(target_path, root).replace("\\", "/")
        print(f"[ws] uploaded: {rel_path} ({size} bytes)")
        return jsonify({"status": "uploaded", "path": rel_path, "size": size})

    @app.route("/api/code/workspace/save", methods=["POST"])
    def api_ws_save():
        root = _ws_root(_get_uid())
        data = request.get_json(force=True, silent=True) or {}
        rel = (data.get("path") or "").strip().replace("\\", "/")
        content = data.get("content", "")
        if not rel:
            return jsonify({"error": "path 필요"}), 400
        full = _safe_join(root, rel)
        if not full:
            return jsonify({"error": "잘못된 경로"}), 400
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return jsonify({"status": "saved", "path": rel, "size": len(content)})

    @app.route("/api/code/workspace/_debug")
    def api_ws_debug():
        root = _ws_root(_get_uid())
        info = {
            "workspace_dir": root,
            "exists": os.path.isdir(root),
            "code_version": "per-user-v3",
            "raw_files": [],
            "raw_dirs": [],
        }
        for dirpath, dirnames, filenames in os.walk(root):
            rel_d = os.path.relpath(dirpath, root).replace("\\", "/")
            if rel_d != ".":
                info["raw_dirs"].append(rel_d)
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                rel_f = os.path.relpath(full, root).replace("\\", "/")
                try:
                    info["raw_files"].append({
                        "path": rel_f, "size": os.path.getsize(full),
                        "ext": os.path.splitext(fn)[1].lower(),
                    })
                except OSError as e:
                    info["raw_files"].append({"path": rel_f, "error": str(e)})
        info["file_count"] = len(info["raw_files"])
        info["dir_count"] = len(info["raw_dirs"])
        return jsonify(info)

    @app.route("/api/code/workspace/clear", methods=["POST"])
    def api_ws_clear():
        """이 사용자의 워크스페이스만 비운다(폴더 자체는 유지)."""
        root = _ws_root(_get_uid())
        removed = 0
        errors: list[str] = []
        for name in os.listdir(root):
            p = os.path.join(root, name)
            try:
                if os.path.isdir(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
                removed += 1
            except Exception as e:
                errors.append(f"{name}: {e}")
        if errors:
            return jsonify({"status": "partial", "removed": removed, "errors": errors}), 207
        return jsonify({"status": "cleared", "removed": removed})

    @app.route("/api/code/workspace/delete", methods=["POST"])
    def api_ws_delete():
        root = _ws_root(_get_uid())
        data = request.get_json(force=True, silent=True) or {}
        rel = (data.get("path") or "").strip().replace("\\", "/")
        if not rel:
            return jsonify({"error": "path 필요"}), 400
        full = _safe_join(root, rel)
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
