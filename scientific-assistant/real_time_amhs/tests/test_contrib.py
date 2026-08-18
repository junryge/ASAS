"""스코어 기여도 추정 — '왜 이 점수인가'.

★점수식을 푼 게 아니라 평소 대비 편차로 낸 **추정**이다. 그래서 눈금이
  깨지는 경우가 실제로 있었다 — 리프터 정체처럼 평소가 대부분 0 인 지표는
  MAD 가 정확히 0 이 되어 z 가 60억이 나왔고, 그 지표 하나가 100%를 먹었다.
"""
import random
import unittest
from datetime import datetime, timedelta

from . import util  # noqa: F401
import contrib as C
from lp_client import load_config

T0 = datetime(2026, 7, 28, 0, 0)
EV = range(200, 216)          # 사건 구간
REASON = "hot_area=M16HUB; S3확정; 발동: M16HUB[R-A_sus,R-C,R-D(STB=99%)]"


def make_rows(rev_quiet=0.0, stb_flat=False):
    """정상 284분 + 사건 16분. rev_quiet=0 이면 리프터 정체이 평소 전부 0."""
    rnd = random.Random(3)
    rows = []
    for i in range(300):
        ev = i in EV
        rows.append({
            "datetime": (T0 + timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M:%S"),
            "unified_risk_score": f"{80 if ev else rnd.uniform(10, 25):.1f}",
            "hot_area": "M16HUB",
            "reason": REASON if ev else "",
            "M16HUB_ra": f"{8.4 if ev else rnd.uniform(2.4, 3.0):.2f}",
            "M16HUB_stb_util": (f"{98.2:.2f}" if stb_flat else
                                f"{98.5 if ev else 97.9 + rnd.uniform(-.3, .3):.2f}"),
            "M16HUB_rev_count": f"{6 if ev else rev_quiet:.0f}",
            "M16HUB_rd_fab": f"{1.2 if ev else 1.15 + rnd.uniform(-.05, .05):.2f}",
            "M14_ra": f"{rnd.uniform(2.5, 2.9):.2f}",              # 무관한 지표
            "M16B_ra": f"{4.9 if ev else rnd.uniform(2.6, 3.0):.2f}",  # 튀지만 룰 미발동
        })
    return rows


class Contrib(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_config()

    def peak(self, rows=None):
        return C.explain(rows or make_rows(), T0 + timedelta(minutes=207), self.cfg)

    def test_합이_100_퍼센트(self):
        d = self.peak()
        self.assertTrue(d["ok"])
        self.assertTrue(d["items"])
        self.assertAlmostEqual(sum(i["pct"] for i in d["items"]), 100, delta=3)

    def test_MAD_0_인_지표가_100퍼센트를_먹지_않는다(self):
        """★실제로 z=6000000000 이 나와 리프터 정체이 100%를 차지했다."""
        d = self.peak()
        top = d["items"][0]
        self.assertLessEqual(top["pct"], 60, [(i["label"], i["pct"]) for i in d["items"]])
        for i in d["items"]:
            self.assertLessEqual(abs(i["z"]), 8.0 + 1e-9, i)

    def test_발동한_지표가_상위에_온다(self):
        d = self.peak()
        top3 = [i["label"] for i in d["items"][:3]]
        self.assertTrue(any("반송시간" in t and "M16HUB" in t for t in top3), top3)
        self.assertTrue(any("리프터 정체" in t for t in top3), top3)

    def test_룰이_안_뜬_지표는_가중치가_낮다(self):
        d = self.peak()
        by = {i["label"]: i for i in d["items"]}
        hub = by.get("M16HUB 반송시간")
        m16b = by.get("M16B 반송시간")
        if hub and m16b:                       # 둘 다 z 상한(8)에 걸려 있음
            self.assertGreater(hub["pct"], m16b["pct"])
            self.assertTrue(hub["fired"])
            self.assertFalse(m16b["fired"])

    def test_하루종일_높은_지표는_상시로_표시(self):
        """스파이크가 아니라 상시 포화 — 조치가 달라지므로 구분해야 한다."""
        d = self.peak(make_rows(stb_flat=True))
        stb = next((i for i in d["items"] if "STB" in i["label"]), None)
        self.assertIsNotNone(stb)
        self.assertTrue(stb["chronic"])
        self.assertTrue(stb["fired"])

    def test_정상_구간은_기여도가_거의_없다(self):
        rows = make_rows()
        d = C.explain(rows, T0 + timedelta(minutes=100), self.cfg)
        self.assertTrue(d["ok"])
        self.assertLessEqual(len(d["items"]), 3, d["items"])

    def test_기준선은_정상_구간에서_잡는다(self):
        d = self.peak()
        self.assertIn("정상 구간", d["note"])
        self.assertGreaterEqual(d["baseline_n"], 200)

    def test_없는_시각은_오류로_알린다(self):
        d = C.explain(make_rows(), T0 + timedelta(days=3), self.cfg)
        self.assertFalse(d["ok"])

    def test_데이터가_없으면_오류(self):
        self.assertFalse(C.explain([], T0, self.cfg)["ok"])

    def test_HTML_에_추정임을_반드시_밝힌다(self):
        """점수식을 푼 값으로 오해하면 안 된다 — 화면 문구를 고정한다."""
        h = C.explain_html(make_rows(), T0 + timedelta(minutes=207), self.cfg)
        self.assertIn("추정", h)
        self.assertIn("점수식을 푼 값이 아닙니다", h)


class Scale(unittest.TestCase):
    """z 눈금 — MAD 가 0 이어도 터지지 않아야 한다."""

    def test_MAD_0_이면_다른_눈금으로_물러난다(self):
        vals = [0.0] * 40 + [1.0] * 5          # 중앙값 0, MAD 0
        sd = C._scale(vals, C._median(vals))
        self.assertIsNotNone(sd)
        self.assertGreater(sd, 1e-6)

    def test_상수라도_값이_있으면_그_값의_10퍼센트를_눈금으로(self):
        """5.0 에서 꿈쩍 않던 지표가 7.0 이 되면 이상하다 — 잴 수 있어야 한다."""
        self.assertAlmostEqual(C._scale([5.0] * 30, 5.0), 0.5)

    def test_전부_0이면_눈금을_만들_수_없다(self):
        """이때만 None. 호출부가 '값이 달라졌으면 z 상한' 으로 처리한다."""
        self.assertIsNone(C._scale([0.0] * 30, 0.0))

    def test_보통은_MAD(self):
        vals = [10, 11, 12, 13, 14, 15, 16] * 5
        self.assertGreater(C._scale(vals, C._median(vals)), 1.0)


if __name__ == "__main__":
    unittest.main()
