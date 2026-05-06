"""
code_assist_v1/utils.py - 자체 글로벌 상태 (demos_v1 와 독립)
"""
from __future__ import annotations
import threading

# GGUF 모델 (llama-cpp-python) — 단일 인스턴스
gguf_model = None       # type: object | None
gguf_loaded_path = None  # type: str | None

# GGUF 멀티모델 풀 (병렬 사용 시)
_gguf_pool: list[dict] = []
_gguf_pool_lock = threading.Lock()
