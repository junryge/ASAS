"""
code_assist_v1/routes_skills.py - 스킬 CRUD (단일 skills/ 폴더)
"""
from __future__ import annotations
import os
import re
import shutil
from datetime import datetime
from flask import request, jsonify

from code_assist_v1.config import SKILLS_DIR, SKILL_WHITELIST_JSON
from code_assist_v1.skill_filter import (
    list_skills,
    get_skill_meta,
    load_skill_content,
    get_skill_path,
)
from code_assist_v1.skill_whitelist import (
    load_user_whitelist,
    save_user_whitelist,
)


_SKILL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9\-_]{1,63}$")


def _validate_skill_id(skill_id: str) -> tuple[bool, str]:
    if not skill_id:
        return False, "skill_id 가 비어있습니다"
    if not _SKILL_ID_RE.match(skill_id):
        return False, "skill_id 는 소문자/숫자/하이픈/언더스코어만 (2~64자)"
    return True, ""


def _build_frontmatter(meta: dict) -> str:
    name = meta.get("name") or meta.get("id") or ""
    desc = meta.get("description") or ""
    license_ = meta.get("license") or "MIT"
    author = meta.get("author") or ""
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    created = meta.get("created") or datetime.now().strftime("%Y-%m-%d")

    lines = ["---", f"name: {name}", f"description: {desc}", f"license: {license_}", "metadata:"]
    if author:
        lines.append(f"  author: {author}")
    lines.append(f"  created: {created}")
    if tags:
        lines.append(f"  tags: [{', '.join(tags)}]")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _sync_harness():
    """(없앰) 예전엔 skills/ 를 하네스 ToolRegistry 에 밀어 넣었다.

    ★그 레지스트리는 데모스가 scientific-skills 389개로 쓰는 **공용** 물건
      이다. 여기서 손대면 남의 것을 오염시킨다. 게다가 code_assist_v1/skills/
      는 비어 있어서 실제로 넣는 것도 없었다. 호출부는 남겨 두되 아무것도
      하지 않는다 — 코드 어시스턴트는 자기 skill_filter 로 스킬을 읽는다.
    """
    return


def register_skill_routes(app):

    @app.route("/api/code/skills/list")
    def api_skills_list():
        query = request.args.get("q", "").strip()
        items = list_skills(query=query)
        return jsonify({"total": len(items), "items": items})

    @app.route("/api/code/skills/<skill_id>")
    def api_skills_view(skill_id):
        meta = get_skill_meta(skill_id)
        if not meta:
            return jsonify({"error": "스킬을 찾을 수 없습니다"}), 404
        content = load_skill_content(skill_id, max_chars=50000) or ""
        return jsonify({"meta": meta, "content": content})

    @app.route("/api/code/skills/create", methods=["POST"])
    def api_skills_create():
        data = request.get_json(force=True, silent=True) or {}
        skill_id = (data.get("id") or "").strip().lower()
        ok, err = _validate_skill_id(skill_id)
        if not ok:
            return jsonify({"error": err}), 400

        skill_dir = os.path.join(SKILLS_DIR, skill_id)
        if os.path.exists(skill_dir):
            return jsonify({"error": "이미 같은 ID 의 스킬이 존재합니다"}), 409

        os.makedirs(skill_dir, exist_ok=True)
        fm = _build_frontmatter({
            "id": skill_id,
            "name": data.get("name", skill_id),
            "description": data.get("description", ""),
            "license": data.get("license", "MIT"),
            "author": data.get("author", ""),
            "tags": data.get("tags", []),
        })
        body = data.get("body", "") or f"# {data.get('name', skill_id)}\n\n{data.get('description', '')}\n"
        skill_md = os.path.join(skill_dir, "SKILL.md")
        with open(skill_md, "w", encoding="utf-8") as f:
            f.write(fm + body)
        _sync_harness()
        return jsonify({"status": "created", "id": skill_id, "path": skill_md})

    @app.route("/api/code/skills/update", methods=["POST"])
    def api_skills_update():
        data = request.get_json(force=True, silent=True) or {}
        skill_id = (data.get("id") or "").strip().lower()
        ok, err = _validate_skill_id(skill_id)
        if not ok:
            return jsonify({"error": err}), 400

        skill_md = os.path.join(SKILLS_DIR, skill_id, "SKILL.md")
        if not os.path.isfile(skill_md):
            return jsonify({"error": "스킬 없음"}), 404

        if "content" in data and isinstance(data["content"], str):
            new_content = data["content"]
        else:
            fm = _build_frontmatter({
                "id": skill_id,
                "name": data.get("name", skill_id),
                "description": data.get("description", ""),
                "license": data.get("license", "MIT"),
                "author": data.get("author", ""),
                "tags": data.get("tags", []),
            })
            new_content = fm + (data.get("body") or "")
        with open(skill_md, "w", encoding="utf-8") as f:
            f.write(new_content)
        _sync_harness()
        return jsonify({"status": "updated", "id": skill_id})

    @app.route("/api/code/skills/delete", methods=["POST"])
    def api_skills_delete():
        data = request.get_json(force=True, silent=True) or {}
        skill_id = (data.get("id") or "").strip().lower()
        ok, err = _validate_skill_id(skill_id)
        if not ok:
            return jsonify({"error": err}), 400
        skill_dir = os.path.join(SKILLS_DIR, skill_id)
        if not os.path.isdir(skill_dir):
            return jsonify({"error": "스킬 없음"}), 404
        try:
            shutil.rmtree(skill_dir)
        except Exception as e:
            return jsonify({"error": f"삭제 실패: {e}"}), 500
        _sync_harness()
        return jsonify({"status": "deleted", "id": skill_id})

    @app.route("/api/code/skills/whitelist", methods=["GET", "POST"])
    def api_skills_whitelist():
        if request.method == "GET":
            data = load_user_whitelist(SKILL_WHITELIST_JSON) or {"include": [], "exclude": []}
            return jsonify(data)
        data = request.get_json(force=True, silent=True) or {}
        norm = {
            "include": [s for s in (data.get("include") or []) if isinstance(s, str)],
            "exclude": [s for s in (data.get("exclude") or []) if isinstance(s, str)],
        }
        save_user_whitelist(SKILL_WHITELIST_JSON, norm)
        return jsonify({"status": "saved", "data": norm})
