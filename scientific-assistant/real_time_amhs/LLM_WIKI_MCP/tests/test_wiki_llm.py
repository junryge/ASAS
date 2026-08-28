# -*- coding: utf-8 -*-
"""위키 app.py 의 LLM 호출부를 진짜 게이트웨이를 세워 두고 확인한다.

돌리는 법
    python3 LLM_WIKI_MCP/tests/test_wiki_llm.py

여기서 잡는 것 — 회사에서 실제로 터진 것들이다.
    · 주소 끝에 /chat/completions 를 붙여 넣어 손잡이가 두 번 붙던 404
    · 사고 모델이 content 를 null 로 줘서 나던
      TypeError: 'NoneType' object is not subscriptable

진짜 DB 와 진짜 HTTP 를 쓴다. 흉내(mock)로는 저 두 개가 안 잡힌다.
"""
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
WIKI = os.environ.get("WIKI_DIR") or os.path.join(
    os.path.dirname(HERE), "amhs-llm-wiki")
if not os.path.isfile(os.path.join(WIKI, "app.py")):
    raise SystemExit("위키를 못 찾았다: {}\nWIKI_DIR 로 알려 줘라.".format(WIKI))
sys.path.insert(0, WIKI)
os.environ["LLM_WIKI_DATA"] = tempfile.mkdtemp(prefix="wikitest_")

import app as W                                                    # noqa: E402


# ───────────────────────────────── 가짜 게이트웨이
class _Gate(BaseHTTPRequestHandler):
    MODE = "ok"          # 클래스 변수로 시험마다 갈아 끼운다
    SEEN = []            # 실제로 받은 payload 들

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n)
        # ★진짜 게이트웨이처럼 이 길만 연다. 손잡이가 두 번 붙으면 404 가 나야 한다.
        if self.path != "/v1/chat/completions":
            return self._send(404, {"error": "not found: " + self.path})
        body = json.loads(raw.decode("utf-8"))
        _Gate.SEEN.append(body)
        mode = _Gate.MODE

        # 이 게이트웨이는 chat_template_kwargs 를 모른다 → 400
        if mode == "picky" and "chat_template_kwargs" in body:
            return self._send(400, {"error": "unknown field chat_template_kwargs"})

        if mode == "ok":
            msg = {"role": "assistant", "content": "2 입니다"}
        elif mode in ("reasoning", "picky"):
            # ★실제 증상: content 가 null, 본문은 reasoning_content 에만
            msg = {"role": "assistant", "content": None,
                   "reasoning_content": "음... 1+1 이니까 2"}
        elif mode == "empty":
            msg = {"role": "assistant", "content": None, "reasoning_content": ""}
        elif mode == "junk":
            return self._send(200, {"nope": 1})
        else:
            raise AssertionError(mode)
        self._send(200, {"choices": [{"message": msg, "finish_reason": "length"}]})

    def _send(self, code, obj):
        raw = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), _Gate)
        cls.url = "http://127.0.0.1:{}/v1".format(cls.srv.server_port)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        _Gate.SEEN = []
        W.init_db()
        self.ctx = W.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def cfg(self, url=None, model="gaia-Qwen3.5-397B-A17B"):
        W.set_setting("llm_base_url", url if url is not None else self.url)
        W.set_setting("llm_model", model)
        W.set_setting("llm_api_key", "")


# ───────────────────────────────── 주소 손질
class TestApiBase(Base):
    def test_손잡이가_붙어_있으면_뗀다(self):
        self.assertEqual(W.api_base("http://h/v1/chat/completions"), "http://h/v1")
        self.assertEqual(W.api_base("http://h/v1/embeddings"), "http://h/v1")
        self.assertEqual(W.api_base("http://h/v1/rerank"), "http://h/v1")

    def test_base_는_그대로_둔다(self):
        self.assertEqual(W.api_base("http://h/v1"), "http://h/v1")
        self.assertEqual(W.api_base("http://h/v1/"), "http://h/v1")

    def test_빈값(self):
        self.assertEqual(W.api_base(None), "")

    def test_completions_만_붙은_것도_뗀다(self):
        self.assertEqual(W.api_base("http://h/v1/completions"), "http://h/v1")


# ───────────────────────────────── 사고 모델 판별
class TestIsReasoning(Base):
    def test_사고_모델들(self):
        for m in ("gaia-Qwen3.5-397B-A17B", "QwQ-32B", "deepseek-r1",
                  "gpt-oss-120b", "o3-mini", "some-thinking-model"):
            self.assertTrue(W._is_reasoning(m), m)

    def test_보통_모델들(self):
        for m in ("gpt-4o", "llama-3.1-70b", "qwen2.5-72b", "", None):
            self.assertFalse(W._is_reasoning(m), m)


class TestNoThink(Base):
    def test_마지막_user_에만_붙는다(self):
        ms = [{"role": "user", "content": "첫째"},
              {"role": "assistant", "content": "네"},
              {"role": "user", "content": "둘째"}]
        out = W._no_think(ms)
        self.assertNotIn("/no_think", out[0]["content"])
        self.assertTrue(out[2]["content"].endswith("/no_think"))

    def test_원본을_안_건드린다(self):
        ms = [{"role": "user", "content": "가"}]
        W._no_think(ms)
        self.assertEqual(ms[0]["content"], "가")

    def test_두_번_안_붙는다(self):
        ms = [{"role": "user", "content": "가\n\n/no_think"}]
        self.assertEqual(W._no_think(ms)[0]["content"].count("/no_think"), 1)

    def test_user_가_없어도_안_터진다(self):
        self.assertEqual(len(W._no_think([{"role": "system", "content": "x"}])), 1)


# ───────────────────────────────── 본문 꺼내기
class TestPickText(Base):
    def test_평범한_응답(self):
        d = {"choices": [{"message": {"content": "답"}}]}
        self.assertEqual(W._pick_text(d), "답")

    def test_content_가_None_이면_reasoning_content_를_쓴다(self):
        d = {"choices": [{"message": {"content": None,
                                      "reasoning_content": "생각한 답"}}]}
        self.assertEqual(W._pick_text(d), "생각한 답")

    def test_content_가_공백만_이어도_넘어간다(self):
        d = {"choices": [{"message": {"content": "   ", "reasoning": "R"}}]}
        self.assertEqual(W._pick_text(d), "R")

    def test_전부_비면_이유를_말한다(self):
        d = {"choices": [{"message": {"content": None}, "finish_reason": "length"}]}
        with self.assertRaises(RuntimeError) as c:
            W._pick_text(d)
        self.assertIn("length", str(c.exception))
        self.assertIn("빈 응답", str(c.exception))

    def test_형식이_이상하면_TypeError_가_아니라_설명(self):
        for d in ({}, {"choices": []}, {"choices": [{}]}, None):
            with self.assertRaises(RuntimeError):
                W._pick_text(d)


# ───────────────────────────────── 실제 호출
class TestLlmChat(Base):
    MSG = [{"role": "user", "content": "1+1은?"}]

    def test_평범한_게이트웨이(self):
        _Gate.MODE = "ok"
        self.cfg(model="gpt-4o")
        self.assertEqual(W.llm_chat(self.MSG, max_tokens=8), "2 입니다")
        self.assertNotIn("/no_think", _Gate.SEEN[0]["messages"][0]["content"])

    def test_사고_모델이_content_를_null_로_줘도_안_터진다(self):
        _Gate.MODE = "reasoning"
        self.cfg()
        self.assertEqual(W.llm_chat(self.MSG, max_tokens=8), "음... 1+1 이니까 2")

    def test_사고_모델엔_생각_끄기를_보낸다(self):
        _Gate.MODE = "reasoning"
        self.cfg()
        W.llm_chat(self.MSG, max_tokens=8)
        p = _Gate.SEEN[0]
        self.assertIs(p["chat_template_kwargs"]["enable_thinking"], False)
        self.assertIn("/no_think", p["messages"][0]["content"])

    def test_옵션을_모르는_게이트웨이면_빼고_다시_부른다(self):
        _Gate.MODE = "picky"
        self.cfg()
        self.assertEqual(W.llm_chat(self.MSG, max_tokens=8), "음... 1+1 이니까 2")
        self.assertEqual(len(_Gate.SEEN), 2)                # 400 한 번, 성공 한 번
        self.assertNotIn("chat_template_kwargs", _Gate.SEEN[1])

    def test_gpt_oss_는_reasoning_effort_부터_시도한다(self):
        _Gate.MODE = "reasoning"
        self.cfg(model="gpt-oss-120b")
        W.llm_chat(self.MSG, max_tokens=8)
        self.assertEqual(_Gate.SEEN[0].get("reasoning_effort"), "low")

    def test_전부_비면_설명이_있는_오류(self):
        _Gate.MODE = "empty"
        self.cfg()
        with self.assertRaises(RuntimeError) as c:
            W.llm_chat(self.MSG, max_tokens=8)
        self.assertIn("빈 응답", str(c.exception))

    def test_주소_끝에_손잡이가_붙어_있어도_404_안_난다(self):
        _Gate.MODE = "ok"
        self.cfg(url=self.url + "/chat/completions", model="gpt-4o")
        self.assertEqual(W.llm_chat(self.MSG, max_tokens=8), "2 입니다")

    def test_설정이_비면_설명(self):
        W.set_setting("llm_base_url", "")
        W.set_setting("llm_model", "")
        with self.assertRaises(RuntimeError) as c:
            W.llm_chat(self.MSG)
        self.assertIn("설정", str(c.exception))

    def test_서버가_없으면_접속_실패라고_말한다(self):
        self.cfg(url="http://127.0.0.1:1/v1", model="gpt-4o")
        with self.assertRaises(RuntimeError) as c:
            W.llm_chat(self.MSG, max_tokens=8)
        self.assertIn("접속 실패", str(c.exception))


# ───────────────────────────────── 화면 (터진 그 자리)
class TestSettingsTestLlm(Base):
    def test_사고_모델로_눌러도_500_이_아니다(self):
        _Gate.MODE = "reasoning"
        self.cfg()
        c = W.app.test_client()
        r = c.post("/settings/test-llm", follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        body = r.get_data(as_text=True)
        self.assertIn("연결 성공", body)
        self.assertNotIn("NoneType", body)

    def test_빈_응답이면_500_대신_설명이_뜬다(self):
        _Gate.MODE = "empty"
        self.cfg()
        c = W.app.test_client()
        r = c.post("/settings/test-llm", follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn("빈 응답", r.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
