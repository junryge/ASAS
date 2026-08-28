# -*- coding: utf-8 -*-
"""
LLM-WIKI — LLM 도메인 학습용 사내 지식 위키 (Flask 모놀리식 단일 파일)

개념: Karpathy llm-wiki (3-layer)
  1) sources/  원본 데이터 (불변, MD/PDF/이미지/TXT/CSV)
  2) wiki/     LLM/사람이 유지하는 마크다운 페이지 (지식 자산)
  3) schema/   작성 규칙 (schema.md)

특징:
  - 담당(도메인)별 관리 + 양식(템플릿) 기반 작성 폼 → 담당자 배포용
  - MD/PDF/이미지/TXT/CSV 업로드 → 텍스트 추출 → 소스 등록
  - OpenAI 호환 API LLM 연동 (사내 게이트웨이 주소를 설정 화면에서 입력)
    · 소스 → 위키 초안 생성  · 위키 기반 QA  · 린트(품질 점검)
  - BM25 검색 (stdlib 구현), 리비전 이력, 전체 export
  - MCP 연동 대비 JSON API (/api/*) + 동봉된 mcp_server.py

의존성: Flask (필수), pypdf (선택: PDF 텍스트 추출)
폐쇄망 기준: Node/Docker 불필요, pip-only, 외부 CDN 없음
"""
import csv
import html
import io
import json
import math
import os
import re
import secrets
import sqlite3
import traceback
import urllib.request
import urllib.error
import urllib.parse
import zipfile
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from flask import (Flask, g, request, redirect, url_for, flash, session,
                   send_file, jsonify, render_template, abort, Response)
from jinja2 import DictLoader
from werkzeug.utils import secure_filename


def html_escape(x):
    """오류 화면에 그대로 박아 넣기 전에 무해하게 만든다."""
    return html.escape(str(x if x is not None else ""), quote=True)

# ---------------------------------------------------------------- 경로/설정
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("LLM_WIKI_DATA", BASE_DIR / "data"))
DB_PATH = DATA_DIR / "wiki.db"
SRC_DIR = DATA_DIR / "sources"
WIKI_DIR = DATA_DIR / "wiki"
SCHEMA_DIR = DATA_DIR / "schema"
SCHEMA_FILE = SCHEMA_DIR / "schema.md"

TEXT_EXT = {".md", ".txt", ".log"}
CSV_EXT = {".csv", ".tsv"}
PDF_EXT = {".pdf"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
ALLOWED_EXT = TEXT_EXT | CSV_EXT | PDF_EXT | IMG_EXT
MAX_UPLOAD_MB = 100

DRAFT_CACHE = {}  # LLM 초안 임시 저장 (token -> markdown)


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------- DB
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_db():
    if "db" not in g:
        g.db = _connect()
    return g.db


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS domains(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS templates(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  domain_id INTEGER,
  name TEXT NOT NULL,
  sections TEXT NOT NULL,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS pages(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  domain_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  slug TEXT NOT NULL,
  ptype TEXT DEFAULT 'concept',
  tags TEXT DEFAULT '',
  summary TEXT DEFAULT '',
  body_md TEXT DEFAULT '',
  author TEXT DEFAULT '',
  source_ids TEXT DEFAULT '',
  created_at TEXT,
  updated_at TEXT
);
CREATE TABLE IF NOT EXISTS logs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  op TEXT NOT NULL,
  title TEXT DEFAULT '',
  detail TEXT DEFAULT '',
  actor TEXT DEFAULT '',
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS revisions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  page_id INTEGER NOT NULL,
  title TEXT,
  body_md TEXT,
  author TEXT,
  saved_at TEXT
);
CREATE TABLE IF NOT EXISTS sources(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  domain_id INTEGER NOT NULL,
  filename TEXT,
  stored_name TEXT,
  filetype TEXT,
  description TEXT DEFAULT '',
  extracted_text TEXT DEFAULT '',
  uploader TEXT DEFAULT '',
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS settings(
  key TEXT PRIMARY KEY,
  value TEXT
);
CREATE TABLE IF NOT EXISTS chunks(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,          -- 'page' | 'source'
  ref_id INTEGER NOT NULL,     -- page.id | source.id
  domain_id INTEGER,
  ord INTEGER DEFAULT 0,
  heading TEXT DEFAULT '',
  text TEXT DEFAULT '',
  emb BLOB,                    -- float32 LE, L2 정규화됨
  dim INTEGER DEFAULT 0,
  model TEXT DEFAULT '',
  updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_chunks_ref ON chunks(kind, ref_id);
CREATE TABLE IF NOT EXISTS evalset(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  question TEXT NOT NULL,
  expect TEXT DEFAULT '',      -- 정답 page id 쉼표구분
  note TEXT DEFAULT '',
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS evalruns(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  label TEXT DEFAULT '',
  config TEXT DEFAULT '',
  n INTEGER DEFAULT 0,
  hit REAL DEFAULT 0, mrr REAL DEFAULT 0, ctxp REAL DEFAULT 0,
  faith REAL DEFAULT -1, arel REAL DEFAULT -1,
  detail TEXT DEFAULT '',
  created_at TEXT
);
"""

DEFAULT_DOMAINS = [
    ("common", "공통", "전 FAB 공통 지식 (시스템 개요, 공용 용어, 표준 절차)"),
    ("m14", "M14", "M14 FAB 지식"),
    ("m14b", "M14B", "M14B FAB 지식"),
    ("m16a", "M16A", "M16A FAB 지식"),
    ("m16b", "M16B", "M16B FAB 지식"),
    ("m16hub", "M16HUB", "M16 HUB 지식"),
]

DEFAULT_TEMPLATES = [
    ("기본 지식 양식", [
        {"title": "개요", "guide": "이 주제가 무엇이고 왜 중요한지 3~5문장으로. 처음 보는 사람 기준으로 작성"},
        {"title": "핵심 용어 정의", "guide": "'- 용어: 정의' 형태로 나열. LLM이 그대로 학습할 수 있게 명확하게"},
        {"title": "프로세스 / 절차", "guide": "단계별로 번호를 붙여 서술. 조건 분기는 '만약 ~이면' 형태로"},
        {"title": "데이터 / 지표", "guide": "관련 테이블·로그·지표의 이름과 의미. 단위를 반드시 명시"},
        {"title": "장애 / 사례", "guide": "실제 발생 사례를 현상 → 원인 → 조치 순서로"},
        {"title": "FAQ", "guide": "신입/타 담당이 자주 묻는 질문과 답"},
        {"title": "참고 소스", "guide": "근거가 된 문서/파일명. 업로드한 소스 번호(#id) 기재"},
    ]),
    ("장애 사례 양식", [
        {"title": "현상", "guide": "언제, 어디서, 무엇이 발생했는지. 시각/호기/구간 명시"},
        {"title": "원인 분석", "guide": "근본 원인. 확정과 추정을 구분해 표기 — 추정이면 '(추정)' 붙이기"},
        {"title": "조치 내용", "guide": "시간 순서대로 조치 내역"},
        {"title": "재발 방지", "guide": "시스템/절차 개선 사항"},
        {"title": "교훈", "guide": "다음 담당자가 반드시 알아야 할 핵심 한두 줄"},
    ]),
]

DEFAULT_SCHEMA_MD = """# AMHS LLM-WIKI 작성 규칙 (schema)

Karpathy의 llm-wiki 스펙을 AMHS 현장에 맞춘 규칙이다.
사람과 LLM 모두 이 문서를 기준으로 작성·갱신한다. (원문의 CLAUDE.md 역할)

## 1. 구조 (3-layer)

```
data/
├─ sources/<FAB>/            원본 자료 — 불변(immutable). 절대 수정하지 않는다
├─ wiki/
│   ├─ index.md              전체 카탈로그 (자동 생성)
│   ├─ log.md                활동 로그, append-only (자동 생성)
│   └─ <FAB>/<타입>/*.md     지식 페이지
└─ schema/schema.md          이 문서
```

- **원본은 진실의 출처**, 위키는 그 위에 사람과 LLM이 유지하는 해석 층이다
- 원본과 위키가 어긋나면 원본이 이긴다

## 2. 담당(FAB) 구분

공통 / M14 / M14B / M16A / M16B / M16HUB
- 특정 FAB에만 해당하면 그 FAB에, 전 FAB 공통이면 **공통**에 작성한다
- 설비 구분(OHT / AGV / CNV / MCS 등)은 담당이 아니라 **태그**로 단다

## 3. 페이지 타입

| 타입 | 용도 | 예 |
|---|---|---|
| `concept` | 주제·개념·절차 (위키의 본체) | OHT 반송 흐름, 정체 판정 기준 |
| `entity` | 고유 대상 — 호기·구간·시스템·조직 | V1023 호기, A구간 HUB, MCS |
| `source` | 원본 자료 1건의 요약 (ingest가 생성) | 소스: 2026 알람코드표.pdf |

## 4. 명명 / 프론트매터 / 상호참조

- **제목**: 검색어로 쓸 말 그대로. 약어는 풀네임 병기 (`OHT(Overhead Hoist Transport)`)
- **프론트매터**: title / type / domain / tags / summary / sources / author / updated
- **상호참조**: 관련 페이지는 반드시 `[[페이지제목]]` 위키링크로 연결한다
- **근거 표기**: 소스에서 온 내용은 `(소스 #12)` 형태로 병기

## 5. 페이지 템플릿

**concept**: 개요 / 핵심 용어 정의 / 프로세스·절차 / 데이터·지표 / 장애·사례 / FAQ / 참고 소스
**entity**: 식별 정보 / 위치·구성 / 이력 / 관련 페이지
**source**: 자료 개요 / 핵심 내용 / 이 위키에 주는 시사점 / 미확인 사항

## 6. 품질 기준

- **1주제 1페이지** — 한 페이지는 하나의 주제만
- **한줄요약 필수** — 검색과 LLM 컨텍스트 선별에 그대로 쓰인다
- **용어는 정의 목록으로** — `- 용어: 정의`
- **사실과 추정 구분** — 확인 안 된 내용은 `(추정)` 표기
- **수치·조건은 원문 그대로** — 요약의 요약으로 정보가 희석되지 않게
- **갱신 우선** — 새 페이지 남발보다 기존 페이지를 갱신·통합
- **고아 페이지 금지** — 어느 페이지에서도 링크되지 않는 페이지는 만들지 않는다

## 7. 연산 (workflows)

**ingest** — 새 소스 반영
1. 소스 요약 페이지(`source`) 작성
2. 관련 기존 페이지 탐색 → 페이지별 갱신안 생성
3. **담당자 검토 후 선택 적용** (LLM 자동 반영 금지)
4. 로그 기록, 카탈로그 갱신

**query** — 질문 응답
1. 위키·소스에서 근거 검색 → 출처 명시해 답변
2. 근거 없으면 "위키에 근거 자료가 없다"고 답한다 (지어내지 않는다)
3. 가치 있는 답변은 노트로 저장해 위키를 키운다

**lint** — 건강 점검
- 페이지 간 모순 / 새 소스에 의해 낡은 내용 / 고아 페이지 /
  빈약한 페이지 / 빠진 상호참조 / 비어 있는 주제

## 8. LLM 사용 규칙

- LLM이 만든 초안·갱신안은 **반드시 담당자 검토 후 저장**한다
- LLM은 소스에 없는 내용을 만들지 않는다. 불확실하면 `(추정)`
- 답변에는 근거 페이지를 명시한다
"""


PTYPES = [
    ("concept", "개념/주제", "설비·시스템·절차 등 주제 단위 지식 (위키의 본체)"),
    ("entity", "대상/개체", "장비 호기·구간·시스템·조직 등 고유 대상"),
    ("source", "소스 요약", "업로드된 원본 자료 1건에 대한 요약 (ingest가 자동 생성)"),
]
PTYPE_NAME = {k: n for k, n, _ in PTYPES}


def seed_settings(conn):
    defaults = {
        "site_name": "AMHS LLM-WIKI 지식정보 시스템",
        "llm_base_url": "",
        "llm_model": "",
        "llm_api_key": "",
        # 검색 — 기본은 지금과 동일한 BM25 단독. 설정해야 켜진다.
        "retrieval_mode": "bm25",      # bm25 | hybrid
        "embed_backend": "none",       # none | api | st
        "embed_base_url": "",          # 비우면 llm_base_url 사용
        "embed_model": "",
        "embed_api_key": "",
        "rerank_backend": "none",      # none | llm | api | st
        "rerank_base_url": "",
        "rerank_model": "",
        "rerank_pool": "30",           # 리랭크 전 후보 수
        "chunk_max": "1200",           # 청크 최대 글자
    }
    for k, v in defaults.items():
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))


def migrate(conn):
    """기존 설치 호환 — 누락 컬럼 추가"""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(pages)")}
    for col, ddl in (("ptype", "TEXT DEFAULT 'concept'"),
                     ("source_ids", "TEXT DEFAULT ''")):
        if col not in cols:
            conn.execute(f"ALTER TABLE pages ADD COLUMN {col} {ddl}")


def init_db():
    for d in (DATA_DIR, SRC_DIR, WIKI_DIR, SCHEMA_DIR):
        d.mkdir(parents=True, exist_ok=True)
    conn = _connect()
    conn.executescript(SCHEMA_SQL)
    migrate(conn)
    if conn.execute("SELECT COUNT(*) c FROM domains").fetchone()["c"] == 0:
        for slug, name, desc in DEFAULT_DOMAINS:
            conn.execute(
                "INSERT INTO domains(slug,name,description,created_at) VALUES(?,?,?,?)",
                (slug, name, desc, now_str()))
    if conn.execute("SELECT COUNT(*) c FROM templates").fetchone()["c"] == 0:
        for name, sections in DEFAULT_TEMPLATES:
            conn.execute(
                "INSERT INTO templates(domain_id,name,sections,created_at) VALUES(NULL,?,?,?)",
                (name, json.dumps(sections, ensure_ascii=False), now_str()))
    seed_settings(conn)
    conn.commit()
    conn.close()
    if not SCHEMA_FILE.exists():
        SCHEMA_FILE.write_text(DEFAULT_SCHEMA_MD, encoding="utf-8")


def get_setting(key, default=""):
    row = get_db().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row and row["value"] is not None else default


def set_setting(key, value):
    get_db().execute(
        "INSERT INTO settings(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    get_db().commit()


# ---------------------------------------------------------------- 유틸
def slugify(s):
    s = re.sub(r"[^\w가-힣\- ]", "", (s or "").strip())
    s = re.sub(r"[\s_]+", "-", s).strip("-").lower()
    return s[:80] or "page"


def unique_page_slug(domain_id, title, exclude_id=None):
    base = slugify(title)
    slug, n = base, 2
    db = get_db()
    while True:
        q = "SELECT id FROM pages WHERE domain_id=? AND slug=?"
        args = [domain_id, slug]
        if exclude_id:
            q += " AND id<>?"
            args.append(exclude_id)
        if not db.execute(q, args).fetchone():
            return slug
        slug = f"{base}-{n}"
        n += 1


def tokenize(text):
    toks = []
    for m in re.findall(r"[0-9A-Za-z_]+|[가-힣]+", (text or "").lower()):
        toks.append(m)
        if re.match(r"[가-힣]", m) and len(m) > 1:
            toks.extend(m[i:i + 2] for i in range(len(m) - 1))
    return toks


def bm25_search(query, docs, k=10):
    """docs: list of dicts {id, kind, title, text, ...}. return [(score, doc)]"""
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


def all_search_docs(domain_id=None, include_sources=True):
    db = get_db()
    docs = []
    q = ("SELECT p.id,p.title,p.summary,p.body_md,p.tags,d.name dname,d.slug dslug "
         "FROM pages p JOIN domains d ON d.id=p.domain_id")
    args = []
    if domain_id:
        q += " WHERE p.domain_id=?"
        args.append(domain_id)
    for r in db.execute(q, args):
        docs.append({"id": r["id"], "kind": "page", "title": r["title"],
                     "text": f"{r['tags']} {r['summary']} {r['body_md']}",
                     "domain": r["dname"], "summary": r["summary"]})
    if include_sources:
        q2 = ("SELECT s.id,s.filename,s.description,s.extracted_text,d.name dname "
              "FROM sources s JOIN domains d ON d.id=s.domain_id")
        args2 = []
        if domain_id:
            q2 += " WHERE s.domain_id=?"
            args2.append(domain_id)
        for r in db.execute(q2, args2):
            docs.append({"id": r["id"], "kind": "source", "title": r["filename"] or "",
                         "text": f"{r['description']} {r['extracted_text'] or ''}"[:20000],
                         "domain": r["dname"], "summary": (r["description"] or "")[:200]})
    return docs


# ================================================================ 검색 엔진
# 3단: ① BM25(어휘) + Dense(의미) → RRF 융합  ② Reranker  ③ 컨텍스트
# 전부 선택적이다. 설정 안 하면 지금까지와 똑같이 BM25 단독으로 동작한다.
# ================================================================
try:
    import numpy as _np
except ImportError:
    _np = None


def emb_conf():
    """임베딩 설정 — base_url 비어있으면 LLM 것을 그대로 쓴다"""
    return {
        "backend": get_setting("embed_backend", "none"),
        "base": (get_setting("embed_base_url") or get_setting("llm_base_url")).rstrip("/"),
        "model": get_setting("embed_model"),
        "key": get_setting("embed_api_key") or get_setting("llm_api_key"),
    }


def embed_ready():
    c = emb_conf()
    if c["backend"] == "api":
        return bool(c["base"] and c["model"])
    if c["backend"] == "st":
        return bool(c["model"])
    return False


_ST_CACHE = {}


def embed_texts(texts):
    """텍스트 리스트 → L2 정규화된 벡터 리스트. 실패 시 RuntimeError."""
    if not texts:
        return []
    c = emb_conf()
    if c["backend"] == "api":
        url = api_base(c["base"]) + "/embeddings"
        headers = {"Content-Type": "application/json"}
        if c["key"]:
            headers["Authorization"] = "Bearer " + c["key"]
        out = []
        for i in range(0, len(texts), 16):          # 배치 16
            batch = [t[:8000] for t in texts[i:i + 16]]
            body = json.dumps({"model": c["model"], "input": batch}).encode()
            req = urllib.request.Request(url, data=body, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    data = json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                raise RuntimeError(f"임베딩 API HTTP {e.code}: {e.read()[:200]!r}")
            except urllib.error.URLError as e:
                raise RuntimeError(f"임베딩 API 접속 실패: {e.reason}")
            try:
                rows = sorted(data["data"], key=lambda x: x.get("index", 0))
                out.extend([r["embedding"] for r in rows])
            except (KeyError, TypeError):
                raise RuntimeError(f"임베딩 응답 형식 이상: {str(data)[:200]}")
        return [_l2(v) for v in out]
    if c["backend"] == "st":
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise RuntimeError("sentence-transformers 미설치. API 백엔드를 쓰거나 pip install 해라.")
        m = _ST_CACHE.get(c["model"])
        if m is None:
            m = _ST_CACHE[c["model"]] = SentenceTransformer(c["model"])
        vecs = m.encode([t[:8000] for t in texts], normalize_embeddings=True)
        return [list(map(float, v)) for v in vecs]
    raise RuntimeError("임베딩 백엔드가 설정되지 않았다 (설정 → 검색)")


def _l2(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _pack(v):
    import struct
    return struct.pack(f"<{len(v)}f", *v)


def _unpack(b, dim):
    import struct
    return struct.unpack(f"<{dim}f", b)


# ---------------------------------------------------------------- 청킹
def chunk_text(body, max_chars=None):
    """마크다운을 '## 헤딩' 단위로 자르고, 너무 길면 문단 경계로 다시 자른다."""
    max_chars = max_chars or int(get_setting("chunk_max", "1200") or 1200)
    body = (body or "").strip()
    if not body:
        return []
    parts, cur_head, cur = [], "", []
    for ln in body.split("\n"):
        m = re.match(r"^(#{1,3})\s+(.*)$", ln)
        if m:
            if any(x.strip() for x in cur):
                parts.append((cur_head, "\n".join(cur).strip()))
            cur_head, cur = m.group(2).strip(), []
        else:
            cur.append(ln)
    if any(x.strip() for x in cur):
        parts.append((cur_head, "\n".join(cur).strip()))
    if not parts:
        parts = [("", body)]
    out = []
    for head, txt in parts:
        if len(txt) <= max_chars:
            out.append((head, txt))
            continue
        buf = []
        size = 0
        for para in txt.split("\n\n"):
            if size + len(para) > max_chars and buf:
                out.append((head, "\n\n".join(buf)))
                buf, size = [], 0
            buf.append(para)
            size += len(para) + 2
        if buf:
            out.append((head, "\n\n".join(buf)))
    return [(h, t) for h, t in out if t.strip()]


def _chunk_payload(title, heading, text):
    """검색 품질용 — 청크 앞에 제목/섹션을 붙여 문맥을 살린다"""
    head = f"{title}" + (f" / {heading}" if heading else "")
    return f"[{head}]\n{text}"


def index_target(kind, ref_id, do_embed=True):
    """페이지/소스 1건의 청크를 재생성 (+ 임베딩). 실패해도 청크는 남는다."""
    db = get_db()
    if kind == "page":
        r = db.execute("SELECT * FROM pages WHERE id=?", (ref_id,)).fetchone()
        if not r:
            return 0
        title, domain_id = r["title"], r["domain_id"]
        body = f"{r['summary']}\n\n{r['body_md'] or ''}"
    else:
        r = db.execute("SELECT * FROM sources WHERE id=?", (ref_id,)).fetchone()
        if not r:
            return 0
        title, domain_id = r["filename"], r["domain_id"]
        body = f"{r['description']}\n\n{r['extracted_text'] or ''}"
    db.execute("DELETE FROM chunks WHERE kind=? AND ref_id=?", (kind, ref_id))
    pieces = chunk_text(body)
    if not pieces:
        db.commit()
        return 0
    ids = []
    for i, (head, txt) in enumerate(pieces):
        cur = db.execute(
            "INSERT INTO chunks(kind,ref_id,domain_id,ord,heading,text,dim,model,updated_at) "
            "VALUES(?,?,?,?,?,?,0,'',?)",
            (kind, ref_id, domain_id, i, head, txt, now_str()))
        ids.append(cur.lastrowid)
    db.commit()
    if do_embed and embed_ready():
        try:
            payloads = [_chunk_payload(title, h, t) for h, t in pieces]
            vecs = embed_texts(payloads)
            model = emb_conf()["model"]
            for cid, v in zip(ids, vecs):
                db.execute("UPDATE chunks SET emb=?, dim=?, model=? WHERE id=?",
                           (_pack(v), len(v), model, cid))
            db.commit()
        except RuntimeError:
            pass          # 임베딩 실패해도 BM25는 계속 동작
    return len(pieces)


def reindex_all(do_embed=True):
    db = get_db()
    n = 0
    for r in db.execute("SELECT id FROM pages").fetchall():
        n += index_target("page", r["id"], do_embed)
    for r in db.execute("SELECT id FROM sources").fetchall():
        n += index_target("source", r["id"], do_embed)
    return n


def index_stats():
    db = get_db()
    try:
        tot = db.execute("SELECT COUNT(*) c FROM chunks").fetchone()["c"]
        emb = db.execute("SELECT COUNT(*) c FROM chunks WHERE emb IS NOT NULL").fetchone()["c"]
        model = db.execute("SELECT model FROM chunks WHERE model<>'' LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return {"chunks": 0, "embedded": 0, "model": ""}
    return {"chunks": tot, "embedded": emb, "model": model["model"] if model else ""}


# ---------------------------------------------------------------- Dense 검색
def dense_search(query, k=30, domain_id=None):
    """코사인 유사도 상위 k개 청크. numpy 있으면 쓰고 없으면 순수 파이썬."""
    if not embed_ready():
        return []
    db = get_db()
    q = "SELECT id,kind,ref_id,heading,text,emb,dim FROM chunks WHERE emb IS NOT NULL"
    args = []
    if domain_id:
        q += " AND domain_id=?"
        args.append(domain_id)
    rows = db.execute(q, args).fetchall()
    if not rows:
        return []
    try:
        qv = embed_texts([query])[0]
    except RuntimeError:
        return []
    dim = rows[0]["dim"]
    rows = [r for r in rows if r["dim"] == dim]      # 모델 바뀌면 차원 불일치 방어
    if not rows:
        return []
    if _np is not None:
        mat = _np.frombuffer(b"".join(r["emb"] for r in rows),
                             dtype="<f4").reshape(len(rows), dim)
        scores = mat @ _np.asarray(qv, dtype="<f4")
        order = _np.argsort(-scores)[:k]
        return [(float(scores[i]), rows[i]) for i in order]
    out = []
    for r in rows:
        v = _unpack(r["emb"], dim)
        out.append((sum(a * b for a, b in zip(v, qv)), r))
    out.sort(key=lambda x: -x[0])
    return out[:k]


# ---------------------------------------------------------------- RRF 융합
def rrf_fuse(ranked_lists, k=60):
    """Reciprocal Rank Fusion — 점수 정규화 없이 순위만으로 합친다."""
    agg = {}
    for lst in ranked_lists:
        for rank, key in enumerate(lst):
            agg[key] = agg.get(key, 0.0) + 1.0 / (k + rank + 1)
    return sorted(agg.items(), key=lambda x: -x[1])


# ---------------------------------------------------------------- Reranker
def rerank_ready():
    b = get_setting("rerank_backend", "none")
    if b == "llm":
        return llm_ready()
    if b == "api":
        return bool((get_setting("rerank_base_url") or get_setting("llm_base_url"))
                    and get_setting("rerank_model"))
    if b == "st":
        return bool(get_setting("rerank_model"))
    return False


def rerank(query, cands, k=5):
    """cands: [(score, doc)] → 재정렬된 [(score, doc)]. 실패하면 원본 순서 유지."""
    backend = get_setting("rerank_backend", "none")
    if backend == "none" or not cands or not rerank_ready():
        return cands[:k]
    passages = [((d.get("chunkText") or d.get("text") or "")[:1200]) for _, d in cands]
    titles = [d["title"] for _, d in cands]
    try:
        if backend == "llm":
            order = _rerank_llm(query, titles, passages)
        elif backend == "api":
            order = _rerank_api(query, passages)
        else:
            order = _rerank_st(query, passages)
    except (RuntimeError, ValueError, KeyError, TypeError):
        return cands[:k]
    if not order:
        return cands[:k]
    seen, out = set(), []
    for i in order:
        if 0 <= i < len(cands) and i not in seen:
            seen.add(i)
            out.append(cands[i])
    for i, c in enumerate(cands):          # 리랭커가 빠뜨린 건 뒤에 붙인다
        if i not in seen:
            out.append(c)
    return out[:k]


def _rerank_llm(query, titles, passages):
    """의존성 0 — 지금 쓰는 chat 엔드포인트로 순위만 매긴다"""
    lines = []
    for i, (t, p) in enumerate(zip(titles, passages)):
        lines.append(f"[{i}] {t}\n{p[:600]}")
    sys_p = ("너는 검색 결과 재정렬기다. 질문에 답하는 데 실제로 도움되는 순서로 문서 번호를 정렬해라.\n"
             "출력은 JSON 배열 하나만. 예: [3,0,7,1]\n"
             "설명·코드블록·다른 텍스트 금지. 관련 없는 문서는 빼도 된다.")
    user_p = f"질문: {query}\n\n=== 후보 문서 ===\n" + "\n\n".join(lines)
    out = llm_chat([{"role": "system", "content": sys_p},
                    {"role": "user", "content": user_p}], max_tokens=300, temperature=0.0)
    m = re.search(r"\[[\d,\s]*\]", out)
    if not m:
        return []
    return [int(x) for x in re.findall(r"\d+", m.group(0))]


def _rerank_api(query, passages):
    """Cohere/Jina 호환 /rerank 엔드포인트"""
    base = (get_setting("rerank_base_url") or get_setting("llm_base_url")).rstrip("/")
    key = get_setting("llm_api_key")
    body = json.dumps({"model": get_setting("rerank_model"), "query": query,
                       "documents": passages, "top_n": len(passages)}).encode()
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(api_base(base) + "/rerank", data=body,
                                 headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        raise RuntimeError(f"rerank API 실패: {e}")
    return [x["index"] for x in data.get("results", [])]


def _rerank_st(query, passages):
    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        raise RuntimeError("sentence-transformers 미설치")
    name = get_setting("rerank_model")
    m = _ST_CACHE.get("ce:" + name)
    if m is None:
        m = _ST_CACHE["ce:" + name] = CrossEncoder(name)
    scores = m.predict([(query, p) for p in passages])
    return [int(i) for i in sorted(range(len(scores)), key=lambda i: -scores[i])]


# ---------------------------------------------------------------- 통합 진입점
def retrieve(query, k=5, domain_id=None, include_sources=True, force_mode=None):
    """모든 검색 경로가 여기를 쓴다.
       mode=bm25   : 지금까지와 동일
       mode=hybrid : BM25 + Dense를 RRF로 합침
       리랭커가 켜져 있으면 후보 pool을 뽑아 재정렬한다."""
    mode = force_mode or get_setting("retrieval_mode", "bm25")
    use_rerank = rerank_ready()
    pool = int(get_setting("rerank_pool", "30") or 30) if use_rerank else k
    pool = max(pool, k)

    docs = all_search_docs(domain_id=domain_id, include_sources=include_sources)
    by_key = {(d["kind"], d["id"]): d for d in docs}
    lex = bm25_search(query, docs, k=pool)
    lex_keys = [(d["kind"], d["id"]) for _, d in lex]
    lex_score = {(d["kind"], d["id"]): s for s, d in lex}

    if mode != "hybrid" or not embed_ready():
        merged = [(lex_score[k2], by_key[k2]) for k2 in lex_keys]
        return rerank(query, merged, k) if use_rerank else merged[:k]

    # Dense — 청크 단위 결과를 문서 단위로 접고, 최고 점수 청크 본문을 함께 들고 간다
    best_chunk = {}
    dense_keys = []
    for sc, row in dense_search(query, k=pool * 2, domain_id=domain_id):
        key = (row["kind"], row["ref_id"])
        if key not in by_key:
            continue
        if key not in best_chunk or sc > best_chunk[key][0]:
            best_chunk[key] = (sc, row["text"], row["heading"])
        if key not in dense_keys:
            dense_keys.append(key)

    fused = rrf_fuse([lex_keys, dense_keys])
    merged = []
    for key, score in fused[:pool]:
        d = dict(by_key[key])
        if key in best_chunk:
            d["chunkText"] = best_chunk[key][1]
            d["chunkHeading"] = best_chunk[key][2]
        merged.append((score, d))
    return rerank(query, merged, k) if use_rerank else merged[:k]


def retrieval_desc():
    """현재 검색 구성 한 줄 요약 — 화면·평가 이력에 쓴다"""
    mode = get_setting("retrieval_mode", "bm25")
    parts = ["BM25"]
    if mode == "hybrid" and embed_ready():
        parts.append(f"Dense({emb_conf()['model']})")
    rb = get_setting("rerank_backend", "none")
    tail = f" + rerank:{rb}" if rerank_ready() else ""
    return " + ".join(parts) + tail


# ---------------------------------------------------------------- 마크다운 렌더러 (stdlib)
import html as html_mod


def _md_inline(s):
    s = html_mod.escape(s, quote=False)
    codes = []

    def _stash(m):
        codes.append(m.group(1))
        return f"\x00{len(codes)-1}\x00"

    s = re.sub(r"`([^`]+)`", _stash, s)
    s = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)",
               r'<img src="\2" alt="\1" style="max-width:100%">', s)
    s = re.sub(r"\[\[([^\]|]+)\]\]",
               lambda m: '<a class="wikilink" href="/page/t/%s">%s</a>' % (
                   urllib.parse.quote(m.group(1).strip()), m.group(1).strip()), s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: "<code>%s</code>" % codes[int(m.group(1))], s)
    return s


def md_to_html(text):
    if not text:
        return ""
    lines = text.replace("\r\n", "\n").split("\n")
    out, i, n = [], 0, len(lines)
    para = []

    def flush():
        if para:
            out.append("<p>" + "<br>".join(_md_inline(x) for x in para) + "</p>")
            para.clear()

    while i < n:
        ln = lines[i]
        # fenced code
        if ln.strip().startswith("```"):
            flush()
            buf = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>%s</code></pre>" % html_mod.escape("\n".join(buf)))
            continue
        # header
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            flush()
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{_md_inline(m.group(2))}</h{lvl}>")
            i += 1
            continue
        # hr
        if re.match(r"^\s*(-{3,}|\*{3,})\s*$", ln):
            flush()
            out.append("<hr>")
            i += 1
            continue
        # table
        if ln.strip().startswith("|") and i + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]):
            flush()
            header = [c.strip() for c in ln.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            t = "<table><thead><tr>" + "".join(f"<th>{_md_inline(c)}</th>" for c in header) + "</tr></thead><tbody>"
            for r in rows:
                t += "<tr>" + "".join(f"<td>{_md_inline(c)}</td>" for c in r) + "</tr>"
            t += "</tbody></table>"
            out.append('<div class="tablewrap">%s</div>' % t)
            continue
        # blockquote
        if ln.startswith(">"):
            flush()
            buf = []
            while i < n and lines[i].startswith(">"):
                buf.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote>%s</blockquote>" % "<br>".join(_md_inline(x) for x in buf))
            continue
        # unordered list
        if re.match(r"^\s*[-*]\s+", ln):
            flush()
            items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i]))
                i += 1
            out.append("<ul>" + "".join(f"<li>{_md_inline(x)}</li>" for x in items) + "</ul>")
            continue
        # ordered list
        if re.match(r"^\s*\d+[.)]\s+", ln):
            flush()
            items = []
            while i < n and re.match(r"^\s*\d+[.)]\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+[.)]\s+", "", lines[i]))
                i += 1
            out.append("<ol>" + "".join(f"<li>{_md_inline(x)}</li>" for x in items) + "</ol>")
            continue
        # blank
        if not ln.strip():
            flush()
            i += 1
            continue
        para.append(ln)
        i += 1
    flush()
    return "\n".join(out)


# ---------------------------------------------------------------- 파일 추출
def read_text_file(path: Path):
    raw = path.read_bytes()
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def extract_csv(path: Path, max_rows=30):
    txt = read_text_file(path)
    delim = "\t" if path.suffix.lower() == ".tsv" else ","
    try:
        delim = csv.Sniffer().sniff(txt[:2000]).delimiter
    except csv.Error:
        pass
    rows = list(csv.reader(io.StringIO(txt), delimiter=delim))
    if not rows:
        return "(빈 파일)"
    header, body = rows[0], rows[1:]
    ncol = len(header)
    md = ["| " + " | ".join(c.replace("|", "\\|") for c in header) + " |",
          "|" + "---|" * ncol]
    for r in body[:max_rows]:
        r = (r + [""] * ncol)[:ncol]
        md.append("| " + " | ".join(c.replace("|", "\\|") for c in r) + " |")
    info = f"\n\n(총 {len(body)}행 × {ncol}열"
    if len(body) > max_rows:
        info += f", 위는 앞 {max_rows}행 미리보기"
    info += ")"
    return "\n".join(md) + info


def extract_pdf(path: Path):
    try:
        from pypdf import PdfReader
    except ImportError:
        return None, "pypdf 미설치 — 'pip install pypdf' 후 재업로드하면 텍스트가 추출된다"
    try:
        reader = PdfReader(str(path))
        parts = []
        for pi, pg in enumerate(reader.pages):
            t = (pg.extract_text() or "").strip()
            if t:
                parts.append(f"[p.{pi+1}]\n{t}")
        return "\n\n".join(parts), None
    except Exception as e:
        return None, f"PDF 추출 실패: {e}"


def extract_source(path: Path):
    """returns (filetype, extracted_text, warn)"""
    ext = path.suffix.lower()
    if ext in TEXT_EXT:
        return "text", read_text_file(path), None
    if ext in CSV_EXT:
        return "csv", extract_csv(path), None
    if ext in PDF_EXT:
        txt, warn = extract_pdf(path)
        return "pdf", (txt or ""), warn
    if ext in IMG_EXT:
        return "image", "", None
    return "other", "", None


# ---------------------------------------------------------------- 위키 파일 미러 (지식 자산 레이어)
def page_frontmatter(p, domain_name):
    tags = ", ".join(t.strip() for t in (p["tags"] or "").split(",") if t.strip())
    ptype = p["ptype"] if "ptype" in p.keys() else "concept"
    srcs = p["source_ids"] if "source_ids" in p.keys() else ""
    return ("---\n"
            f"title: {p['title']}\n"
            f"type: {ptype}\n"
            f"domain: {domain_name}\n"
            f"tags: [{tags}]\n"
            f"summary: {p['summary']}\n"
            f"sources: [{srcs}]\n"
            f"author: {p['author']}\n"
            f"updated: {p['updated_at']}\n"
            "---\n\n")


def write_page_file(page_id):
    db = get_db()
    p = db.execute("SELECT p.*, d.slug dslug, d.name dname FROM pages p "
                   "JOIN domains d ON d.id=p.domain_id WHERE p.id=?", (page_id,)).fetchone()
    if not p:
        return
    d = WIKI_DIR / p["dslug"] / (p["ptype"] or "concept")
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{p['slug']}.md").write_text(
        page_frontmatter(p, p["dname"]) + (p["body_md"] or ""), encoding="utf-8")
    index_target("page", page_id)      # 청크·임베딩 증분 갱신


def add_log(op, title="", detail="", actor=""):
    """카파시 log.md 대응 — append-only 활동 기록"""
    db = get_db()
    db.execute("INSERT INTO logs(op,title,detail,actor,created_at) VALUES(?,?,?,?,?)",
               (op, title, detail, actor, now_str()))
    db.commit()


def build_log_md():
    db = get_db()
    lines = ["# 활동 로그 (append-only)", ""]
    for r in db.execute("SELECT * FROM logs ORDER BY id"):
        lines.append(f"## [{r['created_at']}] {r['op']} | {r['title']}")
        if r["detail"]:
            lines.append(r["detail"])
        if r["actor"]:
            lines.append(f"— {r['actor']}")
        lines.append("")
    return "\n".join(lines)


def build_index_md():
    """카파시 index.md 대응 — 전체 카탈로그 (타입/담당별 한줄요약)"""
    db = get_db()
    out = ["# 지식 카탈로그 (index)", "",
           f"생성: {now_str()}", ""]
    tot = db.execute("SELECT COUNT(*) c FROM pages").fetchone()["c"]
    src = db.execute("SELECT COUNT(*) c FROM sources").fetchone()["c"]
    out += [f"- 페이지 {tot}건 / 원본 소스 {src}건", ""]
    for key, name, _ in PTYPES:
        rows = db.execute(
            "SELECT p.*, d.name dname FROM pages p JOIN domains d ON d.id=p.domain_id "
            "WHERE p.ptype=? ORDER BY d.id, p.title", (key,)).fetchall()
        out.append(f"## {name} ({key}) — {len(rows)}건")
        out.append("")
        if not rows:
            out += ["(없음)", ""]
            continue
        cur = None
        for r in rows:
            if r["dname"] != cur:
                cur = r["dname"]
                out.append(f"### {cur}")
            tg = f" `{r['tags']}`" if r["tags"] else ""
            out.append(f"- [[{r['title']}]]{tg} — {r['summary'] or '(요약 없음)'}")
        out.append("")
    return "\n".join(out)


def sync_all_wiki_files():
    """wiki/ 디렉토리를 DB 기준으로 전체 재생성 (export 시 호출)"""
    import shutil
    if WIKI_DIR.exists():
        shutil.rmtree(WIKI_DIR)
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    db = get_db()
    for p in db.execute("SELECT id FROM pages"):
        write_page_file(p["id"])
    (WIKI_DIR / "index.md").write_text(build_index_md(), encoding="utf-8")
    (WIKI_DIR / "log.md").write_text(build_log_md(), encoding="utf-8")


def find_backlinks(title):
    db = get_db()
    inner = title.replace("~", "~~").replace("%", "~%").replace("_", "~_")
    pat = "%~[~[" + inner + "~]~]%"
    return db.execute(
        "SELECT p.id,p.title,d.name dname FROM pages p JOIN domains d ON d.id=p.domain_id "
        "WHERE p.body_md LIKE ? ESCAPE '~'", (pat,)).fetchall()


# ---------------------------------------------------------------- LLM (OpenAI 호환 API)
def llm_ready():
    return bool(get_setting("llm_base_url") and get_setting("llm_model"))


# 사람이 쓰던 주소를 통째로 붙여 넣는다. 그러면 아래에서 한 번 더 붙어
# /chat/completions/chat/completions 가 되고 404 가 난다 (실제로 그랬다).
_API_TAILS = ("/chat/completions", "/completions", "/embeddings", "/rerank")


def api_base(url):
    """설정에 적힌 주소에서 **base 만** 남긴다. 끝에 붙은 손잡이는 뗀다."""
    b = str(url or "").strip().rstrip("/")
    for t in _API_TAILS:
        if b.endswith(t):
            return b[: -len(t)].rstrip("/")
    return b


# 사고(reasoning) 모델 — 끄지 않으면 사고에만 토큰을 쓰고 본문이 빈다
_REASONING_HINTS = ("qwen3", "qwq", "deepseek-r", "gpt-oss", "o1", "o3", "thinking")


def _is_reasoning(model):
    m = str(model or "").lower()
    return any(h in m for h in _REASONING_HINTS)


def _no_think(messages):
    """마지막 user 메시지에 '/no_think' 를 붙인다 (Qwen3 계열 관례)."""
    out = [dict(m) for m in messages]
    for i in range(len(out) - 1, -1, -1):
        if out[i].get("role") == "user" and isinstance(out[i].get("content"), str):
            if "/no_think" not in out[i]["content"]:
                out[i]["content"] = out[i]["content"].rstrip() + "\n\n/no_think"
            break
    return out


def _pick_text(data):
    """응답에서 본문을 꺼낸다.

    ★사고 모델은 content 를 **None** 으로 주고 reasoning_content 에만 쓴다.
      그대로 돌려주면 호출부가 out[:80] 하다가
      TypeError: 'NoneType' object is not subscriptable 로 터진다 (실제 증상).
    """
    try:
        msg = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(f"LLM 응답 형식 이상: {str(data)[:300]}")
    for k in ("content", "reasoning_content", "reasoning"):
        v = msg.get(k) if isinstance(msg, dict) else None
        if isinstance(v, str) and v.strip():
            return v
    fin = (data.get("choices") or [{}])[0].get("finish_reason")
    raise RuntimeError(
        "LLM 이 빈 응답을 줬다 (finish_reason={}). 사고 모델이 사고에만 "
        "토큰을 쓴 경우가 대부분이다 — 모델명을 사고 없는 것으로 바꾸거나 "
        "max_tokens 를 늘려라.".format(fin))


def llm_chat(messages, max_tokens=2500, temperature=0.3):
    base = get_setting("llm_base_url").rstrip("/")
    model = get_setting("llm_model")
    key = get_setting("llm_api_key")
    if not base or not model:
        raise RuntimeError("LLM 설정이 비어있다. [설정]에서 API 주소와 모델명을 입력해라.")
    url = api_base(base) + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key

    send = _no_think(messages) if _is_reasoning(model) else messages
    # ★사고를 게이트웨이에서 끈다. 이 키를 모르는 서버는 400 을 내므로
    #   한 단계씩 빼며 다시 부른다 (400 은 즉답이라 사실상 공짜다).
    tiers = [{"chat_template_kwargs": {"enable_thinking": False}}, {}]
    if "gpt-oss" in str(model).lower():
        tiers.insert(0, {"chat_template_kwargs": {"enable_thinking": False},
                         "reasoning_effort": "low"})
    last = None
    for extra in tiers:
        payload = {"model": model, "messages": send,
                   "max_tokens": max_tokens, "temperature": temperature}
        payload.update(extra)
        req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return _pick_text(json.loads(r.read().decode("utf-8")))
        except urllib.error.HTTPError as e:
            detail = e.read()[:300]
            last = RuntimeError(f"LLM API HTTP {e.code}: {detail!r}")
            if e.code == 400 and extra:
                continue           # 옵션을 모르는 게이트웨이 — 빼고 다시
            raise last
        except urllib.error.URLError as e:
            raise RuntimeError(f"LLM API 접속 실패: {e.reason}")
    raise last or RuntimeError("LLM 호출 실패")


def schema_text():
    return SCHEMA_FILE.read_text(encoding="utf-8") if SCHEMA_FILE.exists() else DEFAULT_SCHEMA_MD


def llm_draft_from_source(src, template_sections):
    sec_desc = "\n".join(f"## {s['title']}\n({s['guide']})" for s in template_sections)
    text = (src["extracted_text"] or "")[:9000]
    if not text.strip():
        raise RuntimeError("이 소스는 추출된 텍스트가 없다 (이미지/추출실패). 설명을 먼저 입력해라.")
    sys_p = ("너는 사내 지식위키(LLM-WIKI) 작성 보조다. 아래 작성 규칙을 따르고, "
             "주어진 소스 내용만 근거로 위키 페이지 초안을 한국어 마크다운으로 작성해라. "
             "소스에 없는 내용은 지어내지 말고, 불확실하면 '(추정)'을 붙여라.\n\n"
             "=== 작성 규칙 ===\n" + schema_text()[:3000] +
             "\n\n=== 출력 형식 ===\n순수 마크다운 본문만 출력. 아래 섹션 구성을 따라라:\n" + sec_desc)
    user_p = f"[소스 파일: {src['filename']}]\n[소스 설명: {src['description'] or '없음'}]\n\n{text}"
    return llm_chat([{"role": "system", "content": sys_p},
                     {"role": "user", "content": user_p}])


def llm_source_summary(src):
    """카파시 ingest 1단계 — 소스 1건에 대한 요약 페이지 본문 생성"""
    text = (src["extracted_text"] or "")[:9000]
    if not text.strip():
        text = f"(추출 텍스트 없음 — 설명만 있음) {src['description']}"
    sys_p = ("너는 AMHS 지식위키의 소스 요약 담당이다. 주어진 원본 자료 1건을 읽고 "
             "'소스 요약 페이지'를 한국어 마크다운으로 작성해라. 자료에 없는 내용은 지어내지 마라.\n\n"
             "출력 섹션(그대로 사용):\n"
             "## 자료 개요\n(무슨 자료인지 2~3문장)\n"
             "## 핵심 내용\n(불릿 5~10개. 수치·조건·설비명은 원문 그대로 유지)\n"
             "## 이 위키에 주는 시사점\n(어떤 주제 페이지에 반영돼야 하는지)\n"
             "## 미확인 사항\n(자료만으로 판단 안 되는 것. 없으면 '없음')")
    user_p = f"[파일: {src['filename']}]\n[설명: {src['description'] or '없음'}]\n\n{text}"
    return llm_chat([{"role": "system", "content": sys_p},
                     {"role": "user", "content": user_p}], max_tokens=2000)


def llm_page_update(src, page):
    """카파시 ingest 2단계 — 새 소스를 근거로 기존 페이지 갱신안 생성"""
    text = (src["extracted_text"] or src["description"] or "")[:5000]
    sys_p = ("너는 AMHS 지식위키의 유지보수 담당이다. 새로 들어온 소스를 근거로 "
             "기존 위키 페이지를 어떻게 갱신할지 판단해라.\n\n"
             "규칙:\n"
             "- 갱신할 내용이 없으면 첫 줄에 정확히 'NO_UPDATE' 만 출력하고 끝내라\n"
             "- 갱신할 내용이 있으면 아래 형식으로만 출력해라:\n"
             "CHANGE_SUMMARY: (무엇을 왜 바꾸는지 한 줄)\n"
             "---BODY---\n"
             "(갱신된 페이지 전체 본문 마크다운. 기존 내용을 최대한 보존하고 새 내용을 병합. "
             "삭제는 소스가 명확히 뒤집는 경우에만)\n"
             "- 소스에 없는 내용은 지어내지 마라. 불확실하면 '(추정)' 표기\n"
             "- 새 내용에는 근거를 '(소스 #ID)' 형태로 병기")
    user_p = (f"=== 새 소스 #{src['id']}: {src['filename']} ===\n"
              f"[설명: {src['description'] or '없음'}]\n{text}\n\n"
              f"=== 기존 페이지: {page['title']} ===\n"
              f"[요약: {page['summary']}]\n{page['body_md'] or '(본문 없음)'}")
    return llm_chat([{"role": "system", "content": sys_p},
                     {"role": "user", "content": user_p}], max_tokens=3000)


def llm_answer(question, top_docs):
    ctx_parts = []
    for score, d in top_docs:
        # 하이브리드 검색이 짚어준 섹션이 있으면 그 부분을 우선 넣는다
        body = (d.get("chunkText") or d.get("text") or "")[:3000]
        head = f" › {d['chunkHeading']}" if d.get("chunkHeading") else ""
        ctx_parts.append(f"### [{d['kind']}#{d['id']}] {d['title']}{head} (담당: {d['domain']})\n{body}")
    ctx = "\n\n".join(ctx_parts) if ctx_parts else "(검색된 문서 없음)"
    sys_p = ("너는 사내 지식위키(LLM-WIKI) QA 어시스턴트다. 아래 위키 문서 발췌만 근거로 "
             "한국어로 답해라. 근거가 없으면 '위키에 근거 자료가 없다'고 말해라. "
             "답변 끝에 참고한 문서를 [page#번호 제목] 형태로 명시해라.")
    user_p = f"=== 위키 발췌 ===\n{ctx}\n\n=== 질문 ===\n{question}"
    return llm_chat([{"role": "system", "content": sys_p},
                     {"role": "user", "content": user_p}], max_tokens=2000)


# ---------------------------------------------------------------- 린트 (규칙 기반)
def run_lint():
    db = get_db()
    pages = db.execute("SELECT p.*, d.name dname FROM pages p JOIN domains d ON d.id=p.domain_id").fetchall()
    titles = {p["title"] for p in pages}
    linked = set()
    issues = []
    for p in pages:
        for m in re.findall(r"\[\[([^\]|]+)\]\]", p["body_md"] or ""):
            t = m.strip()
            linked.add(t)
            if t not in titles:
                issues.append({"page_id": p["id"], "title": p["title"], "level": "warn",
                               "msg": f"깨진 위키링크: [[{t}]] — 대상 페이지가 없다"})
    # 새 소스가 들어왔는데 아직 어느 페이지에도 반영 안 된 것 (ingest 누락)
    used = set()
    for p in pages:
        for x in (p["source_ids"] or "").split(","):
            if x.strip():
                used.add(x.strip())
    for s in db.execute("SELECT s.id, s.filename, d.name dname FROM sources s "
                        "JOIN domains d ON d.id=s.domain_id"):
        if str(s["id"]) not in used:
            issues.append({"page_id": 0, "title": f"소스: {s['filename']}", "level": "warn",
                           "msg": f"소스 #{s['id']} ({s['dname']})가 아직 어느 페이지에도 반영되지 않았다 — Ingest 실행 필요"})
    cutoff = datetime.now() - timedelta(days=180)
    for p in pages:
        if not (p["summary"] or "").strip():
            issues.append({"page_id": p["id"], "title": p["title"], "level": "warn",
                           "msg": "한줄요약이 비어있다 (검색/LLM 컨텍스트 품질 저하)"})
        if len((p["body_md"] or "").strip()) < 200:
            issues.append({"page_id": p["id"], "title": p["title"], "level": "info",
                           "msg": f"본문이 빈약하다 ({len((p['body_md'] or '').strip())}자)"})
        if p["title"] not in linked and len(pages) > 1:
            issues.append({"page_id": p["id"], "title": p["title"], "level": "info",
                           "msg": "고아 페이지 — 다른 페이지에서 [[링크]]되지 않음"})
        try:
            upd = datetime.strptime(p["updated_at"], "%Y-%m-%d %H:%M")
            if upd < cutoff:
                issues.append({"page_id": p["id"], "title": p["title"], "level": "info",
                               "msg": f"180일 이상 미갱신 (마지막: {p['updated_at']})"})
        except (ValueError, TypeError):
            pass
    return issues


# ---------------------------------------------------------------- Flask 앱
app = Flask(__name__)
app.secret_key = os.environ.get("LLM_WIKI_SECRET", secrets.token_hex(16))
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


@app.teardown_appcontext
def _close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.template_filter("md")
def _f_md(text):
    return md_to_html(text)


@app.template_filter("nl2br")
def _f_nl2br(text):
    return html_mod.escape(text or "").replace("\n", "<br>")


@app.context_processor
def _ctx():
    db = get_db()
    domains = db.execute("SELECT * FROM domains ORDER BY id").fetchall()
    return {"nav_domains": domains,
            "site_name": get_setting("site_name", "AMHS LLM-WIKI 지식정보 시스템"),
            "llm_ok": llm_ready(), "ptypes": PTYPES}


# ---------------------------------------------------------------- 라우트: 대시보드
@app.route("/")
def index():
    db = get_db()
    stats = {
        "domains": db.execute("SELECT COUNT(*) c FROM domains").fetchone()["c"],
        "pages": db.execute("SELECT COUNT(*) c FROM pages").fetchone()["c"],
        "sources": db.execute("SELECT COUNT(*) c FROM sources").fetchone()["c"],
        "revisions": db.execute("SELECT COUNT(*) c FROM revisions").fetchone()["c"],
    }
    dom_rows = db.execute(
        "SELECT d.*, (SELECT COUNT(*) FROM pages p WHERE p.domain_id=d.id) pcnt, "
        "(SELECT COUNT(*) FROM sources s WHERE s.domain_id=d.id) scnt "
        "FROM domains d ORDER BY d.id").fetchall()
    recent_pages = db.execute(
        "SELECT p.*, d.name dname, d.slug dslug FROM pages p JOIN domains d ON d.id=p.domain_id "
        "ORDER BY p.updated_at DESC LIMIT 8").fetchall()
    recent_sources = db.execute(
        "SELECT s.*, d.name dname FROM sources s JOIN domains d ON d.id=s.domain_id "
        "ORDER BY s.id DESC LIMIT 8").fetchall()
    return render_template("index.html", stats=stats, dom_rows=dom_rows,
                           recent_pages=recent_pages, recent_sources=recent_sources)


# ---------------------------------------------------------------- 라우트: 담당
@app.route("/domain/<slug>")
def domain_view(slug):
    db = get_db()
    d = db.execute("SELECT * FROM domains WHERE slug=?", (slug,)).fetchone()
    if not d:
        abort(404)
    pages = db.execute("SELECT * FROM pages WHERE domain_id=? ORDER BY updated_at DESC",
                       (d["id"],)).fetchall()
    sources = db.execute("SELECT * FROM sources WHERE domain_id=? ORDER BY id DESC",
                         (d["id"],)).fetchall()
    templates = db.execute(
        "SELECT * FROM templates WHERE domain_id IS NULL OR domain_id=? ORDER BY id",
        (d["id"],)).fetchall()
    return render_template("domain.html", d=d, pages=pages, sources=sources,
                           templates=templates)


# ---------------------------------------------------------------- 라우트: 페이지
@app.route("/page/new", methods=["GET", "POST"])
def page_new():
    db = get_db()
    domains = db.execute("SELECT * FROM domains ORDER BY id").fetchall()
    templates = db.execute("SELECT * FROM templates ORDER BY id").fetchall()
    if request.method == "POST":
        domain_id = int(request.form["domain_id"])
        title = request.form["title"].strip()
        if not title:
            flash("제목은 필수다", "err")
            return redirect(request.url)
        mode = request.form.get("mode", "free")
        if mode == "form":
            tpl = db.execute("SELECT * FROM templates WHERE id=?",
                             (int(request.form["template_id"]),)).fetchone()
            sections = json.loads(tpl["sections"])
            parts = []
            for idx, sec in enumerate(sections):
                content = (request.form.get(f"sec_{idx}") or "").strip()
                if content:
                    parts.append(f"## {sec['title']}\n\n{content}")
            body = "\n\n".join(parts)
        else:
            body = request.form.get("body_md", "").strip()
        slug = unique_page_slug(domain_id, title)
        now = now_str()
        author = request.form.get("author", "").strip()
        ptype = request.form.get("ptype", "concept")
        cur = db.execute(
            "INSERT INTO pages(domain_id,title,slug,ptype,tags,summary,body_md,author,"
            "source_ids,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (domain_id, title, slug, ptype if ptype in PTYPE_NAME else "concept",
             request.form.get("tags", "").strip(),
             request.form.get("summary", "").strip(), body, author,
             request.form.get("source_ids", "").strip(), now, now))
        pid = cur.lastrowid
        db.execute("INSERT INTO revisions(page_id,title,body_md,author,saved_at) VALUES(?,?,?,?,?)",
                   (pid, title, body, author, now))
        db.commit()
        write_page_file(pid)
        add_log("create", title, f"담당 {domain_id} · 타입 {ptype}", author)
        flash("페이지 저장 완료", "ok")
        return redirect(url_for("page_view", pid=pid))
    # GET
    sel_domain = request.args.get("domain", "")
    sel_template = request.args.get("template", "")
    prefill_title = request.args.get("title", "")
    draft_token = request.args.get("draft", "")
    draft_body = DRAFT_CACHE.pop(draft_token, "") if draft_token else ""
    tpl = None
    sections = []
    if sel_template:
        tpl = db.execute("SELECT * FROM templates WHERE id=?", (sel_template,)).fetchone()
        if tpl:
            sections = json.loads(tpl["sections"])
    return render_template("page_form.html", domains=domains, templates=templates,
                           sel_domain=sel_domain, tpl=tpl, sections=sections,
                           draft_body=draft_body, prefill_title=prefill_title)


@app.route("/page/<int:pid>")
def page_view(pid):
    db = get_db()
    p = db.execute("SELECT p.*, d.name dname, d.slug dslug FROM pages p "
                   "JOIN domains d ON d.id=p.domain_id WHERE p.id=?", (pid,)).fetchone()
    if not p:
        abort(404)
    backlinks = [b for b in find_backlinks(p["title"]) if b["id"] != pid]
    revcnt = db.execute("SELECT COUNT(*) c FROM revisions WHERE page_id=?", (pid,)).fetchone()["c"]
    return render_template("page_view.html", p=p, backlinks=backlinks, revcnt=revcnt)


@app.route("/tag/<path:tag>")
def tag_view(tag):
    """태그(설비/주제)로 페이지 모아보기 — FAB 담당을 가로지르는 뷰"""
    db = get_db()
    tag = tag.strip()
    rows = db.execute(
        "SELECT p.*, d.name dname, d.slug dslug FROM pages p "
        "JOIN domains d ON d.id=p.domain_id ORDER BY p.updated_at DESC").fetchall()
    pages = [r for r in rows
             if tag.lower() in [t.strip().lower() for t in (r["tags"] or "").split(",")]]
    counter = Counter()
    for r in rows:
        for t in (r["tags"] or "").split(","):
            if t.strip():
                counter[t.strip()] += 1
    return render_template("tag.html", tag=tag, pages=pages,
                           all_tags=counter.most_common())


@app.route("/page/t/<path:title>")
def page_by_title(title):
    db = get_db()
    p = db.execute("SELECT id FROM pages WHERE title=?", (title.strip(),)).fetchone()
    if p:
        return redirect(url_for("page_view", pid=p["id"]))
    flash(f"'{title}' 페이지가 아직 없다. 새로 만들어라.", "err")
    return redirect(url_for("page_new", title=title))


@app.route("/page/<int:pid>/edit", methods=["GET", "POST"])
def page_edit(pid):
    db = get_db()
    p = db.execute("SELECT * FROM pages WHERE id=?", (pid,)).fetchone()
    if not p:
        abort(404)
    domains = db.execute("SELECT * FROM domains ORDER BY id").fetchall()
    if request.method == "POST":
        title = request.form["title"].strip() or p["title"]
        domain_id = int(request.form["domain_id"])
        slug = unique_page_slug(domain_id, title, exclude_id=pid)
        now = now_str()
        author = request.form.get("author", "").strip()
        ptype = request.form.get("ptype", p["ptype"] or "concept")
        # 담당/타입이 바뀌면 이전 경로의 파일 정리
        old = db.execute("SELECT p.*, d.slug dslug FROM pages p JOIN domains d ON d.id=p.domain_id "
                         "WHERE p.id=?", (pid,)).fetchone()
        db.execute(
            "UPDATE pages SET domain_id=?,title=?,slug=?,ptype=?,tags=?,summary=?,body_md=?,"
            "author=?,source_ids=?,updated_at=? WHERE id=?",
            (domain_id, title, slug, ptype if ptype in PTYPE_NAME else "concept",
             request.form.get("tags", "").strip(),
             request.form.get("summary", "").strip(), request.form.get("body_md", ""),
             author, request.form.get("source_ids", "").strip(), now, pid))
        db.execute("INSERT INTO revisions(page_id,title,body_md,author,saved_at) VALUES(?,?,?,?,?)",
                   (pid, title, request.form.get("body_md", ""), author, now))
        db.commit()
        if old:
            oldf = WIKI_DIR / old["dslug"] / (old["ptype"] or "concept") / f"{old['slug']}.md"
            if oldf.exists():
                oldf.unlink()
        write_page_file(pid)
        add_log("edit", title, "", author)
        flash("수정 저장 완료", "ok")
        return redirect(url_for("page_view", pid=pid))
    return render_template("page_edit.html", p=p, domains=domains)


@app.route("/page/<int:pid>/delete", methods=["POST"])
def page_delete(pid):
    db = get_db()
    p = db.execute("SELECT p.*, d.slug dslug FROM pages p JOIN domains d ON d.id=p.domain_id "
                   "WHERE p.id=?", (pid,)).fetchone()
    if p:
        db.execute("DELETE FROM revisions WHERE page_id=?", (pid,))
        db.execute("DELETE FROM pages WHERE id=?", (pid,))
        db.execute("DELETE FROM chunks WHERE kind='page' AND ref_id=?", (pid,))
        db.commit()
        f = WIKI_DIR / p["dslug"] / (p["ptype"] or "concept") / f"{p['slug']}.md"
        if f.exists():
            f.unlink()
        add_log("delete", p["title"], "")
        flash("페이지 삭제됨", "ok")
    return redirect(url_for("index"))


@app.route("/page/<int:pid>/history")
def page_history(pid):
    db = get_db()
    p = db.execute("SELECT * FROM pages WHERE id=?", (pid,)).fetchone()
    if not p:
        abort(404)
    revs = db.execute("SELECT * FROM revisions WHERE page_id=? ORDER BY id DESC", (pid,)).fetchall()
    return render_template("page_history.html", p=p, revs=revs)


@app.route("/page/<int:pid>/rev/<int:rid>")
def page_rev(pid, rid):
    db = get_db()
    p = db.execute("SELECT * FROM pages WHERE id=?", (pid,)).fetchone()
    r = db.execute("SELECT * FROM revisions WHERE id=? AND page_id=?", (rid, pid)).fetchone()
    if not p or not r:
        abort(404)
    return render_template("page_rev.html", p=p, r=r)


@app.route("/page/<int:pid>/raw")
def page_raw(pid):
    db = get_db()
    p = db.execute("SELECT p.*, d.name dname FROM pages p JOIN domains d ON d.id=p.domain_id "
                   "WHERE p.id=?", (pid,)).fetchone()
    if not p:
        abort(404)
    content = page_frontmatter(p, p["dname"]) + (p["body_md"] or "")
    return Response(content, mimetype="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={p['slug']}.md"})


# ---------------------------------------------------------------- 라우트: 소스 (업로드/인제스트)
@app.route("/upload", methods=["POST"])
def upload():
    db = get_db()
    domain_id = int(request.form["domain_id"])
    d = db.execute("SELECT * FROM domains WHERE id=?", (domain_id,)).fetchone()
    if not d:
        abort(400)
    files = request.files.getlist("file")
    ok, skip = 0, []
    for f in files:
        if not f or not f.filename:
            continue
        orig = f.filename
        ext = Path(orig).suffix.lower()
        if ext not in ALLOWED_EXT:
            skip.append(f"{orig} (지원 안 하는 형식)")
            continue
        safe = secure_filename(orig)
        if not Path(safe).stem:
            safe = "file" + ext
        ddir = SRC_DIR / d["slug"]
        ddir.mkdir(parents=True, exist_ok=True)
        cur = db.execute(
            "INSERT INTO sources(domain_id,filename,stored_name,filetype,description,uploader,created_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (domain_id, orig, "", "", request.form.get("description", "").strip(),
             request.form.get("uploader", "").strip(), now_str()))
        sid = cur.lastrowid
        stored = f"{sid}_{safe}"
        path = ddir / stored
        f.save(str(path))
        ftype, text, warn = extract_source(path)
        db.execute("UPDATE sources SET stored_name=?, filetype=?, extracted_text=? WHERE id=?",
                   (stored, ftype, text or "", sid))
        db.commit()
        index_target("source", sid)
        if warn:
            flash(f"{orig}: {warn}", "err")
        ok += 1
    if ok:
        add_log("upload", f"{d['name']} 소스 {ok}건",
                request.form.get("description", "").strip(),
                request.form.get("uploader", "").strip())
        flash(f"소스 {ok}건 업로드 완료 — 소스 상세에서 [Ingest] 돌려서 위키에 반영해라", "ok")
    for s in skip:
        flash(s, "err")
    return redirect(url_for("domain_view", slug=d["slug"]))


@app.route("/source/<int:sid>")
def source_view(sid):
    db = get_db()
    s = db.execute("SELECT s.*, d.name dname, d.slug dslug FROM sources s "
                   "JOIN domains d ON d.id=s.domain_id WHERE s.id=?", (sid,)).fetchone()
    if not s:
        abort(404)
    templates = db.execute("SELECT * FROM templates ORDER BY id").fetchall()
    return render_template("source_view.html", s=s, templates=templates)


@app.route("/source/<int:sid>/file")
def source_file(sid):
    db = get_db()
    s = db.execute("SELECT s.*, d.slug dslug FROM sources s JOIN domains d ON d.id=s.domain_id "
                   "WHERE s.id=?", (sid,)).fetchone()
    if not s:
        abort(404)
    path = SRC_DIR / s["dslug"] / s["stored_name"]
    if not path.exists():
        abort(404)
    return send_file(str(path), download_name=s["filename"])


@app.route("/source/<int:sid>/desc", methods=["POST"])
def source_desc(sid):
    db = get_db()
    db.execute("UPDATE sources SET description=? WHERE id=?",
               (request.form.get("description", "").strip(), sid))
    db.commit()
    index_target("source", sid)
    flash("설명 저장됨", "ok")
    return redirect(url_for("source_view", sid=sid))


@app.route("/source/<int:sid>/delete", methods=["POST"])
def source_delete(sid):
    db = get_db()
    s = db.execute("SELECT s.*, d.slug dslug FROM sources s JOIN domains d ON d.id=s.domain_id "
                   "WHERE s.id=?", (sid,)).fetchone()
    if s:
        path = SRC_DIR / s["dslug"] / s["stored_name"]
        if path.exists():
            path.unlink()
        db.execute("DELETE FROM sources WHERE id=?", (sid,))
        db.execute("DELETE FROM chunks WHERE kind='source' AND ref_id=?", (sid,))
        db.commit()
        flash("소스 삭제됨", "ok")
        return redirect(url_for("domain_view", slug=s["dslug"]))
    return redirect(url_for("index"))


@app.route("/source/<int:sid>/draft", methods=["POST"])
def source_draft(sid):
    """LLM으로 소스 → 위키 초안 생성"""
    db = get_db()
    s = db.execute("SELECT s.*, d.slug dslug FROM sources s JOIN domains d ON d.id=s.domain_id "
                   "WHERE s.id=?", (sid,)).fetchone()
    if not s:
        abort(404)
    tpl = db.execute("SELECT * FROM templates WHERE id=?",
                     (int(request.form["template_id"]),)).fetchone()
    sections = json.loads(tpl["sections"]) if tpl else []
    try:
        draft = llm_draft_from_source(s, sections)
    except RuntimeError as e:
        flash(str(e), "err")
        return redirect(url_for("source_view", sid=sid))
    token = secrets.token_hex(8)
    DRAFT_CACHE[token] = f"{draft}\n\n---\n\n> 참고 소스: #{s['id']} {s['filename']} (LLM 초안 — 검토 필수)"
    flash("LLM 초안 생성 완료. 검토 후 저장해라.", "ok")
    return redirect(url_for("page_new", domain=s["dslug"], draft=token,
                            title=Path(s["filename"]).stem))


# ---------------------------------------------------------------- 라우트: INGEST (카파시 핵심 연산)
INGEST_CACHE = {}


@app.route("/source/<int:sid>/ingest", methods=["POST"])
def source_ingest(sid):
    """카파시 ingest — 소스 1건을 위키 전체에 반영:
       ① 소스 요약 페이지 생성  ② 관련 기존 페이지 갱신안 생성  ③ 검토 후 적용 + 로그"""
    db = get_db()
    s = db.execute("SELECT s.*, d.slug dslug, d.name dname FROM sources s "
                   "JOIN domains d ON d.id=s.domain_id WHERE s.id=?", (sid,)).fetchone()
    if not s:
        abort(404)
    scope = request.form.get("scope", "domain")
    fanout = max(1, min(int(request.form.get("fanout", 5)), 15))
    try:
        summary_md = llm_source_summary(s)
    except RuntimeError as e:
        flash(str(e), "err")
        return redirect(url_for("source_view", sid=sid))

    # 관련 기존 페이지 탐색 (소스 텍스트를 질의로)
    probe = f"{s['filename']} {s['description']} {(s['extracted_text'] or '')[:1500]}"
    did = None if scope == "all" else s["domain_id"]
    cands = [d for _, d in retrieve(probe, k=fanout, domain_id=did, include_sources=False)]
    updates, errors = [], []
    for c in cands:
        pg = db.execute("SELECT * FROM pages WHERE id=?", (c["id"],)).fetchone()
        if not pg:
            continue
        try:
            out = llm_page_update(s, pg)
        except RuntimeError as e:
            errors.append(f"{pg['title']}: {e}")
            continue
        if out.strip().upper().startswith("NO_UPDATE"):
            updates.append({"pageId": pg["id"], "title": pg["title"], "skip": True,
                            "changeSummary": "변경 불필요 (LLM 판단)", "newBody": ""})
            continue
        cs, body = "", out
        m = re.search(r"CHANGE_SUMMARY:\s*(.*?)\n", out)
        if m:
            cs = m.group(1).strip()
        if "---BODY---" in out:
            body = out.split("---BODY---", 1)[1].strip()
        updates.append({"pageId": pg["id"], "title": pg["title"], "skip": False,
                        "changeSummary": cs or "(요약 없음)", "newBody": body,
                        "oldLen": len(pg["body_md"] or ""), "newLen": len(body)})
    for e in errors:
        flash(e, "err")
    token = secrets.token_hex(8)
    if len(INGEST_CACHE) > 50:
        INGEST_CACHE.clear()
    INGEST_CACHE[token] = {"sourceId": sid, "summaryMd": summary_md, "updates": updates,
                           "domainSlug": s["dslug"], "filename": s["filename"]}
    return redirect(url_for("ingest_review", token=token))


@app.route("/ingest/<token>")
def ingest_review(token):
    data = INGEST_CACHE.get(token)
    if not data:
        flash("ingest 결과가 만료됐다. 다시 실행해라.", "err")
        return redirect(url_for("index"))
    db = get_db()
    s = db.execute("SELECT s.*, d.name dname FROM sources s JOIN domains d ON d.id=s.domain_id "
                   "WHERE s.id=?", (data["sourceId"],)).fetchone()
    return render_template("ingest.html", token=token, d=data, s=s)


@app.route("/ingest/<token>/apply", methods=["POST"])
def ingest_apply(token):
    data = INGEST_CACHE.get(token)
    if not data:
        flash("ingest 결과가 만료됐다.", "err")
        return redirect(url_for("index"))
    db = get_db()
    s = db.execute("SELECT * FROM sources WHERE id=?", (data["sourceId"],)).fetchone()
    actor = request.form.get("actor", "").strip()
    now = now_str()
    made, touched = 0, 0

    # ① 소스 요약 페이지
    if request.form.get("make_summary"):
        title = request.form.get("summary_title", "").strip() or f"소스: {data['filename']}"
        body = request.form.get("summary_body", "").strip()
        slug = unique_page_slug(s["domain_id"], title)
        cur = db.execute(
            "INSERT INTO pages(domain_id,title,slug,ptype,tags,summary,body_md,author,"
            "source_ids,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (s["domain_id"], title, slug, "source", request.form.get("summary_tags", "").strip(),
             (s["description"] or f"{data['filename']} 요약")[:200], body, actor,
             str(s["id"]), now, now))
        pid = cur.lastrowid
        db.execute("INSERT INTO revisions(page_id,title,body_md,author,saved_at) VALUES(?,?,?,?,?)",
                   (pid, title, body, actor, now))
        db.commit()
        write_page_file(pid)
        made = 1

    # ② 기존 페이지 갱신
    for u in data["updates"]:
        if u["skip"] or not request.form.get(f"apply_{u['pageId']}"):
            continue
        body = request.form.get(f"body_{u['pageId']}", "").strip()
        if not body:
            continue
        pg = db.execute("SELECT * FROM pages WHERE id=?", (u["pageId"],)).fetchone()
        if not pg:
            continue
        srcs = {x for x in (pg["source_ids"] or "").split(",") if x}
        srcs.add(str(s["id"]))
        db.execute("UPDATE pages SET body_md=?, source_ids=?, updated_at=? WHERE id=?",
                   (body, ",".join(sorted(srcs)), now, u["pageId"]))
        db.execute("INSERT INTO revisions(page_id,title,body_md,author,saved_at) VALUES(?,?,?,?,?)",
                   (u["pageId"], pg["title"], body, actor or "ingest", now))
        db.commit()
        write_page_file(u["pageId"])
        touched += 1

    add_log("ingest", data["filename"],
            f"소스 #{s['id']} 반영 — 요약 페이지 {made}건 생성, 기존 페이지 {touched}건 갱신", actor)
    INGEST_CACHE.pop(token, None)
    flash(f"ingest 완료 — 요약 페이지 {made}건, 기존 페이지 {touched}건 갱신", "ok")
    return redirect(url_for("domain_view", slug=data["domainSlug"]))


# ---------------------------------------------------------------- 라우트: index / log
@app.route("/catalog")
def catalog():
    db = get_db()
    groups = []
    for key, name, desc in PTYPES:
        rows = db.execute(
            "SELECT p.*, d.name dname, d.slug dslug FROM pages p JOIN domains d ON d.id=p.domain_id "
            "WHERE p.ptype=? ORDER BY d.id, p.title", (key,)).fetchall()
        groups.append({"key": key, "name": name, "desc": desc, "rows": rows})
    return render_template("catalog.html", groups=groups)


@app.route("/catalog/index.md")
def catalog_md():
    return Response(build_index_md(), mimetype="text/markdown; charset=utf-8")


@app.route("/log")
def log_view():
    db = get_db()
    rows = db.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 300").fetchall()
    return render_template("log.html", rows=rows)


# ---------------------------------------------------------------- 라우트: 담당 노트북 대화 (Open Notebook 스타일)
@app.route("/domain/<slug>/ask", methods=["POST"])
def domain_ask(slug):
    """선택한 소스 + 담당 위키를 근거로 질문 (NotebookLM/Open Notebook 방식)"""
    db = get_db()
    d = db.execute("SELECT * FROM domains WHERE slug=?", (slug,)).fetchone()
    if not d:
        abort(404)
    question = request.form.get("question", "").strip()
    sel_ids = [int(x) for x in request.form.getlist("src") if x.isdigit()]
    answer = None
    if question:
        ctx_parts = []
        if sel_ids:
            marks = ",".join("?" * len(sel_ids))
            for s in db.execute(
                    f"SELECT * FROM sources WHERE id IN ({marks}) AND domain_id=?",
                    (*sel_ids, d["id"])):
                body = (s["extracted_text"] or s["description"] or "")[:4000]
                ctx_parts.append((1.0, {"kind": "source", "id": s["id"],
                                        "title": s["filename"], "domain": d["name"],
                                        "text": body}))
        # 담당 위키 페이지도 하이브리드 검색으로 보강
        for sc, doc in retrieve(question, k=3, domain_id=d["id"],
                                include_sources=not sel_ids):
            ctx_parts.append((sc, doc))
        try:
            answer = llm_answer(question, ctx_parts[:8])
        except RuntimeError as e:
            flash(str(e), "err")
    pages = db.execute("SELECT * FROM pages WHERE domain_id=? ORDER BY updated_at DESC",
                       (d["id"],)).fetchall()
    sources = db.execute("SELECT * FROM sources WHERE domain_id=? ORDER BY id DESC",
                         (d["id"],)).fetchall()
    templates = db.execute(
        "SELECT * FROM templates WHERE domain_id IS NULL OR domain_id=? ORDER BY id",
        (d["id"],)).fetchall()
    return render_template("domain.html", d=d, pages=pages, sources=sources,
                           templates=templates, question=question, answer=answer,
                           sel_ids=sel_ids)


@app.route("/domain/<slug>/save-note", methods=["POST"])
def domain_save_note(slug):
    """대화 답변을 노트(위키 페이지) 초안으로 저장 — 검토 후 확정"""
    db = get_db()
    d = db.execute("SELECT * FROM domains WHERE slug=?", (slug,)).fetchone()
    if not d:
        abort(404)
    question = request.form.get("question", "").strip()
    answer = request.form.get("answer", "").strip()
    if not answer:
        flash("저장할 답변이 없다", "err")
        return redirect(url_for("domain_view", slug=slug))
    if len(DRAFT_CACHE) > 200:
        DRAFT_CACHE.clear()
    token = secrets.token_hex(8)
    DRAFT_CACHE[token] = (f"> 질문: {question}\n\n{answer}\n\n---\n\n"
                          f"> LLM 대화에서 저장된 노트 — 담당자 검토 필수")
    return redirect(url_for("page_new", domain=slug, draft=token,
                            title=question[:60]))


# ---------------------------------------------------------------- 라우트: 검색/QA/린트
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    results = []
    if q:
        results = retrieve(q, k=20)
    return render_template("search.html", q=q, results=results, desc=retrieval_desc())


@app.route("/ask", methods=["GET", "POST"])
def ask():
    answer, question, used = None, "", []
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        if question:
            docs = retrieve(question, k=5)
            used = docs
            try:
                answer = llm_answer(question, docs)
            except RuntimeError as e:
                flash(str(e), "err")
    return render_template("ask.html", question=question, answer=answer, used=used,
                           desc=retrieval_desc())


@app.route("/lint")
def lint():
    issues = run_lint()
    return render_template("lint.html", issues=issues, llm_report=None)


@app.route("/lint/llm", methods=["POST"])
def lint_llm():
    db = get_db()
    pages = db.execute("SELECT p.id,p.title,p.summary,d.name dname FROM pages p "
                       "JOIN domains d ON d.id=p.domain_id").fetchall()
    listing = "\n".join(f"- [page#{p['id']}] ({p['dname']}) {p['title']}: {p['summary']}"
                        for p in pages)
    try:
        report = llm_chat([
            {"role": "system", "content":
                "너는 사내 지식위키 품질 검수자다. 아래 페이지 목록(제목+한줄요약)을 보고 "
                "① 서로 모순되어 보이는 페이지 쌍 ② 중복 주제로 통합이 필요한 페이지 "
                "③ 비어 보이는 주제(있어야 하는데 없는 페이지)를 한국어로 간결하게 보고해라."},
            {"role": "user", "content": listing or "(페이지 없음)"}], max_tokens=1500)
    except RuntimeError as e:
        flash(str(e), "err")
        return redirect(url_for("lint"))
    issues = run_lint()
    return render_template("lint.html", issues=issues, llm_report=report)


# ---------------------------------------------------------------- 라우트: 검색 관리
@app.route("/retrieval")
def retrieval_view():
    return render_template("retrieval.html", stats=index_stats(), desc=retrieval_desc(),
                           embed_ok=embed_ready(), rerank_ok=rerank_ready(),
                           has_numpy=_np is not None)


@app.route("/retrieval/reindex", methods=["POST"])
def retrieval_reindex():
    do_embed = bool(request.form.get("with_embed"))
    if do_embed and not embed_ready():
        flash("임베딩 백엔드가 설정 안 됐다. 청크만 재생성한다.", "err")
        do_embed = False
    n = reindex_all(do_embed)
    st = index_stats()
    add_log("reindex", f"청크 {n}건", f"임베딩 {st['embedded']}/{st['chunks']}")
    flash(f"재색인 완료 — 청크 {n}건, 임베딩 {st['embedded']}건", "ok")
    return redirect(url_for("retrieval_view"))


@app.route("/retrieval/test", methods=["POST"])
def retrieval_test():
    """같은 질의를 BM25 단독 / 현재 설정으로 나란히 돌려 차이를 눈으로 본다"""
    q = request.form.get("q", "").strip()
    base = cur = []
    if q:
        base = retrieve(q, k=5, force_mode="bm25")
        cur = retrieve(q, k=5)
    return render_template("retrieval.html", stats=index_stats(), desc=retrieval_desc(),
                           embed_ok=embed_ready(), rerank_ok=rerank_ready(),
                           has_numpy=_np is not None, q=q, base=base, cur=cur)


# ---------------------------------------------------------------- 라우트: 평가 하네스
@app.route("/eval")
def eval_view():
    db = get_db()
    items = db.execute("SELECT * FROM evalset ORDER BY id").fetchall()
    runs = db.execute("SELECT * FROM evalruns ORDER BY id DESC LIMIT 20").fetchall()
    pages = db.execute("SELECT p.id,p.title,d.name dname FROM pages p "
                       "JOIN domains d ON d.id=p.domain_id ORDER BY d.id,p.title").fetchall()
    return render_template("eval.html", items=items, runs=runs, pages=pages,
                           desc=retrieval_desc())


@app.route("/eval/add", methods=["POST"])
def eval_add():
    db = get_db()
    q = request.form.get("question", "").strip()
    if q:
        db.execute("INSERT INTO evalset(question,expect,note,created_at) VALUES(?,?,?,?)",
                   (q, ",".join(request.form.getlist("expect")),
                    request.form.get("note", "").strip(), now_str()))
        db.commit()
        flash("골든셋에 추가됨", "ok")
    return redirect(url_for("eval_view"))


@app.route("/eval/<int:eid>/delete", methods=["POST"])
def eval_delete(eid):
    db = get_db()
    db.execute("DELETE FROM evalset WHERE id=?", (eid,))
    db.commit()
    return redirect(url_for("eval_view"))


@app.route("/eval/import", methods=["POST"])
def eval_import():
    """CSV 임포트 — 헤더: question,expect(page id ;구분),note"""
    f = request.files.get("file")
    if not f or not f.filename:
        flash("CSV 파일을 골라라", "err")
        return redirect(url_for("eval_view"))
    db = get_db()
    raw = f.read()
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            txt = raw.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        txt = raw.decode("utf-8", errors="replace")
    n = 0
    for row in csv.DictReader(io.StringIO(txt)):
        q = (row.get("question") or "").strip()
        if not q:
            continue
        exp = (row.get("expect") or "").replace(";", ",").replace(" ", "")
        db.execute("INSERT INTO evalset(question,expect,note,created_at) VALUES(?,?,?,?)",
                   (q, exp, (row.get("note") or "").strip(), now_str()))
        n += 1
    db.commit()
    flash(f"{n}건 임포트됨", "ok")
    return redirect(url_for("eval_view"))


def _judge(question, answer, ctx):
    """LLM-as-judge — faithfulness / answer relevance (각 0~1)"""
    sys_p = ("너는 RAG 답변 채점자다. 아래를 읽고 JSON만 출력해라. 설명 금지.\n"
             '{"faithfulness": 0.0~1.0, "answer_relevance": 0.0~1.0}\n'
             "faithfulness: 답변 내용이 주어진 근거로 뒷받침되는 정도 (지어낸 게 있으면 낮게)\n"
             "answer_relevance: 답변이 질문에 실제로 답한 정도")
    user_p = f"=== 근거 ===\n{ctx[:6000]}\n\n=== 질문 ===\n{question}\n\n=== 답변 ===\n{answer[:3000]}"
    out = llm_chat([{"role": "system", "content": sys_p},
                    {"role": "user", "content": user_p}], max_tokens=200, temperature=0.0)
    m = re.search(r"\{[^}]*\}", out)
    if not m:
        return None, None
    try:
        d = json.loads(m.group(0))
        return float(d.get("faithfulness", 0)), float(d.get("answer_relevance", 0))
    except (ValueError, TypeError):
        return None, None


@app.route("/eval/run", methods=["POST"])
def eval_run():
    db = get_db()
    items = db.execute("SELECT * FROM evalset ORDER BY id").fetchall()
    if not items:
        flash("골든셋이 비어있다. 질문을 먼저 등록해라.", "err")
        return redirect(url_for("eval_view"))
    k = int(request.form.get("k", 5))
    mode = request.form.get("mode", "")          # '' = 현재 설정
    with_gen = bool(request.form.get("with_gen")) and llm_ready()
    force = mode if mode in ("bm25", "hybrid") else None
    label = request.form.get("label", "").strip()

    hits, rrs, precs, faiths, arels, detail = [], [], [], [], [], []
    for it in items:
        expect = {int(x) for x in (it["expect"] or "").split(",") if x.strip().isdigit()}
        got = retrieve(it["question"], k=k, force_mode=force)
        got_pages = [d["id"] for _, d in got if d["kind"] == "page"]
        row = {"q": it["question"], "expect": sorted(expect), "got": got_pages}
        if expect:
            hit = 1.0 if expect & set(got_pages) else 0.0
            hits.append(hit)
            rr = 0.0
            for i, pid in enumerate(got_pages):
                if pid in expect:
                    rr = 1.0 / (i + 1)
                    break
            rrs.append(rr)
            precs.append(len(expect & set(got_pages)) / max(1, len(got_pages)))
            row.update({"hit": hit, "rr": round(rr, 3)})
        if with_gen:
            ctx = "\n\n".join((d.get("chunkText") or d.get("text") or "")[:2000]
                              for _, d in got)
            try:
                ans = llm_answer(it["question"], got)
                f, a = _judge(it["question"], ans, ctx)
                if f is not None:
                    faiths.append(f)
                    arels.append(a)
                    row.update({"faith": f, "arel": a, "answer": ans[:400]})
            except RuntimeError as e:
                row["error"] = str(e)[:120]
        detail.append(row)

    def avg(x):
        return round(sum(x) / len(x), 4) if x else -1.0

    cfg = retrieval_desc() if not force else f"강제:{force}"
    cur = db.execute(
        "INSERT INTO evalruns(label,config,n,hit,mrr,ctxp,faith,arel,detail,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (label, f"{cfg} · k={k}", len(items), avg(hits), avg(rrs), avg(precs),
         avg(faiths), avg(arels), json.dumps(detail, ensure_ascii=False), now_str()))
    db.commit()
    add_log("eval", label or cfg, f"{len(items)}건 · Hit@{k}={avg(hits)} MRR={avg(rrs)}")
    flash(f"평가 완료 — Hit@{k} {avg(hits)} / MRR {avg(rrs)}", "ok")
    return redirect(url_for("eval_run_view", rid=cur.lastrowid))


@app.route("/eval/run/<int:rid>")
def eval_run_view(rid):
    db = get_db()
    r = db.execute("SELECT * FROM evalruns WHERE id=?", (rid,)).fetchone()
    if not r:
        abort(404)
    titles = {p["id"]: p["title"] for p in db.execute("SELECT id,title FROM pages")}
    return render_template("eval_run.html", r=r, detail=json.loads(r["detail"] or "[]"),
                           titles=titles)


# ---------------------------------------------------------------- 라우트: schema
@app.route("/schema")
def schema_view():
    return render_template("schema.html", content=schema_text())


@app.route("/schema/edit", methods=["GET", "POST"])
def schema_edit():
    if request.method == "POST":
        SCHEMA_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCHEMA_FILE.write_text(request.form.get("content", ""), encoding="utf-8")
        flash("작성 규칙 저장됨", "ok")
        return redirect(url_for("schema_view"))
    return render_template("schema_edit.html", content=schema_text())


# ---------------------------------------------------------------- 라우트: 설정
@app.route("/settings", methods=["GET", "POST"])
def settings_view():
    db = get_db()
    if request.method == "POST":
        for k in ("site_name", "llm_base_url", "llm_model", "llm_api_key",
                  "retrieval_mode", "embed_backend", "embed_base_url", "embed_model",
                  "embed_api_key", "rerank_backend", "rerank_base_url", "rerank_model",
                  "rerank_pool", "chunk_max"):
            if k in request.form:
                set_setting(k, request.form[k].strip())
        if request.form.get("retrieval_mode") == "hybrid" and not embed_ready():
            flash("하이브리드로 설정했지만 임베딩 백엔드가 비어있다 — BM25 단독으로 동작한다.", "err")
        elif "retrieval_mode" in request.form:
            flash("설정 저장됨 — 임베딩/청크 설정을 바꿨으면 [검색엔진]에서 재색인해라", "ok")
        else:
            flash("설정 저장됨", "ok")
        return redirect(url_for("settings_view"))
    domains = db.execute(
        "SELECT d.*, (SELECT COUNT(*) FROM pages p WHERE p.domain_id=d.id) pcnt, "
        "(SELECT COUNT(*) FROM sources s WHERE s.domain_id=d.id) scnt "
        "FROM domains d ORDER BY d.id").fetchall()
    templates = db.execute("SELECT * FROM templates ORDER BY id").fetchall()
    tpl_lines = {}
    for t in templates:
        secs = json.loads(t["sections"])
        tpl_lines[t["id"]] = "\n".join(f"{s['title']} :: {s['guide']}" for s in secs)
    return render_template("settings.html", domains=domains, templates=templates,
                           tpl_lines=tpl_lines,
                           s={k: get_setting(k) for k in
                              ("site_name", "llm_base_url", "llm_model", "llm_api_key",
                               "retrieval_mode", "embed_backend", "embed_base_url",
                               "embed_model", "embed_api_key", "rerank_backend",
                               "rerank_base_url", "rerank_model", "rerank_pool",
                               "chunk_max")})


@app.route("/settings/test-llm", methods=["POST"])
def settings_test_llm():
    try:
        # ★20 으로 두면 사고 모델이 사고에만 다 쓰고 본문이 비어 '실패'로 보인다.
        out = llm_chat([{"role": "user", "content": "연결 확인. '연결 정상'이라고만 답해라."}],
                       max_tokens=200)
        flash("LLM 연결 성공: {}".format(str(out or "")[:80]), "ok")
    except RuntimeError as e:
        flash(f"LLM 연결 실패: {e}", "err")
    return redirect(url_for("settings_view"))


def _parse_tpl_lines(raw):
    sections = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if "::" in ln:
            t, gd = ln.split("::", 1)
        else:
            t, gd = ln, ""
        sections.append({"title": t.strip(), "guide": gd.strip()})
    return sections


@app.route("/settings/domain/add", methods=["POST"])
def domain_add():
    db = get_db()
    name = request.form.get("name", "").strip()
    if name:
        slug = slugify(name)
        try:
            db.execute("INSERT INTO domains(slug,name,description,created_at) VALUES(?,?,?,?)",
                       (slug, name, request.form.get("description", "").strip(), now_str()))
            db.commit()
            flash(f"담당 '{name}' 추가됨", "ok")
        except sqlite3.IntegrityError:
            flash("같은 이름(슬러그)의 담당이 이미 있다", "err")
    return redirect(url_for("settings_view"))


@app.route("/settings/domain/<int:did>/edit", methods=["POST"])
def domain_edit(did):
    db = get_db()
    db.execute("UPDATE domains SET name=?, description=? WHERE id=?",
               (request.form.get("name", "").strip(),
                request.form.get("description", "").strip(), did))
    db.commit()
    flash("담당 수정됨", "ok")
    return redirect(url_for("settings_view"))


@app.route("/settings/domain/<int:did>/delete", methods=["POST"])
def domain_delete(did):
    db = get_db()
    cnt = db.execute("SELECT (SELECT COUNT(*) FROM pages WHERE domain_id=?) + "
                     "(SELECT COUNT(*) FROM sources WHERE domain_id=?) c", (did, did)).fetchone()["c"]
    if cnt:
        flash("페이지/소스가 남아있는 담당은 삭제 불가. 먼저 옮기거나 삭제해라.", "err")
    else:
        db.execute("DELETE FROM domains WHERE id=?", (did,))
        db.commit()
        flash("담당 삭제됨", "ok")
    return redirect(url_for("settings_view"))


@app.route("/settings/template/add", methods=["POST"])
def template_add():
    db = get_db()
    name = request.form.get("name", "").strip()
    sections = _parse_tpl_lines(request.form.get("sections", ""))
    if name and sections:
        db.execute("INSERT INTO templates(domain_id,name,sections,created_at) VALUES(NULL,?,?,?)",
                   (name, json.dumps(sections, ensure_ascii=False), now_str()))
        db.commit()
        flash(f"양식 '{name}' 추가됨", "ok")
    else:
        flash("양식 이름과 섹션(한 줄에 '섹션명 :: 가이드')을 입력해라", "err")
    return redirect(url_for("settings_view"))


@app.route("/settings/template/<int:tid>/edit", methods=["POST"])
def template_edit(tid):
    db = get_db()
    sections = _parse_tpl_lines(request.form.get("sections", ""))
    if sections:
        db.execute("UPDATE templates SET name=?, sections=? WHERE id=?",
                   (request.form.get("name", "").strip(),
                    json.dumps(sections, ensure_ascii=False), tid))
        db.commit()
        flash("양식 수정됨", "ok")
    return redirect(url_for("settings_view"))


@app.route("/settings/template/<int:tid>/delete", methods=["POST"])
def template_delete(tid):
    db = get_db()
    db.execute("DELETE FROM templates WHERE id=?", (tid,))
    db.commit()
    flash("양식 삭제됨", "ok")
    return redirect(url_for("settings_view"))


# ---------------------------------------------------------------- 라우트: export
@app.route("/export")
def export_view():
    return render_template("export.html")


@app.route("/export/zip")
def export_zip():
    sync_all_wiki_files()
    buf = io.BytesIO()
    db = get_db()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(WIKI_DIR.rglob("*.md")):
            z.write(f, f"wiki/{f.relative_to(WIKI_DIR)}")
        if SCHEMA_FILE.exists():
            z.write(SCHEMA_FILE, "schema/schema.md")
        # index.md / log.md 는 sync_all_wiki_files() 가 wiki/ 루트에 써둔 걸 위 루프가 포함
        # 소스 목록 CSV
        sio = io.StringIO()
        w = csv.writer(sio)
        w.writerow(["id", "domain", "filename", "filetype", "description", "uploader", "created_at"])
        for s in db.execute("SELECT s.*, d.name dname FROM sources s JOIN domains d ON d.id=s.domain_id"):
            w.writerow([s["id"], s["dname"], s["filename"], s["filetype"],
                        s["description"], s["uploader"], s["created_at"]])
        z.writestr("sources_index.csv", sio.getvalue())
        z.writestr("combined.md", _combined_md())
    buf.seek(0)
    return send_file(buf, download_name=f"llm-wiki-export-{datetime.now():%Y%m%d}.zip",
                     as_attachment=True, mimetype="application/zip")


def _combined_md():
    db = get_db()
    parts = ["# LLM-WIKI 전체 결합본 (LLM 학습/컨텍스트 주입용)",
             f"\n생성: {now_str()}\n", "---\n", "## 작성 규칙\n", schema_text(), "\n---\n"]
    for d in db.execute("SELECT * FROM domains ORDER BY id"):
        pages = db.execute("SELECT * FROM pages WHERE domain_id=? ORDER BY title", (d["id"],)).fetchall()
        if not pages:
            continue
        parts.append(f"\n# 담당: {d['name']}\n")
        for p in pages:
            parts.append(f"\n## {p['title']}\n")
            if p["summary"]:
                parts.append(f"> 요약: {p['summary']}\n")
            parts.append((p["body_md"] or "") + "\n")
    return "\n".join(parts)


@app.route("/export/combined")
def export_combined():
    return Response(_combined_md(), mimetype="text/markdown; charset=utf-8",
                    headers={"Content-Disposition":
                             f"attachment; filename=llm-wiki-combined-{datetime.now():%Y%m%d}.md"})


# ---------------------------------------------------------------- JSON API (MCP 연동용)
@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok", "time": now_str()})


@app.route("/api/domains")
def api_domains():
    db = get_db()
    rows = db.execute(
        "SELECT d.*, (SELECT COUNT(*) FROM pages p WHERE p.domain_id=d.id) pcnt, "
        "(SELECT COUNT(*) FROM sources s WHERE s.domain_id=d.id) scnt FROM domains d ORDER BY d.id").fetchall()
    return jsonify({"domains": [
        {"id": r["id"], "slug": r["slug"], "name": r["name"],
         "description": r["description"], "pageCount": r["pcnt"], "sourceCount": r["scnt"]}
        for r in rows]})


@app.route("/api/pages")
def api_pages():
    db = get_db()
    dom = request.args.get("domain")
    q = ("SELECT p.id,p.title,p.slug,p.tags,p.summary,p.author,p.updated_at,d.slug dslug,d.name dname "
         "FROM pages p JOIN domains d ON d.id=p.domain_id")
    args = []
    if dom:
        q += " WHERE d.slug=?"
        args.append(dom)
    q += " ORDER BY p.updated_at DESC"
    rows = db.execute(q, args).fetchall()
    return jsonify({"pages": [
        {"id": r["id"], "title": r["title"], "slug": r["slug"], "tags": r["tags"],
         "summary": r["summary"], "author": r["author"], "updatedAt": r["updated_at"],
         "domain": r["dname"], "domainSlug": r["dslug"]} for r in rows]})


@app.route("/api/page/<int:pid>")
def api_page(pid):
    db = get_db()
    r = db.execute("SELECT p.*, d.name dname, d.slug dslug FROM pages p "
                   "JOIN domains d ON d.id=p.domain_id WHERE p.id=?", (pid,)).fetchone()
    if not r:
        return jsonify({"isError": True, "message": "page not found"}), 404
    return jsonify({"id": r["id"], "title": r["title"], "slug": r["slug"],
                    "domain": r["dname"], "domainSlug": r["dslug"], "tags": r["tags"],
                    "summary": r["summary"], "author": r["author"],
                    "createdAt": r["created_at"], "updatedAt": r["updated_at"],
                    "bodyMd": r["body_md"]})


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    k = min(int(request.args.get("k", 5)), 20)
    if not q:
        return jsonify({"isError": True, "message": "q required"}), 400
    results = retrieve(q, k=k)
    return jsonify({"query": q, "retrieval": retrieval_desc(), "results": [
        {"score": round(s, 3), "kind": d["kind"], "id": d["id"], "title": d["title"],
         "domain": d["domain"], "summary": d.get("summary", ""),
         "snippet": (d.get("chunkText") or "")[:400]} for s, d in results]})


@app.route("/api/sources")
def api_sources():
    db = get_db()
    dom = request.args.get("domain")
    q = ("SELECT s.id,s.filename,s.filetype,s.description,s.uploader,s.created_at,d.slug dslug,d.name dname "
         "FROM sources s JOIN domains d ON d.id=s.domain_id")
    args = []
    if dom:
        q += " WHERE d.slug=?"
        args.append(dom)
    q += " ORDER BY s.id DESC"
    rows = db.execute(q, args).fetchall()
    return jsonify({"sources": [
        {"id": r["id"], "filename": r["filename"], "filetype": r["filetype"],
         "description": r["description"], "uploader": r["uploader"],
         "createdAt": r["created_at"], "domain": r["dname"], "domainSlug": r["dslug"]}
        for r in rows]})


@app.route("/api/source/<int:sid>")
def api_source(sid):
    db = get_db()
    r = db.execute("SELECT s.*, d.name dname, d.slug dslug FROM sources s "
                   "JOIN domains d ON d.id=s.domain_id WHERE s.id=?", (sid,)).fetchone()
    if not r:
        return jsonify({"isError": True, "message": "source not found"}), 404
    return jsonify({"id": r["id"], "filename": r["filename"], "filetype": r["filetype"],
                    "domain": r["dname"], "domainSlug": r["dslug"],
                    "description": r["description"], "uploader": r["uploader"],
                    "createdAt": r["created_at"],
                    "extractedText": (r["extracted_text"] or "")[:30000]})


@app.route("/api/ask", methods=["POST"])
def api_ask():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"isError": True, "message": "question required"}), 400
    docs = retrieve(question, k=5)
    try:
        answer = llm_answer(question, docs)
    except RuntimeError as e:
        return jsonify({"isError": True, "message": str(e)}), 502
    return jsonify({"question": question, "answer": answer,
                    "usedDocs": [{"kind": d["kind"], "id": d["id"], "title": d["title"]}
                                 for _, d in docs]})


# ---------------------------------------------------------------- 템플릿 (인라인, 외부 CDN 없음)
TPL = {}

TPL["layout.html"] = '''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ site_name }}</title>
<style>
:root{--bg:#f4f5f7;--card:#fff;--bd:#e2e4ea;--tx:#1f2430;--mut:#69707d;
 --acc:#3b5bdb;--acc2:#eef1fb;--ok:#0a7d33;--err:#c0342b;--warn:#b7791f;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);
 font-family:'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',system-ui,sans-serif;
 font-size:14.5px;line-height:1.65}
a{color:var(--acc);text-decoration:none} a:hover{text-decoration:underline}
header{position:sticky;top:0;z-index:10;background:var(--card);border-bottom:1px solid var(--bd);
 display:flex;align-items:center;gap:14px;padding:10px 20px;flex-wrap:wrap}
header .logo{font-weight:800;font-size:17px;color:var(--tx)}
header .logo b{color:var(--acc)}
header nav{display:flex;gap:2px;flex-wrap:wrap}
header nav a{padding:6px 10px;border-radius:8px;color:var(--tx);font-weight:600;font-size:13.5px}
header nav a:hover{background:var(--acc2);text-decoration:none}
.searchbox{margin-left:auto;display:flex;gap:6px}
.searchbox input{width:220px}
main{max-width:1240px;margin:22px auto;padding:0 20px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:18px 20px;margin-bottom:16px}
.grid{display:grid;gap:14px}
.g3{grid-template-columns:repeat(auto-fill,minmax(260px,1fr))}
.g4{grid-template-columns:repeat(auto-fill,minmax(200px,1fr))}
.nb-grid{display:grid;grid-template-columns:300px 1fr 320px;gap:14px;align-items:start}
@media(max-width:1000px){.nb-grid{grid-template-columns:1fr}}
.stat{text-align:center;padding:14px}
.stat .num{font-size:26px;font-weight:800;color:var(--acc)}
.stat .lbl{color:var(--mut);font-size:13px}
h1{font-size:22px;margin:4px 0 14px} h2{font-size:17px;margin:0 0 10px}
h3{font-size:15px;margin:14px 0 6px}
.mut{color:var(--mut);font-size:13px}
.chip{display:inline-block;background:var(--acc2);color:var(--acc);border-radius:20px;
 padding:1px 10px;font-size:12px;font-weight:700;margin-right:4px}
.chip.gray{background:#eee;color:#555}
.badge{display:inline-block;border-radius:6px;padding:0 7px;font-size:11.5px;font-weight:700;color:#fff}
.badge.page{background:var(--acc)} .badge.source{background:#7048b6}
.badge.text{background:#4a7} .badge.csv{background:#2a8} .badge.pdf{background:#c55}
.badge.image{background:#c81} .badge.other{background:#888}
input[type=text],input[type=password],select,textarea{width:100%;padding:8px 10px;border:1px solid var(--bd);
 border-radius:9px;font:inherit;background:#fff;color:var(--tx)}
textarea{resize:vertical}
label{font-weight:700;font-size:13px;display:block;margin:10px 0 4px}
label .g{font-weight:400;color:var(--mut)}
button,.btn{display:inline-block;background:var(--acc);color:#fff;border:0;border-radius:9px;
 padding:8px 16px;font:inherit;font-weight:700;cursor:pointer;font-size:13.5px;
 white-space:nowrap;flex-shrink:0}
button:disabled{opacity:.45;cursor:not-allowed}
button:hover,.btn:hover{opacity:.9;text-decoration:none}
.btn.sec{background:#fff;color:var(--tx);border:1px solid var(--bd)}
.btn.warn{background:var(--err)}
.btn.sm{padding:4px 10px;font-size:12.5px;border-radius:7px}
table.list{width:100%;border-collapse:collapse}
table.list th{color:var(--mut);font-size:12.5px;text-align:left;border-bottom:1px solid var(--bd);padding:6px 8px}
table.list td{border-bottom:1px solid #f0f1f4;padding:8px}
.flash{border-radius:10px;padding:10px 14px;margin-bottom:12px;font-weight:600}
.flash.ok{background:#e7f5ec;color:var(--ok)} .flash.err{background:#fdeceb;color:var(--err)}
.md h1,.md h2{border-bottom:1px solid var(--bd);padding-bottom:4px}
.md h2{font-size:18px;margin:22px 0 8px} .md h3{font-size:15.5px}
.md pre{background:#282c34;color:#e6e6e6;border-radius:10px;padding:12px 14px;overflow-x:auto;font-size:13px}
.md code{background:#eef0f4;border-radius:5px;padding:1px 5px;font-size:13px}
.md pre code{background:none;padding:0}
.md blockquote{border-left:4px solid var(--acc);background:var(--acc2);margin:10px 0;
 padding:8px 14px;border-radius:0 8px 8px 0}
.md table{border-collapse:collapse;font-size:13px}
.md th,.md td{border:1px solid var(--bd);padding:5px 9px}
.md th{background:#f2f3f6}
.tablewrap{overflow-x:auto}
.wikilink{font-weight:700}
.srcitem{display:flex;gap:8px;align-items:flex-start;padding:7px 4px;border-bottom:1px solid #f0f1f4}
.srcitem input{margin-top:4px}
.answer{background:var(--acc2);border:1px solid #d5dcf5;border-radius:12px;padding:14px 16px;margin-top:12px}
footer{max-width:1240px;margin:10px auto 30px;padding:0 20px;color:var(--mut);font-size:12.5px}
.right{text-align:right}
details summary{cursor:pointer;font-weight:700}
</style>
</head>
<body>
<header>
  <a class="logo" href="/">🏭 <b>{{ site_name }}</b></a>
  <nav>
    <a href="/">대시보드</a>
    {% for d in nav_domains %}<a href="/domain/{{ d.slug }}">{{ d.name }}</a>{% endfor %}
    <a href="/catalog">카탈로그</a>
    <a href="/ask">질문</a>
    <a href="/retrieval">검색엔진</a>
    <a href="/eval">평가</a>
    <a href="/lint">린트</a>
    <a href="/log">로그</a>
    <a href="/schema">작성규칙</a>
    <a href="/export">내보내기</a>
    <a href="/settings">설정</a>
  </nav>
  <form class="searchbox" action="/search" method="get">
    <input type="text" name="q" placeholder="위키/소스 검색 (BM25)" value="{{ request.args.get('q','') }}">
    <button>검색</button>
  </form>
</header>
<main>
{% with msgs = get_flashed_messages(with_categories=true) %}
  {% for cat, m in msgs %}<div class="flash {{ cat }}">{{ m }}</div>{% endfor %}
{% endwith %}
{% if not llm_ok %}<div class="flash err">⚠ LLM 미설정 — <a href="/settings">설정</a>에서 사내 OpenAI 호환 API 주소/모델을 입력하면 초안 생성·질문 기능이 켜진다. (위키 작성/검색은 LLM 없이도 동작)</div>{% endif %}
{% block content %}{% endblock %}
</main>
<footer>AMHS LLM-WIKI 지식정보 시스템 · Karpathy llm-wiki 3-layer(raw sources / wiki / schema) · 연산: ingest · query · lint · MCP: <code>mcp_server.py</code> → streamable-http :8020 · JSON API <code>/api/*</code></footer>
<script>
(function(){
 try{
  var k='llmwiki_author';
  document.querySelectorAll('input[name=author],input[name=uploader]').forEach(function(el){
    if(!el.value) el.value = localStorage.getItem(k)||'';
    el.addEventListener('change',function(){ localStorage.setItem(k, el.value); });
  });
 }catch(e){}
 document.querySelectorAll('form.danger').forEach(function(f){
  f.addEventListener('submit',function(e){ if(!confirm('정말 삭제할까? 되돌릴 수 없다.')) e.preventDefault(); });
 });
})();
</script>
</body></html>'''

TPL["index.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>대시보드</h1>
<div class="grid g4">
 <div class="card stat"><div class="num">{{ stats.domains }}</div><div class="lbl">담당(노트북)</div></div>
 <div class="card stat"><div class="num">{{ stats.pages }}</div><div class="lbl">위키 페이지</div></div>
 <div class="card stat"><div class="num">{{ stats.sources }}</div><div class="lbl">소스 자료</div></div>
 <div class="card stat"><div class="num">{{ stats.revisions }}</div><div class="lbl">리비전</div></div>
</div>
<h2 style="margin-top:20px">담당별 노트북</h2>
<div class="grid g3">
{% for d in dom_rows %}
 <div class="card">
   <h2><a href="/domain/{{ d.slug }}">{{ d.name }}</a></h2>
   <div class="mut">{{ d.description }}</div>
   <div style="margin-top:8px"><span class="chip">페이지 {{ d.pcnt }}</span><span class="chip gray">소스 {{ d.scnt }}</span></div>
 </div>
{% endfor %}
</div>
<div class="grid" style="grid-template-columns:1fr 1fr;margin-top:6px">
 <div class="card">
  <h2>최근 수정 페이지</h2>
  {% for p in recent_pages %}
    <div class="srcitem"><span class="badge page">{{ p.dname }}</span>
    <div><a href="/page/{{ p.id }}">{{ p.title }}</a><div class="mut">{{ p.updated_at }} · {{ p.author or '-' }}</div></div></div>
  {% else %}<div class="mut">아직 없음 — 담당 노트북에서 양식으로 작성해라</div>{% endfor %}
 </div>
 <div class="card">
  <h2>최근 소스</h2>
  {% for s in recent_sources %}
    <div class="srcitem"><span class="badge {{ s.filetype }}">{{ s.filetype }}</span>
    <div><a href="/source/{{ s.id }}">{{ s.filename }}</a><div class="mut">{{ s.dname }} · {{ s.created_at }}</div></div></div>
  {% else %}<div class="mut">아직 없음 — MD/PDF/이미지/TXT/CSV를 업로드해라</div>{% endfor %}
 </div>
</div>
{% endblock %}'''

TPL["domain.html"] = '''{% extends "layout.html" %}{% block content %}
{% set sel = sel_ids|default([]) %}
<h1>{{ d.name }} <span class="mut" style="font-size:14px">{{ d.description }}</span></h1>
<div class="nb-grid">
 <!-- 좌: 소스 패널 -->
 <div>
  <div class="card">
   <h2>소스 <span class="mut">({{ sources|length }})</span></h2>
   {% for s in sources %}
    <div class="srcitem">
     <input type="checkbox" name="src" value="{{ s.id }}" form="askform"
       {% if s.id in sel %}checked{% endif %}>
     <div><span class="badge {{ s.filetype }}">{{ s.filetype }}</span>
      <a href="/source/{{ s.id }}">{{ s.filename }}</a>
      <div class="mut">{{ s.created_at }}{% if s.uploader %} · {{ s.uploader }}{% endif %}</div></div>
    </div>
   {% else %}<div class="mut">소스 없음</div>{% endfor %}
  </div>
  <div class="card">
   <h2>소스 업로드</h2>
   <form action="/upload" method="post" enctype="multipart/form-data">
    <input type="hidden" name="domain_id" value="{{ d.id }}">
    <label>파일 <span class="g">(MD/PDF/이미지/TXT/CSV, 복수 선택 가능)</span></label>
    <input type="file" name="file" multiple required>
    <label>설명 <span class="g">(무슨 자료인지 한 줄)</span></label>
    <input type="text" name="description">
    <label>업로더</label>
    <input type="text" name="uploader">
    <div style="margin-top:10px"><button>업로드</button></div>
   </form>
  </div>
 </div>
 <!-- 중: 대화 패널 (Open Notebook 방식) -->
 <div class="card">
  <h2>💬 소스에게 질문</h2>
  <div class="mut">왼쪽에서 소스를 체크하고 질문해라. 체크 안 하면 이 담당의 위키·소스 전체에서 BM25로 찾아 답한다.</div>
  <form id="askform" action="/domain/{{ d.slug }}/ask" method="post">
   <label>질문</label>
   <textarea name="question" rows="3" placeholder="예: OO 알람 발생 시 조치 절차는?">{{ question|default('') }}</textarea>
   <div style="margin-top:10px"><button {% if not llm_ok %}disabled title="LLM 설정 필요"{% endif %}>질문하기</button></div>
  </form>
  {% if answer %}
   <div class="answer md">{{ answer|md|safe }}</div>
   <form action="/domain/{{ d.slug }}/save-note" method="post" style="margin-top:8px">
    <input type="hidden" name="question" value="{{ question }}">
    <textarea name="answer" style="display:none">{{ answer }}</textarea>
    <button class="btn sec">📝 이 답변을 노트(위키 초안)로 저장</button>
   </form>
  {% endif %}
 </div>
 <!-- 우: 노트(위키) 패널 -->
 <div>
  <div class="card">
   <h2>노트 / 위키 페이지 <span class="mut">({{ pages|length }})</span></h2>
   <form action="/page/new" method="get" style="display:flex;gap:6px;margin-bottom:10px">
    <input type="hidden" name="domain" value="{{ d.slug }}">
    <select name="template">
     {% for t in templates %}<option value="{{ t.id }}">{{ t.name }}</option>{% endfor %}
    </select>
    <button class="btn sm">양식으로 작성</button>
   </form>
   {% for p in pages %}
    <div class="srcitem"><div>
      <a href="/page/{{ p.id }}"><b>{{ p.title }}</b></a>
      {% if p.summary %}<div class="mut">{{ p.summary }}</div>{% endif %}
      <div class="mut">{{ p.updated_at }}{% if p.author %} · {{ p.author }}{% endif %}</div>
    </div></div>
   {% else %}<div class="mut">아직 노트 없음</div>{% endfor %}
  </div>
 </div>
</div>
{% endblock %}'''

TPL["page_form.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>새 페이지 작성</h1>
<div class="card">
 <form method="get" action="/page/new" style="display:flex;gap:8px;align-items:end;flex-wrap:wrap">
  <div><label>담당</label>
   <select name="domain">
    {% for dm in domains %}<option value="{{ dm.slug }}" {% if dm.slug==sel_domain %}selected{% endif %}>{{ dm.name }}</option>{% endfor %}
   </select></div>
  <div><label>양식 <span class="g">(비우면 자유 작성)</span></label>
   <select name="template">
    <option value="">— 자유 작성 —</option>
    {% for t in templates %}<option value="{{ t.id }}" {% if tpl and tpl.id==t.id %}selected{% endif %}>{{ t.name }}</option>{% endfor %}
   </select></div>
  <button class="btn sec">양식 불러오기</button>
 </form>
</div>
<div class="card">
 <form method="post" action="/page/new">
  <input type="hidden" name="mode" value="{{ 'form' if tpl else 'free' }}">
  {% if tpl %}<input type="hidden" name="template_id" value="{{ tpl.id }}">{% endif %}
  <div class="grid" style="grid-template-columns:2fr 1fr 1fr 1fr">
   <div><label>제목 *</label><input type="text" name="title" required value="{{ prefill_title }}"></div>
   <div><label>담당(FAB) *</label>
    <select name="domain_id">
     {% for dm in domains %}<option value="{{ dm.id }}" {% if dm.slug==sel_domain %}selected{% endif %}>{{ dm.name }}</option>{% endfor %}
    </select></div>
   <div><label>페이지 타입</label>
    <select name="ptype">
     {% for k, n, g in ptypes %}<option value="{{ k }}">{{ n }}</option>{% endfor %}
    </select></div>
   <div><label>작성자</label><input type="text" name="author"></div>
  </div>
  <label>한줄요약 * <span class="g">(검색·LLM 컨텍스트에 그대로 쓰인다)</span></label>
  <input type="text" name="summary">
  <label>태그 <span class="g">(쉼표 구분 — 설비/주제 구분에 쓴다)</span></label>
  <input type="text" name="tags" placeholder="예: OHT, AGV, CNV, MCS, 알람, 정체">
  {% if tpl %}
   <h3>📋 {{ tpl.name }}</h3>
   {% for sec in sections %}
    <label>{{ sec.title }} <span class="g">— {{ sec.guide }}</span></label>
    <textarea name="sec_{{ loop.index0 }}" rows="5" placeholder="{{ sec.guide }}"></textarea>
   {% endfor %}
  {% else %}
   <label>본문 (마크다운) <span class="g">— [[페이지제목]] 으로 위키링크</span></label>
   <textarea name="body_md" rows="20">{{ draft_body }}</textarea>
  {% endif %}
  <div style="margin-top:14px"><button>저장</button>
   <a class="btn sec" href="/schema">작성규칙 보기</a></div>
 </form>
</div>
{% endblock %}'''

TPL["page_view.html"] = '''{% extends "layout.html" %}{% block content %}
<div class="card">
 <div style="display:flex;justify-content:space-between;align-items:start;gap:10px;flex-wrap:wrap">
  <div>
   <h1 style="margin-bottom:6px">{{ p.title }}</h1>
   <span class="chip">{{ p.dname }}</span>
   {% for t in p.tags.split(',') if t.strip() %}<a class="chip gray" href="/tag/{{ t.strip()|urlencode }}">{{ t.strip() }}</a>{% endfor %}
   <div class="mut" style="margin-top:6px">작성 {{ p.created_at }} · 갱신 {{ p.updated_at }}{% if p.author %} · {{ p.author }}{% endif %}</div>
  </div>
  <div style="display:flex;gap:6px;flex-wrap:wrap">
   <a class="btn sec sm" href="/page/{{ p.id }}/edit">편집</a>
   <a class="btn sec sm" href="/page/{{ p.id }}/history">이력({{ revcnt }})</a>
   <a class="btn sec sm" href="/page/{{ p.id }}/raw">MD 다운로드</a>
   <form class="danger" action="/page/{{ p.id }}/delete" method="post" style="display:inline">
    <button class="btn warn sm">삭제</button></form>
  </div>
 </div>
 {% if p.summary %}<div class="answer" style="margin-top:10px"><b>요약</b> — {{ p.summary }}</div>{% endif %}
 <div class="md" style="margin-top:14px">{{ p.body_md|md|safe }}</div>
</div>
{% if backlinks %}
<div class="card"><h2>🔗 이 페이지를 참조하는 페이지</h2>
 {% for b in backlinks %}<div><span class="chip">{{ b.dname }}</span> <a href="/page/{{ b.id }}">{{ b.title }}</a></div>{% endfor %}
</div>
{% endif %}
{% endblock %}'''

TPL["page_edit.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>페이지 편집 — {{ p.title }}</h1>
<div class="card">
 <form method="post">
  <div class="grid" style="grid-template-columns:2fr 1fr 1fr 1fr">
   <div><label>제목 *</label><input type="text" name="title" required value="{{ p.title }}"></div>
   <div><label>담당(FAB)</label>
    <select name="domain_id">
     {% for dm in domains %}<option value="{{ dm.id }}" {% if dm.id==p.domain_id %}selected{% endif %}>{{ dm.name }}</option>{% endfor %}
    </select></div>
   <div><label>페이지 타입</label>
    <select name="ptype">
     {% for k, n, g in ptypes %}<option value="{{ k }}" {% if k==p.ptype %}selected{% endif %}>{{ n }}</option>{% endfor %}
    </select></div>
   <div><label>작성자</label><input type="text" name="author" value="{{ p.author }}"></div>
  </div>
  <label>한줄요약</label><input type="text" name="summary" value="{{ p.summary }}">
  <label>태그</label><input type="text" name="tags" value="{{ p.tags }}">
  <label>근거 소스 ID <span class="g">(쉼표 구분 — ingest가 자동 관리)</span></label>
  <input type="text" name="source_ids" value="{{ p.source_ids }}">
  <label>본문 (마크다운)</label>
  <textarea name="body_md" rows="24">{{ p.body_md }}</textarea>
  <div style="margin-top:12px"><button>저장</button>
   <a class="btn sec" href="/page/{{ p.id }}">취소</a></div>
 </form>
</div>
{% endblock %}'''

TPL["page_history.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>이력 — <a href="/page/{{ p.id }}">{{ p.title }}</a></h1>
<div class="card">
 <table class="list">
  <tr><th>#</th><th>저장 시각</th><th>작성자</th><th>제목</th><th></th></tr>
  {% for r in revs %}
   <tr><td>{{ r.id }}</td><td>{{ r.saved_at }}</td><td>{{ r.author or '-' }}</td>
   <td>{{ r.title }}</td><td><a href="/page/{{ p.id }}/rev/{{ r.id }}">보기</a></td></tr>
  {% endfor %}
 </table>
</div>
{% endblock %}'''

TPL["page_rev.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>리비전 #{{ r.id }} — {{ r.title }} <span class="mut">({{ r.saved_at }})</span></h1>
<div class="card"><div class="md">{{ r.body_md|md|safe }}</div></div>
<a class="btn sec" href="/page/{{ p.id }}/history">← 이력으로</a>
{% endblock %}'''

TPL["source_view.html"] = '''{% extends "layout.html" %}{% block content %}
<div class="card">
 <div style="display:flex;justify-content:space-between;align-items:start;gap:10px;flex-wrap:wrap">
  <div>
   <h1 style="margin-bottom:6px"><span class="badge {{ s.filetype }}">{{ s.filetype }}</span> {{ s.filename }}</h1>
   <div class="mut">담당 <a href="/domain/{{ s.dslug }}">{{ s.dname }}</a> · 업로드 {{ s.created_at }}{% if s.uploader %} · {{ s.uploader }}{% endif %}</div>
  </div>
  <div style="display:flex;gap:6px">
   <a class="btn sec sm" href="/source/{{ s.id }}/file">원본 다운로드</a>
   <form class="danger" action="/source/{{ s.id }}/delete" method="post"><button class="btn warn sm">삭제</button></form>
  </div>
 </div>
 <form action="/source/{{ s.id }}/desc" method="post" style="margin-top:10px;display:flex;gap:8px">
  <input type="text" name="description" value="{{ s.description }}" placeholder="이 자료가 무엇인지 설명 (이미지 소스는 필수 — LLM이 이 설명을 근거로 쓴다)">
  <button class="btn sec sm">설명 저장</button>
 </form>
</div>
<div class="card" style="border:2px solid var(--acc)">
 <h2>⚙️ Ingest — 이 소스를 위키 전체에 반영 <span class="chip">권장</span></h2>
 <div class="mut">카파시 llm-wiki의 핵심 연산이다. ① 소스 요약 페이지를 만들고 ② <b>관련된 기존 페이지들까지 갱신안을 만들어</b> 검토 화면에 올린다. 체크한 것만 적용된다.</div>
 <form action="/source/{{ s.id }}/ingest" method="post" style="display:flex;gap:8px;margin-top:10px;align-items:end;flex-wrap:wrap">
  <div><label>갱신 검토 범위</label>
   <select name="scope">
    <option value="domain">이 담당(FAB) 페이지만</option>
    <option value="all">전 FAB 페이지</option>
   </select></div>
  <div><label>검토할 페이지 수</label>
   <select name="fanout">
    <option value="5">5개</option><option value="10">10개</option><option value="15">15개</option>
   </select></div>
  <button {% if not llm_ok %}disabled title="LLM 설정 필요"{% endif %}>Ingest 실행</button>
 </form>
 <div class="mut" style="margin-top:6px">※ 페이지 수만큼 LLM을 호출한다. 15개면 16회 — 느리면 5개부터.</div>
</div>
<div class="card">
 <h2>단일 페이지 초안만 만들기</h2>
 <div class="mut">기존 페이지 갱신 없이, 이 소스로 새 페이지 1개만 양식에 맞춰 뽑는다.</div>
 <form action="/source/{{ s.id }}/draft" method="post" style="display:flex;gap:8px;margin-top:8px">
  <select name="template_id">
   {% for t in templates %}<option value="{{ t.id }}">{{ t.name }}</option>{% endfor %}
  </select>
  <button class="btn sec" {% if not llm_ok %}disabled title="LLM 설정 필요"{% endif %}>초안 생성</button>
 </form>
</div>
{% if s.filetype == 'image' %}
<div class="card"><h2>미리보기</h2><img src="/source/{{ s.id }}/file" style="max-width:100%;border-radius:10px"></div>
{% endif %}
<div class="card">
 <h2>추출 텍스트 {% if s.extracted_text %}<span class="mut">({{ s.extracted_text|length }}자)</span>{% endif %}</h2>
 {% if s.filetype == 'csv' %}
  <div class="md">{{ s.extracted_text|md|safe }}</div>
 {% elif s.extracted_text %}
  <pre style="white-space:pre-wrap;background:#f7f8fa;border:1px solid var(--bd);border-radius:10px;padding:12px;max-height:480px;overflow:auto">{{ s.extracted_text[:8000] }}{% if s.extracted_text|length > 8000 %}\n... (이하 생략){% endif %}</pre>
 {% else %}
  <div class="mut">추출된 텍스트 없음{% if s.filetype=='image' %} — 이미지는 위 설명란에 내용을 적어라{% endif %}</div>
 {% endif %}
</div>
{% endblock %}'''

TPL["retrieval.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>검색 엔진</h1>
<div class="card">
 <h2>현재 구성</h2>
 <div style="font-size:18px;font-weight:700;color:var(--acc);margin:6px 0">{{ desc }}</div>
 <table class="list" style="margin-top:8px">
  <tr><th style="width:180px">항목</th><th>상태</th></tr>
  <tr><td>청크</td><td>{{ stats.chunks }}건 (임베딩 완료 {{ stats.embedded }}건)</td></tr>
  <tr><td>임베딩 모델</td><td>{{ stats.model or '—' }}</td></tr>
  <tr><td>임베딩 백엔드</td><td>{% if embed_ok %}<span class="chip">사용 가능</span>{% else %}<span class="chip gray">미설정 — BM25 단독</span>{% endif %}</td></tr>
  <tr><td>리랭커</td><td>{% if rerank_ok %}<span class="chip">사용 가능</span>{% else %}<span class="chip gray">미설정</span>{% endif %}</td></tr>
  <tr><td>numpy</td><td>{% if has_numpy %}있음 (벡터 연산 가속){% else %}없음 — 순수 파이썬으로 동작 (수천 청크까진 문제 없음){% endif %}</td></tr>
 </table>
 <div class="mut" style="margin-top:8px">설정 변경은 <a href="/settings">설정</a> 화면에서. 임베딩 모델을 바꾸면 반드시 재색인해라.</div>
</div>
<div class="card">
 <h2>재색인</h2>
 <div class="mut">페이지·소스를 섹션 단위로 다시 자르고 임베딩을 만든다. 페이지 저장 시엔 자동으로 증분 갱신되므로, 이건 <b>설정을 바꿨을 때</b>만 돌리면 된다.</div>
 <form action="/retrieval/reindex" method="post" style="margin-top:10px">
  <label style="display:inline"><input type="checkbox" name="with_embed" checked> 임베딩까지 생성 (LLM 서버 호출 발생)</label>
  <div style="margin-top:8px"><button>재색인 실행</button></div>
 </form>
</div>
<div class="card">
 <h2>A/B 비교</h2>
 <div class="mut">같은 질의를 <b>BM25 단독</b>과 <b>현재 설정</b>으로 나란히 돌린다. 바꾼 게 실제로 먹었는지 눈으로 확인하는 용도.</div>
 <form action="/retrieval/test" method="post" style="display:flex;gap:8px;margin-top:8px">
  <input type="text" name="q" value="{{ q|default('') }}" placeholder="예: 정체 발생 시 확인할 지표">
  <button class="btn sec">비교</button>
 </form>
 {% if q %}
 <div class="grid" style="grid-template-columns:1fr 1fr;margin-top:12px">
  <div><h3>BM25 단독 (기준)</h3>
   {% for s, d in base %}<div class="srcitem"><span class="badge {{ d.kind }}">{{ d.kind }}</span>
    <div><b>{{ d.title }}</b><div class="mut">{{ d.domain }} · {{ '%.3f'|format(s) }}</div></div></div>
   {% else %}<div class="mut">결과 없음</div>{% endfor %}</div>
  <div><h3>현재 설정</h3>
   {% for s, d in cur %}<div class="srcitem"><span class="badge {{ d.kind }}">{{ d.kind }}</span>
    <div><b>{{ d.title }}</b>{% if d.chunkHeading %} <span class="chip gray">{{ d.chunkHeading }}</span>{% endif %}
     <div class="mut">{{ d.domain }} · {{ '%.3f'|format(s) }}</div></div></div>
   {% else %}<div class="mut">결과 없음</div>{% endfor %}</div>
 </div>
 {% endif %}
</div>
{% endblock %}'''

TPL["eval.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>평가 하네스</h1>
<div class="card">
 <div class="mut">담당자들이 실제로 묻는 질문 <b>30~50개</b>와 정답 페이지를 등록해두면,
 검색 설정을 바꿀 때마다 <b>숫자로</b> 좋아졌는지 확인할 수 있다. 감으로 튜닝하지 않으려면 이게 필요하다.</div>
 <div style="margin-top:6px">현재 구성: <b style="color:var(--acc)">{{ desc }}</b></div>
</div>
<div class="card">
 <h2>평가 실행</h2>
 <form action="/eval/run" method="post" style="display:flex;gap:10px;align-items:end;flex-wrap:wrap">
  <div><label>라벨 <span class="g">(비교용 메모)</span></label><input type="text" name="label" placeholder="예: 리랭커 켠 후" style="width:200px"></div>
  <div><label>검색 설정</label>
   <select name="mode"><option value="">현재 설정</option>
    <option value="bm25">BM25 단독(기준선)</option><option value="hybrid">하이브리드 강제</option></select></div>
  <div><label>top-K</label><select name="k"><option>5</option><option>3</option><option>10</option></select></div>
  <div><label style="display:inline"><input type="checkbox" name="with_gen"> 생성 품질도 채점 (LLM 호출 ↑)</label></div>
  <button>실행</button>
 </form>
</div>
<div class="card">
 <h2>실행 이력</h2>
 <table class="list">
  <tr><th style="width:130px">시각</th><th>라벨 / 구성</th><th style="width:70px">건수</th>
   <th style="width:80px">Hit@K</th><th style="width:80px">MRR</th><th style="width:90px">Ctx정밀도</th>
   <th style="width:90px">Faith.</th><th style="width:90px">Ans.Rel</th></tr>
  {% for r in runs %}
   <tr><td class="mut">{{ r.created_at }}</td>
    <td><a href="/eval/run/{{ r.id }}">{% if r.label %}<b>{{ r.label }}</b> · {% endif %}{{ r.config }}</a></td>
    <td>{{ r.n }}</td>
    <td><b>{{ '%.3f'|format(r.hit) if r.hit >= 0 else '—' }}</b></td>
    <td>{{ '%.3f'|format(r.mrr) if r.mrr >= 0 else '—' }}</td>
    <td>{{ '%.3f'|format(r.ctxp) if r.ctxp >= 0 else '—' }}</td>
    <td>{{ '%.3f'|format(r.faith) if r.faith >= 0 else '—' }}</td>
    <td>{{ '%.3f'|format(r.arel) if r.arel >= 0 else '—' }}</td></tr>
  {% else %}<tr><td colspan="8" class="mut">아직 실행 이력 없음</td></tr>{% endfor %}
 </table>
</div>
<div class="card">
 <h2>골든셋 <span class="mut">({{ items|length }}건)</span></h2>
 <table class="list">
  <tr><th style="width:45%">질문</th><th>정답 페이지</th><th style="width:20%">비고</th><th style="width:60px"></th></tr>
  {% for it in items %}
   <tr><td>{{ it.question }}</td>
    <td class="mut">{{ it.expect or '(미지정 — 검색 지표 제외)' }}</td>
    <td class="mut">{{ it.note }}</td>
    <td><form class="danger" action="/eval/{{ it.id }}/delete" method="post"><button class="btn warn sm">삭제</button></form></td></tr>
  {% else %}<tr><td colspan="4" class="mut">비어있다 — 아래에서 추가해라</td></tr>{% endfor %}
 </table>
</div>
<div class="grid" style="grid-template-columns:1fr 1fr">
 <div class="card">
  <h2>질문 추가</h2>
  <form action="/eval/add" method="post">
   <label>질문 *</label><input type="text" name="question" required>
   <label>정답 페이지 <span class="g">(Ctrl+클릭 다중선택)</span></label>
   <select name="expect" multiple size="8">
    {% for p in pages %}<option value="{{ p.id }}">[{{ p.dname }}] {{ p.title }}</option>{% endfor %}
   </select>
   <label>비고</label><input type="text" name="note">
   <div style="margin-top:10px"><button>추가</button></div>
  </form>
 </div>
 <div class="card">
  <h2>CSV 임포트</h2>
  <div class="mut">헤더: <code>question,expect,note</code> — expect는 페이지 ID를 <code>;</code>로 구분</div>
  <pre style="background:#f7f8fa;border:1px solid var(--bd);border-radius:8px;padding:10px;font-size:12.5px">question,expect,note
E101 알람 뜨면 뭐부터 하나,3;7,신입 자주 물음
정체 판정 기준이 뭔가,12,</pre>
  <form action="/eval/import" method="post" enctype="multipart/form-data">
   <input type="file" name="file" accept=".csv" required>
   <div style="margin-top:10px"><button class="btn sec">임포트</button></div>
  </form>
 </div>
</div>
{% endblock %}'''

TPL["eval_run.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>평가 결과 #{{ r.id }} {% if r.label %}— {{ r.label }}{% endif %}</h1>
<div class="card">
 <div class="mut">{{ r.config }} · {{ r.created_at }} · {{ r.n }}건</div>
 <div class="grid g4" style="margin-top:10px">
  <div class="stat"><div class="num">{{ '%.3f'|format(r.hit) if r.hit >= 0 else '—' }}</div><div class="lbl">Hit@K<br><span class="mut">정답을 찾았나</span></div></div>
  <div class="stat"><div class="num">{{ '%.3f'|format(r.mrr) if r.mrr >= 0 else '—' }}</div><div class="lbl">MRR<br><span class="mut">몇 번째로 찾았나</span></div></div>
  <div class="stat"><div class="num">{{ '%.3f'|format(r.faith) if r.faith >= 0 else '—' }}</div><div class="lbl">Faithfulness<br><span class="mut">근거 있는 답인가</span></div></div>
  <div class="stat"><div class="num">{{ '%.3f'|format(r.arel) if r.arel >= 0 else '—' }}</div><div class="lbl">Answer Rel.<br><span class="mut">질문에 답했나</span></div></div>
 </div>
</div>
<div class="card">
 <h2>질문별 상세</h2>
 {% for d in detail %}
  <div style="border:1px solid var(--bd);border-radius:10px;padding:12px;margin-bottom:10px">
   <b>{{ d.q }}</b>
   {% if d.hit is defined %}<span class="chip" style="{% if d.hit < 1 %}background:#fdeceb;color:var(--err){% endif %}">{{ '적중' if d.hit >= 1 else '실패' }}</span>{% endif %}
   {% if d.rr is defined %}<span class="chip gray">RR {{ d.rr }}</span>{% endif %}
   {% if d.faith is defined %}<span class="chip gray">F {{ d.faith }}</span><span class="chip gray">A {{ d.arel }}</span>{% endif %}
   <div class="mut" style="margin-top:6px">기대: {% for p in d.expect %}<a href="/page/{{ p }}">{{ titles.get(p, p) }}</a>{% if not loop.last %}, {% endif %}{% else %}(미지정){% endfor %}</div>
   <div class="mut">검색됨: {% for p in d.got %}<a href="/page/{{ p }}">{{ titles.get(p, p) }}</a>{% if not loop.last %}, {% endif %}{% else %}(없음){% endfor %}</div>
   {% if d.answer %}<details style="margin-top:6px"><summary>답변 보기</summary><div class="mut" style="white-space:pre-wrap">{{ d.answer }}</div></details>{% endif %}
   {% if d.error %}<div class="flash err" style="margin-top:6px">{{ d.error }}</div>{% endif %}
  </div>
 {% endfor %}
</div>
<a class="btn sec" href="/eval">← 평가 화면</a>
{% endblock %}'''

TPL["ingest.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>Ingest 검토 — {{ d.filename }}</h1>
<div class="card">
 <div class="mut">카파시 llm-wiki의 <b>ingest</b> 연산이다. 소스 1건을 읽고 ① 소스 요약 페이지를 만들고
 ② 관련된 기존 페이지들의 갱신안을 만들었다. <b>전부 초안이다 — 검토하고 체크한 것만 적용된다.</b></div>
</div>
<form method="post" action="/ingest/{{ token }}/apply">
 <div class="card">
  <label>적용자 <span class="g">(로그에 기록된다)</span></label>
  <input type="text" name="actor" style="max-width:240px">
 </div>
 <div class="card">
  <h2><label style="display:inline"><input type="checkbox" name="make_summary" checked> ① 소스 요약 페이지 생성</label></h2>
  <label>제목</label>
  <input type="text" name="summary_title" value="소스: {{ d.filename }}">
  <label>태그</label>
  <input type="text" name="summary_tags" placeholder="예: OHT, 알람">
  <label>본문 (검토·수정)</label>
  <textarea name="summary_body" rows="16">{{ d.summaryMd }}</textarea>
 </div>
 <div class="card">
  <h2>② 기존 페이지 갱신안 <span class="mut">({{ d.updates|length }}건 검토)</span></h2>
  {% for u in d.updates %}
   <div style="border:1px solid var(--bd);border-radius:10px;padding:12px;margin-bottom:12px">
    {% if u.skip %}
     <b>{{ u.title }}</b> <span class="chip gray">변경 불필요</span>
     <div class="mut">{{ u.changeSummary }}</div>
    {% else %}
     <label style="display:inline"><input type="checkbox" name="apply_{{ u.pageId }}" checked>
      <b>{{ u.title }}</b></label>
     <span class="chip">{{ u.oldLen }}자 → {{ u.newLen }}자</span>
     <div class="answer" style="margin:8px 0"><b>변경 요약</b> — {{ u.changeSummary }}</div>
     <details><summary>갱신될 본문 보기/수정</summary>
      <textarea name="body_{{ u.pageId }}" rows="16">{{ u.newBody }}</textarea>
     </details>
     <div style="margin-top:6px"><a class="btn sec sm" href="/page/{{ u.pageId }}" target="_blank">현재 페이지 보기</a></div>
    {% endif %}
   </div>
  {% else %}<div class="mut">관련된 기존 페이지가 없다 (위키 초기 상태면 정상 — 소스 요약 페이지만 만들면 된다)</div>{% endfor %}
 </div>
 <div class="card"><button>선택한 항목 적용</button>
  <a class="btn sec" href="/source/{{ d.sourceId }}">취소</a></div>
</form>
{% endblock %}'''

TPL["catalog.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>지식 카탈로그 (index) <a class="btn sec sm" href="/catalog/index.md">index.md 원본</a></h1>
{% for g in groups %}
 <div class="card">
  <h2>{{ g.name }} <span class="chip gray">{{ g.key }}</span> <span class="mut">{{ g.rows|length }}건</span></h2>
  <div class="mut">{{ g.desc }}</div>
  <table class="list" style="margin-top:8px">
   <tr><th style="width:90px">담당</th><th style="width:28%">제목</th><th>한줄요약</th><th style="width:140px">태그</th><th style="width:130px">갱신</th></tr>
   {% for r in g.rows %}
    <tr><td><span class="chip">{{ r.dname }}</span></td>
     <td><a href="/page/{{ r.id }}">{{ r.title }}</a></td>
     <td class="mut">{{ r.summary or '(요약 없음)' }}</td>
     <td>{% for t in r.tags.split(',') if t.strip() %}<a class="chip gray" href="/tag/{{ t.strip()|urlencode }}">{{ t.strip() }}</a>{% endfor %}</td>
     <td class="mut">{{ r.updated_at }}</td></tr>
   {% else %}<tr><td colspan="5" class="mut">없음</td></tr>{% endfor %}
  </table>
 </div>
{% endfor %}
{% endblock %}'''

TPL["log.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>활동 로그 <span class="mut" style="font-size:14px">(append-only · 최근 300건)</span></h1>
<div class="card">
 <table class="list">
  <tr><th style="width:130px">시각</th><th style="width:80px">연산</th><th style="width:28%">대상</th><th>내용</th><th style="width:90px">작업자</th></tr>
  {% for r in rows %}
   <tr><td class="mut">{{ r.created_at }}</td>
    <td><span class="chip">{{ r.op }}</span></td>
    <td>{{ r.title }}</td><td class="mut">{{ r.detail }}</td><td class="mut">{{ r.actor or '-' }}</td></tr>
  {% else %}<tr><td colspan="5" class="mut">기록 없음</td></tr>{% endfor %}
 </table>
</div>
{% endblock %}'''

TPL["tag.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>태그: {{ tag }} <span class="mut" style="font-size:14px">({{ pages|length }}건 · 전 FAB 통합)</span></h1>
<div class="card">
 <h2>전체 태그</h2>
 {% for t, c in all_tags %}<a class="chip gray" href="/tag/{{ t|urlencode }}">{{ t }} {{ c }}</a> {% else %}<span class="mut">태그 없음</span>{% endfor %}
</div>
<div class="card">
 {% for p in pages %}
  <div class="srcitem"><span class="chip">{{ p.dname }}</span>
   <div><a href="/page/{{ p.id }}"><b>{{ p.title }}</b></a>
   {% if p.summary %}<div class="mut">{{ p.summary }}</div>{% endif %}
   <div class="mut">{{ p.updated_at }}{% if p.author %} · {{ p.author }}{% endif %}</div></div>
  </div>
 {% else %}<div class="mut">이 태그의 페이지 없음</div>{% endfor %}
</div>
{% endblock %}'''

TPL["search.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>검색{% if q %}: "{{ q }}"{% endif %} <span class="mut" style="font-size:13px">{{ desc }}</span></h1>
<div class="card">
 {% for score, doc in results %}
  <div class="srcitem">
   <span class="badge {{ doc.kind }}">{{ doc.kind }}</span>
   <div>
    {% if doc.kind == 'page' %}<a href="/page/{{ doc.id }}"><b>{{ doc.title }}</b></a>
    {% else %}<a href="/source/{{ doc.id }}"><b>{{ doc.title }}</b></a>{% endif %}
    <span class="chip">{{ doc.domain }}</span> <span class="mut">score {{ '%.2f'|format(score) }}</span>
    {% if doc.summary %}<div class="mut">{{ doc.summary }}</div>{% endif %}
   </div>
  </div>
 {% else %}<div class="mut">{% if q %}결과 없음{% else %}검색어를 입력해라{% endif %}</div>{% endfor %}
</div>
{% endblock %}'''

TPL["ask.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>전체 위키에 질문</h1>
<div class="card">
 <div class="mut">전체 담당의 위키·소스에서 BM25로 근거를 찾아 LLM이 답한다. 특정 담당 소스만 골라 묻는 건 각 담당 노트북 화면에서.</div>
 <form method="post" style="margin-top:8px">
  <textarea name="question" rows="3" placeholder="예: OHT 정체 발생 시 확인해야 할 지표는?">{{ question }}</textarea>
  <div style="margin-top:10px"><button {% if not llm_ok %}disabled title="LLM 설정 필요"{% endif %}>질문하기</button></div>
 </form>
 {% if answer %}
  <div class="answer md">{{ answer|md|safe }}</div>
  <h3>참고한 문서</h3>
  {% for score, d in used %}
   <div><span class="badge {{ d.kind }}">{{ d.kind }}</span>
    {% if d.kind=='page' %}<a href="/page/{{ d.id }}">{{ d.title }}</a>{% else %}<a href="/source/{{ d.id }}">{{ d.title }}</a>{% endif %}
    <span class="mut">({{ d.domain }})</span></div>
  {% endfor %}
 {% endif %}
</div>
{% endblock %}'''

TPL["lint.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>린트 — 위키 품질 점검</h1>
<div class="card">
 <h2>규칙 기반 점검 <span class="mut">({{ issues|length }}건)</span></h2>
 <table class="list">
  <tr><th>페이지</th><th>수준</th><th>내용</th></tr>
  {% for i in issues %}
   <tr><td>{% if i.page_id %}<a href="/page/{{ i.page_id }}">{{ i.title }}</a>{% else %}{{ i.title }}{% endif %}</td>
   <td>{% if i.level=='warn' %}<span class="chip" style="background:#fdf3e0;color:var(--warn)">주의</span>{% else %}<span class="chip gray">참고</span>{% endif %}</td>
   <td>{{ i.msg }}</td></tr>
  {% else %}<tr><td colspan="3" class="mut">문제 없음 👍</td></tr>{% endfor %}
 </table>
</div>
<div class="card">
 <h2>LLM 심층 점검 <span class="mut">(모순·중복·누락 주제)</span></h2>
 <form action="/lint/llm" method="post">
  <button {% if not llm_ok %}disabled title="LLM 설정 필요"{% endif %}>LLM으로 점검 실행</button>
 </form>
 {% if llm_report %}<div class="answer md" style="margin-top:10px">{{ llm_report|md|safe }}</div>{% endif %}
</div>
{% endblock %}'''

TPL["schema.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>작성 규칙 (schema.md) <a class="btn sec sm" href="/schema/edit">편집</a></h1>
<div class="card md">{{ content|md|safe }}</div>
{% endblock %}'''

TPL["schema_edit.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>작성 규칙 편집</h1>
<div class="card">
 <form method="post">
  <textarea name="content" rows="26">{{ content }}</textarea>
  <div style="margin-top:10px"><button>저장</button> <a class="btn sec" href="/schema">취소</a></div>
 </form>
</div>
{% endblock %}'''

TPL["settings.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>설정</h1>
<div class="card">
 <h2>🤖 LLM 연동 (OpenAI 호환 API)</h2>
 <div class="mut">사내 게이트웨이/추론서버의 OpenAI 호환 주소를 입력해라. 예: <code>http://서버주소:포트/v1</code> — 끝에 /v1까지. Claude 아님, 어떤 OpenAI 호환 엔드포인트든 붙는다.</div>
 <form method="post">
  <div class="grid" style="grid-template-columns:1fr 1fr">
   <div><label>위키 이름</label><input type="text" name="site_name" value="{{ s.site_name }}"></div>
   <div></div>
   <div><label>API Base URL</label><input type="text" name="llm_base_url" value="{{ s.llm_base_url }}" placeholder="http://내부서버:포트/v1"></div>
   <div><label>모델명</label><input type="text" name="llm_model" value="{{ s.llm_model }}" placeholder="서버에 로드된 모델 ID"></div>
   <div><label>API Key <span class="g">(없으면 비워둠)</span></label><input type="password" name="llm_api_key" value="{{ s.llm_api_key }}"></div>
  </div>
  <div style="margin-top:10px"><button>저장</button></div>
 </form>
 <form action="/settings/test-llm" method="post" style="margin-top:8px">
  <button class="btn sec">연결 테스트</button>
 </form>
</div>
<div class="card">
 <h2>🔍 검색 — 하이브리드 & 리랭커</h2>
 <div class="mut">전부 <b>선택</b>이다. 아무것도 안 건드리면 지금까지처럼 BM25 단독으로 동작한다.
  상태 확인·재색인은 <a href="/retrieval">검색엔진</a> 화면에서.</div>
 <form method="post">
  <h3>검색 방식</h3>
  <div class="grid" style="grid-template-columns:1fr 1fr 1fr">
   <div><label>모드</label>
    <select name="retrieval_mode">
     <option value="bm25" {% if s.retrieval_mode=='bm25' %}selected{% endif %}>BM25 단독 (기본)</option>
     <option value="hybrid" {% if s.retrieval_mode=='hybrid' %}selected{% endif %}>하이브리드 (BM25 + Dense, RRF)</option>
    </select></div>
   <div><label>리랭크 전 후보 수</label><input type="text" name="rerank_pool" value="{{ s.rerank_pool }}"></div>
   <div><label>청크 최대 글자</label><input type="text" name="chunk_max" value="{{ s.chunk_max }}"></div>
  </div>
  <h3>임베딩 <span class="mut" style="font-weight:400">— 하이브리드 모드에서만 쓰인다</span></h3>
  <div class="grid" style="grid-template-columns:1fr 1fr 1fr 1fr">
   <div><label>백엔드</label>
    <select name="embed_backend">
     <option value="none" {% if s.embed_backend=='none' %}selected{% endif %}>사용 안 함</option>
     <option value="api" {% if s.embed_backend=='api' %}selected{% endif %}>OpenAI 호환 API (권장)</option>
     <option value="st" {% if s.embed_backend=='st' %}selected{% endif %}>로컬 sentence-transformers</option>
    </select></div>
   <div><label>Base URL <span class="g">(비우면 위 LLM 주소)</span></label><input type="text" name="embed_base_url" value="{{ s.embed_base_url }}"></div>
   <div><label>모델</label><input type="text" name="embed_model" value="{{ s.embed_model }}" placeholder="예: bge-m3"></div>
   <div><label>API Key <span class="g">(비우면 LLM 것)</span></label><input type="password" name="embed_api_key" value="{{ s.embed_api_key }}"></div>
  </div>
  <h3>리랭커 <span class="mut" style="font-weight:400">— 투자 대비 효과가 가장 큰 항목</span></h3>
  <div class="grid" style="grid-template-columns:1fr 1fr 1fr">
   <div><label>백엔드</label>
    <select name="rerank_backend">
     <option value="none" {% if s.rerank_backend=='none' %}selected{% endif %}>사용 안 함</option>
     <option value="llm" {% if s.rerank_backend=='llm' %}selected{% endif %}>LLM 리랭커 (추가 설치 불필요)</option>
     <option value="api" {% if s.rerank_backend=='api' %}selected{% endif %}>/v1/rerank 엔드포인트</option>
     <option value="st" {% if s.rerank_backend=='st' %}selected{% endif %}>로컬 CrossEncoder</option>
    </select></div>
   <div><label>Base URL <span class="g">(api 백엔드용)</span></label><input type="text" name="rerank_base_url" value="{{ s.rerank_base_url }}"></div>
   <div><label>모델 <span class="g">(api/st 백엔드용)</span></label><input type="text" name="rerank_model" value="{{ s.rerank_model }}" placeholder="예: Qwen3-Reranker-0.6B"></div>
  </div>
  <div class="mut" style="margin-top:8px">💡 <b>LLM 리랭커</b>는 지금 쓰는 chat 엔드포인트를 그대로 써서 순위만 매긴다 —
   설치할 게 없으니 여기부터 켜보고, 효과를 <a href="/eval">평가</a>로 확인한 뒤 전용 리랭커로 넘어가면 된다.</div>
  <div style="margin-top:12px"><button>검색 설정 저장</button></div>
 </form>
</div>
<div class="card">
 <h2>👥 담당 관리</h2>
 {% for d in domains %}
  <form action="/settings/domain/{{ d.id }}/edit" method="post" style="display:flex;gap:8px;margin-bottom:6px;align-items:center">
   <input type="text" name="name" value="{{ d.name }}" style="width:140px">
   <input type="text" name="description" value="{{ d.description }}">
   <span class="mut" style="white-space:nowrap">P{{ d.pcnt }}/S{{ d.scnt }}</span>
   <button class="btn sec sm">저장</button>
  </form>
  {% if d.pcnt==0 and d.scnt==0 %}
  <form class="danger" action="/settings/domain/{{ d.id }}/delete" method="post" style="margin:-4px 0 8px"><button class="btn warn sm">삭제</button></form>
  {% endif %}
 {% endfor %}
 <h3>담당 추가</h3>
 <form action="/settings/domain/add" method="post" style="display:flex;gap:8px">
  <input type="text" name="name" placeholder="담당 이름" style="width:160px" required>
  <input type="text" name="description" placeholder="설명">
  <button class="btn sm">추가</button>
 </form>
</div>
<div class="card">
 <h2>📋 양식 관리 <span class="mut">— 한 줄에 「섹션명 :: 작성 가이드」</span></h2>
 {% for t in templates %}
  <form action="/settings/template/{{ t.id }}/edit" method="post" style="margin-bottom:14px">
   <input type="text" name="name" value="{{ t.name }}" style="width:240px;font-weight:700">
   <textarea name="sections" rows="6" style="margin-top:6px">{{ tpl_lines[t.id] }}</textarea>
   <div style="margin-top:6px"><button class="btn sec sm">저장</button></div>
  </form>
  <form class="danger" action="/settings/template/{{ t.id }}/delete" method="post" style="margin:-8px 0 14px"><button class="btn warn sm">양식 삭제</button></form>
 {% endfor %}
 <h3>양식 추가</h3>
 <form action="/settings/template/add" method="post">
  <input type="text" name="name" placeholder="양식 이름" style="width:240px" required>
  <textarea name="sections" rows="4" placeholder="개요 :: 이 주제가 무엇인지 3~5문장&#10;핵심 용어 정의 :: '- 용어: 정의' 형태로"></textarea>
  <div style="margin-top:6px"><button class="btn sm">추가</button></div>
 </form>
</div>
<div class="card">
 <h2>🔌 MCP 연동 안내</h2>
 <div class="md">
  <p>이 위키는 MCP로 바로 노출할 수 있게 준비돼 있다.</p>
  <ul>
   <li><b>동봉된 MCP 서버</b>: <code>python mcp_server.py</code> → streamable-http, 기본 포트 8020. 도구: listDomains / searchWiki / readPage / listSources / readSource</li>
   <li><b>JSON API 직접 사용</b>: <code>/api/domains</code>, <code>/api/pages</code>, <code>/api/page/&lt;id&gt;</code>, <code>/api/search?q=</code>, <code>/api/sources</code>, <code>/api/source/&lt;id&gt;</code>, <code>POST /api/ask</code></li>
   <li><b>학습 데이터 추출</b>: [내보내기]의 combined.md / zip — 담당별 MD 파일이 그대로 지식 자산</li>
  </ul>
 </div>
</div>
{% endblock %}'''

TPL["export.html"] = '''{% extends "layout.html" %}{% block content %}
<h1>내보내기 — 지식 자산화</h1>
<div class="card">
 <h2>📦 전체 ZIP</h2>
 <div class="mut">wiki/담당별 MD 파일(프론트매터 포함) + schema.md + combined.md + 소스 목록 CSV. RAG/파인튜닝/타 시스템 이관용.</div>
 <div style="margin-top:8px"><a class="btn" href="/export/zip">ZIP 다운로드</a></div>
</div>
<div class="card">
 <h2>📄 결합 MD 한 장</h2>
 <div class="mut">전체 위키를 한 파일로 — LLM 컨텍스트에 통째로 넣거나 학습 코퍼스로 쓸 때.</div>
 <div style="margin-top:8px"><a class="btn sec" href="/export/combined">combined.md 다운로드</a></div>
</div>
{% endblock %}'''

app.jinja_loader = DictLoader(TPL)


# ------------------------------------------------- 오류를 사람이 읽게
@app.errorhandler(500)
@app.errorhandler(Exception)
def _show_error(e):
    """★"내부 서버 오류" 만 뜨면 아무도 원인을 못 찾는다. 폐쇄망에서는
    콘솔을 보러 가는 것도 일이다 — 무엇이 어디서 터졌는지 화면에 적는다.

    ★HTTPException(404·405 등)은 그대로 흘려보낸다. 우리가 낸 오류만 잡는다.
    """
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException) and e.code != 500:
        return e
    tb = traceback.format_exc()
    print("[오류] " + tb, flush=True)          # 콘솔에도 남긴다
    where = request.path
    tip = ""
    low = (str(e) + tb).lower()
    if "llm" in low or "urlopen" in low or "http error" in low:
        tip = ("LLM 쪽으로 보인다 — [설정] 의 API 주소는 /v1 까지만 넣는다 "
               "(뒤 /chat/completions 는 앱이 붙인다). 모델명 오타도 흔한 원인이다.")
    elif "no such table" in low or "database" in low or "sqlite" in low:
        tip = "DB 문제로 보인다 — data/wiki.db 를 확인해라."
    elif "template" in low or "jinja" in low:
        tip = "화면 틀 문제로 보인다."
    body = (
        "<div style='font:14px/1.7 system-ui;padding:24px;max-width:900px'>"
        "<h2 style='margin:0 0 6px'>오류가 났다</h2>"
        f"<div style='color:#666;margin-bottom:12px'>{html_escape(where)}</div>"
        f"<div style='background:#fee;border:1px solid #fbb;border-radius:8px;"
        f"padding:10px 12px;margin-bottom:12px'><b>{html_escape(type(e).__name__)}</b>: "
        f"{html_escape(str(e)[:500])}</div>"
        + (f"<div style='background:#eef;border:1px solid #bbf;border-radius:8px;"
           f"padding:10px 12px;margin-bottom:12px'>{html_escape(tip)}</div>" if tip else "")
        + "<details><summary style='cursor:pointer'>자세히 (추적)</summary>"
        f"<pre style='background:#f6f6f6;padding:12px;border-radius:8px;"
        f"overflow:auto;font-size:12px'>{html_escape(tb)}</pre></details>"
        "<p><a href='/'>← 처음으로</a></p></div>")
    return body, 500


# ---------------------------------------------------------------- 실행
init_db()

if __name__ == "__main__":
    host = os.environ.get("LLM_WIKI_HOST", "0.0.0.0")
    port = int(os.environ.get("LLM_WIKI_PORT", "8100"))
    print(f"* LLM-WIKI 시작: http://{host}:{port}  (데이터: {DATA_DIR})")
    app.run(host=host, port=port, debug=False)
