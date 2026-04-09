"""
demos_v1/models.py - MODEL_REGISTRY, API_MODEL_TIERS, ENV_CONFIG, FALLBACK_CHAINS
"""
import os
from demos_v1.config import _EXT_CONFIG

# ============================================
# 설정
# ============================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(BASE_DIR, "scientific-skills")
TOKEN_FILE = os.path.join(BASE_DIR, "TOKEN.TXT")
PROMPTS_DIR = os.path.join(BASE_DIR, "saved-prompts")
os.makedirs(PROMPTS_DIR, exist_ok=True)

# 멀티에이전트 모델 레지스트리 (api_config.json에서 로드, 없으면 기본값)
def _build_model_registry_from_config(config_models):
    """JSON config의 models → Python MODEL_REGISTRY로 변환 (capabilities: list→set)."""
    registry = {}
    for key, info in config_models.items():
        entry = dict(info)
        if "capabilities" in entry and isinstance(entry["capabilities"], list):
            entry["capabilities"] = set(entry["capabilities"])
        registry[key] = entry
    return registry

if _EXT_CONFIG.get("models"):
    MODEL_REGISTRY = _build_model_registry_from_config(_EXT_CONFIG["models"])
else:
    # 기본값 (api_config.json이 없을 때)
    MODEL_REGISTRY = {
    "glm-4.7": {
        "env_id": "dev-legacy",
        "model": "GLM-4.7",
        "url": "http://dev.hcp.llm.skhynix.com/v1/chat/completions",
        "name": "GLM-4.7",
        "capabilities": {"text", "code", "fast"},
        "context_window": 128000,
        "priority": 4,
        "cost_tier": "low",
    },
    "qwen3.5-397b": {
        "env_id": "prod",
        "model": "Qwen3.5-397B-A17B",
        "url": "http://dev.hcp.llm.skhynix.com/v1/chat/completions",
        "name": "PROD (397B)",
        "capabilities": {"text", "code", "analysis", "large"},
        "context_window": 128000,
        "priority": 1,
        "cost_tier": "high",
    },
    "gpt-oss-120b": {
        "env_id": "common",
        "model": "gpt-oss-120b",
        "url": "http://dev.hcp.llm.skhynix.com/v1/chat/completions",
        "name": "COMMON (120B)",
        "capabilities": {"text", "code", "medium"},
        "context_window": 128000,
        "priority": 2,
        "cost_tier": "medium",
    },
    "qwen3-vl-235b": {
        "env_id": "vl-large",
        "model": "Qwen3-VL-235B-A22B-Instruct",
        "url": "http://dev.hcp.llm.skhynix.com/v1/chat/completions",
        "name": "VL-235B (Vision)",
        "capabilities": {"text", "code", "vision", "analysis", "large"},
        "context_window": 128000,
        "priority": 1,
        "cost_tier": "high",
    },
    "qwen2.5-vl-72b": {
        "env_id": "vl-medium",
        "model": "Qwen2.5-VL-72B-Instruct",
        "url": "http://dev.hcp.llm.skhynix.com/v1/chat/completions",
        "name": "VL-72B (Vision)",
        "capabilities": {"text", "vision", "medium"},
        "context_window": 128000,
        "priority": 2,
        "cost_tier": "medium",
    },
    "qwen3-vl-30b": {
        "env_id": "vl-fast",
        "model": "Qwen3-VL-30B-A3B-Instruct",
        "url": "http://dev.hcp.llm.skhynix.com/v1/chat/completions",
        "name": "VL-30B (Vision/Fast)",
        "capabilities": {"text", "vision", "fast"},
        "context_window": 128000,
        "priority": 3,
        "cost_tier": "low",
    },
    "qwen3-coder-480b": {
        "env_id": "coder-480b",
        "model": "Qwen3-Coder-480B-A35B-Instruct",
        "url": "http://dev.hcp.llm.skhynix.com/v1/chat/completions",
        "name": "Coder-480B",
        "capabilities": {"text", "code", "analysis", "large"},
        "context_window": 128000,
        "priority": 1,
        "cost_tier": "high",
    },
    "qwen3.5-397b-fp8": {
        "env_id": "prod-fp8",
        "model": "Qwen3.5-397B-A17B-FP8",
        "url": "http://dev.hcp.llm.skhynix.com/v1/chat/completions",
        "name": "PROD-FP8 (397B)",
        "capabilities": {"text", "code", "analysis", "large"},
        "context_window": 128000,
        "priority": 1,
        "cost_tier": "high",
    },
    "qwen3-235b-2507": {
        "env_id": "qwen3-235b",
        "model": "Qwen3-235B-A22B-Instruct-2507",
        "url": "http://dev.hcp.llm.skhynix.com/v1/chat/completions",
        "name": "Qwen3-235B (2507)",
        "capabilities": {"text", "code", "analysis", "large"},
        "context_window": 128000,
        "priority": 1,
        "cost_tier": "high",
    },
    "qwen3-coder-next": {
        "env_id": "coder-next",
        "model": "Qwen3-Coder-Next",
        "url": "http://dev.hcp.llm.skhynix.com/v1/chat/completions",
        "name": "Coder-Next",
        "capabilities": {"text", "code", "medium"},
        "context_window": 128000,
        "priority": 1,
        "cost_tier": "medium",
    },
    "glm-5": {
        "env_id": "dev",
        "model": "GLM-5",
        "url": "http://dev.hcp.llm.skhynix.com/v1/chat/completions",
        "name": "GLM-5",
        "capabilities": {"text", "code", "analysis", "fast"},
        "context_window": 128000,
        "priority": 1,
        "cost_tier": "medium",
    },
    "glm-4.7-fp8": {
        "env_id": "dev-fp8",
        "model": "GLM-4.7-FP8",
        "url": "http://dev.hcp.llm.skhynix.com/v1/chat/completions",
        "name": "GLM-4.7-FP8",
        "capabilities": {"text", "code", "fast"},
        "context_window": 128000,
        "priority": 2,
        "cost_tier": "low",
    },
    "qwen3.5-35b": {
        "env_id": "qwen35-small",
        "model": "Qwen3.5-35B-A3B",
        "url": "http://dev.hcp.llm.skhynix.com/v1/chat/completions",
        "name": "Qwen3.5-35B (Fast)",
        "capabilities": {"text", "code", "fast"},
        "context_window": 128000,
        "priority": 3,
        "cost_tier": "low",
    },
    "bge-reranker": {
        "env_id": "reranker",
        "model": "bge-reranker-v2-m3",
        "url": "http://dev.hcp.llm.skhynix.com/v1/chat/completions",
        "name": "Reranker",
        "capabilities": {"rerank"},
        "context_window": 8192,
        "priority": 1,
        "cost_tier": "low",
    },
}

# API 모델 크기 티어 (api_config.json > 기본값)
API_MODEL_TIERS = _EXT_CONFIG.get("api_model_tiers", {
    "large": ["qwen3.5-397b", "qwen3-coder-480b", "qwen3-235b-2507", "qwen3.5-397b-fp8"],
    "medium": ["glm-5", "gpt-oss-120b", "qwen3-coder-next"],
    "small": ["glm-4.7", "glm-4.7-fp8", "qwen3.5-35b"],
})

# MODEL_REGISTRY에서 ENV_CONFIG 자동 생성 (하위 호환)
ENV_CONFIG = {
    v["env_id"]: {"url": v["url"], "model": v["model"], "name": v["name"]}
    for v in MODEL_REGISTRY.values()
    if "rerank" not in v.get("capabilities", set())
}
# gguf-N 환경은 앱 시작 시 .gguf 파일 자동 감지되면 추가됨

# env_id → registry key 역매핑
ENV_TO_REGISTRY = {v["env_id"]: k for k, v in MODEL_REGISTRY.items()}

# 폴백 체인 (api_config.json > 기본값)
FALLBACK_CHAINS = _EXT_CONFIG.get("fallback_chains", {
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
    "qwen3-vl-235b":     ["qwen2.5-vl-72b", "qwen3-vl-30b", "qwen3.5-397b", "qwen3-coder-480b", "glm-5", "gpt-oss-120b"],
    "qwen2.5-vl-72b":    ["qwen3-vl-235b", "qwen3-vl-30b", "qwen3.5-397b", "glm-5", "gpt-oss-120b"],
    "qwen3-vl-30b":      ["qwen2.5-vl-72b", "qwen3-vl-235b", "glm-5", "gpt-oss-120b", "qwen3.5-35b"],
})

# Reranker 기능 플래그 (bge-reranker 엔드포인트 안정화 후 활성화)
RERANKER_ENABLED = False

