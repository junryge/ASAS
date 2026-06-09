"""
demos_v1/llm_compat.py - 모델별 OpenAI-호환 페이로드 보정 + 전송 래퍼

일부 모델은 표준 chat 포맷의 일부를 지원하지 않아 게이트웨이가 500을 낸다.
대표 케이스: gemma 계열은 채팅 템플릿에 `system` 역할이 없어서, system
메시지를 보내면 서버에서 템플릿 적용이 실패한다(HTTP 500).
→ gemma 로 보낼 때는 system 내용을 첫 user 메시지 앞에 합쳐서 보낸다.

모든 chat 호출을 chat_post() 로 보내면, 전송 직전에 payload["model"] 을 보고
필요한 보정을 자동 적용한다. (그 외 모델은 그대로 통과)
"""
from __future__ import annotations
import requests as _rq


def fold_system_for_gemma(messages, model):
    """gemma 계열이면 system 역할 메시지를 첫 user 메시지 앞으로 합친다.

    - system 역할을 지원하지 않는 모델용 호환 처리.
    - user 메시지가 없으면 system 내용을 user 메시지로 승격.
    - gemma 가 아니면 원본 그대로 반환(무비용).
    """
    if not model or "gemma" not in str(model).lower():
        return messages
    if not isinstance(messages, list):
        return messages

    sys_texts = []
    rest = []
    had_system = False
    for m in messages:
        if isinstance(m, dict) and m.get("role") == "system":
            had_system = True
            c = m.get("content")
            if isinstance(c, str) and c.strip():
                sys_texts.append(c.strip())
        else:
            rest.append(m)

    if not had_system:
        return messages  # 손댈 것 없음

    prefix = "\n\n".join(sys_texts).strip()
    if not prefix:
        return rest  # 빈 system 만 있었으면 제거

    out = []
    injected = False
    for m in rest:
        if (not injected and isinstance(m, dict) and m.get("role") == "user"):
            out.append({"role": "user",
                        "content": prefix + "\n\n" + (m.get("content") or "")})
            injected = True
        else:
            out.append(m)
    if not injected:
        out = [{"role": "user", "content": prefix}] + out
    return out


def adapt_payload(payload):
    """payload(dict) 의 messages 를 model 에 맞게 보정한 새 dict 반환."""
    if not isinstance(payload, dict):
        return payload
    msgs = payload.get("messages")
    model = payload.get("model")
    if isinstance(msgs, list) and model:
        new_msgs = fold_system_for_gemma(msgs, model)
        if new_msgs is not msgs:
            p = dict(payload)
            p["messages"] = new_msgs
            return p
    return payload


def chat_post(url, **kwargs):
    """req.post 대체. json 페이로드를 모델별로 보정한 뒤 전송."""
    body = kwargs.get("json")
    if isinstance(body, dict):
        kwargs["json"] = adapt_payload(body)
    return _rq.post(url, **kwargs)
