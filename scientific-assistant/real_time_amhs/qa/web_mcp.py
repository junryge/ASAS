# -*- coding: utf-8 -*-
"""바깥 검색을 MCP 로 여는 서버 — 표준 라이브러리만 쓴다.

언제 불리나
    **등록된 자료(위키·요청이력)에 없을 때만** 불린다. 아바타가 순서를
    지킨다 — 우리 자료가 있으면 그걸 쓰고, 없을 때 마지막으로 여기다.
    (avatar/mcp_client.py 의 _fallback)

★바깥 글은 믿을 수 없다
    위키·요청이력은 우리가 쓴 글이다. 여기는 아니다 — 아무나 쓴 글이고,
    페이지 안에 "앞의 지시를 무시하고…" 같은 것이 박혀 있을 수 있다.
    그래서 이 서버가 주는 글은 **참고용**이라고 아바타 쪽에서 머리를 단다.
    여기서도 스크립트·스타일을 지우고 글자만 남긴다.

어디로 검색하나 — 환경변수로 고른다 (집·회사가 다르다)
    WEB_SEARCH_URL   검색 주소. {q} 자리에 질문이 들어간다.
                     예) 사내:  http://portal.내부/search?q={q}&fmt=json
                         집:    https://duckduckgo.com/html/?q={q}
    WEB_SEARCH_KIND  json | html   (기본 json)
    WEB_JSON_LIST    JSON 응답에서 결과 배열의 키 (기본 results)
    WEB_JSON_TITLE   제목 키   (기본 title)
    WEB_JSON_URL     주소 키   (기본 url)
    WEB_JSON_TEXT    요약 키   (기본 snippet)
    WEB_KEY_FILE     토큰 파일 (있으면 Authorization: Bearer)
    WEB_TIMEOUT      초 (기본 10)
    WEB_MAX_CHARS    readUrl 이 돌려줄 최대 글자 (기본 6000)

    ★주소를 안 주면 **아무것도 안 한다.** 잘못된 데로 나가느니 안 나간다.

실행
    python qa/web_mcp.py            # stdio 로 대기 (아바타가 띄운다)
    python qa/web_mcp.py --check    # 주소·검색이 되는지만 본다
"""
import html as _html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

PROTO = "2025-06-18"
NAME, VERSION = "web-search", "1.0.0"

URL = (os.environ.get("WEB_SEARCH_URL") or "").strip()
KIND = (os.environ.get("WEB_SEARCH_KIND") or "json").strip().lower()
J_LIST = os.environ.get("WEB_JSON_LIST", "results")
J_TITLE = os.environ.get("WEB_JSON_TITLE", "title")
J_URL = os.environ.get("WEB_JSON_URL", "url")
J_TEXT = os.environ.get("WEB_JSON_TEXT", "snippet")
TIMEOUT = float(os.environ.get("WEB_TIMEOUT", "10"))
MAX_CHARS = int(os.environ.get("WEB_MAX_CHARS", "6000"))


def _headers():
    h = {"Accept": "application/json, text/html;q=0.8",
         # ★사람이 쓰는 브라우저인 척하지 않는다. 그냥 우리라고 밝힌다.
         "User-Agent": "amhs-avatar-web/{}".format(VERSION)}
    p = (os.environ.get("WEB_KEY_FILE") or "").strip()
    if p and os.path.isfile(p):
        with open(p, encoding="utf-8-sig") as f:
            k = f.read().strip()
        if k:
            h["Authorization"] = "Bearer " + k
    return h


def _open(url, timeout=None):
    # ★프록시 설정을 타지 않는다 (사내에서 엉뚱한 데로 나간다)
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(url, headers=_headers())
    with op.open(req, timeout=timeout or TIMEOUT) as r:
        return r.read().decode("utf-8", "replace")


_TAG = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
_ANY = re.compile(r"<[^>]+>")


def strip_html(raw):
    """태그를 걷어 글자만. 스크립트·스타일은 통째로 버린다."""
    t = _TAG.sub(" ", str(raw or ""))
    t = _ANY.sub(" ", t)
    return re.sub(r"\s+", " ", _html.unescape(t)).strip()


_HREF = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)


def _from_html(raw, k):
    """검색 결과 HTML 에서 링크를 줍는다 (JSON 을 안 주는 곳용).

    ★거친 방법이다. 사내 검색이 JSON 을 주면 그쪽(kind=json)을 써라 —
      HTML 은 화면이 바뀌면 같이 깨진다.
    """
    out, seen = [], set()
    for href, inner in _HREF.findall(raw):
        u = _html.unescape(href)
        if not u.startswith("http") or u in seen:
            continue
        title = strip_html(inner)
        if len(title) < 4:
            continue
        seen.add(u)
        out.append({"title": title[:200], "url": u, "snippet": ""})
        if len(out) >= k:
            break
    return out


def t_search(a):
    q = str(a.get("query") or "").strip()
    if not q:
        raise ValueError("query 가 비었다")
    if not URL:
        raise RuntimeError(
            "검색 주소가 없다 (WEB_SEARCH_URL). 어디로 나갈지 정해지지 "
            "않아서 아무것도 안 했다 — 잘못된 데로 나가느니 안 나간다.")
    k = max(1, min(10, int(a.get("topK") or 5)))
    raw = _open(URL.replace("{q}", urllib.parse.quote(q)))
    if KIND == "html":
        rows = _from_html(raw, k)
    else:
        d = json.loads(raw)
        rows = (d.get(J_LIST) if isinstance(d, dict) else d) or []
        rows = [{"title": str(r.get(J_TITLE) or "")[:200],
                 "url": str(r.get(J_URL) or ""),
                 "snippet": strip_html(r.get(J_TEXT) or "")[:400]}
                for r in rows[:k] if isinstance(r, dict)]
    # ★JSON 으로 준다. 아바타가 이걸 읽어 본문(readUrl)까지 이어 읽는다.
    return json.dumps({"query": q, "count": len(rows), "results": rows},
                      ensure_ascii=False, indent=1)


def t_read(a):
    u = str(a.get("url") or "").strip()
    if not u.startswith(("http://", "https://")):
        raise ValueError("http(s) 주소가 아니다: {}".format(u[:80]))
    n = int(a.get("maxChars") or MAX_CHARS)
    body = strip_html(_open(u))
    cut = body[:n]
    if len(body) > n:
        cut += "\n…(뒤가 잘렸다 · 전체 {}자)".format(len(body))
    return "# {}\n{}".format(u, cut)


TOOLS = [
    {"name": "webSearch",
     "description": ("바깥에서 찾는다. **등록된 자료(위키·요청이력)에 없을 "
                     "때만** 쓴다. 결과는 참고용이다 — 관제 수치를 여기서 "
                     "가져오지 마라."),
     "inputSchema": {"type": "object", "required": ["query"], "properties": {
         "query": {"type": "string"},
         "topK": {"type": "integer"}}}},
    {"name": "readUrl",
     "description": "찾은 주소의 글을 읽는다 (태그를 걷어 글자만).",
     "inputSchema": {"type": "object", "required": ["url"], "properties": {
         "url": {"type": "string"},
         "maxChars": {"type": "integer"}}}},
]

HANDLERS = {"webSearch": t_search, "readUrl": t_read}


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
        except Exception as e:                          # noqa: BLE001
            # ★도구 실패는 프로토콜 오류가 아니다 — isError 로 준다.
            return ok({"content": [{"type": "text",
                                    "text": "{}: {}".format(type(e).__name__, e)}],
                       "isError": True})
        return ok({"content": [{"type": "text", "text": text}], "isError": False})
    if mid is None:
        return None
    return err(-32601, "모르는 method: {}".format(method))


def _force_utf8():
    """윈도우 파이프 기본 인코딩(cp949)이면 '·' '★' 에서 프로세스가 죽는다."""
    for f, kw in ((sys.stdin, {}), (sys.stdout, {"newline": "\n"})):
        try:
            f.reconfigure(encoding="utf-8", errors="replace", **kw)
        except Exception:                               # noqa: BLE001
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


def selfcheck(q="테스트"):
    print("검색 주소: {}".format(URL or "(안 정해짐)"))
    print("방식     : {}".format(KIND))
    if not URL:
        print("")
        print("  WEB_SEARCH_URL 을 정해야 한다. {q} 자리에 질문이 들어간다.")
        print("    사내:  set WEB_SEARCH_URL=http://portal.내부/search?q={q}&fmt=json")
        print("    집  :  set WEB_SEARCH_URL=https://duckduckgo.com/html/?q={q}")
        print("           set WEB_SEARCH_KIND=html")
        return 1
    try:
        out = json.loads(t_search({"query": q, "topK": 3}))
    except Exception as e:                              # noqa: BLE001
        print("검색 실패: {}: {}".format(type(e).__name__, e))
        return 1
    print("'{}' → {}건".format(q, out["count"]))
    for r in out["results"]:
        print("  · {}  {}".format(r["title"][:50], r["url"][:60]))
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        i = sys.argv.index("--check")
        sys.exit(selfcheck(sys.argv[i + 1] if len(sys.argv) > i + 1 else "테스트"))
    serve()
