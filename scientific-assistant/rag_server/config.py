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


_LOCAL_PATH = os.path.join(BASE_DIR, "rag_config.local.json")  # 집/회사별 override (git 제외)


def _merge(base, over):
    """over 를 base 위에 병합. local/api 같은 중첩 dict 는 키 단위로 병합."""
    for k, v in over.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            nb = dict(base[k]); nb.update({kk: vv for kk, vv in v.items() if not kk.startswith("_")})
            base[k] = nb
        else:
            base[k] = v
    return base


def _load():
    cfg = dict(_DEFAULTS)
    # 1) 공용 rag_config.json (git 공유 기본값)
    if os.path.isfile(_CFG_PATH):
        try:
            with open(_CFG_PATH, encoding="utf-8") as f:
                cfg = _merge(cfg, json.load(f))
        except Exception as e:
            print(f"[config] rag_config.json 파싱 실패({e}) — 기본값 사용")
    # 2) rag_config.local.json (이 PC 전용 override — 집/회사 설정 분리. git 에 안 올림)
    if os.path.isfile(_LOCAL_PATH):
        try:
            with open(_LOCAL_PATH, encoding="utf-8") as f:
                cfg = _merge(cfg, json.load(f))
            print("[config] rag_config.local.json override 적용됨 (이 PC 전용 설정)")
        except Exception as e:
            print(f"[config] rag_config.local.json 파싱 실패({e}) — 무시")
    return cfg


CFG = _load()


def abspath(p):
    """rag_server 기준 상대경로를 절대경로로."""
    if not p:
        return p
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(BASE_DIR, p))


KNOWLEDGE_DIR = abspath(CFG["knowledge_dir"])
DB_PATH = abspath(os.path.join("data", "index.db"))
