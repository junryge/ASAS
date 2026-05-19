"""
gguf.py - GGUF 단일 모델 채팅 헬퍼 (집용).

설계 원칙:
- 집용 = 단일 GGUF 모델, 병렬 없음 (멀티풀 로직 제거됨)
- API 경로(backend/api_client.py)와 완전 독립 — 이 파일은 backend.api_client 를 import 하지 않음
- 모델 로드/언로드는 foundry_server.py 가 담당 (gguf_model, gguf_loaded_path 전역)
- 본 파일은 "이미 로드된 모델을 사용한 채팅" 만 책임
"""
import os
import threading

# foundry_server 의 전역 단일 인스턴스를 참조. 순환 import 피하려고 함수 안에서 import.
_chat_lock = threading.Lock()


def _get_loaded():
    """foundry_server 모듈에서 현재 로드된 단일 GGUF 인스턴스를 가져옴."""
    import foundry_server as fs
    return fs.gguf_model, fs.gguf_loaded_path


def _inject_no_think_for_qwen3(messages, model_path):
    """Qwen3 모델 사용 시 reasoning 비활성화 — '/no_think' 키워드 자동 주입.

    Qwen3 공식 chat template: 시스템/user 메시지에 '/no_think' 있으면 사고 토큰 생성 X.
    → 토큰/시간 낭비 차단 + 영문 사고 노출 방지.
    예외: think_mode 토글 ON (시스템 프롬프트에 명시적 사고 지시) 시 사고 허용.
    """
    if not model_path or "qwen3" not in os.path.basename(model_path).lower():
        return messages
    if not messages:
        return messages
    for m in messages:
        if m.get("role") == "system":
            content = m.get("content", "") if isinstance(m.get("content"), str) else ""
            if "<think>...</think> 태그 안에서" in content or "사고한 후 답변" in content:
                return messages
            break
    new_msgs = list(messages)
    for i, m in enumerate(new_msgs):
        if m.get("role") == "system":
            content = m.get("content", "")
            if isinstance(content, str) and "/no_think" not in content:
                new_msgs[i] = {**m, "content": content + "\n\n/no_think"}
            return new_msgs
    for i in range(len(new_msgs) - 1, -1, -1):
        if new_msgs[i].get("role") == "user":
            content = new_msgs[i].get("content", "")
            if isinstance(content, str) and "/no_think" not in content:
                new_msgs[i] = {**new_msgs[i], "content": content + "\n\n/no_think"}
            break
    return new_msgs


def gguf_chat(messages, temperature=0.5, max_tokens=4096, stop_flag=None):
    """로드된 단일 GGUF 모델로 채팅.

    Returns: (text, error) 튜플. 정상이면 (text, None), 실패 시 (None, msg).
    GGUF 경로는 본질적으로 직렬이라 _chat_lock 으로 동시 호출 방지.
    """
    model, model_path = _get_loaded()
    if model is None:
        return None, "GGUF 모델이 로드되지 않았습니다. /api/gguf/load 먼저 호출하세요."

    messages = _inject_no_think_for_qwen3(messages, model_path or "")

    with _chat_lock:
        try:
            if stop_flag is not None:
                chunks = []
                for chunk in model.create_chat_completion(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                ):
                    if stop_flag.get("stop", False):
                        partial = "".join(chunks)
                        return (partial + "\n\n⏹️ (응답이 중단되었습니다)") if partial else None, None
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        chunks.append(content)
                return "".join(chunks), None
            else:
                resp = model.create_chat_completion(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                if resp and "choices" in resp and len(resp["choices"]) > 0:
                    return resp["choices"][0].get("message", {}).get("content") or "", None
                return None, f"예상치 못한 응답: {resp}"
        except Exception as e:
            return None, f"GGUF 추론 오류: {e}"
