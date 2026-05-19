"""
backend/config.py - api_config.json 로더 + 시크릿 환경변수 치환.

집/회사 양쪽에서 공유되는 설정만 들고 있음. gguf 단일 인스턴스 관련 상태는
foundry_server.py 모듈 전역에 남겨두고 여기로 가져오지 않는다 (경로 분리).
"""
import json
import os
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_DIR = _BACKEND_DIR.parent
_CONFIG_PATH = _PROJECT_DIR / "api_config.json"


def _resolve_env(value):
    """문자열이 '${VAR}' 형태면 환경변수로 치환. 그 외는 그대로."""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return os.environ.get(value[2:-1], "")
    return value


def _walk(obj):
    if isinstance(obj, dict):
        return {k: _walk(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_walk(v) for v in obj]
    return _resolve_env(obj)


def load_config():
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    cfg = _walk(raw)

    # logpresso.api_key_env 우선 → 없으면 logpresso.api_key (구버전 호환)
    lp = cfg.get("logpresso") or {}
    env_name = lp.get("api_key_env")
    if env_name:
        lp["api_key"] = os.environ.get(env_name, "")
    cfg["logpresso"] = lp
    return cfg


_CFG = load_config()

PROJECT_DIR = str(_PROJECT_DIR)
TOKEN_SETTINGS = _CFG.get("token_settings", {})
GGUF_SETTINGS = _CFG.get("gguf", {})
LOGPRESSO = _CFG.get("logpresso", {})
MODELS = _CFG.get("models", {})
API_MODEL_TIERS = _CFG.get("api_model_tiers", {})
FALLBACK_CHAINS = _CFG.get("fallback_chains", {})

# 단일 GGUF 운영용 — gguf.py가 쓰던 풀 관련 상수는 의도적으로 제거.
DEFAULT_N_CTX = int(TOKEN_SETTINGS.get("default_n_ctx", 4096))
GGUF_REPLY_CAP = int(TOKEN_SETTINGS.get("gguf_reply_cap", 4096))


def default_model_for_tier(tier):
    """tier ∈ {'large','medium','small'} 에서 첫 모델 id 반환."""
    arr = API_MODEL_TIERS.get(tier) or []
    return arr[0] if arr else None


def get_model(model_id):
    """model_id로 models 엔트리 반환 (없으면 None)."""
    return MODELS.get(model_id)


def fallback_chain(model_id):
    """주어진 모델의 fallback 체인 (자기 자신 미포함)."""
    return list(FALLBACK_CHAINS.get(model_id, []))
