"""
backend/api_client.py - HCP/Common LLM 동기 호출자.

설계 원칙:
- 회사용. gguf.py 와 완전 독립 (이 파일에서 gguf 또는 foundry_server import 안 함)
- 단일 책임: 모델 id 받아서 텍스트 응답 반환. fallback 체인 자동 시도
- urllib 만 사용 (외부 의존성 추가 없음)
"""
import json
import time
import urllib.request
import urllib.error

from . import config


class ApiError(RuntimeError):
    pass


def _post_json(url, payload, timeout=120):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)


def _extract_text(resp):
    """OpenAI 호환 응답에서 텍스트 추출."""
    try:
        return resp["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


def _call_one(model_id, messages, temperature, max_tokens, timeout):
    entry = config.get_model(model_id)
    if not entry:
        raise ApiError(f"unknown model_id: {model_id}")
    payload = {
        "model": entry["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    resp = _post_json(entry["url"], payload, timeout=timeout)
    text = _extract_text(resp)
    return text, resp


def call_model(
    model_id,
    messages,
    temperature=0.4,
    max_tokens=2048,
    timeout=120,
    use_fallback=True,
):
    """모델 호출. 실패 시 fallback_chain 순차 재시도.

    Returns: (text, used_model_id, attempts)
        attempts = [{"model_id": ..., "ok": bool, "error"?: str, "elapsed": float}]
    Raises: ApiError — 모든 모델 실패 시
    """
    chain = [model_id]
    if use_fallback:
        chain += config.fallback_chain(model_id)

    attempts = []
    last_err = None
    for mid in chain:
        t0 = time.time()
        try:
            text, _resp = _call_one(mid, messages, temperature, max_tokens, timeout)
            attempts.append({"model_id": mid, "ok": True, "elapsed": time.time() - t0})
            if text:
                return text, mid, attempts
            last_err = "empty response"
            attempts[-1].update(ok=False, error=last_err)
        except (urllib.error.URLError, urllib.error.HTTPError, ApiError, OSError, ValueError) as e:
            last_err = f"{type(e).__name__}: {e}"
            attempts.append({"model_id": mid, "ok": False, "error": last_err, "elapsed": time.time() - t0})
            continue

    raise ApiError(f"all models failed (last: {last_err}); attempts={attempts}")


def resolve_default(tier="medium"):
    """model_id 미지정 시 기본값."""
    return config.default_model_for_tier(tier)
