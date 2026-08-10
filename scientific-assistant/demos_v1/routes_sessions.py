"""
demos_v1/routes_sessions.py — 대화 세션 서버 저장 + 전문검색 (SQLite FTS5)

왜 필요한가
    세션은 지금까지 브라우저 localStorage 에만 있었다. PC/브라우저를 바꾸면
    사라지고, 용량이 차면 오래된 것부터 잘려나간다("세션 저장 실패" 경고).
    이 모듈은 같은 세션을 서버에도 올려두고, 본문 전체를 검색하게 한다.

설계
    - localStorage 를 없애지 않는다. 서버는 '사본 + 검색 색인' 이다.
      기존 동작은 그대로 두고, 로그인한 사용자에 한해 사본을 올린다.
    - 저장소는 demos_data/sessions.db 하나. 사용자별 분리는 user_id 컬럼.
    - 검색은 FTS5. 없는 빌드면 LIKE 로 자동 강등한다(폐쇄망 파이썬 대비).
    - 헤르메스 sessions/*.jsonl 과는 목적이 다르다. 그쪽은 '회상용 메시지 로그',
      여기는 '세션 복원용 스냅샷'. 서로 건드리지 않는다.

엔드포인트
    POST   /api/sessions/sync            세션 1건 업서트 (body: {user_id, session})
    GET    /api/sessions?user_id=        목록 (id/name/updated_at/preview)
    GET    /api/sessions/<sid>?user_id=  전체 페이로드 (복원용)
    GET    /api/sessions/search?user_id=&q=   본문 전문검색 (snippet 포함)
    DELETE /api/sessions/<sid>?user_id=  삭제
    GET    /api/sessions/stat?user_id=   건수·용량·검색엔진 종류
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time

from flask import jsonify, request

from demos_v1.utils import BASE_DIR

DB_PATH = os.path.join(BASE_DIR, "demos_data", "sessions.db")

# 세션 1건 상한. msgsHtml(렌더된 HTML)이 커서 통째로는 무거워질 수 있다.
MAX_PAYLOAD = 2 * 1024 * 1024        # 2MB
MAX_BODY_CHARS = 200_000             # 검색 색인용 본문 상한
KEEP_PER_USER = 500                  # 사용자당 보관 세션 수 (넘치면 오래된 것부터)

_lock = threading.Lock()
_HAS_FTS = None


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def _init() -> bool:
    """스키마 생성. FTS5 가 있으면 True, 없으면 LIKE 폴백으로 False."""
    global _HAS_FTS
    if _HAS_FTS is not None:
        return _HAS_FTS
    with _lock:
        con = _connect()
        try:
            con.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    user_id    TEXT NOT NULL,
                    sid        TEXT NOT NULL,
                    name       TEXT NOT NULL DEFAULT '',
                    updated_at INTEGER NOT NULL DEFAULT 0,
                    archived   INTEGER NOT NULL DEFAULT 0,
                    msg_count  INTEGER NOT NULL DEFAULT 0,
                    preview    TEXT NOT NULL DEFAULT '',
                    body       TEXT NOT NULL DEFAULT '',
                    payload    TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (user_id, sid)
                )""")
            con.execute("CREATE INDEX IF NOT EXISTS ix_sessions_upd "
                        "ON sessions(user_id, updated_at DESC)")
            try:
                con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts "
                            "USING fts5(user_id UNINDEXED, sid UNINDEXED, name, body,"
                            " tokenize='unicode61')")
                _HAS_FTS = True
            except sqlite3.OperationalError:
                _HAS_FTS = False        # FTS5 없는 빌드 → LIKE 검색
            con.commit()
        finally:
            con.close()
    return _HAS_FTS


def _uid() -> str:
    """user_id 는 폴더/키로 쓰이므로 형태를 제한한다."""
    v = (request.args.get("user_id")
         or (request.get_json(silent=True) or {}).get("user_id") or "").strip()
    return v if v and "/" not in v and "\\" not in v and ".." not in v else ""


def _strip_html(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(s or ""))).strip()


def _body_of(sess: dict) -> str:
    """검색 색인용 본문 — history 의 사용자/모델 발화만 모은다."""
    parts = []
    for m in (sess.get("history") or []):
        if not isinstance(m, dict):
            continue
        c = m.get("content")
        if isinstance(c, str) and c.strip():
            parts.append(c)
        elif isinstance(c, list):        # 멀티모달 content 블록
            parts += [b.get("text", "") for b in c
                      if isinstance(b, dict) and b.get("text")]
    txt = "\n".join(parts)
    if not txt and sess.get("msgsHtml"):
        txt = _strip_html(sess["msgsHtml"])
    return txt[:MAX_BODY_CHARS]


def _preview(body: str) -> str:
    return (body or "").strip().replace("\n", " ")[:160]


def register_session_routes(app) -> bool:
    has_fts = _init()

    @app.route("/api/sessions/sync", methods=["POST"])
    def api_sessions_sync():
        """세션 1건 업서트. 브라우저가 저장할 때마다 같은 내용을 서버에도 올린다."""
        uid = _uid()
        if not uid:
            return jsonify({"error": "user_id 필요"}), 400
        data = request.get_json(silent=True) or {}
        sess = data.get("session") or {}
        sid = str(sess.get("id") or "").strip()
        if not sid:
            return jsonify({"error": "session.id 필요"}), 400

        body = _body_of(sess)
        payload = json.dumps(sess, ensure_ascii=False)
        dropped = ""
        if len(payload.encode("utf-8")) > MAX_PAYLOAD:
            # 렌더된 HTML 부터 버린다 — history 만 있어도 검색·요약은 된다
            slim = dict(sess)
            slim.pop("msgsHtml", None)
            payload = json.dumps(slim, ensure_ascii=False)
            dropped = "msgsHtml"
            if len(payload.encode("utf-8")) > MAX_PAYLOAD:
                return jsonify({"error": "세션이 너무 큽니다(2MB 초과)"}), 413

        row = (uid, sid, str(sess.get("name") or "새 세션"),
               int(sess.get("updatedAt") or time.time() * 1000),
               1 if sess.get("archived") else 0,
               len(sess.get("history") or []), _preview(body), body, payload)
        with _lock:
            con = _connect()
            try:
                con.execute(
                    "INSERT INTO sessions(user_id,sid,name,updated_at,archived,"
                    "msg_count,preview,body,payload) VALUES(?,?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(user_id,sid) DO UPDATE SET name=excluded.name,"
                    "updated_at=excluded.updated_at,archived=excluded.archived,"
                    "msg_count=excluded.msg_count,preview=excluded.preview,"
                    "body=excluded.body,payload=excluded.payload", row)
                if has_fts:
                    con.execute("DELETE FROM sessions_fts WHERE user_id=? AND sid=?",
                                (uid, sid))
                    con.execute("INSERT INTO sessions_fts(user_id,sid,name,body) "
                                "VALUES(?,?,?,?)", (uid, sid, row[2], body))
                _trim(con, uid)
                con.commit()
            finally:
                con.close()
        return jsonify({"ok": True, "sid": sid, "dropped": dropped,
                        "chars": len(body)})

    def _trim(con, uid: str) -> None:
        """사용자당 보관 수를 넘으면 오래된 세션부터 지운다."""
        old = [r["sid"] for r in con.execute(
            "SELECT sid FROM sessions WHERE user_id=? ORDER BY updated_at DESC "
            "LIMIT -1 OFFSET ?", (uid, KEEP_PER_USER))]
        for sid in old:
            con.execute("DELETE FROM sessions WHERE user_id=? AND sid=?", (uid, sid))
            if has_fts:
                con.execute("DELETE FROM sessions_fts WHERE user_id=? AND sid=?",
                            (uid, sid))

    @app.route("/api/sessions", methods=["GET"])
    def api_sessions_list():
        uid = _uid()
        if not uid:
            return jsonify({"sessions": []})
        limit = min(int(request.args.get("limit", 200) or 200), 500)
        con = _connect()
        try:
            rows = con.execute(
                "SELECT sid,name,updated_at,archived,msg_count,preview FROM sessions "
                "WHERE user_id=? ORDER BY updated_at DESC LIMIT ?",
                (uid, limit)).fetchall()
        finally:
            con.close()
        return jsonify({"sessions": [dict(r) for r in rows]})

    @app.route("/api/sessions/search", methods=["GET"])
    def api_sessions_search():
        """본문 전문검색. FTS5 가 있으면 snippet, 없으면 LIKE + 주변 문맥."""
        uid = _uid()
        q = (request.args.get("q") or "").strip()
        if not uid:
            return jsonify({"error": "user_id 필요"}), 400
        if not q:
            return jsonify({"results": [], "engine": "fts5" if has_fts else "like"})
        limit = min(int(request.args.get("limit", 30) or 30), 100)
        out = []
        con = _connect()
        try:
            if has_fts:
                # ① 사용자 입력을 그대로 MATCH 에 넣으면 문법 오류가 난다 → 따옴표로 감싼다
                # ② 한국어는 조사가 붙어 한 토큰이 된다('저장율' vs '저장율이').
                #    접두 검색(")*")을 붙여야 조사 붙은 말도 걸린다.
                terms = [t.replace('"', "") for t in re.findall(r"[^\s\"']+", q)]
                expr = " ".join('"%s"*' % t for t in terms if t)
                try:
                    rows = con.execute(
                        "SELECT f.sid, f.name, snippet(sessions_fts,3,'<em>','</em>','…',18) AS snip, "
                        "  s.updated_at, s.msg_count "
                        "FROM sessions_fts f JOIN sessions s "
                        "  ON s.user_id=f.user_id AND s.sid=f.sid "
                        "WHERE f.user_id=? AND sessions_fts MATCH ? "
                        "ORDER BY bm25(sessions_fts) LIMIT ?",
                        (uid, expr, limit)).fetchall()
                    out = [dict(r) for r in rows]
                except sqlite3.OperationalError:
                    out = []
            if not out:
                # 폴백(또는 FTS 무소득) — 낱말마다 LIKE AND. 통짜 문자열로 걸면
                # '저장율 Queue' 처럼 떨어져 있는 말이 영영 안 걸린다.
                words = [w for w in re.split(r"\s+", q) if w][:6] or [q]
                cond = " AND ".join(["(body LIKE ? OR name LIKE ?)"] * len(words))
                args = []
                for w in words:
                    like = "%" + w.replace("%", "").replace("_", "") + "%"
                    args += [like, like]
                rows = con.execute(
                    "SELECT sid,name,updated_at,msg_count,body FROM sessions "
                    "WHERE user_id=? AND " + cond + " ORDER BY updated_at DESC LIMIT ?",
                    [uid] + args + [limit]).fetchall()
                for r in rows:
                    d = dict(r)
                    b = d.pop("body", "") or ""
                    i = b.lower().find(words[0].lower())
                    d["snip"] = (b[max(0, i - 60):i + 120] if i >= 0 else b[:160]).strip()
                    out.append(d)
        finally:
            con.close()
        return jsonify({"results": out, "engine": "fts5" if has_fts else "like",
                        "count": len(out)})

    @app.route("/api/sessions/stat", methods=["GET"])
    def api_sessions_stat():
        uid = _uid()
        con = _connect()
        try:
            n = con.execute("SELECT COUNT(*) c FROM sessions WHERE user_id=?",
                            (uid,)).fetchone()["c"] if uid else 0
            total = con.execute("SELECT COUNT(*) c FROM sessions").fetchone()["c"]
        finally:
            con.close()
        return jsonify({"engine": "fts5" if has_fts else "like", "mine": n,
                        "all": total, "db": DB_PATH,
                        "size": os.path.getsize(DB_PATH) if os.path.isfile(DB_PATH) else 0})

    @app.route("/api/sessions/<sid>", methods=["GET"])
    def api_sessions_get(sid):
        uid = _uid()
        if not uid:
            return jsonify({"error": "user_id 필요"}), 400
        con = _connect()
        try:
            r = con.execute("SELECT payload FROM sessions WHERE user_id=? AND sid=?",
                            (uid, sid)).fetchone()
        finally:
            con.close()
        if not r:
            return jsonify({"error": "없는 세션"}), 404
        try:
            return jsonify({"session": json.loads(r["payload"])})
        except json.JSONDecodeError:
            return jsonify({"error": "세션 데이터 손상"}), 500

    @app.route("/api/sessions/<sid>", methods=["DELETE"])
    def api_sessions_delete(sid):
        uid = _uid()
        if not uid:
            return jsonify({"error": "user_id 필요"}), 400
        with _lock:
            con = _connect()
            try:
                con.execute("DELETE FROM sessions WHERE user_id=? AND sid=?", (uid, sid))
                if has_fts:
                    con.execute("DELETE FROM sessions_fts WHERE user_id=? AND sid=?",
                                (uid, sid))
                con.commit()
            finally:
                con.close()
        return jsonify({"ok": True})

    return has_fts
