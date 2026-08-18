"""컨텍스트 예산 — 넘치면 API 는 거절하고 GGUF 는 죽는다.

무엇이 이상했나
    ① 스킬 예산을 DEFAULT_N_CTX 로 계산하는데 그 값이 **4096** 이었다.
       128,000 토큰 모델을 골라도 스킬은 늘 2,000자. 모델을 뭘 고르든
       상관이 없었다.
    ② **아무도 합계를 안 봤다.** 스킬·지식·첨부가 각자 제 상한만 지켰다:

         spark-gemma4-12b (16k):  입력 12,858 + 답변 16,384 = 29,242 ❌
         spark-qwen36-35b (32k):  입력 21,050 + 답변 16,384 = 37,434 ❌

    ③ 이력을 '최근 12턴' 으로 잘랐다. 코드가 붙은 12턴과 인사말 12턴은
       크기가 백 배 다르다.

★이 파일의 제일 중요한 시험은 '어떤 조합을 넣어도 한도를 안 넘는다' 다.
  회사는 API(128k), 집은 GGUF(작고, 넘기면 크래시) — 양쪽 다 재야 한다.
"""
from __future__ import annotations

import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from code_assist_v1 import ctxbudget as cb        # noqa: E402

# 실제로 쓰는 모델들의 컨텍스트 (api_config.json 기준)
CTXS = [4096, 8192, 16384, 32768, 128000]


class Estimate(unittest.TestCase):
    def test_한글이_영문보다_토큰을_많이_먹는다(self):
        """★한 글자당 하나로 뭉뚱그리면 한쪽이 크게 틀린다."""
        ko = cb.est_tokens("가" * 100)
        en = cb.est_tokens("a" * 100)
        self.assertGreater(ko, en)

    def test_빈_문자열은_0(self):
        self.assertEqual(cb.est_tokens(""), 0)

    def test_실제보다_적게_잡지_않는다(self):
        """★적게 잡으면 넘긴 채로 보낸다 — 많이 잡는 쪽이 안전하다.

        한글은 대략 글자당 1토큰 언저리다. 그보다 낮게 어림하면 안 된다.
        """
        n = 500
        self.assertGreaterEqual(cb.est_tokens("가" * n), n * 0.6)


class Plan(unittest.TestCase):
    def test_어떤_모델이든_한도를_안_넘는다(self):
        """★제일 중요한 시험."""
        for ctx in CTXS:
            for reply in (1024, 4096, 8192, 16384):
                for sysx in (200, 2000, 8000):
                    b = cb.plan(ctx, reply, sysx)
                    if b.system_overflow:
                        # 시스템 프롬프트만으로 이미 넘는 경우 — 예산으로는
                        # 못 고친다. 대신 반드시 표시돼야 하고(아래 시험),
                        # 나머지는 0 이어야 한다.
                        self.assertEqual(
                            (b.skills, b.knowledge, b.workspace, b.history),
                            (0, 0, 0, 0),
                            f"넘치는데도 자리를 나눠 줬다 ctx={ctx} sys={sysx}")
                        continue
                    self.assertTrue(
                        b.fits(),
                        f"ctx={ctx} reply={reply} sys={sysx} → "
                        f"입력 {b.input_total} + 답변 {b.reply} + 여유 {b.safety} "
                        f"> {ctx}")

    def test_시스템_프롬프트만으로_넘치면_알려_준다(self):
        """★조용히 넘기면 API 400 / GGUF 크래시로 튄다.

        예산으로 못 고치는 상황이니, 최소한 '못 고친다' 고 말해야
        부르는 쪽이 프롬프트를 줄이든 모델을 바꾸든 한다.
        """
        b = cb.plan(4096, 1024, 8000)
        self.assertTrue(b.system_overflow, b.to_json())
        self.assertFalse(b.fits())

    def test_들어가는_경우엔_넘침_표시가_없다(self):
        self.assertFalse(cb.plan(128000, 8192, 2000).system_overflow)

    def test_큰_모델이_더_많이_받는다(self):
        small = cb.plan(16384, 4096, 500)
        big = cb.plan(128000, 4096, 500)
        self.assertGreater(big.workspace, small.workspace * 4)
        self.assertGreater(big.skills, small.skills)

    def test_답변_자리를_먼저_지킨다(self):
        """★입력으로 꽉 채우면 모델이 답을 쓸 자리가 없다."""
        b = cb.plan(16384, 8192, 500)
        self.assertGreaterEqual(b.reply, 512)
        self.assertLessEqual(b.reply, int(16384 * 0.4) + 1)

    def test_안_쓰는_칸의_몫을_돌려_준다(self):
        """지식·스킬을 안 쓰면 그 자리는 첨부가 가져가야 한다."""
        with_all = cb.plan(32768, 4096, 500)
        ws_only = cb.plan(32768, 4096, 500,
                          want_skills=False, want_knowledge=False)
        self.assertGreater(ws_only.workspace, with_all.workspace)
        self.assertEqual(ws_only.skills, 0)
        self.assertEqual(ws_only.knowledge, 0)

    def test_아주_좁아도_안_죽는다(self):
        """시스템 프롬프트가 컨텍스트를 거의 다 먹는 극단 — 죽지는 않는다."""
        b = cb.plan(4096, 4096, 3800)
        self.assertGreaterEqual(b.reply, 256)
        self.assertTrue(b.system_overflow)      # 못 고치는 상황임을 표시
        b2 = cb.plan(4096, 4096, 1500)          # 이건 들어가야 한다
        self.assertTrue(b2.fits(), b2.to_json())

    def test_모델을_모르면_보수적으로(self):
        b = cb.plan(None, 4096, 500)
        self.assertTrue(b.fits())


class History(unittest.TestCase):
    def test_토큰으로_자른다(self):
        """★'최근 N턴' 이 아니다 — 큰 메시지 하나가 예산을 다 먹을 수 있다."""
        msgs = [{"role": "user", "content": "가" * 2000} for _ in range(10)]
        keep, dropped = cb.trim_history(msgs, 500)
        self.assertLess(len(keep), 10)
        self.assertEqual(dropped, 10 - len(keep))

    def test_마지막_질문은_반드시_남는다(self):
        """★그게 질문이다. 예산을 넘어도 버리면 안 된다."""
        msgs = [{"role": "user", "content": "가" * 5000}]
        keep, _ = cb.trim_history(msgs, 10)
        self.assertEqual(len(keep), 1)

    def test_최근_것부터_남긴다(self):
        msgs = [{"role": "user", "content": f"메시지{i}"} for i in range(20)]
        keep, _ = cb.trim_history(msgs, 60)
        self.assertEqual(keep[-1]["content"], "메시지19")

    def test_넉넉하면_다_남는다(self):
        msgs = [{"role": "user", "content": "짧다"} for _ in range(5)]
        keep, dropped = cb.trim_history(msgs, 100000)
        self.assertEqual((len(keep), dropped), (5, 0))

    def test_빈_이력(self):
        self.assertEqual(cb.trim_history([], 100), ([], 0))


class ResolveCtx(unittest.TestCase):
    def test_api는_설정값을_쓴다(self):
        self.assertEqual(cb.resolve_n_ctx({"n_ctx": 128000}, "api"), 128000)

    def test_api_필드명이_달라도_찾는다(self):
        self.assertEqual(cb.resolve_n_ctx({"context_window": 32768}, "api"), 32768)

    def test_gguf는_모르면_좁게_잡는다(self):
        """★GGUF 는 넘기면 크래시다 — 모르면 크게 잡으면 안 된다."""
        self.assertLessEqual(cb.resolve_n_ctx({}, "gguf"), 4096)

    def test_gguf는_실제_로드된_모델을_본다(self):
        """설정에 32768 이라 적혀 있어도 4096 으로 올라가 있으면 4096 이다."""
        import types
        fake = types.SimpleNamespace(n_ctx=lambda: 4096)
        mod = types.ModuleType("demos_v1.utils")
        mod.gguf_model = fake
        saved = sys.modules.get("demos_v1.utils")
        sys.modules["demos_v1.utils"] = mod
        try:
            self.assertEqual(cb.resolve_n_ctx({"n_ctx": 32768}, "gguf"), 4096)
        finally:
            if saved is not None:
                sys.modules["demos_v1.utils"] = saved
            else:
                del sys.modules["demos_v1.utils"]


class SkillBudget(unittest.TestCase):
    """★스킬 예산이 DEFAULT_N_CTX(=4096) 로 계산돼서, 128k 모델을 골라도
    늘 2,000자였다. 고른 모델이 뭐든 상관이 없었다."""

    def _build(self, budget_chars):
        from unittest.mock import patch
        import code_assist_v1.engine as eng
        with patch.object(eng, "load_skill_content",
                          lambda sid, max_chars=4000: "SKILLBODY" * 500):
            return eng.build_coding_system_prompt(
                skill_ids=["a", "b", "c"], skill_budget_chars=budget_chars)

    def test_예산이_크면_스킬이_더_들어간다(self):
        small = self._build(2000)
        big = self._build(30000)
        self.assertGreater(len(big), len(small) * 3,
                           f"예산을 15배 줬는데 {len(small)} → {len(big)} 밖에 안 늘었다")

    def test_예산을_지킨다(self):
        out = self._build(2500)
        self.assertLess(out.count("SKILLBODY") * 9, 2500 + 600)

    def test_모델_크기가_스킬_예산으로_이어진다(self):
        """plan() → build_coding_system_prompt 로 실제로 흘러가는지."""
        small = cb.plan(16384, 4096, 500)
        big = cb.plan(128000, 4096, 500)
        self.assertGreater(len(self._build(cb.est_chars(big.skills))),
                           len(self._build(cb.est_chars(small.skills))))


class EndToEnd(unittest.TestCase):
    """실제 조립 경로가 한도를 지키는지 — 예산표만 맞고 실물이 넘치면 소용없다."""

    def test_조립된_프롬프트가_한도_안에_있다(self):
        from code_assist_v1.engine import build_workspace_block, build_coding_system_prompt
        files = [{"filename": f"m{i}.py", "content": "x = 1\n" * 500}
                 for i in range(200)]
        for ctx in CTXS:
            sysx = build_coding_system_prompt(can_edit=True, n_ctx=ctx)
            b = cb.plan(ctx, 8192, cb.est_tokens(sysx), want_knowledge=False,
                        want_skills=False)
            ws = build_workspace_block(files, max_total=cb.est_chars(b.workspace))
            total = cb.est_tokens(sysx) + cb.est_tokens(ws["content"])
            self.assertLessEqual(
                total + b.reply + b.safety, ctx,
                f"ctx={ctx} 에서 조립 결과가 넘친다 (입력 {total} + 답변 {b.reply})")


if __name__ == "__main__":
    unittest.main()
