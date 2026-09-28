# -*- coding: utf-8 -*-
"""
demos_v1/whiteboard.py — 화이트보드 1단계: 답변 속 Mermaid 글을 그림(SVG)으로 바꿔 준다

  POST /api/whiteboard/render
      {"src": "flowchart TD ..."}                  → 그림 하나 (결과 그대로)
      {"items": [{"src": "..."}, ...]}             → 여러 개를 한 번에 → {"items": [결과, ...]}
      결과 = wb_render.render() — ok · kind · kind_ko · svg · w · h · title · error · line
  GET  /api/whiteboard/info                        → 그릴 수 있는 종류 · 판

★그림은 서버(wb_render.py)가 그린다. 폐쇄망이라 mermaid.min.js 를 받을 길이 없어서다.
  데모스(/) · 개인 에이전트 창 · 코딩 어시스턴트(/code/) 가 모두 이 한 곳을 부른다
  (화면 쪽은 static/whiteboard.js).
★그림 하나가 틀려도 답변은 그대로 보인다 — 못 그린 것은 ok=False 와 이유(몇째 줄)만 돌려준다.
"""
from __future__ import annotations

from flask import jsonify, request

from demos_v1 import wb_render

VERSION = "1.0"
MAX_ITEMS = 20            # 한 번에 받는 그림 수
MAX_TOTAL = 400_000       # 한 번에 받는 글 합계(자) — 그림 하나는 wb_render.MAX_SRC 로 따로 막는다


def _one(src) -> dict:
    if not isinstance(src, str):
        return {"ok": False, "kind": "", "error": "src 는 글이어야 합니다", "line": 0}
    return wb_render.render(src)


def register_whiteboard_routes(app):
    @app.route("/api/whiteboard/render", methods=["POST"])
    def api_whiteboard_render():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"ok": False, "error": "JSON 본문이 필요합니다"}), 400

        if "items" in data:
            items = data.get("items")
            if not isinstance(items, list):
                return jsonify({"ok": False, "error": "items 는 목록이어야 합니다"}), 400
            if len(items) > MAX_ITEMS:
                return jsonify({"ok": False, "error": f"한 번에 {MAX_ITEMS}개까지 그립니다"}), 413
            srcs = [(it.get("src") if isinstance(it, dict) else it) for it in items]
            total = sum(len(s) for s in srcs if isinstance(s, str))
            if total > MAX_TOTAL:
                return jsonify({"ok": False, "error": "글이 너무 깁니다 — 나눠 보내 주세요"}), 413
            return jsonify({"ok": True, "items": [_one(s) for s in srcs]})

        return jsonify(_one(data.get("src")))

    @app.route("/api/whiteboard/info", methods=["GET"])
    def api_whiteboard_info():
        return jsonify({"ok": True, "version": VERSION, "supported": list(wb_render.SUPPORTED),
                        "max_items": MAX_ITEMS, "max_src": wb_render.MAX_SRC})

    return True
