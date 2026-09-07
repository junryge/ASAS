# -*- coding: utf-8 -*-
"""정합성 검사 서류 — 고객 제출용 문서를 코드에서 뽑는다.

왜 손으로 안 쓰나
    고객이 물은 것은 넷이다: 룰 개정 이력 · 룰 제작 데이터 기간 ·
    평가 데이터 기간 · 성능(P/R/F1). 이걸 손으로 적어 두면 룰이 바뀔 때
    문서만 옛날 값으로 남는다. 그 문서가 나중에 근거로 쓰인다.

무엇을 지키나
    ① **지어내지 않는다** — 표본이 없으면 0.0 이 아니라 '없음'
    ② **출처를 밝힌다** — 룰 원본을 못 찾으면 받아 적은 값이라고 말한다
    ③ **판정 이름이 accuracy.py 와 같다** — 두 벌이 되면 숫자가 갈린다
"""
import io
import os
import unittest

from . import util

DOC = os.path.join(util.BASE, "정합성_문서.py")


def _mod():
    import importlib.util
    import sys
    if not os.path.isfile(DOC):
        raise unittest.SkipTest("정합성_문서.py 가 없다")
    sys.path.insert(0, util.BASE)
    spec = importlib.util.spec_from_file_location("정합성문서", DOC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class 지어내지_않는다(unittest.TestCase):
    """표본이 없는 것과 성능이 0 인 것은 다르다. 표에 0.000 이 찍히면
    고객은 '성능이 바닥' 으로 읽는다."""

    def setUp(self):
        self.m = _mod()

    def test_표본이_없으면_숫자를_안_만든다(self):
        p, r, f = self.m._prf(0, 0, 0)
        self.assertIsNone(p)
        self.assertIsNone(r)
        self.assertIsNone(f)
        self.assertEqual(self.m._f3(None), "—")

    def test_한쪽만_없어도_F1_은_없다(self):
        p, r, f = self.m._prf(0, 5, 0)      # 적중 0 → Precision 0, Recall 없음
        self.assertEqual(p, 0.0)
        self.assertIsNone(r)
        self.assertIsNone(f, "Recall 이 없는데 F1 을 만들면 안 된다")

    def test_계산이_맞는다(self):
        p, r, f = self.m._prf(8, 2, 2)
        self.assertAlmostEqual(p, 0.8)
        self.assertAlmostEqual(r, 0.8)
        self.assertAlmostEqual(f, 0.8)


class 판정_이름이_안_갈린다(unittest.TestCase):
    """accuracy.py 가 CSV 에 쓰는 말과 여기서 세는 말이 같아야 한다.
    한쪽만 고치면 성능이 조용히 0 이 된다."""

    def test_같은_말을_쓴다(self):
        m = _mod()
        src = io.open(os.path.join(util.BASE, "accuracy.py"),
                      encoding="utf-8").read()
        i = src.index("_HIT, _FP, _FN, _EFFECT")
        line = src[i:src.index("\n", i)]
        for w in (m.HIT, m.FP, m.FN, m.EFFECT):
            self.assertIn('"{}"'.format(w), line,
                          "accuracy.py 와 판정 이름이 다르다: " + w)

    def test_조치효과는_분모에서_빠진다(self):
        """조치를 잘할수록 성능이 나빠 보이면 안 된다."""
        m = _mod()
        src = io.open(DOC, encoding="utf-8").read()
        i = src.index("def _prf(")
        body = src[i:src.index("def score_days")]
        self.assertNotIn(m.EFFECT, body, "조치효과가 계산식에 들어갔다")


class 출처를_밝힌다(unittest.TestCase):
    """어디서 온 숫자인지가 정합성 문서의 절반이다."""

    def test_룰_원본을_직접_읽는다(self):
        m = _mod()
        ru = m.read_rule_source()
        self.assertTrue(ru["version"], "룰 버전이 비었다")
        if ru["found"]:
            self.assertIn("v", ru["version"].lower())
            self.assertTrue(ru["train"], "룰 제작 데이터 기간을 못 읽었다")
            self.assertTrue(os.path.isfile(ru["path"]))

    def test_못_찾으면_받아_적은_값이라고_한다(self):
        m = _mod()
        old = m.RULE_DIRS
        try:
            m.RULE_DIRS = ["없는폴더"]
            os.environ.pop("RULE_SRC", None)
            ru = m.read_rule_source()
            self.assertFalse(ru["found"])
            self.assertTrue(ru["version"], "그래도 버전은 말해야 한다")
        finally:
            m.RULE_DIRS = old

    def test_오늘은_평가에서_뺀다(self):
        """검증 창이 안 찬 행이 많아 실제보다 나쁘게 나온다."""
        src = io.open(DOC, encoding="utf-8").read()
        i = src.index("def pick_days(")
        self.assertIn("timedelta(days=1)", src[i:i + 900])


class 문서가_만들어진다(unittest.TestCase):

    def test_데이터가_없어도_만들어진다(self):
        """데이터가 없다고 문서 자체가 안 나오면 안 된다 — 방법과 기준은
        데이터 없이도 낼 수 있어야 한다."""
        m = _mod()
        d = m.build()
        h = m.render_html(d)
        md = m.render_md(d)
        for t in ("정합성 검사 서류", "unified_risk_score", "area_score",
                  "Precision", "Recall", "F1"):
            self.assertIn(t, h, "HTML 에 없다: " + t)
            self.assertIn(t, md, "MD 에 없다: " + t)
        # 룰 버전이 문서에 실려야 한다
        self.assertIn(d["rule"]["version"][:12], h)

    def test_등급컷을_코드에서_읽는다(self):
        """손으로 60/71/85 를 적어 두면 정책이 바뀔 때 문서만 옛날 값이다."""
        import sys
        sys.path.insert(0, util.BASE)
        import sentinel
        from lp_client import load_config
        w, dg, c = sentinel.grade_cuts(load_config())
        m = _mod()
        h = m.render_html(m.build())
        self.assertIn("경계 {} / 위험 {} / 초위험 {}".format(w, dg, c),
                      h.replace("\n", " "))


if __name__ == "__main__":
    unittest.main()
