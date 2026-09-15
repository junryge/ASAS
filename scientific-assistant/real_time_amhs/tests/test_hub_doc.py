# -*- coding: utf-8 -*-
"""M16 HUB 데드락 문서가 **자료에서 읽은 것**만 쓰는지.

고객이 손으로 분석해 온 것을 검증하는 문서라, 여기 숫자가 틀리면 고객
분석까지 같이 틀린 것이 된다. 쓰면서 한 번 걸렸다 — "PIO 만으로는 초위험에
못 닿는다" 고 적었는데 바로 위 표에 80점(초위험)이 찍혀 있었다. 결론을 손으로
쓰면 이렇게 된다. 그래서 결론도 계산해서 뽑고, 이 시험이 그걸 지킨다.

  · PIO 구간표는 지어내지 않는다 — pio_10min_cnt → pio_score 를 자료에서 읽는다
  · reason 글자의 PIO 건수가 발동이벤트 값과 같아야 그 글자를 쓸 수 있다
  · 선행 시간은 '내가 보기 시작한 시각' 이 아니라 예측이 이어진 시작이다
"""
import importlib.util
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)

_spec = importlib.util.spec_from_file_location(
    "_hub", os.path.join(_BASE, "M16HUB분석_문서.py"))
hub = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hub)


class PIO_구간표(unittest.TestCase):
    def test_구간이_겹치지_않고_올라간다(self):
        band = hub.PIO_BAND
        los = [lo for lo, _p in band]
        pts = [p for _lo, p in band]
        self.assertEqual(los, sorted(los, reverse=True), "구간이 내림차순이어야 한다")
        self.assertEqual(pts, sorted(pts, reverse=True), "건수가 많을수록 점수가 커야 한다")

    def test_임계_미만은_0점이다(self):
        self.assertEqual(hub.pio_pts(hub.PIO_THR - 1), 0)
        self.assertGreater(hub.pio_pts(hub.PIO_THR), 0)

    def test_건수가_늘면_점수가_줄지_않는다(self):
        prev = -1
        for c in range(0, 200):
            v = hub.pio_pts(c)
            self.assertGreaterEqual(v, prev, "%d개에서 점수가 내려갔다" % c)
            prev = v


class 등급(unittest.TestCase):
    def test_컷은_밖에서_받는다(self):
        self.assertEqual(hub.lv_of(43, (43, 57, 72)), "경계")
        self.assertEqual(hub.lv_of(42, (43, 57, 72)), "정상")
        self.assertEqual(hub.lv_of(80, (43, 57, 72)), "초위험")
        # 컷을 바꾸면 같은 값이 다른 등급이 된다
        self.assertEqual(hub.lv_of(43, (36, 52, 72)), "경계")
        self.assertEqual(hub.lv_of(43, (50, 60, 80)), "정상")

    def test_값이_없으면_정상으로_둔다(self):
        self.assertEqual(hub.lv_of(None, (43, 57, 72)), "정상")


class Reason_에서_PIO를_읽는다(unittest.TestCase):
    """발동이벤트가 없는 날에도 쓰려고 글자에서 뽑는다 — 정규식이 정확해야 한다."""

    def test_건수를_뽑는다(self):
        m = hub._PIO.search("M16HUB Queue 상승 · PIO 반송실패 134개/10분 · 주 M16HUB")
        self.assertIsNotNone(m)
        self.assertEqual(int(m.group(1)), 134)

    def test_꾸밈말이_붙어도_뽑는다(self):
        m = hub._PIO.search("… PIO 반송실패 22개/10분(조금 많음) · 주 M16HUB")
        self.assertEqual(int(m.group(1)), 22)

    def test_없으면_None(self):
        self.assertIsNone(hub._PIO.search("M16HUB 반송지연 · Storage FULL"))

    def test_다른_숫자를_주워오지_않는다(self):
        # '4분초과 41.2%' 같은 글자가 같이 있어도 PIO 것만 집는다
        s = "M16HUB[SLA(41.2%4분초과)] · PIO 반송실패 17개/10분"
        self.assertEqual(int(hub._PIO.search(s).group(1)), 17)


class 결론을_손으로_쓰지_않는다(unittest.TestCase):
    """render 가 등급 판정을 lv_of 로 하는지 — 글자로 박으면 자료와 어긋난다."""

    def setUp(self):
        with open(os.path.join(_BASE, "M16HUB분석_문서.py"), encoding="utf-8") as fh:
            self.src = fh.read()

    def test_초위험_결론이_계산에서_나온다(self):
        i = self.src.index("hit = [")
        self.assertIn("lv_of(v, cuts) == LV[-1]", self.src[i:i + 200],
                      "'초위험에 닿는다/못 닿는다' 는 계산 결과여야 한다")

    def test_못_닿는다를_무조건_적지_않는다(self):
        # 예전 판이 이 문장을 조건 없이 박아 두고 있었다
        bad = '"세 사건 모두 <b>%s</b> 까지는 가는데 <b>%s</b> 에는 못 닿는다. "'
        self.assertNotIn(bad, self.src)

    def test_선행_시간은_창_끝값이_아니다(self):
        # 앞 1시간만 보면 "15:00부터" 가 나오는데 그건 내가 보기 시작한 시각이다
        self.assertIn("hub_edge", self.src,
                      "창 끝에 걸린 경우를 '적어도' 로 표시해야 한다")
        self.assertIn("GAP", self.src, "끊김 허용치가 있어야 한다")


if __name__ == "__main__":
    unittest.main()
