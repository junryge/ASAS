"""데모스 컨텍스트 보호 — 한글을 절반으로 세고 있었다.

demos_v1/routes_chat.py 의 _make_token_counter 설명은 "과소평가 절대 금지"
인데, 정작 API 경로(tpc=0.5)에서 한글을 글자당 0.5토큰으로 셌다.
한글은 한 글자가 대략 한 토큰이다 — 두 배로 과소평가한 것이다.

닿는 구간이 실제로 있었다. 16k 스파크 모델 기준:

    입력 예산 = 16,384 − 답변 4,096 − 여유 1,024 = 11,264 토큰

    한글 16,000자 → 추정 8,000  (예산 안) / 실제 16,000 → ❌ 넘침
    한글 22,000자 → 추정 11,000 (예산 안) / 실제 22,000 → ❌ 넘침

추정이 "괜찮다" 고 해서 트림을 안 하는데 실제로는 넘어가, 업스트림이 400 을
뱉는다. 128k 모델에서는 잘 안 닿아서 안 드러났다 — 집에서 GGUF 쓸 때나
스파크 모델 고를 때 터진다.
"""
from __future__ import annotations

import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _counter(tpc):
    from demos_v1.routes_chat import _make_token_counter
    return _make_token_counter(model=None, tpc=tpc)


class KoreanTokenCount(unittest.TestCase):
    def test_한글을_절반으로_세지_않는다(self):
        """★핵심 회귀. 한글 N자를 0.5N 토큰으로 세면 안 된다."""
        n = 8000
        got = _counter(0.5)("한" * n)
        self.assertGreaterEqual(
            got, n * 0.9,
            f"한글 {n:,}자를 {got:,} 토큰으로 셌다 — 절반으로 과소평가")

    def test_영문은_예전대로_현실적으로_센다(self):
        """★한글 때문에 영문까지 부풀리면 멀쩡한 텍스트를 헛되이 자른다."""
        n = 8000
        got = _counter(0.5)("a" * n)
        self.assertLessEqual(got, n * 0.7, f"영문 {n:,}자를 {got:,} 토큰 — 과대평가")

    def test_섞인_글도_한글_몫을_제대로_센다(self):
        c = _counter(0.5)
        mixed = ("한글" + "abcd") * 1000        # 한글 2000자 + 영문 4000자
        self.assertGreaterEqual(c(mixed), 2000 * 0.9)

    def test_gguf_설정은_동작이_그대로다(self):
        """★tpc=2.6 은 이미 1.0 보다 크다 — 건드리면 안 된다."""
        n = 1000
        c = _counter(2.6)
        self.assertGreaterEqual(c("한" * n), n * 2.6)
        self.assertGreaterEqual(c("a" * n), n * 2.6)

    def test_빈_문자열(self):
        self.assertLessEqual(_counter(0.5)(""), 1)


class FitTrimsKorean(unittest.TestCase):
    """추정만 고쳐도 소용없다 — 실제로 트림이 일어나야 한다."""

    def test_한글_대화가_16k_모델_예산_안으로_들어온다(self):
        from demos_v1.routes_chat import _fit_messages_to_ctx, _make_token_counter
        ctx, reply, safety = 16384, 4096, 1024
        msgs = [
            {"role": "system", "content": "너는 도우미다."},
            {"role": "user", "content": "한글 문장입니다. " * 1200},   # ≈12,000자
        ]
        fitted, reply_budget, _warn = _fit_messages_to_ctx(
            msgs, ctx, reply, model=None, safety=safety,
            hard_char_cap=False, tpc=0.5)
        count = _make_token_counter(None, 0.5)
        used = sum(count(str(m.get("content") or "")) + 8 for m in fitted) + 16
        self.assertLessEqual(
            used + reply_budget + safety, ctx,
            f"트림 후에도 넘친다: 입력 {used:,} + 답변 {reply_budget:,}")

    def test_짧은_한글은_안_자른다(self):
        """★넘치지도 않는데 자르면 대화가 망가진다."""
        from demos_v1.routes_chat import _fit_messages_to_ctx
        msgs = [{"role": "user", "content": "안녕하세요, 오늘 반송 정체 상황 알려줘"}]
        fitted, _rb, warn = _fit_messages_to_ctx(
            msgs, 128000, 8192, model=None, safety=1024,
            hard_char_cap=False, tpc=0.5)
        self.assertEqual(fitted[0]["content"], msgs[0]["content"])
        self.assertEqual(warn, "")


if __name__ == "__main__":
    unittest.main()
