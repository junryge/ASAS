# -*- coding: utf-8 -*-
"""MCP — 요청/응답 관리(qa/app.py)를 서윤에게 물려주는 길.

왜 직접 짰나
    폐쇄망이다. 공식 mcp SDK 는 pydantic·starlette·uvicorn 등 30개 남짓을
    끌고 온다. MCP 는 실체가 JSON-RPC 2.0 이라 stdlib 로 짜진다.
    규격이 맞는지는 망 열린 곳에서 공식 SDK 로 양방향 확인했다:
      · 우리 서버 ↔ 공식 SDK 클라이언트  — 악수·tools/list·tools/call 통과
      · 우리 클라이언트 ↔ 공식 SDK 서버  — 같은 것 통과
    여기서는 그 결과를 **SDK 없이** 재현한다. 폐쇄망 PC 에서도 돌아야 한다.

무엇을 못 박나
    1. 규격 — 악수/도구목록/도구호출/알림/오류 처리
    2. 읽기 전용 — 등록·수정·삭제 도구는 **없어야** 한다
    3. 붙음 — 진짜 프로세스를 띄워 stdio 로 주고받는다
    4. 서윤 — 결과가 프롬프트의 **제 칸**에 실리고, [관제 근거] 에 섞이지 않는다
"""
import importlib.util
import json
import os
import socket
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from . import util

sys.path.insert(0, os.path.join(util.BASE, "avatar_2d"))
from avatar import config, llm, mcp_client, sentinel   # noqa: E402


def _load_server():
    """qa/mcp_server.py 를 모듈로 집어 온다 (qa 는 패키지가 아니다)."""
    path = os.path.join(util.BASE, "qa", "mcp_server.py")
    spec = importlib.util.spec_from_file_location("qa_mcp_server", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SRV = _load_server()

# app.py 가 돌려주는 모양 그대로 (진짜 응답을 받아 적었다)
META = {"categories": ["요청", "제안", "확인", "이슈"],
        "statuses": ["대기", "검토중", "적용완료", "보류", "반려"],
        "tags": ["M14", "M16B", "M16HUB"],
        "people": ["김반송", "박관제"], "counts": {"검토중": 1, "대기": 1},
        "total": 2, "confirmed": 0, "open": 2}
ITEMS = {"items": [
    {"id": 7, "seq": 2, "status": "대기", "category": "요청",
     "requester": "박관제", "target": "M14", "tags": ["M14"],
     "request_date": "2026-08-26", "content": "M14 4분 초과 알람 임계 60으로",
     "confirmed_at": None, "applied_date": None,
     "responses": [], "attachments": []},
    {"id": 3, "seq": 1, "status": "검토중", "category": "이슈",
     "requester": "김반송", "target": "M16HUB", "tags": ["M16HUB"],
     "request_date": "2026-08-25", "content": "3층 STK 저장율 90% 초과 반복",
     "confirmed_at": "2026-08-26 09:00", "confirmed_by": "김윤환TL",
     "applied_date": "2026-08-26",
     "responses": [{"id": 1, "responder": "이설비", "created_at": "2026-08-26 10:00",
                    "content": "반출 우선순위 올렸습니다", "attachments": []}],
     "attachments": [{"filename": "그래프.png"}]},
]}
HIST = {"history": [{"created_at": "2026-08-26 11:00", "actor": "이설비",
                     "field": "status", "old_value": "대기",
                     "new_value": "검토중"}]}


# 지금 어떤 자료를 세워 둘지 — 시험이 갈아 끼운다 (실제 등록 데이터 재현용)
DATA = {"items": None, "meta": None}


def _filter(items, qs):
    """app.py 의 fetch_items 와 같은 규칙으로 좁힌다 (필요한 것만)."""
    import urllib.parse
    p = {k: v[0] for k, v in urllib.parse.parse_qs(qs).items()}
    out = items
    if p.get("status"):
        out = [r for r in out if r.get("status") == p["status"]]
    if p.get("category"):
        out = [r for r in out if r.get("category") == p["category"]]
    if p.get("target"):
        out = [r for r in out if p["target"] in (r.get("target") or "")]
    if p.get("requester"):
        out = [r for r in out if p["requester"] in (r.get("requester") or "")]
    if p.get("q"):
        q = p["q"]
        out = [r for r in out
               if q in (r.get("content") or "") or q in (r.get("requester") or "")
               or q in (r.get("target") or "")]
    return out


class 가짜_요청관리(BaseHTTPRequestHandler):
    """app.py 대신 세워 두는 최소 서버 — flask 없이 돈다.
    ★조건(q/status/target)을 **실제로 걸러야** 한다. 자식 프로세스가 HTTP 로
      물어보므로 파이썬 안에서 _get 을 갈아 끼우는 것으로는 안 잡힌다."""

    def do_GET(self):                      # noqa: N802
        p, _, qs = self.path.partition("?")
        if p == "/api/meta":
            body = DATA["meta"] or META
        elif p == "/api/items":
            src = DATA["items"] if DATA["items"] is not None else ITEMS["items"]
            body = {"items": _filter(src, qs)}
        elif p.endswith("/history"):
            body = HIST
        else:
            self.send_error(404)
            return
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):             # 조용히
        pass


class _Fake(unittest.TestCase):
    """가짜 요청관리 서버를 띄운 채로 도는 시험."""

    @classmethod
    def setUpClass(cls):
        cls.httpd = HTTPServer(("127.0.0.1", 0), 가짜_요청관리)
        cls.port = cls.httpd.server_address[1]
        cls.base = "http://127.0.0.1:{}".format(cls.port)
        cls.th = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.th.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        self._old = SRV.BASE
        SRV.BASE = self.base
        self.addCleanup(lambda: setattr(SRV, "BASE", self._old))


# ═══ 1. 규격 ═════════════════════════════════════════════════════════════
class 규격을_지킨다(_Fake):

    def test_악수는_부른_버전을_돌려준다(self):
        r = SRV.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                        "params": {"protocolVersion": "2025-03-26"}})
        self.assertEqual(r["id"], 1)
        self.assertEqual(r["result"]["protocolVersion"], "2025-03-26")
        self.assertEqual(r["result"]["serverInfo"]["name"], "qa-reqlog")
        self.assertIn("tools", r["result"]["capabilities"])

    def test_버전을_안_주면_우리_기본값(self):
        r = SRV.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                        "params": {}})
        self.assertEqual(r["result"]["protocolVersion"], SRV.PROTO)

    def test_알림에는_답하지_않는다(self):
        """★id 가 없는 것에 답하면 규격 위반이다 — 클라이언트가 끊는다."""
        for m in ("notifications/initialized", "notifications/cancelled",
                  "뭔지모를알림"):
            self.assertIsNone(SRV.handle({"jsonrpc": "2.0", "method": m}))

    def test_모르는_method_는_오류로(self):
        r = SRV.handle({"jsonrpc": "2.0", "id": 9, "method": "resources/list"})
        self.assertEqual(r["error"]["code"], -32601)

    def test_도구마다_이름_설명_스키마가_있다(self):
        ts = SRV.handle({"jsonrpc": "2.0", "id": 1,
                         "method": "tools/list"})["result"]["tools"]
        self.assertTrue(ts)
        for t in ts:
            self.assertTrue(t["name"], t)
            self.assertTrue(t["description"], t["name"])
            self.assertEqual(t["inputSchema"]["type"], "object", t["name"])

    def test_없는_도구는_거부한다(self):
        r = SRV.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                        "params": {"name": "qa_지우기", "arguments": {}}})
        self.assertEqual(r["error"]["code"], -32602)

    def test_도구_실패는_프로토콜_오류가_아니다(self):
        """★여기서 JSON-RPC error 를 내면 클라이언트가 연결을 접는다.
        요청관리 서버가 죽어 있어도 대화는 이어져야 한다."""
        SRV.BASE = "http://127.0.0.1:1"        # 아무도 없는 포트
        r = SRV.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                        "params": {"name": "qa_meta", "arguments": {}}})
        self.assertNotIn("error", r)
        self.assertTrue(r["result"]["isError"])
        self.assertIn("못 붙었다", r["result"]["content"][0]["text"])

    def test_깨진_줄은_버린다(self):
        import io
        out = io.StringIO()
        SRV.serve(io.StringIO('{"어쩌구\n\n{"jsonrpc":"2.0","id":1,'
                              '"method":"ping"}\n'), out)
        got = [json.loads(x) for x in out.getvalue().splitlines() if x.strip()]
        self.assertEqual(len(got), 1, "깨진 줄에도 답했다")
        self.assertEqual(got[0]["id"], 1)


# ═══ 2. 읽기 전용 ════════════════════════════════════════════════════════
class 읽기만_연다(_Fake):
    """★서윤이 사람 대신 요청을 지우거나 상태를 바꾸면 이력 관리가 무너진다.
    app.py 에는 쓰기 API 가 있지만 MCP 로는 **일부러 안 연다**."""

    WRITE = ("create", "update", "delete", "add", "set", "confirm", "import",
             "등록", "수정", "삭제", "변경")

    def test_쓰기_도구가_없다(self):
        for t in SRV.TOOLS:
            low = t["name"].lower()
            for w in self.WRITE:
                self.assertNotIn(w, low, "쓰기 도구가 열렸다: " + t["name"])

    def test_손잡이가_GET_뿐이다(self):
        """서버 소스에 POST/PUT/DELETE 를 보내는 곳이 없어야 한다."""
        with open(os.path.join(util.BASE, "qa", "mcp_server.py"),
                  encoding="utf-8") as f:
            src = f.read()
        for verb in ('"POST"', '"PUT"', '"DELETE"', "method=\"POST\""):
            self.assertNotIn(verb, src, "쓰기 호출이 들어 있다: " + verb)


# ═══ 3. 도구가 제 값을 준다 ══════════════════════════════════════════════
class 도구가_제_값을_준다(_Fake):

    def _call(self, name, args=None):
        r = SRV.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                        "params": {"name": name, "arguments": args or {}}})
        self.assertNotIn("error", r)
        self.assertFalse(r["result"]["isError"], r["result"])
        return r["result"]["content"][0]["text"]

    def test_현황(self):
        t = self._call("qa_meta")
        self.assertIn("요청 2건", t)
        self.assertIn("검토중 1건", t)
        self.assertIn("M16HUB", t)
        self.assertIn("김반송", t)

    def test_목록은_상태와_대상까지_적는다(self):
        t = self._call("qa_items")
        self.assertIn("#2", t)
        self.assertIn("[대기]", t)
        self.assertIn("M16HUB", t)
        self.assertIn("확인완료", t, "고객확인 여부가 안 보인다")

    def test_한_건은_응답과_첨부까지_펼친다(self):
        t = self._call("qa_item", {"seq": 1})
        self.assertIn("↳ 응답", t)
        self.assertIn("이설비", t)
        self.assertIn("반출 우선순위", t)
        self.assertIn("그래프.png", t)
        self.assertIn("고객확인", t)

    def test_없는_번호는_없다고_한다(self):
        self.assertIn("없다", self._call("qa_item", {"seq": 99}))

    def test_이력은_바뀐_값을_적는다(self):
        t = self._call("qa_history", {"seq": 1})
        self.assertIn("대기 → 검토중", t)
        self.assertIn("이설비", t)

    def _many(self, n, content=None):
        """가짜 목록 n건을 세운다 (본문을 길게 줄 수도 있다)."""
        base = dict(ITEMS["items"][0])
        if content is not None:
            base["content"] = content
        big = {"items": [dict(base, seq=i, id=i) for i in range(1, n + 1)]}
        keep = SRV._get
        SRV._get = lambda p, q=None: big if p == "/api/items" else keep(p, q)
        self.addCleanup(lambda: setattr(SRV, "_get", keep))

    def test_예산에_들어가면_안_자른다(self):
        """★건수로 자르면 안 된다. 실제 등록분(9건)을 다 펴도 3천 자라
        예산에 들어가는데, 예전 건수 상한(20건)에 걸려 잘려 나갔다."""
        self._many(40)                      # 짧은 본문 40건
        t = self._call("qa_items")
        self.assertIn("40건", t)
        self.assertNotIn("안 실었다", t, "예산이 남는데 잘랐다")
        self.assertIn("#40", t, "마지막 건이 빠졌다")

    def test_목록이_길면_잘랐다고_밝힌다(self):
        """★말없이 자르면 '이게 전부' 로 읽힌다."""
        self._many(40, content="가" * 400)   # 본문이 길어 예산을 넘긴다
        t = self._call("qa_items")
        self.assertIn("40건", t)
        # ★몇 건을 못 실었는지와, 그 건을 어떻게 볼 수 있는지까지 말해야 한다.
        #   "안 실었다" 만 있으면 받는 쪽은 거기서 멈춘다.
        self.assertRegex(t, r"길어서 \d+건은 안 실었다")
        self.assertIn("번호를 대면", t)
        self.assertLessEqual(len(t), SRV.LIST_BUDGET + 400, "예산을 넘겼다")


# ═══ 4. 진짜로 붙는다 (프로세스를 띄운다) ════════════════════════════════
class 진짜_프로세스에_붙는다(_Fake):
    """★소스만 보면 못 잡는다. 악수·줄바꿈·버퍼링이 어긋나면 여기서 걸린다."""

    def _client(self):
        c = mcp_client.Client(
            sys.executable, [os.path.join(util.BASE, "qa", "mcp_server.py")],
            env={"QA_BASE": self.base}, cwd=util.BASE, timeout=20)
        self.addCleanup(c.close)
        return c

    def test_악수하고_도구를_받는다(self):
        c = self._client()
        self.assertEqual(c.server["name"], "qa-reqlog")
        self.assertEqual(c.proto, mcp_client.PROTO)
        self.assertEqual({t["name"] for t in c.tools()},
                         {"qa_meta", "qa_items", "qa_item", "qa_history"})

    def test_도구를_부른다(self):
        c = self._client()
        txt, bad = c.call("qa_items", {"target": "M16HUB"})
        self.assertFalse(bad)
        self.assertIn("M16HUB", txt)

    def test_한글이_안_깨진다(self):
        """★인코딩을 안 정하면 사내 PC(cp949)에서 여기가 깨진다."""
        c = self._client()
        txt, _ = c.call("qa_meta")
        self.assertIn("김반송", txt)

    def test_여러_번_불러도_이어진다(self):
        c = self._client()
        for _ in range(3):
            self.assertFalse(c.call("qa_meta")[1])

    def test_없는_도구는_실패로_돌아온다(self):
        """★예외로 터지면 대화 한 줄이 통째로 500 이 된다."""
        c = self._client()
        txt, bad = c.call("없는도구")
        self.assertTrue(bad)
        self.assertTrue(txt)

    def test_서버가_죽으면_알아챈다(self):
        c = self._client()
        c.proc.kill()
        c.proc.wait(timeout=5)
        with self.assertRaises(mcp_client.McpError):
            c.tools()


# ═══ 5. Hub — 걸릴 때만 띄운다 ═══════════════════════════════════════════
class 상세한_내용까지_보낸다(_Fake):
    """★실제 증상 — "하기는 잘해, 근데 상세한 내용을 물어보면 몰라".

    등록된 요청은 여러 문단짜리다. 목록 한 줄이 100자에서 끊겨
        "M16HUB 반송 지연 관련 개선 요청드립니다. 현재 R-A 룰이…"
    까지만 가고, 정작 사람이 묻는 **요청사항 (1)(2)(3)** 과 응답의
    **결론(적용 예정일)** 은 한 글자도 안 갔다. 응답은 200자에서 잘렸다.
    """

    LONG = ("M16HUB 반송 지연 개선 요청드립니다. 야간(23~05시)에는 물동이 적어 "
            "평균이 흔들려 오탐이 잦습니다. 아래 세 가지를 부탁드립니다.\n"
            "요청사항: (1) 야간은 창을 5분으로 늘려주세요. (2) FABSTORAGERATIO 가 "
            "0.8 이상일 때만 발동하도록 AND 조건을 걸어주세요. "
            "(3) 8/12 02:14 오탐은 리포트에서 제외.")
    ANSWER = ("검토 결과 야간 창 확대는 반영 가능합니다. 다만 AND 조건은 M16HUB "
              "만 적용하고 나머지 FAB 은 기존대로 두는 것이 좋겠습니다. 이유는 "
              "M14/M14B 는 스토리지 비율이 상시 낮아 룰이 사실상 죽습니다. "
              "8/12 오탐은 제외 처리했고 야간 가중치 표를 별도로 뒀습니다. "
              "적용 예정일은 8/28 입니다.")

    def _stand(self, n=1):
        one = dict(ITEMS["items"][0], content=self.LONG, seq=7, id=7,
                   responses=[{"id": 1, "responder": "서지원",
                               "created_at": "2026-08-21 10:20",
                               "content": self.ANSWER, "attachments": []}])
        rows = [dict(one, seq=7 + i, id=7 + i) for i in range(n)]
        keep = SRV._get

        def fake(p, q=None):
            if p != "/api/items":
                return keep(p, q)
            # ★검색어를 무시하면 '빗나감' 상황 자체를 못 만든다
            out = rows
            if (q or {}).get("q"):
                out = [r for r in out if q["q"] in (r.get("content") or "")]
            return {"items": out}

        SRV._get = fake
        self.addCleanup(lambda: setattr(SRV, "_get", keep))

    def _call(self, name, args=None):
        r = SRV.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                        "params": {"name": name, "arguments": args or {}}})
        return r["result"]["content"][0]["text"]

    def test_좁혀지면_본문을_통째로_준다(self):
        """★핵심. 사람은 "No.7 펼쳐줘" 가 아니라 "그 요청 뭐야" 라고 묻는다."""
        self._stand(1)
        t = self._call("qa_items")
        self.assertIn("(3) 8/12 02:14 오탐은 리포트에서 제외", t,
                      "요청사항 끝이 잘렸다")

    def test_응답의_결론까지_준다(self):
        """★응답 끝에 결론이 온다 — 앞 200자만 보내면 정확히 그게 날아간다."""
        self._stand(1)
        for tool, args in (("qa_items", {}), ("qa_item", {"seq": 7})):
            self.assertIn("적용 예정일은 8/28", self._call(tool, args),
                          "{} 에서 응답 결론이 잘렸다".format(tool))

    def test_한_줄_요약도_뒤에_뭐가_있는지_밝힌다(self):
        """★'응답 2건' 을 안 적었더니 목록만 보고 "아직 응답이 없습니다" 라고
        답했다. 안 실은 것은 없는 것과 다르다."""
        self._stand(40)                       # 예산을 넘겨 한 줄 요약으로 떨어진다
        t = self._call("qa_items")
        self.assertNotIn("내용:", t, "이 시험은 한 줄 요약 상태여야 한다")
        self.assertIn("본문 더 있음", t)
        self.assertIn("응답 1건", t)

    def test_검색어가_빗나가도_빈손으로_안_온다(self):
        """★"그런 요청 없습니다" 라고 단언하게 만들면 안 된다 — 있는데도."""
        self._stand(1)
        t = self._call("qa_items", {"q": "있을리없는말123"})
        self.assertNotIn("해당하는 요청이 없다", t)
        self.assertIn("조건을 풀고 전체를 본다", t)


class 조회한_것을_대화_안에서_기억한다(_Fake):
    """★실제 증상 — "MCP 문제 이후에 내용을 기억을 못하는것도 문제지".

    "7번 요청 뭐야?" 로 조회가 걸려 내용을 받아 놓고, 바로 다음
    "그럼 언제 적용돼?" 에는 '요청'·'이력' 같은 낱말이 없어 서버가 아예 안
    불린다 → 프롬프트에서 MCP 칸이 통째로 빠진다 → 서윤은 **방금 자기가
    읽은 내용을 못 보는 채로** 답해야 한다.
    """

    def setUp(self):
        _Fake.setUp(self)
        DATA["items"] = REAL["items"]
        DATA["meta"] = dict(META, tags=["ALL"], total=5)
        self.addCleanup(lambda: DATA.update(items=None, meta=None))
        self.hub = mcp_client.Hub([
            dict(s, cwd=util.BASE, command=sys.executable,
                 args=[os.path.join(util.BASE, "qa", "mcp_server.py")],
                 env={"QA_BASE": self.base})
            for s in config.MCP_SERVERS])
        self.addCleanup(self.hub.close)

    def _turn(self, q, hist):
        got, used = self.hub.gather(q, use_cache=False, history=hist)
        hist += [{"role": "user", "content": q},
                 {"role": "assistant", "content": "(대답)"}]
        return got, used

    def test_이어지는_질문에도_직전_조회를_들고_간다(self):
        hist = []
        first, used = self._turn("보류된 요청 뭐야", hist)
        self.assertTrue(used, "첫 질문에서 조회가 걸려야 한다")
        self.assertIn("AVGTOTALTIME1MIN", first)
        # 이어지는 질문 — 걸릴 낱말이 하나도 없다
        nxt, used2 = self._turn("그럼 그건 언제까지야?", hist)
        self.assertEqual(self.hub.matched("그럼 그건 언제까지야?"), [],
                         "이 질문은 원래 안 걸리는 질문이어야 시험이 된다")
        self.assertEqual(used2, 0, "이어받기는 도구를 다시 부르면 안 된다")
        self.assertIn("AVGTOTALTIME1MIN", nxt, "직전 조회를 잊었다")

    def test_이어받은_것은_이어받았다고_밝힌다(self):
        """★방금 조회한 것처럼 말하면 안 된다."""
        hist = []
        self._turn("보류된 요청 뭐야", hist)
        nxt, _ = self._turn("그건 언제야?", hist)
        self.assertIn("조금 전에 조회해 둔", nxt)

    def test_대화가_길어지면_놓는다(self):
        """★무한정 들고 가면 요청이력 이야기가 끝난 뒤에도 프롬프트에 남는다."""
        hist = []
        self._turn("보류된 요청 뭐야", hist)
        for _ in range(self.hub.CARRY_TURNS):
            self._turn("그건 언제야?", hist)
        last, _ = self._turn("그건 언제야?", hist)
        self.assertEqual(last, "", "너무 오래 들고 간다")

    def test_다른_대화에는_안_샌다(self):
        """★첫 발화가 다르면 다른 대화다. 남의 조회 결과가 가면 안 된다."""
        hist = []
        self._turn("보류된 요청 뭐야", hist)
        other, _ = self.hub.gather("그건 언제야?", use_cache=False, history=[
            {"role": "user", "content": "완전히 다른 대화의 첫 질문"},
            {"role": "assistant", "content": "(대답)"}])
        self.assertEqual(other, "")

    def test_실패한_조회는_기억하지_않는다(self):
        """★"붙지 못했다" 를 들고 다니면, 서버가 살아난 뒤에도 계속
        "확인할 수 없다" 고 말한다."""
        hub = mcp_client.Hub([
            dict(s, cwd=util.BASE, command=sys.executable,
                 args=[os.path.join(util.BASE, "qa", "mcp_server.py")],
                 env={"QA_BASE": "http://127.0.0.1:1"})     # 죽은 주소
            for s in config.MCP_SERVERS])
        self.addCleanup(hub.close)
        hist = []
        bad, _ = hub.gather("보류된 요청 뭐야", use_cache=False, history=hist)
        self.assertTrue(bad, "실패해도 글은 넘어와야 한다")
        hist += [{"role": "user", "content": "보류된 요청 뭐야"},
                 {"role": "assistant", "content": "(대답)"}]
        self.assertEqual(hub.gather("그건 언제야?", use_cache=False,
                                    history=hist)[0], "",
                         "실패한 조회를 들고 다닌다")


class 필요할_때만_띄운다(_Fake):

    def _hub(self, **over):
        s = {"key": "qa", "name": "QA 요청이력",
             "when": ["요청", "개선"], "command": sys.executable,
             "args": [os.path.join(util.BASE, "qa", "mcp_server.py")],
             "cwd": util.BASE, "env": {"QA_BASE": self.base},
             "calls": [{"tool": "qa_meta", "label": "현황"}]}
        s.update(over)
        h = mcp_client.Hub([s])
        self.addCleanup(h.close)
        return h

    def test_안_걸리는_질문에는_프로세스를_안_띄운다(self):
        """★평소 대화마다 프로세스를 띄우면 그게 비용이다."""
        h = self._hub()
        self.assertEqual(h.matched("M16HUB 지금 몇 점이야?"), [])
        txt, n = h.gather("M16HUB 지금 몇 점이야?")
        self.assertEqual((txt, n), ("", 0))
        self.assertEqual(h._live, {}, "안 걸렸는데 띄웠다")

    def test_걸리는_질문에는_부른다(self):
        h = self._hub()
        txt, n = h.gather("M16HUB 개선요청 뭐 올라와 있어?")
        self.assertEqual(n, 1)
        self.assertIn("QA 요청이력", txt)
        self.assertIn("요청 2건", txt)

    def test_한_번_띄운_것을_다시_쓴다(self):
        h = self._hub()
        h.gather("요청 현황")
        p1 = h._live["qa"].proc.pid
        h.gather("요청 현황")
        self.assertEqual(h._live["qa"].proc.pid, p1, "매번 새로 띄운다")

    def test_죽으면_다시_띄운다(self):
        h = self._hub()
        h.gather("요청 현황")
        old = h._live["qa"]
        old.proc.kill()
        old.proc.wait(timeout=5)
        txt, n = h.gather("요청 현황")
        self.assertEqual(n, 1)
        self.assertIn("요청 2건", txt)

    def test_못_띄워도_대화는_이어진다(self):
        """★서버 하나 못 떠서 서윤이 입을 닫으면 안 된다."""
        h = self._hub(command="/없는/실행파일")
        txt, n = h.gather("요청 현황")
        self.assertEqual(n, 0)
        self.assertIn("붙지 못했다", txt)

    def test_꺼둔_서버는_아예_안_본다(self):
        h = mcp_client.Hub([{"key": "qa", "enabled": False,
                             "when": ["요청"], "command": sys.executable}])
        self.assertEqual(h.matched("요청 현황"), [])

    def test_인자를_질문에서_뽑는다(self):
        h = self._hub(calls=[
            {"tool": "qa_item", "label": "지목",
             "pick": {"seq": {"kind": "regex", "re": r"(?:No\.?|#)\s*(\d+)",
                              "int": True}}}])
        txt, n = h.gather("#1 요청 내용 보여줘")
        self.assertEqual(n, 1)
        self.assertIn("3층 STK", txt)

    def test_인자를_못_뽑으면_그_도구는_건너뛴다(self):
        """★못 뽑았는데 부르면 엉뚱한 건을 답한다."""
        h = self._hub(calls=[
            {"tool": "qa_item",
             "pick": {"seq": {"kind": "regex", "re": r"#(\d+)", "int": True}}}])
        txt, n = h.gather("요청 좀 보여줘")      # 번호가 없다
        self.assertEqual(n, 0)
        self.assertEqual(txt, "")

    def test_같은_질문은_다시_조회하지_않는다(self):
        """★화면의 컨텍스트 계측이 **타이핑을 멈출 때마다** /api/ctx 를 부르고,
        보내면 대화가 또 부른다. 캐시가 없으면 한 문장에 도구가 여러 번 돈다."""
        h = self._hub()
        t1, n1 = h.gather("요청 현황")
        t2, n2 = h.gather("요청 현황")
        self.assertEqual(t1, t2)
        self.assertEqual(n1, 1)
        self.assertEqual(n2, 0, "같은 질문을 또 조회했다")

    def test_캐시를_끄면_다시_조회한다(self):
        h = self._hub()
        h.gather("요청 현황")
        self.assertEqual(h.gather("요청 현황", use_cache=False)[1], 1)

    def test_다른_질문은_따로_조회한다(self):
        h = self._hub()
        h.gather("요청 현황")
        self.assertEqual(h.gather("보류된 요청")[1], 1, "엉뚱한 캐시를 줬다")

    def test_캐시가_죽은_서버를_가리지_않는다(self):
        """★서버가 끝났는데 15초 동안 옛 답을 그대로 주면, 그 사이에
        '요청이력은 이렇다' 고 말한다 — 실은 아무것도 못 보고 있는데."""
        h = self._hub()
        h.gather("요청 현황")
        h._live["qa"].proc.kill()
        h._live["qa"].proc.wait(timeout=5)
        self.assertFalse(h._all_alive())
        self.assertEqual(h.gather("요청 현황")[1], 1, "죽었는데 캐시를 줬다")

    def test_시간이_지나면_다시_조회한다(self):
        h = self._hub()
        h.gather("요청 현황")
        h.CACHE_S = 0.0
        self.assertEqual(h.gather("요청 현황")[1], 1, "묵은 값을 계속 준다")

    def test_대상은_질문에_있는_FAB_으로(self):
        h = self._hub(calls=[
            {"tool": "qa_items", "label": "관련 요청",
             "pick": {"target": {"kind": "oneof",
                                 "values": ["M16HUB", "M14"]}}}])
        txt, n = h.gather("M16HUB 개선요청")
        self.assertEqual(n, 1)
        self.assertIn("M16HUB", txt)


# ═══ 6. 서윤 프롬프트에 실린다 ═══════════════════════════════════════════
class _빈자료:
    def context(self, *a, **k):
        return ""


class 서윤에게_전달된다(unittest.TestCase):

    ST = {"docBudget": 6000}
    MCP = "[QA 요청이력]\n· 현황\n총 2건 · 미결 2건"

    def _sys(self, **kw):
        kw.setdefault("mcp_text", self.MCP)
        m = llm.build_messages("서윤이다.", "M16HUB 개선요청 뭐 있어?", [],
                               _빈자료(), self.ST, **kw)
        return m[0]["content"]

    def test_실린다(self):
        s = self._sys()
        self.assertIn("[외부 도구 — MCP]", s)
        self.assertIn("총 2건", s)

    def test_없으면_칸도_안_생긴다(self):
        self.assertNotIn("[외부 도구", self._sys(mcp_text=""))

    def test_관제_근거_안에_섞이지_않는다(self):
        """★[관제 근거] 에는 '대답 첫머리에 데이터 시각을 말하라' 가 붙어 있다.
        요청이력을 거기 넣으면 "2026-08-26 04:20 데이터 기준으로 개선요청이…"
        라고 시작한다 — 첨부에서 이미 겪은 사고와 같은 자리다."""
        s = self._sys(evidence_text="M16HUB 72점 위험")
        i_ev, i_mcp = s.index("[관제 근거"), s.index("[외부 도구")
        self.assertLess(i_ev, i_mcp, "MCP 가 근거보다 앞에 있다")
        block = s[i_ev:i_mcp]
        self.assertIn("72점", block)
        self.assertNotIn("총 2건", block, "MCP 결과가 관제 근거 안에 들어갔다")

    def test_관제_실측이_아니라고_못_박는다(self):
        s = self._sys()
        tail = s[s.index("[외부 도구"):]
        self.assertIn("관제 실측이 아니라", tail)
        self.assertIn("데이터 시각을 앞세우지 마라", tail)

    def test_지어내지_말라고_적는다(self):
        self.assertIn("지어내지 않는다", self._sys()[self._sys().index("[외부 도구"):])

    def test_룰_코드는_소독해서_넣는다(self):
        """★근거·스킬은 소독하는데 여기만 빠지면 'R-D' 가 새어 나간다."""
        s = self._sys(mcp_text="R-D 룰 관련 요청 1건")
        tail = s[s.index("[외부 도구"):]
        self.assertNotIn("R-D", tail, "룰 코드가 그대로 실렸다")


class 관제가_죽었을_때_요청이력으로_답하지_않는다(unittest.TestCase):
    """★"젠장 서버가 끊겼다 — 요청이 올라와 있어요 라고 답하네" (실제 지적).

    관제가 끊기면 [관제 근거] 는 "못 받았다" 인데, [외부 도구] 칸에는
    "총 5건" 같은 **구체적인 숫자**가 있다. 모델은 눈에 보이는 숫자를 집어
    상태 질문에 요청이력으로 답해 버린다. 그러면 관제가 끊긴 걸 물었는데
    엉뚱한 걸 답하는 셈이다.
    """

    ST = {"docBudget": 6000}
    DOWN = ("관제 서버에서 데이터를 못 받았다 (연결 거부). 수치는 알 수 없다 — "
            "반드시 '데이터를 못 본다' 고 말하고, 숫자를 지어내지 마라.")
    MCP = "[QA 요청이력]\n· 현황\n총 5건 · 미결 5건"

    def _tail(self, **kw):
        kw.setdefault("mcp_text", self.MCP)
        s = llm.build_messages("서윤이다.", "지금 상태 어때?", [], _빈자료(),
                               self.ST, **kw)[0]["content"]
        return s[s.index("[외부 도구"):]

    def test_끊겼으면_그렇게_못_박는다(self):
        t = self._tail(evidence_text=self.DOWN, evidence_down=True)
        self.assertIn("관제 데이터를 못 받은 상태", t)
        self.assertIn("답이 **될 수 없다**", t)

    def test_먼저_못_본다고_말하라고_시킨다(self):
        t = self._tail(evidence_text=self.DOWN, evidence_down=True)
        self.assertIn("먼저 '관제 데이터를 못 보고 있다' 고", t)

    def test_멀쩡할_때는_그_경고를_안_붙인다(self):
        """★평소에도 붙이면 관제가 살아 있는데 '못 본다' 고 말하게 된다."""
        t = self._tail(evidence_text="M16HUB 72점 위험")
        self.assertNotIn("관제 데이터를 못 받은 상태", t)

    def test_요청_건수와_알람_건수를_안_섞게_한다(self):
        """★'5건' 을 알람 5건으로 읽으면 그것도 거짓말이다."""
        t = self._tail(evidence_text="M16HUB 72점 위험")
        self.assertIn("요청 접수 건수", t)
        self.assertIn("FAB 점수·알람 건수와", t)

    def test_서버가_끊김을_실제로_넘긴다(self):
        """★llm 에 인자만 만들어 두고 server 가 안 넘기면 아무 소용이 없다."""
        p = os.path.join(util.BASE, "avatar_2d", "avatar", "server.py")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("evidence_down=down", src, "대화 경로가 안 넘긴다")
        i = src.index("down = ")
        self.assertIn("not ev.get(\"ok\")", src[i:i + 120])


class 현황_글이_헷갈리지_않는다(_Fake):
    """★서윤이 실제로 이렇게 답했다 (존 포레스트 지적):

        "현재 조회 현황은 0건이며, 총 4건이 완료된 기록만 남아 있어요"

    실제 자료는 총 5건 · 보류 1건 · 적용완료 4건이다. 우리가 준 글이
        총 5건 · 미결 5건 · 고객확인 완료 0건
        상태별: 보류 1건 · 적용완료 4건
    였다 — '완료' 가 두 뜻으로 들어 있고, '미결 5건' 과 '적용완료 4건' 이
    모순돼 보인다. 총 5건도 보류 1건도 통째로 사라졌다. 가장 중요한 게.
    """

    def setUp(self):
        _Fake.setUp(self)
        DATA["meta"] = dict(META, total=5, confirmed=0, open=5,
                            tags=["ALL"], people=["김윤환TL님"],
                            counts={"보류": 1, "적용완료": 4})
        self.addCleanup(lambda: DATA.update(meta=None))

    def test_총_건수를_먼저_말한다(self):
        t = SRV.t_meta({})
        self.assertTrue(t.startswith("요청 5건"), t.splitlines()[0])

    def test_안_끝난_것이_안_사라진다(self):
        self.assertIn("보류 1건", SRV.t_meta({}))

    def test_완료가_두_뜻으로_안_쓰인다(self):
        """★'고객확인 완료' 와 '적용완료' 가 한 줄에 있으면 섞어 읽는다."""
        for line in SRV.t_meta({}).splitlines():
            if "완료" in line and "적용완료" in line:
                self.assertNotIn("고객", line, "한 줄에 두 '완료' 가 있다")

    def test_미결이라는_말을_안_쓴다(self):
        """★'미결 5건' 과 '적용완료 4건' 은 서로 모순돼 보인다 —
        앞은 고객확인 얘기고 뒤는 진행상태 얘기인데."""
        self.assertNotIn("미결", SRV.t_meta({}))

    def test_고객확인은_분모까지_적는다(self):
        self.assertIn("5건 중 0건", SRV.t_meta({}))

    def test_많은_상태부터_적는다(self):
        t = SRV.t_meta({})
        i = t.index("진행 상태")
        self.assertLess(t.index("적용완료", i), t.index("보류", i))


class 관제_끊김을_요청조회_실패로_말하지_않는다(unittest.TestCase):
    """★서윤이 이렇게 답했다 (존 포레스트 지적):

        "최근 요청은 서버가 끊기면서 실패했기 때문에, 잠시 후에 다시
         시도해 주시면 좋을 것 같아요"

    요청조회는 **멀쩡히 성공**했다. 끊긴 건 관제다. 둘은 다른 서버인데
    서윤이 붙여 말했다.
    """

    ST = {"docBudget": 6000}
    MCP = "[QA 요청이력]\n· 현황\n요청 5건 (등록된 전부)"

    def _tail(self, mcp=None, down=True):
        s = llm.build_messages("서윤이다.", "qa 요청 상황 확인해봐", [], _빈자료(),
                               self.ST, evidence_text="관제 데이터를 못 받았다.",
                               mcp_text=mcp if mcp is not None else self.MCP,
                               evidence_down=down)[0]["content"]
        return s[s.index("[외부 도구"):]

    def test_성공했으면_성공했다고_못_박는다(self):
        t = self._tail()
        self.assertIn("이 조회는 **성공했다**", t)
        self.assertIn("다른 서버", t)

    def test_다시_시도하라고_말하지_말라고_한다(self):
        self.assertIn("나중에 다시 시도하라고 말하지", self._tail())

    def test_진짜_실패했으면_그_줄을_안_붙인다(self):
        """★실패했는데 '성공했다' 고 적으면 그게 더 큰 거짓말이다."""
        t = self._tail(mcp="[요청이력] 조회에 실패했다 — 요청관리 서버에 못 붙었다.")
        self.assertNotIn("이 조회는 **성공했다**", t)

    def test_총_건수와_안_끝난_것을_말하라고_시킨다(self):
        """★"총 4건이 완료된 기록만" — 총 5건도 보류 1건도 빠뜨렸다."""
        t = self._tail()
        self.assertIn("숫자를 빠뜨리지 마라", t)
        self.assertIn("아직 안 끝난 것", t)


class 목록이_한_줄로_안_나온다(unittest.TestCase):
    """★"글자 /n 처리 좀 해라... 한 줄로 쭉 나오면 우짜노" — 실제 지적.

    말풍선 CSS 는 이미 white-space:pre-wrap 이라 \\n 만 오면 줄이 갈라진다.
    문제는 모델이 안 넣는 것. 규칙으로 시켜도 붙여 쓴다 — 그래서 **결정적
    규칙으로 서버가 나눈다** (LLM 을 다시 부르지 않는다).
    """

    ONE = ("요청 5건이에요. #5 [적용완료] 제안 · 이준력 — 스킬.FAB 알람 구축 "
           "#4 [적용완료] 요청 · 윤재철TL님 — 스코어 산점 제작 "
           "#3 [보류] 요청 · 김윤환 — 지표 사용한 이유")

    def test_번호_목록을_줄로_가른다(self):
        r = llm.reflow_list(self.ONE)
        self.assertEqual(r.count("\n"), 3, r)
        self.assertTrue(r.splitlines()[1].startswith("#5"))

    def test_빈_줄이_안_생긴다(self):
        """★\\s* 로 쓰면 길이 0 매치가 겹쳐 \\n\\n 이 된다."""
        self.assertNotIn("\n\n", llm.reflow_list(self.ONE))

    def test_점_목록도_가른다(self):
        r = llm.reflow_list(
            "현황을 정리해 드릴게요. - 적용완료 4건입니다 - 보류 1건이에요 "
            "- 고객확인은 5건 중 0건입니다 - 대상은 전부 ALL 이고요")
        self.assertEqual(r.count("\n"), 4, r)

    def test_이미_나뉜_것은_안_건드린다(self):
        t = "가\n#1 [대기] 하나\n#2 [보류] 둘"
        self.assertEqual(llm.reflow_list(t), t)

    def test_짧은_줄은_안_건드린다(self):
        """★멀쩡한 문장을 쪼개면 그게 더 나쁘다. 짧은 잡담에도 '- ' 나
        '#3 [' 이 섞일 수 있는데, 그때 쪼개면 말이 토막 난다."""
        for t in ("#1 [대기] 하나뿐이에요",
                  "네 - 맞아요 - 그렇습니다",
                  "#1 [대기] 이거랑 #2 [보류] 저거요"):
            self.assertEqual(llm.reflow_list(t), t, t)

    def test_항목이_하나면_안_가른다(self):
        """★한 개짜리는 목록이 아니다. 가르면 문장 중간이 끊긴다."""
        for t in ("아주 긴 문장인데요 #3 [보류] 요청 하나만 있고 나머지는 그냥 "
                  "말이 계속 이어지는 문장입니다 네네 길이를 충분히 넘겨서 "
                  "길이 안전장치에 먼저 걸리지 않게 만듭니다",
                  "이번 건은 길게 설명드릴게요 - 그러니까 이런 사정이 있었고 "
                  "저런 경위로 이렇게 되었다는 이야기입니다 네 이 문장도 "
                  "충분히 길게 늘여서 길이 조건을 넘겨 둡니다"):
            self.assertGreater(len(t), 60, "시험 글이 짧아 길이 안전장치에 걸린다")
            self.assertEqual(llm.reflow_list(t), t, t)

    def test_날짜의_붙임표는_안_건드린다(self):
        """★'2026-08-26' 을 목록으로 보면 날짜가 쪼개진다."""
        t = ("적용일은 2026-08-26 이고 요청일은 2026-08-24 입니다 "
             "아주 긴 문장을 만들어 길이를 넘겨 봅니다")
        self.assertEqual(llm.reflow_list(t), t)

    def test_빈_글도_안_터진다(self):
        self.assertEqual(llm.reflow_list(""), "")
        self.assertEqual(llm.reflow_list(None), "")

    def test_실제_응답_경로에서_돈다(self):
        """★함수만 만들어 두고 finalize 가 안 부르면 소용이 없다."""
        out = llm.finalize(json.dumps(
            {"emotion": "neutral", "intensity": 0.5, "motion": "none",
             "text": self.ONE}, ensure_ascii=False))
        self.assertIn("\n", out["text"], "실제 답에 줄바꿈이 없다")

    def test_프롬프트에도_시킨다(self):
        s = llm.build_messages("서윤이다.", "요청 뭐 있어?", [], _빈자료(),
                               {"docBudget": 6000},
                               mcp_text="[QA 요청이력]\n· 현황\n요청 5건")[0]["content"]
        t = s[s.index("[외부 도구"):]
        self.assertIn("한 건에 한 줄", t)


class 컨텍스트_계측에_칸이_있다(unittest.TestCase):
    """★칸이 없으면 실려 있는데도 화면에서는 '없는 것' 으로 보인다 —
    참고자료 MD 때 똑같이 겪었다."""

    def test_CTX_KEYS_에_있다(self):
        self.assertIn("mcp", llm.CTX_KEYS)

    def test_순서가_프롬프트와_같다(self):
        k = list(llm.CTX_KEYS)
        self.assertLess(k.index("evidence"), k.index("mcp"))
        self.assertLess(k.index("mcp"), k.index("skills"))

    def test_잰_값이_0_이_아니다(self):
        seg = llm.measure("서윤이다.", "개선요청 뭐 있어?", [], _빈자료(),
                          {"docBudget": 6000}, mcp_text="[QA]\n총 2건")
        self.assertGreater(seg["mcp"], 0, "MCP 를 안 세고 있다")
        self.assertEqual(seg["total"], sum(seg[k] for k in llm.CTX_KEYS))

    def test_안_넣으면_0(self):
        seg = llm.measure("서윤이다.", "안녕", [], _빈자료(), {"docBudget": 6000})
        self.assertEqual(seg["mcp"], 0)

    def test_화면_칸_목록에도_있다(self):
        with open(os.path.join(util.BASE, "avatar_2d", "static", "app.js"),
                  encoding="utf-8") as f:
            js = f.read()
        i = js.index("const KEYS_ALL")
        blk = js[i:i + 700]
        self.assertIn("'mcp'", blk, "화면 칸 목록에 없다 — 합계에서 빠져 보인다")
        self.assertIn("mcp:", blk, "색·이름이 없다")


# ═══ 6-2. 실제로 등록된 데이터 모양 ══════════════════════════════════════
REAL = {"items": [
    {"id": i, "seq": i, "status": st, "category": cat, "requester": who,
     "target": "ALL", "tags": ["ALL"], "request_date": d, "content": c,
     "confirmed_at": None, "applied_date": None,
     "responses": [], "attachments": []}
    for i, (st, cat, who, d, c) in enumerate([
        ("적용완료", "요청", "김윤환TL님", "2026-08-24",
         "M16HUB.STRATE.ALL.FABSTORAGERATIO 만 사용"),
        ("적용완료", "요청", "김윤환TL님", "2026-08-24", "R-A룰에서 M16_PKT 제외하기"),
        ("보류", "요청", "김윤환", "2026-08-24",
         "AVGTOTALTIME10MIN 말고 AVGTOTALTIME1MIN 사용한 이유"),
        ("적용완료", "요청", "윤재철TL님/김윤환TL님", "2026-08-25",
         "FAB별_위험도_스코어_산점 제작"),
        ("적용완료", "제안", "이준력", "2026-08-25", "스킬.FAB 알람 시스템 구축"),
    ], 1)]}


class 실제_등록_데이터로_찾는다(_Fake):
    """★현장에 등록된 5건은 **대상이 전부 ALL** 이다. 목록을 FAB 이름으로만
    좁히게 해 놨더니 목록이 **한 번도 안 나왔다** — "총 5건" 만 말하고
    그 5건이 뭔지는 못 말했다. 그 사고를 여기서 못 박는다."""

    def setUp(self):
        _Fake.setUp(self)
        DATA["items"] = REAL["items"]
        DATA["meta"] = dict(META, tags=["ALL"], total=5,
                            counts={"보류": 1, "적용완료": 4},
                            people=["김윤환", "김윤환TL님",
                                    "윤재철TL님/김윤환TL님", "이준력"])
        self.addCleanup(lambda: DATA.update(items=None, meta=None))
        self.hub = mcp_client.Hub([
            dict(s, cwd=util.BASE, command=sys.executable,
                 args=[os.path.join(util.BASE, "qa", "mcp_server.py")],
                 env={"QA_BASE": self.base})
            for s in config.MCP_SERVERS])
        self.addCleanup(self.hub.close)

    def rows(self, q):
        """조회 결과를 **건 단위 덩어리**로 자른다.

        ★줄 단위(startswith('#'))로 세면 안 된다. 좁혀지면 서버가 내용·응답
          까지 펴서 여러 줄로 주는데, 그러면 머리글 줄에는 번호·상태·사람만
          있고 정작 찾는 내용은 다음 줄에 있다. 한 건이 몇 줄이든 한 덩어리로
          봐야 '몇 건인가' 와 '거기 그 말이 있나' 를 같이 볼 수 있다.
        """
        txt, _ = self.hub.gather(q)
        out = []
        for ln in txt.split("\n"):
            if ln.startswith("#"):
                out.append(ln)
            elif out:
                out[-1] += "\n" + ln
        return out

    def test_대상이_전부_ALL_이어도_목록이_나온다(self):
        r = self.rows("요청 뭐 올라와 있어?")
        self.assertEqual(len(r), 5, "목록이 안 나온다 — 건수만 말하게 된다")

    def test_상태로_좁힌다(self):
        r = self.rows("보류된 요청 뭐야")
        self.assertEqual(len(r), 1)
        self.assertIn("AVGTOTALTIME1MIN", r[0])

    def test_사람으로_좁힌다(self):
        r = self.rows("김윤환TL님이 올린 요청")
        self.assertEqual(len(r), 3)

    def test_컬럼_이름만_말해도_찾는다(self):
        """★"AVGTOTALTIME1MIN 왜 썼어?" — 답이 보류 건에 그대로 있는데
        '요청' 이라는 낱말이 없다고 안 걸려서 못 찾아 줬다."""
        r = self.rows("AVGTOTALTIME1MIN 왜 썼어?")
        self.assertEqual(len(r), 1)
        self.assertIn("보류", r[0])

    def test_룰_이름_뒤에_한글이_붙어도_찾는다(self):
        r = self.rows("R-A룰 왜 바꿨어")
        self.assertEqual(len(r), 1)
        self.assertIn("M16_PKT", r[0])

    def test_한글_밑줄_이름도_찾는다(self):
        r = self.rows("FAB별_위험도_스코어 그거 누가 요청했어")
        self.assertTrue(r, "한글에 밑줄이 섞인 이름을 못 찾는다")
        self.assertIn("윤재철", r[0])

    def test_관제_질문에는_여전히_안_뜬다(self):
        """★코드로 걸리게 했다고 FAB 이름까지 코드로 보면, 관제 대화마다
        요청이력을 뒤진다."""
        for q in ("M16HUB 지금 몇 점이야?", "M14 반송시간 알려줘",
                  "ALL 점수 얼마야", "지금 상태 어때", "M16B 어때"):
            self.assertEqual(self.hub.matched(q), [], q)


class 질문에서_인자를_뽑는다(unittest.TestCase):
    """_arg_of 만 따로 — 목록·상세가 엉뚱한 것을 찾는 원인은 대개 여기다."""

    def test_긴_이름을_먼저_본다(self):
        """★["M14","M14B"] 순서면 "M14B 요청" 에서 M14 가 먼저 걸려
        엉뚱한 FAB 을 찾는다. 설정 순서에 기대면 안 된다."""
        spec = {"kind": "oneof", "values": ["M14", "M14B", "M16A", "M16HUB"]}
        self.assertEqual(mcp_client._arg_of("M14B 요청 뭐 있어", spec), "M14B")
        self.assertEqual(mcp_client._arg_of("M16HUB 요청", spec), "M16HUB")
        self.assertEqual(mcp_client._arg_of("M14 요청", spec), "M14")

    def test_없으면_None(self):
        spec = {"kind": "oneof", "values": ["M14"]}
        self.assertIsNone(mcp_client._arg_of("요청 현황", spec))

    def test_any_는_앞에서부터_시도한다(self):
        spec = {"kind": "any", "of": [
            {"kind": "regex", "re": r"(R-[A-Z])(?![A-Z])"},
            {"kind": "regex", "re": r"([가-힣]{2,4})님"}]}
        self.assertEqual(mcp_client._arg_of("R-A룰 김윤환님", spec), "R-A")
        self.assertEqual(mcp_client._arg_of("김윤환님 요청", spec), "김윤환")
        self.assertIsNone(mcp_client._arg_of("요청 현황", spec))

    def test_숫자로_바꿔_준다(self):
        spec = {"kind": "regex", "re": r"#(\d+)", "int": True}
        self.assertEqual(mcp_client._arg_of("#12 요청", spec), 12)


# ═══ 7. 설정 ═════════════════════════════════════════════════════════════
class 설정이_말이_된다(unittest.TestCase):

    def test_서버_정의에_필요한_것이_다_있다(self):
        for s in config.MCP_SERVERS:
            self.assertTrue(s.get("key"))
            self.assertTrue(s.get("when"), s["key"] + ": 걸릴 말이 없다")
            self.assertTrue(s.get("calls"), s["key"] + ": 부를 도구가 없다")
            for c in s["calls"]:
                self.assertTrue(c.get("tool"))

    def test_부르는_도구가_실제로_있다(self):
        """★설정에 오타가 나면 조용히 아무것도 안 나온다."""
        have = {t["name"] for t in SRV.TOOLS}
        for c in config.MCP_SERVERS[0]["calls"]:
            self.assertIn(c["tool"], have)

    def test_관제_질문에는_안_걸린다(self):
        """★평소 관제 대화마다 MCP 가 뜨면 그게 비용이다."""
        h = mcp_client.Hub(config.MCP_SERVERS)
        for q in ("M16HUB 지금 몇 점이야?", "어제 8시에 어땠어?",
                  "M14 반송시간 알려줘"):
            self.assertEqual(h.matched(q), [], q)

    def test_요청_질문에는_걸린다(self):
        h = mcp_client.Hub(config.MCP_SERVERS)
        for q in ("M16HUB 개선요청 뭐 올라와 있어?", "이슈 접수된 거 있나",
                  "보류된 요청 알려줘"):
            self.assertTrue(h.matched(q), q)


class 끊긴_파이프에_안_터진다(_Fake):
    """★서윤 콘솔에 이게 찍혔다 (존 포레스트 로그):

        ↳ MCP 도구 2회 · 174자
        ↳ MCP 실패: [Errno 22] Invalid argument

    윈도우에서 **닫힌 파이프**에 쓰면 나는 오류다. 원인은 경합이었다 —
    화면의 컨텍스트 계측(/api/ctx)과 대화(/api/chat)가 동시에 같은 MCP
    프로세스를 쓰는데, 한쪽이 "죽었네" 하고 닫는 순간 다른 쪽이 쓴다.
    """

    def _hub(self):
        h = mcp_client.Hub([
            dict(s, cwd=util.BASE, command=sys.executable,
                 args=[os.path.join(util.BASE, "qa", "mcp_server.py")],
                 env={"QA_BASE": self.base})
            for s in config.MCP_SERVERS])
        self.addCleanup(h.close)
        return h

    def test_예외가_새어_나가지_않는다(self):
        """★윈도우는 OSError, 리눅스는 ValueError — **같은 사고인데 이름이
        다르다**. 하나만 잡으면 다른 쪽에서 대화가 통째로 실패한다."""
        import threading
        h = self._hub()
        h.gather("요청 현황")
        leaked = []

        def hit(i):
            try:
                for _ in range(6):
                    h.gather("요청 현황 {}".format(i), use_cache=False)
            except Exception as e:            # noqa: BLE001
                leaked.append("{}: {}".format(type(e).__name__, e))

        def killer():
            for _ in range(5):
                time.sleep(0.03)
                c = h._live.get("qa")
                if c:
                    try:
                        c.close()
                    except Exception:          # noqa: BLE001
                        pass

        ths = [threading.Thread(target=hit, args=(i,)) for i in range(6)]
        ths.append(threading.Thread(target=killer))
        for t in ths:
            t.start()
        for t in ths:
            t.join(30)
        self.assertEqual(leaked, [], "예외가 새어 나갔다 — 대화가 통째로 실패한다")

    def test_끊겨도_다시_붙어_값을_준다(self):
        h = self._hub()
        h.gather("요청 현황")
        h._live["qa"].proc.kill()
        h._live["qa"].proc.wait(timeout=5)
        txt, n = h.gather("요청 현황", use_cache=False)
        self.assertIn("요청 2건", txt, "다시 안 붙었다")
        self.assertGreaterEqual(n, 1)

    def test_부르는_도중_끊기면_다시_붙어_받아_온다(self):
        """★_client() 가 죽은 걸 알고 새로 띄우는 것과는 **다른 경로**다.
        이미 손에 쥔 연결이 도중에 끊기는 경우 — 존 포레스트 로그가 그것이다
        ("도구 2회" 뒤에 실패). 재시도가 없으면 그 질문이 통째로 빈손이 된다."""
        h = self._hub()
        h.gather("요청 현황")
        c = h._live["qa"]
        c.proc.kill()
        c.proc.wait(timeout=5)
        txt, bad = h._call_retry(h.servers[0], c, "qa_meta", {})
        self.assertFalse(bad, "다시 안 붙었다: {}".format(txt))
        self.assertIn("요청 2건", txt)

    def test_한_서버는_한_번에_하나만_돈다(self):
        """★자물쇠가 없으면 두 스레드가 같은 파이프를 동시에 쓴다."""
        h = self._hub()
        lk = h._srv_lock("qa")
        self.assertIs(lk, h._srv_lock("qa"), "부를 때마다 새 자물쇠를 만든다")

    def test_끊김과_도구실패를_구분한다(self):
        """★도구가 실패한 것까지 '끊겼다' 로 보고 다시 띄우면 낭비다."""
        self.assertTrue(mcp_client._looks_dead("서버에 못 썼다 ([Errno 22])"))
        self.assertTrue(mcp_client._looks_dead("서버가 끊겼다 (tools/call)"))
        self.assertFalse(mcp_client._looks_dead("그런 도구가 없다: xx"))
        self.assertFalse(mcp_client._looks_dead("요청관리 서버에 못 붙었다"))


class 윈도우_인코딩에_안_죽는다(unittest.TestCase):
    """★자식이 한글을 stdout 으로 내보낸다. 윈도우 파이프의 기본 인코딩은
    지역 코드페이지라, 못 쓰는 글자가 하나라도 있으면 **자식이 죽는다**.
    그러면 부모는 죽은 파이프에 쓰다가 [Errno 22] 를 맞는다."""

    def test_UTF8_로_못_박는다(self):
        p = os.path.join(util.BASE, "qa", "mcp_server.py")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("def _force_utf8()", src)
        self.assertIn('encoding="utf-8"', src)
        i = src.index("def serve(")
        self.assertIn("_force_utf8()", src[i:i + 260], "serve 가 안 부른다")

    def test_좁은_인코딩에서도_한글이_온다(self):
        """진짜 자식을 띄워 확인한다 — 소스만 보면 못 잡는다."""
        import subprocess
        env = dict(os.environ, PYTHONIOENCODING="ascii",
                   QA_BASE="http://127.0.0.1:1")     # 붙을 필요 없다
        p = subprocess.Popen(
            [sys.executable, os.path.join(util.BASE, "qa", "mcp_server.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, env=env, cwd=util.BASE,
            text=True, encoding="utf-8", errors="replace", bufsize=1)
        self.addCleanup(p.kill)
        p.stdin.write(json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n")
        p.stdin.flush()
        line = p.stdout.readline()
        self.assertTrue(line, "자식이 죽었다 — 인코딩")
        self.assertIn("요청", line, "한글이 깨졌다")
        self.assertIsNone(p.poll(), "한 번 쓰고 죽었다")


class 왜_안_되는지_알려_준다(unittest.TestCase):
    """★"왜 안 되지??" 를 반복하게 만들면 안 된다. 원인은 늘 셋 중 하나다 —
    주소가 다르다 / 파일이 없다 / 서버가 안 떴다. 셋 다 말해 줘야 한다."""

    SRC = os.path.join(util.BASE, "avatar_2d", "avatar", "server.py")

    def _src(self):
        with open(self.SRC, encoding="utf-8") as f:
            return f.read()

    def test_켤_때_보는_주소를_찍는다(self):
        """★안 찍으면 127.0.0.1 을 보고 있는 줄 모른다.

        stdio(요청이력)는 env 의 QA_BASE, http(위키)는 url 이다.
        둘 다 찍혀야 한다 — 한쪽만 보면 나머지는 빈 칸으로 나온다.
        """
        s = self._src()
        self.assertIn('(s.get("env") or {}).get("QA_BASE")', s)
        self.assertIn('s.get("url")', s)
        self.assertIn("MCP: {} \u2192 {}", s)

    def test_바깥_환경변수가_이긴다(self):
        """★요청관리가 다른 PC 면 코드를 고치게 만들면 안 된다."""
        s = self._src()
        i = s.index("env = dict(s.get(\"env\") or {})")
        self.assertIn("os.environ.get(k)", s[i:i + 260])

    def test_run_py_에_qa_옵션이_있다(self):
        p = os.path.join(util.BASE, "avatar_2d", "run.py")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        self.assertIn('"--qa"', src)
        self.assertIn('os.environ["QA_BASE"]', src)

    def test_파일이_없으면_끄고_말해_준다(self):
        """★avatar_2d 를 real_time_amhs 밖에 풀면 qa/mcp_server.py 가 없다.
        그러면 물어볼 때마다 조용히 실패한다."""
        s = self._src()
        self.assertIn("MCP '{}' 끔 — 파일이 없습니다", s)
        self.assertIn('s["enabled"] = False', s)

    def test_걸렸는데_빈손이면_그렇게_말한다(self):
        """★조용히 빈 글을 넘기면 서윤이 아무 말도 안 한다 — 사용자는
        MCP 가 도는지조차 모른다."""
        s = self._src()
        self.assertIn("MCP 걸렸는데 결과 없음", s)
        i = s.index("hit = hub.matched(text)")
        self.assertIn("확인할 수 없다", s[i:i + 900])
        self.assertIn("지어내지 마라", s[i:i + 900])
        # ★어느 서버인지 이름을 박아야 한다. 무조건 "요청이력" 이라고 적으면,
        #   위키가 안 떠 있는데 서윤이 요청관리를 붙잡고 고치라고 말한다.
        self.assertIn('s2.get("name")', s[i:i + 900])
        self.assertNotIn("요청관리 서버에 못 붙었다", s)

    def test_서버에_붙는지_혼자_확인할_수_있다(self):
        """★전부 띄우지 않고도 주소가 맞는지 재 볼 수 있어야 한다."""
        p = os.path.join(util.BASE, "qa", "mcp_server.py")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("def selfcheck()", src)
        self.assertIn('"--check" in sys.argv', src)
        self.assertIn("보는 주소:", src)


class 모듈_이름이_안_가린다(unittest.TestCase):
    """★이 프로젝트에서 config 모듈이 함수 이름에 가려 관제 주소를 못 읽은
    적이 있다. avatar/mcp.py 로 지었으면 공식 SDK 의 `mcp` 와 헷갈린다."""

    def test_avatar_에_mcp_py_가_없다(self):
        d = os.path.join(util.BASE, "avatar_2d", "avatar")
        self.assertFalse(os.path.exists(os.path.join(d, "mcp.py")))

    def test_stdlib_밖을_안_쓴다(self):
        """★폐쇄망이다. 여기에 pip 패키지가 끼면 배포가 막힌다."""
        import ast
        std = set(sys.stdlib_module_names)
        for path in (os.path.join(util.BASE, "qa", "mcp_server.py"),
                     os.path.join(util.BASE, "avatar_2d", "avatar",
                                  "mcp_client.py")):
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
            out = set()
            for n in ast.walk(tree):
                if isinstance(n, ast.Import):
                    out |= {a.name.split(".")[0] for a in n.names}
                elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
                    out.add(n.module.split(".")[0])
            self.assertEqual(out - std, set(),
                             os.path.basename(path) + " 가 밖의 것을 쓴다")



# ═══ 6. 위키(LLM_WIKI_MCP) — streamable-http 로 붙는다 ════════════════════
# 요청이력은 우리가 짠 stdio 서버다. 위키는 **공식 SDK(FastMCP)** 로 짜여
# 있고 transport 가 streamable-http 다 — 자식 프로세스로 못 띄운다. 그래서
# 붙는 쪽(HttpClient)을 새로 만들었고, 여기서 그게 진짜로 도는지 본다.
#
# ★핵심 함정: 같은 주소가 두 가지로 답한다.
#     application/json   악수 응답
#     text/event-stream  도구 결과 (FastMCP 가 이렇게 준다)
#   JSON 만 읽으면 **붙기는 하는데 도구가 통째로 안 된다** — 화면에는
#   "MCP 연결됨" 이 뜨고 답만 비는, 제일 헷갈리는 실패다.

WIKI_PAGE = {
    "id": 12, "title": "반송 장치 종류와 역할", "domain": "버츄얼 아바타",
    "tags": "VHL,OHT,LFT,CNV,STK,STB,Sorter,MLUD",
    "summary": "FOUP이 거치는 반송 장치의 역할과 포트 규칙.",
    "author": "", "updatedAt": "2026-08-30",
    "bodyMd": ("## 핵심 용어 정의\n"
               "- **VHL**: FOUP을 레일로 이동하는 장치.\n"
               "- **LFT**: 리프터. ZT라고도 불림. 층간 반송을 담당.\n"
               "- **STK**: 스토커. FOUP 임시 저장.\n"
               "- **Sorter**: FOSB↔FOUP 변환. 대기Q가 많으면 반송량이 많다는 방증.\n"),
}
WIKI_SEARCH = {"query": "LFT가 뭐야", "retrieval": "BM25", "results": [
    {"score": 8.21, "kind": "page", "id": 12, "title": "반송 장치 종류와 역할",
     "domain": "버츄얼 아바타", "summary": "FOUP이 거치는 반송 장치…",
     "snippet": "- **LFT**: 리프터. ZT라고도 불림. 층간 반송을 담당."},
    {"score": 3.10, "kind": "source", "id": 4, "title": "연결도.png",
     "domain": "버츄얼 아바타", "summary": "", "snippet": "M14↔M16 연결도"},
    {"score": 2.02, "kind": "page", "id": 15, "title": "FAB 간 연결 경로",
     "domain": "버츄얼 아바타", "summary": "", "snippet": "6ABL60~ 경유"},
]}


class 가짜_위키_MCP(BaseHTTPRequestHandler):
    """FastMCP 흉내 — 악수는 JSON, 도구 결과는 SSE 로 준다."""

    sse = True              # 시험에서 껐다 켰다 한다
    seen = []               # 받은 헤더를 들여다본다

    def log_message(self, *a):
        pass

    def _send(self, code, ctype, body, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        req = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
        type(self).seen.append(dict(self.headers))
        if "id" not in req:                       # 알림
            self._send(202, "text/plain", b"")
            return
        m, mid = req.get("method"), req["id"]
        if m == "initialize":
            body = json.dumps({"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                "serverInfo": {"name": "llm-wiki", "version": "1.0"}}})
            self._send(200, "application/json", body.encode("utf-8"),
                       {"mcp-session-id": "sess-42"})
            return
        if m == "tools/list":
            res = {"tools": [{"name": n2} for n2 in
                             ("listDomains", "searchWiki", "readPage",
                              "listSources", "readSource")]}
        elif m == "tools/call":
            name = (req.get("params") or {}).get("name")
            args = (req.get("params") or {}).get("arguments") or {}
            if name == "searchWiki":
                data = WIKI_SEARCH
            elif name == "readPage":
                data = WIKI_PAGE if args.get("pageId") == 12 else \
                    {"isError": True, "message": "page 없음"}
            elif name == "listDomains":
                data = {"domains": [{"slug": "virtual-avatar",
                                     "name": "버츄얼 아바타", "pageCount": 4}]}
            else:
                res = {"content": [{"type": "text", "text": "없는 도구"}],
                       "isError": True}
                self._reply(mid, res)
                return
            res = {"content": [{"type": "text",
                                "text": json.dumps(data, ensure_ascii=False)}],
                   "structuredContent": data}
        else:
            body = json.dumps({"jsonrpc": "2.0", "id": mid,
                               "error": {"code": -32601,
                                         "message": "모르는 method"}})
            self._send(200, "application/json", body.encode("utf-8"))
            return
        self._reply(mid, res)

    def _reply(self, mid, result):
        msg = json.dumps({"jsonrpc": "2.0", "id": mid, "result": result},
                         ensure_ascii=False)
        if type(self).sse:
            body = ("event: message\ndata: {}\n\n".format(msg)).encode("utf-8")
            self._send(200, "text/event-stream", body)
        else:
            self._send(200, "application/json", msg.encode("utf-8"))


class _Wiki(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = HTTPServer(("127.0.0.1", 0), 가짜_위키_MCP)
        cls.url = "http://127.0.0.1:{}/mcp".format(cls.httpd.server_address[1])
        cls.th = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.th.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        가짜_위키_MCP.sse = True
        가짜_위키_MCP.seen = []


class 위키에_붙는다(_Wiki):

    def test_악수하고_도구를_받는다(self):
        c = mcp_client.HttpClient(self.url)
        self.assertEqual(c.server.get("name"), "llm-wiki")
        self.assertIn("searchWiki", [t["name"] for t in c.tools()])
        self.assertTrue(c.alive())

    def test_도구_결과가_SSE_로_와도_읽는다(self):
        """★FastMCP 는 도구 결과를 event-stream 으로 준다.

        JSON 만 읽으면 악수는 되고 도구만 안 된다 — 화면에는 '연결됨' 이
        뜨는데 답이 비는, 제일 헷갈리는 실패다.
        """
        c = mcp_client.HttpClient(self.url)
        txt, bad = c.call("searchWiki", {"query": "LFT가 뭐야"})
        self.assertFalse(bad)
        self.assertEqual(json.loads(txt)["results"][0]["id"], 12)

    def test_JSON_으로_와도_읽는다(self):
        """서버가 SSE 를 안 쓸 수도 있다. 둘 다 받아야 한다."""
        가짜_위키_MCP.sse = False
        c = mcp_client.HttpClient(self.url)
        txt, bad = c.call("readPage", {"pageId": 12})
        self.assertFalse(bad)
        self.assertIn("리프터", txt)

    def test_세션을_돌려준다(self):
        """★악수에서 받은 mcp-session-id 를 다음 요청에 실어야 한다.
        안 실으면 서버가 400/404 로 끊는다."""
        c = mcp_client.HttpClient(self.url)
        c.call("listDomains")
        self.assertEqual(c.session, "sess-42")
        self.assertEqual(가짜_위키_MCP.seen[-1].get("Mcp-Session-Id"), "sess-42")

    def test_두_가지를_다_받겠다고_말한다(self):
        """Accept 에 event-stream 이 빠지면 FastMCP 가 406 을 준다."""
        mcp_client.HttpClient(self.url)
        acc = 가짜_위키_MCP.seen[0].get("Accept") or ""
        self.assertIn("application/json", acc)
        self.assertIn("text/event-stream", acc)

    def test_웹앱_주소를_넣으면_그렇다고_말해_준다(self):
        """★실제 증상. 위키 웹앱(:8100)을 MCP 주소로 넣으면 그쪽에 /mcp 가
        없어서 Flask 가 HTML 404 를 준다:

            못 붙었습니다 — 서버가 끊겼다 (HTTP 404 <!doctype html> …)

        이렇게만 말하면 서버는 멀쩡히 떠 있는데 왜 안 되는지 알 길이 없다.
        MCP 서버는 JSON 만 준다 — HTML 이 오면 그 주소가 아닌 것이다.
        """
        class 가짜_웹앱(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = (b"<!doctype html>\n<html lang=en>\n"
                        b"<title>404 Not Found</title>\n<h1>Not Found</h1>\n"
                        b"<p>The requested URL was not found on the server.</p>")
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        srv = HTTPServer(("127.0.0.1", 0), 가짜_웹앱)
        url = "http://127.0.0.1:{}/mcp".format(srv.server_address[1])
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        with self.assertRaises(mcp_client.McpError) as e:
            mcp_client.HttpClient(url, timeout=3)
        m = str(e.exception)
        self.assertIn("MCP 서버가 아닙니다", m)
        self.assertIn("app.py", m)          # 무엇과 헷갈렸는지
        self.assertIn("mcp_server.py", m)   # 무엇을 띄워야 하는지
        self.assertIn(url, m)               # 지금 어디를 보고 있는지

    def test_HTML_이_아니면_그_말은_안_한다(self):
        """★아무 404 에나 이 말을 붙이면, 진짜 세션 만료를 가린다."""
        c = mcp_client.HttpClient(self.url)
        self.assertEqual(c._hint(404, '{"error":"session"}'), "")
        self.assertEqual(c._hint(500, "boom"), "")
        self.assertIn("MCP 서버가 아닙니다", c._hint(404, "<HTML><body>x</body>"))

    def test_안_떠_있으면_끊겼다고_말한다(self):
        """★'끊겼다' 라고 말해야 위에서 새로 붙어 다시 건다 (_looks_dead)."""
        with socket.socket() as s:          # 아무도 안 듣는 포트
            s.bind(("127.0.0.1", 0))
            dead = "http://127.0.0.1:{}/mcp".format(s.getsockname()[1])
        with self.assertRaises(mcp_client.McpError) as e:
            mcp_client.HttpClient(dead, timeout=2)
        self.assertTrue(mcp_client._looks_dead(str(e.exception)),
                        "다시 붙을 신호로 안 읽힌다: {}".format(e.exception))

    def test_사내_주소라_프록시를_안_탄다(self):
        """★관제·월드모델에서 이미 밟았다 — 회사 프록시가 사내 IP 를 못 찾아
        407 을 준다. 환경변수에 프록시가 있어도 그대로 붙어야 한다.

        (핸들러 목록을 뒤지지 않고 **진짜로 붙여 본다**. 빈 ProxyHandler 는
         여는 메서드가 없어서 opener.handlers 에 안 들어간다 — 목록만 보면
         막은 것을 안 막았다고 읽는다.)
        """
        for k in ("http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"):
            old = os.environ.get(k)
            os.environ[k] = "http://127.0.0.1:9"      # 아무도 안 듣는다
            self.addCleanup(lambda k=k, v=old:
                            os.environ.__setitem__(k, v) if v is not None
                            else os.environ.pop(k, None))
        c = mcp_client.HttpClient(self.url, timeout=5)
        txt, bad = c.call("listDomains")
        self.assertFalse(bad)
        self.assertIn("버츄얼 아바타", txt)

    def test_transport_를_보고_갈라_붙는다(self):
        c = mcp_client._connect({"key": "w", "transport": "http",
                                 "url": self.url})
        self.assertIsInstance(c, mcp_client.HttpClient)
        self.assertEqual(c.where(), self.url)


class 검색하고_본문까지_읽는다(_Wiki):
    """★조각(500자)만 주면 앞머리만 아는 상태가 된다.

    요청이력에서 그대로 겪은 일이다 — "하기는 잘해.. 근데 상세한 내용을
    물어보면 몰라". 검색으로 어느 쪽인지 찾았으면 그 쪽 본문을 읽어야 한다.
    """

    def srv(self, **kw):
        s = {"key": "wiki", "name": "AMHS 위키", "transport": "http",
             "url": self.url, "when": ["LFT"],
             "calls": [{"tool": "searchWiki", "label": "위키 검색",
                        "args": {"topK": 4},
                        "pick": {"query": {"kind": "text"}},
                        "then": {"tool": "readPage", "label": "위키 본문",
                                 "arg": "pageId", "list": "results",
                                 "id": "id", "only": {"kind": "page"},
                                 "max": 2}}]}
        s.update(kw)
        return s

    def test_검색_뒤에_본문을_읽는다(self):
        h = mcp_client.Hub([self.srv()])
        self.addCleanup(h.close)
        got, used = h.gather("LFT가 뭐야?")
        self.assertIn("위키 검색", got)
        self.assertIn("위키 본문 #12", got)
        self.assertIn("리프터", got)          # 조각이 아니라 본문에만 있다
        self.assertEqual(used, 3)             # 검색 1 + 본문 2

    def test_페이지가_아닌_것은_안_읽는다(self):
        """★kind='source' 를 readPage 에 넣으면 없는 페이지를 친다."""
        ids = mcp_client.Hub._ids_of(
            {"list": "results", "id": "id", "only": {"kind": "page"}},
            json.dumps(WIKI_SEARCH, ensure_ascii=False))
        self.assertEqual(ids, [12, 15])

    def test_몇_개까지만_읽는다(self):
        h = mcp_client.Hub([self.srv(calls=[{
            "tool": "searchWiki", "pick": {"query": {"kind": "text"}},
            "then": {"tool": "readPage", "arg": "pageId", "list": "results",
                     "id": "id", "only": {"kind": "page"}, "max": 1}}])])
        self.addCleanup(h.close)
        _, used = h.gather("LFT가 뭐야?")
        self.assertEqual(used, 2)             # 검색 1 + 본문 1

    def test_JSON_이_아니면_그냥_넘어간다(self):
        """앞 도구가 사람 글을 주면 id 를 못 뽑는다 — 터지면 안 된다."""
        self.assertEqual(mcp_client.Hub._ids_of({}, "총 5건입니다"), [])
        self.assertEqual(mcp_client.Hub._ids_of({}, ""), [])

    def test_질문을_검색어로_쓴다(self):
        """★군말(뭐야·알려줘)은 뺀다 — 문서에 없는 말이라 점수만 흩뜨린다.
        영문·코드(LFT·ZT)는 짧아도 남긴다: 그게 제일 센 신호다."""
        spec = {"kind": "text", "max": 160}
        got = mcp_client._arg_of("  LFT랑  ZT  차이가 뭐야 ", spec)
        self.assertIn("LFT랑", got)
        self.assertIn("ZT", got)
        self.assertNotIn("뭐야", got)
        self.assertIsNone(mcp_client._arg_of("   ", spec))

    def test_긴_본문은_정한_몫까지만_싣는다(self):
        """★위키 본문은 길다. 통째로 넣으면 관제 근거·첨부가 밀려난다."""
        cut = mcp_client.Hub._fit({"budget": 40}, "가" * 200)
        self.assertLess(len(cut), 120)
        self.assertIn("잘렸다", cut)
        self.assertIn("전체 200자", cut)      # 얼마나 잘렸는지 말해 준다
        self.assertEqual(mcp_client.Hub._fit({}, "가" * 200), "가" * 200)


class 안_떠_있는_서버에_매달리지_않는다(unittest.TestCase):
    """★실제 증상: 아바타 화면에 "관제 연결 끊김 — TimeoutError" 가 떴다.

    화면의 컨텍스트 계측은 **타이핑을 멈출 때마다**(500ms) /api/ctx 를 부르고,
    그때마다 MCP 조회가 돈다. 위키가 안 떠 있으면 그 요청들이 전부 붙기를
    기다리며 쌓인다 — 스레드가 계속 늘고 아바타 프로세스가 무거워진다.
    관제 감시 스레드까지 느려지면 화면에는 엉뚱하게 관제가 끊겼다고 뜬다.

    stdio 서버는 이 문제가 약하다(로컬 프로세스라 실패가 빠르다). http 로
    붙는 서버를 넣으면서 생긴 자리다.
    """

    DEAD = "http://10.255.255.1:8020/mcp"      # 라우팅 안 됨 = 무응답

    def srv(self, **kw):
        s = {"key": "wiki", "name": "AMHS 위키", "transport": "http",
             "url": self.DEAD, "when": ["LFT"], "timeout": 20,
             "calls": [{"tool": "searchWiki",
                        "pick": {"query": {"kind": "text"}}}]}
        s.update(kw)
        return s

    def test_악수는_오래_안_기다린다(self):
        """★도구 호출은 오래 걸려도 되지만, **안 뜬 서버를 20초** 기다리는
        것은 그냥 손해다. 그 20초 동안 대화가 멎어 있다."""
        self.assertLessEqual(mcp_client.HttpClient.HANDSHAKE_S, 5.0)
        h = mcp_client.Hub([self.srv()])
        self.addCleanup(h.close)
        t0 = time.time()
        h.gather("LFT가 뭐야?", use_cache=False)
        self.assertLess(time.time() - t0, 8.0)

    def test_한_번_못_붙으면_잠깐_쉰다(self):
        """두 번째부터는 두들기지 않고 즉시 실패로 답한다."""
        h = mcp_client.Hub([self.srv()])
        self.addCleanup(h.close)
        h.gather("LFT가 뭐야?", use_cache=False)
        t0 = time.time()
        for _ in range(5):
            got, used = h.gather("LFT가 뭐야?", use_cache=False)
        self.assertLess(time.time() - t0, 1.0, "쉬지 않고 계속 두들긴다")
        self.assertIn("붙지 못했다", got)      # 실패는 여전히 말해 준다

    def test_쉬는_동안에도_실패를_말한다(self):
        """★조용히 빈 글을 주면 서윤이 '위키에 없다' 고 답해 버린다.
        못 본 것과 없는 것은 다르다."""
        h = mcp_client.Hub([self.srv()])
        self.addCleanup(h.close)
        h.gather("LFT가 뭐야?", use_cache=False)
        got, _ = h.gather("LFT가 뭐야?", use_cache=False)
        self.assertIn("AMHS 위키", got)
        self.assertIn("확인 못 한다", got)

    def test_쉬는_시간이_지나면_다시_붙어_본다(self):
        h = mcp_client.Hub([self.srv()])
        self.addCleanup(h.close)
        h.RETRY_S = 0.0
        h.gather("LFT가 뭐야?", use_cache=False)
        with h._lock:
            self.assertIn("wiki", h._down)     # 못 붙은 것은 기억한다
        t0 = time.time()
        h.gather("LFT가 뭐야?", use_cache=False)
        self.assertGreater(time.time() - t0, 0.3, "쉬는 시간이 지나도 안 붙어 본다")

    def test_죽은_서버가_다른_서버를_안_세운다(self):
        """★붙는 동안 전체 자물쇠를 쥐고 있으면, 안 떠 있는 서버 하나가
        멀쩡한 서버 조회까지 통째로 세운다."""
        import inspect
        src = inspect.getsource(mcp_client.Hub._client)
        i, j = src.index("_srv_lock"), src.index("_connect(s)")
        self.assertLess(i, j, "서버별 자물쇠 안에서 붙어야 한다")
        # 전체 자물쇠(_lock)를 쥔 채로 붙으면 안 된다
        head = src[:j]
        self.assertNotIn("with self._lock:\n            c = _connect", head)

    def test_화면에_저장한_주소가_이기는_것을_보여_준다(self):
        """★실제로 하루를 잡아먹은 자리.

        화면에서 한 번 넣은 주소는 data/settings.json 에 남아서 코드 기본값을
        이긴다. 그게 맞는 동작인데, **이기고 있다는 사실이 안 보였다.**
        기본값을 8100→8020 으로 되돌렸는데도 저장된 8100 이 남아 계속
        HTML 404 가 났다 — 코드를 아무리 고쳐도 안 바뀌니 원인을 못 찾는다.
        """
        p1 = os.path.join(util.BASE, "avatar_2d", "avatar", "server.py")
        with open(p1, encoding="utf-8") as f:
            src = f.read()
        i = src.index('if v.get("url") and s.get("url"):')
        self.assertIn('s["url_default"]', src[i:i + 700])
        # 되돌릴 길이 있어야 한다
        self.assertIn('elif op == "url_default":', src)
        j = src.index('elif op == "url_default":')
        self.assertIn('{"mcp": {key: {"url": ""}}}', src[j:j + 800])
        # 상태에 실어 보내고
        p2 = os.path.join(util.BASE, "avatar_2d", "avatar", "mcp_client.py")
        with open(p2, encoding="utf-8") as f:
            self.assertIn('"url_default"', f.read())
        # 화면에 띄우고 되돌리는 단추까지
        p3 = os.path.join(util.BASE, "avatar_2d", "static", "app.js")
        with open(p3, encoding="utf-8") as f:
            js = f.read()
        self.assertIn("s.url_default", js)
        self.assertIn("기본값으로", js)
        self.assertIn("'url_default', s.key", js)

    def test_빈_주소를_저장하면_기본값으로_돌아간다(self):
        """★지우는 길이 없으면 한 번 넣은 값이 영영 남는다."""
        import pathlib, shutil, tempfile
        from avatar.settings import Settings
        d = tempfile.mkdtemp(prefix="mcpurl")
        self.addCleanup(lambda: shutil.rmtree(d, True))
        st = Settings(pathlib.Path(d) / "settings.json")
        st.update({"mcp": {"wiki": {"url": "http://a:8100/mcp"}}})
        self.assertEqual(st.all()["mcp"]["wiki"]["url"], "http://a:8100/mcp")
        st.update({"mcp": {"wiki": {"url": ""}}})
        self.assertNotIn("url", st.all()["mcp"]["wiki"])

    def test_코드_안_고치고_끌_수_있다(self):
        """★안 떠 있는 서버 때문에 느려질 때, 바로 뗄 수 있어야 한다."""
        p1 = os.path.join(util.BASE, "avatar_2d", "avatar", "server.py")
        with open(p1, encoding="utf-8") as f:
            src = f.read()
        i = src.index('"{}_MCP_URL".format')
        self.assertIn('"off"', src[i:i + 400])
        self.assertIn('s["enabled"] = False', src[i:i + 400])
        p2 = os.path.join(util.BASE, "avatar_2d", "run.py")
        with open(p2, encoding="utf-8") as f:
            run = f.read()
        self.assertIn('"off"', run[run.index("args.wiki"):])

    def test_진단은_차단기를_무시한다(self):
        """★서버를 고쳐 놓고 눌렀는데 '쉬는 중' 이라고 답하면 못 고친다."""
        import inspect
        src = inspect.getsource(mcp_client.Hub.status)
        self.assertIn("_down.clear()", src)


class 화면에서_켜고_끈다(_Wiki):
    """★"MCP 안 되는 것 같은데" 를 콘솔 로그로만 짚을 수는 없다.

    안 떠 있는 서버는 켜 두면 물어볼 때마다 붙으러 갔다가 실패해서 답이
    느려진다 — 그래서 **끄는 것이 실제 조치**다. 화면에 그 자리가 있어야 한다.
    """

    def hub(self, **kw):
        s = {"key": "wiki", "name": "AMHS 위키", "transport": "http",
             "url": self.url, "when": ["LFT"], "probe": "listDomains",
             "calls": [{"tool": "searchWiki",
                        "pick": {"query": {"kind": "text"}}}]}
        s.update(kw)
        h = mcp_client.Hub([s])
        self.addCleanup(h.close)
        return h

    def test_꺼도_목록에_남는다(self):
        """★예전엔 꺼진 서버를 Hub 가 아예 안 들고 있었다 — 목록에 없으니
        화면에서 다시 켤 방법이 없었다."""
        h = self.hub(enabled=False)
        self.assertEqual([s["key"] for s in h.servers], ["wiki"])
        self.assertEqual(h.on(), [])
        self.assertEqual(h.matched("LFT가 뭐야?"), [])
        h.set_enabled("wiki", True)
        self.assertEqual([s["key"] for s in h.matched("LFT가 뭐야?")], ["wiki"])

    def test_끄면_조회를_안_한다(self):
        """★끄면 들고 다니던 직전 결과도 버린다.

        안 버리면, 껐는데도 서윤이 15분 동안 그 내용을 계속 말한다
        (이어지는 질문에 직전 조회를 들고 가는 장치가 있다). 틀려서 껐는데
        계속 나오면 끈 의미가 없다.
        """
        h = self.hub()
        got, used = h.gather("LFT가 뭐야?", use_cache=False)
        self.assertTrue(used)
        h.set_enabled("wiki", False)
        got, used = h.gather("LFT가 뭐야?", use_cache=False)
        self.assertEqual(used, 0)
        self.assertEqual(got, "", "껐는데 직전 결과를 계속 들고 다닌다")

    def test_끄면_붙어_있던_것을_놓는다(self):
        """★안 놓으면 프로세스·세션이 그대로 살아 있는데 화면은 꺼진 것으로
        보인다. stdio 서버면 자식 프로세스가 계속 떠 있는다."""
        h = self.hub()
        h.gather("LFT가 뭐야?", use_cache=False)
        self.assertIn("wiki", h._live)
        h.set_enabled("wiki", False)
        self.assertNotIn("wiki", h._live)

    def test_꺼진_서버는_두들기지_않는다(self):
        """★껐는데 화면을 열 때마다 붙으러 가면, 끈 이유가 그대로 남는다."""
        h = self.hub(enabled=False, url="http://10.255.255.1:8020/mcp",
                     off_reason="화면에서 껐습니다")
        t0 = time.time()
        st = h.status()
        self.assertLess(time.time() - t0, 1.0, "꺼진 서버를 두들긴다")
        self.assertFalse(st["servers"][0]["enabled"])
        self.assertIn("화면에서 껐습니다", st["servers"][0]["err"])
        self.assertEqual(st["on"], 0)

    def test_주소를_바꾸면_다시_붙는다(self):
        h = self.hub()
        h.gather("LFT가 뭐야?", use_cache=False)
        self.assertIn("wiki", h._live)
        h.set_url("wiki", "http://10.255.255.1:8020/mcp")
        self.assertNotIn("wiki", h._live)      # 옛 연결을 놓는다
        self.assertEqual(h.find("wiki")["url"], "http://10.255.255.1:8020/mcp")

    def test_주소에_mcp_를_빠뜨려도_붙여_준다(self):
        """★빠뜨리기 쉽다 — 그러면 조용히 404 다."""
        h = self.hub()
        h.set_url("wiki", "http://10.1.2.3:8020")
        self.assertEqual(h.find("wiki")["url"], "http://10.1.2.3:8020/mcp")
        h.set_url("wiki", "http://10.1.2.3:8020/mcp/")
        self.assertEqual(h.find("wiki")["url"], "http://10.1.2.3:8020/mcp")

    def test_다시_붙기가_차단기를_푼다(self):
        """★서버를 고쳐 놓고 눌렀는데 '30초 쉬는 중' 이면 못 고친다."""
        h = self.hub(url="http://10.255.255.1:8020/mcp")
        h.gather("LFT가 뭐야?", use_cache=False)
        with h._lock:
            self.assertIn("wiki", h._down)
        h.reconnect("wiki")
        with h._lock:
            self.assertNotIn("wiki", h._down)

    def test_상태에_켜짐과_붙음을_같이_준다(self):
        h = self.hub()
        st = h.status()
        r = st["servers"][0]
        self.assertTrue(r["enabled"])
        self.assertTrue(r["ok"])
        self.assertEqual(r["transport"], "http")
        self.assertIn("listDomains", r["tools"])
        self.assertEqual((st["on"], st["live"]), (1, 1))


class 화면_설정이_남는다(unittest.TestCase):
    """★재시작하면 되돌아가면, 느려서 껐던 사람이 그 일을 또 겪는다."""

    def store(self):
        import pathlib, tempfile
        from avatar.settings import Settings
        d = tempfile.mkdtemp(prefix="mcpset")
        self.addCleanup(lambda: __import__("shutil").rmtree(d, True))
        return Settings(pathlib.Path(d) / "settings.json"), pathlib.Path(d)

    def test_껐다는_사실이_파일에_남는다(self):
        st, d = self.store()
        st.update({"mcp": {"wiki": {"enabled": False}}})
        saved = json.loads((d / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["mcp"]["wiki"]["enabled"], False)

    def test_한_서버만_고쳐도_나머지가_안_날아간다(self):
        """★통째로 갈아끼우면, 화면이 한 줄만 보냈을 때 나머지가 사라진다."""
        st, _ = self.store()
        st.update({"mcp": {"wiki": {"enabled": False, "url": "http://a:8020/mcp"}}})
        st.update({"mcp": {"qa": {"enabled": True}}})
        m = st.all()["mcp"]
        self.assertEqual(m["wiki"]["enabled"], False)
        self.assertEqual(m["wiki"]["url"], "http://a:8020/mcp")
        self.assertEqual(m["qa"]["enabled"], True)

    def test_같은_서버의_다른_칸을_안_지운다(self):
        st, _ = self.store()
        st.update({"mcp": {"wiki": {"url": "http://a:8020/mcp"}}})
        st.update({"mcp": {"wiki": {"enabled": False}}})
        self.assertEqual(st.all()["mcp"]["wiki"]["url"], "http://a:8020/mcp")

    def test_이상한_값은_안_받는다(self):
        st, _ = self.store()
        st.update({"mcp": "전부 꺼"})
        st.update({"mcp": {"wiki": "꺼"}})
        self.assertEqual(st.all()["mcp"], {})

    def test_켤_때_화면_설정을_얹는다(self):
        """코드 기본값 → 환경변수 → **화면**. 순서가 이래야 한다."""
        p = os.path.join(util.BASE, "avatar_2d", "avatar", "server.py")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        i = src.index('saved = App.settings.get("mcp")')
        j = src.index('live = [s for s in srv if s.get("enabled", True)]')
        self.assertLess(i, j, "화면 설정을 얹기 전에 목록을 확정한다")
        # 환경변수 처리보다 **뒤에** 와야 한다 (화면이 이긴다)
        self.assertLess(src.index('"{}_MCP_URL".format'), i)


class 화면에_MCP_자리가_있다(unittest.TestCase):

    def _read(self, *parts):
        p = os.path.join(util.BASE, "avatar_2d", *parts)
        if not os.path.isfile(p):
            raise unittest.SkipTest("{} 가 없다".format(p))
        with open(p, encoding="utf-8") as f:
            return f.read()

    def test_설정_탭에_칸이_있다(self):
        h = self._read("static", "index.html")
        for i in ("mcpList", "mcpRefresh", "mcpReconnect", "mcpDot", "mcpMsg"):
            self.assertIn('id="{}"'.format(i), h, i)
        self.assertIn("외부 도구 (MCP)", h)

    def test_찾을_수_있는_자리에_있다(self):
        """★"어디서 해야 할지 몰라서" 라는 말이 나왔다.

        설정 탭 아홉 번째 칸에 있으면 아무도 못 찾는다. 연결끼리 붙여 둔다 —
        LLM 연결 **바로 다음**이다. 서랍의 칩에서도 바로 갈 수 있다.
        """
        h = self._read("static", "index.html")
        llm = h.index("LLM 연결")
        mcp = h.index("외부 도구 (MCP)")
        self.assertLess(llm, mcp)
        # 사이에 다른 칸이 끼면 안 된다
        between = h[llm:mcp]
        self.assertEqual(between.count("<h4>"), 0,
                         "LLM 연결과 외부 도구 사이에 다른 칸이 있다")
        self.assertIn('id="mcpChip"', h, "서랍 칩이 없다")
        j = self._read("static", "app.js")
        i = j.index("$('#mcpChip').onclick")
        self.assertIn("data-p=cfg", j[i:i + 500])
        self.assertIn("scrollIntoView", j[i:i + 500])
        self.assertIn("mcpLoad()", j[i:i + 500])

    def test_따로_띄워야_한다는_것을_적어_둔다(self):
        """★이걸 모르면 "왜 안 되지" 를 계속 반복한다."""
        h = self._read("static", "index.html")
        self.assertIn("mcp_server.py", h)
        self.assertIn("따로 띄워", h)

    def test_켜고_끄는_길이_붙어_있다(self):
        j = self._read("static", "app.js")
        self.assertIn("function mcpLoad", j)
        self.assertIn("function mcpOp", j)
        self.assertIn("'/api/mcp'", j)
        for op in ("'on'", "'off'", "'url'", "'reconnect'"):
            self.assertIn(op, j, op)

    def test_두들기는_동안_버튼을_잠근다(self):
        """★죽은 서버는 3초 걸린다. 안 잠그면 계속 눌러 요청이 쌓인다."""
        j = self._read("static", "app.js")
        i = j.index("function mcpSetBusy")
        self.assertIn("disabled", j[i:i + 400])

    def test_첫_화면을_MCP_때문에_늦추지_않는다(self):
        """★죽은 서버 두들기기 3초 동안 화면이 안 뜨면 안 된다."""
        j = self._read("static", "app.js")
        self.assertIn("\n  mcpLoad();", j)
        self.assertNotIn("await mcpLoad()", j)

    def test_서버에_길이_있다(self):
        s = self._read("avatar", "server.py")
        self.assertIn('if path == "/api/mcp":', s)
        self.assertIn("def _mcp_op", s)
        i = s.index("def _mcp_op")
        self.assertIn('App.settings.update({"mcp"', s[i:i + 2200])

    def test_파일이_없어서_꺼진_것은_화면이_못_켠다(self):
        """★켜졌다고 해 놓고 물어볼 때마다 실패하면, 사람은 다른 데를 뒤진다."""
        s = self._read("avatar", "server.py")
        i = s.index("def _mcp_op")
        self.assertIn('off_reason', s[i:i + 2200])
        self.assertIn('startswith("서버 파일")', s[i:i + 2200])


class 위키를_직접_띄우는_길도_있다(unittest.TestCase):
    """LLM_WIKI_MCP/wiki_mcp_stdio.py — 포트도 설치도 없는 쪽.

    ★왜 또 만들었나. 공식 SDK 쪽(streamable-http)이 현장에서 세 번 걸렸다:
        · 사람이 따로 띄워야 한다
        · 포트를 헷갈린다 (웹앱 :8100 · MCP :8020 → HTML 404)
        · pip install "mcp>=1.27,<2" 가 필요하다 (폐쇄망 반입)
      이건 아바타가 자식 프로세스로 띄우므로 셋 다 없다.
    """

    PATH = ("LLM_WIKI_MCP", "wiki_mcp_stdio.py")

    def setUp(self):
        import sqlite3, tempfile, shutil
        p = os.path.join(util.BASE, *self.PATH)
        if not os.path.isfile(p):
            raise unittest.SkipTest("wiki_mcp_stdio.py 가 없다")
        self.py = p
        self.dir = tempfile.mkdtemp(prefix="wikidb")
        self.addCleanup(lambda: shutil.rmtree(self.dir, ignore_errors=True))
        self.db = os.path.join(self.dir, "wiki.db")
        c = sqlite3.connect(self.db)
        c.executescript(
            "CREATE TABLE domains(id INTEGER PRIMARY KEY, slug TEXT, name TEXT,"
            " description TEXT, created_at TEXT);"
            "CREATE TABLE pages(id INTEGER PRIMARY KEY, domain_id INT, title TEXT,"
            " slug TEXT, ptype TEXT, tags TEXT, summary TEXT, body_md TEXT,"
            " author TEXT, source_ids TEXT, created_at TEXT, updated_at TEXT);"
            "CREATE TABLE sources(id INTEGER PRIMARY KEY, domain_id INT,"
            " filename TEXT, stored_name TEXT, filetype TEXT, description TEXT,"
            " extracted_text TEXT, uploader TEXT, created_at TEXT);"
            "INSERT INTO domains VALUES(1,'virtual-avatar','버츄얼 아바타','','');"
            "INSERT INTO pages VALUES(12,1,'반송 장치 종류와 역할','x','concept',"
            "'VHL,LFT','FOUP 이 거치는 장치','LFT 는 리프터다. 층간 반송을 "
            "담당한다.','','','','2026-08-30');"
            "INSERT INTO sources VALUES(4,1,'연결도.png','a.png','image',"
            "'M14 와 M16 연결도','','john','2026-08-30');")
        c.commit()
        c.close()

    def talk(self, *calls):
        """진짜 프로세스를 띄워 stdio 로 주고받는다."""
        import subprocess
        reqs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize",
                 "params": {"protocolVersion": mcp_client.PROTO}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"}]
        for i, (name, args) in enumerate(calls, start=2):
            reqs.append({"jsonrpc": "2.0", "id": i, "method": "tools/call",
                         "params": {"name": name, "arguments": args}}
                        if name else
                        {"jsonrpc": "2.0", "id": i, "method": "tools/list"})
        p = subprocess.run(
            [sys.executable, self.py],
            input="\n".join(json.dumps(r) for r in reqs),
            capture_output=True, text=True, timeout=40,
            env=dict(os.environ, WIKI_DB=self.db))
        return [json.loads(x) for x in p.stdout.splitlines() if x.strip()]

    def test_악수하고_도구를_준다(self):
        got = self.talk((None, None))
        self.assertEqual(got[0]["result"]["serverInfo"]["name"], "llm-wiki")
        names = [t["name"] for t in got[1]["result"]["tools"]]
        self.assertEqual(set(names), {"listDomains", "searchWiki", "readPage",
                                      "listSources", "readSource"})

    def test_읽기_전용이다(self):
        """★위키를 고치는 도구가 섞이면 안 된다."""
        got = self.talk((None, None))
        for t in got[1]["result"]["tools"]:
            for bad in ("create", "update", "delete", "write", "ingest",
                        "save", "edit"):
                self.assertNotIn(bad, t["name"].lower(), t["name"])

    def test_검색하고_본문을_읽는다(self):
        got = self.talk(("searchWiki", {"query": "LFT 가 뭐야"}),
                        ("readPage", {"pageId": 12}))
        s1 = got[1]["result"]["content"][0]["text"]
        self.assertIn("#12", s1)
        self.assertIn("반송 장치", s1)
        self.assertFalse(got[1]["result"]["isError"])
        s2 = got[2]["result"]["content"][0]["text"]
        self.assertIn("리프터", s2)          # 조각이 아니라 본문

    def test_없는_것은_isError_로_준다(self):
        """★JSON-RPC error 를 내면 클라이언트가 연결을 접는다."""
        got = self.talk(("readPage", {"pageId": 999}))
        self.assertNotIn("error", got[1])
        self.assertTrue(got[1]["result"]["isError"])

    def test_검색_순위가_웹앱과_같다(self):
        """★화면에서 검색한 순서와 서윤이 받는 순서가 다르면
        "화면엔 이게 위에 뜨는데 왜 딴소리냐" 가 된다."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("wiki_stdio", self.py)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        # app.py 의 tokenize 와 같은 규칙 (한글은 2글자 조각까지)
        self.assertEqual(m.tokenize("LFT 리프터"),
                         ["lft", "리프터", "리프", "프터"])
        docs = [{"id": 1, "kind": "page", "title": "리프터", "text": "층간 반송"},
                {"id": 2, "kind": "page", "title": "스토커", "text": "임시 저장"}]
        self.assertEqual(m.bm25_search("리프터", docs)[0][1]["id"], 1)

    def test_DB_를_못_찾으면_어디를_봤는지_말한다(self):
        """★"안 된다" 만 하면 어디를 고쳐야 할지 모른다."""
        import subprocess
        p = subprocess.run(
            [sys.executable, self.py, "--check"], capture_output=True,
            text=True, timeout=30,
            env=dict(os.environ, WIKI_DB=os.path.join(self.dir, "없다.db")))
        self.assertIn("없다.db", p.stdout)
        self.assertIn("WIKI_DB", p.stdout)

    def test_혼자_확인할_수_있다(self):
        import subprocess
        p = subprocess.run(
            [sys.executable, self.py, "--check"], capture_output=True,
            text=True, timeout=30, env=dict(os.environ, WIKI_DB=self.db))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("버츄얼 아바타", p.stdout)
        self.assertIn("페이지 1", p.stdout)

    def test_설정에_바꾸는_법을_적어_뒀다(self):
        """★코드를 읽는 사람이 이 길이 있다는 걸 알아야 쓴다."""
        p = os.path.join(util.BASE, "avatar_2d", "avatar", "config.py")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("wiki_mcp_stdio.py", src)


class 가드가_위키_답을_먹지_않는다(unittest.TestCase):
    """★실제로 겪은 것. 위키는 제대로 읽어 왔는데 **마지막 자리에서 지워졌다.**

    나가기 직전 숫자 가드(_guard)는 대답의 숫자가 전부 근거에 있는지 본다.
    그런데 '근거' 를 관제 수치로만 잡고 있었다 — 위키에서 읽어 온 호기명
    (4AFC3201 · 6ABL60)과 층수(3F · 6F · 10F)가 '지어낸 수' 로 걸려서,
    **답이 통째로 버려지고** 엉뚱한 관제 상태 요약으로 바뀌어 나갔다.

        Q. FAB 간 연결 경로 알려줘
        A. 2026-09-01 08:55 데이터 기준으로 현재 상태는 정상이며 17.0점입니다.
           ← 위키를 물었는데 관제 점수가 나온다

    MCP 로 받아 온 글의 숫자도 **근거다.**
    """

    WIKI = ("[AMHS 위키]\n· 위키 본문 #15\n"
            "| M14A(3F) ↔ M16 HUBROOM(3F) | CNV | 남측 4AFC3201 / 북측 4AFC3301 |\n"
            "| M16A(6F) ↔ M16 HUBROOM(3F) | LFT | 6ABL60~ 로 시작 |\n"
            "| M16A(6F) ↔ M16B(10F) | LFT | 6ALF 로 시작 |")
    ANSWER = ("M14A(3F) 에서 M16 으로 가려면 CNV 를 타요. 남측 4AFC3201, "
              "북측 4AFC3301 이고요. M16A(6F) 는 6ABL60~ 리프터로, "
              "M16B(10F) 는 6ALF 로 이어져요.")

    def test_관제_숫자만으로는_통째로_걸린다(self):
        """무엇이 문제였는지 못 박아 둔다 — 되돌아가면 이게 다시 난다."""
        ok, bad = sentinel.check_numbers(self.ANSWER, {17.0, 2.61})
        self.assertFalse(ok)
        for n in (3201.0, 3301.0, 60.0):
            self.assertIn(n, bad, n)

    def test_MCP_숫자를_보태면_통과한다(self):
        allowed = {17.0, 2.61} | sentinel.numbers_of(self.WIKI)
        ok, bad = sentinel.check_numbers(self.ANSWER, allowed)
        self.assertTrue(ok, "위키 숫자를 보탰는데도 걸린다: {}".format(bad))

    def test_지어낸_수는_여전히_걸린다(self):
        """★가드를 헐겁게 만들면 안 된다. 위키에도 관제에도 없는 수는 잡는다."""
        allowed = {17.0} | sentinel.numbers_of(self.WIKI)
        ok, bad = sentinel.check_numbers(
            "M16A 는 9999 점이고 리프터가 4321 대예요", allowed)
        self.assertFalse(ok)
        self.assertIn(9999.0, bad)
        self.assertIn(4321.0, bad)

    def test_서버가_MCP_숫자를_근거에_넣는다(self):
        p = os.path.join(util.BASE, "avatar_2d", "avatar", "server.py")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        i = src.index("mcp = self._mcp_text(text, history)")
        blk = src[i:i + 900]
        self.assertIn("numbers_of(mcp)", blk)
        self.assertIn('ev["numbers"]', blk)
        # 가드보다 **먼저** 넣어야 한다 (넣기 전에 검사하면 소용없다)
        self.assertLess(i, src.index("def _guard"))

    def test_numbers_of_가_공개되어_있다(self):
        self.assertTrue(hasattr(sentinel, "numbers_of"))
        self.assertEqual(sentinel.numbers_of("3F 6ABL60 10.5"),
                         {3.0, 6.0, 60.0, 10.5})


class 검색어에서_군말을_뺀다(unittest.TestCase):
    """★"AMHS 위키 너가 알고 있는 내용 확인해봐" 를 통째로 넘기면 BM25 가
    문서에 없는 말(너가·알고·확인해봐)에 점수를 나눠 준다. 찾을 말만 남긴다.

    (이것만으로 못 찾던 것이 찾아지지는 않았다 — 진짜 원인은 숫자 가드였다.
     여기는 검색어를 깨끗하게 하는 것이 목적이다.)
    """

    SPEC = {"kind": "text", "max": 160}

    def q(self, t):
        return mcp_client._arg_of(t, self.SPEC)

    def test_상투어를_뺀다(self):
        self.assertEqual(self.q("AMHS 위키 너가 알고 있는 내용 확인해봐"),
                         "AMHS 위키")
        self.assertEqual(self.q("M16 HUBROOM 유의 지표 설명해봐"),
                         "M16 HUBROOM 유의 지표")

    def test_영문_숫자_코드는_짧아도_남긴다(self):
        """★그게 제일 센 신호다. 길이로 자르면 LFT·ZT·R4 가 날아간다."""
        for w in ("LFT", "ZT", "R4", "6ABL60", "4AFC3201", "M16WT", "CNV"):
            self.assertIn(w, self.q(w + " 가 뭐야"), w)

    def test_다_빼면_원문을_그대로_쓴다(self):
        """★빈 검색어를 보내면 도구가 아무것도 못 한다."""
        self.assertTrue(self.q("그거 뭐야"))
        self.assertIsNone(self.q("   "))

    def test_뜻있는_한글은_남긴다(self):
        got = self.q("반송 장치 종류 알려줘")
        self.assertIn("반송", got)
        self.assertIn("장치", got)
        self.assertIn("종류", got)
        self.assertNotIn("알려줘", got)


class 위키_설정이_말이_된다(unittest.TestCase):

    def hub(self):
        return mcp_client.Hub(config.MCP_SERVERS)

    def keys(self, q):
        return [s["key"] for s in self.hub().matched(q)]

    def test_등록되어_있다(self):
        w = [s for s in config.MCP_SERVERS if s["key"] == "wiki"]
        self.assertEqual(len(w), 1)
        self.assertEqual(w[0]["transport"], "http")
        self.assertTrue(w[0]["url"].endswith("/mcp"))

    def test_기본_주소가_MCP_포트다(self):
        """★위키는 프로세스가 **둘**이다. 여기서 한 번 헛짚었다.

            app.py         Flask 웹앱      기본 :8100   사람이 보는 화면
            mcp_server.py  FastMCP · MCP   기본 :8020   서윤이 붙는 곳

        웹앱 포트를 기본값으로 두면 /mcp 가 없어서 HTML 404 가 난다 —
        서버는 멀쩡히 떠 있는데 왜 안 되는지 알 길이 없다.
        """
        w = [s for s in config.MCP_SERVERS if s["key"] == "wiki"][0]
        self.assertIn(":8020/mcp", w["url"])
        self.assertNotIn(":8100", w["url"], "웹앱 포트를 보고 있다")
        # 문서가 둘을 갈라 놓아야 한다 — 안 그러면 그대로 또 헤맨다
        d = os.path.join(util.BASE, "LLM_WIKI_MCP", "연결방법.md")
        if os.path.isfile(d):
            with open(d, encoding="utf-8") as f:
                doc = f.read()
            self.assertIn("app.py", doc)
            self.assertIn("8100", doc)
            self.assertIn("8020", doc)
            self.assertIn("LLM_WIKI_MCP_PORT", doc)

    def test_반송_지식_질문에_걸린다(self):
        """★지식은 위키에 있고 **서윤은 거기서 가져온다.** 미리 알고 있으면
        안 된다 — 위키를 고쳐도 서윤이 옛 것을 말하게 된다.
        그러니 도메인 질문에는 **반드시** 걸려야 한다."""
        for q in ("LFT가 뭐야?", "STK랑 STB 차이가 뭐지",
                  "M16 HUBROOM 이 뭐하는 데야", "Sorter 대기Q 왜 중요해",
                  "FOUP 이 어디를 경유해?", "OHT 가 무엇을 하는 거야",
                  "반송 장치 종류 뭐가 있어"):
            self.assertIn("wiki", self.keys(q), q)

    def test_장치의_다른_이름으로도_걸린다(self):
        """★현장은 다른 이름으로 부른다 — LFT=ZT · STB=ZFS · MLUD=FIO."""
        for q in ("ZT 가 뭐야", "ZFS 랑 STK 차이", "FIO 는 무슨 장치야",
                  "rack master 가 뭐지", "FOSB 가 뭔데", "VHL 이 뭐야"):
            self.assertIn("wiki", self.keys(q), q)

    def test_호기명으로도_걸린다(self):
        """★"4AFC3201 이 뭐야" 는 낱말이 하나도 안 걸린다. 호기명은 숫자로
        시작하는 대문자 코드라 관제 질문에는 안 나온다 — 코드로 잡는다."""
        for q in ("4AFC3201 이 뭐야", "6ABL60 은 어디 리프터야",
                  "4ABLD 로 시작하는 게 뭐지", "6FIOB 는 뭐하는 거야",
                  "SORTERWAITCOUNTOVER 이 뭔데"):
            self.assertIn("wiki", self.keys(q), q)

    def test_관제_시스템이_아닌_건물로도_걸린다(self):
        """★M14분석실·M16EUV·M16WT·M10A·R4 는 관제 시스템이 아니다 —
        이 이름이 나오면 지식 질문이다."""
        for q in ("M16EUV 랑 M16WT 는 어떻게 이어져", "R4 는 어디야",
                  "M10A 에서 M16 어떻게 가", "M14분석실은 뭐로 연결돼"):
            self.assertIn("wiki", self.keys(q), q)

    def test_서윤이_미리_알고_있지_않다(self):
        """★반송 지식을 스킬로 심어 두면 안 된다.

        지식의 집은 **위키 하나**다. 스킬에 박아 두면 위키를 고쳐도 서윤은
        옛 것을 말한다 — 두 벌이 되는 순간 어느 쪽이 맞는지 아무도 모른다.
        서윤은 **위키에서 가져와야** 한다.

        (fab-score·m16-hub-* 는 배점·임계 스킬이라 여기 해당 없다 —
         용어·장치·경로·호기명만 위키 몫이다.)
        """
        p = os.path.join(util.BASE, "avatar_2d", "avatar", "skills.py")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("seed_hubroom", src,
                         "반송 지식을 스킬로 심고 있다")
        for w in ("MLUD", "4AFC", "6ABL", "6FIOB", "ZFS", "FOSB", "WIS_M16WT"):
            self.assertNotIn(w, src, "반송 지식이 스킬에 박혀 있다: " + w)
        d = os.path.join(util.BASE, "docs")
        if os.path.isdir(d):
            for n in os.listdir(d):
                self.assertNotIn("도메인지식", n,
                                 "반송 지식이 스킬 원본으로 남아 있다: " + n)

    def test_관제_질문에는_안_걸린다(self):
        """★"M14 반송시간 알려줘" 가 걸려서 '반송' 을 낱말에서 뺐다.
        평소 관제 대화마다 위키를 뒤지면 그게 곧 비용이다."""
        for q in ("M16HUB 지금 몇 점이야?", "M14 반송시간 알려줘",
                  "ALL 점수 얼마야", "지금 상태 어때", "M16B 어때",
                  "M14 반송 어떻게 되고 있어?", "어제 8시에 어땠어?"):
            self.assertNotIn("wiki", self.keys(q), q)

    def test_주소를_밖에서_바꿀_수_있다(self):
        """★위키가 다른 PC 에 떠 있는 게 보통이다. 코드를 고치게 만들면
        안 된다 — run.py --wiki 나 WIKI_MCP_URL 로 준다."""
        p = os.path.join(util.BASE, "avatar_2d", "avatar", "server.py")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        self.assertIn('"{}_MCP_URL".format(s["key"].upper())', src)
        p2 = os.path.join(util.BASE, "avatar_2d", "run.py")
        with open(p2, encoding="utf-8") as f:
            run = f.read()
        self.assertIn('"--wiki"', run)
        self.assertIn('os.environ["WIKI_MCP_URL"]', run)
        # ★/mcp 를 빠뜨리면 조용히 404 다 — 붙여 준다
        self.assertIn('endswith("/mcp")', run)

    def test_요청이력과_안_겹친다(self):
        """둘이 같은 질문에 다 걸리면 한 번에 도구가 6번 돈다."""
        self.assertEqual(self.keys("보류된 요청 알려줘"), ["qa"])
        self.assertEqual(self.keys("LFT가 뭐야?"), ["wiki"])

    def test_요청이력_규칙이_위키에_안_붙는다(self):
        """★한 블록에 규칙을 다 쏟으면 서로 오염된다.

        요청이력 규칙에는 "여기 적힌 건수는 요청 접수 건수다", "총 건수와
        아직 안 끝난 것을 반드시 말한다" 가 있다. 위키 결과에 그게 붙으면
        서윤이 위키 페이지를 놓고 건수를 세려 든다.
        """
        wiki = ("[AMHS 위키]\n· 위키 본문 #12\n"
                "LFT: 리프터. 층간 반송을 담당.")
        s = llm.build_messages("서윤이다.", "LFT가 뭐야?", [], _빈자료(),
                               {"docBudget": 6000}, mcp_text=wiki)[0]["content"]
        self.assertIn("[외부 도구 — MCP]", s)
        self.assertIn("지금 수치가 아니다", s)          # 위키 규칙
        self.assertNotIn("요청 접수 건수", s)           # 요청이력 규칙
        self.assertNotIn("보류·대기·검토중", s)

    def test_위키_규칙이_요청이력에_안_붙는다(self):
        s = llm.build_messages("서윤이다.", "요청 뭐 있어?", [], _빈자료(),
                               {"docBudget": 6000},
                               mcp_text="[QA 요청이력]\n· 현황\n총 2건"
                               )[0]["content"]
        self.assertIn("요청 접수 건수", s)
        self.assertNotIn("[AMHS 위키] 는 **지식 문서**다", s)

    def test_둘_다_오면_둘_다_붙는다(self):
        both = "[QA 요청이력]\n총 2건\n\n[AMHS 위키]\nLFT: 리프터."
        s = llm.build_messages("서윤이다.", "LFT 요청 있어?", [], _빈자료(),
                               {"docBudget": 6000}, mcp_text=both)[0]["content"]
        self.assertIn("요청 접수 건수", s)
        self.assertIn("지금 수치가 아니다", s)

    def test_지식_설명은_짧게_줄이지_말라고_박는다(self):
        """★페르소나에 "1~3문장 · 목록 금지" 가 있다. 그건 **잡담용**이다.

        지식 설명에까지 걸면 "LFT 는 리프터예요" 한 줄로 끝난다 — 층간
        반송이라는 것도, ZT 라고도 부른다는 것도 다 잘린다. 위키를 읽어 온
        보람이 없다. 말투는 그대로 두고 분량만 푼다.
        """
        s = llm.build_messages("서윤이다.", "LFT가 뭐야?", [], _빈자료(),
                               {"docBudget": 6000},
                               mcp_text="[AMHS 위키]\nLFT: 리프터."
                               )[0]["content"]
        self.assertIn("짧게 줄이지 마라", s)
        self.assertIn("잡담", s)
        self.assertIn("말투는 그대로", s)
        self.assertIn("줄바꿈으로 나눠", s)

    def test_호기명을_뭉개지_말라고_박는다(self):
        """★`6ABL60~` 를 '6ABL 계열' 로 뭉개면 현장이 아는 이름이 사라진다."""
        s = llm.build_messages("서윤이다.", "6ABL60 이 뭐야?", [], _빈자료(),
                               {"docBudget": 6000},
                               mcp_text="[AMHS 위키]\n6ABL60~ 리프터"
                               )[0]["content"]
        self.assertIn("원문 그대로", s)
        self.assertIn("6ABL60", s)
        self.assertIn("경로를 물으면", s)      # 중간을 건너뛰지 말라고

    def test_잡담에는_분량_규칙을_안_푼다(self):
        """★위키가 안 걸린 대화까지 길어지면 서윤이 아니다."""
        s = llm.build_messages("서윤이다.", "요청 뭐 있어?", [], _빈자료(),
                               {"docBudget": 6000},
                               mcp_text="[QA 요청이력]\n총 2건")[0]["content"]
        self.assertNotIn("짧게 줄이지 마라", s)

    def test_본문을_넉넉히_읽는다(self):
        """★검색 조각(500자)만 보고 답하면 앞머리만 안다. 본문 몫을 따로
        크게 준다 — 검색은 '어느 쪽인가' 만 알면 된다."""
        w = [x for x in config.MCP_SERVERS if x["key"] == "wiki"][0]
        then = w["calls"][0]["then"]
        self.assertGreaterEqual(then["max"], 3, "본문을 두 쪽만 읽는다")
        self.assertGreater(then.get("budget", 0), w["budget"],
                           "본문 몫이 검색 조각 몫보다 작다")

    def test_본문_예산이_검색_예산과_따로_논다(self):
        h = mcp_client.Hub([])
        self.assertIn("잘렸다", h._fit({"budget": 10}, "가" * 50))
        self.assertEqual(h._fit({"budget": 4000}, "가" * 50), "가" * 50)

    def test_위키_숫자를_현재값으로_말하지_말라고_박는다(self):
        """★위키에는 예시 수치가 적혀 있다. 그걸 현재 값처럼 말하면
        관제 화면과 어긋난다 — 첨부에서 똑같이 겪은 자리다."""
        s = llm.build_messages("서윤이다.", "STK 저장율?", [], _빈자료(),
                               {"docBudget": 6000},
                               mcp_text="[AMHS 위키]\n저장율 90% 초과 반복"
                               )[0]["content"]
        self.assertIn("현재 값으로 말하면 안 된다", s)

    def test_잘린_본문을_아는_척하지_말라고_박는다(self):
        s = llm.build_messages("서윤이다.", "LFT?", [], _빈자료(),
                               {"docBudget": 6000},
                               mcp_text="[AMHS 위키]\n가나다\n…(뒤가 잘렸다 · 전체 900자)"
                               )[0]["content"]
        self.assertIn("안 본 부분을 아는 것처럼 말하지 마라", s)

    def test_읽기_전용만_부른다(self):
        """★위키는 쓰기 도구(페이지 생성·수정)도 갖고 있다. 서윤이
        부르는 목록에 그런 게 섞이면 안 된다."""
        w = [s for s in config.MCP_SERVERS if s["key"] == "wiki"][0]
        names = [c["tool"] for c in w["calls"]]
        names += [c["then"]["tool"] for c in w["calls"] if c.get("then")]
        for n in names:
            self.assertIn(n, ("searchWiki", "readPage", "listDomains",
                              "listSources", "readSource"), n)


if __name__ == "__main__":
    unittest.main()
