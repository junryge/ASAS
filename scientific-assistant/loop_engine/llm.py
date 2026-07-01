"""
llm.py — 부품 ④ 커넥터(LLM)

OpenAI 호환 /chat/completions 를 stdlib(urllib)만으로 호출.
- 외부 의존성 0
- 사내 self-signed 인증서 대비 verify_ssl=False 지원
- transport 콜러블 교체로 단위테스트(목) 가능
"""
from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .config import LLMConfig


Message = Dict[str, str]            # {"role": "...", "content": "..."}
Transport = Callable[[str, Dict[str, str], dict, int, bool], dict]


# ---------------------------------------------------------------------------
# 기본 HTTP transport (urllib)
# ---------------------------------------------------------------------------
def _urllib_transport(url: str, headers: Dict[str, str], payload: dict,
                      timeout: int, verify_ssl: bool) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    ctx = None
    if url.lower().startswith("https"):
        ctx = ssl.create_default_context()
        if not verify_ssl:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        raise LLMError(f"HTTP {e.code} {e.reason} :: {body[:500]}") from e
    except urllib.error.URLError as e:
        raise LLMError(f"연결 실패: {e.reason}") from e


class LLMError(RuntimeError):
    """LLM 호출 실패."""


@dataclass
class LLMResponse:
    text: str
    model: str
    raw: dict
    usage: Optional[dict] = None


class LLMClient:
    """내부 LLM 클라이언트.

    사용:
        client = LLMClient(LLMConfig(endpoint="LOCAL"))
        out = client.chat([{"role": "user", "content": "안녕"}])
        print(out.text)
    """

    def __init__(self, cfg: Optional[LLMConfig] = None,
                 transport: Optional[Transport] = None):
        self.cfg = cfg or LLMConfig()
        self.transport: Transport = transport or _urllib_transport
        self._base_url = self.cfg.resolve_base_url()
        self._token = self.cfg.resolve_token()

    # -- 핵심 호출 --
    def chat(self,
             messages: List[Message],
             model: Optional[str] = None,
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None,
             extra: Optional[dict] = None) -> LLMResponse:
        model = model or self.cfg.generator_model
        payload = {
            "model": model,
            "messages": messages,
            "temperature": self.cfg.temperature if temperature is None else temperature,
            "max_tokens": max_tokens or self.cfg.max_tokens,
        }
        if extra:
            payload.update(extra)

        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        url = f"{self._base_url}/chat/completions"

        last_err: Optional[Exception] = None
        for attempt in range(self.cfg.retries + 1):
            try:
                raw = self.transport(url, headers, payload,
                                     self.cfg.timeout, self.cfg.verify_ssl)
                text = self._extract_text(raw)
                return LLMResponse(text=text, model=model, raw=raw,
                                   usage=raw.get("usage"))
            except LLMError as e:
                last_err = e
                if attempt < self.cfg.retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise
        raise last_err  # pragma: no cover

    # -- 편의: system + user --
    def complete(self, prompt: str, system: Optional[str] = None,
                 **kw) -> str:
        msgs: List[Message] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        return self.chat(msgs, **kw).text

    @staticmethod
    def _extract_text(raw: dict) -> str:
        """OpenAI 호환 응답에서 텍스트 추출 (chat / completion 양식 모두 방어)."""
        try:
            choices = raw.get("choices") or []
            if not choices:
                return ""
            c0 = choices[0]
            if isinstance(c0.get("message"), dict):
                return (c0["message"].get("content") or "").strip()
            # 일부 서버는 text 필드만 줄 수 있음
            return (c0.get("text") or "").strip()
        except Exception as e:
            raise LLMError(f"응답 파싱 실패: {e} :: {str(raw)[:300]}")


# ---------------------------------------------------------------------------
# 테스트/오프라인용 목 transport 빌더
# ---------------------------------------------------------------------------
def make_mock_transport(responder: Callable[[List[Message], str], str]) -> Transport:
    """엔드포인트 없이 동작시키는 목.

    responder(messages, model) -> str 를 받아 OpenAI 호환 응답으로 감싼다.
    """
    def _t(url, headers, payload, timeout, verify_ssl):
        text = responder(payload.get("messages", []), payload.get("model", ""))
        return {
            "model": payload.get("model", "mock"),
            "choices": [{"message": {"role": "assistant", "content": text}}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }
    return _t
