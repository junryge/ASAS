#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
앱 설정 관리 - config.ini 기반 ENV_CONFIG, 토큰 로딩, GGUF 모델 목록
API URL/모델 설정은 config.ini 파일에서 관리
"""

import os
import sys
import logging
import configparser
from pathlib import Path

logger = logging.getLogger(__name__)

# 앱 기본 경로 (PyInstaller EXE 환경 지원)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(os.path.dirname(sys.executable))
else:
    BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# === config.ini 로드 ===
_FALLBACK_CONFIG = {
    "dev":    {"url": "", "model": "Qwen3-Coder-30B-A3B-Instruct", "name": "DEV(30B)", "max_tokens": "8192"},
    "prod":   {"url": "", "model": "Qwen3-Next-80B-A3B-Instruct",  "name": "PROD(80B)", "max_tokens": "8192"},
    "common": {"url": "", "model": "gpt-oss-20b",                   "name": "COMMON(20B)", "max_tokens": "4096"},
    "local":  {"url": "", "model": "Qwen3-14B-Q4_K_M",             "name": "LOCAL(14B-GGUF)", "max_tokens": "4096"},
}


def _load_env_config() -> dict:
    """config.ini 파일에서 환경별 설정 로드"""
    config_file = BASE_DIR / "config.ini"
    parser = configparser.ConfigParser()

    if config_file.exists():
        try:
            parser.read(str(config_file), encoding="utf-8")
            logger.info(f"config.ini 로드: {config_file}")
        except Exception as e:
            logger.warning(f"config.ini 로드 실패: {e}")

    result = {}
    for section in ["dev", "prod", "common", "local"]:
        fallback = _FALLBACK_CONFIG[section]
        if parser.has_section(section):
            result[section] = {
                "url":        parser.get(section, "url",        fallback=fallback["url"]).strip(),
                "model":      parser.get(section, "model",      fallback=fallback["model"]).strip(),
                "name":       parser.get(section, "name",       fallback=fallback["name"]).strip(),
                "max_tokens": int(parser.get(section, "max_tokens", fallback=fallback["max_tokens"])),
            }
        else:
            result[section] = {
                "url":        fallback["url"],
                "model":      fallback["model"],
                "name":       fallback["name"],
                "max_tokens": int(fallback["max_tokens"]),
            }
    return result


class AppConfig:
    """앱 전체 설정 관리"""

    ENV_CONFIG = _load_env_config()

    @staticmethod
    def _find_gguf(filename):
        """GGUF 파일 탐색: 현재폴더 → models/ 폴더"""
        for loc in [BASE_DIR / filename, BASE_DIR / "models" / filename]:
            if loc.exists():
                return str(loc)
        return str(BASE_DIR / filename)  # 기본값 (없어도 경로 반환)

    AVAILABLE_GGUF_MODELS = {
        "qwen3-14b": {
            "path": _find_gguf.__func__("Qwen3-14B-Q4_K_M.gguf"),
            "name": "Qwen3-14B",
            "desc": "14B Q4_K_M - 균형 잡힌 성능",
            "gpu_layers": 35,
            "ctx": 16384,
            "max_tokens": 4096
        },
        "qwen3-8b": {
            "path": _find_gguf.__func__("Qwen3-8B-Q6_K.gguf"),
            "name": "Qwen3-8B",
            "desc": "8B Q6_K - 빠른 추론",
            "gpu_layers": 35,
            "ctx": 32768,
            "max_tokens": 4096
        },
        "qwen3-1.7b": {
            "path": _find_gguf.__func__("qwen3-1.7b-q8_0.gguf"),
            "name": "Qwen3-1.7B",
            "desc": "1.7B Q8_0 - 경량 모델",
            "gpu_layers": 35,
            "ctx": 4096,
            "max_tokens": 2048
        },
    }

    def __init__(self):
        self.api_token = None
        self.llm_mode = "api"       # "api" 또는 "local"
        self.env_mode = "common"    # "dev", "prod", "common", "local"
        self.api_url = self.ENV_CONFIG["common"]["url"]
        self.api_model = self.ENV_CONFIG["common"]["model"]

        # 실제 존재하는 GGUF 모델 자동 감지
        default_model = self._detect_default_gguf()
        self.current_gguf_model = default_model
        self.gguf_model_path = self.AVAILABLE_GGUF_MODELS[default_model]["path"]

    def _detect_default_gguf(self) -> str:
        """실제 존재하는 GGUF 모델을 찾아 기본값 반환"""
        # 우선순위: qwen3-8b → qwen3-14b → qwen3-1.7b
        priority = ["qwen3-8b", "qwen3-14b", "qwen3-1.7b"]
        for key in priority:
            path = self.AVAILABLE_GGUF_MODELS[key]["path"]
            if os.path.exists(path):
                logger.info(f"GGUF 모델 자동 감지: {key} → {path}")
                return key
        # 모두 없으면 기본값
        logger.warning("GGUF 모델 파일을 찾을 수 없음 - 기본값 사용")
        return "qwen3-8b"

    def reload_config(self):
        """config.ini 다시 로드 (런타임 갱신)"""
        AppConfig.ENV_CONFIG = _load_env_config()
        if self.env_mode in self.ENV_CONFIG:
            self.api_url = self.ENV_CONFIG[self.env_mode]["url"]
            self.api_model = self.ENV_CONFIG[self.env_mode]["model"]
        logger.info("config.ini 설정 다시 로드 완료")

    def load_token(self) -> bool:
        """token.txt에서 API 토큰 로드 (로컬 → 상위 → 홈 디렉토리)"""
        paths = [
            str(BASE_DIR / "token.txt"),
            str(BASE_DIR.parent / "token.txt"),
            os.path.expanduser("~/token.txt"),
        ]
        for p in paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        token = f.read().strip()
                    if token and "REPLACE" not in token:
                        self.api_token = token
                        logger.info(f"토큰 로드 성공: {p}")
                        return True
                except Exception as e:
                    logger.error(f"토큰 로드 실패: {e}")
        logger.warning("토큰 파일을 찾을 수 없습니다")
        return False

    def set_env(self, env: str) -> bool:
        """LLM 환경 전환"""
        if env not in self.ENV_CONFIG:
            return False

        self.env_mode = env
        if env == "local":
            self.llm_mode = "local"
        else:
            if not self.api_token:
                return False
            self.llm_mode = "api"
            self.api_url = self.ENV_CONFIG[env]["url"]
            self.api_model = self.ENV_CONFIG[env]["model"]
        return True

    def switch_gguf_model(self, model_key: str) -> bool:
        """GGUF 모델 전환"""
        if model_key not in self.AVAILABLE_GGUF_MODELS:
            return False
        cfg = self.AVAILABLE_GGUF_MODELS[model_key]
        if not os.path.exists(cfg["path"]):
            return False
        self.current_gguf_model = model_key
        self.gguf_model_path = cfg["path"]
        self.ENV_CONFIG["local"]["model"] = cfg["name"]
        self.ENV_CONFIG["local"]["name"] = f"LOCAL({cfg['name']})"
        return True

    def get_gguf_config(self) -> dict:
        """현재 GGUF 모델 설정 반환"""
        return self.AVAILABLE_GGUF_MODELS.get(self.current_gguf_model, {})

    def get_max_tokens(self) -> int:
        """현재 모드/모델에 맞는 max_tokens 반환"""
        if self.llm_mode == "local":
            gguf_cfg = self.get_gguf_config()
            return gguf_cfg.get("max_tokens", 4096)
        else:
            env_cfg = self.ENV_CONFIG.get(self.env_mode, {})
            return env_cfg.get("max_tokens", 4096)
