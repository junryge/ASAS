"""
demos_v1/hermes/routes.py — 헤르메스 Flask 라우트 (방안 A: 메인 /api/chat 무수정)

흐름 (개인 에이전트 창이 헤르메스 ON일 때):
  1. POST /api/hermes/prep  {user_id, query}
       → 시스템 프롬프트에 더할 헤르메스 블록(system_addon) 반환
       → 창이 이걸 system_prompt 에 합쳐 기존 /api/chat 로 스트리밍
  2. POST /api/hermes/post  {user_id, answer, user_message, session_id}
       → 응답 블록 처리: 메모리 즉시저장 / 스킬은 승인대기(pending) / 되묻기 추출
       → 세션 로그 기록 + 카운터 증가 (+ 리뷰 due 플래그)
  3. POST /api/hermes/skill/confirm {user_id, spec}  → 승인된 스킬 실제 저장

그 외: 스킬 목록/보기/pin/삭제, 메모리 조회/편집, 세션 검색
"""
from __future__ import annotations
from flask import request, jsonify

from demos_v1.hermes import engine, memory, skills, sessions, counters


def _uid():
    return request.args.get("user_id", "") or ""


def register_hermes_routes(app) -> int:
    registered = 0

    # 앱 시작 시 큐레이터 1회 (밀린 스킬 정리 따라잡기)
    try:
        from demos_v1.hermes import curator
        _cr = curator.run_all_users()
        if _cr.get("ran"):
            print(f"  🗂 헤르메스 큐레이터: {_cr['ran']}명 (stale {_cr['staled']}, archive {_cr['archived']})")
    except Exception as _ce:
        print(f"  ⚠️  헤르메스 큐레이터 스킵: {_ce}")

    # ── 1) 프롬프트 준비 ──
    @app.route("/api/hermes/prep", methods=["POST"])
    def hermes_prep():
        d = request.get_json(force=True, silent=True) or {}
        uid = d.get("user_id", "")
        if not uid:
            return jsonify({"error": "user_id 필요"}), 400
        try:
            addon = engine.build_system_prompt(uid, d.get("query", ""))
        except Exception as e:
            return jsonify({"error": f"prep 실패: {e}", "system_addon": ""}), 200
        return jsonify({"system_addon": addon})

    # ── 2) 응답 후처리 ──
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
            return jsonify({"error": f"post 실패: {e}", "clean": answer,
                            "pending_skills": [], "questions": []}), 200

        # 세션 로그 (사용자 메시지 + 정리된 답변)
        try:
            if user_msg:
                sessions.append_message(uid, "user", user_msg, sid)
            if res.get("clean"):
                sessions.append_message(uid, "assistant", res["clean"], sid)
        except Exception:
            pass

        # 카운터 + 리뷰 due
        review_due = False
        try:
            counters.bump_turn(uid)
            due = counters.due(uid)
            review_due = bool(due.get("memory") or due.get("skill"))
        except Exception:
            pass

        res["review_due"] = review_due
        return jsonify(res)

    # ── 3) 스킬 승인 저장 (확인형) ──
    @app.route("/api/hermes/skill/confirm", methods=["POST"])
    def hermes_skill_confirm():
        d = request.get_json(force=True, silent=True) or {}
        uid = d.get("user_id", "")
        spec = d.get("spec") or {}
        if not uid or not spec:
            return jsonify({"error": "user_id/spec 필요"}), 400
        ok, msg = engine.confirm_skill(uid, spec)
        return jsonify({"ok": ok, "msg": msg})

    # ── 스킬 관리 ──
    @app.route("/api/hermes/skills", methods=["GET"])
    def hermes_skills_list():
        return jsonify({"skills": skills.list_skills(_uid())})

    @app.route("/api/hermes/skill/view", methods=["GET"])
    def hermes_skill_view():
        uid = _uid()
        name = request.args.get("name", "")
        ok, nm = skills.valid_name(name)
        if not ok:
            return jsonify({"error": nm}), 400
        import os
        path = os.path.join(skills._skills_dir(uid), nm, "SKILL.md")
        return jsonify({"name": nm, "content": skills.store.read_text(path)})

    @app.route("/api/hermes/skill/pin", methods=["POST"])
    def hermes_skill_pin():
        d = request.get_json(force=True, silent=True) or {}
        ok = skills.set_pinned(d.get("user_id", ""), d.get("name", ""), bool(d.get("pinned")))
        return jsonify({"ok": ok})

    @app.route("/api/hermes/skill/delete", methods=["POST"])
    def hermes_skill_delete():
        d = request.get_json(force=True, silent=True) or {}
        ok, msg = skills.delete(d.get("user_id", ""), d.get("name", ""))
        return jsonify({"ok": ok, "msg": msg})

    # ── 메모리 조회/편집 (사용자 직접) ──
    @app.route("/api/hermes/memory", methods=["GET"])
    def hermes_memory_get():
        uid = _uid()
        return jsonify({
            "memory": memory.read_items(uid, "memory"),
            "user": memory.read_items(uid, "user"),
        })

    @app.route("/api/hermes/memory/op", methods=["POST"])
    def hermes_memory_op():
        d = request.get_json(force=True, silent=True) or {}
        uid = d.get("user_id", "")
        sname = d.get("store", "memory")
        action = d.get("action", "add")
        if action == "add":
            ok, msg = memory.add(uid, sname, d.get("text", ""))
        elif action == "replace":
            ok, msg = memory.replace(uid, sname, d.get("target", ""), d.get("text", ""))
        elif action == "remove":
            ok, msg = memory.remove(uid, sname, d.get("target", ""))
        else:
            ok, msg = False, f"알 수 없는 액션: {action}"
        return jsonify({"ok": ok, "msg": msg})

    # ── 세션 검색 ──
    @app.route("/api/hermes/sessions/search", methods=["GET"])
    def hermes_sessions_search():
        uid = _uid()
        q = request.args.get("q", "")
        if not q:
            return jsonify({"recent": sessions.list_recent(uid)})
        return jsonify({"hits": sessions.search(uid, q)})

    registered = 1
    return registered
