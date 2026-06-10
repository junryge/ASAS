"""rag_server/search.py — 하이브리드 검색 (BM25 + 코사인, RRF 융합).

- BM25: knowledge.py 와 동일 파라미터(k1=1.5, b=0.75) + substring 보너스(언더스코어 식별자 대응)
- 벡터: 임베딩 가능 시 질의 임베딩 vs 청크 임베딩 코사인(=정규화 내적, 순수 파이썬)
- 융합: RRF score = Σ 1/(60+rank) — 스케일 정규화 불필요, 견고
임베딩 없으면 BM25 단독.
"""
import math
import time

import store
from config import CFG

K1, B = 1.5, 0.75
RRF_K = 60


def _bm25_scores(cands, q_terms):
    N = len(cands)
    if not N or not q_terms:
        return [0.0] * N
    avgdl = sum(c["tok"] for c in cands) / max(1, N)
    df = {}
    for c in cands:
        for t in set(c["tf"].keys()):
            df[t] = df.get(t, 0) + 1
    qset = set(q_terms)
    scores = []
    for c in cands:
        s = 0.0
        dl = c["tok"] or 1
        for t in qset:
            f = c["tf"].get(t, 0)
            if f:
                idf = math.log(1 + (N - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))
                s += idf * (f * (K1 + 1)) / (f + K1 * (1 - B + B * dl / avgdl))
        # substring 보너스 (예: 'sla' 가 'transport4minoverratio' 토큰 안에)
        low = c["text"].lower()
        for t in qset:
            if len(t) >= 3 and t not in c["tf"] and t in low:
                s += low.count(t) * 0.6
        scores.append(s)
    return scores


def _dot(a, b):
    # a,b 는 array('f') (정규화됨) → 코사인 = 내적
    n = min(len(a), len(b))
    s = 0.0
    for i in range(n):
        s += a[i] * b[i]
    return s


def _rank_map(scores):
    """점수 → {index: rank(0이 최고)} (점수>0 인 것만)."""
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    rm = {}
    for rank, i in enumerate(order):
        if scores[i] > 0:
            rm[i] = rank
    return rm


def search(user_id, query, chunker, embedder, top_k=None, max_chars=None, files=None):
    t0 = time.time()
    top_k = top_k or CFG["default_top_k"]
    max_chars = max_chars or CFG["default_max_chars"]

    store.sync_user(user_id, chunker, embedder)
    cands = store.fetch_chunks(user_id, files=files)
    if not cands:
        return {"mode": _mode(embedder), "results": [], "elapsed_ms": int((time.time() - t0) * 1000)}

    q_terms = store.tokenize(query)
    bm = _bm25_scores(cands, q_terms)
    bm_rank = _rank_map(bm)

    use_vec = embedder is not None and getattr(embedder, "available", False) \
        and any(c["vec"] is not None for c in cands)
    vec_rank = {}
    if use_vec:
        # 후보 제한: 너무 많으면 BM25 상위만 코사인
        idxs = list(range(len(cands)))
        if not files and len(cands) > CFG["vector_candidate_limit"]:
            idxs = sorted(idxs, key=lambda i: bm[i], reverse=True)[:CFG["bm25_prefilter_top"]]
        try:
            qv = embedder.embed([query])[0]
            vscores = {}
            for i in idxs:
                v = cands[i]["vec"]
                vscores[i] = _dot(qv, v) if v is not None else 0.0
            order = sorted(vscores, key=lambda i: vscores[i], reverse=True)
            for rank, i in enumerate(order):
                if vscores[i] > 0:
                    vec_rank[i] = rank
        except Exception as e:
            print(f"[search] 질의 임베딩 실패: {e} — BM25 단독")
            use_vec = False

    # RRF 융합
    fused = {}
    for i, rk in bm_rank.items():
        fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + rk)
    for i, rk in vec_rank.items():
        fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + rk)
    if not fused:  # 둘 다 0 → BM25 원점수로라도
        fused = {i: bm[i] for i in range(len(cands)) if bm[i] > 0}

    ranked = sorted(fused, key=lambda i: fused[i], reverse=True)[:max(top_k * 3, top_k)]

    # 결과 조립: 같은 파일 인접 청크 묶고 max_chars 패킹
    results, total = [], 0
    for i in ranked:
        c = cands[i]
        text = c["text"]
        if total + len(text) > max_chars and results:
            continue
        results.append({
            "filename": c["filename"], "heading": c["heading"], "text": text,
            "score": round(fused[i], 5),
            "lex_rank": bm_rank.get(i, -1), "vec_rank": vec_rank.get(i, -1),
        })
        total += len(text)
        if len(results) >= top_k or total >= max_chars:
            break
    return {"mode": _mode(embedder, use_vec), "results": results,
            "elapsed_ms": int((time.time() - t0) * 1000)}


def _mode(embedder, used=None):
    if embedder is not None and getattr(embedder, "available", False):
        return "hybrid" if used is None or used else "lexical"
    return "lexical"
