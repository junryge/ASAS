# -*- coding: utf-8 -*-
"""대화가 이어지게 하는 세 자리.

무엇이 문제였나 — 셋 다 실제로 겪은 것이다.
  ① 조회해 둔 자료가 이어지는 질문에 안 실렸다
     대화 열쇠를 '첫 사람 발화' 로 짚었는데, 화면은 history 를 최근
     keepMsgs 개만 보낸다. 12개(=7턴쯤)를 넘는 순간부터 '첫 발화' 가
     매 턴 바뀌어 열쇠가 달라졌다 — 기억이 매번 끊겼다.
  ② 컨텍스트 한도를 넘어도 아무것도 안 잘랐다
     ctxLimit 은 화면 게이지 숫자로만 쓰였다. 넘으면 모델이 실패하거나
     조용히 뒤를 잘라 먹었고, 사람은 "왜 이상하게 답하지" 만 겪었다.
  ③ stdio 위키가 본문을 못 읽었다
     검색이 사람 읽는 글을 줘서, 본문까지 이어 읽는 길(then)이 JSON 을
     못 읽고 조용히 멈췄다. 요약·발췌만 보고 답했다.
"""
import json
import os
import sqlite3
import sys
import tempfile
import unittest

from . import util

sys.path.insert(0, os.path.join(util.BASE, "avatar_2d"))
from avatar import llm as allm                            # noqa: E402
from avatar.mcp_client import Hub                         # noqa: E402


class 대화_열쇠(unittest.TestCase):
    """세션 id 가 오면 대화가 아무리 길어져도 열쇠가 안 바뀐다."""

    KEEP = 12

    def _run(self, sid=""):
        h = Hub([])
        full, keys = [], []
        for turn in range(1, 16):
            q = "질문{}".format(turn)
            keys.append(h._conv_key(full[-self.KEEP:], q, sid))
            full += [{"role": "user", "content": q},
                     {"role": "assistant", "content": "답"}]
        return keys

    def test_세션_id_면_안_바뀐다(self):
        keys = self._run("s-abc")
        self.assertEqual(len(set(keys)), 1, "열쇠가 바뀌었다")
        self.assertEqual(keys[0], "sid:s-abc")

    def test_세션_id_가_없으면_길어질_때_바뀐다(self):
        """옛 화면(세션 id 를 안 보냄)에서 실제로 나던 증상 — 못 박아 둔다.
        이 시험이 깨지면 그 한계가 사라진 것이니 위 주석도 같이 고친다."""
        keys = self._run("")
        self.assertEqual(len(set(keys[:7])), 1, "짧을 때는 안 바뀌어야 한다")
        self.assertGreater(len(set(keys)), 1, "길어지면 바뀌는 것이 옛 동작")

    def test_기억이_세션_id_로_이어진다(self):
        h = Hub([])
        full = [{"role": "user", "content": "처음"},
                {"role": "assistant", "content": "답"}]
        h._remember(full, "처음", "[AMHS 위키]\n본문", sid="s-1")
        # 대화가 길어져 '첫 발화' 가 사라진 뒤에도
        long = full + [{"role": r, "content": "x"}
                       for _ in range(10) for r in ("user", "assistant")]
        got = h._recall(long[-12:], "그럼 언제?", sid="s-1")
        self.assertIn("AMHS 위키", got, "세션 id 로도 못 들고 왔다")

    def test_세션이_다르면_안_섞인다(self):
        h = Hub([])
        h._remember([], "q", "[AMHS 위키]\n가", sid="s-1")
        self.assertEqual(h._recall([], "q", sid="s-2"), "",
                         "남의 대화 자료를 들고 왔다")

    def test_화면이_세션_id_를_보낸다(self):
        js = open(os.path.join(util.BASE, "avatar_2d", "static", "app.js"),
                  encoding="utf-8").read()
        i = js.index("function chatPayload(")
        self.assertIn("sid:", js[i:i + 700], "chat 에 세션 id 를 안 보낸다")
        self.assertIn("curSession", js[i:i + 700])


class 컨텍스트_한도(unittest.TestCase):
    """넘으면 줄인다. 그리고 줄였다고 말한다."""

    class Store:
        def context(self, q, budget):
            return "자" * min(budget, 20000)

        def get(self, n):
            return None

    def _fit(self, limit):
        hist = [{"role": r, "content": "긴 대화 " + "가" * 300}
                for _ in range(30) for r in ("user", "assistant")]
        st = {"keepMsgs": 12, "docBudget": 6000}
        return allm.fit_messages("서윤이다.", "M16HUB 점수 뭐야?", hist,
                                 self.Store(), st, limit=limit,
                                 evidence_text="M16HUB 72점", mcp_text="")

    def test_한도가_0_이면_안_줄인다(self):
        """예전과 같아야 한다 — 끄고 쓸 수 있어야 한다."""
        msgs, note = self._fit(0)
        self.assertEqual(note, "")
        self.assertGreater(len(msgs), 5)

    def test_넉넉하면_그대로다(self):
        msgs, note = self._fit(1000000)
        self.assertEqual(note, "")

    def test_넘으면_지난_대화부터_줄인다(self):
        big, _ = self._fit(0)
        msgs, note = self._fit(8000)
        self.assertLess(len(msgs), len(big), "안 줄였다")
        self.assertIn("지난 대화", note)

    def test_그래도_넘으면_자료를_줄인다(self):
        msgs, note = self._fit(4000)
        self.assertIn("참고 자료", note)
        # 지금 질문은 끝까지 남아야 한다 — 없으면 답이 성립하지 않는다
        self.assertEqual(msgs[-1]["role"], "user")
        self.assertIn("M16HUB 점수", msgs[-1]["content"])

    def test_다_줄여도_안_되면_말한다(self):
        """조용히 보내면 사람은 왜 이상한지 모른다."""
        msgs, note = self._fit(300)
        self.assertIn("★", note)
        self.assertIn("한도", note)

    def test_서버가_이_길을_쓴다(self):
        src = open(os.path.join(util.BASE, "avatar_2d", "avatar", "server.py"),
                   encoding="utf-8").read()
        self.assertIn("llm.fit_messages(", src)
        self.assertIn("ctx_note", src)

    def test_화면이_알림을_보여_준다(self):
        js = open(os.path.join(util.BASE, "avatar_2d", "static", "app.js"),
                  encoding="utf-8").read()
        self.assertIn("j.type === 'note'", js)


class stdio_위키가_본문까지_읽는다(unittest.TestCase):
    """검색이 JSON 을 줘야 본문까지 이어 읽는 길(then)이 돈다."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.db = os.path.join(cls.dir, "wiki.db")
        c = sqlite3.connect(cls.db)
        c.executescript("""
        CREATE TABLE domains(id INTEGER PRIMARY KEY, name TEXT, slug TEXT);
        CREATE TABLE pages(id INTEGER PRIMARY KEY, domain_id INT, title TEXT,
          slug TEXT, ptype TEXT, tags TEXT, summary TEXT, body_md TEXT,
          author TEXT, created_at TEXT, updated_at TEXT);
        CREATE TABLE sources(id INTEGER PRIMARY KEY, domain_id INT,
          filename TEXT, stored_name TEXT, title TEXT, description TEXT,
          extracted_text TEXT, created_at TEXT);
        """)
        c.execute("INSERT INTO domains VALUES(1,'관제','gwanje')")
        c.execute(
            "INSERT INTO pages VALUES(1,1,'M14 영역이 보는 컬럼과 임계','m14',"
            "'entity','M14, area_score','M14 는 룰 9종이 붙는다.',?,"
            "'','2026-09-08','2026-09-08')",
            ("M14 의 반송지연은 AVGLOADTIME1MIN 을 본다. "
             "★이 문장은 본문에만 있다.",))
        c.commit()
        c.close()

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.dir, ignore_errors=True)

    def _hub(self):
        return Hub([{
            "key": "wiki", "name": "AMHS 위키", "enabled": True,
            "when": ["M14", "컬럼"], "command": None,
            "args": ["LLM_WIKI_MCP/wiki_mcp_stdio.py"], "cwd": None,
            "env": {"WIKI_DB": self.db}, "timeout": 25, "budget": 4000,
            "calls": [{"tool": "searchWiki", "label": "위키 검색",
                       "args": {"topK": 3},
                       "pick": {"query": {"kind": "text", "max": 120}},
                       "then": [{"tool": "readPage", "label": "위키 본문",
                                 "arg": "pageId", "list": "results",
                                 "id": "id", "only": {"kind": "page"},
                                 "max": 2, "budget": 3000}]}]}])

    def test_검색이_JSON_이다(self):
        """글로 주면 then 이 json.loads 에 실패해 조용히 멈춘다."""
        got, used = self._hub().gather("M14 는 어느 컬럼을 봐?")
        i = got.index("{")
        j = got.rindex("}", 0, got.index("· 위키 본문")) + 1 \
            if "· 위키 본문" in got else got.rindex("}") + 1
        d = json.loads(got[i:j])
        self.assertIn("results", d)
        self.assertEqual(d["results"][0]["kind"], "page")
        self.assertIn("id", d["results"][0])

    def test_본문까지_이어_읽는다(self):
        got, used = self._hub().gather("M14 는 어느 컬럼을 봐?")
        self.assertGreaterEqual(used, 2, "검색만 하고 본문을 안 읽었다")
        self.assertIn("★이 문장은 본문에만 있다", got,
                      "요약·발췌만 보고 있다 — then 이 안 돈다")

    def test_http_와_열쇠_이름이_같다(self):
        """두 경로가 다른 이름을 주면 config 를 두 벌로 관리하게 된다."""
        src = open(os.path.join(util.BASE, "LLM_WIKI_MCP", "wiki_mcp_stdio.py"),
                   encoding="utf-8").read()
        i = src.index("def t_search(")
        blk = src[i:src.index("def t_page(")]
        for k in ('"kind"', '"id"', '"title"', '"snippet"', '"results"'):
            self.assertIn(k, blk, "열쇠가 없다: " + k)


if __name__ == "__main__":
    unittest.main()
