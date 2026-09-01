#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""위키가 왜 안 잡히나 — 한 번에 다 두들겨 본다.

    python wiki_진단.py
    python wiki_진단.py VHL "FAB 간 연결 경로"      # 찾을 말을 직접 줘도 된다

★왜 필요한가
  "등록은 했는데 서윤이 못 찾는다" 를 눈으로 가르는 자리가 없었다.
  갈릴 수 있는 곳이 넷인데, 넷을 따로따로 짚느라 한나절이 갔다:

      ① 웹앱(app.py)이 보는 wiki.db      ← 등록이 들어간 곳
      ② MCP 서버가 보는 wiki.db          ← 서윤이 읽는 곳
      ③ 그 DB 에 페이지가 정말 있나
      ④ 그 낱말로 검색하면 나오나

  ①과 ②가 다르면 등록은 성공하고 서윤은 못 찾는다 — 제일 헷갈리는 모양이다.
  app.py 는 **자기 파일이 있는 폴더의 data/wiki.db** 를 쓴다. mcp_server.py
  를 다른 폴더에서 띄웠으면 둘은 다른 파일이다.
"""
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.environ.get("LLM_WIKI_BASE", "http://127.0.0.1:8100")
MCP = os.environ.get("WIKI_MCP_URL", "http://127.0.0.1:8020/mcp")
WORDS = ["VHL", "LFT", "반송 장치", "FAB 간 연결 경로", "M16 HUBROOM 유의 지표"]


def _open(req, timeout=10):
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return op.open(req, timeout=timeout)


def db_paths():
    """이 컴퓨터에 wiki.db 가 몇 개 있나 — **두 개면 그게 원인이다.**"""
    out = []
    for root, _d, files in os.walk(os.path.dirname(HERE)):
        if "wiki.db" in files:
            p = os.path.join(root, "wiki.db")
            out.append((p, os.path.getsize(p)))
    return out


def db_counts(path):
    import sqlite3
    try:
        c = sqlite3.connect("file:{}?mode=ro".format(path), uri=True, timeout=5)
        c.row_factory = sqlite3.Row
        d = c.execute("SELECT COUNT(*) n FROM domains").fetchone()["n"]
        p = c.execute("SELECT COUNT(*) n FROM pages").fetchone()["n"]
        ts = [r["title"] for r in c.execute(
            "SELECT title FROM pages ORDER BY id").fetchall()]
        c.close()
        return d, p, ts
    except Exception as e:                              # noqa: BLE001
        return None, None, [str(e)]


def web_pages():
    try:
        with _open(urllib.request.Request(
                WEB.rstrip("/") + "/api/pages",
                headers={"Accept": "application/json"})) as r:
            return (json.loads(r.read().decode("utf-8", "replace"))
                    or {}).get("pages") or [], ""
    except Exception as e:                              # noqa: BLE001
        return [], "{}: {}".format(type(e).__name__, e)


def mcp_call(name, args, mid=2):
    """MCP 서버에 도구 하나 — 악수부터 다시 한다 (stateless 라 괜찮다)."""
    def one(payload):
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            MCP, data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "Accept": "application/json, text/event-stream"})
        with _open(req, 20) as r:
            raw = r.read().decode("utf-8", "replace")
            sid = r.headers.get("mcp-session-id") or ""
        for chunk in raw.split("\n"):
            if chunk.startswith("data:"):
                raw = chunk[5:].strip()
                break
        return json.loads(raw), sid

    init, sid = one({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                     "params": {"protocolVersion": "2025-06-18",
                                "capabilities": {},
                                "clientInfo": {"name": "진단", "version": "1"}}})
    body = json.dumps({"jsonrpc": "2.0", "id": mid, "method": "tools/call",
                       "params": {"name": name, "arguments": args}}).encode()
    h = {"Content-Type": "application/json",
         "Accept": "application/json, text/event-stream"}
    if sid:
        h["Mcp-Session-Id"] = sid
    req = urllib.request.Request(MCP, data=body, method="POST", headers=h)
    with _open(req, 30) as r:
        raw = r.read().decode("utf-8", "replace")
    for chunk in raw.split("\n"):
        if chunk.startswith("data:"):
            raw = chunk[5:].strip()
            break
    return json.loads(raw)


def main(argv):
    words = argv[1:] or WORDS
    print("=" * 70)
    print("① 이 컴퓨터의 wiki.db")
    print("=" * 70)
    dbs = db_paths()
    if not dbs:
        print("  하나도 없다 — 위키를 한 번도 안 띄운 것이다 (python app.py)")
    for p, size in dbs:
        d, n, ts = db_counts(p)
        print("  {}\n     {:,}바이트 · 담당 {} · 페이지 {}"
              .format(p, size, d, n))
        for t in ts[:8]:
            print("        · {}".format(t))
    if len(dbs) > 1:
        print("")
        print("  ★★ wiki.db 가 {}개다. **이게 원인일 가능성이 제일 크다.**"
              .format(len(dbs)))
        print("     app.py 는 자기 폴더의 data/wiki.db 를 쓴다. mcp_server.py")
        print("     를 다른 폴더에서 띄웠으면 서로 다른 파일을 본다 —")
        print("     등록은 성공하고 서윤은 못 찾는다.")

    print("")
    print("=" * 70)
    print("② 웹앱(app.py) 이 아는 페이지   {}".format(WEB))
    print("=" * 70)
    pages, err = web_pages()
    if err:
        print("  못 붙었다: {}".format(err))
        print("  (app.py 를 띄우고 다시 — LLM_WIKI_BASE 로 주소를 줄 수 있다)")
    elif not pages:
        print("  ★페이지가 하나도 없다 — 등록이 안 된 것이다.")
    else:
        for x in pages:
            print("  · [{}] {}".format(x.get("domain"), x.get("title")))

    print("")
    print("=" * 70)
    print("③ MCP 서버가 찾아 주나   {}".format(MCP))
    print("=" * 70)
    try:
        t = mcp_call("listDomains", {})
        c = ((t.get("result") or {}).get("content") or [{}])[0].get("text", "")
        print("  담당 목록: {}".format(str(c)[:200] or "(빈손)"))
    except Exception as e:                              # noqa: BLE001
        print("  못 붙었다: {}: {}".format(type(e).__name__, e))
        print("  (mcp_server.py 를 띄우고 다시 — WIKI_MCP_URL 로 주소를 줄 수 있다)")
        return 1
    bad = 0
    for w in words:
        try:
            t = mcp_call("searchWiki", {"query": w, "topK": 3})
            txt = ((t.get("result") or {}).get("content") or [{}])[0].get("text", "")
            hit = "없" not in txt[:40] and "0건" not in txt[:40]
            bad += 0 if hit else 1
            print("  {} {:<24} {}".format("OK " if hit else "★✗", w,
                                          txt.replace("\n", " ")[:90]))
        except Exception as e:                          # noqa: BLE001
            bad += 1
            print("  ★✗ {:<24} {}".format(w, e))

    print("")
    print("=" * 70)
    if bad:
        print("★{}개를 못 찾았다.".format(bad))
        print("  · ②에는 있는데 ③이 못 찾으면 → **DB 가 두 개다** (①을 봐라)")
        print("  · ②에도 없으면 → 등록이 안 됐다 (wiki_import.py --apply)")
    else:
        print("전부 찾았다. 여기까지 정상이면 남은 것은 아바타 쪽이다 —")
        print("설정 → 외부 도구에서 AMHS 위키가 초록불인지 봐라.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
