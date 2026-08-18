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
#
# ★'엑셀 파일 정리해줘' 의 정답에 file-organizer 도 넣어 뒀다. 처음엔 xlsx
#   하나만 정답으로 박아 놓고 라우터를 그쪽으로 끌어당겼는데, 질의를 다시
#   읽어 보면 "파일 정리해줘" 다 — file-organizer 가 틀린 답이 아니다.
#   내가 정한 답에 맞추려고 라우터를 비트는 건 점수 조작이지 개선이 아니다.
CASES: list[tuple[str, tuple[str, ...]]] = [
    # 문서·파일
    ("엑셀 파일 정리해줘", ("xlsx", "file-organizer")),
    ("스프레드시트 만들어줘", ("xlsx",)),
    ("엑셀에 차트 넣어줘", ("xlsx",)),
    ("엑셀 피벗테이블", ("xlsx",)),
    ("워드 문서 만들어줘", ("docx",)),
    ("파워포인트 발표자료", ("pptx",)),
    ("pdf 합쳐줘", ("pdf",)),
    ("PDF 표 추출", ("pdf", "markitdown")),
    # 문헌
    ("논문 검색", ("openalex-database", "pubmed-database", "bgpt-paper-search")),
    # 생명정보
    ("단일세포 분석", ("scanpy", "anndata", "scvi-tools")),
    ("차등발현 유전자", ("pydeseq2",)),
    ("단백질 구조 예측", ("esm", "pdb-database", "boltz", "alphafold")),
    ("분자 도킹", ("diffdock", "rdkit", "autodock")),
    ("유전체 서열 정렬", ("scikit-bio", "biopython", "pysam")),
    # 데이터·통계
    ("통계 검정 해줘", ("statistical-analysis", "statsmodels", "scipy")),
    ("시계열 예측 모델", ("aeon", "timesfm-forecasting", "sktime", "prophet")),
    ("지도에 좌표 찍어줘", ("geopandas", "folium")),
]
MIN_TOP1 = 16       # 17개 중 (지금 17/17) — 이 아래로 떨어지면 회귀다
MIN_TOP3 = 17


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

    def test_붙여쓴_복합어_안쪽까지_본다(self):
        """'논문' 은 스킬에 '논문검색' 으로 붙여 적혀 있다.

        ★한국어는 낱말을 붙여 쓴다. 이걸 약한 '부분 일치' 로 세면, 흔해 빠진
          '검색' 한 낱말만 가진 범용 agent-search-specialist 가 pubmed 를
          이긴다. 실제로 그랬다. 복합어 조각은 제대로 된 근거로 세야 한다.
        """
        got = [m["name"] for m in self.route("논문 검색", limit=1)]
        self.assertTrue(
            got and got[0] in ("pubmed-database", "openalex-database",
                               "bgpt-paper-search"),
            f"범용 검색 에이전트가 논문 스킬을 눌렀다: {got}")

    def test_복합어_문서빈도로_IDF를_센다(self):
        """'단일세포' 의 희귀도를 낱말 단위로 세면 0건이 되어 IDF가 헛돈다.

        ★그러면 '분석' 만 남아 아무 분석 스킬이나 딸려 온다. 상위권이
          전부 단일세포 계열이어야 IDF 가 제대로 도는 것이다.
        """
        got = [m["name"] for m in self.route("단일세포 분석", limit=2)]
        self.assertEqual(got[0], "scanpy", got)
        self.assertIn(got[1], ("anndata", "scvi-tools", "squidpy", "scirpy"),
                      f"2순위가 단일세포와 무관하다: {got}")

    def test_같은_낱말을_두_번_세지_않는다(self):
        """'분석은' 은 조사를 떼면 '분석' 이다 — 둘 다 점수를 주면 부풀려진다.

        ★조사 붙은 형태와 뗀 형태가 **둘 다** 걸리는 설명으로 재야 한다.
          한쪽이 어차피 0점인 예제로 재면, 합산으로 되돌려 놔도 값이 같아
          시험이 통과해 버린다(그렇게 한 번 놓쳤다).
        """
        from harness.router import ToolRouter
        r = ToolRouter(__import__("harness_bridge").get_registry())
        r.route("warm up")
        desc = "x: 분석은, 분석 — 데이터를 다룬다"
        a = r._score_parts([{"분석"}], "x", desc)[0]
        b = r._score_parts([{"분석은"}], "x", desc)[0]
        both = r._score_parts([{"분석은", "분석"}], "x", desc)[0]
        self.assertGreater(min(a, b), 0, "예제가 애초에 안 걸린다 — 시험이 무의미하다")
        # 한 묶음이 내는 값은 '합' 이 아니라 '더 잘 맞는 하나'
        self.assertAlmostEqual(both, max(a, b), places=6,
                               msg=f"변형형을 두 번 셌다 (합 {a + b} / 나온 값 {both})")

    def test_없는_말은_빈_결과(self):
        self.assertEqual(self.route("zzqqxx없는말", limit=3), [])


if __name__ == "__main__":
    unittest.main()
