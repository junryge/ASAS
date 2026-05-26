"""
hermes-web/gguf_engine.py — GGUF 추론 엔진 (llama-cpp-python 단순 래퍼)

- F:\M14_Q\scientific-assistant\ 주변에서 *.gguf 자동 탐색
- 한 번에 하나의 GGUF 모델만 로드 (메모리 절약)
- Qwen3 계열은 /no_think 자동 주입
- 스트리밍/일반 채팅 둘 다 지원
"""
import os
import glob
import threading

# llama-cpp-python 은 무거운 import 라 lazy
_LLAMA_CLS = None


def _get_llama_cls():
    global _LLAMA_CLS
    if _LLAMA_CLS is not None:
        return _LLAMA_CLS
    from llama_cpp import Llama
    _LLAMA_CLS = Llama
    return _LLAMA_CLS


# ─────────────────────────────────────────────────────────────────────────────
# 전역 상태 (단일 모델)
# ─────────────────────────────────────────────────────────────────────────────
_model = None
_model_path = None
_model_lock = threading.Lock()


def find_gguf_files(base_dir):
    """base_dir 와 그 하위 models/, model/ 에서 *.gguf 검색.
    크기 큰 순서대로 정렬 (demos 와 동일) → gguf-N 인덱스 일관성."""
    patterns = [
        os.path.join(base_dir, "*.gguf"),
        os.path.join(base_dir, "models", "*.gguf"),
        os.path.join(base_dir, "model", "*.gguf"),
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    files = [f for f in files if "mmproj" not in os.path.basename(f).lower()]
    result = [
        {
            "path": f,
            "name": os.path.basename(f),
            "id": os.path.splitext(os.path.basename(f))[0],
            "size_gb": round(os.path.getsize(f) / 1e9, 1),
        }
        for f in files
    ]
    # 크기 내림차순 (gguf-0 = 가장 큰 모델, demos 와 동일)
    result.sort(key=lambda x: x["size_gb"], reverse=True)
    return result


def load_model(model_path, n_ctx=32768, n_gpu_layers=99, n_batch=2048):
    """모델 로드. 이미 같은 path + 충분한 ctx 면 스킵."""
    global _model, _model_path
    with _model_lock:
        if _model is not None and _model_path == model_path:
            try:
                cur_ctx_attr = getattr(_model, "n_ctx", None)
                cur_ctx = cur_ctx_attr() if callable(cur_ctx_attr) else (cur_ctx_attr or 0)
            except Exception:
                cur_ctx = 0
            if cur_ctx >= n_ctx:
                return True, f"이미 로드됨 ({os.path.basename(model_path)}, ctx={cur_ctx})"

        # 기존 모델 unload
        if _model is not None:
            try:
                del _model
            except Exception:
                pass
            _model = None

        try:
            import gc
            gc.collect()
        except Exception:
            pass

        try:
            Llama = _get_llama_cls()
            print(f"[gguf] 로드 시작: {os.path.basename(model_path)} (n_ctx={n_ctx})")
            _model = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                n_batch=n_batch,
                verbose=False,
            )
            _model_path = model_path
            print(f"[gguf] 로드 완료: {os.path.basename(model_path)}")
            return True, "OK"
        except Exception as e:
            _model = None
            _model_path = None
            return False, f"GGUF 로드 실패: {e}"


def get_loaded_model():
    return {
        "loaded": _model is not None,
        "path": _model_path,
        "name": os.path.basename(_model_path) if _model_path else None,
        "id": (os.path.splitext(os.path.basename(_model_path))[0] if _model_path else None),
    }


def _inject_no_think_for_qwen3(messages, model_path):
    """Qwen3 / Qwen3.5 모델은 reasoning 모드가 기본 → /no_think 시스템 프롬프트 주입."""
    if not model_path:
        return messages
    name = os.path.basename(model_path).lower()
    if "qwen3" not in name and "qwen-3" not in name:
        return messages
    has_no_think = any(
        m.get("role") == "system" and "/no_think" in (m.get("content") or "")
        for m in messages
    )
    if has_no_think:
        return messages
    return [{"role": "system", "content": "/no_think"}] + list(messages)


def chat_completion(messages, temperature=0.5, max_tokens=4096, stream=False, **extra):
    """OpenAI 호환 chat completion. stream=True 면 generator 반환.

    extra 로 tools, tool_choice, top_p, top_k, response_format, seed 등 전달 가능.
    일부 chat_format 이 tools 를 거부하면 자동으로 tools 제거 후 재시도.
    """
    if _model is None:
        return None, "GGUF 모델이 로드되지 않았습니다"

    messages = _inject_no_think_for_qwen3(messages, _model_path)

    call_kwargs = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }
    # OpenAI 호환 추가 필드 패스스루
    for key in ("tools", "tool_choice", "top_p", "top_k", "response_format",
                "seed", "frequency_penalty", "presence_penalty"):
        if key in extra and extra[key] is not None:
            call_kwargs[key] = extra[key]

    has_tools = "tools" in call_kwargs

    def _try_call(kwargs):
        return _model.create_chat_completion(**kwargs)

    try:
        if stream:
            def _gen():
                try:
                    for chunk in _try_call(call_kwargs):
                        yield chunk
                except Exception as e:
                    # tools 거부 시 자동 제거 후 재시도 (chat_format 호환)
                    if has_tools:
                        print(f"[gguf] tools 거부 ({e}) — tools 빼고 재시도")
                        retry = dict(call_kwargs)
                        for k in ("tools", "tool_choice", "response_format"):
                            retry.pop(k, None)
                        for chunk in _try_call(retry):
                            yield chunk
                    else:
                        raise
            return _gen(), None
        else:
            try:
                resp = _try_call(call_kwargs)
            except Exception as e:
                if has_tools:
                    print(f"[gguf] tools 거부 ({e}) — tools 빼고 재시도")
                    retry = dict(call_kwargs)
                    for k in ("tools", "tool_choice", "response_format"):
                        retry.pop(k, None)
                    resp = _try_call(retry)
                else:
                    raise
            return resp, None
    except Exception as e:
        return None, f"GGUF 추론 오류: {e}"
