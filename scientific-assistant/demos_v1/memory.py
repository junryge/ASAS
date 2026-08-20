"""demos_v1/memory.py — 대화가 잘려 나갈 때 오래 남을 것만 건져 둔다.

무엇이 문제였나
    컨텍스트가 차면 `_trim_history_for_context` 가 오래된 메시지를 그냥
    버린다(`msgs.pop(idx)`). 그 안에 있던 **결정·제약·관례**도 같이 사라진다.
    그래서 어제 정한 것을 오늘 다시 묻고, 모델은 같은 제안을 또 낸다.

무엇을 하나 (magic-context 의 세 동작을 우리 것으로 옮겼다)
    · **Capture**  — 버리기 직전 그 조각을 큐에 넣는다. 배경에서 LLM 이
                     "오래 갈 지식" 만 뽑아 기억으로 적는다.
    · **Consolidate** — 유휴 시간에 중복을 합치고 안 쓰이는 것을 삭힌다.
    · **Recall**   — 다음 대화에 관련 기억을 예산 안에서 넣어 준다.

왜 직접 만들었나
    원본(cortexkit/magic-context, MIT)은 OpenCode·Pi 플러그인이다. Bun/TS
    런타임이 필요하고, 로컬 임베딩 모델(~90MB)을 처음 쓸 때 내려받는다 —
    공장 망에는 둘 다 없다. 설계만 가져오고 구현은 우리 것으로 했다.

지켜야 할 것
    ★응답 경로를 막지 않는다. Capture 는 LLM 을 부르므로 큐에 넣기만 하고,
      뽑아내는 일은 예약 워커가 한다. 대화가 느려지면 안 쓰게 된다.
    ★새 의존성 없음. 기존 sqlite3 + (있으면) FTS5, 없으면 LIKE 로 내려간다.
    ★임베딩은 있으면 쓰고 없으면 키워드만으로 돈다 — 없다고 멈추지 않는다.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time
import uuid

# ★세션 DB(routes_sessions)와 **같은 폴더**에 둔다. 데이터가 두 군데로
#   흩어지면 백업·이관에서 한쪽이 조용히 빠진다.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "demos_data", "memory.db")

_lock = threading.RLock()
_READY = False

# 기억의 갈래 — 이 다섯 가지만 받는다.
# ★"오늘 무슨 얘기를 했나" 는 요약이지 기억이 아니다. 다음에 다시 쓸 수
#   있는 것만 남긴다. 갈래를 좁혀 두면 모델도 덜 헤맨다.
KINDS = {
    "결정": "이렇게 하기로 정했다",
    "제약": "이건 하면 안 된다 / 이런 한계가 있다",
    "관례": "우리는 늘 이렇게 한다",
    "사실": "변하지 않는 수치·이름·구조",
    "용어": "이 말은 여기서 이런 뜻이다",
}

MAX_TEXT = 300           # 기억 한 줄 길이 상한
MAX_PER_CHUNK = 8        # 조각 하나에서 최대 몇 개까지 뽑나
DEFAULT_TOP = 6          # 한 번에 넣어 줄 기억 수


# ══════════════════════════════════════════════════════════════
# 저장소
# ══════════════════════════════════════════════════════════════
def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def init() -> bool:
    """스키마 생성 (한 번만).

    ★FTS5 를 쓰지 않는다 — 한국어 복합어를 못 쪼개서(‘반송’ 으로 ‘반송시간’ 을
      못 찾는다) 정작 필요한 기억을 놓친다. 수백 개 규모라 전수 검사가 더
      정확하고 충분히 빠르다.
    """
    global _READY
    if _READY:
        return True
    with _lock:
        con = _connect()
        try:
            con.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    user_id   TEXT NOT NULL,
                    mid       TEXT NOT NULL,
                    kind      TEXT NOT NULL DEFAULT '사실',
                    text      TEXT NOT NULL,
                    why       TEXT NOT NULL DEFAULT '',
                    sid       TEXT NOT NULL DEFAULT '',
                    at        INTEGER NOT NULL DEFAULT 0,
                    hits      INTEGER NOT NULL DEFAULT 0,
                    last_hit  INTEGER NOT NULL DEFAULT 0,
                    dropped   INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (user_id, mid)
                )""")
            con.execute("CREATE INDEX IF NOT EXISTS ix_mem_user "
                        "ON memories(user_id, dropped, at DESC)")
            # 아직 뽑아내지 않은 조각 — 응답 경로를 막지 않으려고 큐로 둔다
            con.execute("""
                CREATE TABLE IF NOT EXISTS pending (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    sid     TEXT NOT NULL DEFAULT '',
                    body    TEXT NOT NULL,
                    at      INTEGER NOT NULL DEFAULT 0,
                    tries   INTEGER NOT NULL DEFAULT 0
                )""")
            con.commit()
        finally:
            con.close()
    _READY = True
    return True


def _now() -> int:
    return int(time.time())


def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


# ══════════════════════════════════════════════════════════════
# Capture — 1) 버리기 직전에 큐에 넣는다 (빠르다, LLM 안 부른다)
# ══════════════════════════════════════════════════════════════
def enqueue(user_id: str, sid: str, messages: list) -> int:
    """잘려 나갈 메시지들을 큐에 담는다. → 담은 글자 수.

    ★여기서 LLM 을 부르면 안 된다. 이 함수는 사용자가 질문을 보낸 직후,
      답이 나오기 전에 호출된다. 여기가 느려지면 대화 전체가 느려진다.
    """
    init()
    body = _msgs_to_text(messages)
    if len(body) < 40:            # 너무 짧으면 건질 게 없다
        return 0
    with _lock:
        con = _connect()
        try:
            con.execute("INSERT INTO pending(user_id, sid, body, at) VALUES(?,?,?,?)",
                        (str(user_id or ""), str(sid or ""), body, _now()))
            con.commit()
        finally:
            con.close()
    return len(body)


def _msgs_to_text(messages: list) -> str:
    out = []
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue
        c = m.get("content")
        if isinstance(c, list):                  # 멀티모달 — 글자만
            c = " ".join(p.get("text", "") for p in c
                         if isinstance(p, dict) and p.get("type") == "text")
        c = _norm(c)
        if c:
            out.append(("나" if role == "user" else "도우미") + ": " + c[:4000])
    return "\n".join(out)


def pending_count(user_id: str = "") -> int:
    init()
    con = _connect()
    try:
        if user_id:
            r = con.execute("SELECT COUNT(*) c FROM pending WHERE user_id=?",
                            (user_id,)).fetchone()
        else:
            r = con.execute("SELECT COUNT(*) c FROM pending").fetchone()
        return int(r["c"])
    finally:
        con.close()


def take_pending(limit: int = 1) -> list[dict]:
    """배경 작업이 처리할 조각을 꺼낸다 (오래된 것부터)."""
    init()
    con = _connect()
    try:
        rows = con.execute("SELECT * FROM pending ORDER BY id LIMIT ?",
                           (max(1, int(limit)),)).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def drop_pending(pid: int) -> None:
    with _lock:
        con = _connect()
        try:
            con.execute("DELETE FROM pending WHERE id=?", (pid,))
            con.commit()
        finally:
            con.close()


def bump_pending(pid: int) -> int:
    """실패했다. 시도 횟수를 올리고, 너무 많이 실패했으면 버린다.

    ★모델이 못 뽑는 조각(잡담뿐인 대화 등)이 큐 맨 앞에 박혀 있으면 뒤가
      영영 안 돈다. 세 번 해 보고 넘어간다.
    """
    with _lock:
        con = _connect()
        try:
            con.execute("UPDATE pending SET tries=tries+1 WHERE id=?", (pid,))
            r = con.execute("SELECT tries FROM pending WHERE id=?", (pid,)).fetchone()
            tries = int(r["tries"]) if r else 99
            if tries >= 3:
                con.execute("DELETE FROM pending WHERE id=?", (pid,))
            con.commit()
            return tries
        finally:
            con.close()


# ══════════════════════════════════════════════════════════════
# Capture — 2) 조각에서 기억을 뽑는다 (배경에서 LLM 호출)
# ══════════════════════════════════════════════════════════════
EXTRACT_PROMPT = """너는 대화에서 **나중에 다시 쓸 지식만** 골라내는 사서다.
출력은 오직 JSON 배열. 앞뒤 설명도, 코드펜스도 붙이지 마라.

무엇을 남기나 — 다음 다섯 갈래만:
  "결정" 이렇게 하기로 정했다
  "제약" 이건 하면 안 된다 / 이런 한계가 있다
  "관례" 우리는 늘 이렇게 한다
  "사실" 변하지 않는 수치·이름·구조
  "용어" 이 말은 여기서 이런 뜻이다

무엇을 버리나 (중요):
  · "무슨 얘기를 했다" 같은 **요약** — 그건 기억이 아니다
  · 그때만 맞는 것 (지금 몇 시다, 이번 파일 이름이 뭐다)
  · 인사·잡담·감탄
  · 모델이 스스로 한 제안 중 **사람이 받아들이지 않은 것**

형식 (각 항목):
  {"kind":"결정","text":"한 문장, 40자 안팎","why":"근거가 된 말 짧게"}

규칙:
  1. 최대 8개. 건질 게 없으면 빈 배열 [] 을 내라 — 억지로 채우지 마라.
  2. text 는 그 자체로 읽히게. "그거", "아까 그 파일" 같은 말 금지.
  3. 한국어로.
"""


def parse_extracted(raw, sid: str = "") -> list[dict]:
    """모델 출력 → 기억 목록. ★모델 출력은 못 믿는다. 살릴 것만 살린다."""
    if isinstance(raw, str):
        txt = raw.strip()
        m = re.search(r"```(?:json)?\s*(\[[\s\S]*\])\s*```", txt)
        if m:
            txt = m.group(1)
        else:
            i, j = txt.find("["), txt.rfind("]")
            if i >= 0 and j > i:
                txt = txt[i:j + 1]
        try:
            raw = json.loads(txt)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, list):
        return []

    out, seen = [], set()
    for it in raw[:MAX_PER_CHUNK * 2]:
        if isinstance(it, str):
            it = {"kind": "사실", "text": it}
        if not isinstance(it, dict):
            continue
        text = _norm(it.get("text"))[:MAX_TEXT]
        if len(text) < 4:
            continue
        key = re.sub(r"[^0-9a-z가-힣]+", "", text.lower())
        if not key or key in seen:
            continue
        seen.add(key)
        kind = str(it.get("kind") or "사실").strip()
        out.append({"kind": kind if kind in KINDS else "사실",
                    "text": text, "why": _norm(it.get("why"))[:200],
                    "sid": sid})
        if len(out) >= MAX_PER_CHUNK:
            break
    return out


def add(user_id: str, items: list[dict]) -> int:
    """기억을 적는다. 같은 내용은 다시 적지 않는다 → 새로 적은 개수."""
    init()
    if not items:
        return 0
    n = 0
    with _lock:
        con = _connect()
        try:
            have = {_key(r["text"]) for r in con.execute(
                "SELECT text FROM memories WHERE user_id=? AND dropped=0",
                (user_id,)).fetchall()}
            for it in items:
                k = _key(it["text"])
                if not k or k in have:
                    continue
                have.add(k)
                mid = uuid.uuid4().hex[:12]
                con.execute(
                    "INSERT INTO memories(user_id, mid, kind, text, why, sid, at)"
                    " VALUES(?,?,?,?,?,?,?)",
                    (user_id, mid, it.get("kind", "사실"), it["text"],
                     it.get("why", ""), it.get("sid", ""), _now()))
                n += 1
            con.commit()
        finally:
            con.close()
    return n


def _key(text: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", str(text or "").lower())


def all_memories(user_id: str, include_dropped: bool = False) -> list[dict]:
    init()
    con = _connect()
    try:
        q = "SELECT * FROM memories WHERE user_id=?"
        if not include_dropped:
            q += " AND dropped=0"
        q += " ORDER BY at DESC"
        return [dict(r) for r in con.execute(q, (user_id,)).fetchall()]
    finally:
        con.close()


def forget(user_id: str, mid: str) -> bool:
    """지우지 않고 접어 둔다 — 왜 사라졌냐는 물음에 답할 수 있어야 한다."""
    init()
    with _lock:
        con = _connect()
        try:
            cur = con.execute(
                "UPDATE memories SET dropped=1 WHERE user_id=? AND mid=?",
                (user_id, mid))
            con.commit()
            return cur.rowcount > 0
        finally:
            con.close()


# ══════════════════════════════════════════════════════════════
# Recall — 관련 기억 찾기
# ══════════════════════════════════════════════════════════════
# ★키워드로 후보를 고르고, 임베딩이 되면 그 후보만 다시 줄 세운다.
#   질문마다 임베딩을 부르는 건 응답 경로에 붙는 지연이라, 실패하거나
#   느리면 그냥 키워드 결과를 쓴다 — 멈추지 않는다.
_HANGUL = re.compile(r"[가-힣]")


# 한국어는 조사가 붙어 단어가 달라진다 — "반송이" 로는 "반송시간" 을 못 찾는다.
# 형태소 분석기 없이, 흔한 조사만 떼어 낸 형태를 같이 넣는다.
_JOSA = ("으로부터", "에서부터", "이라고", "으로는", "에게서", "이라는", "한테는",
         "으로", "에서", "에게", "한테", "보다", "처럼", "까지", "부터", "라고",
         "이랑", "만큼", "조차", "마저", "이나", "라도", "은", "는", "이", "가",
         "을", "를", "에", "의", "도", "만", "과", "와", "로", "랑", "야", "여")


def _tokens(q: str) -> list[str]:
    raw = re.findall(r"[0-9a-zA-Z]{2,}|[가-힣]{2,}", str(q or "").lower())
    out, seen = [], set()
    for t in raw[:24]:
        for v in (t, _strip_josa(t)):
            if v and len(v) >= 2 and v not in seen:
                seen.add(v)
                out.append(v)
    return out


def _strip_josa(t: str) -> str:
    """조사를 뗀 형태. 떼고 나면 너무 짧아지는 건 그대로 둔다."""
    if not _HANGUL.search(t):
        return t
    for j in _JOSA:
        if t.endswith(j) and len(t) - len(j) >= 2:
            return t[:-len(j)]
    return t


# 기억 자체를 묻는 말 — 걸릴 단어가 없는 게 당연하니 최근 것을 보여 준다
_META = re.compile(
    r"(지난|예전|이전|아까|전에|저번|어제|그때)\s*(대화|얘기|이야기|것|거)?"
    r"|기억(나|해|하|이|을|은|하고)|까먹|잊(어|었)|뭐라고\s*했|무슨\s*얘기"
    r"|정했|정한\s*(거|것)|알고\s*있")


def is_meta(query: str) -> bool:
    return bool(_META.search(str(query or "")))


def _kw_score(text: str, toks: list[str]) -> float:
    """★한글은 복합어로 붙는다 — '반송' 이 '반송지연' 안에 있다.
    하네스 라우터에서 배운 것과 같은 이유로, 한글은 부분 일치까지 본다."""
    t = str(text or "").lower()
    s = 0.0
    for tok in toks:
        if _HANGUL.search(tok):
            if tok in t:
                s += 2.0 if re.search(rf"(^|[^가-힣]){re.escape(tok)}([^가-힣]|$)", t) else 1.4
        else:
            if re.search(rf"\b{re.escape(tok)}\b", t):
                s += 2.0
            elif tok in t:
                s += 0.8
    return s


def search(user_id: str, query: str, top: int = DEFAULT_TOP,
           use_embed: bool = True, cfg: dict | None = None) -> list[dict]:
    """관련 기억 → 점수 높은 순. 아무것도 없으면 빈 목록."""
    init()
    toks = _tokens(query)
    con = _connect()
    try:
        # ★전수로 훑는다. FTS5(unicode61)는 한국어 복합어를 못 쪼갠다 —
        #   '반송' 으로 찾으면 '반송시간' 이 **0건** 이다(직접 확인). 접두
        #   검색으로 반쯤 되지만 중간에 낀 말은 여전히 못 찾는다.
        #   살아 있는 기억은 사용자당 수백 개(MAX_KEEP)라 전수가 더 정확하고
        #   충분히 빠르다. 인덱스를 늘리는 대신 정확도를 택했다.
        cands = [dict(r) for r in con.execute(
            "SELECT * FROM memories WHERE user_id=? AND dropped=0"
            " ORDER BY at DESC LIMIT 2000", (user_id,)).fetchall()]
    finally:
        con.close()
    if not cands:
        return []

    for c in cands:
        c["score"] = _kw_score(c["text"] + " " + (c.get("why") or ""), toks)
        # 자주 불려 나온 기억을 살짝 올린다 (쓰이는 것이 쓸모 있는 것)
        c["score"] += min(1.0, 0.15 * float(c.get("hits") or 0))

    hit = [c for c in cands if c["score"] > 0]
    # ★걸리는 게 없으면 **넣지 않는다.** 예전엔 최근 것을 그냥 밀어 넣었는데,
    #   그러면 "zzz" 같은 무관한 질문에도 기억이 끼어든다 — 잘못된 기억이
    #   모델을 자신 있게 틀리게 만드는 바로 그 경로다.
    #   딱 하나 예외: 기억 자체를 묻는 말("지난 대화 기억나?")은 걸릴 단어가
    #   없는 게 당연하다. 그때는 최근 것을 보여 준다.
    if not hit:
        if not is_meta(query):
            return []
        hit = sorted(cands, key=lambda c: -(c.get("at") or 0))[:40]
    pool = hit

    if use_embed and len(pool) > top:
        ranked = _embed_rank(query, pool, cfg)
        if ranked is not None:
            pool = ranked
        else:
            pool.sort(key=lambda c: (-c["score"], -(c.get("at") or 0)))
    else:
        pool.sort(key=lambda c: (-c["score"], -(c.get("at") or 0)))
    return pool[:max(1, int(top))]


def _embed_rank(query: str, pool: list[dict], cfg: dict | None):
    """임베딩으로 후보를 다시 줄 세운다. 못 하면 None (호출부가 키워드로)."""
    try:
        vq = embed([query], cfg)
        if not vq:
            return None
        texts = [c["text"] for c in pool]
        vs = embed(texts, cfg)
        if not vs or len(vs) != len(pool):
            return None
    except Exception:
        return None
    q = vq[0]
    for c, v in zip(pool, vs):
        c["sim"] = _cos(q, v)
        # 키워드와 의미를 섞는다 — 한쪽만 믿으면 둘 다의 약점을 그대로 먹는다
        c["score"] = c["score"] + 4.0 * c["sim"]
    pool.sort(key=lambda c: (-c["score"], -(c.get("at") or 0)))
    return pool


def _cos(a, b) -> float:
    n = min(len(a), len(b))
    if not n:
        return 0.0
    dot = sa = sb = 0.0
    for i in range(n):
        x, y = a[i], b[i]
        dot += x * y
        sa += x * x
        sb += y * y
    if sa <= 0 or sb <= 0:
        return 0.0
    return dot / ((sa ** 0.5) * (sb ** 0.5))


# ── 임베딩 ──
# 사내 게이트웨이에 bge-m3 / Qwen3-Embedding-8B 가 있다. 한국어는 bge-m3 가
# 낫다. ★없거나 느리면 그냥 키워드로 간다 — 여기서 막히면 채팅이 멈춘다.
EMBED_DEFAULTS = {"enabled": True, "model": "bge-m3",
                  "url": "", "timeout_s": 3.0, "max_batch": 64}


def embed_cfg(cfg: dict | None = None) -> dict:
    try:
        from demos_v1.config import _EXT_CONFIG
        ext = _EXT_CONFIG
    except Exception:
        ext = {}
    c = dict(EMBED_DEFAULTS)
    c.update((cfg or {}).get("embedding") or ext.get("embedding") or {})
    if not c.get("url"):
        # 채팅 URL 에서 엔드포인트만 갈아 끼운다 — 주소를 두 군데 적지 않으려고
        base = ""
        for m in (ext.get("models") or {}).values():
            u = str((m or {}).get("url") or "")
            if "/v1/chat/completions" in u:
                base = u.split("/v1/chat/completions")[0]
                break
        c["url"] = (base + "/v1/embeddings") if base else ""
    return c


def embed(texts: list[str], cfg: dict | None = None) -> list[list[float]] | None:
    """문장들 → 벡터들. 못 하면 None."""
    c = embed_cfg(cfg)
    if not c.get("enabled") or not c.get("url") or not texts:
        return None
    try:
        import requests
        from demos_v1.config import API_TOKEN
    except Exception:
        return None
    if not API_TOKEN:
        return None
    out: list[list[float]] = []
    step = max(1, int(c.get("max_batch", 64)))
    for i in range(0, len(texts), step):
        chunk = [str(t)[:2000] for t in texts[i:i + step]]
        try:
            r = requests.post(
                c["url"],
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {API_TOKEN}"},
                json={"model": c.get("model", "bge-m3"), "input": chunk},
                timeout=float(c.get("timeout_s", 3.0)), verify=False)
            if r.status_code != 200:
                return None
            data = r.json().get("data") or []
            if len(data) != len(chunk):
                return None
            out.extend([d.get("embedding") or [] for d in data])
        except Exception:
            return None
    return out if out and all(out) else None


def mark_used(user_id: str, mids: list[str]) -> None:
    """넣어 준 기억에 표시를 남긴다 — 안 쓰이는 것을 나중에 삭히려면 필요하다."""
    if not mids:
        return
    init()
    with _lock:
        con = _connect()
        try:
            now = _now()
            con.executemany(
                "UPDATE memories SET hits=hits+1, last_hit=? WHERE user_id=? AND mid=?",
                [(now, user_id, m) for m in mids])
            con.commit()
        finally:
            con.close()


def block(user_id: str, query: str, budget_chars: int = 1200,
          top: int = DEFAULT_TOP, cfg: dict | None = None) -> tuple[str, list[str]]:
    """시스템 프롬프트에 넣을 기억 블록 → (글, 쓴 기억 id들).

    ★예산을 넘기지 않는다. 기억이 컨텍스트를 먹어 정작 대화가 잘리면
      본말전도다.
    """
    hits = search(user_id, query, top=top, cfg=cfg)
    if not hits:
        return "", []
    lines, used, n = [], [], 0
    for h in hits:
        line = f"- [{h['kind']}] {h['text']}"
        if n + len(line) + 1 > budget_chars:
            break
        lines.append(line)
        used.append(h["mid"])
        n += len(line) + 1
    if not lines:
        return "", []
    head = ("═══════ 지난 대화에서 남긴 것 ═══════\n"
            "아래는 예전 대화에서 정해진 사실이다. 이미 정해진 것을 다시 묻지 말고,\n"
            "어긋나는 말을 하려면 먼저 그 사실을 짚어라. 관련 없으면 그냥 무시해라.\n")
    return head + "\n".join(lines), used


# ══════════════════════════════════════════════════════════════
# Consolidate — 유휴 시간에 정리
# ══════════════════════════════════════════════════════════════
# ★기억은 쌓이기만 하면 쓰레기가 된다. 같은 말이 열 줄로 늘어나면 검색이
#   그걸로 다 차 버리고, 정작 필요한 게 밀린다. 그렇다고 지우면 "왜
#   사라졌냐" 에 답할 수 없으니 접어 두기만 한다(dropped=1).
STALE_DAYS = 120         # 이만큼 안 불려 나오면 삭힌다
MAX_KEEP = 400           # 사용자당 살아 있는 기억 상한


_NUM = re.compile(r"\d+(?:\.\d+)?")


def _nums(s: str) -> set:
    return set(_NUM.findall(str(s or "")))


def _similar(a: str, b: str) -> float:
    """겹치는 정도 0~1. 형태소 분석기 없이 글자 2-gram 으로 본다.

    ★한국어는 조사가 붙어 단어가 조금씩 달라진다("임계값을"/"임계값은").
      단어 단위로 비교하면 같은 말을 다른 말로 센다.

    ★★숫자가 다르면 0 이다. 이 시스템에서 숫자는 곧 내용이다 —
      "임계값 0.30" 과 "임계값 0.25" 는 글자로는 거의 같지만 정반대 지시다.
      합쳐 버리면 임계값 하나가 조용히 사라진다. 글자 유사도만으로는
      이 둘(0.61)과 진짜 같은 말(0.50~0.67)을 가를 수 없어서 직접 확인했다.
    """
    if _nums(a) != _nums(b):
        return 0.0

    def grams(s):
        s = re.sub(r"[^0-9a-z가-힣]+", "", str(s or "").lower())
        return {s[i:i + 2] for i in range(len(s) - 1)} or ({s} if s else set())
    ga, gb = grams(a), grams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def consolidate(user_id: str, dup_at: float = 0.45,
                stale_days: int = STALE_DAYS,
                max_keep: int = MAX_KEEP) -> dict:
    """중복 병합 + 오래 안 쓰인 것 삭히기 + 상한 넘으면 정리.

    → {"merged": n, "stale": n, "trimmed": n, "left": n}
    """
    init()
    rows = all_memories(user_id)
    merged = stale = trimmed = 0
    now = _now()
    kill: list[str] = []

    # 1) 중복 — 오래된 쪽(먼저 적힌 쪽)을 남기고 뒤엣것을 접는다.
    #    ★남은 쪽에 hits 를 합쳐 준다. 안 그러면 자주 쓰이던 기억이
    #      중복 정리 한 번에 '안 쓰인 기억' 이 되어 다음 단계에서 삭는다.
    keep: list[dict] = []
    absorb: dict[str, int] = {}
    for r in sorted(rows, key=lambda r: r.get("at") or 0):
        twin = next((k for k in keep if _similar(k["text"], r["text"]) >= dup_at), None)
        if twin is None:
            keep.append(r)
        else:
            kill.append(r["mid"])
            absorb[twin["mid"]] = absorb.get(twin["mid"], 0) + int(r.get("hits") or 0)
            merged += 1

    # 2) 오래 안 쓰인 것 — 한 번도 안 불려 나온 채 오래된 것만
    cut = now - int(stale_days) * 86400
    for r in keep:
        if r["mid"] in kill:
            continue
        last = int(r.get("last_hit") or 0) or int(r.get("at") or 0)
        if last < cut and int(r.get("hits") or 0) == 0:
            kill.append(r["mid"])
            stale += 1

    # 3) 그래도 많으면 — 덜 쓰이고 오래된 것부터
    alive = [r for r in keep if r["mid"] not in kill]
    if len(alive) > max_keep:
        alive.sort(key=lambda r: (int(r.get("hits") or 0), int(r.get("at") or 0)))
        for r in alive[:len(alive) - max_keep]:
            kill.append(r["mid"])
            trimmed += 1

    if kill or absorb:
        with _lock:
            con = _connect()
            try:
                if kill:
                    con.executemany(
                        "UPDATE memories SET dropped=1 WHERE user_id=? AND mid=?",
                        [(user_id, m) for m in kill])
                for mid, add_hits in absorb.items():
                    if add_hits:
                        con.execute("UPDATE memories SET hits=hits+? "
                                    "WHERE user_id=? AND mid=?",
                                    (add_hits, user_id, mid))
                con.commit()
            finally:
                con.close()
    return {"merged": merged, "stale": stale, "trimmed": trimmed,
            "left": len(all_memories(user_id))}


def stats(user_id: str) -> dict:
    init()
    con = _connect()
    try:
        r = con.execute(
            "SELECT COUNT(*) n, SUM(dropped) d FROM memories WHERE user_id=?",
            (user_id,)).fetchone()
        by = con.execute(
            "SELECT kind, COUNT(*) n FROM memories"
            " WHERE user_id=? AND dropped=0 GROUP BY kind", (user_id,)).fetchall()
        return {"total": int(r["n"] or 0), "dropped": int(r["d"] or 0),
                "live": int(r["n"] or 0) - int(r["d"] or 0),
                "by_kind": {x["kind"]: int(x["n"]) for x in by},
                "pending": pending_count(user_id),
                "db": DB_PATH}
    finally:
        con.close()


# ══════════════════════════════════════════════════════════════
# 배경 일꾼 — 큐에서 꺼내 뽑고, 가끔 정리한다
# ══════════════════════════════════════════════════════════════
# ★뽑기는 LLM 호출이라 느리다. 그래서 응답 경로가 아니라 여기서 돈다.
#   느려도 아무도 기다리지 않는다.
TICK_SEC = 45
CONSOLIDATE_EVERY = 60 * 60      # 한 시간에 한 번
_worker_started = False
_last_consolidate = 0.0


def _default_chat(messages: list[dict], max_tokens: int = 1200):
    """예약 작업이 쓰는 것과 같은 게이트웨이·토큰을 쓴다 (새 배선 안 만든다)."""
    from demos_v1.routes_schedule import _complete
    return _complete("", messages, max_tokens)


def extract_once(chat=None) -> dict:
    """큐에서 하나 꺼내 기억으로 만든다 → {"got": n} / {"idle": True}."""
    rows = take_pending(1)
    if not rows:
        return {"idle": True}
    row = rows[0]
    chat = chat or _default_chat
    try:
        body, err = chat([{"role": "system", "content": EXTRACT_PROMPT},
                          {"role": "user", "content": row["body"][:12000]}], 1200)
    except Exception as e:
        body, err = "", f"{type(e).__name__}: {e}"
    if err or not (body or "").strip():
        n = bump_pending(row["id"])
        return {"error": err or "빈 응답", "tries": n}

    items = parse_extracted(body, sid=row.get("sid") or "")
    got = add(row["user_id"], items)
    drop_pending(row["id"])       # ★건질 게 없었어도 처리된 것이다. 다시 안 본다.
    return {"got": got, "found": len(items), "user": row["user_id"]}


def tick(chat=None, per_tick: int = 2) -> dict:
    """한 바퀴 — 몇 개 뽑고, 시간이 됐으면 정리한다."""
    global _last_consolidate
    out = {"extracted": 0, "consolidated": None}
    for _ in range(max(1, per_tick)):
        r = extract_once(chat)
        if r.get("idle"):
            break
        out["extracted"] += int(r.get("got") or 0)

    now = time.time()
    if now - _last_consolidate >= CONSOLIDATE_EVERY:
        _last_consolidate = now
        init()
        con = _connect()
        try:
            users = [r["user_id"] for r in con.execute(
                "SELECT DISTINCT user_id FROM memories WHERE dropped=0").fetchall()]
        finally:
            con.close()
        out["consolidated"] = {u: consolidate(u) for u in users}
    return out


def start_worker(chat=None) -> bool:
    """데몬 스레드 하나. 두 번 불러도 하나만 돈다."""
    global _worker_started
    if _worker_started:
        return False
    _worker_started = True

    def loop():
        while True:
            time.sleep(TICK_SEC)
            try:
                r = tick(chat)
                if r.get("extracted"):
                    print(f"  🧠 [기억] {r['extracted']}건 새로 적음")
            except Exception as e:      # 일꾼이 죽으면 기억이 영영 안 쌓인다
                print(f"  🧠 [기억] 일꾼 오류(계속): {e}")

    threading.Thread(target=loop, daemon=True).start()
    print(f"  🧠 기억 일꾼 시작 ({TICK_SEC}초 주기)")
    return True


# ══════════════════════════════════════════════════════════════
# 언제 담을 것인가
# ══════════════════════════════════════════════════════════════
# ★처음엔 '컨텍스트가 넘쳐 잘릴 때' 만 담았다. 그런데 API 모델은 128K 라
#   그런 일이 거의 없다 — 하루 종일 얘기해도 기억이 한 줄도 안 쌓인다.
#   그래서 **대화가 길어지면** 넘치기 전에도 담는다. 원본(magic-context)도
#   한도의 몇 % 에서 미리 도는 방식이다.
# ★담아도 대화에서 빼지는 않는다. 이건 '복사해 두기' 지 '자르기' 가 아니다.
KEEP_TAIL = 4            # 최근 이만큼은 아직 살아 있는 얘기라 안 담는다
CAPTURE_EVERY = 6        # 담지 않은 메시지가 이만큼 쌓이면 한 번 담는다


def _captured_upto(user_id: str, sid: str) -> int:
    init()
    con = _connect()
    try:
        con.execute("""CREATE TABLE IF NOT EXISTS captured (
                        user_id TEXT NOT NULL, sid TEXT NOT NULL,
                        upto INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (user_id, sid))""")
        r = con.execute("SELECT upto FROM captured WHERE user_id=? AND sid=?",
                        (user_id, sid)).fetchone()
        return int(r["upto"]) if r else 0
    finally:
        con.close()


def _set_captured(user_id: str, sid: str, upto: int) -> None:
    with _lock:
        con = _connect()
        try:
            con.execute("""CREATE TABLE IF NOT EXISTS captured (
                            user_id TEXT NOT NULL, sid TEXT NOT NULL,
                            upto INTEGER NOT NULL DEFAULT 0,
                            PRIMARY KEY (user_id, sid))""")
            con.execute("INSERT INTO captured(user_id, sid, upto) VALUES(?,?,?)"
                        " ON CONFLICT(user_id, sid) DO UPDATE SET upto=excluded.upto",
                        (user_id, sid, int(upto)))
            con.commit()
        finally:
            con.close()


def capture_if_long(user_id: str, sid: str, messages: list) -> int:
    """대화가 길어졌으면 아직 안 담은 앞부분을 담는다 → 담은 메시지 수.

    ★같은 대화를 매 턴 다시 담으면 안 된다. 어디까지 담았는지 기억해 둔다
      (안 그러면 큐가 같은 내용으로 가득 차고 LLM 값도 그만큼 나간다).
    """
    if not user_id:
        return 0
    init()
    turns = [m for m in (messages or [])
             if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
    end = max(0, len(turns) - KEEP_TAIL)
    done = _captured_upto(user_id, sid or "")
    if end - done < CAPTURE_EVERY:
        return 0
    chunk = turns[done:end]
    if enqueue(user_id, sid or "", chunk) <= 0:
        return 0
    _set_captured(user_id, sid or "", end)
    return len(chunk)
