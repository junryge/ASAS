"""rag_server/config.py — rag_config.json 로드 + 경로 정규화."""
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CFG_PATH = os.path.join(BASE_DIR, "rag_config.json")

_DEFAULTS = {
    "host": "127.0.0.1", "port": 8765,
    "knowledge_dir": "../knowledge",
    "embed_backend": "local",
    "local": {"model_path": "models/bge-m3-Q8_0.gguf", "n_ctx": 2048,
              "n_gpu_layers": 0, "n_threads": 0, "n_batch": 64},
    "api": {"url": "", "model": "bge-m3", "token_file": "", "timeout_s": 30},
    "chunk_size": 1000, "chunk_overlap": 180, "chunk_min": 200,
    "vector_candidate_limit": 6000, "bm25_prefilter_top": 600,
    "default_top_k": 8, "default_max_chars": 12000,
}


def _load():
    cfg = dict(_DEFAULTS)
    if os.path.isfile(_CFG_PATH):
        try:
            with open(_CFG_PATH, encoding="utf-8") as f:
                user = json.load(f)
            cfg.update({k: v for k, v in user.items() if not k.startswith("_")})
        except Exception as e:
            print(f"[config] rag_config.json 파싱 실패({e}) — 기본값 사용")
    return cfg


CFG = _load()


def abspath(p):
    """rag_server 기준 상대경로를 절대경로로."""
    if not p:
        return p
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(BASE_DIR, p))


KNOWLEDGE_DIR = abspath(CFG["knowledge_dir"])
DB_PATH = abspath(os.path.join("data", "index.db"))
