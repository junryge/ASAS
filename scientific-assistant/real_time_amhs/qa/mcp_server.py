# -*- coding: utf-8 -*-
"""요청/응답 관리(app.py)를 MCP 로 여는 서버 — 표준 라이브러리만 쓴다.

왜 공식 SDK 를 안 쓰나
    폐쇄망이다. 공식 mcp SDK 는 pydantic·starlette·uvicorn·cryptography 등
    30개 남짓을 끌고 온다. 이 프로젝트는 원래 '단일 파일 · pip only · CDN
    없음' 전제로 만들어져 있어서 그걸 다 넣을 수 없다.
    MCP 는 실체가 JSON-RPC 2.0 이라 stdio 로 주고받으면 stdlib 로 충분하다.
    (규격이 맞는지는 망 열린 곳에서 공식 SDK 클라이언트로 검증했다 —
     tests/test_mcp.py 는 그 결과를 stdlib 만으로 재현한다.)

읽기 전용이다
    등록·수정·삭제·상태변경은 **일부러 안 연다**. 서윤(아바타)이 사람 대신
    요청을 지우거나 상태를 바꾸면 이력 관리의 의미가 없어진다. 조회만 준다.

실행
    python mcp_server.py            # stdio 로 대기 (부모가 띄운다)
    QA_BASE=http://127.0.0.1:10500  # app.py 주소 (기본값이 이것)
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("QA_BASE", "http://127.0.0.1:10500").rstrip("/")
TIMEOUT = float(os.environ.get("QA_TIMEOUT", "10"))
PROTO = "2025-06-18"
NAME, VERSION = "qa-reqlog", "1.0.0"
MAX_ROWS = 20          # 프롬프트에 실릴 글이라 무한정 못 준다


# ── app.py 조회 ───────────────────────────────────────────────────────────
def _get(path, params=None):
    url = BASE + path
    if params:
        pairs = []
        for k, v in params.items():
            if v in (None, "", []):
                continue
            for one in (v if isinstance(v, (list, tuple)) else [v]):
                pairs.append((k, str(one)))
        if pairs:
            url += "?" + urllib.parse.urlencode(pairs)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    # ★사내 프록시를 타면 안 된다 — 같은 기계 안의 주소다.
    #   ProxyHandler({}) 를 안 주면 http_proxy 환경변수에 끌려간다.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


# ── 도구 ──────────────────────────────────────────────────────────────────
TOOLS = [
    {"name": "qa_meta",
     "description": "요청/응답 관리 현황 — 총건수·미결·확인완료·상태별 건수·"
                    "대상(FAB) 목록·사람 목록",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "qa_items",
     "description": "요청을 조건으로 찾는다. 조건을 하나도 안 주면 최근 것부터 준다.",
     "inputSchema": {"type": "object", "properties": {
         "q": {"type": "string", "description": "본문·요청자·응답 안에서 찾을 말"},
         "status": {"type": "string",
                    "description": "대기 / 검토중 / 적용완료 / 보류 / 반려"},
         "category": {"type": "string", "description": "요청 / 제안 / 확인 / 이슈"},
         "target": {"type": "string", "description": "대상 FAB (예: M16HUB)"},
         "requester": {"type": "string", "description": "요청자 이름"},
         "confirmed": {"type": "string",
                       "description": "Y=고객확인 끝난 것만, N=아직 안 된 것만"},
         "from": {"type": "string", "description": "요청일 시작 (YYYY-MM-DD)"},
         "to": {"type": "string", "description": "요청일 끝 (YYYY-MM-DD)"},
     }}},
    {"name": "qa_item",
     "description": "요청 한 건을 응답·첨부까지 펼쳐서 본다",
     "inputSchema": {"type": "object",
                     "properties": {"seq": {"type": "integer",
                                            "description": "화면에 보이는 No."}},
                     "required": ["seq"]}},
    {"name": "qa_history",
     "description": "요청 한 건의 변경 이력 (누가 언제 무엇을 바꿨나)",
     "inputSchema": {"type": "object",
                     "properties": {"seq": {"type": "integer"}},
                     "required": ["seq"]}},
]


def _one_line(it):
    return "#{} [{}] {} · 요청자 {} · 대상 {} · 요청일 {}{} — {}".format(
        it.get("seq"), it.get("status") or "?", it.get("category") or "?",
        it.get("requester") or "-", ", ".join(it.get("tags") or []) or "-",
        it.get("request_date") or "-",
        " · 확인완료" if it.get("confirmed_at") else "",
        (it.get("content") or "").replace("\n", " ")[:100])


def _find(seq):
    """seq(화면 No.)로 한 건을 집는다. app.py 는 seq 검색이 없어서 훑는다."""
    for it in (_get("/api/items") or {}).get("items") or []:
        if int(it.get("seq") or 0) == int(seq):
            return it
    return None


def t_meta(_):
    """현황 — ★말이 헷갈리면 안 된다.

    예전엔 한 줄에 이렇게 적었다:
        총 5건 · 미결 5건 · 고객확인 완료 0건
        상태별: 보류 1건 · 적용완료 4건
    '완료' 가 두 가지 뜻(고객확인 완료 / 적용완료)으로 들어 있고, '미결 5건'
    과 '적용완료 4건' 이 서로 모순돼 보인다. 실제로 서윤이 이걸
        "조회 현황은 0건이며, 총 4건이 완료된 기록만 남아 있어요"
    로 읽었다 — 총 5건도, 보류 1건도 통째로 사라졌다. 가장 중요한 게.
    """
    m = _get("/api/meta")
    counts = m.get("counts") or {}
    total = m.get("total") or 0
    conf = m.get("confirmed") or 0
    # 상태는 많은 것부터 — 읽는 사람이 먼저 봐야 할 순서
    order = sorted(counts.items(), key=lambda kv: -kv[1])
    return ("요청 {}건 (등록된 전부)\n"
            "진행 상태: {}\n"
            "고객 최종확인: {}건 중 {}건 확인됨\n"
            "대상: {}\n"
            "올린 사람: {}".format(
                total,
                " · ".join("{} {}건".format(k, v) for k, v in order) or "없음",
                total, conf,
                ", ".join(m.get("tags") or []) or "없음",
                ", ".join(m.get("people") or []) or "없음"))


def t_items(a):
    d = _get("/api/items", {k: a.get(k) for k in
                            ("q", "status", "category", "target", "requester",
                             "confirmed", "from", "to")})
    items = d.get("items") or []
    if not items:
        return "그 조건에 해당하는 요청이 없다."
    L = ["{}건 (최근 순, 최대 {}건까지 보여준다)".format(len(items), MAX_ROWS)]
    L += [_one_line(x) for x in items[:MAX_ROWS]]
    if len(items) > MAX_ROWS:
        L.append("… 그 밖 {}건은 안 실었다".format(len(items) - MAX_ROWS))
    return "\n".join(L)


def t_item(a):
    it = _find(a.get("seq"))
    if it is None:
        return "No.{} 요청이 없다.".format(a.get("seq"))
    L = [_one_line(it), "내용: " + (it.get("content") or "").strip()]
    if it.get("applied_date"):
        L.append("적용일: " + it["applied_date"])
    if it.get("confirmed_at"):
        L.append("고객확인: {} {}".format(it["confirmed_at"][:10],
                                          it.get("confirmed_by") or ""))
    for r in it.get("responses") or []:
        L.append("  ↳ 응답 [{}] {} — {}".format(
            (r.get("created_at") or "")[:16], r.get("responder") or "?",
            (r.get("content") or "").replace("\n", " ")[:200]))
    atts = [x.get("filename") for x in (it.get("attachments") or [])]
    if atts:
        L.append("첨부 {}건: {}".format(len(atts), ", ".join(atts)))
    return "\n".join(L)


def t_history(a):
    it = _find(a.get("seq"))
    if it is None:
        return "No.{} 요청이 없다.".format(a.get("seq"))
    rows = (_get("/api/items/{}/history".format(it["id"])) or {}).get("history") or []
    if not rows:
        return "No.{} 변경 이력이 없다.".format(a.get("seq"))
    L = ["No.{} 변경 이력 {}건".format(a.get("seq"), len(rows))]
    for r in rows[:MAX_ROWS]:
        bit = r.get("field") or r.get("action") or "?"
        old, new = r.get("old_value"), r.get("new_value")
        chg = ("{} → {}".format(old or "빈칸", new or "빈칸")
               if (old or new) else "")
        L.append("{} · {} · {} {}".format((r.get("created_at") or "")[:16],
                                          r.get("actor") or "?", bit, chg).strip())
    return "\n".join(L)


HANDLERS = {"qa_meta": t_meta, "qa_items": t_items,
            "qa_item": t_item, "qa_history": t_history}


# ── JSON-RPC ──────────────────────────────────────────────────────────────
def handle(msg):
    """요청 하나 → 응답 dict. 알림(id 없음)이면 None."""
    mid, method, p = msg.get("id"), msg.get("method"), msg.get("params") or {}

    def ok(res):
        return {"jsonrpc": "2.0", "id": mid, "result": res}

    def err(code, text):
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": code, "message": text}}

    if method == "initialize":
        # ★규격: 클라이언트가 부른 버전을 우리가 감당하면 그대로 돌려준다.
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
        except urllib.error.URLError as e:
            # ★도구 실패는 프로토콜 오류가 아니다 — isError 결과로 준다.
            #   여기서 JSON-RPC error 를 내면 클라이언트가 연결을 접는다.
            return ok({"content": [{"type": "text", "text":
                                    "요청관리 서버({})에 못 붙었다: {}"
                                    .format(BASE, e)}], "isError": True})
        except Exception as e:  # noqa: BLE001
            return ok({"content": [{"type": "text", "text": str(e)}],
                       "isError": True})
        return ok({"content": [{"type": "text", "text": text}],
                   "isError": False})
    if mid is None:
        return None          # notifications/* — 답하지 않는다
    return err(-32601, "모르는 method: {}".format(method))


def _force_utf8():
    """stdin/stdout 을 UTF-8 로 못 박는다.

    ★윈도우에서는 파이프의 기본 인코딩이 지역 코드페이지(한국은 cp949)다.
      우리가 내보내는 글에는 '·' '—' '★' 같은 글자가 있어서 cp949 로는
      못 쓴다 → UnicodeEncodeError 로 **이 프로세스가 죽는다**.
      그러면 부모는 죽은 파이프에 쓰다가 [Errno 22] Invalid argument 를
      맞는다 — 실제로 그 증상이 났다. 원인은 여기다.
    """
    for f, kw in ((sys.stdin, {}), (sys.stdout, {"newline": "\n"})):
        try:
            f.reconfigure(encoding="utf-8", errors="replace", **kw)
        except Exception:      # noqa: BLE001  (아주 옛 파이썬·이상한 스트림)
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
            continue         # 깨진 줄은 버린다 (규격상 답할 id 도 없다)
        res = handle(msg)
        if res is not None:
            stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
            stdout.flush()


def selfcheck():
    """`python qa/mcp_server.py --check` — 주소가 맞는지만 본다.

    ★"왜 안 되지" 의 답은 거의 늘 **주소**다. 요청관리를 10.139.x.x 에 띄워
      놓고 여기는 127.0.0.1 을 보고 있으면 조용히 아무것도 안 나온다.
      그걸 한 줄로 알려 준다.
    """
    print("보는 주소: {}".format(BASE))
    try:
        m = _get("/api/meta")
    except Exception as e:  # noqa: BLE001
        print("붙지 못했다: {}".format(e))
        print("")
        print("  · 그 주소에서 qa/app.py 가 떠 있나?  (python app.py)")
        print("  · 다른 PC 면 주소를 줘야 한다:")
        print("      python run.py --qa http://<그 PC>:10500")
        print("      또는  set QA_BASE=http://<그 PC>:10500")
        print("  · 방화벽에서 10500 이 열려 있나?")
        return 1
    print("붙었다 — 총 {}건 · 미결 {}건 · 대상 {}".format(
        m.get("total"), m.get("open"),
        ", ".join(m.get("tags") or []) or "없음"))
    n = len((_get("/api/items") or {}).get("items") or [])
    print("목록 조회 {}건".format(n))
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(selfcheck())
    serve()
