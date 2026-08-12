"""reason 한글 요약 + 실제지표 — 원문이 새어 나가면 실패.

실제로 화면에 이게 튀어나왔던 적이 있다:
    hot_area=M16HUB; S3확정; 발동: M16HUB[R-A'(AVGTOTALTIME1MIN=6.30분/기준9.0),
    R-A_sus,R-C'(역증가4개:6ABL6012,…),R-D(FAB저장=0.6%,STB=99.4%)…
룰 코드도, 스킬이 금지한 '역증가' 도 그대로였다. 원인은 두 겹이었다 —
① 요약기가 닫는 ']' 없는(잘린) 블록을 못 찾아 빈 문자열을 돌려줬고
② 호출부가 `summarize_reason(...) or raw_reason` 이라 원문으로 되돌아갔다.
"""
import unittest

from . import util  # noqa: F401  (import 경로 설정)
from sentinel import reason_metrics, summarize_reason

# 화면에 절대 나오면 안 되는 것들 — 룰 코드·영문 컬럼·금지어
BANNED = ("R-A", "R-B", "R-C", "R-D", "역증가", "역방향", "역류",
          "hot_area=", "AVGTOTALTIME", "S3확정", "6ABL", "STORAGE_UTIL")

CUT = ("hot_area=M16HUB; S3확정; 발동: M16HUB[R-A'(AVGTOTALTIME1MIN=6.30분/기준9.0),"
       "R-A_sus,R-C'(역증가4개:6ABL6012,6ABL6022,6ABL6032,6ABL0122),"
       "R-D(FAB저장=0.6%,STB=99.4%)")          # ← 닫는 ']' 가 없다 (실제로 이렇게 왔다)
FULL = "hot_area=M16HUB; S3확정; 발동: M16HUB[R-A_sus,R-C,R-D(STB=100.0%)]; M14[R-A_sus]"
MULTI = "hot_area=M14; 발동: M16HUB[R-C]; M14[R-A_sus,R-D]"
NOBRACKET = "hot_area=M16B; S2확정; 발동: R-A_sus R-D"
UNKNOWN = "hot_area=M16B; S3확정; 발동: M16B[R-Z'(신규룰:역증가3개)]"


class SummarizeReason(unittest.TestCase):
    def _no_leak(self, out):
        hits = [w for w in BANNED if w in out]
        self.assertEqual(hits, [], f"원문 누출: {hits} in {out!r}")

    def test_잘린_블록도_요약된다(self):
        """★이게 실제 장애였다. 닫는 ']' 가 없어도 룰을 읽어야 한다."""
        out = summarize_reason(CUT, "M16HUB")
        self.assertTrue(out.startswith("M16HUB "), out)
        self.assertIn("리프터막힘", out)
        self.assertIn("Storage FULL", out)
        self._no_leak(out)

    def test_정상_블록(self):
        out = summarize_reason(FULL, "M16HUB")
        self.assertIn("반송지연 지속", out)
        self.assertIn("리프터막힘", out)
        self._no_leak(out)

    def test_영역이_여러개면_hot_area_것을_고른다(self):
        out = summarize_reason(MULTI, "M14")
        self.assertTrue(out.startswith("M14 "), out)
        self.assertIn("반송지연 지속", out)
        self.assertIn("Storage FULL", out)
        self.assertNotIn("리프터막힘", out)     # 그건 M16HUB 블록 것
        self._no_leak(out)

    def test_대괄호가_아예_없어도_읽는다(self):
        out = summarize_reason(NOBRACKET, "M16B")
        self.assertIn("반송지연 지속", out)
        self._no_leak(out)

    def test_모르는_룰이면_원문_대신_한글로(self):
        """새 룰이 생겨도 원문을 뱉으면 안 된다 — 금지어가 그대로 나간다."""
        out = summarize_reason(UNKNOWN, "M16B")
        self.assertEqual(out, "M16B 이상 감지")
        self._no_leak(out)

    def test_빈_값은_빈_문자열(self):
        self.assertEqual(summarize_reason("", "M16HUB"), "")
        self.assertEqual(summarize_reason(None, ""), "")

    def test_저장된_CSV_전체에서_누출_0(self):
        from store_csv import read_day
        from lp_client import load_config
        cfg = load_config()
        rows = read_day("20260728", cfg) or []
        if not rows:
            self.skipTest("샘플 CSV 없음")
        for r in rows:
            raw = (r.get("reason") or "").strip()
            if raw:
                self._no_leak(summarize_reason(raw, (r.get("hot_area") or "").strip()))


class ReasonMetrics(unittest.TestCase):
    """한글 요약 옆 '실제지표' 칸 — 그 룰이 실제로 보는 raw 컬럼명."""

    def test_룰_코드만_와도_지표가_나온다(self):
        """예전엔 괄호 안 수치 문구가 있을 때만 지표를 붙여 통째로 비었다."""
        raws = [m["raw"] for m in reason_metrics(FULL, "M16HUB")]
        self.assertIn("M16HUB.QUE.TIME.AVGTOTALTIME1MIN", raws)
        self.assertIn("M16HUB.QUE.LFT.3F_LFT_REVERSALCNT", raws)
        self.assertIn("M16HUB.STRATE.STB.3F_STORAGE_UTIL", raws)

    def test_잘린_블록에서도_나온다(self):
        raws = [m["raw"] for m in reason_metrics(CUT, "M16HUB")]
        self.assertIn("M16HUB.QUE.TIME.AVGTOTALTIME1MIN", raws)
        self.assertIn("M16HUB.STRATE.ALL.FABSTORAGERATIO", raws)

    def test_영역별로_다른_컬럼(self):
        raws = [m["raw"] for m in reason_metrics(MULTI, "M14")]
        self.assertIn("M14.QUE.LOAD.AVGLOADTIME1MIN", raws)
        self.assertNotIn("M16HUB.QUE.TIME.AVGTOTALTIME1MIN", raws)

    def test_빈_값(self):
        self.assertEqual(reason_metrics("", "M16HUB"), [])


if __name__ == "__main__":
    unittest.main()
