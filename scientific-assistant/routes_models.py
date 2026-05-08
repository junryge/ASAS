"""
code_assist_v1/routes_models.py - 모델 목록 + 기본 시스템 프롬프트 노출 API

API 모델 + GGUF 모델 정보를 demos_v1.models에서 직접 가져와 노출.
(통합 모드 — code_assist_v1은 demos_v1과 같은 모델 풀을 그대로 공유)
"""
from __future__ import annotations
from flask import jsonify

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
        """demos_v1의 MODEL_REGISTRY + ENV_CONFIG(GGUF 포함)를 그대로 노출.

        demos_v1이 부팅 시 자동 등록한 GGUF가 이미 ENV_CONFIG에 들어있으므로
        code_assist_v1은 별도 빌드 없이 그것을 그대로 사용한다.
        """
        # demos_v1의 모델 정보 직접 import (요청 시점이라 부팅 후 최신 상태 보장)
        from demos_v1.models import MODEL_REGISTRY, ENV_CONFIG
        # priority 순서는 code_assist_v1 자체 설정 사용 (demos_v1엔 없음)
        from code_assist_v1.config import DEFAULT_MODEL_PRIORITY

        api_models = []
        for mid, info in MODEL_REGISTRY.items():
            caps = info.get("capabilities", [])
            if isinstance(caps, set):
                caps = sorted(caps)
            api_models.append({
                "id": mid,
                "env_id": info.get("env_id"),
                "name": info.get("name"),
                "model": info.get("model"),
                "url": info.get("url"),
                "context_window": info.get("context_window", 0),
                "cost_tier": info.get("cost_tier", "medium"),
                "capabilities": list(caps),
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

        # default 모델 — demos_v1 priority 첫 항목
        default_id = next(
            (mid for mid in DEFAULT_MODEL_PRIORITY if mid in MODEL_REGISTRY),
            next(iter(MODEL_REGISTRY.keys()), "")
        )

        return jsonify({
            "api": api_models,
            "gguf": gguf_models,
            "default": default_id,
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
