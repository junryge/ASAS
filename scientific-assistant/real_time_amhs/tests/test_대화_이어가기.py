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


class 숫자_하네스(unittest.TestCase):
    """나가기 직전 결정적 검사 — 근거에 없는 수를 막는다.

    ★예전에는 **근거가 있을 때만** 돌았다. 관제가 안 떠 있는 동안 모델이
      "M16HUB 72점" 을 지어내도 아무도 안 막았다 — 그때가 제일 위험한데.
    ★이름에 박힌 수(M16HUB 의 16, 6ABL0111 의 111)를 값으로 세던 것도
      고쳤다. 근거가 넉넉할 때는 근거 글에도 M16 이 있어 가려졌지만,
      근거가 없으면 FAB 이름을 말할 때마다 가드가 터진다.
    """

    def _guard(self, text, ev, data_q, mcpn=None):
        from avatar import server as S

        class F:
            def _say(self, m):
                pass

        r = S.Handler._guard(F(), {"text": text, "emotion": "neutral",
                                   "intensity": 0.5, "motion": "none"},
                             ev, data_q, mcpn)
        return r["text"]

    def test_근거가_있으면_그_안의_수만(self):
        ev = {"ok": True, "numbers": {72.0}, "fallback": "계산값"}
        self.assertIn("72점", self._guard("M16HUB 72점 위험이에요.", ev, True))
        out = self._guard("M16HUB 88점 초위험이에요.", ev, True)
        self.assertIn("근거에 없는 숫자", out)

    def test_근거가_없어도_관제_질문이면_막는다(self):
        """★여기가 예전에 뚫려 있던 자리다."""
        out = self._guard("M16HUB 는 지금 72점이에요.", {"ok": False}, True)
        self.assertIn("근거 없는 숫자", out)
        self.assertIn("관제 데이터를 못 읽고", out)
        self.assertNotIn("72", out)

    def test_근거가_없고_수를_안_쓰면_통과(self):
        t = "지금은 확인이 안 돼요."
        self.assertEqual(self._guard(t, {"ok": False}, True), t)

    def test_관제_질문이_아니면_숫자를_안_본다(self):
        """일반 지식 답에는 수가 있어도 된다 (규칙 1-0 ③).
        여기까지 막으면 아무 말도 못 하게 된다."""
        t = "RTX 6000 은 메모리가 48GB 예요."
        self.assertEqual(self._guard(t, {"ok": False}, False), t)

    def test_MCP_로_받은_수는_쓸_수_있다(self):
        from avatar import sentinel
        t = "요청 7번은 2026-08-26 에 올라왔어요."
        got = self._guard(t, {"ok": False}, True,
                          sentinel.numbers_of("요청 7번 2026-08-26 접수"))
        self.assertEqual(got, t)

    def test_이름에_박힌_수는_값이_아니다(self):
        from avatar import sentinel
        for name in ("M16HUB", "M14B", "6ABL0111", "3F_LFT_MAXCAPA",
                     "AVGTOTALTIME1MIN", "v4.1"):
            self.assertEqual(sentinel.numbers_of(name), set(), name)
        # 값은 그대로 센다
        self.assertEqual(sentinel.numbers_of("72점 15.98분 31.2%"),
                         {72.0, 15.98, 31.2})

    def test_FAB_이름만_말해도_안_걸린다(self):
        """근거가 없을 때 이 오탐이 나면 아바타가 말을 못 한다."""
        t = "M16HUB 와 M14B 는 3F 로 이어져요."
        self.assertEqual(self._guard(t, {"ok": False}, True), t)

    def test_지어낸_수는_여전히_잡는다(self):
        """가드를 헐겁게 만들면 안 된다."""
        out = self._guard("M16HUB 는 9999 점이에요.", {"ok": False}, True)
        self.assertIn("근거 없는 숫자", out)

    def test_두_경로에_다_걸린다(self):
        """스트리밍이 평소 경로다 — 거기 안 걸리면 사실상 없는 가드다."""
        src = open(os.path.join(util.BASE, "avatar_2d", "avatar", "server.py"),
                   encoding="utf-8").read()
        self.assertEqual(src.count("self._guard("), 2, "호출이 둘이 아니다")
        i = src.index("SSE : 파싱된 이벤트")
        self.assertIn("self._guard(", src[i:i + 1500], "스트리밍에 가드가 없다")


class 재료를_읽었나(unittest.TestCase):
    """MCP 가 답을 줬는데 "모른다" 고 하면 그건 실패다.

    실제로 겪은 것 — 위키에 올려 둔 글이 프롬프트에 들어갔는데도
    "지금은 확인이 안 돼요" 라고 답했다. 지금까지 이걸 막는 것은 프롬프트
    규칙뿐이었다. 규칙은 부탁이지 검사가 아니다.
    """

    @classmethod
    def setUpClass(cls):
        from avatar import harness
        cls.h = harness

    def _run(self, mcp, question, answer):
        c = self.h.used_material(mcp, question)
        return c.fn(answer, "")

    # ── 열쇠 뽑기 ────────────────────────────────────────────────
    def test_재료에_있는_낱말만_열쇠다(self):
        ks = self.h.question_keys("리센느 누구야?", "리센느는 아르카디아 리더")
        self.assertIn("리센느", ks)

    def test_재료에_없는_낱말은_열쇠가_아니다(self):
        self.assertEqual(
            self.h.question_keys("슬로아 누구야?", "리센느는 아르카디아 리더"),
            [])

    def test_조사가_붙어도_찾는다(self):
        """'리센느는' 으로 물어도 재료의 '리센느' 를 찾아야 한다."""
        ks = self.h.question_keys("리센느는 누구지", "아르카디아의 리더는 리센느.")
        self.assertIn("리센느", ks)

    def test_재료가_비면_열쇠도_없다(self):
        self.assertEqual(self.h.question_keys("리센느 누구야?", ""), [])

    # ── 검사 ────────────────────────────────────────────────────
    def test_재료에_있는데_모른다면_실패(self):
        ok, why = self._run("리센느는 아르카디아의 리더예요.",
                            "리센느 누구야?", "지금은 확인이 안 돼요.")
        self.assertFalse(ok)
        self.assertIn("리센느", why)

    def test_재료를_읽고_답하면_통과(self):
        ok, _ = self._run("리센느는 아르카디아의 리더예요.",
                          "리센느 누구야?", "리센느는 아르카디아의 리더예요.")
        self.assertTrue(ok)

    def test_재료에_없으면_모른다고_해도_된다(self):
        """이게 무너지면 '모르면 모른다' 가 깨진다 — 지어내게 된다."""
        ok, _ = self._run("리센느는 아르카디아의 리더예요.",
                          "슬로아 누구야?", "지금은 확인이 안 돼요.")
        self.assertTrue(ok)

    def test_재료가_아예_없으면_검사_안_한다(self):
        ok, _ = self._run("", "리센느 누구야?", "지금은 확인이 안 돼요.")
        self.assertTrue(ok)


class 재료_검사가_실제로_걸리나(unittest.TestCase):
    """붙여 놓기만 하고 안 부르면 없는 것과 같다 — 실제로 그랬다."""

    @classmethod
    def setUpClass(cls):
        cls.src = open(
            os.path.join(util.BASE, "avatar_2d", "avatar", "server.py"),
            encoding="utf-8").read()

    def test_두_경로에_다_재료를_넘긴다(self):
        """스트리밍이 평소 경로다. 한쪽만 넘기면 브라우저에선 안 돈다."""
        self.assertEqual(self.src.count("mcp=mcp"), 2,
                         "_analysis_loop 에 재료를 넘기는 자리가 둘이 아니다")

    def test_스트리밍_쪽에도_넘긴다(self):
        i = self.src.index("SSE : 파싱된 이벤트")
        self.assertIn("mcp=mcp", self.src[i:i + 1500],
                      "스트리밍에서 재료를 안 넘긴다")

    def test_재료_검사는_분석_질문이_아니어도_돈다(self):
        """"리센느 누구야?" 는 분석이 아니다 — 그래도 재료는 읽어야 한다."""
        i = self.src.index("def _analysis_loop")
        seg = self.src[i:i + 1500]
        self.assertIn("self._material_checks(mcp, question, ev)", seg)
        # 분석 요건은 예전처럼 '분석을 물었을 때만'
        j = seg.index("_material_checks")
        self.assertIn("ANALYSIS_ASK.search", seg[j:],
                      "분석 요건이 잡담에도 걸린다")

    def test_잡담에는_분석_요건을_안_건다(self):
        """첨부를 열어 둔 채 "고마워" 까지 다그치면 잡담마다 LLM 을 또 부른다."""
        i = self.src.index("def _analysis_loop")
        seg = self.src[i:i + 1500]
        j = seg.index("ANALYSIS_ASK.search")
        self.assertIn("self._analysis_checks(aname, ev)", seg[j:j + 200])

    def test_관제가_죽으면_모른다고_해도_안_걸린다(self):
        """관제 down 인 데이터 질문에서 '확인이 안 돼요' 는 맞는 답이다."""
        i = self.src.index("def _material_checks")
        seg = self.src[i:self.src.index("def _analysis_checks", i)]
        self.assertIn("is_data_question(question)", seg)
        self.assertIn("return []", seg)


if __name__ == "__main__":
    unittest.main()
