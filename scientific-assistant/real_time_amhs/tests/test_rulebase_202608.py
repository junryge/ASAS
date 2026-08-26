# -*- coding: utf-8 -*-
"""2026-08 룰베이스 변경 — 현장 배포본과 어긋나지 않게 못 박는다.

출처 (사용자가 준 배포 문서 · 코드)
    · 룰베이스 변경 내역 2026-08.html
    · FAB 별 스코어 비교.html
    · 발동이벤트_영역분리.py

바뀐 것 넷
    ① R-D 판정에서 STB(3F_STORAGE_UTIL) 제외 — **값은 계속 기록**
    ② M16_PKT 영역 전면 제외 (발동이벤트 135 → 134 컬럼)
    ③ M16B 가중 0.5 취소 → 전 영역 1.0
    ④ 경계·사건 시작 기준 50 → 60

왜 테스트로 두나
    이건 우리가 정한 규칙이 아니라 **현장 예측기가 정한 것**이다. 우리가
    임의로 되돌리면 화면이 예측기와 다른 말을 한다 — 그게 제일 위험하다.
"""
import os
import re
import unittest

from . import util  # noqa: F401

import fab_score  # noqa: E402

BASE = util.BASE


class R_D_는_FABSTORAGERATIO_만_본다(unittest.TestCase):
    """★① 2026-08 — STB 항 제거. 단 값 기록은 유지."""

    def _rd(self):
        return fab_score.WATCH["M16HUB"]["RD"]

    def test_FAB저장율은_그대로_판정한다(self):
        fab = [x for x in self._rd() if "FABSTORAGERATIO" in x["amos"]]
        self.assertEqual(len(fab), 1)
        self.assertEqual(fab[0]["thr"], 25.75)
        self.assertFalse(fab[0].get("record_only"))

    def test_STB_는_판정에서_뺀다(self):
        stb = [x for x in self._rd() if "3F_STORAGE_UTIL" in x["amos"]]
        self.assertEqual(len(stb), 1, "STB 항목 자체는 남아 있어야 한다(기록용)")
        self.assertIsNone(stb[0]["thr"], "임계가 남아 있으면 다시 판정한다")
        self.assertTrue(stb[0].get("record_only"))

    def test_STB_값은_계속_기록된다(self):
        """★판정에서 뺐다고 컬럼까지 지우면 안 된다 — 되돌릴 때 데이터가 빈다."""
        row = {"M16HUB_stb_util": "99.9", "M16HUB_rd_fab": "20"}
        got = [r for r in fab_score.readings(row, "M16HUB")
               if "3F_STORAGE_UTIL" in r["amos"]]
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["value"], 99.9)
        self.assertTrue(got[0]["has_value"])
        self.assertTrue(got[0]["record_only"])

    def test_STB_가_임계를_넘어도_넘음_표시가_안_붙는다(self):
        """★"STB 99.9% ← 넘음" 이 보이면 그게 원인인 줄 안다."""
        row = {"M16HUB_stb_util": "99.9"}
        got = [r for r in fab_score.readings(row, "M16HUB")
               if "3F_STORAGE_UTIL" in r["amos"]][0]
        self.assertNotEqual(got["over"], True)

    def test_기록용과_임계_미정의를_구분해_말한다(self):
        """★"임계 미정의"(기준이 없음)와 "판정 미사용"(일부러 뺌)은 다르다."""
        with open(os.path.join(BASE, "avatar_2d", "avatar", "sentinel.py"),
                  encoding="utf-8") as f:
            src = f.read()
        self.assertIn('c.get("record_only")', src)
        self.assertIn("판정 미사용", src)

    def test_그래프가_STB_를_R_D_원인으로_안_그린다(self):
        """★R-D 가 켜졌다고 STB 를 그리면 '이것 때문' 으로 읽힌다."""
        with open(os.path.join(BASE, "report_graphs.py"), encoding="utf-8") as f:
            src = f.read()
        i = src.index("M16HUB_stb_util")
        line = src[src.rindex("\n", 0, i) + 1:src.index("\n", i)]
        prev = src[:i]
        cond = prev[prev.rindex("if ", 0, len(prev)):]
        self.assertNotIn('has("D")', cond.split("\n")[0],
                         "R-D 발동만으로 STB 를 그린다")
        self.assertIn("기록용", line)


class M16_PKT_는_어디에도_없다(unittest.TestCase):
    """★② 2026-08 — 영역 전면 제외. M16_PKT_score 컬럼도 더는 안 온다."""

    def test_추가_영역_목록에서_빠졌다(self):
        names = [a for a, _c in fab_score.EXTRA_AREAS]
        self.assertNotIn("M16_PKT", names)
        self.assertEqual(names, ["M16", "M16_WT"])

    def test_비교표에_M16_PKT_줄이_안_선다(self):
        row = {"unified_risk_score": "30", "M16_PKT_score": "40",
               "M16_score": "10", "datetime": "2026-08-26 10:00"}
        out = fab_score.compare([row])
        blob = str(out)
        self.assertNotIn("M16_PKT", blob,
                         "M16_PKT 가 아직 비교 결과에 실린다")

    def test_감시_컬럼_정의에도_없다(self):
        self.assertNotIn("M16_PKT", fab_score.WATCH)

    def test_그래프도_제외한다(self):
        for fn in ("graphs.py", "report_graphs.py"):
            with open(os.path.join(BASE, fn), encoding="utf-8") as f:
                src = f.read()
            self.assertIn("M16_PKT", src, fn + " 에 제외 규칙이 있어야 한다")
            self.assertRegex(src, r"M16_PKT.{0,80}(제외|EXCLUDE)",
                             fn + " 에서 제외인지 확인 불가")


class M16B_가중치는_1_0(unittest.TestCase):
    """★③ 2026-08 — 0.5 취소. 전 영역 1.0."""

    def test_기본값이_비어_있다(self):
        self.assertEqual(fab_score.AREA_WEIGHT, {})

    def test_전_영역이_1_0(self):
        for f in fab_score.fabs():
            self.assertEqual(fab_score.area_weight(f), 1.0, f)

    def test_설정에도_0_5_가_안_남아_있다(self):
        import json
        with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        aw = (cfg.get("fab_score") or {}).get("area_weight") or {}
        self.assertNotIn("M16B", aw, "config 에 0.5 가 남아 코드를 덮어쓴다")


class 경계는_60부터(unittest.TestCase):
    """★④ 2026-08 — 사건 시작·등급 하한 50 → 60."""

    def test_등급_구간(self):
        from sentinel import grade, grade_cuts
        from lp_client import load_config
        cfg = load_config()
        self.assertEqual(grade_cuts(cfg), (60, 71, 85))
        self.assertEqual(grade(59, cfg)["level"], "정상")
        self.assertEqual(grade(60, cfg)["level"], "경계")


if __name__ == "__main__":
    unittest.main()
