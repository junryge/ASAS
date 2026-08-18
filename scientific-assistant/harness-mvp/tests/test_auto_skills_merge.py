"""자동 스킬 추천의 병합 순서 — 라우터가 맞혀도 여기서 뒤집히면 소용없다.

/api/auto-skills 는 네 군데서 후보를 모은다. 그런데 점수 척도가 서로 달랐다:

    옛 키워드 매칭  = 맞은 글자 수        ('임계값' → 3점)
    하네스 라우터   = IDF 가중 점수        (보통 10~35점)
    Expert Pool    = 관련도 + 2
    조합 추천      = 1

이걸 한 줄에 놓고 정렬하니, 하네스가 **2순위**로 얹은 스킬이 키워드
**1순위**를 눌렀다. 실제로 이렇게 나왔다:

    '임계값 어떻게 조정해'    → brainstorming, m16-hub-thresholds, ...
    '발동이벤트 결과 해석해줘' → shap, m16-hub-interpret, ...

라우터를 17/17 로 맞춰 놔도 사용자가 보는 건 이 순서다. 출처마다 그 안에서의
상대값(0~100)으로 바꿔 놓고 합치도록 고쳤고, 이 파일이 그걸 지킨다.
"""
from __future__ import annotations

import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# 질의 → 1위여야 하는 스킬 후보
TOP1_CASES = [
    ("M16 허브룸 반송 정체 분석해줘", ("m16-hub-overview", "m16-hub-interpret")),
    ("임계값 어떻게 조정해", ("m16-hub-thresholds",)),
    ("발동이벤트 결과 해석해줘", ("m16-hub-interpret",)),
    ("엑셀 피벗테이블 만들어줘", ("xlsx",)),
    ("단일세포 분석해줘", ("scanpy",)),
    ("논문 검색해줘", ("pubmed-database", "openalex-database", "bgpt-paper-search")),
    ("pdf 합쳐줘", ("pdf",)),
    ("워드 문서 만들어줘", ("docx",)),
    ("통계 검정 해줘", ("statistical-analysis", "statsmodels", "scipy")),
]


class AutoSkillsMerge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import demos_v1
            cls.client = demos_v1.create_app().test_client()
        except Exception as e:
            raise unittest.SkipTest(f"데모스 앱을 못 띄운다: {e}")

    def _ask(self, q):
        r = self.client.post("/api/auto-skills", json={"query": q})
        self.assertEqual(r.status_code, 200, q)
        return [(s["id"], s["score"]) for s in r.get_json().get("skills", [])]

    def test_1위가_맞다(self):
        bad = []
        for q, want in TOP1_CASES:
            got = self._ask(q)
            if not got or got[0][0] not in want:
                bad.append(f"{q} → {[g[0] for g in got]} (기대 {want})")
        self.assertEqual(bad, [], "\n  " + "\n  ".join(bad))

    def test_점수가_내림차순이다(self):
        for q, _ in TOP1_CASES:
            scores = [s for _, s in self._ask(q)]
            self.assertEqual(scores, sorted(scores, reverse=True), q)

    def test_보조_신호가_본_매칭을_못_이긴다(self):
        """Expert Pool·조합 추천은 거들 뿐이다 — 1위를 뺏으면 안 된다.

        ★boosted 로만 올라온 스킬이 1위면, 그건 병합 척도가 또 어긋난 것이다.
        """
        for q, want in TOP1_CASES:
            r = self.client.post("/api/auto-skills", json={"query": q})
            skills = r.get_json().get("skills", [])
            if not skills:
                continue
            top = skills[0]
            self.assertIn(top["id"], want,
                          f"{q}: 1위가 {top['id']} (boosted={top.get('boosted')})")

    def test_점수_척도가_한_가지다(self):
        """옛 척도(글자 수, 한 자릿수)가 그대로 섞여 나오면 안 된다."""
        for q, _ in TOP1_CASES:
            got = self._ask(q)
            if got:
                self.assertGreater(
                    got[0][1], 50,
                    f"{q}: 1위 점수가 {got[0][1]} — 옛 척도가 섞였다")


if __name__ == "__main__":
    unittest.main()
