"""화면·CSV 에 나가는 글자 — 잘림과 누출.

  · LLM 판단이 문장 중간에서 뚝 끊겨 "…반송시간이 6.3분까지 올" 로 남았다
  · 일일 리포트 통계 폴백에 reason 원문(룰 코드·금지어)이 그대로 찍혔다
"""
import unittest

from . import util  # noqa: F401
from accuracy import clip

BANNED = ("R-A_sus", "R-C", "R-D(", "역증가", "역방향", "hot_area=", "S3확정")


class Clip(unittest.TestCase):
    LONG = ("M16HUB STB 저장율 99.4%로 포화되어 리프터 반출이 막혔고, "
            "반송시간이 6.3분(기준 9분)까지 올라 정체가 시작됐습니다. "
            "상류 M14 로도 번질 조짐이 보입니다.")

    def test_짧으면_그대로(self):
        self.assertEqual(clip("정상 운영입니다.", 200), "정상 운영입니다.")

    def test_한도_안이면_안_자른다(self):
        self.assertEqual(clip(self.LONG, 260), self.LONG)

    def test_문장_경계에서_자른다(self):
        """★말이 중간에 끊기면 안 된다."""
        out = clip(self.LONG, 90)
        self.assertTrue(out.endswith("…"))
        self.assertTrue(out[:-1].rstrip().endswith("."), out)

    def test_문장이_안_끝나면_쉼표에서라도(self):
        out = clip(self.LONG, 40)
        self.assertTrue(out.endswith("…"))
        self.assertNotIn(",…", out)          # 쉼표는 떼고 … 를 붙인다

    def test_리스트는_슬래시로_합친다(self):
        self.assertEqual(clip(["근거1", "근거2"], 100), "근거1 / 근거2")
        self.assertEqual(clip(["근거1", "", "  "], 100), "근거1")

    def test_줄바꿈_중복공백_정리(self):
        self.assertEqual(clip("가\n\n나   다", 100), "가 나 다")

    def test_빈_값(self):
        self.assertEqual(clip(None, 100), "")
        self.assertEqual(clip([], 100), "")


class DayReportLeak(unittest.TestCase):
    """일일 리포트에 reason 원문이 새면 안 된다 (LLM 없이 통계만으로도)."""

    def test_통계_폴백_본문에_룰_코드가_없다(self):
        from lp_client import load_config
        import report
        cfg = load_config()
        cfg.setdefault("llm", {})["enabled"] = False
        try:
            r = report.build_day_report("20260728", cfg, use_llm=False)
        except Exception as e:                       # 샘플 CSV 없는 배포본
            self.skipTest(f"리포트 생성 불가: {e}")
        body = r.get("body") or ""
        if not body:
            self.skipTest("본문 없음")
        hits = [w for w in BANNED if w in body]
        self.assertEqual(hits, [], f"원문 누출: {hits}")

    def test_사건목록에_한글_요약이_붙는다(self):
        """reason 원문은 그래프용으로 남기되, 사람이 보는 줄은 reason_kr."""
        from lp_client import load_config
        from daily import day_material
        from sentinel import summarize_reason
        cfg = load_config()
        try:
            mat = day_material("20260728", cfg)
        except Exception as e:
            self.skipTest(f"자료 없음: {e}")
        for row in (mat.get("incidents") or []):
            raw = row.get("발동사유") or ""
            if raw:
                kr = summarize_reason(raw, row.get("시작영역", ""))
                self.assertTrue(kr)
                self.assertEqual([w for w in BANNED if w in kr], [])


if __name__ == "__main__":
    unittest.main()


class GlossaryScrub(unittest.TestCase):
    """페르소나 §용어 표준 — LLM 이 어겨도 화면에는 표준 표현만 나간다.

    ★'역방향'·'카운트' 는 어디에도 노출 금지(페르소나 규칙 4). 그 외에도
      적체→정체, 저장공간→Storage, 허브룸→HUBROOM, 큐→Queue, 짐→Carrier,
      반송카→OHT, 진원지→시작 영역, 감독관→에이전트 로 바꾼다.
    """

    BAN = ("역방향", "카운트", "역증가", "적체", "리프터막힘", "허브룸",
           "저장공간", "저장율", "포화", "만석", "치솟", "급증", "반송카",
           "진원지", "감독관", "물류")

    def test_금지어가_결과에_남지_않는다(self):
        from llm_client import scrub
        for src in ("3F 리프터 역방향 카운트 증가로 적체가 발생, 큐가 밀림",
                    "M16 허브룸 저장공간이 100% 포화, 짐이 쌓임",
                    "저장율 급증으로 물류 정체가 치솟았습니다",
                    "감독관 의견: 반송카 지연, 진원지는 HUBROOM"):
            out = scrub(src)
            for w in self.BAN:
                self.assertNotIn(w, out, f"{src!r} → {out!r} 에 '{w}' 남음")

    def test_조사가_깨지지_않는다(self):
        """저장공간이 → Storage가 / 진원지는 → 시작 영역은."""
        from llm_client import scrub
        self.assertIn("Storage가", scrub("저장공간이 부족"))
        self.assertIn("시작 영역은", scrub("진원지는 M16HUB"))
        self.assertIn("Carrier를", scrub("짐을 못 내림"))
        self.assertIn("Queue가", scrub("큐가 밀림"))

    def test_컬럼명과_일반어는_안_건드린다(self):
        """raw 컬럼은 그대로 보여야 하고('실제지표' 칸), 엉뚱한 말도 안 깨야."""
        from llm_client import scrub
        for keep in ("M16HUB.QUE.LFT.3F_LFT_REVERSALCNT",
                     "짐작건대 Queue 누적",
                     "디스크큐 사용률"):
            self.assertEqual(scrub(keep), keep)

    def test_룰명이_새_표준이다(self):
        from sentinel import summarize_reason
        out = summarize_reason("발동: M16HUB[R-C,R-D]; M16A[SORT]", "M16HUB")
        self.assertIn("리프터 정체", out)
        self.assertNotIn("리프터막힘", out)
        self.assertIn("분류기 대기",
                      summarize_reason("발동: M16A[SORT]", "M16A"))
