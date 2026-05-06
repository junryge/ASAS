"""
Goose App - Goose Desktop Clone
Flask 백엔드: LLM 프록시, 세션, 확장, 레시피 API
"""

import os
import json
import uuid
import time
import glob
import yaml
import threading
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory, Response, stream_with_context
import requests as req

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
EXTENSIONS_DIR = os.path.join(BASE_DIR, "extensions")
RECIPES_DIR = os.path.join(BASE_DIR, "recipes")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

for d in [SESSIONS_DIR, EXTENSIONS_DIR, RECIPES_DIR, UPLOADS_DIR]:
    os.makedirs(d, exist_ok=True)

# ── Config ──
_CONFIG_PATH = os.path.join(BASE_DIR, "api_config.json")
CONFIG = {}
if os.path.isfile(_CONFIG_PATH):
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        CONFIG = json.load(f)
    print(f"[CONFIG] Loaded {len(CONFIG.get('models', {}))} models")

API_TOKEN = ""
_token_path = os.path.join(BASE_DIR, "TOKEN.TXT")
if os.path.isfile(_token_path):
    API_TOKEN = open(_token_path).read().strip()

# ── In-memory state ──
chat_stop_flag = {"stop": False}
active_subagents = {}  # {id: {status, messages, result}}


# ============================================
# Helper: LLM API call
# ============================================
def call_llm(model_key, messages, max_tokens=4096, stream=False, temperature=0.7):
    """Call LLM API with fallback chain support."""
    models = CONFIG.get("models", {})
    fallbacks = CONFIG.get("fallback_chains", {})

    # Build chain: primary + fallbacks
    chain = [model_key]
    if model_key in fallbacks:
        chain.extend(fallbacks[model_key])

    last_error = None
    for mk in chain:
        if mk not in models:
            continue
        m = models[mk]
        url = m["url"]
        model_name = m["model"]

        headers = {"Content-Type": "application/json"}
        if API_TOKEN:
            headers["Authorization"] = f"Bearer {API_TOKEN}"

        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }

        try:
            if stream:
                resp = req.post(url, json=payload, headers=headers, stream=True, timeout=120)
                if resp.status_code == 200:
                    return resp
            else:
                resp = req.post(url, json=payload, headers=headers, timeout=120)
                if resp.status_code == 200:
                    return resp.json()
            last_error = f"{mk}: HTTP {resp.status_code}"
        except Exception as e:
            last_error = f"{mk}: {e}"
            continue

    return {"error": last_error or "All models failed"}


# ============================================
# Routes: Pages
# ============================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(os.path.join(BASE_DIR, "static"), filename)


# ============================================
# Routes: Config
# ============================================
@app.route("/api/config")
def api_config():
    models = CONFIG.get("models", {})
    providers = {}
    for key, m in models.items():
        caps = m.get("capabilities", [])
        if "rerank" in caps:
            continue
        providers[key] = {
            "id": key,
            "name": m.get("name", key),
            "model": m.get("model", ""),
            "capabilities": caps,
            "context_window": m.get("context_window", 128000),
            "priority": m.get("priority", 5),
            "cost_tier": m.get("cost_tier", "medium"),
            "status": "available",
        }
    return jsonify({
        "providers": providers,
        "token_settings": CONFIG.get("token_settings", {}),
        "has_token": bool(API_TOKEN),
    })


@app.route("/api/config/provider", methods=["POST"])
def set_provider():
    """Save provider settings to localStorage (handled client-side)."""
    return jsonify({"ok": True})


# ============================================
# Routes: Chat
# ============================================
@app.route("/api/chat", methods=["POST"])
def api_chat():
    chat_stop_flag["stop"] = False
    data = request.json
    messages = data.get("messages", [])
    model_key = data.get("model", "auto")
    max_tokens = data.get("max_tokens", 4096)
    temperature = data.get("temperature", 0.7)
    extensions = data.get("extensions", [])
    stream = data.get("stream", True)

    # Auto model selection
    if model_key == "auto":
        tiers = CONFIG.get("api_model_tiers", {})
        model_key = (tiers.get("large", [None]) or ["qwen3.5-397b"])[0]

    # Build system prompt with active extensions
    system_parts = ["You are Goose, an autonomous AI agent. You help users with coding, analysis, and automation tasks."]
    if extensions:
        ext_descriptions = []
        for ext_id in extensions:
            ext = load_extension(ext_id)
            if ext:
                ext_descriptions.append(f"- {ext.get('name', ext_id)}: {ext.get('description', '')}")
        if ext_descriptions:
            system_parts.append("\nActive extensions:\n" + "\n".join(ext_descriptions))

    system_msg = {"role": "system", "content": "\n".join(system_parts)}
    full_messages = [system_msg] + messages

    if stream:
        def generate():
            resp = call_llm(model_key, full_messages, max_tokens=max_tokens, stream=True, temperature=temperature)
            if isinstance(resp, dict) and "error" in resp:
                yield f"data: {json.dumps({'error': resp['error']})}\n\n"
                return

            buffer = ""
            for line in resp.iter_lines(decode_unicode=True):
                if chat_stop_flag["stop"]:
                    yield f"data: {json.dumps({'done': True, 'stopped': True})}\n\n"
                    return
                if not line:
                    continue
                if line.startswith("data: "):
                    chunk_str = line[6:]
                    if chunk_str.strip() == "[DONE]":
                        yield f"data: {json.dumps({'done': True})}\n\n"
                        return
                    try:
                        chunk = json.loads(chunk_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            buffer += content
                            yield f"data: {json.dumps({'content': content})}\n\n"
                    except json.JSONDecodeError:
                        continue
            yield f"data: {json.dumps({'done': True, 'full_content': buffer})}\n\n"

        return Response(stream_with_context(generate()), mimetype="text/event-stream")
    else:
        result = call_llm(model_key, full_messages, max_tokens=max_tokens, stream=False, temperature=temperature)
        if isinstance(result, dict) and "error" in result:
            return jsonify(result), 500
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        return jsonify({"content": content, "model": model_key})


@app.route("/api/chat/stop", methods=["POST"])
def api_chat_stop():
    chat_stop_flag["stop"] = True
    return jsonify({"stopped": True})


# ============================================
# Routes: Sessions
# ============================================
@app.route("/api/sessions", methods=["GET"])
def list_sessions():
    sessions = []
    for f in sorted(glob.glob(os.path.join(SESSIONS_DIR, "*.json")), key=os.path.getmtime, reverse=True):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                s = json.load(fh)
                sessions.append({
                    "id": s.get("id"),
                    "name": s.get("name", "Untitled"),
                    "created": s.get("created"),
                    "updated": s.get("updated"),
                    "message_count": len(s.get("messages", [])),
                    "model": s.get("model", "auto"),
                })
        except Exception:
            continue
    return jsonify(sessions)


@app.route("/api/sessions", methods=["POST"])
def create_session():
    sid = str(uuid.uuid4())[:8]
    session = {
        "id": sid,
        "name": request.json.get("name", f"Session {sid[:4]}"),
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
        "messages": [],
        "model": request.json.get("model", "auto"),
        "extensions": request.json.get("extensions", []),
    }
    with open(os.path.join(SESSIONS_DIR, f"{sid}.json"), "w", encoding="utf-8") as f:
        json.dump(session, f, ensure_ascii=False, indent=2)
    return jsonify(session)


@app.route("/api/sessions/<sid>", methods=["GET"])
def get_session(sid):
    path = os.path.join(SESSIONS_DIR, f"{sid}.json")
    if not os.path.exists(path):
        return jsonify({"error": "Session not found"}), 404
    with open(path, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.route("/api/sessions/<sid>", methods=["PUT"])
def update_session(sid):
    path = os.path.join(SESSIONS_DIR, f"{sid}.json")
    if not os.path.exists(path):
        return jsonify({"error": "Session not found"}), 404
    with open(path, "r", encoding="utf-8") as f:
        session = json.load(f)
    data = request.json
    if "name" in data:
        session["name"] = data["name"]
    if "messages" in data:
        session["messages"] = data["messages"]
    if "model" in data:
        session["model"] = data["model"]
    if "extensions" in data:
        session["extensions"] = data["extensions"]
    session["updated"] = datetime.now().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(session, f, ensure_ascii=False, indent=2)
    return jsonify(session)


@app.route("/api/sessions/<sid>", methods=["DELETE"])
def delete_session(sid):
    path = os.path.join(SESSIONS_DIR, f"{sid}.json")
    if os.path.exists(path):
        os.remove(path)
    return jsonify({"deleted": True})


@app.route("/api/sessions/<sid>/export", methods=["GET"])
def export_session(sid):
    path = os.path.join(SESSIONS_DIR, f"{sid}.json")
    if not os.path.exists(path):
        return jsonify({"error": "Session not found"}), 404
    with open(path, "r", encoding="utf-8") as f:
        session = json.load(f)
    return jsonify(session)


# ============================================
# Routes: Extensions (MCP-style)
# ============================================
def load_extension(ext_id):
    path = os.path.join(EXTENSIONS_DIR, f"{ext_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


@app.route("/api/extensions", methods=["GET"])
def list_extensions():
    extensions = []
    for f in sorted(glob.glob(os.path.join(EXTENSIONS_DIR, "*.json"))):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                ext = json.load(fh)
                extensions.append(ext)
        except Exception:
            continue
    return jsonify(extensions)


@app.route("/api/extensions/<ext_id>", methods=["GET"])
def get_extension(ext_id):
    ext = load_extension(ext_id)
    if ext:
        return jsonify(ext)
    return jsonify({"error": "Extension not found"}), 404


@app.route("/api/extensions/<ext_id>/toggle", methods=["POST"])
def toggle_extension(ext_id):
    ext = load_extension(ext_id)
    if not ext:
        return jsonify({"error": "Extension not found"}), 404
    ext["enabled"] = not ext.get("enabled", False)
    path = os.path.join(EXTENSIONS_DIR, f"{ext_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ext, f, ensure_ascii=False, indent=2)
    return jsonify(ext)


# ============================================
# Routes: Recipes
# ============================================
@app.route("/api/recipes", methods=["GET"])
def list_recipes():
    recipes = []
    for f in sorted(glob.glob(os.path.join(RECIPES_DIR, "*.yaml")) + glob.glob(os.path.join(RECIPES_DIR, "*.yml"))):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                recipe = yaml.safe_load(fh)
                recipe["_file"] = os.path.basename(f)
                recipes.append(recipe)
        except Exception:
            continue
    return jsonify(recipes)


@app.route("/api/recipes/<recipe_id>/run", methods=["POST"])
def run_recipe(recipe_id):
    """Execute a recipe with given parameters."""
    # Find recipe file
    recipe_file = None
    for ext in [".yaml", ".yml"]:
        path = os.path.join(RECIPES_DIR, f"{recipe_id}{ext}")
        if os.path.exists(path):
            recipe_file = path
            break

    if not recipe_file:
        return jsonify({"error": "Recipe not found"}), 404

    with open(recipe_file, "r", encoding="utf-8") as f:
        recipe = yaml.safe_load(f)

    params = request.json.get("params", {})
    instructions = recipe.get("instructions", "")

    # Substitute parameters
    for key, val in params.items():
        instructions = instructions.replace(f"{{{{{key}}}}}", str(val))

    messages = [{"role": "user", "content": instructions}]
    model_key = recipe.get("model", "auto")
    if model_key == "auto":
        tiers = CONFIG.get("api_model_tiers", {})
        model_key = (tiers.get("large", []) or ["qwen3.5-397b"])[0]

    result = call_llm(model_key, messages, max_tokens=recipe.get("max_tokens", 4096), stream=False)
    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 500

    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    return jsonify({"content": content, "recipe": recipe.get("name", recipe_id)})


# ============================================
# Routes: Subagents
# ============================================
@app.route("/api/subagents/spawn", methods=["POST"])
def spawn_subagent():
    data = request.json
    agent_id = str(uuid.uuid4())[:8]
    task = data.get("task", "")
    model_key = data.get("model", "auto")

    if model_key == "auto":
        tiers = CONFIG.get("api_model_tiers", {})
        model_key = (tiers.get("medium", []) or ["glm-5"])[0]

    active_subagents[agent_id] = {
        "id": agent_id,
        "task": task,
        "status": "running",
        "model": model_key,
        "created": datetime.now().isoformat(),
        "result": None,
    }

    def run_agent():
        messages = [{"role": "user", "content": task}]
        result = call_llm(model_key, messages, max_tokens=4096, stream=False)
        if isinstance(result, dict) and "error" in result:
            active_subagents[agent_id]["status"] = "error"
            active_subagents[agent_id]["result"] = result["error"]
        else:
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            active_subagents[agent_id]["status"] = "completed"
            active_subagents[agent_id]["result"] = content

    threading.Thread(target=run_agent, daemon=True).start()
    return jsonify(active_subagents[agent_id])


@app.route("/api/subagents", methods=["GET"])
def list_subagents():
    return jsonify(list(active_subagents.values()))


@app.route("/api/subagents/<agent_id>", methods=["GET"])
def get_subagent(agent_id):
    if agent_id in active_subagents:
        return jsonify(active_subagents[agent_id])
    return jsonify({"error": "Subagent not found"}), 404


# ============================================
# Routes: File Upload
# ============================================
@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400
    safe_name = f"{uuid.uuid4().hex[:8]}_{f.filename}"
    save_path = os.path.join(UPLOADS_DIR, safe_name)
    f.save(save_path)
    size = os.path.getsize(save_path)

    # Read preview for text files
    preview = ""
    try:
        with open(save_path, "r", encoding="utf-8") as fh:
            preview = fh.read(2000)
    except Exception:
        preview = "(binary file)"

    return jsonify({
        "filename": f.filename,
        "saved_as": safe_name,
        "size": size,
        "preview": preview[:500],
    })


@app.route("/api/uploads", methods=["GET"])
def list_uploads():
    files = []
    for f in os.listdir(UPLOADS_DIR):
        path = os.path.join(UPLOADS_DIR, f)
        if os.path.isfile(path):
            files.append({"name": f, "size": os.path.getsize(path)})
    return jsonify(files)


# ============================================
# Routes: Settings
# ============================================
@app.route("/api/settings", methods=["GET"])
def get_settings():
    settings_path = os.path.join(BASE_DIR, "settings.json")
    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({
        "theme": "dark",
        "default_model": "auto",
        "max_tokens": 4096,
        "temperature": 0.7,
        "shortcuts": True,
    })


@app.route("/api/settings", methods=["POST"])
def save_settings():
    settings_path = os.path.join(BASE_DIR, "settings.json")
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(request.json, f, ensure_ascii=False, indent=2)
    return jsonify({"saved": True})


# ============================================
# Main
# ============================================
if __name__ == "__main__":
    print(f"""
    ╔══════════════════════════════════════╗
    ║         Goose App v1.0               ║
    ║   http://localhost:10010             ║
    ╚══════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=10010, debug=True)
