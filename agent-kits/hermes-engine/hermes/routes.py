"""
hermes/routes.py — Flask 라우트 (어떤 Flask 앱에도 드롭인)

register_hermes_routes(app) 한 줄이면 /api/hermes/* 가 붙는다.
메인 채팅(/api/chat 등)은 건드리지 않는다.
"""
from __future__ import annotations
from flask import request, jsonify

from . import engine, memory, skills, sessions


def _uid():
    return request.args.get("user_id", "") or ""


def register_hermes_routes(app) -> int:
    # 앱 시작 시 큐레이터 1회 (밀린 스킬 정리 따라잡기)
    try:
        from . import curator
        curator.run_all_users()
    except Exception:
        pass

    @app.route("/api/hermes/prep", methods=["POST"])
    def hermes_prep():
        d = request.get_json(force=True, silent=True) or {}
        uid = d.get("user_id", "")
        if not uid:
            return jsonify({"error": "user_id 필요", "system_addon": ""}), 200
        try:
            addon = engine.build_system_prompt(uid, d.get("query", ""))
        except Exception as e:
            return jsonify({"error": str(e), "system_addon": ""}), 200
        return jsonify({"system_addon": addon})

    @app.route("/api/hermes/post", methods=["POST"])
    def hermes_post():
        d = request.get_json(force=True, silent=True) or {}
        uid = d.get("user_id", "")
        if not uid:
            return jsonify({"error": "user_id 필요"}), 400
        answer = d.get("answer", "") or ""
        sid = d.get("session_id", "") or ""
        user_msg = d.get("user_message", "") or ""
        try:
            res = engine.apply_response(uid, answer)
        except Exception as e:
            return jsonify({"error": str(e), "clean": answer,
                            "pending_skills": [], "questions": []}), 200
        try:
            if user_msg:
                sessions.append_message(uid, "user", user_msg, sid)
            if res.get("clean"):
                sessions.append_message(uid, "assistant", res["clean"], sid)
        except Exception:
            pass
        review_due = False
        try:
            from . import counters
            counters.bump_turn(uid)
            dd = counters.due(uid)
            review_due = bool(dd.get("memory") or dd.get("skill"))
        except Exception:
            pass
        res["review_due"] = review_due
        return jsonify(res)

    @app.route("/api/hermes/skill/confirm", methods=["POST"])
    def hermes_skill_confirm():
        d = request.get_json(force=True, silent=True) or {}
        uid, spec = d.get("user_id", ""), d.get("spec") or {}
        if not uid or not spec:
            return jsonify({"error": "user_id/spec 필요"}), 400
        ok, msg = engine.confirm_skill(uid, spec)
        return jsonify({"ok": ok, "msg": msg})

    @app.route("/api/hermes/skills", methods=["GET"])
    def hermes_skills_list():
        return jsonify({"skills": skills.list_skills(_uid())})

    @app.route("/api/hermes/skill/view", methods=["GET"])
    def hermes_skill_view():
        import os
        ok, nm = skills.valid_name(request.args.get("name", ""))
        if not ok:
            return jsonify({"error": nm}), 400
        path = os.path.join(skills._skills_dir(_uid()), nm, "SKILL.md")
        return jsonify({"name": nm, "content": skills.store.read_text(path)})

    @app.route("/api/hermes/skill/pin", methods=["POST"])
    def hermes_skill_pin():
        d = request.get_json(force=True, silent=True) or {}
        return jsonify({"ok": skills.set_pinned(d.get("user_id", ""), d.get("name", ""), bool(d.get("pinned")))})

    @app.route("/api/hermes/skill/delete", methods=["POST"])
    def hermes_skill_delete():
        d = request.get_json(force=True, silent=True) or {}
        ok, msg = skills.delete(d.get("user_id", ""), d.get("name", ""))
        return jsonify({"ok": ok, "msg": msg})

    @app.route("/api/hermes/memory", methods=["GET"])
    def hermes_memory_get():
        uid = _uid()
        return jsonify({"memory": memory.read_items(uid, "memory"),
                        "user": memory.read_items(uid, "user")})

    @app.route("/api/hermes/memory/op", methods=["POST"])
    def hermes_memory_op():
        d = request.get_json(force=True, silent=True) or {}
        uid, sn, a = d.get("user_id", ""), d.get("store", "memory"), d.get("action", "add")
        if a == "add":
            ok, msg = memory.add(uid, sn, d.get("text", ""))
        elif a == "replace":
            ok, msg = memory.replace(uid, sn, d.get("target", ""), d.get("text", ""))
        elif a == "remove":
            ok, msg = memory.remove(uid, sn, d.get("target", ""))
        else:
            ok, msg = False, f"알 수 없는 액션: {a}"
        return jsonify({"ok": ok, "msg": msg})

    @app.route("/api/hermes/sessions/search", methods=["GET"])
    def hermes_sessions_search():
        uid, q = _uid(), request.args.get("q", "")
        if not q:
            return jsonify({"recent": sessions.list_recent(uid)})
        return jsonify({"hits": sessions.search(uid, q)})

    return 1
