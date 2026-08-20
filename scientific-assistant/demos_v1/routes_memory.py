"""demos_v1/routes_memory.py — 기억 보기·지우기 API.

★사람이 들여다볼 수 있어야 한다. 어떤 기억이 쌓였는지 못 보면, 엉뚱한
  답이 나왔을 때 원인이 기억인지 모델인지 가릴 수가 없다.
"""
from flask import jsonify, request

from demos_v1 import memory as M


def _uid() -> str:
    d = request.get_json(silent=True) or {}
    return str(request.args.get("user_id") or d.get("user_id") or "").strip()


def register_memory_routes(app) -> None:

    @app.route("/api/memory", methods=["GET"])
    def api_memory_list():
        """쌓인 기억 목록 + 현황."""
        uid = _uid()
        if not uid:
            return jsonify({"error": "user_id 가 필요합니다"}), 400
        return jsonify({"items": M.all_memories(uid), "stats": M.stats(uid)})

    @app.route("/api/memory/search", methods=["GET"])
    def api_memory_search():
        """지금 이 질문이면 무엇이 들어갈지 — 미리 보기."""
        uid = _uid()
        q = (request.args.get("q") or "").strip()
        if not uid or not q:
            return jsonify({"error": "user_id 와 q 가 필요합니다"}), 400
        hits = M.search(uid, q, top=int(request.args.get("top") or M.DEFAULT_TOP))
        blk, used = M.block(uid, q)
        return jsonify({"hits": hits, "block": blk, "used": used})

    @app.route("/api/memory/forget", methods=["POST"])
    def api_memory_forget():
        """★지우지 않고 접는다 — 왜 사라졌냐에 답할 수 있어야 한다."""
        uid = _uid()
        mid = str((request.get_json(silent=True) or {}).get("mid") or "").strip()
        if not uid or not mid:
            return jsonify({"error": "user_id 와 mid 가 필요합니다"}), 400
        return jsonify({"ok": M.forget(uid, mid)})

    @app.route("/api/memory/add", methods=["POST"])
    def api_memory_add():
        """사람이 직접 적어 넣기 — 모델이 못 뽑은 것을 손으로 박을 수 있어야 한다."""
        uid = _uid()
        b = request.get_json(silent=True) or {}
        text = str(b.get("text") or "").strip()
        if not uid or not text:
            return jsonify({"error": "user_id 와 text 가 필요합니다"}), 400
        kind = str(b.get("kind") or "사실")
        n = M.add(uid, [{"kind": kind if kind in M.KINDS else "사실",
                         "text": text[:M.MAX_TEXT], "why": "직접 적음"}])
        return jsonify({"ok": True, "added": n})

    @app.route("/api/memory/tick", methods=["POST"])
    def api_memory_tick():
        """지금 바로 한 바퀴 돌린다 — 45초를 기다리지 않고 확인하려고."""
        try:
            return jsonify({"ok": True, **M.tick()})
        except Exception as e:
            return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500
