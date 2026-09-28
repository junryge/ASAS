"""
code_assist_v1/models.py - 모델 목록 · 토큰/GGUF 설정

API 모델 목록은 데모스(demos_v1.models)의 것을 그대로 쓴다 — 게이트웨이 /v1/models 목록.
api_config.json 에서는 token_settings · gguf 설정만 읽는다. GGUF 는 예전 그대로다.
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
        print("[code_assist_v1] api_config.json 로드 완료 (토큰 · GGUF 설정)")
    except Exception as _e:
        print(f"[code_assist_v1] api_config.json 로드 실패, 기본값 사용: {_e}")
else:
    print(f"[code_assist_v1] api_config.json 없음 → 기본값 사용 ({API_CONFIG_PATH})")


# ★API 모델 목록은 데모스와 같은 것 — 게이트웨이(/v1/models)가 준 목록이다 (demos_v1/models.py).
#   예전엔 api_config.json 의 "models" 를 여기서도 따로 읽어, 데모스와 목록이 어긋날 수 있었다.
#   같은 dict 객체를 가져오므로 데모스가 목록을 다시 읽으면 여기도 그대로 바뀐다.
try:
    from demos_v1.models import (  # noqa: E402
        MODEL_REGISTRY, ENV_CONFIG, ENV_TO_REGISTRY, DEFAULT_MODEL_PRIORITY,
    )
except Exception as _e:  # 데모스 없이 따로 켠 경우(더는 지원하지 않음) — 빈 목록
    print(f"[code_assist_v1] 데모스 모델 목록을 못 가져옴: {_e}")
    MODEL_REGISTRY, ENV_CONFIG, ENV_TO_REGISTRY, DEFAULT_MODEL_PRIORITY = {}, {}, {}, []

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
