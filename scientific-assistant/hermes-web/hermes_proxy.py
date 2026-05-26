"""
hermes_proxy.py — Hermes Web 용 LLM 프록시 (HOME GGUF + OFFICE vLLM)

- 127.0.0.1:8765 listen
- 환경 자동 감지:
  * HOME  (F:\M14_Q\scientific-assistant 존재) → 로컬 GGUF 추론 (gguf_engine)
  * OFFICE (그 외)                              → common.llm.skhynix.com 으로 forward
- TOKEN.TXT 자동 로드 (OFFICE 에서 Auth 헤더 주입)
- tools / tool_choice / functions 전부 통과 (Agent 동작)
- 스트리밍 / 비스트리밍 둘 다 지원
- 환경변수 의존 X
"""
import os
import sys
import json
import time
from flask import Flask, request, Response, jsonify, stream_with_context
import requests

# ─── 환경 자동 감지 ────────────────────────────────────────────────────────
HOME_BASE = r"F:\M14_Q\scientific-assistant"
OFFICE_BASE = r"C:\연구과제\CODE\데모스_분석툴\scientific-assistant"

if os.path.isdir(HOME_BASE):
    ENV_MODE = "HOME"
    SCIENTIFIC_BASE = HOME_BASE
elif os.path.isdir(OFFICE_BASE):
    ENV_MODE = "OFFICE"
    SCIENTIFIC_BASE = OFFICE_BASE
else:
    ENV_MODE = "UNKNOWN"
    SCIENTIFIC_BASE = os.path.dirname(os.path.abspath(__file__))

# ─── 고정 설정 ─────────────────────────────────────────────────────────────
UPSTREAM = "http://common.llm.skhynix.com"  # OFFICE 용
LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 8765
TIMEOUT_S = 600
VERIFY_SSL = False

# TOKEN.TXT 자동 로드
_TOKEN = ""
for path in (
    os.path.join(SCIENTIFIC_BASE, "TOKEN.TXT"),
    r"C:\연구과제\CODE\데모스_분석툴\scientific-assistant\TOKEN.TXT",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "TOKEN.TXT"),
):
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                _TOKEN = f.read().strip()
            print(f"[PROXY] TOKEN.TXT 로드: {path}  (len={len(_TOKEN)})")
            break
        except Exception as e:
            print(f"[PROXY] ! TOKEN.TXT 읽기 실패 ({path}): {e}", file=sys.stderr)

# HOME 모드: GGUF 엔진 lazy import (없으면 OFFICE 로 fallback)
_GGUF_AVAILABLE = False
if ENV_MODE == "HOME":
    try:
        import gguf_engine
        _GGUF_AVAILABLE = True
        print(f"[PROXY] gguf_engine 로드 성공")
    except Exception as e:
        print(f"[PROXY] ! gguf_engine import 실패 ({e}) — OFFICE 처럼 forward 만 함")

app = Flask(__name__)


def _build_headers():
    """클라이언트 헤더 복사 + TOKEN.TXT Auth 강제."""
    h = {}
    for k, v in request.headers.items():
        if k.lower() in ("host", "content-length", "connection"):
            continue
        h[k] = v
    if _TOKEN:
        h["Authorization"] = f"Bearer {_TOKEN}"
    return h


def _mask_auth(h):
    a = h.get("Authorization", "(none)")
    if a.startswith("Bearer "):
        tok = a[7:]
        return f"Bearer {tok[:6]}...{tok[-4:]} (len={len(tok)})"
    return a


# ─── HOME: GGUF 자체 추론 ─────────────────────────────────────────────────
def _gguf_ensure_loaded(model_id_hint=None):
    """원하는 모델 GGUF 가 로드돼있나 확인, 안 됐으면 자동 로드.
    model_id_hint 가 있으면 그 id 와 일치하는 .gguf 우선."""
    if not _GGUF_AVAILABLE:
        return None, "GGUF 사용 불가"

    cur = gguf_engine.get_loaded_model() or {}
    # 이미 원하는 모델 로드돼있으면 그대로
    if cur.get("loaded"):
        if not model_id_hint or model_id_hint == cur.get("id") or model_id_hint == cur.get("name"):
            return cur, None

    # 디스크에서 .gguf 찾기
    files = gguf_engine.find_gguf_files(SCIENTIFIC_BASE)
    if not files:
        return None, f"{SCIENTIFIC_BASE} 에서 .gguf 못 찾음"

    target = files[0]["path"]
    # hint 와 매치되는 파일 우선
    if model_id_hint:
        for f in files:
            if f.get("id") == model_id_hint or f.get("name") == model_id_hint:
                target = f["path"]
                break

    ok, msg = gguf_engine.load_model(target)
    if not ok:
        return None, msg
    print(f"[PROXY/HOME] GGUF 로드 완료: {os.path.basename(target)}")
    return gguf_engine.get_loaded_model(), None


def _gguf_chat(body):
    """HOME 의 /v1/chat/completions 처리."""
    cur, err = _gguf_ensure_loaded(body.get("model"))
    if err:
        return jsonify({"error": err}), 503
    messages = body.get("messages") or []
    temperature = body.get("temperature", 0.5)
    max_tokens = body.get("max_tokens", 4096)
    stream = bool(body.get("stream", False))

    if stream:
        gen, err = gguf_engine.chat_completion(
            messages, temperature=temperature,
            max_tokens=max_tokens, stream=True,
        )
        if err:
            return jsonify({"error": err}), 500

        def _sse():
            for chunk in gen:
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        return Response(stream_with_context(_sse()), mimetype="text/event-stream")
    else:
        resp, err = gguf_engine.chat_completion(
            messages, temperature=temperature,
            max_tokens=max_tokens, stream=False,
        )
        if err:
            return jsonify({"error": err}), 500
        return jsonify(resp)


# ─── OFFICE: 그대로 forward ──────────────────────────────────────────────
def _forward(method, subpath, body, is_stream):
    url = f"{UPSTREAM}/v1/{subpath}"
    headers = _build_headers()
    try:
        r = requests.request(
            method, url,
            headers=headers,
            json=body if body else None,
            stream=is_stream,
            timeout=TIMEOUT_S,
            verify=VERIFY_SSL,
        )
    except Exception as e:
        print(f"[PROXY] ✗ upstream 호출 실패: {e}")
        return jsonify({"error": str(e)}), 502

    if r.status_code >= 400:
        try:
            print(f"[PROXY] ✗ upstream {r.status_code}: {r.text[:300]}")
        except Exception:
            pass

    if is_stream:
        def gen():
            for chunk in r.iter_content(chunk_size=None):
                if chunk:
                    yield chunk
        excluded = {"content-encoding", "transfer-encoding", "content-length", "connection"}
        resp_headers = [(k, v) for k, v in r.headers.items() if k.lower() not in excluded]
        return Response(stream_with_context(gen()), status=r.status_code, headers=resp_headers)
    else:
        return Response(
            r.content,
            status=r.status_code,
            content_type=r.headers.get("Content-Type", "application/json"),
        )


# ─── 라우팅 ────────────────────────────────────────────────────────────────
@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    body = request.get_json(silent=True) or {}
    is_stream = bool(body.get("stream", False))
    model = body.get("model", "?")
    headers_auth = _mask_auth(_build_headers())
    print(f"[PROXY/{ENV_MODE}] POST chat/completions  model={model!r}  stream={is_stream}  auth={headers_auth}")

    if ENV_MODE == "HOME" and _GGUF_AVAILABLE:
        return _gguf_chat(body)
    return _forward("POST", "chat/completions", body, is_stream)


@app.route("/v1/models", methods=["GET"])
def models():
    if ENV_MODE == "HOME" and _GGUF_AVAILABLE:
        files = gguf_engine.find_gguf_files(SCIENTIFIC_BASE)
        return jsonify({
            "object": "list",
            "data": [{"id": f["id"], "object": "model", "owned_by": "local"} for f in files],
        })
    return _forward("GET", "models", None, False)


@app.route("/v1/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE"])
def forward_anything(subpath):
    body = request.get_json(silent=True) or {}
    is_stream = bool(body.get("stream", False))
    return _forward(request.method, subpath, body, is_stream)


@app.route("/health")
def health():
    return jsonify({
        "ok": True,
        "env_mode": ENV_MODE,
        "gguf_available": _GGUF_AVAILABLE,
        "scientific_base": SCIENTIFIC_BASE,
        "upstream": UPSTREAM if ENV_MODE != "HOME" else None,
        "token_loaded": bool(_TOKEN),
    })


if __name__ == "__main__":
    print("=" * 60)
    print(f"  Hermes Proxy")
    print(f"  Mode:      {ENV_MODE}")
    print(f"  Base:      {SCIENTIFIC_BASE}")
    if ENV_MODE == "HOME" and _GGUF_AVAILABLE:
        files = gguf_engine.find_gguf_files(SCIENTIFIC_BASE)
        print(f"  GGUF 파일: {len(files)}개")
        for f in files[:5]:
            print(f"    - {f['name']}")
    else:
        print(f"  Upstream:  {UPSTREAM}")
        print(f"  Token:     {'로드됨 (' + str(len(_TOKEN)) + '자)' if _TOKEN else '없음'}")
    print(f"  Listen:    http://{LISTEN_HOST}:{LISTEN_PORT}")
    print(f"  통과 필드: tools, tool_choice, functions 전부 forward")
    print("=" * 60)
    app.run(host=LISTEN_HOST, port=LISTEN_PORT, debug=False, threaded=True)
