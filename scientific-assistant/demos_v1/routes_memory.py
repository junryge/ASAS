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
        st = M.stats(uid)
        # ★"왜 안 들어갔나" 를 사람 말로 답한다. 이게 없으면 안 될 때
        #   원인이 기억인지 모델인지 사용자가 가릴 수가 없다.
        if st["live"] == 0 and st["pending"] == 0:
            why = (f"'{uid}' 로 쌓인 기억이 없습니다. 기억은 사용자별로 따로 "
                   f"모입니다 — 다른 아이디로 대화했다면 그쪽에 있습니다. "
                   f"대화 {M.KEEP_TAIL + M.CAPTURE_EVERY}턴쯤 지나야 담기기 시작합니다.")
        elif st["live"] == 0 and st["pending"]:
            why = (f"담아 둔 조각이 {st['pending']}개 있는데 아직 안 뽑았습니다. "
                   f"배경 일꾼이 {M.TICK_SEC}초마다 돕니다 — "
                   f"POST /api/memory/tick 으로 바로 돌릴 수 있습니다.")
        elif not blk:
            why = f"기억은 {st['live']}건 있는데 이 질문과 걸리는 게 없습니다."
        else:
            why = f"기억 {st['live']}건 중 {len(used)}건이 들어갑니다."
        return jsonify({"hits": hits, "block": blk, "used": used,
                        "stats": st, "why": why})

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

    @app.route("/api/memory/backfill", methods=["POST"])
    def api_memory_backfill():
        """지난 세션에서 기억을 채운다.

        ★기억 기능은 붙인 날부터 쌓인다. 그전 대화는 비어 있어서 처음 켠
          사람에게는 고장으로 보인다 — 지난 대화는 이미 저장돼 있으니
          거기서 채운다.
        """
        uid = _uid()
        if not uid:
            return jsonify({"error": "user_id 가 필요합니다"}), 400
        b = request.get_json(silent=True) or {}
        try:
            lim = int(b.get("limit") or M.BACKFILL_MAX_SESSIONS)
        except (TypeError, ValueError):
            lim = M.BACKFILL_MAX_SESSIONS
        return jsonify(M.backfill(uid, lim))

    @app.route("/api/memory/tick", methods=["POST"])
    def api_memory_tick():
        """지금 바로 한 바퀴 돌린다 — 45초를 기다리지 않고 확인하려고."""
        try:
            return jsonify({"ok": True, **M.tick()})
        except Exception as e:
            return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500
