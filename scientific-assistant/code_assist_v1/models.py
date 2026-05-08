"""
code_assist_v1/models.py - 자체 MODEL_REGISTRY (api_config.json 자체 로딩)

demos_v1.models 와 분리. 같은 프로세스에서도 독립 동작.
"""
from __future__ import annotations
import json
import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_THIS_DIR)
API_CONFIG_PATH = os.path.join(_ROOT_DIR, "api_config.json")  # demos_v1과 공유

# 외부 설정 로드
_EXT_CONFIG: dict = {}
if os.path.isfile(API_CONFIG_PATH):
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as _cf:
            _EXT_CONFIG = json.load(_cf)
        print(f"[code_assist_v1] api_config.json 로드 완료 ({len(_EXT_CONFIG.get('models', {}))}개 모델)")
    except Exception as _e:
        print(f"[code_assist_v1] api_config.json 로드 실패, 기본값 사용: {_e}")
else:
    print(f"[code_assist_v1] api_config.json 없음 → 기본값 사용 ({API_CONFIG_PATH})")


def _build_model_registry(config_models: dict) -> dict:
    """JSON config 의 models → Python MODEL_REGISTRY (capabilities: list→set)."""
    registry = {}
    for key, info in config_models.items():
        entry = dict(info)
        if "capabilities" in entry and isinstance(entry["capabilities"], list):
            entry["capabilities"] = set(entry["capabilities"])
        registry[key] = entry
    return registry


# 기본 모델 (api_config.json 없을 때 폴백)
_DEFAULT_MODELS = {
    "qwen3-coder-480b": {
        "env_id": "coder-480b",
        "model": "Qwen3-Coder-480B-A35B-Instruct",
        "url": "http://dev.hcp.llm.skhynix.com/v1/chat/completions",
        "name": "Coder-480B (HCP)",
        "capabilities": {"text", "code", "analysis", "large"},
        "context_window": 128000,
        "priority": 1,
        "cost_tier": "high",
    },
}

if _EXT_CONFIG.get("models"):
    MODEL_REGISTRY = _build_model_registry(_EXT_CONFIG["models"])
else:
    MODEL_REGISTRY = _DEFAULT_MODELS

# env_id → {url, model, name} 매핑 (GGUF는 app_code 에서 동적 추가됨)
ENV_CONFIG: dict = {
    v["env_id"]: {"url": v["url"], "model": v["model"], "name": v["name"]}
    for v in MODEL_REGISTRY.values()
}

# env_id → registry key 역매핑
ENV_TO_REGISTRY: dict = {v["env_id"]: k for k, v in MODEL_REGISTRY.items()}

# 토큰/컨텍스트 설정 (api_config.json > 환경변수 > 기본값)
_token_cfg = _EXT_CONFIG.get("token_settings", {})
TOKEN_SETTINGS = {
    "agent_max_tokens": int(os.getenv("AGENT_MAX_TOKENS", str(_token_cfg.get("agent_max_tokens", 8192)))),
    "synth_max_tokens": int(os.getenv("SYNTH_MAX_TOKENS", str(_token_cfg.get("synth_max_tokens", 16384)))),
    "default_n_ctx": int(os.getenv("DEFAULT_N_CTX", str(_token_cfg.get("default_n_ctx", 32768)))),
    "gguf_reply_cap": int(os.getenv("GGUF_MAX_TOKENS_CAP", str(_token_cfg.get("gguf_reply_cap", 4096)))),
    "gguf_ctx_reserve": int(os.getenv("GGUF_CONTEXT_RESERVE", str(_token_cfg.get("gguf_ctx_reserve", 1536)))),
    "parallel_agent_max_tokens": int(os.getenv("PARALLEL_AGENT_MAX_TOKENS", str(_token_cfg.get("parallel_agent_max_tokens", 4096)))),
}

# GGUF 설정
_gguf_cfg = _EXT_CONFIG.get("gguf", {})
GGUF_MODEL_DIR_NAME = _gguf_cfg.get("model_dir", "MODEL_GGUF")
MAX_POOL_SIZE = int(os.getenv("GGUF_MAX_POOL_SIZE", str(_gguf_cfg.get("max_pool_size", 4))))
VRAM_BUDGET_GB = float(os.getenv("GGUF_VRAM_BUDGET_GB", str(_gguf_cfg.get("vram_budget_gb", 14))))
GGUF_DEFAULT_N_CTX = int(_gguf_cfg.get("n_ctx", 32768))
GGUF_DEFAULT_N_GPU_LAYERS = int(_gguf_cfg.get("n_gpu_layers", 99))
GGUF_DEFAULT_N_BATCH = int(_gguf_cfg.get("n_batch", 2048))

# 기본 모델 우선순위 (api_config.json > 코드 기본값)
DEFAULT_MODEL_PRIORITY = _EXT_CONFIG.get("default_model_priority", [
    "qwen3-coder-480b",
    "qwen3-coder-next",
    "qwen3-coder-30b",
    "glm-5",
    "qwen3-next-80b",
    "gpt-oss-20b",
])
