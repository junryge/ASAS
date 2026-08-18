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


# ── 프로젝트(zip) 첨부 ──
# ★예전엔 .zip 이 확장자 목록에 없어서 415 로 거부됐다. 프로젝트를 통째로
#   주려면 파일을 하나씩 수백 번 올려야 했다. zip 하나로 끝나게 한다.
ZIP_EXT = {".zip"}
ZIP_MAX_FILES = 3000          # 폭탄 방지 — 이보다 많으면 앞에서 끊고 알려 준다
ZIP_MAX_TOTAL_MB = 300        # 풀었을 때 총 크기 상한
ZIP_SKIP_DIRS = {
    "__pycache__", ".git", ".svn", ".hg", "node_modules", ".venv", "venv",
    "env", ".idea", ".vscode", "dist", "build", ".next", ".cache",
    ".pytest_cache", ".mypy_cache", "site-packages", ".tox", "target",
}
ZIP_SKIP_EXT = {
    ".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe", ".bin", ".o", ".a",
    ".class", ".jar", ".war", ".zip", ".tar", ".gz", ".7z", ".rar",
    ".mp4", ".mov", ".avi", ".mp3", ".wav", ".iso", ".db", ".sqlite",
    ".lock", ".map", ".min.js", ".woff", ".woff2", ".ttf", ".eot",
}


def _zip_skip_reason(name: str) -> str | None:
    """이 항목을 건너뛸 이유. 없으면 None."""
    parts = [p for p in name.replace("\\", "/").split("/") if p]
    if not parts:
        return "빈 경로"
    if any(p in ZIP_SKIP_DIRS for p in parts[:-1]):
        return "제외 폴더"
    leaf = parts[-1]
    if leaf.startswith("."):
        return "숨김 파일"
    ext = os.path.splitext(leaf)[1].lower()
    if ext in ZIP_SKIP_EXT:
        return "코드 아님"
    return None


def _extract_zip(fileobj, root: str) -> dict:
    """zip 을 워크스페이스에 안전하게 푼다.

    ★zip 안의 경로는 못 믿는다. '../../etc/passwd' 같은 이름이 들어 있으면
      워크스페이스 밖에 쓰게 된다(zip slip). 항목마다 정규화한 뒤 root 밖으로
      나가면 버린다.
    ★압축을 풀었을 때 크기도 못 믿는다(zip bomb). 개수·총량 상한을 둔다.
    """
    import zipfile

    added, skipped, total = [], {}, 0

    def _skip(why):
        skipped[why] = skipped.get(why, 0) + 1

    try:
        zf = zipfile.ZipFile(fileobj)
    except zipfile.BadZipFile:
        return {"error": "zip 파일이 아니거나 깨졌다"}

    with zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            if len(added) >= ZIP_MAX_FILES:
                _skip(f"개수 상한 {ZIP_MAX_FILES} 초과")
                continue
            why = _zip_skip_reason(info.filename)
            if why:
                _skip(why)
                continue
            if total + info.file_size > ZIP_MAX_TOTAL_MB * 1024 * 1024:
                _skip(f"총량 상한 {ZIP_MAX_TOTAL_MB}MB 초과")
                continue

            raw = [p for p in info.filename.replace("\\", "/").split("/") if p and p != "."]
            # ★'..' 를 조용히 지우면 '../../etc/passwd' 가 'etc/passwd' 로 둔갑해
            #   워크스페이스 안에 남는다. 밖으로 새지는 않지만, 넣으려던 게
            #   아닌 파일이 생긴다. 그런 항목은 아예 거부한다.
            if ".." in raw:
                _skip("경로 이탈")
                continue
            parts = raw
            if not parts:
                _skip("잘못된 경로")
                continue
            safe = [_safe_name_unicode(p) for p in parts]
            dest = _safe_join(root, *safe)
            if not dest:                     # zip slip — 워크스페이스 밖
                _skip("경로 이탈")
                continue

            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                with zf.open(info) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out, 64 * 1024)
            except Exception:
                _skip("풀기 실패")
                continue
            total += info.file_size
            added.append(os.path.relpath(dest, root).replace("\\", "/"))

    return {"added": added, "skipped": skipped, "total_bytes": total}


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
        if not is_folder_upload and ext and ext not in ALLOWED_UPLOAD_EXT and ext not in ZIP_EXT:
            return jsonify({"error": f"지원하지 않는 확장자: {ext}"}), 415

        f.stream.seek(0, os.SEEK_END)
        size = f.stream.tell()
        f.stream.seek(0)
        if size > MAX_UPLOAD_MB * 1024 * 1024:
            if is_folder_upload:
                return jsonify({"status": "skipped", "reason": f"크기 초과 ({MAX_UPLOAD_MB}MB)", "path": relpath}), 200
            return jsonify({"error": f"파일 크기 초과 ({MAX_UPLOAD_MB}MB)"}), 413

        # 프로젝트 zip → 워크스페이스에 통째로 풀어 준다
        if ext in ZIP_EXT and not is_folder_upload:
            res = _extract_zip(f.stream, root)
            if "error" in res:
                return jsonify(res), 400
            print(f"[ws] zip 해제: {len(res['added'])}개 · {res['total_bytes']}바이트 "
                  f"· 건너뜀 {sum(res['skipped'].values())}개")
            # 목록이 잘렸을 때 프런트가 '이 폴더 전부' 로 다시 물어볼 수 있게
            # 공통 최상위 폴더를 알려 준다. 없으면(파일이 루트에 흩어져 있으면) 빈 문자열.
            tops = {p.split("/")[0] for p in res["added"] if "/" in p}
            root_prefix = tops.pop() if len(tops) == 1 else ""
            return jsonify({
                "status": "extracted",
                "kind": "zip",
                "count": len(res["added"]),
                "files": res["added"][:200],      # 응답이 너무 커지지 않게
                "truncated_list": len(res["added"]) > 200,
                "root_prefix": root_prefix,
                "skipped": res["skipped"],        # 왜 건너뛰었는지 그대로 보여 준다
                "total_bytes": res["total_bytes"],
            })

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

    @app.route("/api/code/workspace/files", methods=["POST"])
    def api_ws_files():
        """여러 파일을 한 번에 읽는다 (프로젝트 첨부용).

        ★예전엔 프런트가 파일 하나마다 요청을 보냈다. 300개짜리 프로젝트를
          붙이면 요청이 300번 — 느리고, 중간에 하나 실패하면 조용히 빠졌다.
          prefix 를 주면 그 폴더 아래 전부, paths 를 주면 그것만 읽는다.
        """
        root = _ws_root(_get_uid())
        data = request.get_json(force=True, silent=True) or {}
        paths = data.get("paths")
        prefix = (data.get("prefix") or "").strip().replace("\\", "/").strip("/")
        limit = int(data.get("limit") or 2000)

        if not paths:
            paths = []
            base = _safe_join(root, prefix) if prefix else root
            if not base or not os.path.isdir(base):
                return jsonify({"error": "폴더 없음"}), 404
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [d for d in dirnames
                               if d not in ZIP_SKIP_DIRS and not d.startswith(".")]
                for fn in sorted(filenames):
                    rel = os.path.relpath(os.path.join(dirpath, fn), root)
                    paths.append(rel.replace("\\", "/"))
            paths.sort()

        out, skipped = [], {}

        def _skip(why):
            skipped[why] = skipped.get(why, 0) + 1

        for rel in paths[:limit]:
            rel = str(rel).strip().replace("\\", "/")
            full = _safe_join(root, rel)
            if not full or not os.path.isfile(full):
                _skip("파일 없음")
                continue
            if _zip_skip_reason(rel):
                _skip("코드 아님")
                continue
            if os.path.getsize(full) > MAX_VIEW_MB * 1024 * 1024:
                _skip("크기 초과")
                continue
            content = None
            for enc in ("utf-8", "cp949"):
                try:
                    with open(full, "r", encoding=enc) as fh:
                        content = fh.read()
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
                except Exception:
                    break
            if content is None:
                _skip("텍스트 아님")
                continue
            out.append({"filename": rel, "content": content})

        return jsonify({
            "files": out,
            "count": len(out),
            "skipped": skipped,
            "truncated": len(paths) > limit,
        })

    @app.route("/api/code/edits/preview", methods=["POST"])
    def api_edits_preview():
        """모델 답변에서 수정 블록을 뽑아 diff 만 만든다 (파일은 안 건드림)."""
        return _edits_endpoint(dry_run=True)

    @app.route("/api/code/edits/apply", methods=["POST"])
    def api_edits_apply():
        """모델이 제안한 수정을 실제 워크스페이스에 반영한다."""
        return _edits_endpoint(dry_run=False)

    def _edits_endpoint(dry_run: bool):
        from code_assist_v1.edits import parse_edits, apply_edits
        root = _ws_root(_get_uid())
        data = request.get_json(force=True, silent=True) or {}
        text = data.get("text") or ""
        if not text.strip():
            return jsonify({"error": "text 필요"}), 400
        edits = parse_edits(text)
        if not edits:
            return jsonify({"applied": 0, "failed": 0, "edits": [],
                            "message": "수정 블록이 없다"})
        res = apply_edits(edits, root, _safe_join, dry_run=dry_run)
        out = res.to_json()
        out["dry_run"] = dry_run
        if not dry_run:
            print(f"[ws] 수정 적용: {res.applied}건 성공 · {res.failed}건 거절")
        return jsonify(out)

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
