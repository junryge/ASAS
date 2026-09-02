"""
demos_v1/routes_openai.py — 이미 떠 있는 GGUF 를 OpenAI 호환으로 내보낸다.

★왜 서버를 따로 안 띄우나
  집은 GPU 한 장이다. 앱마다 llama-cpp 로 모델을 올리면 같은 모델이 VRAM 에
  두 벌 세 벌 올라가서 결국 아무것도 안 뜬다. demos_v1 이 부팅할 때 이미
  한 벌 올려 두므로(app.py), 그걸 **문만 열어** 나눠 쓴다.

★왜 하필 OpenAI 모양인가
  아바타(avatar_2d)는 원래 OpenAI 호환 게이트웨이만 말할 줄 안다.
  주소만 여기로 돌리면 코드를 안 고치고 그대로 붙는다.
  나중에 다른 도구가 붙을 때도 같다 — 표준 모양이 제일 싸다.

  GET  /v1/models
  POST /v1/chat/completions        (stream=true 면 SSE)

★한 번에 하나만 생성한다
  llama.cpp 모델 객체는 스레드 안전하지 않다. 두 요청이 동시에 들어오면
  토큰이 섞이거나 프로세스가 죽는다 — 락으로 줄을 세운다.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid

from flask import Response, jsonify, request

import demos_v1.utils as _utils_mod
from demos_v1.models import ENV_CONFIG

# 생성은 한 번에 하나. (모델 로딩까지 같은 락으로 감싼다)
_GEN_LOCK = threading.Lock()


# ── 모델 목록 ────────────────────────────────────────────────────────────
def _gguf_envs():
    """ENV_CONFIG 에서 gguf-N 만. app.py 가 부팅 때 넣어 둔 것들이다."""
    return {k: v for k, v in ENV_CONFIG.items()
            if str(k).startswith("gguf-") and v.get("_gguf_path")}


def _resolve(model_id):
    """요청의 model 을 (env_id, gguf 경로) 로 푼다.

    ★세 가지 이름을 다 받는다 — 부르는 쪽마다 아는 이름이 다르다.
        env_id      gguf-0
        모델 이름   Qwen3-14B-Q4_K_M
        파일 이름   Qwen3-14B-Q4_K_M.gguf
      빈 값이면 **지금 올라와 있는 모델**을 쓴다. 그게 제일 안 아프다.
    """
    envs = _gguf_envs()
    if not envs:
        return None, None
    want = str(model_id or "").strip()
    if not want:
        cur = getattr(_utils_mod, "gguf_loaded_path", "") or ""
        for k, v in envs.items():
            if v["_gguf_path"] == cur:
                return k, cur
        k = sorted(envs)[0]
        return k, envs[k]["_gguf_path"]
    low = want.lower()
    for k, v in envs.items():
        base = os.path.basename(v["_gguf_path"])
        if low in (str(k).lower(), str(v.get("model", "")).lower(),
                   base.lower(), base.lower().replace(".gguf", "")):
            return k, v["_gguf_path"]
    return None, None


# ── 생성 ────────────────────────────────────────────────────────────────
def _ensure_loaded(path):
    """필요하면 갈아 끼운다. 이미 그 모델이면 load_gguf_model 이 알아서 넘긴다."""
    from demos_v1.gguf import load_gguf_model
    if getattr(_utils_mod, "gguf_loaded_path", None) == path \
            and getattr(_utils_mod, "gguf_model", None) is not None:
        return True
    return bool(load_gguf_model(path))


def _kwargs(body):
    """OpenAI 파라미터 중 llama-cpp 가 아는 것만 골라 넘긴다.

    ★response_format 은 **살려서 넘긴다.** 아바타는 답을 통째로 JSON 으로
      받는 구조라, 이게 없으면 매번 본문에서 JSON 을 긁어내야 한다.
      llama-cpp 는 json_object 를 문법(grammar)으로 강제해 준다.
    """
    out = {"temperature": float(body.get("temperature", 0.7))}
    mt = body.get("max_tokens")
    out["max_tokens"] = int(mt) if mt else 4096
    for k in ("top_p", "top_k", "presence_penalty", "frequency_penalty", "seed"):
        if body.get(k) is not None:
            out[k] = body[k]
    stop = body.get("stop")
    if stop:
        out["stop"] = stop if isinstance(stop, list) else [stop]
    rf = body.get("response_format")
    if isinstance(rf, dict) and rf.get("type"):
        out["response_format"] = rf
    return out


def _rf_ladder(rf):
    """response_format 을 **약한 쪽으로 한 계단씩** 낮춘 목록.

    ★아바타는 json_schema 로 보낸다(감정·모션 enum 까지 박은 스키마).
      그런데 llama-cpp 빌드마다 아는 모양이 다르다 —
          json_schema                          최신만 안다
          {"type":"json_object","schema":{…}}  llama-cpp 가 오래 쓰던 모양
          {"type":"json_object"}               JSON 이라는 것만 강제
          (없음)                               자유 생성
      바로 버리면 JSON 보장이 통째로 날아가서, 답을 본문에서 긁어내야 한다.
      한 계단씩 낮추면 그 빌드가 아는 가장 센 것에서 멈춘다.
    """
    out = [rf]
    if isinstance(rf, dict) and rf.get("type") == "json_schema":
        inner = (rf.get("json_schema") or {}).get("schema")
        if inner:
            out.append({"type": "json_object", "schema": inner})
    if not (isinstance(rf, dict) and rf.get("type") == "json_object"
            and "schema" not in rf):
        out.append({"type": "json_object"})
    out.append(None)                       # 마지막엔 포기
    return out


def _call(messages, kw):
    """create_chat_completion. response_format 은 낮춰 가며 다시 시도한다."""
    m = _utils_mod.gguf_model
    rf = kw.get("response_format")
    if rf is None:
        return m.create_chat_completion(messages=messages, **kw)
    base = {k: v for k, v in kw.items() if k != "response_format"}
    last = None
    for cand in _rf_ladder(rf):
        try:
            if cand is None:
                return m.create_chat_completion(messages=messages, **base)
            return m.create_chat_completion(messages=messages,
                                            response_format=cand, **base)
        except Exception as e:             # noqa: BLE001, PERF203
            last = e
    raise last


def register_openai_routes(app):
    """app.py 의 create_app() 에서 부른다."""

    @app.route("/v1/models", methods=["GET"])
    def openai_models():
        envs = _gguf_envs()
        cur = getattr(_utils_mod, "gguf_loaded_path", "") or ""
        now = int(time.time())
        data = []
        for k in sorted(envs):
            v = envs[k]
            data.append({
                "id": v.get("model") or k,
                "object": "model",
                "created": now,
                "owned_by": "local-gguf",
                # 표준 밖이지만 붙는 쪽에 도움이 된다 — 무시해도 그만이다
                "env_id": k,
                "loaded": v["_gguf_path"] == cur,
                "size_gb": v.get("_size_gb"),
            })
        return jsonify({"object": "list", "data": data})

    @app.route("/v1/chat/completions", methods=["POST"])
    def openai_chat():
        body = request.get_json(silent=True) or {}
        messages = body.get("messages") or []
        if not isinstance(messages, list) or not messages:
            return jsonify({"error": {"message": "messages 가 비어 있습니다",
                                      "type": "invalid_request_error"}}), 400

        env_id, path = _resolve(body.get("model"))
        if not path:
            return jsonify({"error": {
                "message": "GGUF 모델이 없습니다. app.py 옆(또는 models/)에 "
                           ".gguf 파일을 두고 다시 띄우세요.",
                "type": "model_not_found"}}), 404

        kw = _kwargs(body)
        name = ENV_CONFIG.get(env_id, {}).get("model") or env_id
        cid = "chatcmpl-" + uuid.uuid4().hex[:24]
        created = int(time.time())

        # ── 스트리밍 ────────────────────────────────────────────────
        if body.get("stream"):
            def gen():
                # ★락을 제너레이터 **안에서** 잡는다. 밖에서 잡으면 응답이
                #   끝나기 전에 함수가 반환돼 락이 풀린다.
                with _GEN_LOCK:
                    if not _ensure_loaded(path):
                        yield "data: " + json.dumps({"error": {
                            "message": "모델 로드 실패: " + os.path.basename(path)}},
                            ensure_ascii=False) + "\n\n"
                        yield "data: [DONE]\n\n"
                        return
                    try:
                        from demos_v1.gguf import _inject_no_think_for_qwen3 as _nt
                        msgs = _nt(messages, path)
                    except Exception:
                        msgs = messages
                    try:
                        for ch in _call(msgs, dict(kw, stream=True)):
                            d = (ch.get("choices") or [{}])[0].get("delta") or {}
                            txt = d.get("content") or ""
                            if not txt:
                                continue
                            yield "data: " + json.dumps({
                                "id": cid, "object": "chat.completion.chunk",
                                "created": created, "model": name,
                                "choices": [{"index": 0,
                                             "delta": {"content": txt},
                                             "finish_reason": None}],
                            }, ensure_ascii=False) + "\n\n"
                    except Exception as e:                     # noqa: BLE001
                        yield "data: " + json.dumps({"error": {
                            "message": str(e)}}, ensure_ascii=False) + "\n\n"
                    yield "data: " + json.dumps({
                        "id": cid, "object": "chat.completion.chunk",
                        "created": created, "model": name,
                        "choices": [{"index": 0, "delta": {},
                                     "finish_reason": "stop"}],
                    }, ensure_ascii=False) + "\n\n"
                    yield "data: [DONE]\n\n"

            return Response(gen(), mimetype="text/event-stream",
                            headers={"Cache-Control": "no-cache",
                                     "X-Accel-Buffering": "no"})

        # ── 한 번에 ────────────────────────────────────────────────
        with _GEN_LOCK:
            if not _ensure_loaded(path):
                return jsonify({"error": {
                    "message": "모델 로드 실패: " + os.path.basename(path),
                    "type": "server_error"}}), 500
            try:
                from demos_v1.gguf import _inject_no_think_for_qwen3 as _nt
                msgs = _nt(messages, path)
            except Exception:
                msgs = messages
            try:
                out = _call(msgs, kw)
            except Exception as e:                             # noqa: BLE001
                return jsonify({"error": {"message": str(e),
                                          "type": "server_error"}}), 500

        text = ((out.get("choices") or [{}])[0].get("message") or {}).get("content", "")
        usage = out.get("usage") or {}
        return jsonify({
            "id": cid, "object": "chat.completion", "created": created,
            "model": name,
            "choices": [{"index": 0,
                         "message": {"role": "assistant", "content": text},
                         "finish_reason": (out.get("choices") or [{}])[0]
                         .get("finish_reason") or "stop"}],
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        })

    print("  🔌 GGUF OpenAI 호환 라우트 등록 완료 (/v1/models · /v1/chat/completions)")
