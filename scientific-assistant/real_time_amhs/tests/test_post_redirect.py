# -*- coding: utf-8 -*-
"""게이트웨이가 302 로 넘길 때 POST 가 통째로 깨지던 것.

무슨 일이 있었나
    사내 게이트웨이가 http→https 로 302 를 준다. urllib(과 requests)은 그걸
    따라가면서 **POST 를 GET 으로 바꾼다.** 본문이 사라지니 서버는 그런 GET
    경로가 없다며 404 {"detail":"Not Found"} 를 돌려준다.

    화면에는 "LLM 연결 실패: HTTP 404" 만 뜬다 — 주소가 틀린 것처럼 보이는데
    사실은 맞았다. /v1/models 는 **GET** 이라 잘 되니 더 헷갈린다.
    "models 는 되는데 채팅만 404" 가 이 증상이다.

여기서 지키는 것
    30x 를 만나면 POST 를 유지한 채 새 주소로 다시 보낸다.
"""
import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import llm_client                                           # noqa: E402


class _Gate(BaseHTTPRequestHandler):
    """사내 게이트웨이 흉내 — /old 는 302, /new 는 POST 만 받는다."""

    seen: list = []
    port = 0

    def log_message(self, *a):
        pass

    def _redir(self):
        type(self).seen.append((self.command, self.path))
        self.send_response(302)
        self.send_header("Location",
                         "http://127.0.0.1:{}/new/chat/completions".format(type(self).port))
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/old"):
            return self._redir()
        # POST 자리에 GET 이 오면 FastAPI 는 404 를 준다
        type(self).seen.append(("GET", self.path))
        b = b'{"detail":"Not Found"}'
        self.send_response(404)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        if self.path.startswith("/old"):
            return self._redir()
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n)
        type(self).seen.append(("POST", self.path, len(body)))
        b = json.dumps({"choices": [{"message": {"content": "안녕하세요"}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


class 리다이렉트에서_POST_를_잃지_않는다(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), _Gate)
        _Gate.port = cls.srv.server_address[1]
        cls.url = "http://127.0.0.1:{}/old/chat/completions".format(_Gate.port)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        _Gate.seen = []

    def _payload(self):
        return {"model": "x", "messages": [{"role": "user", "content": "안녕"}]}

    def test_예전_방식은_404_가_난다(self):
        """왜 이 테스트가 있나 — 이게 실제로 난 증상이다. 기본 urllib 은
        302 를 따라가며 POST 를 GET 으로 바꾼다."""
        req = urllib.request.Request(
            self.url, data=json.dumps(self._payload()).encode(),
            headers={"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(cm.exception.code, 404)
        self.assertIn(b"Not Found", cm.exception.read())
        # 서버가 받은 두 번째 요청이 GET 이다 — 본문이 사라졌다
        self.assertEqual(_Gate.seen[1][0], "GET")

    def test_고친_방식은_POST_로_다시_보낸다(self):
        req = urllib.request.Request(
            self.url, data=json.dumps(self._payload()).encode(),
            headers={"Content-Type": "application/json"})
        with llm_client._POST_OPENER.open(req, timeout=5) as r:
            out = json.loads(r.read().decode("utf-8"))
        self.assertEqual(out["choices"][0]["message"]["content"], "안녕하세요")
        self.assertEqual(_Gate.seen[1][0], "POST")
        self.assertGreater(_Gate.seen[1][2], 0)     # 본문이 살아서 갔다

    def test_chat_이_그_opener_를_쓴다(self):
        """함수를 만들어 놓고 안 쓰면 아무 소용이 없다."""
        import inspect
        src = inspect.getsource(llm_client.chat)
        self.assertIn("_POST_OPENER.open(req", src)
        self.assertNotIn("urllib.request.urlopen(req", src)


class 위키도_같이_고쳤다(unittest.TestCase):
    """위키(app.py)는 flask 가 없으면 import 가 안 되므로 파일로 확인한다."""

    @classmethod
    def setUpClass(cls):
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "LLM_WIKI_MCP", "amhs-llm-wiki", "app.py")
        with open(p, encoding="utf-8") as f:
            cls.src = f.read()

    def test_POST_세_군데가_다_새_길로_간다(self):
        """채팅만 고치면 임베딩·리랭커가 같은 자리에서 또 걸린다."""
        self.assertIn("class _KeepPost", self.src)
        self.assertEqual(self.src.count("post_json("), 4)   # 정의 1 + 사용 3
        self.assertNotIn("urllib.request.urlopen(req", self.src)


if __name__ == "__main__":
    unittest.main()


class md_는_자기_설명을_쓴다(unittest.TestCase):
    """화면의 '설명' 칸은 한 번에 올린 파일 **전부**에 같은 값이 붙는다.
    md 9개를 올리면 아홉 개가 똑같은 설명을 갖게 되는데 그건 설명이 아니다.
    md 는 자기 summary 를 갖고 있으니 그걸 쓴다."""

    @classmethod
    def setUpClass(cls):
        import re
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.wiki = os.path.join(base, "LLM_WIKI_MCP")
        with open(os.path.join(cls.wiki, "amhs-llm-wiki", "app.py"),
                  encoding="utf-8") as f:
            src = f.read()
        cls.src = src
        ns = {"re": re}
        exec("import re\nMD_FM_RE = "
             + re.search(r"MD_FM_RE = (re\.compile\(.*?\))\n", src, re.S).group(1), ns)
        for name in ("parse_md_front", "md_desc"):
            i = src.index("def %s(" % name)
            exec(src[i:src.index("\ndef ", i + 1)], ns)
        cls.ns = ns

    def _desc(self, raw):
        meta, body = self.ns["parse_md_front"](raw)
        return self.ns["md_desc"](meta, body)

    def test_머리말_summary_를_쓴다(self):
        raw = ("---\ntitle: 개요\nsummary: M16 HUBROOM 은 M14 와 M16 을 잇는다.\n"
               "---\n# 개요\n본문이다.")
        self.assertEqual(self._desc(raw), "M16 HUBROOM 은 M14 와 M16 을 잇는다.")

    def test_summary_가_없으면_첫_문단(self):
        self.assertEqual(self._desc("# 등록 방법\n\n먼저 담당을 만든다."),
                         "등록 방법")

    def test_표_인용_코드_구분선은_설명이_아니다(self):
        raw = "---\n\n> 인용\n\n| 표 | 머리 |\n\n```\n코드\n```\n\n진짜 설명이다."
        self.assertEqual(self._desc(raw), "진짜 설명이다.")

    def test_줄바꿈은_한_줄로_편다(self):
        raw = "---\nsummary: 첫 줄이다.\n  이어지는 줄이다.\n---\n본문"
        self.assertNotIn("\n", self._desc(raw))

    def test_진짜_MD_들이_다_설명을_갖는다(self):
        import glob
        got = 0
        for p in glob.glob(os.path.join(self.wiki, "버츄얼 아바타", "*.md")):
            with open(p, encoding="utf-8-sig") as f:
                d = self._desc(f.read())
            self.assertTrue(d, os.path.basename(p) + " 에 설명이 없다")
            got += 1
        self.assertGreaterEqual(got, 9)

    def test_화면_설명이_있으면_그것을_먼저_쓴다(self):
        """사람이 적었으면 사람 말이 우선이다."""
        self.assertIn("fdesc = fdesc or md_desc(meta, body)", self.src)

    def test_소스로_갈_때도_읽는다(self):
        """as_page 가 꺼져 있어도 md 는 자기 설명을 갖는다."""
        self.assertIn('if ext in (".md", ".markdown"):', self.src)
        self.assertNotIn('if as_page and ext in (".md", ".markdown"):', self.src)
