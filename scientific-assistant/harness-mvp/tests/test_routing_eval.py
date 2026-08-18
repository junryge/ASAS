"""라우팅 정확도 평가 — 숫자로 재고, 나빠지면 실패한다.

왜 이게 필요한가
    스킬 389개 중 맞는 걸 고르는 게 하네스의 핵심 기능인데, 예전엔 '되는지'
    를 아무도 안 쟀다. 실제로 이런 상태였다:

      '엑셀 파일 정리해줘'  → agent-build-engineer, agent-performance-engineer
      '단일세포 분석'      → agent-architect-reviewer, agent-business-analyst

    원인 셋:
      ① description 이 "폴더명: 폴더명" 이었다 — SKILL.md 가 스스로 써 둔
         풍부한 설명(Agent Skills 규격의 1차 라우팅 신호)을 통째로 버렸다.
      ② 점수가 '맞은 토큰 개수' 였다 — '분석'(32개 스킬)과 '엑셀'(1개)이
         똑같이 1점. 흔한 말이 희귀한 말을 덮었다.
      ③ 동점이면 이름 알파벳순 — agent-* 가 늘 이겼다.

    고친 뒤 1위 적중 7/8. 이 파일이 그 수준을 지킨다.

★평가셋은 '정답이 하나' 가 아니다. '논문 검색' 은 pubmed 도 openalex 도
  맞다. 그래서 허용 목록으로 채점한다 — 억지 정답을 만들면 그 숫자는 거짓말이다.
"""
from __future__ import annotations

import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (_ROOT, os.path.join(_ROOT, "harness-mvp")):
    if p not in sys.path:
        sys.path.insert(0, p)

SKILLS_DIR = os.path.join(_ROOT, "scientific-skills")

# (질의, 정답 후보들) — 후보 중 하나라도 1위면 적중
CASES: list[tuple[str, tuple[str, ...]]] = [
    ("엑셀 파일 정리해줘", ("xlsx",)),
    ("스프레드시트 만들어줘", ("xlsx",)),
    ("엑셀에 차트 넣어줘", ("xlsx",)),
    ("워드 문서 만들어줘", ("docx",)),
    ("파워포인트 발표자료", ("pptx",)),
    ("pdf 합쳐줘", ("pdf",)),
    ("PDF 표 추출", ("pdf", "markitdown")),
    ("논문 검색", ("openalex-database", "pubmed-database", "bgpt-paper-search")),
    ("단일세포 분석", ("scanpy",)),
    ("차등발현 유전자", ("pydeseq2",)),
]
MIN_TOP1 = 8        # 10개 중 — 이 아래로 떨어지면 회귀다
MIN_TOP3 = 10


def _route():
    from demos_v1.skills import SKILL_KEYWORDS
    import harness_bridge as hb
    hb.init_harness(skills_dir=SKILLS_DIR, skill_keywords=SKILL_KEYWORDS)
    return hb.harness_route


@unittest.skipUnless(os.path.isdir(SKILLS_DIR), "scientific-skills 없음")
class RoutingAccuracy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.route = staticmethod(_route())
        except Exception as e:                       # demos 의존이 없는 환경
            raise unittest.SkipTest(f"하네스 초기화 불가: {e}")

    def _run(self):
        top1 = top3 = 0
        lines = []
        for q, want in CASES:
            got = [m["name"] for m in self.route(q, limit=3)]
            ok1 = bool(got) and got[0] in want
            ok3 = any(w in got for w in want)
            top1 += ok1
            top3 += ok3
            lines.append(f"  {'O' if ok1 else ('~' if ok3 else 'X')} {q} → {got}")
        return top1, top3, "\n".join(lines)

    def test_1위_적중률(self):
        top1, _t3, detail = self._run()
        self.assertGreaterEqual(
            top1, MIN_TOP1,
            f"\n1위 적중 {top1}/{len(CASES)} (기준 {MIN_TOP1})\n{detail}")

    def test_3위_안_적중률(self):
        _t1, top3, detail = self._run()
        self.assertGreaterEqual(
            top3, MIN_TOP3,
            f"\n3위 안 적중 {top3}/{len(CASES)} (기준 {MIN_TOP3})\n{detail}")

    def test_설명이_실제_내용이다(self):
        """★description 이 '폴더명: 폴더명' 이면 라우팅이 이름만 보고 한다."""
        import harness_bridge as hb
        items = hb.get_registry().list_all()
        thin = [t.name for t in items
                if len(t.description) < len(t.name) * 2 + 8]
        self.assertLess(len(thin), len(items) * 0.5,
                        f"설명이 비어 있다시피 한 스킬이 너무 많다: {thin[:8]}")
        x = next((t for t in items if t.name == "xlsx"), None)
        if x:
            self.assertIn("spreadsheet", x.description.lower(),
                          "SKILL.md 의 description 을 안 읽고 있다")

    def test_흔한_말이_희귀한_말을_못_덮는다(self):
        """'분석'(32개) 때문에 '단일세포'(3개) 가 밀리면 안 된다."""
        got = [m["name"] for m in self.route("단일세포 분석", limit=3)]
        self.assertEqual(got[:1], ["scanpy"], got)

    def test_없는_말은_빈_결과(self):
        self.assertEqual(self.route("zzqqxx없는말", limit=3), [])


if __name__ == "__main__":
    unittest.main()
