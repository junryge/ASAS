"""Model registry and fallback chains.

Reference: SKILL/scientific-assistant/app.py lines 350-522
"""

from __future__ import annotations

from typing import Any

# All models point to SK Hynix internal LLM server (OpenAI-compatible)
_BASE_URL = "http://dev.hcp.llm.skhynix.com/v1/chat/completions"

MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    # ── Text/Code models (performance descending) ──
    "qwen3.5-397b": {
        "env_id": "prod",
        "model": "Qwen3.5-397B-A17B",
        "url": _BASE_URL,
        "name": "PROD (397B)",
        "capabilities": {"text", "code", "analysis", "large"},
        "context_window": 128_000,
        "priority": 1,
        "cost_tier": "high",
    },
    "qwen3-coder-480b": {
        "env_id": "coder-480b",
        "model": "Qwen3-Coder-480B-A35B-Instruct",
        "url": _BASE_URL,
        "name": "Coder-480B",
        "capabilities": {"text", "code", "analysis", "large"},
        "context_window": 128_000,
        "priority": 1,
        "cost_tier": "high",
    },
    "qwen3-235b-2507": {
        "env_id": "qwen3-235b",
        "model": "Qwen3-235B-A22B-Instruct-2507",
        "url": _BASE_URL,
        "name": "Qwen3-235B (2507)",
        "capabilities": {"text", "code", "analysis", "large"},
        "context_window": 128_000,
        "priority": 1,
        "cost_tier": "high",
    },
    "glm-5": {
        "env_id": "dev",
        "model": "GLM-5",
        "url": _BASE_URL,
        "name": "GLM-5",
        "capabilities": {"text", "code", "analysis", "fast"},
        "context_window": 128_000,
        "priority": 1,
        "cost_tier": "medium",
    },
    "gpt-oss-120b": {
        "env_id": "common",
        "model": "gpt-oss-120b",
        "url": _BASE_URL,
        "name": "COMMON (120B)",
        "capabilities": {"text", "code", "medium"},
        "context_window": 128_000,
        "priority": 2,
        "cost_tier": "medium",
    },
    "qwen3-coder-next": {
        "env_id": "coder-next",
        "model": "Qwen3-Coder-Next",
        "url": _BASE_URL,
        "name": "Coder-Next",
        "capabilities": {"text", "code", "medium"},
        "context_window": 128_000,
        "priority": 1,
        "cost_tier": "medium",
    },
    "glm-4.7": {
        "env_id": "dev-legacy",
        "model": "GLM-4.7",
        "url": _BASE_URL,
        "name": "GLM-4.7",
        "capabilities": {"text", "code", "fast"},
        "context_window": 128_000,
        "priority": 4,
        "cost_tier": "low",
    },
    "glm-4.7-fp8": {
        "env_id": "dev-fp8",
        "model": "GLM-4.7-FP8",
        "url": _BASE_URL,
        "name": "GLM-4.7-FP8",
        "capabilities": {"text", "code", "fast"},
        "context_window": 128_000,
        "priority": 2,
        "cost_tier": "low",
    },
    "qwen3.5-397b-fp8": {
        "env_id": "prod-fp8",
        "model": "Qwen3.5-397B-A17B-FP8",
        "url": _BASE_URL,
        "name": "PROD-FP8 (397B)",
        "capabilities": {"text", "code", "analysis", "large"},
        "context_window": 128_000,
        "priority": 1,
        "cost_tier": "high",
    },
    "qwen3.5-35b": {
        "env_id": "qwen35-small",
        "model": "Qwen3.5-35B-A3B",
        "url": _BASE_URL,
        "name": "Qwen3.5-35B (Fast)",
        "capabilities": {"text", "code", "fast"},
        "context_window": 128_000,
        "priority": 3,
        "cost_tier": "low",
    },
    # ── Vision models ──
    "qwen3-vl-235b": {
        "env_id": "vl-large",
        "model": "Qwen3-VL-235B-A22B-Instruct",
        "url": _BASE_URL,
        "name": "VL-235B (Vision)",
        "capabilities": {"text", "code", "vision", "analysis", "large"},
        "context_window": 128_000,
        "priority": 1,
        "cost_tier": "high",
    },
    "qwen2.5-vl-72b": {
        "env_id": "vl-medium",
        "model": "Qwen2.5-VL-72B-Instruct",
        "url": _BASE_URL,
        "name": "VL-72B (Vision)",
        "capabilities": {"text", "vision", "medium"},
        "context_window": 128_000,
        "priority": 2,
        "cost_tier": "medium",
    },
    "qwen3-vl-30b": {
        "env_id": "vl-fast",
        "model": "Qwen3-VL-30B-A3B-Instruct",
        "url": _BASE_URL,
        "name": "VL-30B (Vision/Fast)",
        "capabilities": {"text", "vision", "fast"},
        "context_window": 128_000,
        "priority": 3,
        "cost_tier": "low",
    },
}

# Fallback chains: on failure, try models in performance-descending order
FALLBACK_CHAINS: dict[str, list[str]] = {
    "qwen3.5-397b":      ["qwen3-coder-480b", "qwen3-235b-2507", "glm-5", "gpt-oss-120b", "qwen3-coder-next", "glm-4.7", "glm-4.7-fp8", "qwen3.5-397b-fp8", "qwen3.5-35b"],
    "qwen3-coder-480b":  ["qwen3.5-397b", "qwen3-235b-2507", "glm-5", "gpt-oss-120b", "qwen3-coder-next", "glm-4.7", "qwen3.5-35b"],
    "qwen3-235b-2507":   ["qwen3.5-397b", "qwen3-coder-480b", "glm-5", "gpt-oss-120b", "qwen3-coder-next", "glm-4.7", "qwen3.5-35b"],
    "glm-5":             ["qwen3.5-397b", "qwen3-coder-480b", "qwen3-235b-2507", "gpt-oss-120b", "qwen3-coder-next", "glm-4.7", "qwen3.5-35b"],
    "gpt-oss-120b":      ["qwen3.5-397b", "qwen3-coder-480b", "qwen3-235b-2507", "glm-5", "qwen3-coder-next", "glm-4.7", "glm-4.7-fp8", "qwen3.5-35b"],
    "qwen3-coder-next":  ["qwen3.5-397b", "qwen3-coder-480b", "qwen3-235b-2507", "glm-5", "gpt-oss-120b", "glm-4.7", "qwen3.5-35b"],
    "glm-4.7":           ["glm-5", "qwen3.5-397b", "qwen3-coder-480b", "qwen3-235b-2507", "gpt-oss-120b", "glm-4.7-fp8", "qwen3.5-35b"],
    "glm-4.7-fp8":       ["glm-5", "glm-4.7", "qwen3.5-397b", "qwen3-coder-480b", "qwen3-235b-2507", "gpt-oss-120b", "qwen3.5-35b"],
    "qwen3.5-397b-fp8":  ["qwen3.5-397b", "qwen3-coder-480b", "qwen3-235b-2507", "glm-5", "gpt-oss-120b", "glm-4.7", "qwen3.5-35b"],
    "qwen3.5-35b":       ["glm-5", "gpt-oss-120b", "qwen3-coder-next", "glm-4.7", "qwen3.5-397b", "qwen3-coder-480b", "qwen3-235b-2507"],
    # Vision models: vision first → text fallback
    "qwen3-vl-235b":     ["qwen2.5-vl-72b", "qwen3-vl-30b", "qwen3.5-397b", "qwen3-coder-480b", "glm-5", "gpt-oss-120b"],
    "qwen2.5-vl-72b":    ["qwen3-vl-235b", "qwen3-vl-30b", "qwen3.5-397b", "glm-5", "gpt-oss-120b"],
    "qwen3-vl-30b":      ["qwen2.5-vl-72b", "qwen3-vl-235b", "glm-5", "gpt-oss-120b", "qwen3.5-35b"],
}

# Auto-generated env_id → config mapping
ENV_CONFIG: dict[str, dict[str, str]] = {
    v["env_id"]: {"url": v["url"], "model": v["model"], "name": v["name"]}
    for v in MODEL_REGISTRY.values()
}

# env_id → registry key reverse mapping
ENV_TO_REGISTRY: dict[str, str] = {
    v["env_id"]: k for k, v in MODEL_REGISTRY.items()
}

# Default model for new sessions
DEFAULT_MODEL = "qwen3.5-397b"


def get_model_config(model_key: str) -> dict[str, Any] | None:
    """Get model configuration by registry key or env_id."""
    if model_key in MODEL_REGISTRY:
        return MODEL_REGISTRY[model_key]
    # Try env_id lookup
    reg_key = ENV_TO_REGISTRY.get(model_key)
    if reg_key:
        return MODEL_REGISTRY[reg_key]
    return None


def get_fallback_chain(model_key: str) -> list[str]:
    """Get fallback chain for a model."""
    return FALLBACK_CHAINS.get(model_key, [])


def get_max_tokens(model_key: str) -> int:
    """Get max_tokens based on model cost tier."""
    config = get_model_config(model_key)
    if not config:
        return 4096
    tier = config.get("cost_tier", "medium")
    if tier == "high":
        return 16384
    elif tier == "medium":
        return 8192
    return 4096


def list_text_models() -> list[str]:
    """List all text/code model keys (no vision)."""
    return [
        k for k, v in MODEL_REGISTRY.items()
        if "vision" not in v["capabilities"]
    ]


def list_vision_models() -> list[str]:
    """List all vision-capable model keys."""
    return [
        k for k, v in MODEL_REGISTRY.items()
        if "vision" in v["capabilities"]
    ]


def classify_and_route(
    prompt: str,
    has_images: bool = False,
) -> str:
    """Auto-select model based on query complexity.

    Reference: app.py lines 1996-2089
    """
    prompt_lower = prompt.lower()
    prompt_len = len(prompt)

    # Vision routing
    if has_images:
        complexity_signals = sum([
            "분석" in prompt_lower or "analyze" in prompt_lower,
            "비교" in prompt_lower or "compare" in prompt_lower,
            prompt_len > 200,
        ])
        if complexity_signals >= 2:
            return "qwen3-vl-235b"
        elif complexity_signals >= 1:
            return "qwen2.5-vl-72b"
        return "qwen3-vl-30b"

    # Code routing
    code_signals = sum([
        "코드" in prompt_lower or "code" in prompt_lower,
        "함수" in prompt_lower or "function" in prompt_lower,
        "구현" in prompt_lower or "implement" in prompt_lower,
        "리팩토링" in prompt_lower or "refactor" in prompt_lower,
        "디버그" in prompt_lower or "debug" in prompt_lower,
        "```" in prompt,
    ])
    if code_signals >= 2:
        return "qwen3-coder-480b"

    # Complex analysis routing
    analysis_signals = sum([
        "분석" in prompt_lower or "analyze" in prompt_lower,
        "설계" in prompt_lower or "design" in prompt_lower or "architect" in prompt_lower,
        "비교" in prompt_lower or "compare" in prompt_lower,
        prompt_len > 500,
        prompt.count("\n") > 5,
    ])
    if analysis_signals >= 2:
        return "qwen3.5-397b"

    # Simple Q&A
    if prompt_len < 50:
        return "gpt-oss-120b"

    # Default: balanced model
    return "glm-5"
