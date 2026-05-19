"""
backend/routes_elements.py - 5대 요소 Flask Blueprint.

prefix: /api/elements
mode 파라미터로 elements_api / elements_gguf 분기.
"""
import csv
import io
import json
import os
import traceback
import uuid

from flask import Blueprint, Response, jsonify, request
from werkzeug.utils import secure_filename

from . import context_schemas, elements_api, elements_gguf, ralph_orchestrator


UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50MB
ALLOWED_EXT = {
    ".csv", ".tsv", ".json", ".parquet", ".xlsx", ".npy",
    ".yaml", ".yml", ".txt", ".env", ".md",
}


def save_upload(file_storage):
    """업로드 파일을 backend/uploads/<uuid>.<ext> 로 저장. (saved_path, original_name)."""
    name = secure_filename(file_storage.filename or "upload")
    ext = os.path.splitext(name)[1].lower()
    if ext and ext not in ALLOWED_EXT:
        raise ValueError(f"허용되지 않는 확장자: {ext}")
    uid = uuid.uuid4().hex[:12]
    out_name = f"{uid}{ext or '.bin'}"
    out_path = os.path.join(UPLOAD_DIR, out_name)
    file_storage.save(out_path)
    size = os.path.getsize(out_path)
    if size > MAX_UPLOAD_BYTES:
        os.remove(out_path)
        raise ValueError(f"파일 50MB 초과 ({size} bytes)")
    return out_path, name


def peek_csv(path, max_preview_rows=5):
    """CSV/TSV 한정 컬럼명 + 행수 추출. 실패 시 None."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".csv", ".tsv"):
        return None
    delim = "\t" if ext == ".tsv" else ","
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            head = f.read(8192)
        reader = csv.reader(io.StringIO(head), delimiter=delim)
        rows = list(reader)
        if not rows:
            return None
        columns = rows[0]
        # 전체 행수는 라인 수로 추정 (헤더 1줄 제외)
        with open(path, "rb") as f:
            line_count = sum(1 for _ in f)
        return {
            "columns": columns[:64],
            "rows": max(line_count - 1, 0),
            "preview": rows[1:1 + max_preview_rows],
        }
    except Exception:
        return None


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
    """multipart/form-data 우선, JSON도 허용 (호환).

    multipart 필드:
      - mode: "api" | "gguf"
      - project_type: "ml" | "data" | "web" | "cli" | "automation" | "general"
      - slots_json: {"requirement": "...", "metric": "...", "freeform_note": "..."}
      - model_id: 선택 (api 모드)
      - <file_slot_key>: 파일 (예: dataset, schema_file, example_input, config_file)
      - attachments: 다중 파일 (선택)
    """
    if request.content_type and request.content_type.startswith("multipart/"):
        mode = (request.form.get("mode") or "api").lower()
        if mode not in ("api", "gguf"):
            return jsonify({"ok": False, "error": "mode must be 'api' or 'gguf'"}), 400
        project_type = (request.form.get("project_type") or "general").lower()
        model_id = request.form.get("model_id") or None
        try:
            slots = json.loads(request.form.get("slots_json") or "{}")
        except json.JSONDecodeError:
            return jsonify({"ok": False, "error": "slots_json 파싱 실패"}), 400

        schema = context_schemas.get_schema(project_type)
        file_slot_keys = [k for k, w in schema["widgets"].items() if w == "file"]

        saved_files = []  # 정리용
        dataset_meta = None
        try:
            for key in file_slot_keys:
                if key == "attachments":
                    files = request.files.getlist("attachments")
                    paths = []
                    for f in files:
                        if not f or not f.filename:
                            continue
                        path, orig = save_upload(f)
                        saved_files.append(path)
                        paths.append({"path": path, "name": orig})
                    if paths:
                        slots["attachments"] = paths
                else:
                    f = request.files.get(key)
                    if f and f.filename:
                        path, orig = save_upload(f)
                        saved_files.append(path)
                        slots[key] = path
                        if key == "dataset":
                            dataset_meta = peek_csv(path)

            if mode == "api":
                ctx = elements_api.Context(model_id=model_id)
            else:
                ctx = elements_gguf.Context()
            parsed = ctx.parse(project_type=project_type, slots=slots, dataset_meta=dataset_meta)
            return jsonify({
                "ok": True,
                "parsed": parsed,
                "dataset_meta": dataset_meta,
                "saved_files": [os.path.basename(p) for p in saved_files],
            })
        except ValueError as ve:
            return jsonify({"ok": False, "error": str(ve)}), 413
        except Exception as e:
            traceback.print_exc()
            return jsonify({"ok": False, "error": str(e)}), 500

    # JSON 경로 (파일 없이 호출)
    data = request.json or {}
    mode, err_resp, err_code = _pick_mode(data)
    if err_resp:
        return err_resp, err_code
    project_type = (data.get("project_type") or "general").lower()
    slots = data.get("slots") or {}
    if not slots and data.get("requirement"):
        slots = {"requirement": data["requirement"]}
    try:
        if mode == "api":
            ctx = elements_api.Context(model_id=data.get("model_id"))
        else:
            ctx = elements_gguf.Context()
        parsed = ctx.parse(project_type=project_type, slots=slots)
        return jsonify({"ok": True, "parsed": parsed})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/context/schemas", methods=["GET"])
def context_schemas_route():
    """UI가 슬롯 템플릿 자동 동기화할 때 쓸 수 있는 단일 진실 소스."""
    return jsonify({"ok": True, "schemas": {
        k: {"required": v["required"], "widgets": v["widgets"]}
        for k, v in context_schemas.SCHEMAS.items()
    }})


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
