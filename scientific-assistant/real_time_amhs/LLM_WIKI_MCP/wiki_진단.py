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
import re
import sys
import urllib.error
import urllib.parse
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


# ── ⓪ MD 가 왜 소스로 가나 ─────────────────────────────────────────────
# 머리말 붙은 md 를 **페이지**로 넣는 기능은 나중에 들어갔다. 그 전 app.py 는
# 올리는 것을 무엇이든 소스로 넣는다. 파일만 덮고 웹앱을 안 껐다 켜도 마찬가지다
# — 파이썬이 옛 코드를 물고 있다. 이 둘이 눈으로 안 갈려서 한참 헤맸다.
MD_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.S)


def app_file_has_feature():
    """디스크의 app.py 에 기능이 있나 (없으면 옛날 파일)."""
    p = os.path.join(HERE, "amhs-llm-wiki", "app.py")
    if not os.path.isfile(p):
        return None, p
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return ("md_as_page" in f.read()), p


def server_has_feature():
    """**지금 도는** 웹앱이 그 기능을 내놓나 — 업로드 화면을 직접 받아 본다.
    디스크 파일이 아니라 프로세스를 보는 것이라, 재시작을 안 했으면 여기서 갈린다."""
    try:
        with _open(urllib.request.Request(
                WEB.rstrip("/") + "/api/domains",
                headers={"Accept": "application/json"})) as r:
            doms = (json.loads(r.read().decode("utf-8", "replace"))
                    or {}).get("domains") or []
    except Exception as e:                              # noqa: BLE001
        return None, "웹앱에 못 붙었다: {}: {}".format(type(e).__name__, e)
    if not doms:
        return None, "담당이 하나도 없다 — 화면에서 먼저 담당을 만들어라"
    slug = doms[0].get("slug") or ""
    try:
        with _open(urllib.request.Request(
                WEB.rstrip("/") + "/domain/" + urllib.parse.quote(slug))) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception as e:                              # noqa: BLE001
        return None, "업로드 화면을 못 받았다: {}: {}".format(type(e).__name__, e)
    return ("md_as_page" in html), "담당 '{}' 화면으로 확인".format(slug)


def md_plan(folder):
    """그 폴더의 md 가 페이지로 갈지 소스로 갈지 — 올리기 전에 미리 본다."""
    out = []
    if not os.path.isdir(folder):
        return out
    for n in sorted(os.listdir(folder)):
        p = os.path.join(folder, n)
        if not os.path.isfile(p):
            continue
        if os.path.splitext(n)[1].lower() not in (".md", ".markdown"):
            out.append((n, "소스", "md 가 아니다"))
            continue
        with open(p, "r", encoding="utf-8-sig", errors="replace") as f:
            raw = f.read()
        m = MD_FM_RE.match(raw)
        title = ""
        if m:
            for line in m.group(1).splitlines():
                k, sep, v = line.partition(":")
                if sep and k.strip().lower() == "title":
                    title = v.strip().strip("'\"")
        out.append((n, "페이지" if title else "소스",
                    title or "머리말(--- title: … ---)이 없다"))
    return out


def main(argv):
    words = argv[1:] or WORDS
    print("=" * 70)
    print("⓪ MD 를 올리면 페이지로 가나, 소스로 가나")
    print("=" * 70)
    fileok, fpath = app_file_has_feature()
    srvok, how = server_has_feature()
    print("  디스크 app.py : {}  ({})".format(
        "새 버전 (MD→페이지 있음)" if fileok else
        ("옛날 버전 (MD→페이지 없음)" if fileok is False else "파일을 못 찾음"), fpath))
    print("  도는 웹앱     : {}  ({})".format(
        "새 버전" if srvok else ("옛날 버전" if srvok is False else "확인 못 함"), how))
    if fileok and srvok is False:
        print("")
        print("  ★★ 파일은 새것인데 **도는 웹앱이 옛날 것**이다.")
        print("     → 웹앱을 껐다 켜라 (Ctrl+C 후 python app.py).")
        print("       파일만 덮으면 파이썬이 옛 코드를 계속 물고 있다.")
    elif fileok is False:
        print("")
        print("  ★★ app.py 가 **옛날 파일**이다 — 올리는 것을 무엇이든 소스로 넣는다.")
        print("     → 새 app.py 로 덮고 웹앱을 껐다 켜라.")
        print("     (지금 당장은 업로드 화면 대신 wiki_import.py 를 써라 —")
        print("      /page/new 로 직접 보내서 소스로 갈 길이 없다)")
    elif fileok and srvok:
        print("")
        print("  여기는 정상이다. 그래도 소스로 갔다면 **그 파일에 머리말이 없는 것**이다 —")
        print("  아래 목록을 봐라.")
    # ★폴더 이름을 박아 두지 않는다. '검색시험' 처럼 새로 만든 폴더가
    #   목록에 안 떠서 "넣었는데 왜 안 보이냐" 가 됐다. md 가 든 폴더는 다 본다.
    folders = sorted(n for n in os.listdir(HERE)
                     if os.path.isdir(os.path.join(HERE, n))
                     and not n.startswith((".", "_"))
                     and n not in ("amhs-llm-wiki", "tests", "data")
                     and any(x.lower().endswith((".md", ".markdown", ".txt"))
                             for x in os.listdir(os.path.join(HERE, n))))
    for folder in folders:
        rows = md_plan(os.path.join(HERE, folder))
        if not rows:
            continue
        print("")
        print("  [{}] 올리면 어디로 가나".format(folder))
        for n, where, why in rows:
            print("    {:<38} → {:<4} {}".format(
                n[:38], where, "" if where == "페이지" else why))

    print("")
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
