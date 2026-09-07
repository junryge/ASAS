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
    WEB_SEARCH_KIND  json | html | mediawiki   (기본 json)
                     mediawiki = 위키백과 API. 주소는 api.php 까지만 준다:
                       WEB_SEARCH_URL=https://ko.wikipedia.org/w/api.php
                       WEB_SEARCH_KIND=mediawiki
    WEB_JSON_LIST    JSON 응답에서 결과 배열의 키 (기본 results)
    WEB_JSON_TITLE   제목 키   (기본 title)
    WEB_JSON_URL     주소 키   (기본 url)
    WEB_JSON_TEXT    요약 키   (기본 snippet)
    WEB_KEY_FILE     토큰 파일
    WEB_KEY_HEADER   토큰을 실을 머리 (기본 Authorization)
    WEB_KEY_PREFIX   토큰 앞에 붙일 말 (기본 "Bearer ")
                     예) Brave: HEADER=X-Subscription-Token · PREFIX=(빈칸)
    WEB_USER_AGENT   보낼 UA. **403 이 나면 여기부터 의심한다** —
                     UA 를 안 보내면 막는 데가 있다 (DuckDuckGo html).
                       set WEB_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64)
    WEB_USE_PROXY    1 이면 시스템 프록시를 탄다 (기본 안 탐).
                     사내에서 **바깥**으로 나갈 때 대개 필요하다.
                     사내 검색을 쓸 때는 켜지 마라 — 엉뚱한 데로 나간다.
    WEB_TIMEOUT      초 (기본 10)
    WEB_MAX_CHARS    readUrl 이 돌려줄 최대 글자 (기본 6000)

    ★주소를 안 주면 **아무것도 안 한다.** 잘못된 데로 나가느니 안 나간다.

설정을 어디서 읽나 — 두 군데를 본다
    ① 환경변수 (아바타가 띄울 때 config.py 의 env 를 이렇게 넣어 준다)
    ② 없으면 avatar_2d/avatar/config.py 의 web 칸을 **직접 읽는다**

    ★②가 왜 있나. config.py 의 env 는 **아바타가 이 파일을 띄울 때만**
      쓰인다. 그래서 사람이 손으로 --check 를 하면 환경변수가 비어
      "검색 주소: (안 정해짐)" 만 나왔다. 실제로 그랬다. 이제 손으로 해도
      아바타와 **같은 자리**를 보므로 똑같이 나온다.
    ★config.py 를 import 하지 않는다. ast 로 글만 읽는다 — avatar 꾸러미가
      없어도 되고, 남의 코드를 실행하지도 않는다.

실행
    python WEB_MCP/web_mcp.py            # stdio 로 대기 (아바타가 띄운다)
    python WEB_MCP/web_mcp.py --check    # 주소·검색이 되는지만 본다
                                         #   (어느 폴더에서 해도 된다 —
                                         #    config.py 를 제 발로 찾는다)
"""
import ast
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

# ─────────────────────────────────────────────────────────────────────
# 설정 읽기 — 환경변수 → config.py 순서
# ─────────────────────────────────────────────────────────────────────
def _config_path():
    """avatar_2d/avatar/config.py 를 제 발로 찾는다.

    ★어느 폴더에서 실행하든 되게 __file__ 기준으로 올라간다.
      WEB_MCP/web_mcp.py → 한 칸 위가 real_time_amhs → avatar_2d/avatar.
    """
    p = (os.environ.get("WEB_CONFIG") or "").strip()
    if p:
        return p if os.path.isfile(p) else ""
    here = os.path.dirname(os.path.abspath(__file__))
    up = here
    for _ in range(4):
        c = os.path.join(up, "avatar_2d", "avatar", "config.py")
        if os.path.isfile(c):
            return c
        nxt = os.path.dirname(up)
        if nxt == up:
            break
        up = nxt
    return ""


_CFG_CACHE = {}


def _config_env():
    """config.py 의 web 칸 env 를 (dict, 파일경로) 로 돌려준다.

    ★ast 로 읽는다. MCP_SERVERS 안에서 "key": "web" 인 표를 찾아
      그 표의 env 만 꺼낸다. 못 찾으면 빈 dict — 조용히 넘어간다.
    """
    if "v" in _CFG_CACHE:
        return _CFG_CACHE["v"]
    out, path = {}, _config_path()
    try:
        if path:
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Dict):
                    continue
                d = {}
                for kn, vn in zip(node.keys, node.values):
                    if isinstance(kn, ast.Constant) and kn.value in ("key", "env"):
                        try:
                            d[kn.value] = ast.literal_eval(vn)
                        except Exception:               # noqa: BLE001
                            pass
                if d.get("key") == "web" and isinstance(d.get("env"), dict):
                    out = {str(k): str(v) for k, v in d["env"].items()}
                    break
    except Exception:                                   # noqa: BLE001
        out = {}                    # config.py 가 깨져도 서버는 뜬다
    _CFG_CACHE["v"] = (out, path)
    return _CFG_CACHE["v"]


def _setting(name, default=""):
    """환경변수가 있으면 그것, 없으면 config.py, 그것도 없으면 기본값."""
    v = (os.environ.get(name) or "").strip()
    if v:
        return v
    v = (_config_env()[0].get(name) or "").strip()
    return v or default


def _num(name, default, cast):
    try:
        return cast(_setting(name, str(default)))
    except (TypeError, ValueError):
        return default


URL = _setting("WEB_SEARCH_URL")
KIND = _setting("WEB_SEARCH_KIND", "json").lower()
J_LIST = _setting("WEB_JSON_LIST", "results")
J_TITLE = _setting("WEB_JSON_TITLE", "title")
J_URL = _setting("WEB_JSON_URL", "url")
J_TEXT = _setting("WEB_JSON_TEXT", "snippet")
TIMEOUT = _num("WEB_TIMEOUT", 10.0, float)
MAX_CHARS = _num("WEB_MAX_CHARS", 6000, int)


# 키를 어느 머리에 실을지 — API 마다 다르다.
#   OpenAI 계열   Authorization: Bearer <키>      (기본값)
#   Brave         X-Subscription-Token: <키>      HEADER=X-Subscription-Token PREFIX=
#   그 밖         쓰는 API 문서대로
KEY_HEADER = _setting("WEB_KEY_HEADER", "Authorization")

# ★PREFIX 만 다르게 읽는다 — **빈칸이 뜻을 가진다** (Brave 는 접두어가
#   없다). 그래서 '비었으면 다음 자리' 가 아니라 '있으면 그대로' 다.
KEY_PREFIX = os.environ.get("WEB_KEY_PREFIX")
if KEY_PREFIX is None:
    KEY_PREFIX = _config_env()[0].get("WEB_KEY_PREFIX", "Bearer ")


# ★UA 를 안 보내면 403 을 주는 데가 있다 (DuckDuckGo html 이 그렇다).
#   기본은 우리라고 밝히고, 필요하면 WEB_USER_AGENT 로 바꾼다 —
#   403 이 나면 여기부터 의심한다.
UA = _setting("WEB_USER_AGENT") or "amhs-avatar-web/{}".format(VERSION)

# ★사내에서 바깥으로 나가려면 대개 프록시를 타야 한다. 그런데 기본은
#   **안 탄다** — 사내 검색을 쓸 때 프록시로 나가면 엉뚱한 데로 간다.
#   바깥(DuckDuckGo·위키백과)을 쓸 때만 켠다: WEB_USE_PROXY=1
USE_PROXY = _setting("WEB_USE_PROXY").lower() not in ("", "0", "off", "false")


def _headers():
    h = {"Accept": "application/json, text/html;q=0.8",
         "User-Agent": UA}
    p = (os.environ.get("WEB_KEY_FILE") or "").strip()
    if p and os.path.isfile(p):
        with open(p, encoding="utf-8-sig") as f:
            k = f.read().strip()
        if k:
            h[KEY_HEADER] = KEY_PREFIX + k
    return h


def _open(url, timeout=None):
    op = (urllib.request.build_opener() if USE_PROXY
          else urllib.request.build_opener(urllib.request.ProxyHandler({})))
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
# 우리 것이 아닌 링크(로고·설정·다음페이지)를 걸러 낸다
_SKIP = ("duckduckgo.com/settings", "duckduckgo.com/about", "/y.js",
         "spreadprivacy", "help.duckduckgo", "twitter.com/duckduckgo",
         "duckduckgo.com/traffic", "apps.apple.com", "play.google.com")


def _real_url(u):
    """진짜 주소로 편다.

    ★DuckDuckGo 는 결과 링크를 두 겹으로 준다:
        //duckduckgo.com/l/?uddg=https%3A%2F%2Fsbs.co.kr&rut=…
      ① 앞이 '//' 라 http 로 시작하지 않는다 → 예전엔 여기서 다 버려서
         **0건**이 나왔다.
      ② 진짜 주소는 uddg= 안에 들어 있다.
    """
    u = _html.unescape(str(u or "")).strip()
    if u.startswith("//"):
        u = "https:" + u
    if "uddg=" in u:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(u).query)
        real = (q.get("uddg") or [""])[0]
        if real.startswith("http"):
            return real
    return u


def _from_html(raw, k):
    """검색 결과 HTML 에서 링크를 줍는다 (JSON 을 안 주는 곳용).

    ★거친 방법이다. 사내 검색이 JSON 을 주면 그쪽(kind=json)을 써라 —
      HTML 은 화면이 바뀌면 같이 깨진다.
    """
    out, seen = [], set()
    for href, inner in _HREF.findall(raw):
        u = _real_url(href)
        if not u.startswith("http") or u in seen:
            continue
        if any(x in u for x in _SKIP):
            continue
        title = strip_html(inner)
        if len(title) < 4:
            continue
        seen.add(u)
        out.append({"title": title[:200], "url": u, "snippet": ""})
        if len(out) >= k:
            break
    return out


# ★조사를 떼고 찾는다. 위키(BM25)는 조사가 붙어도 되지만 웹 검색은
#   "SBS가" 로 물으면 결과가 나빠진다 — 실제로 그렇게 나갔다.
_JOSA = ("이라는", "라는", "이란", "에서는", "에서", "에게", "으로", "라고",
         "이가", "께서", "부터", "까지", "처럼", "보다", "이나", "하고",
         "은", "는", "이", "가", "을", "를", "의", "에", "도", "만", "과",
         "와", "로", "랑")


def _clean_query(q):
    out = []
    for w in str(q or "").split():
        for j in _JOSA:                 # 긴 것부터 (위 목록 순서)
            if w.endswith(j) and len(w) - len(j) >= 2:
                w = w[: -len(j)]
                break
        out.append(w)
    return " ".join(out).strip()


def _from_mediawiki(raw, k, base):
    """위키백과(MediaWiki) API 응답 → 결과 목록.

    ★왜 따로 두나. 이 API 는 결과가 query.search 아래에 있고 **주소를 안 준다**
      (제목으로 만들어야 한다). 그래서 일반 JSON 규칙으로는 못 읽는다.
      한국어 위키백과가 폐쇄망 밖에서 제일 쓸 만한 자료라 자리를 만들어 둔다.
    ★나무위키는 안 쓴다 — Cloudflare 로 막혀 있고, CC BY-NC-SA(비영리)라
      회사 업무에 쓰면 걸린다.
    """
    d = json.loads(raw)
    rows = ((d.get("query") or {}).get("search")) or []
    out = []
    for r in rows[:k]:
        t = str(r.get("title") or "")
        if not t:
            continue
        out.append({
            "title": t,
            # /w/api.php → /wiki/<제목>
            "url": "{}/wiki/{}".format(
                base.split("/w/api.php")[0].rstrip("/"),
                urllib.parse.quote(t.replace(" ", "_"))),
            # snippet 에 <span class="searchmatch"> 가 섞여 온다
            "snippet": strip_html(r.get("snippet") or "")[:400],
        })
    return out


# 위키백과 검색에 붙일 것들 (사람이 주소에 안 적어도 되게)
_MW_Q = ("action=query&list=search&format=json&utf8=1"
         "&srlimit={k}&srsearch={q}")


def t_search(a):
    q = str(a.get("query") or "").strip()
    if not q:
        raise ValueError("query 가 비었다")
    if not URL:
        raise RuntimeError(
            "검색 주소가 없다 (WEB_SEARCH_URL). 어디로 나갈지 정해지지 "
            "않아서 아무것도 안 했다 — 잘못된 데로 나가느니 안 나간다.")
    q = _clean_query(q) or q
    k = max(1, min(10, int(a.get("topK") or 5)))
    if KIND == "mediawiki":
        # 주소는 api.php 까지만 주면 된다 — 질의는 우리가 붙인다
        u = URL.split("?")[0].rstrip("/")
        raw = _open(u + "?" + _MW_Q.format(k=k, q=urllib.parse.quote(q)))
        rows = _from_mediawiki(raw, k, u)
    elif KIND == "html":
        raw = _open(URL.replace("{q}", urllib.parse.quote(q)))
        rows = _from_html(raw, k)
    else:
        raw = _open(URL.replace("{q}", urllib.parse.quote(q)))
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
    cfg, path = _config_env()
    if (os.environ.get("WEB_SEARCH_URL") or "").strip():
        src = "환경변수"
    elif (cfg.get("WEB_SEARCH_URL") or "").strip():
        src = "config.py"
    else:
        src = "(없음)"
    print("검색 주소: {}".format(URL or "(안 정해짐)"))
    print("방식     : {}".format(KIND))
    print("설정 출처: {}".format(src))
    print("설정 파일: {}".format(path or "★config.py 를 못 찾았다"))
    if not URL:
        print("")
        if path:
            # 파일은 찾았는데 비었다 = config.py 가 옛것이다. 이게 대부분이다.
            print("  config.py 는 찾았는데 web 칸의 WEB_SEARCH_URL 이 비어 있다.")
            print("  → config.py 가 옛것이다. 새 config.py 로 덮고 아바타를 다시 띄워라.")
        else:
            print("  avatar_2d/avatar/config.py 를 못 찾았다.")
            print("  → WEB_MCP 가 real_time_amhs 안에 있어야 한다. 아니면 자리를 직접 준다:")
            print("       set WEB_CONFIG=C:\\...\\real_time_amhs\\avatar_2d\\avatar\\config.py")
        print("")
        print("  급하면 이 창에서만 직접 줘도 된다 ({q} 자리에 질문이 들어간다):")
        print("    set WEB_SEARCH_URL=https://duckduckgo.com/html/?q={q}")
        print("    set WEB_SEARCH_KIND=html")
        print("    set WEB_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        return 1
    try:
        out = json.loads(t_search({"query": q, "topK": 3}))
    except Exception as e:                              # noqa: BLE001
        print("검색 실패: {}: {}".format(type(e).__name__, e))
        msg = str(e)
        if "403" in msg or "401" in msg:
            print("")
            print("  403/401 은 대개 둘 중 하나다.")
            print("   ① UA 를 막는 곳이다 (DuckDuckGo html 이 그렇다)")
            print("      set WEB_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
            print("   ② 사내 프록시를 타야 한다")
            print("      set WEB_USE_PROXY=1")
        elif "407" in msg or "Proxy" in msg:
            print("")
            print("  프록시 인증이 필요하다 — set WEB_USE_PROXY=1 과 함께")
            print("  HTTPS_PROXY=http://<아이디>:<비번>@<프록시>:<포트> 를 준다.")
        elif "URLError" in type(e).__name__ or "getaddrinfo" in msg:
            print("")
            print("  주소 자체를 못 찾았다 — 이 PC 에서 그 도메인이 열리나?")
            print("  사내면 프록시가 필요할 수 있다: set WEB_USE_PROXY=1")
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
