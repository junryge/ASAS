"""
routes_foundry.py - 자율 제조 공장 (Foundry v6.3) GGUF 연결 엔드포인트
app.py 또는 메인 등록부에서 register_foundry_routes(app) 한 줄로 등록.
"""
import os
import gc
from flask import request, jsonify


def register_foundry_routes(app):
    """Foundry 전용 라우트 등록. 기존 routes_api.py 건드리지 않음."""
    from demos_v1.gguf import find_gguf_files, load_gguf_model, _pool_status
    from demos_v1.config import _gguf_pool, _gguf_pool_lock, VRAM_BUDGET_GB
    from demos_v1.utils import BASE_DIR
    import demos_v1.utils as _u

    # -------------------- Foundry UI 서빙 --------------------
    @app.route("/foundry")
    def foundry_page():
        """자율 제조 공장 v6.3 UI 페이지 (foundry_v1.html 그대로 서빙)."""
        path = os.path.join(BASE_DIR, "foundry_v1.html")
        if not os.path.exists(path):
            return "foundry_v1.html not found at " + path, 404
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    # -------------------- GGUF 목록 --------------------
    @app.route("/api/gguf/list")
    def api_gguf_list():
        """BASE_DIR / models / model 폴더에서 GGUF 파일 검색."""
        files = find_gguf_files()
        return jsonify({
            "files": files,
            "count": len(files),
            "vram_budget_gb": VRAM_BUDGET_GB,
        })

    # -------------------- GGUF 로드 --------------------
    @app.route("/api/gguf/load", methods=["POST"])
    def api_gguf_load():
        """GGUF 모델 수동 로드. body: { path: str, n_ctx?: int }"""
        data = request.json or {}
        path = data.get("path")
        n_ctx = int(data.get("n_ctx", 16384))
        if not path:
            return jsonify({"ok": False, "error": "path 필수"}), 400
        if not os.path.exists(path):
            return jsonify({"ok": False, "error": "파일 없음: " + path}), 404
        try:
            ok = load_gguf_model(path, n_ctx=n_ctx)
            size_gb = round(os.path.getsize(path) / 1e9, 1)
            pool = _pool_status()
            vram_used = sum(e.get("size_gb", 0) for e in pool)
            return jsonify({
                "ok": bool(ok),
                "loaded": os.path.basename(path),
                "path": path,
                "size_gb": size_gb,
                "n_ctx": n_ctx,
                "vram_used_gb": vram_used,
                "vram_budget_gb": VRAM_BUDGET_GB,
                "pool": pool,
            })
        except Exception as e:
            return jsonify({"ok": False, "error": str(e), "type": type(e).__name__}), 500

    # -------------------- GGUF 언로드 --------------------
    @app.route("/api/gguf/unload", methods=["POST"])
    def api_gguf_unload():
        """현재 로드된 GGUF 모델 + 풀에서 idle 항목 전부 언로드."""
        prev = _u.gguf_loaded_path
        _u.gguf_model = None
        _u.gguf_loaded_path = None
        # 풀에서 사용 중이 아닌 항목 제거
        with _gguf_pool_lock:
            idle = [e for e in _gguf_pool if not e.get("in_use")]
            for e in idle:
                _gguf_pool.remove(e)
                try:
                    del e["model"]
                except Exception:
                    pass
            removed = len(idle)
        gc.collect()
        # CUDA VRAM 해제 (가능하면)
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        return jsonify({
            "ok": True,
            "unloaded": os.path.basename(prev) if prev else None,
            "removed_from_pool": removed,
            "pool": _pool_status(),
        })

    # -------------------- GGUF 채팅 (단일 호출, 4대 요소 순차 사용) --------------------
    @app.route("/api/gguf/chat", methods=["POST"])
    def api_gguf_chat():
        """로드된 GGUF로 단일 추론. body: { messages, temperature?, max_tokens? }"""
        from demos_v1.gguf import gguf_chat
        data = request.json or {}
        messages = data.get("messages") or []
        if not messages:
            return jsonify({"ok": False, "error": "messages 필수"}), 400
        try:
            text = gguf_chat(
                messages,
                temperature=float(data.get("temperature", 0.5)),
                max_tokens=int(data.get("max_tokens", 4096)),
            )
            return jsonify({"ok": True, "text": text})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
