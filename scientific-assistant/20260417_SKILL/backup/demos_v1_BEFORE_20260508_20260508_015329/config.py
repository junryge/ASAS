"""
demos_v1/config.py - Configuration loading, external config, token, logpresso settings
"""
import os
import json
import time
import re
import threading
from demos_v1.utils import BASE_DIR, TOKEN_FILE

# ============================================
# 외부 설정 파일 로드 (api_config.json)
# ============================================
_CONFIG_PATH = os.path.join(BASE_DIR, "api_config.json")
_EXT_CONFIG = {}
if os.path.isfile(_CONFIG_PATH):
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as _cf:
            _EXT_CONFIG = json.load(_cf)
        print(f"[CONFIG] api_config.json 로드 완료 ({len(_EXT_CONFIG.get('models', {}))}개 모델)")
    except Exception as _cfg_err:
        print(f"[CONFIG] api_config.json 로드 실패, 기본값 사용: {_cfg_err}")
else:
    print("[CONFIG] api_config.json 없음, 기본값 사용")

# GGUF 멀티모델 풀 설정
_gguf_cfg = _EXT_CONFIG.get("gguf", {})
MAX_POOL_SIZE = int(os.getenv("GGUF_MAX_POOL_SIZE", str(_gguf_cfg.get("max_pool_size", 4))))
VRAM_BUDGET_GB = float(os.getenv("GGUF_VRAM_BUDGET_GB", str(_gguf_cfg.get("vram_budget_gb", 14))))

# ── 토큰/컨텍스트 설정 (api_config.json > 환경변수 > 기본값) ──
_token_cfg = _EXT_CONFIG.get("token_settings", {})
TOKEN_SETTINGS = {
    "agent_max_tokens": int(os.getenv("AGENT_MAX_TOKENS", str(_token_cfg.get("agent_max_tokens", 8192)))),
    "synth_max_tokens": int(os.getenv("SYNTH_MAX_TOKENS", str(_token_cfg.get("synth_max_tokens", 16384)))),
    "default_n_ctx": int(os.getenv("DEFAULT_N_CTX", str(_token_cfg.get("default_n_ctx", 32768)))),
    "gguf_reply_cap": int(os.getenv("GGUF_MAX_TOKENS_CAP", str(_token_cfg.get("gguf_reply_cap", 16384)))),
    "gguf_ctx_reserve": int(os.getenv("GGUF_CONTEXT_RESERVE", str(_token_cfg.get("gguf_ctx_reserve", 1536)))),
    "parallel_agent_max_tokens": int(os.getenv("PARALLEL_AGENT_MAX_TOKENS", str(_token_cfg.get("parallel_agent_max_tokens", 4096)))),
}

_gguf_pool_lock = threading.Lock()
_gguf_pool = []  # [{"model": Llama, "path": str, "size_gb": float, "n_ctx": int, "in_use": bool, "last_used": float}]


def load_token():
    """TOKEN.TXT 파일에서 API 키 읽기"""
    if os.path.isfile(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8-sig") as f:
            token = f.read().strip()
            if not token:
                print(f"  ⚠️  TOKEN.TXT 파일이 비어있습니다 - API 키를 입력하세요: {TOKEN_FILE}")
                return ""
            # ASCII만 허용 (한글 플레이스홀더 무시)
            try:
                token.encode("ascii")
                return token
            except UnicodeEncodeError:
                print(f"  ⚠️  TOKEN.TXT에 비영문 문자 포함 - 실제 API 키로 교체하세요")
                return ""
    else:
        print(f"  ⚠️  TOKEN.TXT 파일을 찾을 수 없습니다: {TOKEN_FILE}")
    return ""


API_TOKEN = load_token()

# Reranker 기능 플래그 (bge-reranker 엔드포인트 안정화 후 활성화)
RERANKER_ENABLED = False
