# -*- coding: utf-8 -*-
"""최종 리포트 대신 '검토 메모' 가 나오던 것.

30분 구간을 분석하면 '## 종합 판정' 자리에 보고서가 아니라

    사용자의 요청은 … 주요 제약 사항과 규칙을 다시 한번 확인합니다.
    1. 출력 언어: … 9. 최종 점검: *자기수정*: 페르소나 규칙과 제공된
    판정 기준이 상충할 수 있음 …

같은 작성 계획이 그대로 실려 나왔다. 1시간·하루는 멀쩡했다.

왜 짧은 구간에서만 그런가
    긴 구간에는 쓸 사건이 있어 바로 본문으로 들어간다. 조용한 21분에는
    사건이 0건이라 **정할 게 등급뿐**인데, 페르소나에 60/71/85 표가 박혀
    있고 프롬프트는 시스템 컷(예: 48)을 준다. 두 기준이 달라 보이니
    어느 쪽을 따를지 따지다가 출력을 다 써 버린다.

두 군데를 막는다
    · 애초에 안 따지게 — 시스템 컷을 시스템 프롬프트에 못박고 '비교하지
      마라' 고 끝내 준다
    · 그래도 나오면 — 검토 메모를 알아보고 다시 묻는다. 두 번 다 그러면
      숫자만 채운 골격으로 간다 (메모를 리포트라고 내보내지 않는다)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analysis                                             # noqa: E402
from llm_client import _grade_rule, build_system_prompt      # noqa: E402
from lp_client import load_config, sys_cfg                   # noqa: E402

# 사용자가 실제로 받은 출력 (앞부분)
MEMO = """사용자의 요청은 제공된 분석 재료를 바탕으로 '관제 통합 리포트'를 작성하는 것입니다.
주요 제약 사항과 규칙을 다시 한번 확인합니다.
1. 출력 언어: 반드시 한국어. 영어 문장 금지.
2. 추론 과정 출력 금지: 'Thinking Process' 등을 쓰지 말고 요구된 형식만 출력.
* 등급 이모지 사용. 단, 제공된 판정 기준이 다름 (48점 임계). 적용해야 할지 확인 필요.
* 중요: 페르소나 규칙과 제공된 데이터의 판정 기준이 상충할 수 있음.
5. 작성 전략: 종합 판정은 전체 점수가 임계 미만이나 …
6. 용어 교정: 정체 → 정체
9. 최종 점검: *자기수정*: 페르소나 규칙에 "등급은 항상 이모지로" 라고 되어 있고 …"""

REPORT = """## 종합 판정
최고 36점(🟢 정상)으로 임계 48점을 넘은 구간은 없었습니다.
## 구역 상황
M14 가 09:50 부터 올라와 10:02 에 M16HUB 로 이어졌습니다.
## 조치
- STB 사용률 98% 이상 지속 시 용량 확보 검토
## 주의
- Storage FULL 과 리프터 정체의 인과는 아직 '의심' 입니다."""


class 검토_메모를_알아본다(unittest.TestCase):

    def test_사용자가_받은_그_출력을_잡는다(self):
        self.assertTrue(analysis._looks_like_plan(MEMO))

    def test_제대로_된_리포트는_안_잡는다(self):
        self.assertFalse(analysis._looks_like_plan(REPORT))

    def test_짧아도_네_섹션이면_리포트다(self):
        """사건 0건이면 리포트가 원래 짧다. 길이로 자르면 안 된다."""
        short = ("## 종합 판정\n최고 36점. 이벤트 없음.\n## 구역 상황\n조용했습니다.\n"
                 "## 조치\n- 없음\n## 주의\n- 없음")
        self.assertFalse(analysis._looks_like_plan(short))

    def test_본문에_그_낱말이_있어도_섹션이_있으면_통과(self):
        """'확인 필요'·'상충' 은 본문에도 쓸 수 있는 말이다. 낱말만 보면
        멀쩡한 리포트를 버린다."""
        body = REPORT + "\n- 두 지표가 상충하는 부분은 추가 확인 필요합니다."
        self.assertFalse(analysis._looks_like_plan(body))

    def test_빈_값은_계획이_아니다(self):
        for x in ("", "   ", None):
            self.assertFalse(analysis._looks_like_plan(x))

    def test_다시_물을_때_붙이는_말이_짧고_분명하다(self):
        hard = analysis._FINAL_HARD
        self.assertIn("검토 메모", hard)
        self.assertIn("따지지 말고", hard)
        self.assertIn("## 종합 판정", hard)
        self.assertLess(len(hard), 400)         # 길면 그것대로 또 읽고 앉아 있다


class 등급_기준을_시스템_값으로_못박는다(unittest.TestCase):
    """페르소나의 60/71/85 와 정책 탭의 컷이 다르면 모델이 '어느 쪽이냐'
    를 따지느라 답을 안 쓴다. 미리 끝내 준다."""

    def test_이_시스템_컷이_들어간다(self):
        from sentinel import alarm_floor, grade_cuts
        cfg = sys_cfg(load_config(), "M14")
        w, d, c = grade_cuts(cfg)
        rule = _grade_rule(cfg)
        self.assertIn(f"🟠 경계 {w}~{d-1}", rule)
        self.assertIn(f"🔴 위험 {d}~{c-1}", rule)
        self.assertIn(f"⛔ 초위험 {c}~100", rule)
        self.assertIn(f"알람 임계 {alarm_floor(cfg)}점", rule)

    def test_따지지_말라고_적는다(self):
        rule = _grade_rule(sys_cfg(load_config(), "ALL"))
        self.assertIn("이 줄을 따른다", rule)
        self.assertIn("비교하거나", rule)
        self.assertIn("그 과정을 답에 쓰면 안 된다", rule)

    def test_시스템_프롬프트_맨_뒤에_붙는다(self):
        """앞에 두면 뒤에 오는 페르소나 표에 덮인다."""
        p = build_system_prompt(sys_cfg(load_config(), "ALL"))
        self.assertTrue(p.rstrip().endswith("위 숫자로 넣는다."))

    def test_컷을_못_읽어도_프롬프트는_나온다(self):
        """등급 기준 한 줄 때문에 분석 전체가 죽으면 안 된다."""
        self.assertEqual(_grade_rule({"grade": "망가진 값"}), "")


class 말하다_잘린_리포트(unittest.TestCase):
    """'## 주의' 항목이 "…경계를 초과하는 패턴이 이어질 경우, 추" 에서
    끊긴 채로 화면에 나갔다. 본문이 나왔으므로 반환값만으로는 성공과
    구분이 안 된다 — finish_reason="length" 가 그 신호다."""

    FULL = ("최고 36점(🟢 정상)입니다.\n## 구역 상황\nM14 가 올라왔습니다.\n"
            "## 조치\n- 모니터링\n## 주의\n- 추이를 지켜봅니다.")
    CUT = ("최고 36점(🟢 정상)입니다.\n## 구역 상황\nM14 가 올라왔습니다.\n"
           "## 조치\n- 모니터링\n## 주의\n- 반복되는 패턴이 이어질 경우, 추")

    def _run(self, calls):
        """calls = [(돌려줄 본문, finish_reason), …] — 부른 순서대로."""
        import llm_client
        seen = []
        it = iter(calls)

        def fake(messages, cfg=None, max_tokens=None, meta=None, **kw):
            body, fin = next(it)
            seen.append({"max_tokens": max_tokens,
                         "user": messages[-1]["content"]})
            if meta is not None:
                meta["finish_reason"] = fin
            return body, None

        old = llm_client.chat
        llm_client.chat = fake
        try:
            out = analysis._stage_final("[전체 통계] …", [], None, None,
                                        load_config())
        finally:
            llm_client.chat = old
        return out, seen

    def test_안_잘렸으면_한_번만_부른다(self):
        (body, note, _t, _m), seen = self._run([(self.FULL, "stop")])
        self.assertEqual(len(seen), 1)
        self.assertIn("## 주의", body)
        self.assertNotIn("잘렸", str(note or ""))

    def test_잘리면_토큰을_올려_다시_묻는다(self):
        (body, _n, _t, _m), seen = self._run(
            [(self.CUT, "length"), (self.FULL, "stop")])
        self.assertEqual(len(seen), 2)
        self.assertGreater(seen[1]["max_tokens"], seen[0]["max_tokens"])
        self.assertIn("짧게", seen[1]["user"])          # 짧게 쓰라고 같이 부탁
        self.assertIn("추이를 지켜봅니다", body)         # 두 번째(완성본)를 쓴다

    def test_두_번_다_잘리면_긴_쪽을_쓰고_밝힌다(self):
        short = "최고 36점입니다.\n## 구역 상황\nM14"
        (body, note, _t, _m), seen = self._run(
            [(self.CUT, "length"), (short, "length")])
        self.assertEqual(len(seen), 2)
        self.assertIn("반복되는 패턴", body)            # 더 많이 쓴 쪽
        self.assertIn("잘렸을 수 있습니다", str(note))   # 숨기지 않는다

    def test_애초에_분량을_정해_준다(self):
        _out, seen = self._run([(self.FULL, "stop")])
        self.assertIn("'## 주의' 까지 다 쓰고 끝내라", seen[0]["user"])


class 안_쓰는_말(unittest.TestCase):

    def test_국지적을_지운다(self):
        from llm_client import scrub
        for a, b in (("M14 에서 국지적인 부하 상승이 발생", "M14 에서 부하 상승이 발생"),
                     ("M14 국지적 부하: 정상", "M14 부하: 정상"),
                     ("국지적으로 점수가 올랐습니다", "점수가 올랐습니다"),
                     ("구역의 국지적 부하 상승", "구역의 부하 상승")):
            self.assertEqual(scrub(a), b)

    def test_지우고_나서_이상한_말이_안_남는다(self):
        from llm_client import scrub
        for t in ("국지적인 부하", "국지적 부하", "국지적으로 상승"):
            self.assertNotIn("국지", scrub(t))
            self.assertFalse(scrub(t).startswith(("인 ", "으로 ", "이 ")))


if __name__ == "__main__":
    unittest.main()
