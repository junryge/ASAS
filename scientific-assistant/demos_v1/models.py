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
    # 기본값 (api_config.json이 없을 때) - 2026-06-05 사용 가능한 모델 5개만
    # 게이트웨이가 common.llm.skhynix.com 로 통합되고 아래 5종만 서비스됨.
    # (dev.hcp / GLM-5 / Coder 계열 / Next-80B 는 더 이상 사용 불가)
    MODEL_REGISTRY = {
    # === common.llm.skhynix.com — 현재 사용 가능한 5개 (2026-06-05) ===
    "qwen36-35b": {
        "env_id": "dev",
        "model": "Qwen3.6-35B-A3B",
        "url": "http://common.llm.skhynix.com/v1/chat/completions",
        "name": "Qwen3.6-35B-A3B (Common)",
        "capabilities": {"text", "code", "analysis", "large"},
        "context_window": 128000,
        "priority": 1,
        "cost_tier": "high",
    },
    "qwen25-vl-72b": {
        "env_id": "vl-72b",
        "model": "Qwen2.5-VL-72B-Instruct",
        "url": "http://common.llm.skhynix.com/v1/chat/completions",
        "name": "VL-72B (Vision/Common)",
        "capabilities": {"text", "vision", "large", "analysis"},
        "context_window": 128000,
        "priority": 1,
        "cost_tier": "high",
    },
    "qwen3-vl-30b": {
        "env_id": "vl-fast",
        "model": "Qwen3-VL-30B-A3B-Instruct",
        "url": "http://common.llm.skhynix.com/v1/chat/completions",
        "name": "VL-30B-A3B (Vision/Common)",
        "capabilities": {"text", "vision", "fast"},
        "context_window": 128000,
        "priority": 2,
        "cost_tier": "low",
    },
    "gemma-4-31b": {
        "env_id": "gemma",
        "model": "gemma-4-31B-it",
        "url": "http://common.llm.skhynix.com/v1/chat/completions",
        "name": "Gemma-4-31B-it (Common)",
        "capabilities": {"text", "analysis", "medium"},
        "context_window": 128000,
        "priority": 2,
        "cost_tier": "medium",
    },
    "gpt-oss-20b": {
        "env_id": "common",
        "model": "gpt-oss-20b",
        "url": "http://common.llm.skhynix.com/v1/chat/completions",
        "name": "GPT-OSS (20B/Common)",
        "capabilities": {"text", "code", "fast"},
        "context_window": 128000,
        "priority": 3,
        "cost_tier": "low",
    },
}

# API 모델 크기 티어 (api_config.json > 기본값)
API_MODEL_TIERS = _EXT_CONFIG.get("api_model_tiers", {
    "large": ["qwen25-vl-72b", "qwen36-35b"],
    "medium": ["gemma-4-31b", "qwen3-vl-30b"],
    "small": ["gpt-oss-20b"],
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
    # 텍스트 체인 (vision 모델은 텍스트도 가능하므로 후순위 포함)
    "qwen36-35b":    ["gemma-4-31b", "gpt-oss-20b"],
    "gemma-4-31b":   ["qwen36-35b", "gpt-oss-20b"],
    "gpt-oss-20b":   ["gemma-4-31b", "qwen36-35b"],
    # 비전 체인 (vision 우선 → 텍스트 폴백)
    "qwen25-vl-72b": ["qwen3-vl-30b", "qwen36-35b", "gemma-4-31b"],
    "qwen3-vl-30b":  ["qwen25-vl-72b", "qwen36-35b", "gemma-4-31b"],
})

# Reranker 기능 플래그 (bge-reranker 엔드포인트 안정화 후 활성화)
RERANKER_ENABLED = False
