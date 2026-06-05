"""
Hermes Engine — 포터블 "기억하고 배우는" AI 에이전트 레이어.

기존 hermes-agent 패키지 없이, 어떤 Flask + LLM 챗 앱에도 드롭인으로 추가.
폐쇄망 / GGUF / API 어디서나 동작 (네이티브 툴콜 불필요, 텍스트 프로토콜).

빠른 사용:
    from hermes import register_hermes_routes
    register_hermes_routes(app)         # /api/hermes/* 등록

프로그래밍 API:
    from hermes import engine
    addon = engine.build_system_prompt(user_id, query)   # 시스템 프롬프트에 추가
    res   = engine.apply_response(user_id, answer)        # 응답 블록 처리
"""
from .routes import register_hermes_routes
from . import engine, memory, skills, sessions, counters, protocol, store, config, curator, review, builtin

__all__ = [
    "register_hermes_routes",
    "engine", "memory", "skills", "sessions", "counters", "protocol", "store", "config",
    "curator", "review", "builtin",
]
__version__ = "0.1.0"
