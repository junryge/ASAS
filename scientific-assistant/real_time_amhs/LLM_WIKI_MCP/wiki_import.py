#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""마크다운 → 위키 페이지 등록. 손으로 4번 붙여넣지 않게.

무엇을 하나
    `버츄얼 아바타/*.md` 처럼 **프론트매터가 붙은 md** 를 읽어, 위키 웹앱에
    페이지로 넣는다. 같은 제목이 이미 있으면 수정하고, 없으면 만든다.

★DB 를 직접 건드리지 않는다 — 웹앱의 폼으로 넣는다
    페이지 하나를 만들면 위키는 여러 가지를 같이 한다:
        slug 만들기 · revisions 남기기 · data/wiki/ 아래 파일 쓰기 ·
        **청크·임베딩 색인 갱신(index_target)**
    DB 에 INSERT 만 하면 마지막 색인이 빠진다 — 화면 검색에서 새 페이지가
    안 나오는데 DB 에는 있는, 제일 찾기 어려운 상태가 된다.
    그래서 사람이 폼에 넣는 것과 **똑같은 길**로 보낸다.

    (도메인·기존 페이지 조회만 DB 를 읽기 전용으로 연다.)

쓰는 법
    python wiki_import.py "버츄얼 아바타"                 # 무엇을 할지 보기만
    python wiki_import.py "버츄얼 아바타" --apply         # 실제로 넣기
    python wiki_import.py <폴더> --domain "버츄얼 아바타" --base http://127.0.0.1:8100

    ★기본은 **마른 실행(dry-run)** 이다. 무엇이 새로 생기고 무엇이 덮이는지
      먼저 보여 준다. 남의 위키를 조용히 고치면 안 된다.

프론트매터
    --- 사이의 title / type / tags / summary / domain 을 읽는다.
    domain 은 --domain 으로 덮을 수 있다. 없으면 폴더 이름을 쓴다.
"""
import argparse
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE = os.environ.get("LLM_WIKI_BASE", "http://127.0.0.1:8100")
PTYPES = ("concept", "entity", "howto", "case", "source", "spec")


def db_path():
    p = (os.environ.get("WIKI_DB") or "").strip()
    if p:
        return p
    data = (os.environ.get("LLM_WIKI_DATA") or "").strip()
    if data:
        return os.path.join(data, "wiki.db")
    here = os.path.dirname(os.path.abspath(__file__))
    for t in (os.path.join(here, "data", "wiki.db"),
              os.path.join(here, "amhs-llm-wiki", "data", "wiki.db")):
        if os.path.isfile(t):
            return t
    return os.path.join(here, "data", "wiki.db")


def _ro():
    p = db_path()
    if not os.path.isfile(p):
        raise SystemExit("위키 DB 가 없다: {}\n  WIKI_DB 로 자리를 줄 수 있다."
                         .format(p))
    c = sqlite3.connect("file:{}?mode=ro".format(p), uri=True, timeout=5)
    c.row_factory = sqlite3.Row
    return c


# ── 프론트매터 ────────────────────────────────────────────────────────────
def parse_md(path):
    """--- 사이를 머리말로 읽고 나머지를 본문으로. (YAML 파서를 안 쓴다 —
    폐쇄망이라 의존성을 늘리지 않는다. 우리가 쓰는 모양만 읽으면 된다.)"""
    with open(path, encoding="utf-8-sig") as f:
        raw = f.read()
    meta, body = {}, raw
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", raw, re.S)
    if m:
        body = m.group(2)
        for line in m.group(1).splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            k, _, v = line.partition(":")
            if not _:
                continue
            k, v = k.strip().lower(), v.strip()
            if v.startswith("[") and v.endswith("]"):
                v = ", ".join(x.strip().strip("'\"")
                              for x in v[1:-1].split(",") if x.strip())
            meta[k] = v.strip().strip("'\"")
    meta.setdefault("title", os.path.splitext(os.path.basename(path))[0])
    return meta, body.strip()


def files_of(folder):
    out = []
    for n in sorted(os.listdir(folder)):
        if not n.lower().endswith((".md", ".markdown")):
            continue
        # 00_등록방법.md 같은 안내문은 페이지가 아니다
        if re.match(r"^0*0[_\-]", n):
            continue
        out.append(os.path.join(folder, n))
    return out


# ── 위키에 보내기 ─────────────────────────────────────────────────────────
def get_json(base, path, timeout=20):
    """웹앱에서 JSON 하나 — 사내 주소라 프록시를 타면 안 된다."""
    import json as _json
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(base.rstrip("/") + path,
                                 headers={"Accept": "application/json"})
    with op.open(req, timeout=timeout) as r:
        return _json.loads(r.read().decode("utf-8", "replace"))


def post(base, path, fields, timeout=30):
    url = base.rstrip("/") + path
    data = urllib.parse.urlencode(fields, encoding="utf-8").encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    # ★리다이렉트를 따라가지 않는다. 위키는 저장에 성공하면 302 로 목록으로
    #   보낸다 — 그 302 가 곧 성공 신호다. 따라가 봐야 버릴 화면을 한 번 더
    #   받는 것이고, 그 GET 이 실패하면 **저장은 됐는데 실패로 보인다.**
    # 사내 주소다 — 프록시도 타면 안 된다
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **kw):
            return None

    op = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                     _NoRedirect())
    try:
        with op.open(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")[:200]
    except urllib.error.HTTPError as e:
        # 302/303 은 여기로 온다 (위 핸들러가 안 따라가므로) — 성공이다
        return e.code, e.read().decode("utf-8", "replace")[:200]
    except urllib.error.URLError as e:
        return 0, "못 붙었다: {}".format(e.reason)


def main(argv=None):
    ap = argparse.ArgumentParser(description="마크다운을 위키 페이지로 등록")
    ap.add_argument("folder", help="md 파일이 있는 폴더")
    ap.add_argument("--domain", default="", help="담당 이름/슬러그 (없으면 프론트매터·폴더명)")
    ap.add_argument("--base", default=DEFAULT_BASE, help="위키 웹앱 주소 (기본 :8100)")
    ap.add_argument("--author", default="", help="작성자")
    ap.add_argument("--apply", action="store_true", help="실제로 넣는다 (기본은 보기만)")
    a = ap.parse_args(argv)

    folder = os.path.abspath(a.folder)
    if not os.path.isdir(folder):
        raise SystemExit("그런 폴더가 없다: {}".format(folder))
    paths = files_of(folder)
    if not paths:
        raise SystemExit("md 파일이 없다: {}".format(folder))

    conn = _ro()
    doms = {}
    for r in conn.execute("SELECT id,slug,name FROM domains"):
        doms[r["name"]] = r["id"]
        doms[r["slug"]] = r["id"]

    print("위키   : {}".format(a.base))
    print("DB     : {}".format(db_path()))
    print("폴더   : {}  ({}개)".format(folder, len(paths)))
    print("")

    plan, missing = [], set()
    for p in paths:
        meta, body = parse_md(p)
        dom = (a.domain or meta.get("domain")
               or os.path.basename(folder)).strip()
        did = doms.get(dom)
        if did is None:
            missing.add(dom)
            continue
        row = conn.execute("SELECT id FROM pages WHERE domain_id=? AND title=?",
                           (did, meta["title"])).fetchone()
        plan.append({"file": os.path.basename(p), "domain": dom, "domain_id": did,
                     "pid": row["id"] if row else None, "meta": meta, "body": body})
    conn.close()

    if missing:
        # ★담당을 여기서 만들지 않는다. 이름을 잘못 적으면 비슷한 담당이 하나
        #   더 생기고, 나중에 어느 쪽이 진짜인지 모르게 된다.
        print("★없는 담당이 있다: {}".format(", ".join(sorted(missing))))
        print("  위키 화면에서 먼저 담당을 만들고 다시 돌려라.")
        print("  (또는 --domain 으로 이미 있는 담당을 지정)")
        print("  지금 있는 담당: {}".format(", ".join(sorted(
            {k for k in doms if not k.islower() or " " in k}))))
        return 2

    for it in plan:
        print("  {:<34} {:<12} {}".format(
            it["file"], it["domain"],
            "수정 (#{})".format(it["pid"]) if it["pid"] else "새로 만듦"))
        print("     제목: {}  · 타입 {} · {}자".format(
            it["meta"]["title"], it["meta"].get("type") or "concept",
            len(it["body"])))
    print("")

    if not a.apply:
        print("※ 지금은 **보기만** 했다. 실제로 넣으려면 --apply 를 붙여라.")
        print("   먼저 위키 웹앱이 떠 있어야 한다 ({} · python app.py)"
              .format(a.base))
        return 0

    ok = 0
    for it in plan:
        m = it["meta"]
        ptype = (m.get("type") or "concept").strip()
        f = {"domain_id": str(it["domain_id"]), "title": m["title"],
             "mode": "free", "body_md": it["body"],
             "tags": m.get("tags", ""), "summary": m.get("summary", ""),
             "ptype": ptype if ptype in PTYPES else "concept",
             "author": a.author or m.get("author", ""),
             "source_ids": m.get("source_ids", "")}
        path = "/page/{}/edit".format(it["pid"]) if it["pid"] else "/page/new"
        code, body = post(a.base, path, f)
        good = code in (200, 302, 303)
        ok += 1 if good else 0
        print("  {} {}  →  HTTP {}{}".format(
            "OK  " if good else "실패", it["meta"]["title"], code,
            "" if good else "  " + body.replace("\n", " ")[:120]))
    print("")
    print("{}/{} 건 처리했다.".format(ok, len(plan)))
    if ok < len(plan):
        print("★실패한 것이 있다. 위키 웹앱(app.py)이 떠 있나? ({})"
              .format(a.base))
        return 1

    # ── 진짜 들어갔나 — **웹앱에 다시 물어본다** ────────────────────────
    # ★HTTP 302 는 "받았다" 지 "그 위키에 있다" 가 아니다. 실제로 겪었다:
    #   등록은 다 성공했는데 서윤이 "위키에 그런 내용이 없어요" 라고 했다.
    #   웹앱(app.py)과 MCP 서버가 **서로 다른 wiki.db** 를 보고 있으면
    #   이런 일이 난다 — app.py 는 자기 폴더의 data/wiki.db 를 쓴다.
    #   등록해 놓고 못 찾는 것만큼 헛수고가 없다. 넣었으면 확인한다.
    try:
        pages = (get_json(a.base, "/api/pages") or {}).get("pages") or []
    except Exception as e:                              # noqa: BLE001
        print("※ 확인은 못 했다 ({}). 위키 화면에서 페이지가 보이는지 직접 "
              "봐라.".format(e))
        return 0
    live = {(str(x.get("domain") or ""), str(x.get("title") or ""))
            for x in pages}
    miss = [it for it in plan
            if (it["domain"], it["meta"]["title"]) not in live]
    if not miss:
        print("확인: 웹앱에 {}건 다 있다.".format(len(plan)))
    else:
        print("")
        print("★넣었다는데 웹앱에서 안 보인다 ({}건):".format(len(miss)))
        for it in miss:
            print("    {} / {}".format(it["domain"], it["meta"]["title"]))
        print("")
        print("  거의 언제나 **DB 가 두 개**여서 그렇다.")
        print("    내가 읽은 DB : {}".format(db_path()))
        print("    웹앱({})은 **자기 폴더의 data/wiki.db** 를 쓴다."
              .format(a.base))
        print("  둘이 다르면 담당 번호도 달라서 엉뚱한 곳에 들어간다.")
        print("  · app.py 와 mcp_server.py 를 **같은 폴더**에서 띄우거나")
        print("  · 환경변수로 한 곳을 가리켜라:  set LLM_WIKI_DATA=<...>\\data")
        return 1
    print("위키 화면에서 [린트] 를 한 번 돌려 고아 페이지·깨진 링크를 확인해라.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
