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
# ── 얼마나 실어 보낼까 ────────────────────────────────────────────────
# ★프롬프트에 그대로 실리는 글이라 무한정 못 준다. 그런데 **너무 조였더니**
#   서윤이 요청 내용을 반도 못 봤다. 목록 한 줄이 100자에서 끊겨
#   "M16HUB 반송 지연 관련 개선 요청드립니다. 현재 R-A 룰이…" 까지만 가고
#   정작 사람이 물어보는 **요청사항 (1)(2)(3)** 은 한 글자도 안 갔다.
#   글자 수로만 막지 말고, **좁혀졌으면 통째로 편다**.
MAX_ROWS = int(os.environ.get("QA_MAX_ROWS", "20"))    # 한 줄 요약을 적을 최소 건수
HARD_ROWS = 60         # 예산이 남아도 여기까지만 (한 질문에 60줄이면 충분하다)
# ★건수가 아니라 **예산**이 기준이다. 실제 등록분(9건)을 전부 펴도 2987자로
#   예산 4000자에 다 들어가는데, 건수 상한 6건에 걸려 한 줄 요약만 갔다.
#   여기 숫자는 '말도 안 되게 많을 때' 를 막는 안전판일 뿐이다.
FULL_ROWS = int(os.environ.get("QA_FULL_ROWS", "25"))  # 통째로 펼 건수 안전판
LIST_BUDGET = int(os.environ.get("QA_LIST_BUDGET", "4000"))   # qa_items 글자 상한
ITEM_BUDGET = int(os.environ.get("QA_ITEM_BUDGET", "2500"))   # qa_item 글자 상한
LINE_CUT = 110         # 한 줄 요약에서 본문을 자르는 길이


def _fit(lines, budget, tail=""):
    """예산 안에서 줄을 담는다. 넘치면 **몇 줄을 못 실었는지 밝힌다**.

    ★말없이 자르면 받는 쪽이 '이게 전부' 로 읽는다. 실제로 그래서 서윤이
      "총 4건이 완료된 기록만 남아 있어요" 라고 답한 적이 있다.
    """
    out, used = [], 0
    for i, ln in enumerate(lines):
        if used + len(ln) > budget and out:
            left = len(lines) - i
            out.append("… 길어서 {}건은 안 실었다. 번호를 대면(예: No.{}) "
                       "그 건만 펼쳐 볼 수 있다.".format(left, _seq_of(lines[i])))
            break
        out.append(ln)
        used += len(ln) + 1
    if tail:
        out.append(tail)
    return "\n".join(out)


def _seq_of(line):
    """'#37 [적용완료] …' 같은 줄에서 번호만. 못 찾으면 물음표."""
    t = str(line or "").lstrip()
    if t.startswith("#"):
        n = ""
        for ch in t[1:]:
            if not ch.isdigit():
                break
            n += ch
        if n:
            return n
    return "?"


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
    """목록 한 줄. 본문은 여기서 자른다 — 대신 **뒤에 뭐가 더 있는지** 적는다.

    ★'응답 2건' 을 안 적었더니 서윤이 목록만 보고 "아직 응답이 없습니다" 라고
      답했다. 실제로는 응답에 결론(적용 예정일)이 들어 있었다. 안 실은 것은
      없는 것과 다르다 — 있다는 사실은 반드시 남긴다.
    """
    body = (it.get("content") or "").replace("\n", " ").strip()
    more = []
    if len(body) > LINE_CUT:
        more.append("본문 더 있음")
    nr = len(it.get("responses") or [])
    if nr:
        more.append("응답 {}건".format(nr))
    na = len(it.get("attachments") or [])
    if na:
        more.append("첨부 {}건".format(na))
    return "{} — {}{}".format(
        _head(it), body[:LINE_CUT],
        "  ({})".format(" · ".join(more)) if more else "")


def _head(it):
    """번호·상태·사람·날짜만. 본문은 붙이지 않는다."""
    return "#{} [{}] {} · 요청자 {} · 대상 {} · 요청일 {}{}".format(
        it.get("seq"), it.get("status") or "?", it.get("category") or "?",
        it.get("requester") or "-", ", ".join(it.get("tags") or []) or "-",
        it.get("request_date") or "-",
        " · 확인완료" if it.get("confirmed_at") else "")


def _detail(it):
    """한 건을 응답·첨부까지 펼친 여러 줄.

    ★응답을 200자에서 자르던 자리다. 사람이 궁금해하는 **결론**(적용 예정일,
      어느 FAB 만 적용하기로 했는지)은 응답 끝에 온다 — 앞 200자만 보내면
      정확히 그 부분이 날아간다. 여기서는 자르지 않고, 전체 길이는 부르는
      쪽이 예산으로 막는다.
    """
    L = [_head(it)]
    body = (it.get("content") or "").strip()
    if body:
        L.append("내용: " + body)
    if it.get("applied_date"):
        L.append("적용일: " + it["applied_date"])
    if it.get("confirmed_at"):
        L.append("고객확인: {} {}".format(it["confirmed_at"][:10],
                                          it.get("confirmed_by") or ""))
    for r in it.get("responses") or []:
        L.append("  ↳ 응답 [{}] {} — {}".format(
            (r.get("created_at") or "")[:16], r.get("responder") or "?",
            (r.get("content") or "").replace("\n", " ").strip()))
    atts = [x.get("filename") for x in (it.get("attachments") or [])]
    if atts:
        L.append("  첨부 {}건: {}".format(len(atts), ", ".join(atts)))
    return "\n".join(L)


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
    note = ""
    if not items and a.get("q"):
        # ★검색어가 빗나갔다고 "없다" 로 끝내면 안 된다. 사람이 쓴 말
        #   ("레일 캡쳐", "PIO") 이 등록된 글자와 안 맞는 일은 흔하다.
        #   그럴 때 빈손으로 돌아오면 서윤은 "그런 요청 없습니다" 라고
        #   단언한다 — 실제로는 있는데도.
        d = _get("/api/items", {k: a.get(k) for k in
                                ("status", "category", "target", "requester",
                                 "confirmed", "from", "to")})
        items = d.get("items") or []
        if items:
            note = ("'{}' 로는 못 찾아서 **조건을 풀고 전체를 본다**. "
                    "아래에서 직접 골라 읽어라.\n".format(a["q"]))
    if not items:
        return "그 조건에 해당하는 요청이 없다."

    # ★몇 건 안 되면 **내용을 통째로 편다.** 이게 이 도구의 핵심이다.
    #   사람은 "M16HUB 야간 오탐 건 어떻게 됐어?" 라고 묻지 "No.37 펼쳐줘"
    #   라고 묻지 않는다. 그래서 qa_item(번호가 있어야 부른다)은 거의 안
    #   불렸고, 서윤은 100자짜리 요약만 들고 답해야 했다. 조건으로 좁혀졌다는
    #   건 사람이 그걸 물었다는 뜻이다 — 그러면 다 보여준다.
    #
    #   ★기준은 **건수가 아니라 예산**이다. 건수로 자르면(예: 3건 이하)
    #     짧은 요청 7건이 예산 절반도 안 쓰면서 전부 잘려 나간다. 실제로
    #     그랬다 — 7건 1359자에 예산은 4000자였다. 넣을 수 있으면 넣는다.
    if len(items) <= FULL_ROWS:
        full = [_detail(x) for x in items]
        if sum(len(x) + 1 for x in full) <= LIST_BUDGET - 40:
            return note + "{}건 — 내용과 응답까지 폅니다.\n".format(len(items)) \
                   + "\n\n".join(full)

    head = note + "{}건 (최근 순).".format(len(items))
    lines = [_one_line(x) for x in items[:HARD_ROWS]]
    # 예산이 남으면 MAX_ROWS 를 넘겨서도 싣는다 — 20건에서 딱 끊으면
    # "그래서 나머지는?" 에 영영 답을 못 한다.
    body = _fit(lines, LIST_BUDGET - len(head))
    tail = ("\n… 그 밖 {}건은 안 실었다".format(len(items) - HARD_ROWS)
            if len(items) > HARD_ROWS else "")
    return head + "\n" + body + tail


def t_item(a):
    it = _find(a.get("seq"))
    if it is None:
        return "No.{} 요청이 없다.".format(a.get("seq"))
    return _fit(_detail(it).split("\n"), ITEM_BUDGET)


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
