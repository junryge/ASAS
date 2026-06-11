"""rag_server/embedder.py — 임베딩 백엔드 (교체형).

- local : bge-m3 GGUF (llama-cpp, CPU). 채팅이 API라 GPU 안 씀.
- api   : 사내 /v1/embeddings (requests)
- none  : 임베딩 없음 → 서버는 lexical(BM25+청킹) 모드

공통: embed(texts)->list[vec] (L2 정규화). available 로 가용성 확인.
모델/엔드포인트 부재·로드실패 시 available=False → 서버는 계속 동작.
"""
import os
import math
import threading

from config import CFG, abspath


def _l2norm(v):
    s = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / s for x in v]


def _flatten_pool(vec):
    """llama-cpp .embed 결과가 토큰단위([[...],...])면 평균풀링 → 단일 벡터."""
    if vec and isinstance(vec[0], (list, tuple)):
        n = len(vec)
        dim = len(vec[0])
        out = [0.0] * dim
        for row in vec:
            for i in range(dim):
                out[i] += row[i]
        return [x / n for x in out]
    return list(vec)


class _Base:
    available = False
    dim = 0
    name = "none"
    def embed(self, texts):
        raise NotImplementedError


class NoneEmbedder(_Base):
    name = "none"


class LocalEmbedder(_Base):
    name = "local"
    def __init__(self, conf):
        self._lock = threading.Lock()
        self._llm = None
        self.available = False
        self.dim = 0
        path = abspath(conf.get("model_path", ""))
        if not path or not os.path.isfile(path):
            print(f"[embedder] local 모델 없음: {path} → lexical 모드")
            return
        try:
            from llama_cpp import Llama
            kw = dict(
                model_path=path, embedding=True,
                n_ctx=int(conf.get("n_ctx", 2048)),
                n_gpu_layers=int(conf.get("n_gpu_layers", 0)),
                n_threads=(int(conf["n_threads"]) or None) if conf.get("n_threads") else None,
                n_batch=int(conf.get("n_batch", 64)),
                verbose=False,
            )
            # 임베딩 모델 평균풀링 — 일부 버전은 pooling_type 미설정 시 .embed() 가 거부함
            try:
                from llama_cpp import LLAMA_POOLING_TYPE_MEAN
                kw["pooling_type"] = LLAMA_POOLING_TYPE_MEAN
            except Exception:
                pass
            self._llm = Llama(**kw)
            probe = self._raw_embed("warmup")
            self.dim = len(probe)
            self.available = self.dim > 0
            print(f"[embedder] local bge-m3 로드 OK (dim={self.dim}, CPU) — {os.path.basename(path)}")
        except Exception as e:
            print(f"[embedder] local 로드 실패({e}) → lexical 모드")

    def _raw_embed(self, text):
        """버전 호환: create_embedding(표준) 우선, 실패 시 embed() 폴백. 단일 벡터(평균풀링) 반환."""
        t = text or " "
        # 1순위: OpenAI 스타일 create_embedding (일부 버전 .embed() 버그 우회)
        try:
            r = self._llm.create_embedding(t)
            emb = r["data"][0]["embedding"]
            return _flatten_pool(emb)
        except Exception:
            pass
        # 2순위: embed()
        return _flatten_pool(self._llm.embed(t))

    def embed(self, texts):
        out = []
        with self._lock:
            for t in texts:
                out.append(_l2norm(self._raw_embed(t)))
        return out


class ApiEmbedder(_Base):
    name = "api"
    def __init__(self, conf):
        self.available = False
        self.url = (conf.get("url") or "").rstrip("/")
        self.model = conf.get("model", "bge-m3")
        self.timeout = int(conf.get("timeout_s", 30))
        self.dim = 0
        tok = ""
        tf = conf.get("token_file") or ""
        if tf and os.path.isfile(abspath(tf)):
            tok = open(abspath(tf), encoding="utf-8-sig").read().strip()
        self.headers = {"Content-Type": "application/json"}
        if tok:
            self.headers["Authorization"] = "Bearer " + tok
        if not self.url:
            print("[embedder] api url 미설정 → lexical 모드")
            return
        try:
            import requests  # noqa
            probe = self.embed(["warmup"])
            self.dim = len(probe[0]) if probe and probe[0] else 0
            self.available = self.dim > 0
            print(f"[embedder] api 임베딩 OK (dim={self.dim}) — {self.url}")
        except Exception as e:
            print(f"[embedder] api 임베딩 실패({e}) → lexical 모드")

    def embed(self, texts):
        import requests
        r = requests.post(self.url, headers=self.headers,
                          json={"model": self.model, "input": list(texts)},
                          timeout=self.timeout)
        r.raise_for_status()
        data = r.json().get("data", [])
        return [_l2norm(d["embedding"]) for d in data]


def build_embedder():
    backend = (CFG.get("embed_backend") or "none").lower()
    try:
        if backend == "local":
            return LocalEmbedder(CFG.get("local", {}))
        if backend == "api":
            return ApiEmbedder(CFG.get("api", {}))
    except Exception as e:
        print(f"[embedder] build 실패({e}) → none")
    return NoneEmbedder()
