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
    m = _get("/api/meta")
    counts = m.get("counts") or {}
    return ("총 {}건 · 미결 {}건 · 고객확인 완료 {}건\n"
            "상태별: {}\n대상: {}\n사람: {}".format(
                m.get("total"), m.get("open"), m.get("confirmed"),
                " · ".join("{} {}건".format(k, v)
                           for k, v in counts.items()) or "없음",
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


def serve(stdin=None, stdout=None):
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


if __name__ == "__main__":
    serve()
