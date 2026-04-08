"""LLM Provider - OpenAI-compatible API client with fallback chains.

Reference: SKILL/scientific-assistant/app.py lines 7073-7244
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Iterator

import urllib.request
import urllib.error

from .token import load_token, print_token_status, find_token_file
from .models import (
    MODEL_REGISTRY,
    DEFAULT_MODEL,
    get_model_config,
    get_fallback_chain,
    get_max_tokens,
    classify_and_route,
)


@dataclass
class ChatMessage:
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class ChatResponse:
    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    finish_reason: str = "stop"
    fallback_used: bool = False
    attempts: list[str] = field(default_factory=list)


class ProviderError(Exception):
    """Raised when all models fail."""
    pass


@dataclass
class Provider:
    """OpenAI-compatible LLM API provider with token auth and fallback chains."""

    token: str = ""
    default_model: str = DEFAULT_MODEL
    timeout: int = 120
    max_retries: int = 6
    _initialized: bool = False

    def __post_init__(self) -> None:
        if not self.token:
            self.token = load_token()
        self._initialized = True

    @property
    def has_token(self) -> bool:
        return bool(self.token)

    def print_status(self) -> None:
        """Print provider status at startup."""
        print_token_status(self.token, find_token_file())
        if self.has_token:
            model_cfg = get_model_config(self.default_model)
            if model_cfg:
                print(f"  🤖 Default model: {model_cfg['name']}")

    def chat(
        self,
        messages: list[ChatMessage] | list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = False,
        auto_route: bool = True,
    ) -> ChatResponse:
        """Send chat completion request with automatic fallback.

        Args:
            messages: Chat messages (ChatMessage or dict)
            model: Model key (auto-selected if None and auto_route=True)
            temperature: Sampling temperature
            max_tokens: Max output tokens (auto from cost tier if None)
            stream: Enable streaming (not yet implemented)
            auto_route: Auto-select model based on query complexity
        """
        if not self.has_token:
            raise ProviderError(
                "No API token. Place your key in ~/.openharness/TOKEN.TXT"
            )

        # Normalize messages
        msg_dicts = []
        for m in messages:
            if isinstance(m, ChatMessage):
                msg_dicts.append({"role": m.role, "content": m.content})
            else:
                msg_dicts.append(m)

        # Auto-route model selection
        if model is None and auto_route:
            last_user = ""
            has_images = False
            for m in reversed(msg_dicts):
                if m["role"] == "user":
                    if isinstance(m["content"], str):
                        last_user = m["content"]
                    elif isinstance(m["content"], list):
                        parts = [p.get("text", "") for p in m["content"] if p.get("type") == "text"]
                        last_user = " ".join(parts)
                        has_images = any(p.get("type") == "image_url" for p in m["content"])
                    break
            model = classify_and_route(last_user, has_images)
        elif model is None:
            model = self.default_model

        if max_tokens is None:
            max_tokens = get_max_tokens(model)

        # Build attempt chain: primary + fallbacks
        attempt_chain = [model] + get_fallback_chain(model)
        attempt_chain = attempt_chain[:self.max_retries]

        attempts: list[str] = []
        last_error = ""

        for try_model_key in attempt_chain:
            config = get_model_config(try_model_key)
            if not config:
                continue

            try_url = config["url"]
            try_model_name = config["model"]
            attempts.append(try_model_key)

            try:
                response = self._api_call(
                    url=try_url,
                    model=try_model_name,
                    messages=msg_dicts,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return ChatResponse(
                    content=response["content"],
                    model=try_model_key,
                    usage=response.get("usage", {}),
                    finish_reason=response.get("finish_reason", "stop"),
                    fallback_used=len(attempts) > 1,
                    attempts=attempts,
                )
            except Exception as e:
                last_error = str(e)
                time.sleep(1)  # Brief pause before fallback
                continue

        raise ProviderError(
            f"All {len(attempts)} models failed. "
            f"Last error: {last_error}. "
            f"Attempted: {', '.join(attempts)}"
        )

    def _api_call(
        self,
        url: str,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Execute single API call to OpenAI-compatible endpoint."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        payload = json.dumps({
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            raise ProviderError(f"HTTP {e.code}: {body[:200]}")
        except urllib.error.URLError as e:
            raise ProviderError(f"Connection error: {e.reason}")
        except TimeoutError:
            raise ProviderError(f"Timeout after {self.timeout}s")

        # Parse OpenAI-compatible response
        if "choices" not in data or not data["choices"]:
            raise ProviderError(f"Invalid response format: {json.dumps(data)[:200]}")

        choice = data["choices"][0]
        content = choice.get("message", {}).get("content", "")

        # Handle thinking token overflow: retry with 2x tokens if only <think> tags
        if content.strip().startswith("<think>") and "</think>" in content:
            after_think = content.split("</think>", 1)
            if len(after_think) < 2 or not after_think[1].strip():
                # Only thinking, no actual answer - would need retry with more tokens
                pass

        return {
            "content": content,
            "usage": data.get("usage", {}),
            "finish_reason": choice.get("finish_reason", "stop"),
        }

    def stream_chat(
        self,
        messages: list[ChatMessage] | list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        """Stream chat response token by token (SSE)."""
        if not self.has_token:
            raise ProviderError("No API token")

        msg_dicts = []
        for m in messages:
            if isinstance(m, ChatMessage):
                msg_dicts.append({"role": m.role, "content": m.content})
            else:
                msg_dicts.append(m)

        if model is None:
            model = self.default_model
        if max_tokens is None:
            max_tokens = get_max_tokens(model)

        config = get_model_config(model)
        if not config:
            raise ProviderError(f"Unknown model: {model}")

        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        payload = json.dumps({
            "model": config["model"],
            "messages": msg_dicts,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }).encode("utf-8")

        req = urllib.request.Request(
            config["url"], data=payload, headers=headers, method="POST"
        )

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue


def create_provider(
    token: str | None = None,
    model: str = DEFAULT_MODEL,
) -> Provider:
    """Factory function to create a Provider instance."""
    return Provider(
        token=token or "",
        default_model=model,
    )
