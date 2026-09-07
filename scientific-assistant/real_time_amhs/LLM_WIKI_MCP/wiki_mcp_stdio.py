#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""위키 MCP — **stdio · 표준 라이브러리만**. 아바타가 직접 띄운다.

왜 이걸 또 만드나 (amhs-llm-wiki/mcp_server.py 가 이미 있는데)
    그쪽은 공식 SDK(FastMCP) 로 streamable-http 를 쓴다. 좋은 서버인데
    현장에서 세 번 걸렸다:

      ① 사람이 **따로 띄워야** 한다 — 안 띄우면 아바타가 붙을 데가 없다
      ② 포트를 헷갈린다 — 위키는 프로세스가 둘이다(웹앱 :8100 · MCP :8020).
        웹앱 주소를 넣으면 Flask 가 HTML 404 를 준다. 실제로 이걸로 한나절
        헤맸다: "이 주소는 MCP 서버가 아닙니다 (HTML 404)"
      ③ `pip install "mcp>=1.27,<2"` 가 필요하다 — 폐쇄망에서 반입이 일이다

    이 파일은 셋 다 없앤다. 아바타가 **자식 프로세스로 띄우므로** 사람이
    띄울 것도, 포트도, 설치할 것도 없다. 요청이력(qa/mcp_server.py)과
    같은 방식이다 — 거기서 이미 잘 돌고 있다.

무엇을 읽나
    위키 DB(data/wiki.db)를 **직접** 읽는다. 웹앱(app.py)이 꺼져 있어도 된다.
    검색 순위(tokenize · BM25)는 app.py 의 것을 **그대로** 옮겼다 —
    화면에서 검색한 순서와 서윤이 보는 순서가 다르면 안 된다.

    ★읽기 전용이다. 페이지를 만들거나 고치는 도구는 없다.

DB 를 어디서 찾나 (순서대로 · 있는 것을 쓴다)
    ① 환경변수 WIKI_DB
    ② 환경변수 LLM_WIKI_DATA 아래 wiki.db
    ③ 이 파일 옆의 data/wiki.db            ← 현장 배치가 이렇다
    ④ 이 파일 옆의 amhs-llm-wiki/data/wiki.db
  ★③ 을 빼먹으면 안 된다. 현장에서는 mcp_server.py 를 LLM_WIKI_MCP 바로
    아래에 두고 돌린다 (콘솔에 …\LLM_WIKI_MCP\data\wiki.db 로 찍힌다).

혼자 확인
    python wiki_mcp_stdio.py --check
"""
import json
import math
import os
import re
import sqlite3
import sys
from collections import Counter

PROTO = "2025-06-18"
NAME, VERSION = "llm-wiki", "1.0.0"

# 한 번에 실어 보낼 양 — 프롬프트 예산이 있다. 아바타 쪽에서도 한 번 더 자른다.
SNIPPET = 500
BODY_MAX = int(os.environ.get("WIKI_BODY_MAX", "6000"))
SRC_MAX = int(os.environ.get("WIKI_SRC_MAX", "20000"))


def db_path():
    p = (os.environ.get("WIKI_DB") or "").strip()
    if p:
        return p
    data = (os.environ.get("LLM_WIKI_DATA") or "").strip()
    if data:
        return os.path.join(data, "wiki.db")
    here = os.path.dirname(os.path.abspath(__file__))
    tries = [os.path.join(here, "data", "wiki.db"),
             os.path.join(here, "amhs-llm-wiki", "data", "wiki.db")]
    for t in tries:
        if os.path.isfile(t):
            return t
    return tries[0]          # 없으면 첫째를 가리켜 놓고 그 자리를 말해 준다


def _connect():
    p = db_path()
    if not os.path.isfile(p):
        raise FileNotFoundError(
            "위키 DB 가 없다: {}\n"
            "  · 위키를 한 번이라도 띄웠나? (amhs-llm-wiki 에서 python app.py)\n"
            "  · 다른 자리에 있으면 환경변수로 준다: WIKI_DB=<...>/wiki.db"
            .format(p))
    # 읽기 전용으로 연다 — 이 프로세스가 위키를 건드릴 일은 없다
    c = sqlite3.connect("file:{}?mode=ro".format(p), uri=True, timeout=5)
    c.row_factory = sqlite3.Row
    return c


# ── 검색 — app.py 의 tokenize / bm25_search 를 그대로 옮겼다 ────────────────
#    ★고쳐 쓰면 안 된다. 화면에서 검색한 순서와 서윤이 받는 순서가 달라지면,
#      "화면엔 이게 위에 뜨는데 왜 딴소리냐" 가 된다.
def tokenize(text):
    toks = []
    for m in re.findall(r"[0-9A-Za-z_]+|[가-힣]+", (text or "").lower()):
        toks.append(m)
        if re.match(r"[가-힣]", m) and len(m) > 1:
            toks.extend(m[i:i + 2] for i in range(len(m) - 1))
    return toks


def bm25_search(query, docs, k=10):
    q = set(tokenize(query))
    if not q or not docs:
        return []
    dtoks, df = [], Counter()
    for d in docs:
        t = tokenize((d["title"] + " ") * 3 + (d.get("text") or ""))
        dtoks.append(t)
        for w in set(t):
            df[w] += 1
    N = len(docs)
    avgdl = max(1.0, sum(len(t) for t in dtoks) / N)
    k1, b = 1.5, 0.75
    scored = []
    for i, t in enumerate(dtoks):
        tf = Counter(t)
        dl = len(t) or 1
        s = 0.0
        for w in q:
            f = tf.get(w, 0)
            if not f:
                continue
            idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
            s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * dl / avgdl))
        if s > 0:
            scored.append((s, docs[i]))
    scored.sort(key=lambda x: -x[0])
    return scored[:k]


def _docs(conn, domain_id=None):
    """검색 대상 — 페이지 + 소스(추출 텍스트)."""
    out = []
    q = ("SELECT p.id,p.title,p.summary,p.body_md,p.tags,d.name dname "
         "FROM pages p JOIN domains d ON d.id=p.domain_id")
    a = []
    if domain_id:
        q += " WHERE p.domain_id=?"
        a.append(domain_id)
    for r in conn.execute(q, a):
        out.append({"id": r["id"], "kind": "page", "title": r["title"],
                    "domain": r["dname"], "summary": r["summary"] or "",
                    "text": "{} {} {}".format(r["summary"] or "",
                                              r["tags"] or "",
                                              r["body_md"] or "")})
    q = ("SELECT s.id,s.filename,s.description,s.extracted_text,d.name dname "
         "FROM sources s JOIN domains d ON d.id=s.domain_id")
    a = []
    if domain_id:
        q += " WHERE s.domain_id=?"
        a.append(domain_id)
    for r in conn.execute(q, a):
        out.append({"id": r["id"], "kind": "source", "title": r["filename"] or "",
                    "domain": r["dname"], "summary": r["description"] or "",
                    "text": "{} {}".format(r["description"] or "",
                                           r["extracted_text"] or "")})
    return out


def _cut(s, n):
    s = str(s or "")
    return s if len(s) <= n else s[:n] + "\n…(뒤가 잘렸다 · 전체 {}자)".format(len(s))


# ── 도구 ──────────────────────────────────────────────────────────────────
TOOLS = [
    {"name": "listDomains",
     "description": "담당(도메인) 목록과 페이지·소스 개수.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "searchWiki",
     "description": ("위키 페이지·소스를 검색한다 (BM25). query 는 한국어/영문 "
                     "자연어 또는 키워드. domainSlug 로 한 담당만 볼 수 있다."),
     "inputSchema": {"type": "object", "required": ["query"], "properties": {
         "query": {"type": "string"},
         "topK": {"type": "integer"},
         "domainSlug": {"type": "string"}}}},
    {"name": "readPage",
     "description": "위키 페이지 본문(마크다운). searchWiki 의 kind='page' id 를 쓴다.",
     "inputSchema": {"type": "object", "required": ["pageId"], "properties": {
         "pageId": {"type": "integer"}}}},
    {"name": "listSources",
     "description": "업로드된 소스(원본 자료) 목록.",
     "inputSchema": {"type": "object", "properties": {
         "domainSlug": {"type": "string"}}}},
    {"name": "wikiWords",
     "description": ("이 위키에 무엇이 들어 있는지 **낱말로** 알려준다 "
                     "(페이지 제목·태그). 아바타가 '어떤 질문에 위키를 뒤질까' "
                     "를 정할 때 쓴다 — 문서를 새로 넣으면 낱말도 같이 는다."),
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "readSource",
     "description": "소스의 추출 텍스트 (이미지는 설명만).",
     "inputSchema": {"type": "object", "required": ["sourceId"], "properties": {
         "sourceId": {"type": "integer"},
         "maxChars": {"type": "integer"}}}},
]


def t_domains(_a):
    with _connect() as c:
        rows = c.execute(
            "SELECT d.*, (SELECT COUNT(*) FROM pages p WHERE p.domain_id=d.id) pc,"
            " (SELECT COUNT(*) FROM sources s WHERE s.domain_id=d.id) sc "
            "FROM domains d ORDER BY d.id").fetchall()
    if not rows:
        return "담당이 하나도 없다 (위키가 비었다)."
    return "\n".join("· {} ({}) — 페이지 {} · 소스 {}"
                     .format(r["name"], r["slug"], r["pc"], r["sc"])
                     for r in rows)


def _domain_id(c, slug):
    if not slug:
        return None
    r = c.execute("SELECT id FROM domains WHERE slug=? OR name=?",
                  (slug, slug)).fetchone()
    if not r:
        raise ValueError("그런 담당이 없다: {}".format(slug))
    return r["id"]


def t_search(a):
    q = str(a.get("query") or "").strip()
    if not q:
        raise ValueError("query 가 비었다")
    k = max(1, min(20, int(a.get("topK") or 5)))
    with _connect() as c:
        docs = _docs(c, _domain_id(c, str(a.get("domainSlug") or "").strip()))
    hits = bm25_search(q, docs, k)
    if not hits:
        return "'{}' 로 찾은 것이 없다 (페이지·소스 {}건 중).".format(q, len(docs))
    out = ["'{}' 검색 — {}건 (BM25)".format(q, len(hits))]
    for s, d in hits:
        head = "· [{}] #{} {} · {}".format(
            "페이지" if d["kind"] == "page" else "소스", d["id"], d["title"],
            d["domain"])
        out.append("{}  (점수 {:.1f})".format(head, s))
        if d.get("summary"):
            out.append("   요약: {}".format(_cut(d["summary"], 200)))
        body = re.sub(r"\s+", " ", d.get("text") or "").strip()
        if body:
            out.append("   {}".format(_cut(body, SNIPPET)))
    out.append("")
    out.append("★조각만 보고 답하지 마라. 페이지면 readPage(pageId=#) 로 "
               "본문을 읽는다.")
    return "\n".join(out)


def t_page(a):
    pid = int(a.get("pageId"))
    with _connect() as c:
        r = c.execute(
            "SELECT p.*, d.name dname FROM pages p JOIN domains d "
            "ON d.id=p.domain_id WHERE p.id=?", (pid,)).fetchone()
    if not r:
        raise ValueError("page {} 가 없다".format(pid))
    head = ["# {}".format(r["title"]),
            "담당: {} · 갱신: {}".format(r["dname"], r["updated_at"] or "-")]
    if r["tags"]:
        head.append("태그: {}".format(r["tags"]))
    if r["summary"]:
        head.append("요약: {}".format(r["summary"]))
    return "\n".join(head) + "\n\n" + _cut(r["body_md"] or "", BODY_MAX)


def t_sources(a):
    with _connect() as c:
        did = _domain_id(c, str(a.get("domainSlug") or "").strip())
        q = ("SELECT s.id,s.filename,s.filetype,s.description,s.created_at,"
             "d.name dname FROM sources s JOIN domains d ON d.id=s.domain_id")
        args = []
        if did:
            q += " WHERE s.domain_id=?"
            args.append(did)
        rows = c.execute(q + " ORDER BY s.id DESC", args).fetchall()
    if not rows:
        return "올라온 소스가 없다."
    return "\n".join("· #{} {} ({}) · {} · {}{}"
                     .format(r["id"], r["filename"], r["filetype"] or "?",
                             r["dname"], r["created_at"] or "-",
                             "\n   " + _cut(r["description"], 200)
                             if r["description"] else "")
                     for r in rows)


def t_source(a):
    sid = int(a.get("sourceId"))
    n = max(1000, min(SRC_MAX, int(a.get("maxChars") or SRC_MAX)))
    with _connect() as c:
        r = c.execute(
            "SELECT s.*, d.name dname FROM sources s JOIN domains d "
            "ON d.id=s.domain_id WHERE s.id=?", (sid,)).fetchone()
    if not r:
        raise ValueError("source {} 가 없다".format(sid))
    head = "# {} ({}) · {}".format(r["filename"], r["filetype"] or "?",
                                   r["dname"])
    if r["description"]:
        head += "\n설명: {}".format(r["description"])
    txt = r["extracted_text"] or ""
    if not txt.strip():
        # ★그림은 텍스트가 없다. 설명란이 비면 LLM 이 읽을 것이 하나도 없다.
        return head + "\n\n(추출된 텍스트가 없다 — 그림이면 설명란이 전부다)"
    return head + "\n\n" + _cut(txt, n)


# ★위키를 뒤질 낱말은 **위키가 안다** — 코드에 박아 두면 문서를 넣을 때마다
#   아바타 코드를 고쳐야 한다. 실제로 "리센느" 를 넣고도 아바타가 위키를
#   아예 안 뒤져서 "왜 안 되냐" 가 됐다. 제목·태그를 그대로 준다.
# ★관제 낱말은 빼고 준다. 'M14'·'점수'·'알람' 이 낱말로 넘어가면 상태 질문
#   마다 위키를 뒤진다 (그래서 원래 목록도 그걸 일부러 피해 놨다).
#   제목은 **구절 통째로** 주므로 "반송 장치 종류와 역할" 은 남고
#   "M14 반송시간 알려줘" 는 안 걸린다.
WORD_DENY = {
    "all", "m14", "m14b", "m16", "m16a", "m16b", "m16hub", "hub",
    "반송", "관제", "상태", "현황", "데이터", "지표", "컬럼", "점수", "스코어",
    "등급", "알람", "경계", "위험", "초위험", "임계", "정체", "큐", "queue",
    "oht", "모니터링", "이상", "서버", "ai", "mcp", "amhs", "fab", "sla",
}
WORD_MIN = 2            # 한 글자는 아무 데나 걸린다
WORD_MAX = 400          # 너무 많으면 낱말 검사만 오래 걸린다


def t_words(_a):
    """페이지 제목·태그 → 아바타가 쓸 낱말 목록."""
    with _connect() as c:
        rows = c.execute("SELECT title, tags FROM pages").fetchall()
    out, seen = [], set()
    for r in rows:
        cand = [str(r["title"] or "")]
        cand += [t for t in re.split(r"[,\s]+", str(r["tags"] or "")) if t]
        for w in cand:
            w = w.strip()
            k = w.lower()
            if (len(w) < WORD_MIN or k in WORD_DENY or k in seen):
                continue
            seen.add(k)
            out.append(w)
            if len(out) >= WORD_MAX:
                break
    if not out:
        return "(위키에 페이지가 없다)"
    return "\n".join(out)


HANDLERS = {"listDomains": t_domains, "searchWiki": t_search,
            "wikiWords": t_words,
            "readPage": t_page, "listSources": t_sources,
            "readSource": t_source}


# ── 규격 (qa/mcp_server.py 와 같은 뼈대) ──────────────────────────────────
def handle(msg):
    mid, method, p = msg.get("id"), msg.get("method"), msg.get("params") or {}

    def ok(res):
        return {"jsonrpc": "2.0", "id": mid, "result": res}

    def err(code, text):
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": code, "message": text}}

    if method == "initialize":
        return ok({"protocolVersion": p.get("protocolVersion") or PROTO,
                   "capabilities": {"tools": {"listChanged": False}},
                   "serverInfo": {"name": NAME, "version": VERSION}})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": TOOLS})
    if method == "tools/call":
        fn = HANDLERS.get(p.get("name"))
        if fn is None:
            return err(-32602, "그런 도구가 없다: {}".format(p.get("name")))
        try:
            text = fn(p.get("arguments") or {})
        except Exception as e:      # noqa: BLE001
            # ★도구 실패는 프로토콜 오류가 아니다 — isError 결과로 준다.
            #   여기서 JSON-RPC error 를 내면 클라이언트가 연결을 접는다.
            return ok({"content": [{"type": "text", "text": str(e)}],
                       "isError": True})
        return ok({"content": [{"type": "text", "text": text}],
                   "isError": False})
    if mid is None:
        return None              # notifications/* — 답하지 않는다
    return err(-32601, "모르는 method: {}".format(method))


def _force_utf8():
    """★윈도우 파이프는 기본이 cp949 다. '·' '★' 를 못 써서 프로세스가 죽고,
    부모는 [Errno 22] 를 맞는다 — 요청이력에서 실제로 겪은 사고다."""
    for f, kw in ((sys.stdin, {}), (sys.stdout, {"newline": "\n"})):
        try:
            f.reconfigure(encoding="utf-8", errors="replace", **kw)
        except Exception:        # noqa: BLE001
            pass


def serve(stdin=None, stdout=None):
    if stdin is None and stdout is None:
        _force_utf8()
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        res = handle(msg)
        if res is not None:
            stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
            stdout.flush()


def selfcheck():
    """python wiki_mcp_stdio.py --check — DB 를 찾았나, 뭐가 들었나."""
    print("보는 DB: {}".format(db_path()))
    try:
        with _connect() as c:
            d = c.execute("SELECT COUNT(*) n FROM domains").fetchone()["n"]
            p = c.execute("SELECT COUNT(*) n FROM pages").fetchone()["n"]
            s = c.execute("SELECT COUNT(*) n FROM sources").fetchone()["n"]
    except Exception as e:       # noqa: BLE001
        print("못 읽었다: {}".format(e))
        return 1
    print("담당 {} · 페이지 {} · 소스 {}".format(d, p, s))
    print("")
    print(t_domains({}))
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(selfcheck())
    serve()
