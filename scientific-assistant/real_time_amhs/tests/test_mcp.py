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
from avatar import config, llm, mcp_client   # noqa: E402


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

    def test_목록이_길면_잘랐다고_밝힌다(self):
        """★말없이 자르면 '이게 전부' 로 읽힌다."""
        big = {"items": [dict(ITEMS["items"][0], seq=i, id=i)
                         for i in range(1, 41)]}
        old = SRV._get
        SRV._get = lambda p, q=None: big if p == "/api/items" else old(p, q)
        self.addCleanup(lambda: setattr(SRV, "_get", old))
        t = self._call("qa_items")
        self.assertIn("40건", t)
        self.assertIn("그 밖 20건은 안 실었다", t)


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
    """★서윤이 실제로 이렇게 답했다 (사장님 지적):

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
    """★서윤이 이렇게 답했다 (사장님 지적):

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
        txt, _ = self.hub.gather(q)
        return [l for l in txt.split("\n") if l.startswith("#")]

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
    """★서윤 콘솔에 이게 찍혔다 (사장님 로그):

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
        이미 손에 쥔 연결이 도중에 끊기는 경우 — 사장님 로그가 그것이다
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
        """★안 찍으면 127.0.0.1 을 보고 있는 줄 모른다."""
        s = self._src()
        self.assertIn('addr = (s.get("env") or {}).get("QA_BASE")', s)
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
        i = s.index("elif hub.matched(text):")
        self.assertIn("확인할 수 없다", s[i:i + 420])
        self.assertIn("건수를 지어내지", s[i:i + 420])

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


if __name__ == "__main__":
    unittest.main()
