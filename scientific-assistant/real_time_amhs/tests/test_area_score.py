# -*- coding: utf-8 -*-
"""area_score — 예측기(발동이벤트_영역분리.py)와 같은 눈금인가.

실제 사고
    "경계값 60인데 왜 35에서 울리냐"
    우리는 raw 를 **AREA_CAP(50)** 으로 나눠 0~100 을 만들었다. 그런데
    예측기의 정의는

        area_score = min(100, round(score_raw × 100 ÷ 분모))     분모 기본 70
        area_level = 60 경계 / 71 위험 / 85 초위험

    50 은 '융합에 들어갈 때 잘리는 상한(SATURATE_AT)' 이지 점수 분모가 아니다.
    그래서 점수가 40% 부풀어 raw 35 가 70점(위험)으로 나왔다 — 올바른 값은 50점,
    정상이다. 등급 하나가 통째로 앞당겨져 울린 것이다.

여기서 지키는 것
    ① 분모는 70 (설정으로 덮을 수 있고, 영역별 조정도 예측기와 같은 식)
    ② 등급 컷 60/71/85 는 **area_score(0~100)** 에 붙는다
    ③ FAB 분리 파일(data/{FAB}/{day}_TOTAL.CSV)의 area_score 가 있으면
       그게 원본이다 — 되계산보다 우선한다
"""
import os
import shutil
import tempfile
import unittest

from . import util  # noqa: F401

import fab_score  # noqa: E402
import store_csv  # noqa: E402
from lp_client import load_config  # noqa: E402


def _grade(s):
    return "초위험" if s >= 85 else "위험" if s >= 71 else "경계" if s >= 60 else "정상"


class 예측기와_같은_계산(unittest.TestCase):
    def test_분모는_70이다(self):
        """★50 으로 나누면 40% 부풀어 한 등급씩 앞당겨 울린다."""
        self.assertEqual(fab_score.AREA_DENOM, 70)
        self.assertEqual(set(fab_score.area_denoms().values()), {70.0})

    def test_예측기_공식_그대로(self):
        for raw, want in [(0, 0), (25, 36), (30, 43), (35, 50), (42, 60),
                          (50, 71), (60, 86), (70, 100), (999, 100)]:
            self.assertEqual(fab_score.area_score_100(raw, "M16HUB"), want,
                             "raw {}".format(raw))

    def test_35는_정상이다(self):
        """★바로 그 지적 — 35에서 울리면 안 된다."""
        self.assertEqual(_grade(fab_score.area_score_100(35, "M16HUB")), "정상")
        self.assertEqual(_grade(fab_score.area_score_100(42, "M16HUB")), "경계")

    def test_옛_분모로는_35가_울렸다(self):
        """무엇이 틀렸었는지 못 박아 둔다 — 되돌아가면 이 값이 다시 나온다."""
        self.assertEqual(fab_score.risk(35), 70)
        self.assertEqual(_grade(70), "경계")

    def test_영역별_조정도_예측기와_같은_식(self):
        """실효 분모 = 분모 ÷ (조정/100)"""
        cfg = load_config()
        fs = dict(cfg.get("fab_score") or {})
        cfg = dict(cfg, fab_score=dict(fs, denom=70, adjust={"M16HUB": 120}))
        d = fab_score.area_denoms(cfg)
        self.assertAlmostEqual(d["M16HUB"], 70 / 1.2, places=6)
        self.assertAlmostEqual(d["M14"], 70.0, places=6)

    def test_분모를_설정으로_덮는다(self):
        cfg = load_config()
        fs = dict(cfg.get("fab_score") or {})
        cfg = dict(cfg, fab_score=dict(fs, denom=50))
        self.assertEqual(fab_score.area_score_100(35, "M16HUB", cfg), 70)


class 등급_구간(unittest.TestCase):
    """정상 0~59 · 경계 60~70 · 위험 71~84 · 초위험 85~100"""

    def test_구간이_예측기와_같다(self):
        from sentinel import grade, grade_cuts
        cfg = load_config()
        self.assertEqual(grade_cuts(cfg), (60, 71, 85))
        for sc, want in [(0, "정상"), (59, "정상"), (60, "경계"), (70, "경계"),
                         (71, "위험"), (84, "위험"), (85, "초위험"),
                         (100, "초위험")]:
            self.assertEqual(grade(sc, cfg)["level"], want, sc)


class FAB_분리_파일을_읽는다(unittest.TestCase):
    """★"data/M16HUB/20260826_TOTAL.CSV 에 area_score 다 있는데 왜 다른 걸 보냐" """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._base = store_csv.BASE_DIR
        store_csv.BASE_DIR = self.tmp
        self.d = os.path.join(self.tmp, "data")
        os.makedirs(self.d)
        self.cfg = load_config()
        self.cfg.setdefault("storage", {})["daily_csv_dir"] = "data"

    def tearDown(self):
        store_csv.BASE_DIR = self._base
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _all(self, raw=35):
        with open(os.path.join(self.d, "20260826_TOTAL.CSV"), "w",
                  encoding="utf-8") as f:
            f.write("datetime,unified_risk_score,M16HUB_pts_RA,M16HUB_score,"
                    "M16HUB_score_raw\n"
                    "2026-08-26 10:00,67,{r},{r},{r}\n".format(r=raw))

    def _fab(self, fab="M16HUB", score=50, level="", sat=""):
        os.makedirs(os.path.join(self.d, fab), exist_ok=True)
        with open(os.path.join(self.d, fab, "20260826_TOTAL.CSV"), "w",
                  encoding="utf-8") as f:
            f.write("datetime,area_score,area_level,area_saturated\n"
                    "2026-08-26 10:00,{},{},{}\n".format(score, level, sat))

    def _row(self, fab="M16HUB"):
        rows = store_csv.read_day("20260826", self.cfg)
        out = fab_score.compare(rows, None, self.cfg, day="20260826")
        return [r for r in out["rows"] if r.get("fab") == fab][0]

    def test_분리_파일의_area_score_를_쓴다(self):
        """★되계산 값과 **다른** 값을 넣어야 어느 쪽을 쓰는지 알 수 있다.
        (raw 35 를 되계산하면 50 이다 — 파일에는 일부러 63 을 넣는다)"""
        self._all(raw=35)
        self._fab(score=63)
        r = self._row()
        self.assertEqual(r["area_score"], 63, "되계산 값(50)을 썼다")
        self.assertEqual(r["source"], "fab_file")
        self.assertEqual(r["score_col"], "area_score")

    def test_예측기가_적어_준_등급을_그대로_쓴다(self):
        """우리가 다시 매기면 기준이 두 벌이 되어 언젠가 어긋난다.
        ★우리 계산과 **다른** 등급을 넣어야 확인이 된다 — 62점이면 우리는
        '경계' 라고 매기지만, 파일이 '위험' 이라고 하면 파일을 따라야 한다
        (영역등급.json 의 기준이 바뀌었을 수 있다)."""
        self._all(raw=35)
        self._fab(score=62, level="위험")
        r = self._row()
        self.assertEqual(r["area_score"], 62)
        self.assertEqual(r["level"], "위험", "우리가 다시 매겼다")

    def test_포화_표시도_가져온다(self):
        self._all(raw=60)
        self._fab(score=86, level="초위험", sat="Y")
        self.assertTrue(self._row()["saturated"])

    def test_분리_파일이_없으면_되계산하고_그렇다고_밝힌다(self):
        self._all(raw=35)
        r = self._row()
        self.assertEqual(r["area_score"], 50)     # raw 35 → 50점
        self.assertEqual(r["source"], "calc")
        self.assertIn("분모", r["measures"])

    def test_융합용_area_와_섞지_않는다(self):
        """★area(0~50, 융합 기여분)와 area_score(0~100)는 다른 수다."""
        self._all(raw=35)
        self._fab(score=50)
        r = self._row()
        self.assertEqual(r["area"], 35.0)         # 룰 배점 합 (상한 50)
        self.assertEqual(r["area_score"], 50)     # 예측기 점수
        self.assertNotEqual(r["area"], r["area_score"])


class 화면도_같은_눈금이다(unittest.TestCase):
    def test_FAB_도_0에서_100_축이다(self):
        with open(os.path.join(util.BASE, "avatar_2d", "avatar", "sentinel.py"),
                  encoding="utf-8") as f:
            src = f.read()
        blk = src[src.index('"value": row.get("score") if is_all'):]
        blk = blk[:blk.index("risk")]
        self.assertIn('"vmax": 100', blk, "FAB 을 아직 0~50 축으로 그린다")
        self.assertIn("area_score", blk, "area_score 를 안 쓴다")

    def test_되계산이면_화면에_표시한다(self):
        with open(os.path.join(util.BASE, "avatar_2d", "static", "app.js"),
                  encoding="utf-8") as f:
            js = f.read()
        self.assertIn("f.source==='calc'", js, "되계산인지 화면에서 못 본다")
        self.assertIn("area_score", js)


if __name__ == "__main__":
    unittest.main()
