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
    """필요하면 갈아 끼운다. 이미 그 모델이면 load_gguf_model 이 알아서 넘긴다.

    ★갈아 끼우는 것은 **공짜가 아니다.** GPU 가 한 장이라 지금 올라온 모델을
      내려야 하는데, 26B 급이면 1분 넘게 걸린다. 그동안 데모스·UIO·코딩
      어시스턴트도 다 멈추고, 그쪽이 다시 쓰려면 또 갈아 끼워야 한다
      (실제로 아바타가 gemma-4-26B 를 고르는 바람에 데모스가 쓰던
       gemma-4-12b 가 내려갔다).
      막지는 않는다 — 사람이 골랐으면 그 모델이 맞다. 다만 **왜 멈췄는지**
      로그에 남긴다. 안 남기면 그냥 먹통으로 보인다.
    """
    from demos_v1.gguf import load_gguf_model
    cur = getattr(_utils_mod, "gguf_loaded_path", None)
    if cur == path and getattr(_utils_mod, "gguf_model", None) is not None:
        return True
    if cur:
        print("  ⚠️  /v1 요청이 모델을 갈아 끼웁니다 — "
              "{} → {}".format(os.path.basename(cur), os.path.basename(path)))
        print("      GPU 한 장이라 지금 것을 내립니다. 로딩 동안 데모스·UIO·"
              "코딩어시스턴트도 같이 멈춥니다.")
        print("      매번 이러면, 붙는 쪽에서 지금 올라온 모델을 고르세요 "
              "(/v1/models 목록의 맨 위가 그것입니다).")
    return bool(load_gguf_model(path))


def _n_ctx():
    """지금 올라온 모델의 컨텍스트 길이. 못 알아내면 0."""
    m = getattr(_utils_mod, "gguf_model", None)
    if m is None:
        return 0
    try:
        v = getattr(m, "n_ctx", None)
        v = v() if callable(v) else v
        return int(v or 0)
    except Exception:                                      # noqa: BLE001
        return 0


def _prompt_tokens(messages):
    """프롬프트가 몇 토큰인지 **재 본다.** 못 재면 글자수로 어림한다.

    ★한국어는 글자당 대략 1.5~2 토큰이다. 못 재는 상황에서 1 로 잡으면
      한참 모자라게 세서, 결국 답이 잘린다. 넉넉히 2 로 잡는다.
    """
    m = getattr(_utils_mod, "gguf_model", None)
    txt = "\n".join(str((x or {}).get("content") or "") for x in messages)
    try:
        return len(m.tokenize(txt.encode("utf-8"), add_bos=True))
    except Exception:                                      # noqa: BLE001
        return int(len(txt) * 2)


def _fit_max_tokens(messages, want):
    """컨텍스트에 **실제로 들어가는** 만큼으로 줄인다.

    ★이걸 안 하면 답이 문장 한복판에서 끊긴다. 위키를 읽어 오면 프롬프트가
      확 커지는데(페이지 3쪽 × 4000자), max_tokens 를 4096 으로 박아 두면
      프롬프트 + 4096 이 n_ctx 를 넘어서 llama.cpp 가 생성을 잘라 버린다.
      화면에는 그냥 "말을 다 안 하는" 것으로 보인다 — 실제로 그렇게 나왔다.
    반환 (max_tokens, 모자란 정도). 모자라면 두 번째가 양수다.
    """
    n_ctx = _n_ctx()
    if n_ctx <= 0:
        return want, 0
    used = _prompt_tokens(messages)
    room = n_ctx - used - 256          # 여유 (특수토큰·템플릿)
    if room < 256:
        return 256, 256 - room
    return max(256, min(want, room)), 0


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
        # ★지금 올라와 있는 것을 **맨 앞**에 둔다. 붙는 쪽(아바타 run.py)은
        #   목록의 첫 번째를 기본값으로 고른다 — 그게 이미 VRAM 에 있는
        #   모델이면 갈아 끼울 일이 없다. 이름순으로 두면 엉뚱한 것이
        #   1번이 되어, 고르는 순간 데모스가 쓰던 모델이 내려간다.
        for k in sorted(envs, key=lambda k: (envs[k]["_gguf_path"] != cur, k)):
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
                fin = "stop"
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
                    kw["max_tokens"], short = _fit_max_tokens(msgs, kw["max_tokens"])
                    if short:
                        yield "data: " + json.dumps({"error": {
                            "message": "프롬프트가 컨텍스트보다 {} 토큰 큽니다 "
                                       "(n_ctx={}).".format(short, _n_ctx())},
                        }, ensure_ascii=False) + "\n\n"
                        yield "data: [DONE]\n\n"
                        return
                    try:
                        for ch in _call(msgs, dict(kw, stream=True)):
                            c0 = (ch.get("choices") or [{}])[0]
                            if c0.get("finish_reason"):
                                fin = c0["finish_reason"]
                            d = c0.get("delta") or {}
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
                    # ★잘렸으면 잘렸다고 말한다. "stop" 으로 박아 두면
                    #   토큰 한도로 끊긴 답이 정상 종료처럼 보인다 —
                    #   말을 다 안 하는데 아무도 이유를 모른다.
                    yield "data: " + json.dumps({
                        "id": cid, "object": "chat.completion.chunk",
                        "created": created, "model": name,
                        "choices": [{"index": 0, "delta": {},
                                     "finish_reason": fin}],
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
            kw["max_tokens"], short = _fit_max_tokens(msgs, kw["max_tokens"])
            if short:
                # ★조용히 자르지 않는다. 프롬프트가 컨텍스트를 넘으면 무엇을
                #   줄여야 하는지 사람이 알아야 한다.
                return jsonify({"error": {
                    "message": "프롬프트가 컨텍스트보다 {} 토큰 큽니다 "
                               "(n_ctx={}). 참고 자료를 줄이거나 n_ctx 를 "
                               "키우세요.".format(short, _n_ctx()),
                    "type": "context_length_exceeded"}}), 400
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
