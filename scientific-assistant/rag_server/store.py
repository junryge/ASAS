"""rag_server/store.py — SQLite 인덱스 + mtime 증분 재인덱싱.

knowledge/<user>/*.md 를 청킹+임베딩해서 보관.
- files(user_id, filename, mtime, chunk_count)
- chunks(id, user_id, filename, heading, text, tf_json, token_count, embedding BLOB)
임베딩은 L2 정규화 후 array('f').tobytes() 로 저장 (코사인=내적).
토크나이저/BM25 토큰은 demos_v1/knowledge.py 와 동일 규칙.
"""
import os
import re
import json
import array
import sqlite3
import threading

from config import KNOWLEDGE_DIR, DB_PATH, CFG

_TOKEN_RE = re.compile(r"[가-힣]{2,}|[a-z0-9_]{2,}")
_lock = threading.Lock()
_conn = None


def tokenize(text):
    return _TOKEN_RE.findall((text or "").lower())


def _tf(tokens):
    d = {}
    for t in tokens:
        d[t] = d.get(t, 0) + 1
    return d


def conn():
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.executescript("""
        CREATE TABLE IF NOT EXISTS files(
          user_id TEXT, filename TEXT, mtime REAL, chunk_count INT,
          PRIMARY KEY(user_id, filename));
        CREATE TABLE IF NOT EXISTS chunks(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id TEXT, filename TEXT, heading TEXT, text TEXT,
          tf_json TEXT, token_count INT, embedding BLOB);
        CREATE INDEX IF NOT EXISTS idx_chunks_user ON chunks(user_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(user_id, filename);
        """)
        _conn.commit()
    return _conn


def vec_to_blob(vec):
    return array.array("f", vec).tobytes() if vec else None


def blob_to_vec(blob):
    if not blob:
        return None
    a = array.array("f")
    a.frombytes(blob)
    return a  # array 는 인덱싱/내적에 그대로 사용 가능


def _user_dir(user_id):
    return os.path.join(KNOWLEDGE_DIR, user_id)


def _index_file(user_id, filename, chunker, embedder):
    """단일 파일 청킹+임베딩 후 DB 갱신 (기존 청크 삭제 후 재삽입)."""
    path = os.path.join(_user_dir(user_id), filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return 0
    _meta, body = chunker.parse_frontmatter(content)
    chs = chunker.chunk_markdown(body, CFG["chunk_size"], CFG["chunk_overlap"], CFG["chunk_min"])
    vecs = [None] * len(chs)
    if embedder is not None and getattr(embedder, "available", False) and chs:
        try:
            vecs = embedder.embed([c["text"] for c in chs])
        except Exception as e:
            print(f"[store] 임베딩 실패({filename}): {e} — 이 파일은 lexical만")
            vecs = [None] * len(chs)
    c = conn()
    with _lock:
        c.execute("DELETE FROM chunks WHERE user_id=? AND filename=?", (user_id, filename))
        for ch, v in zip(chs, vecs):
            toks = tokenize(ch["text"])
            c.execute(
                "INSERT INTO chunks(user_id,filename,heading,text,tf_json,token_count,embedding) "
                "VALUES(?,?,?,?,?,?,?)",
                (user_id, filename, ch["heading"], ch["text"],
                 json.dumps(_tf(toks)), len(toks), vec_to_blob(v)))
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = 0
        c.execute("INSERT OR REPLACE INTO files(user_id,filename,mtime,chunk_count) VALUES(?,?,?,?)",
                  (user_id, filename, mtime, len(chs)))
        c.commit()
    return len(chs)


def sync_user(user_id, chunker, embedder, force=False):
    """mtime 비교로 변경/신규 파일만 재인덱싱, 삭제 파일 정리. 변경 여부 반환."""
    d = _user_dir(user_id)
    c = conn()
    cur = {r[0]: r[1] for r in c.execute(
        "SELECT filename, mtime FROM files WHERE user_id=?", (user_id,))}
    disk = {}
    if os.path.isdir(d):
        for fn in os.listdir(d):
            if fn.lower().endswith((".md", ".txt")):
                try:
                    disk[fn] = os.path.getmtime(os.path.join(d, fn))
                except OSError:
                    pass
    changed = False
    for fn, mt in disk.items():
        if force or fn not in cur or abs(cur[fn] - mt) > 1e-6:
            _index_file(user_id, fn, chunker, embedder)
            changed = True
    for fn in list(cur):
        if fn not in disk:
            with _lock:
                c.execute("DELETE FROM chunks WHERE user_id=? AND filename=?", (user_id, fn))
                c.execute("DELETE FROM files WHERE user_id=? AND filename=?", (user_id, fn))
                c.commit()
            changed = True
    return changed


def list_users():
    d = KNOWLEDGE_DIR
    if not os.path.isdir(d):
        return []
    return [u for u in os.listdir(d) if os.path.isdir(os.path.join(d, u))]


def fetch_chunks(user_id, files=None):
    """검색 후보 청크 로드. files 지정 시 해당 파일만."""
    c = conn()
    if files:
        q = "SELECT id,filename,heading,text,tf_json,token_count,embedding FROM chunks " \
            "WHERE user_id=? AND filename IN (%s)" % ",".join("?" * len(files))
        rows = c.execute(q, (user_id, *files)).fetchall()
    else:
        rows = c.execute(
            "SELECT id,filename,heading,text,tf_json,token_count,embedding FROM chunks WHERE user_id=?",
            (user_id,)).fetchall()
    out = []
    for r in rows:
        out.append({"id": r[0], "filename": r[1], "heading": r[2], "text": r[3],
                    "tf": json.loads(r[4]) if r[4] else {}, "tok": r[5],
                    "vec": blob_to_vec(r[6])})
    return out


def stats():
    c = conn()
    nu = c.execute("SELECT COUNT(DISTINCT user_id) FROM files").fetchone()[0]
    nc = c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    ne = c.execute("SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL").fetchone()[0]
    return {"users": nu, "chunks": nc, "embedded_chunks": ne}
