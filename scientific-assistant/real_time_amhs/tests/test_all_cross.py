# -*- coding: utf-8 -*-
"""ALL 분석은 FAB 다섯을 같이 봐야 한다.

ALL 과 FAB 은 배점표가 겹치지 않는다 — ALL 에만 흐름 30점, FAB 에만
RA/RB/RC/RD 45점. 그래서 한쪽만 올라가는 일이 **구조적으로** 생긴다.
그런데 LLM 모델 분석이 ALL 점수만 읽고 "전 구간 정상" 이라고 썼다.
ALL 전체 분석은 그런 게 아니다.

  ① ALL 경계 이상 · FAB 전부 정상   → 전체적으로 FAB 들이 같이 올라온 것(물량)
  ② ALL 경계 미만 · FAB 한 곳 경계↑ → 그 FAB 에서 문제가 진행 중일 수 있다
  ③ ALL 경계 미만 · FAB 두 곳 경계↑ → 한 FAB 이 다른 FAB 에 영향을 주는 중
"""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analysis                                             # noqa: E402
import fab_score                                            # noqa: E402
from lp_client import load_config, sys_cfg                  # noqa: E402

_CFG = load_config()
_FABS = fab_score.fabs(_CFG)


def _row(all_sc, hot=(), chain=""):
    r = {"unified_risk_score": all_sc, "hot_area": "M16HUB",
         "reason": "", "propagation_chain": chain}
    for f in _FABS:
        r[f"{f}_score"] = 95 if f in hot else 20
    return r


def _seq(rows):
    base = dt.datetime(2026, 9, 4, 7, 0)
    out = []
    for i, r in enumerate(rows):
        d = base + dt.timedelta(minutes=i)
        r = {**r, "datetime": d.strftime("%Y-%m-%d %H:%M")}
        out.append((d, float(r["unified_risk_score"]), r))
    return out


class 다섯_점수를_한_줄에_세운다(unittest.TestCase):

    def test_경계를_넘은_FAB_과_아닌_FAB_을_가른다(self):
        lu = fab_score.lineup(_row(44, hot=("M16A",)), _CFG)
        self.assertEqual([x["fab"] for x in lu["hot"]], ["M16A"])
        self.assertEqual(len(lu["quiet"]), len(_FABS) - 1)
        self.assertTrue(all("cut" in x for x in lu["hot"] + lu["quiet"]))

    def test_근거가_없으면_지어내지_않는다(self):
        """없는 FAB 점수를 0(정상)으로 채우면 'FAB 전부 정상' 이라는 거짓이 된다."""
        self.assertIsNone(fab_score.lineup({"unified_risk_score": 70}, _CFG))

    def test_엇갈리지_않아도_돌려준다(self):
        """divergence 는 엇갈릴 때만 말한다. 프롬프트는 조용할 때도 다섯 점수가
           필요하다 — '정말 조용했다' 는 것도 근거다."""
        lu = fab_score.lineup(_row(20), _CFG)
        self.assertIsNotNone(lu)
        self.assertEqual(lu["hot"], [])
        self.assertIsNone(fab_score.divergence(_row(20), _CFG))


class 세_가지_갈래(unittest.TestCase):

    def test_1_ALL만_높으면_물량(self):
        d = fab_score.divergence(_row(74), _CFG)
        self.assertEqual(d["kind"], "전체물량")
        self.assertIn("물량이 올라온 것", d["text"])

    def test_2_FAB_한_곳이면_그_FAB_에서_진행중(self):
        d = fab_score.divergence(_row(44, hot=("M16A",)), _CFG)
        self.assertEqual(d["kind"], "단일FAB")
        self.assertIn("M16A 에서 문제가 진행 중", d["text"])
        self.assertIn("ALL 이 조용하다고 정상으로 보면 안 된다", d["text"])

    def test_3_FAB_두_곳이면_서로_영향(self):
        d = fab_score.divergence(_row(41, hot=("M16A", "M14B")), _CFG)
        self.assertEqual(d["kind"], "FAB전이")
        self.assertIn("M16A", d["text"])
        self.assertIn("M14B", d["text"])

    def test_전이_경로가_없으면_방향을_단정하지_않는다(self):
        """없는 인과를 만들면 관제가 엉뚱한 FAB 을 본다."""
        d = fab_score.divergence(_row(41, hot=("M16A", "M14B")), _CFG)
        self.assertIn("확정할 수 없다", d["text"])
        d2 = fab_score.divergence(
            _row(41, hot=("M16A", "M14B"), chain="M16A→M14B"), _CFG)
        self.assertIn("M16A→M14B", d2["text"])


class 분석_프롬프트에_실린다(unittest.TestCase):

    def _mixed(self):
        return _seq([_row(74)] * 12 + [_row(44, hot=("M16A",))] * 12
                    + [_row(41, hot=("M16A", "M14B"))] * 7)

    def test_세_갈래가_분수로_세어져_들어간다(self):
        txt = analysis._fab_cross(self._mixed(), _CFG,
                                  dt.datetime(2026, 9, 4, 7, 0))
        self.assertIn("전체물량 12분", txt)
        self.assertIn("단일FAB 12분", txt)
        self.assertIn("FAB전이 7분", txt)

    def test_읽는_법_세_줄이_같이_간다(self):
        """숫자만 주면 모델이 ALL 만 보고 '정상' 이라고 쓴다."""
        txt = analysis._fab_cross(self._mixed(), _CFG,
                                  dt.datetime(2026, 9, 4, 7, 0))
        self.assertIn("ALL 점수만 보고 '전 구간 정상' 이라고 쓰지 마라", txt)
        for n in ("1)", "2)", "3)"):
            self.assertIn(n, txt)

    def test_최고점_시각의_다섯_점수를_적는다(self):
        txt = analysis._fab_cross(self._mixed(), _CFG,
                                  dt.datetime(2026, 9, 4, 7, 0))
        self.assertIn("최고점 시각 07:00:", txt)
        for f in _FABS:
            self.assertIn(f, txt)

    def test_전체_통계에_붙는다(self):
        txt, _meta = analysis._overview(self._mixed(), _CFG, "07:00~07:30")
        self.assertIn("[FAB 대조]", txt)
        # 자리 — [전체 통계] 다음, [이벤트 목록] 앞
        self.assertLess(txt.index("[전체 통계]"), txt.index("[FAB 대조]"))
        self.assertLess(txt.index("[FAB 대조]"), txt.index("[이벤트 목록]"))

    def test_FAB_하나를_볼_때는_안_붙는다(self):
        """그 CSV 에 남의 FAB 점수가 없다. 없는 것을 채우면 거짓이 된다."""
        cfg = sys_cfg(_CFG, "M16HUB")
        seq = _seq([{"unified_risk_score": 55, "hot_area": "M16HUB", "reason": ""}] * 10)
        self.assertEqual(analysis._fab_cross(seq, cfg, seq[0][0]), "")
        txt, _ = analysis._overview(seq, cfg, "07:00~07:09")
        self.assertNotIn("[FAB 대조]", txt)


class 일차도_FAB_을_본다(unittest.TestCase):
    """1차는 요약이 아니라 **분단위**를 보는 단계다. 그런데 ALL 점수만
    실려 있어서 'ALL 44점 — 정상' 으로 관찰하고 넘어갔다. 그 밑에서
    M16A 가 경계를 넘었어도 1차가 한 번도 못 보면, 2·3차가 이어받을
    관찰 자체가 없다."""

    def _chunk(self, rows):
        return analysis._chunks(_seq(rows), _CFG)[0]["text"]

    def test_경계를_넘은_FAB_이_줄에_붙는다(self):
        txt = self._chunk([_row(44, hot=("M16A",))] * 5)
        self.assertIn("FAB↑ M16A", txt)
        self.assertIn("(60)", txt)          # 그 FAB 의 경계도 같이

    def test_넘은_FAB_이_없으면_아무것도_안_붙인다(self):
        """1440줄에 다섯 점수를 다 적으면 정작 봐야 할 줄이 안 보인다."""
        txt = self._chunk([_row(30)] * 5)
        self.assertNotIn("FAB↑", txt)

    def test_있는_조각에만_읽는_법을_적는다(self):
        hot = self._chunk([_row(44, hot=("M16A",))] * 5)
        self.assertIn("ALL 점수가 낮아도 그냥 넘기지 마라", hot)
        self.assertNotIn("ALL 점수가 낮아도", self._chunk([_row(30)] * 5))

    def test_두_곳이_넘으면_둘_다_적는다(self):
        txt = self._chunk([_row(41, hot=("M16A", "M14B"))] * 5)
        line = next(x for x in txt.splitlines() if x.startswith("07:00"))
        self.assertIn("M16A", line)
        self.assertIn("M14B", line)

    def test_FAB_하나를_볼_때는_안_붙는다(self):
        cfg = sys_cfg(_CFG, "M16HUB")
        seq = _seq([{"unified_risk_score": 55, "hot_area": "M16HUB", "reason": ""}] * 5)
        self.assertNotIn("FAB↑", analysis._chunks(seq, cfg)[0]["text"])


if __name__ == "__main__":
    unittest.main()
