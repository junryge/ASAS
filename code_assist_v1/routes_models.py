"""
code_assist_v1/routes_models.py - 모델 목록 + 기본 시스템 프롬프트 노출 API
"""
from __future__ import annotations
from flask import jsonify

from code_assist_v1.config import (
    MODEL_REGISTRY,
    ENV_CONFIG,
    DEFAULT_MODEL_PRIORITY,
    get_default_model,
)
from code_assist_v1.prompts import (
    CODING_SYSTEM_PROMPT,
    ANTI_HALLUCINATION,
    KNOWLEDGE_INJECT_HEADER,
    WORKSPACE_INJECT_HEADER,
    SKILL_INJECT_HEADER,
)


def register_model_routes(app):
    @app.route("/api/code/models")
    def api_code_models():
        """API 모델 + GGUF 모델 통합 목록.

        GGUF 는 app_code 기동 시 ENV_CONFIG 에 'gguf-N' 으로 동적 등록됨.
        """
        api_models = []
        for mid, info in MODEL_REGISTRY.items():
            api_models.append({
                "id": mid,
                "env_id": info.get("env_id"),
                "name": info.get("name"),
                "model": info.get("model"),
                "url": info.get("url"),
                "context_window": info.get("context_window", 0),
                "cost_tier": info.get("cost_tier", "medium"),
                "capabilities": sorted(list(info.get("capabilities", []))),
                "kind": "api",
            })

        gguf_models = []
        for env_id, ecfg in ENV_CONFIG.items():
            if env_id.startswith("gguf-"):
                gguf_models.append({
                    "id": env_id,
                    "env_id": env_id,
                    "name": ecfg.get("name"),
                    "model": ecfg.get("model"),
                    "url": ecfg.get("url"),
                    "size_gb": ecfg.get("_size_gb"),
                    "kind": "gguf",
                })

        return jsonify({
            "api": api_models,
            "gguf": gguf_models,
            "default": get_default_model(),
            "priority": DEFAULT_MODEL_PRIORITY,
        })

    @app.route("/api/code/system_prompt")
    def api_system_prompt():
        """기본 시스템 프롬프트를 클라이언트에 노출 (확인·편집용)."""
        return jsonify({
            "base": CODING_SYSTEM_PROMPT.strip(),
            "anti_hallucination": ANTI_HALLUCINATION.strip(),
            "headers": {
                "knowledge": KNOWLEDGE_INJECT_HEADER.strip(),
                "workspace": WORKSPACE_INJECT_HEADER.strip(),
                "skill": SKILL_INJECT_HEADER.strip(),
            },
            "note": "활성 스킬 본문 + 도메인 지식(KB ON 시) + 워크스페이스 첨부 파일이 위에 더해져 최종 시스템 메시지가 만들어집니다.",
        })
