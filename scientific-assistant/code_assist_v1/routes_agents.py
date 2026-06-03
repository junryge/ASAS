"""
code_assist_v1/routes_agents.py - 개인 에이전트(프리셋) 저장/로드 라우트

자주 쓰는 설정 묶음(모델·effort·스킬·지식검색·페르소나)을 사용자별로
code_assist_v1/agents/<user_id>/ 에 JSON 으로 저장한다.
routes_sessions.py 패턴을 따르되 user_id 로 스코프한다 (knowledge_store._scope_dir 참고).

엔드포인트:
    POST   /api/code/agent/save               (body: {user_id, agent_id?, name, persona, skills?, enable_knowledge?, model?, effort?})
    GET    /api/code/agent/list?user_id=...
    GET    /api/code/agent/load/<aid>?user_id=...
    DELETE /api/code/agent/delete/<aid>?user_id=...
"""
from __future__ import annotations
import json
import os
import time
from uuid import uuid4

from flask import request, jsonify

from code_assist_v1.config import AGENTS_DIR


def _safe_id(val: str) -> str:
    val = (val or "").strip()
    if not val or "/" in val or "\\" in val or ".." in val:
        return ""
    return val


def _scope_dir(user_id: str) -> str:
    """user_id 있으면 AGENTS_DIR/<user_id>, 없으면 AGENTS_DIR 루트."""
    uid = _safe_id(user_id)
    if uid:
        d = os.path.join(AGENTS_DIR, uid)
    else:
        d = AGENTS_DIR
    os.makedirs(d, exist_ok=True)
    return d


def _agent_path(user_id: str, aid: str) -> str:
    return os.path.join(_scope_dir(user_id), f"{aid}.json")


def _save(payload: dict) -> dict:
    user_id = _safe_id(payload.get("user_id") or "")
    aid = _safe_id(payload.get("agent_id") or "") or uuid4().hex

    effort = payload.get("effort")
    try:
        effort = int(effort) if effort is not None else 2
    except (TypeError, ValueError):
        effort = 2

    data = {
        "agent_id": aid,
        "user_id": user_id,
        "name": (payload.get("name") or "이름 없는 에이전트").strip()[:120],
        "persona": payload.get("persona") or "",
        "skills": [s for s in (payload.get("skills") or []) if isinstance(s, str)],
        "enable_knowledge": bool(payload.get("enable_knowledge")),
        "model": (payload.get("model") or "").strip(),
        "effort": effort,
        "timestamp": time.time(),
    }
    with open(_agent_path(user_id, aid), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def _load(user_id: str, aid: str) -> dict | None:
    aid = _safe_id(aid)
    if not aid:
        return None
    p = _agent_path(user_id, aid)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _list(user_id: str) -> list[dict]:
    d = _scope_dir(user_id)
    if not os.path.isdir(d):
        return []
    out: list[dict] = []
    for name in os.listdir(d):
        if not name.endswith(".json"):
            continue
        p = os.path.join(d, name)
        try:
            with open(p, "r", encoding="utf-8") as f:
                a = json.load(f)
            out.append(a)
        except Exception:
            continue
    out.sort(key=lambda a: a.get("timestamp", 0), reverse=True)
    return out


def _delete(user_id: str, aid: str) -> bool:
    aid = _safe_id(aid)
    if not aid:
        return False
    p = _agent_path(user_id, aid)
    if not os.path.isfile(p):
        return False
    try:
        os.remove(p)
        return True
    except Exception:
        return False


def _route_exists(app_or_bp, rule: str, method: str) -> bool:
    url_map = getattr(app_or_bp, "url_map", None)
    if url_map is None:
        return False
    for r in url_map.iter_rules():
        if str(r) == rule and method in (r.methods or set()):
            return True
    return False


def register_agent_routes(app) -> int:
    """개인 에이전트 라우트 등록. 이미 동일 URL+메서드가 있으면 건너뛴다.

    Returns: 새로 등록된 라우트 수.
    """
    registered = 0

    if not _route_exists(app, "/api/code/agent/save", "POST"):
        @app.route("/api/code/agent/save", methods=["POST"], endpoint="ca_agent_save")
        def _ca_agent_save():
            data = request.get_json(force=True, silent=True) or {}
            try:
                agent = _save(data)
            except Exception as e:
                return jsonify({"error": f"저장 실패: {e}"}), 500
            return jsonify({"agent": agent, "status": "saved"})
        registered += 1

    if not _route_exists(app, "/api/code/agent/list", "GET"):
        @app.route("/api/code/agent/list", endpoint="ca_agent_list")
        def _ca_agent_list():
            user_id = request.args.get("user_id", "")
            return jsonify({"agents": _list(user_id)})
        registered += 1

    if not _route_exists(app, "/api/code/agent/load/<agent_id>", "GET"):
        @app.route("/api/code/agent/load/<agent_id>", endpoint="ca_agent_load")
        def _ca_agent_load(agent_id):
            user_id = request.args.get("user_id", "")
            a = _load(user_id, agent_id)
            if a is None:
                return jsonify({"error": "에이전트 없음"}), 404
            return jsonify(a)
        registered += 1

    if not _route_exists(app, "/api/code/agent/delete/<agent_id>", "DELETE"):
        @app.route("/api/code/agent/delete/<agent_id>", methods=["DELETE"], endpoint="ca_agent_delete")
        def _ca_agent_delete(agent_id):
            user_id = request.args.get("user_id", "")
            ok = _delete(user_id, agent_id)
            if not ok:
                return jsonify({"error": "삭제 실패 또는 에이전트 없음"}), 404
            return jsonify({"status": "deleted", "agent_id": agent_id})
        registered += 1

    return registered
