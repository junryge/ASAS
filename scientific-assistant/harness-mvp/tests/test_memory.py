"""데모스 기억 — 대화가 잘려 나갈 때 오래 남을 것만 건진다.

무엇이 문제였나
    컨텍스트가 차면 오래된 메시지를 그냥 버린다(_trim_history_for_context 의
    msgs.pop). 그 안의 결정·제약·관례도 같이 사라져서, 어제 정한 것을 오늘
    다시 묻게 된다.

설계 (cortexkit/magic-context, MIT 의 세 동작을 우리 것으로 옮김)
    Capture → Consolidate → Recall.
    원본은 OpenCode/Pi 플러그인(Bun/TS)이라 공장 망에 못 들인다. 설계만
    가져오고 구현은 파이썬으로 했다.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from demos_v1 import memory as M            # noqa: E402

U = "tester"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="mem_")
        self._old = M.DB_PATH
        M.DB_PATH = os.path.join(self.tmp, "memory.db")
        M._READY = False          # 새 임시 DB 에 스키마를 다시 만들게
        M.init()

    def tearDown(self):
        M.DB_PATH = self._old
        M._READY = False
        shutil.rmtree(self.tmp, ignore_errors=True)


class 담기(Base):
    """★응답 경로에서 부른다 — 여기가 느려지면 대화 전체가 느려진다."""

    MSGS = [
        {"role": "user", "content": "임계값은 0.30 으로 가자. 0.25 는 헛울림이 많았어."},
        {"role": "assistant", "content": "0.30 으로 맞추겠습니다."},
    ]

    def test_잘려나갈_메시지를_담는다(self):
        self.assertGreater(M.enqueue(U, "s1", self.MSGS), 0)
        self.assertEqual(M.pending_count(U), 1)

    def test_LLM을_부르지_않는다(self):
        """★큐에 넣기만 한다. 여기서 모델을 부르면 채팅이 멈춘다."""
        import demos_v1.memory as mod
        called = []
        real = mod.embed
        mod.embed = lambda *a, **k: called.append(1)
        try:
            M.enqueue(U, "s1", self.MSGS)
        finally:
            mod.embed = real
        self.assertEqual(called, [])

    def test_짧은_건_안_담는다(self):
        self.assertEqual(M.enqueue(U, "s1", [{"role": "user", "content": "ㅇㅇ"}]), 0)
        self.assertEqual(M.pending_count(U), 0)

    def test_시스템_메시지는_뺀다(self):
        body = M._msgs_to_text([{"role": "system", "content": "너는 도우미다" * 20}]
                               + self.MSGS)
        self.assertNotIn("너는 도우미다", body)
        self.assertIn("임계값", body)

    def test_이미지가_섞여도_글자만_담는다(self):
        msgs = [{"role": "user", "content": [
            {"type": "text", "text": "이 그래프 보면 임계값 0.30 이 맞다"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}}]}]
        body = M._msgs_to_text(msgs)
        self.assertIn("임계값", body)
        self.assertNotIn("base64", body)

    def test_못_뽑는_조각은_결국_비운다(self):
        """★큐 맨 앞에 박혀 있으면 뒤가 영영 안 돈다."""
        M.enqueue(U, "s1", self.MSGS)
        pid = M.take_pending(1)[0]["id"]
        for _ in range(3):
            M.bump_pending(pid)
        self.assertEqual(M.pending_count(U), 0)


class 뽑기(Base):
    RAW = json.dumps([
        {"kind": "결정", "text": "선제경보 임계값은 0.30 으로 한다", "why": "0.25 는 헛울림"},
        {"kind": "제약", "text": "주피터 비밀번호는 저장소에 넣지 않는다"},
        {"kind": "잡담", "text": "오늘 날씨가 좋다"},
    ], ensure_ascii=False)

    def test_모델_출력을_읽는다(self):
        got = M.parse_extracted(self.RAW, sid="s1")
        self.assertEqual(len(got), 3)
        self.assertEqual(got[0]["kind"], "결정")
        self.assertEqual(got[0]["sid"], "s1")

    def test_모르는_갈래는_사실로_떨군다(self):
        """★갈래를 지어내도 버리지는 않는다 — 내용은 쓸 만할 수 있다."""
        self.assertEqual(M.parse_extracted(self.RAW)[2]["kind"], "사실")

    def test_코드펜스를_벗긴다(self):
        self.assertEqual(len(M.parse_extracted("```json\n" + self.RAW + "\n```")), 3)

    def test_잡담이_섞여도_배열만_꺼낸다(self):
        self.assertEqual(
            len(M.parse_extracted("알겠습니다. 결과는 다음과 같습니다:\n" + self.RAW)), 3)

    def test_망가진_출력은_빈_목록(self):
        for bad in ("", "그냥 잡담", "{}", None, 42, "[[[", '{"a":1}'):
            self.assertEqual(M.parse_extracted(bad), [], repr(bad))

    def test_빈_배열도_정상이다(self):
        """★건질 게 없으면 없다고 하는 게 맞다. 억지로 채우면 쓰레기가 쌓인다."""
        self.assertEqual(M.parse_extracted("[]"), [])

    def test_한_조각에서_너무_많이_안_뽑는다(self):
        many = json.dumps([{"kind": "사실", "text": f"항목 {i} 입니다"}
                           for i in range(30)], ensure_ascii=False)
        self.assertLessEqual(len(M.parse_extracted(many)), M.MAX_PER_CHUNK)

    def test_같은_말은_한_번만(self):
        dup = json.dumps([{"kind": "사실", "text": "임계값은 0.30 이다"},
                          {"kind": "결정", "text": "임계값은 0.30 이다."}],
                         ensure_ascii=False)
        self.assertEqual(len(M.parse_extracted(dup)), 1)


class 적기(Base):
    ITEMS = [{"kind": "결정", "text": "선제경보 임계값은 0.30 으로 한다", "why": ""},
             {"kind": "제약", "text": "주피터 비밀번호는 저장소에 넣지 않는다", "why": ""}]

    def test_적고_읽는다(self):
        self.assertEqual(M.add(U, self.ITEMS), 2)
        self.assertEqual(len(M.all_memories(U)), 2)

    def test_두_번_적어도_안_늘어난다(self):
        M.add(U, self.ITEMS)
        self.assertEqual(M.add(U, self.ITEMS), 0)
        self.assertEqual(len(M.all_memories(U)), 2)

    def test_사용자끼리_안_섞인다(self):
        """★남의 기억이 내 대화에 끼면 그건 사고다."""
        M.add(U, self.ITEMS)
        M.add("other", [{"kind": "사실", "text": "다른 사람 기억"}])
        self.assertEqual(len(M.all_memories(U)), 2)
        self.assertNotIn("다른 사람", json.dumps(M.all_memories(U), ensure_ascii=False))

    def test_잊기는_지우지_않고_접는다(self):
        """왜 사라졌냐는 물음에 답할 수 있어야 한다."""
        M.add(U, self.ITEMS)
        mid = M.all_memories(U)[0]["mid"]
        self.assertTrue(M.forget(U, mid))
        self.assertEqual(len(M.all_memories(U)), 1)
        self.assertEqual(len(M.all_memories(U, include_dropped=True)), 2)


class 찾기(Base):
    def setUp(self):
        super().setUp()
        M.add(U, [
            {"kind": "결정", "text": "선제경보 임계값은 0.30 으로 한다"},
            {"kind": "제약", "text": "주피터 비밀번호는 저장소에 넣지 않는다"},
            {"kind": "관례", "text": "리포트는 항상 한국어로 쓴다"},
            {"kind": "사실", "text": "M16 HUBROOM 반송시간 임계는 14.765분이다"},
            {"kind": "용어", "text": "AMOS 는 반송 실적 집계표를 뜻한다"},
        ])

    def find(self, q, **kw):
        kw.setdefault("use_embed", False)
        return [h["text"] for h in M.search(U, q, **kw)]

    def test_관련된_걸_먼저_준다(self):
        self.assertIn("0.30", self.find("임계값 얼마로 했지?")[0])

    def test_한글_복합어를_찾는다(self):
        """★'반송' 이 '반송시간' 안에 있다 — 단어 단위로만 보면 못 찾는다."""
        self.assertTrue(any("14.765" in t for t in self.find("반송 얼마나 걸려?")))

    def test_관련_없으면_억지로_안_올린다(self):
        top = M.search(U, "점심 뭐 먹지", top=3, use_embed=False)
        self.assertTrue(all(h["score"] <= 1.0 for h in top),
                        [(h["text"], h["score"]) for h in top])

    def test_기억이_없으면_빈_목록(self):
        self.assertEqual(M.search("아무도아님", "임계값", use_embed=False), [])

    def test_자주_쓰인_기억이_조금_유리하다(self):
        ms = M.all_memories(U)
        one = next(m for m in ms if "한국어" in m["text"])
        for _ in range(5):
            M.mark_used(U, [one["mid"]])
        got = M.search(U, "한국어 리포트", top=1, use_embed=False)
        self.assertIn("한국어", got[0]["text"])
        self.assertGreater(got[0]["hits"], 0)


class 넣어주기(Base):
    def setUp(self):
        super().setUp()
        # ★예산이 실제로 걸리려면 한 물음에 여러 기억이 걸려야 한다
        M.add(U, [{"kind": "결정", "text": "선제경보 임계값은 0.30 으로 한다"},
                  {"kind": "사실", "text": "임계값 아래로 내려가면 경보를 푼다"},
                  {"kind": "관례", "text": "임계값을 바꾸면 하루치로 되감아 확인한다"},
                  {"kind": "제약", "text": "임계값은 운영자 승인 없이 못 바꾼다"},
                  {"kind": "용어", "text": "임계값은 반송시간 기준선을 뜻한다"},
                  {"kind": "제약", "text": "주피터 비밀번호는 저장소에 넣지 않는다"}])

    def test_블록을_만든다(self):
        text, used = M.block(U, "임계값 얼마?", cfg={"embedding": {"enabled": False}})
        self.assertIn("0.30", text)
        self.assertIn("[결정]", text)
        self.assertTrue(used)

    def test_예산을_안_넘는다(self):
        """★기억이 컨텍스트를 먹어 정작 대화가 잘리면 본말전도다."""
        head, _ = M.block(U, "임계값", budget_chars=10_000,
                          cfg={"embedding": {"enabled": False}})
        head_len = len(head) - sum(len(l) + 1 for l in head.split("\n")
                                   if l.startswith("- "))
        for budget in (30, 60, 200):
            text, used = M.block(U, "임계값", budget_chars=budget,
                                 cfg={"embedding": {"enabled": False}})
            body = sum(len(l) + 1 for l in text.split("\n") if l.startswith("- "))
            self.assertLessEqual(body, budget,
                                 f"예산 {budget} 인데 본문 {body}자를 넣었다")
            self.assertTrue(used, f"예산 {budget} 인데 하나도 못 넣었다")
        wide, wide_used = M.block(U, "임계값", budget_chars=10_000,
                                  cfg={"embedding": {"enabled": False}})
        self.assertGreater(len(wide_used), 2, "예산이 넉넉한데도 적게 넣는다")

    def test_기억이_없으면_빈_글(self):
        text, used = M.block("아무도아님", "임계값")
        self.assertEqual(text, "")
        self.assertEqual(used, [])

    def test_무시해도_된다고_알려_준다(self):
        """★관련 없는 기억이 끼면 모델이 엉뚱한 답을 한다. 무시할 길을 준다."""
        text, _ = M.block(U, "임계값", cfg={"embedding": {"enabled": False}})
        self.assertIn("무시", text)


class 임베딩(Base):
    """★있으면 쓰고, 없거나 느리면 키워드로 간다 — 여기서 막히면 채팅이 멈춘다."""

    def setUp(self):
        super().setUp()
        M.add(U, [{"kind": "사실", "text": "반송시간 임계는 14.765분이다"},
                  {"kind": "관례", "text": "리포트는 한국어로 쓴다"},
                  {"kind": "결정", "text": "임계값은 0.30 으로 한다"},
                  {"kind": "용어", "text": "AMOS 는 반송 실적 집계표다"},
                  {"kind": "제약", "text": "비밀번호는 저장소에 안 넣는다"},
                  {"kind": "사실", "text": "M16 HUBROOM 은 허브룸이다"},
                  {"kind": "사실", "text": "리프터 대기는 3분이 관찰 기준이다"}])

    def _with_embed(self, fn):
        import demos_v1.memory as mod
        real = mod.embed
        mod.embed = fn
        try:
            return M.search(U, "반송이 얼마나 걸리나", top=3)
        finally:
            mod.embed = real

    def test_임베딩이_있으면_섞어_쓴다(self):
        def fake(texts, cfg=None):
            # '한국어' 기억에 억지로 높은 점수를 주도록 벡터를 만든다
            return [[1.0, 0.0] if "한국어" in t else [0.0, 1.0] for t in texts] \
                if len(texts) > 1 else [[1.0, 0.0]]
        got = self._with_embed(fake)
        self.assertIn("한국어", got[0]["text"], [g["text"] for g in got])
        self.assertIn("sim", got[0])

    def test_임베딩이_죽어도_결과가_나온다(self):
        def dead(texts, cfg=None):
            return None
        got = self._with_embed(dead)
        self.assertTrue(got)
        self.assertNotIn("sim", got[0])

    def test_임베딩이_예외를_던져도_안_죽는다(self):
        def boom(texts, cfg=None):
            raise RuntimeError("게이트웨이 끊김")
        self.assertTrue(self._with_embed(boom))

    def test_개수가_안_맞으면_안_쓴다(self):
        """★모델이 일부만 돌려주면 엉뚱한 기억에 남의 점수가 붙는다."""
        got = self._with_embed(lambda texts, cfg=None: [[1.0, 0.0]])
        self.assertNotIn("sim", got[0])

    def test_주소를_두_군데_안_적는다(self):
        """채팅 URL 에서 엔드포인트만 갈아 끼운다."""
        c = M.embed_cfg({"embedding": {}})
        if c.get("url"):
            self.assertTrue(c["url"].endswith("/v1/embeddings"), c["url"])

    def test_토큰이_없으면_조용히_안_부른다(self):
        import demos_v1.config as cfgmod
        real = cfgmod.API_TOKEN
        cfgmod.API_TOKEN = ""
        try:
            self.assertIsNone(M.embed(["x"], {"embedding": {"enabled": True,
                                                            "url": "http://x/v1/embeddings"}}))
        finally:
            cfgmod.API_TOKEN = real


class 정리(Base):
    def test_같은_말을_합친다(self):
        M.add(U, [{"kind": "결정", "text": "선제경보 임계값은 0.30 으로 한다"},
                  {"kind": "결정", "text": "선제경보 임계값을 0.30 으로 정한다"},
                  {"kind": "관례", "text": "리포트는 한국어로 쓴다"}])
        r = M.consolidate(U)
        self.assertEqual(r["merged"], 1)
        self.assertEqual(r["left"], 2)

    def test_합칠_때_쓰인_횟수를_넘겨받는다(self):
        """★안 그러면 자주 쓰이던 기억이 정리 한 번에 '안 쓰인 것' 이 되어
        다음 단계에서 삭는다."""
        M.add(U, [{"kind": "결정", "text": "임계값은 0.30 으로 한다"}])
        first = M.all_memories(U)[0]["mid"]
        M.add(U, [{"kind": "결정", "text": "임계값을 0.30 으로 정한다"}])
        later = next(m["mid"] for m in M.all_memories(U) if m["mid"] != first)
        M.mark_used(U, [later] * 1)
        M.mark_used(U, [later])
        M.consolidate(U)
        left = M.all_memories(U)
        self.assertEqual(len(left), 1)
        self.assertGreaterEqual(left[0]["hits"], 2)

    def test_숫자가_다르면_절대_안_합친다(self):
        """★이 시스템에서 숫자는 곧 내용이다. "임계값 0.30" 과 "0.25" 는
        글자로는 거의 같지만(0.61) 정반대 지시다 — 합치면 임계값 하나가
        조용히 사라진다."""
        a = "선제경보 임계값은 0.30 으로 한다"
        b = "선제경보 임계값은 0.25 으로 한다"
        # 숫자를 빼고 보면 합칠 만큼 닮았다 — 그래서 보호장치가 필요하다
        import re as _re
        bare = lambda t: _re.sub(r"[\d.]+", "N", t)
        self.assertGreaterEqual(M._similar(bare(a), bare(b)), 0.45,
                                "이 쌍은 애초에 안 닮아서 보호장치를 시험하지 못한다")
        # 숫자를 그대로 두면 0.647 — 문턱 0.45 를 넘어 합쳐져 버린다
        self.assertEqual(M._similar(a, b), 0.0, "보호장치가 안 걸렸다")
        M.add(U, [{"kind": "결정", "text": a}, {"kind": "결정", "text": b}])
        self.assertEqual(M.consolidate(U)["merged"], 0)
        self.assertEqual(M.consolidate(U)["left"], 2)

    def test_다른_말은_안_합친다(self):
        M.add(U, [{"kind": "결정", "text": "선제경보 임계값은 0.30 으로 한다"},
                  {"kind": "제약", "text": "주피터 비밀번호는 저장소에 넣지 않는다"}])
        self.assertEqual(M.consolidate(U)["merged"], 0)

    def test_오래_안_쓰인_건_삭힌다(self):
        M.add(U, [{"kind": "사실", "text": "옛날에 적은 쓸모없는 기억"}])
        con = M._connect()
        con.execute("UPDATE memories SET at=?, last_hit=0, hits=0",
                    (M._now() - 200 * 86400,))
        con.commit(); con.close()
        self.assertEqual(M.consolidate(U)["stale"], 1)

    def test_한_번이라도_쓰인_건_안_삭힌다(self):
        """★쓰인 적 있는 기억은 오래됐다고 버리면 안 된다. 계절을 타는
        지식(연말 정산, 정기 점검)은 반년쯤 잠자코 있다가 다시 쓰인다."""
        M.add(U, [{"kind": "사실", "text": "오래 전에 쓰였던 기억"}])
        mid = M.all_memories(U)[0]["mid"]
        M.mark_used(U, [mid])
        old = M._now() - 200 * 86400
        con = M._connect()
        con.execute("UPDATE memories SET at=?, last_hit=?", (old, old))
        con.commit(); con.close()
        self.assertEqual(M.consolidate(U)["stale"], 0)
        self.assertEqual(len(M.all_memories(U)), 1)

    def test_너무_많으면_줄인다(self):
        words = ["리프터", "반송", "저장소", "분류기", "경보", "임계", "지연",
                 "허브룸", "야간", "순찰", "집계", "검증", "보고", "그래프", "튜닝"]
        M.add(U, [{"kind": "사실", "text": f"{w} 관련 규칙 {j} 를 지킨다"}
                  for j, w in enumerate(words * 2)][:30])
        r = M.consolidate(U, max_keep=10)
        self.assertEqual(r["left"], 10)
        self.assertGreater(r["trimmed"], 0)

    def test_지우지_않고_접는다(self):
        M.add(U, [{"kind": "사실", "text": t} for t in
                  ["리프터 대기를 본다", "반송 지연을 본다", "저장소 사용률을 본다",
                   "분류기 상태를 본다", "야간 순찰 경로를 본다"]])
        M.consolidate(U, max_keep=2)
        self.assertEqual(len(M.all_memories(U, include_dropped=True)), 5)

    def test_접힌_건_검색에_안_나온다(self):
        M.add(U, [{"kind": "사실", "text": "임계값 관련 기억이다"},
                  {"kind": "사실", "text": "임계값 관련 기억입니다"}])
        M.consolidate(U)
        self.assertEqual(len(M.search(U, "임계값", top=9, use_embed=False)), 1)

    def test_빈_사용자도_안_죽는다(self):
        self.assertEqual(M.consolidate("아무도아님")["left"], 0)


class 현황(Base):
    def test_숫자를_준다(self):
        M.add(U, [{"kind": "결정", "text": "임계값은 0.30 으로 한다"},
                  {"kind": "제약", "text": "비밀번호는 저장소에 안 넣는다"}])
        M.enqueue(U, "s1", [{"role": "user", "content": "긴 대화 내용" * 20}])
        s = M.stats(U)
        self.assertEqual(s["live"], 2)
        self.assertEqual(s["pending"], 1)
        self.assertEqual(s["by_kind"]["결정"], 1)


if __name__ == "__main__":
    unittest.main()


class 배선(Base):
    """★모듈이 아무리 좋아도 대화 경로에 안 붙으면 아무 일도 안 일어난다."""

    def test_잘릴_때_담긴다(self):
        """_fit_messages_to_ctx 가 버리는 메시지를 on_drop 으로 넘긴다."""
        from demos_v1.routes_chat import _fit_messages_to_ctx
        msgs = ([{"role": "system", "content": "너는 도우미다"}]
                + [{"role": "user" if i % 2 == 0 else "assistant",
                    "content": f"임계값 논의 {i} 번째 " + "가" * 400}
                   for i in range(12)])
        got = []
        out, _, _ = _fit_messages_to_ctx(msgs, 2000, 300, tpc=1.0,
                                         on_drop=lambda d: got.extend(d))
        self.assertLess(len(out), len(msgs), "아무것도 안 잘렸다 — 시험이 안 된다")
        self.assertTrue(got, "잘렸는데 아무것도 안 넘겨줬다")
        self.assertTrue(all(m.get("role") in ("user", "assistant") for m in got))

    def test_담기가_실패해도_대화는_계속된다(self):
        """★기억은 거들 뿐이다. 여기서 예외가 나면 채팅이 죽는다."""
        from demos_v1.routes_chat import _fit_messages_to_ctx

        def boom(dropped):
            raise RuntimeError("디스크 꽉 참")

        msgs = ([{"role": "system", "content": "s"}]
                + [{"role": "user", "content": "긴 내용 " + "가" * 400}
                   for _ in range(12)])
        out, cap, _ = _fit_messages_to_ctx(msgs, 2000, 300, tpc=1.0, on_drop=boom)
        self.assertTrue(out)
        self.assertGreater(cap, 0)

    def test_안_잘리면_안_부른다(self):
        from demos_v1.routes_chat import _fit_messages_to_ctx
        got = []
        _fit_messages_to_ctx([{"role": "user", "content": "짧다"}], 8000, 300,
                             on_drop=lambda d: got.extend(d))
        self.assertEqual(got, [])


class 일꾼(Base):
    """뽑기는 LLM 을 부른다 — 배경에서 돌고, 실패해도 큐가 막히지 않아야 한다."""

    def setUp(self):
        super().setUp()
        M.enqueue(U, "s1", [
            {"role": "user", "content": "선제경보 임계값은 0.30 으로 가자. "
                                        "0.25 는 헛울림이 너무 많았어."},
            {"role": "assistant", "content": "0.30 으로 맞추겠습니다."}])

    def test_뽑아서_적는다(self):
        out = M.extract_once(lambda msgs, mt=0: (json.dumps(
            [{"kind": "결정", "text": "선제경보 임계값은 0.30 으로 한다"}],
            ensure_ascii=False), ""))
        self.assertEqual(out["got"], 1)
        self.assertEqual(M.pending_count(U), 0)
        self.assertIn("0.30", M.all_memories(U)[0]["text"])

    def test_근거를_LLM에_준다(self):
        seen = {}

        def fake(msgs, mt=0):
            seen["sys"] = msgs[0]["content"]
            seen["user"] = msgs[1]["content"]
            return "[]", ""

        M.extract_once(fake)
        self.assertIn("결정", seen["sys"])
        self.assertIn("요약", seen["sys"])          # 요약은 기억이 아니라는 지시
        self.assertIn("임계값", seen["user"])

    def test_건질_게_없어도_큐를_비운다(self):
        """★못 뽑은 조각을 남겨 두면 매번 다시 부른다 — 돈과 시간이 샌다."""
        out = M.extract_once(lambda msgs, mt=0: ("[]", ""))
        self.assertEqual(out["got"], 0)
        self.assertEqual(M.pending_count(U), 0)

    def test_LLM이_죽으면_다시_시도한다(self):
        out = M.extract_once(lambda msgs, mt=0: ("", "API 500"))
        self.assertEqual(out["tries"], 1)
        self.assertEqual(M.pending_count(U), 1)

    def test_계속_죽으면_포기하고_넘어간다(self):
        """★큐 맨 앞에 박혀 있으면 뒤가 영영 안 돈다."""
        for _ in range(3):
            M.extract_once(lambda msgs, mt=0: ("", "API 500"))
        self.assertEqual(M.pending_count(U), 0)

    def test_예외가_나도_큐가_안_막힌다(self):
        def boom(msgs, mt=0):
            raise RuntimeError("게이트웨이 끊김")
        self.assertIn("error", M.extract_once(boom))
        self.assertEqual(M.pending_count(U), 1)

    def test_큐가_비면_조용히_쉰다(self):
        M.extract_once(lambda msgs, mt=0: ("[]", ""))
        self.assertTrue(M.extract_once(lambda msgs, mt=0: ("[]", ""))["idle"])

    def test_한_바퀴에_여러_개를_처리한다(self):
        M.enqueue(U, "s2", [{"role": "user", "content": "리포트는 한국어로 쓰기로 했다. " * 3}])
        n = [0]

        def fake(msgs, mt=0):
            n[0] += 1
            return json.dumps([{"kind": "관례", "text": f"규칙 {n[0]} 을 지킨다"}],
                              ensure_ascii=False), ""

        r = M.tick(fake, per_tick=3)
        self.assertEqual(r["extracted"], 2)
        self.assertEqual(M.pending_count(U), 0)


class 언제_담나(Base):
    """★처음엔 '컨텍스트가 넘쳐 잘릴 때' 만 담았다. API 모델은 128K 라 그런
    일이 거의 없다 — 하루 종일 얘기해도 기억이 한 줄도 안 쌓인다."""

    def turns(self, n):
        return [{"role": "user" if i % 2 == 0 else "assistant",
                 "content": f"임계값 관련 이야기 {i} 번째입니다. 꽤 긴 내용이 이어집니다."}
                for i in range(n)]

    def test_짧은_대화는_안_담는다(self):
        """★조금씩 자주 담으면 LLM 호출만 늘고 건질 건 없다.
        꼬리를 뺀 나머지가 CAPTURE_EVERY 만큼 쌓여야 한 번 담는다."""
        self.assertEqual(M.capture_if_long(U, "s1", self.turns(4)), 0)
        # 꼬리 빼면 3개 — 아직 문턱(6) 미만이다
        self.assertEqual(M.capture_if_long(U, "s1", self.turns(7)), 0)
        self.assertEqual(M.pending_count(U), 0)

    def test_길어지면_넘치기_전에도_담는다(self):
        n = M.capture_if_long(U, "s1", self.turns(12))
        self.assertGreater(n, 0)
        self.assertEqual(M.pending_count(U), 1)

    def test_최근_몇_개는_남겨_둔다(self):
        """아직 살아 있는 얘기다 — 지금 대화에 그대로 있다."""
        self.assertEqual(M.capture_if_long(U, "s1", self.turns(12)),
                         12 - M.KEEP_TAIL)

    def test_같은_대화를_두_번_안_담는다(self):
        """★매 턴 다시 담으면 큐가 같은 내용으로 차고 LLM 값이 그만큼 나간다."""
        msgs = self.turns(12)
        M.capture_if_long(U, "s1", msgs)
        self.assertEqual(M.capture_if_long(U, "s1", msgs), 0)
        self.assertEqual(M.pending_count(U), 1)

    def test_더_길어지면_이어서_담는다(self):
        M.capture_if_long(U, "s1", self.turns(12))
        self.assertGreater(M.capture_if_long(U, "s1", self.turns(24)), 0)
        self.assertEqual(M.pending_count(U), 2)

    def test_대화가_다르면_따로_센다(self):
        M.capture_if_long(U, "s1", self.turns(12))
        self.assertGreater(M.capture_if_long(U, "s2", self.turns(12)), 0)

    def test_user_id_가_없으면_아무것도_안_한다(self):
        """★로그인 안 한 요청까지 담으면 남의 기억이 섞인다."""
        self.assertEqual(M.capture_if_long("", "s1", self.turns(12)), 0)
        self.assertEqual(M.pending_count(), 0)

    def test_담아도_대화에서_빼지_않는다(self):
        """이건 '복사해 두기' 지 '자르기' 가 아니다."""
        msgs = self.turns(12)
        before = len(msgs)
        M.capture_if_long(U, "s1", msgs)
        self.assertEqual(len(msgs), before)
