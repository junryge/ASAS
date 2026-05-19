"""
backend/routes_elements.py - 5대 요소 Flask Blueprint.

prefix: /api/elements
mode 파라미터로 elements_api / elements_gguf 분기.
"""
import json
import traceback

from flask import Blueprint, Response, jsonify, request

from . import elements_api, elements_gguf, ralph_orchestrator


bp = Blueprint("elements", __name__, url_prefix="/api/elements")


def _pick_mode(data):
    mode = (data.get("mode") or "api").lower()
    if mode not in ("api", "gguf"):
        return None, jsonify({"ok": False, "error": "mode must be 'api' or 'gguf'"}), 400
    return mode, None, None


# =====================================================================
# 나노봇 — 4단 SSE 스트림
# =====================================================================
@bp.route("/nanabot/stream", methods=["POST"])
def nanabot_stream():
    data = request.json or {}
    mode, err_resp, err_code = _pick_mode(data)
    if err_resp:
        return err_resp, err_code

    requirement = (data.get("requirement") or "").strip()
    if not requirement:
        return jsonify({"ok": False, "error": "requirement 필수"}), 400
    type_label = data.get("type_label", "일반 프로그램")
    lang_label = data.get("language_label", "Python")
    fw_label = data.get("framework_label", "")
    model_id = data.get("model_id")

    if mode == "api":
        nb = elements_api.Nanabot(model_id=model_id)
    else:
        nb = elements_gguf.Nanabot()

    def emit(obj):
        return "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"

    def generate():
        outputs = []
        for stage in nb.stages(requirement, type_label, lang_label, fw_label):
            try:
                yield emit({"stage": stage["id"], "name": stage["name"], "status": "running"})
                text, used = nb.run_stage(stage, outputs)
                outputs.append(text)
                yield emit({
                    "stage": stage["id"], "name": stage["name"],
                    "status": "done", "output": text, "model": used,
                })
            except Exception as e:
                traceback.print_exc()
                yield emit({"stage": stage["id"], "status": "error", "error": str(e)})
                return
        final_md = (outputs[2] if len(outputs) > 2 else "") + (
            "\n\n---\n\n## 🔍 자체 검토 (Reviewer)\n\n" + outputs[3] if len(outputs) > 3 else ""
        )
        yield emit({"stage": "complete", "status": "done", "final_md": final_md})

    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive",
    })


# =====================================================================
# 컨텍스트 — 파서
# =====================================================================
@bp.route("/context/parse", methods=["POST"])
def context_parse():
    data = request.json or {}
    mode, err_resp, err_code = _pick_mode(data)
    if err_resp:
        return err_resp, err_code
    requirement = (data.get("requirement") or "").strip()
    if not requirement:
        return jsonify({"ok": False, "error": "requirement 필수"}), 400
    csv_uri = data.get("csv_uri")

    try:
        if mode == "api":
            ctx = elements_api.Context(model_id=data.get("model_id"))
        else:
            ctx = elements_gguf.Context()
        parsed = ctx.parse(requirement, csv_uri=csv_uri)
        return jsonify({"ok": True, "parsed": parsed})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# =====================================================================
# 헤르메스 — 코드 생성
# =====================================================================
@bp.route("/hermes/generate", methods=["POST"])
def hermes_generate():
    data = request.json or {}
    mode, err_resp, err_code = _pick_mode(data)
    if err_resp:
        return err_resp, err_code
    md_spec = (data.get("md_spec") or "").strip()
    if not md_spec:
        return jsonify({"ok": False, "error": "md_spec 필수"}), 400
    lang = data.get("lang", "Python")
    fw = data.get("fw", "")

    try:
        if mode == "api":
            hm = elements_api.Hermes(model_id=data.get("model_id"))
        else:
            hm = elements_gguf.Hermes()
        result = hm.generate(md_spec, lang=lang, fw=fw)
        return jsonify({"ok": True, **result})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# =====================================================================
# 하네스 — 검증 (L1+L2)
# =====================================================================
@bp.route("/harness/validate", methods=["POST"])
def harness_validate():
    data = request.json or {}
    mode, err_resp, err_code = _pick_mode(data)
    if err_resp:
        return err_resp, err_code
    code = data.get("code") or ""
    if not code.strip():
        return jsonify({"ok": False, "error": "code 필수"}), 400

    try:
        if mode == "api":
            hn = elements_api.Harness(model_id_l2=data.get("model_id_l2"))
        else:
            hn = elements_gguf.Harness()
        verdict = hn.validate(code, run_l2=bool(data.get("run_l2", True)))
        return jsonify({"ok": True, "verdict": verdict})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# =====================================================================
# 랄프 위검 — 헤르메스↔하네스 루프 SSE
# =====================================================================
@bp.route("/ralph/loop", methods=["POST"])
def ralph_loop():
    data = request.json or {}
    mode, err_resp, err_code = _pick_mode(data)
    if err_resp:
        return err_resp, err_code
    md_spec = (data.get("md_spec") or "").strip()
    if not md_spec:
        return jsonify({"ok": False, "error": "md_spec 필수"}), 400

    max_iter = int(data.get("max_iter", 20))
    lang = data.get("lang", "Python")
    fw = data.get("fw", "")

    if mode == "api":
        hermes = elements_api.Hermes(model_id=data.get("hermes_model_id"))
        harness = elements_api.Harness(model_id_l2=data.get("harness_model_id_l2"))
    else:
        hermes = elements_gguf.Hermes()
        harness = elements_gguf.Harness()

    def emit(obj):
        return "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"

    def generate():
        try:
            for ev in ralph_orchestrator.run_loop(
                hermes, harness, md_spec, lang=lang, fw=fw, max_iter=max_iter,
            ):
                yield emit(ev)
        except Exception as e:
            traceback.print_exc()
            yield emit({"event": "error", "error": str(e)})

    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive",
    })


# =====================================================================
# 모델 목록 (UI 드롭다운용)
# =====================================================================
@bp.route("/models", methods=["GET"])
def list_models():
    from . import config as cfg
    items = []
    for mid, m in cfg.MODELS.items():
        items.append({
            "id": mid,
            "name": m.get("name"),
            "model": m.get("model"),
            "capabilities": m.get("capabilities", []),
            "cost_tier": m.get("cost_tier"),
            "context_window": m.get("context_window"),
        })
    return jsonify({"ok": True, "models": items, "tiers": cfg.API_MODEL_TIERS})


def register(app):
    """foundry_server.py 에서 한 줄로 등록."""
    app.register_blueprint(bp)
