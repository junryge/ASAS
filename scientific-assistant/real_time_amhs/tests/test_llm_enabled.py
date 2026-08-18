"""LLM 판단 일치가 '왜 비어 있는지' 를 화면이 말하게 한다.

무슨 일이 있었나
    아침에 보니 LLM 데이터가 하루치 통째로 없었다. 실시간 수집은 멀쩡히
    돌고 있었다. 원인은 config 의 llm.per_minute.enabled 가 false —
    LLM.CSV 를 **쓰는 쪽**이 꺼져 있었다.

    그런데 화면은 이렇게 말하고 있었다:

        LLM 판단 일치
        –
        1분 추론 0건 · 대기 0 · 20분 뒤 채점      ← 곧 채워질 것처럼 보인다

    만드는 쪽이 꺼져 있으니 영영 0 인데, 카드만 보면 '아직 안 쌓였나 보다'
    로 읽힌다. 정책 탭의 시스템별 행도 '판단 (항상)' 이라 더 헷갈렸다 —
    주기 1분·건수 3건까지 맞춰 놓고 하루를 날렸다.

★그래서 이 파일이 지키는 것은 정확도가 아니라 **정직함**이다:
  꺼져 있으면 꺼져 있다고 말해야 한다.
"""
from __future__ import annotations

import copy
import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from accuracy import summary, pm_cfg          # noqa: E402


def _cfg(**over) -> dict:
    with open(os.path.join(_ROOT, "config.json"), encoding="utf-8-sig") as f:
        c = json.load(f)
    pm = c.setdefault("llm", {}).setdefault("per_minute", {})
    pm.update(over)
    return c


class SummaryReportsEnabled(unittest.TestCase):
    def test_켜져_있으면_켜졌다고_한다(self):
        self.assertIs(summary(None, _cfg(enabled=True, every_min=1))["enabled"], True)

    def test_꺼져_있으면_꺼졌다고_한다(self):
        """★이게 없어서 카드가 '20분 뒤 채점' 이라고 거짓말했다."""
        self.assertIs(summary(None, _cfg(enabled=False))["enabled"], False)

    def test_주기가_0이면_안_도는_것이다(self):
        """enabled 가 참이어도 every_min=0 이면 아무것도 안 만든다."""
        self.assertIs(summary(None, _cfg(enabled=True, every_min=0))["enabled"], False)

    def test_시스템이_off면_그_시스템은_안_도는_것이다(self):
        """정책 탭에서 그 시스템만 '끔' 으로 둔 경우."""
        c = _cfg(enabled=True, every_min=1)
        c["llm"]["per_minute"]["by_sys"] = {"M16A": {"mode": "off"}}
        c["_sys"] = "M16A"
        self.assertIs(summary(None, c)["enabled"], False)
        c2 = copy.deepcopy(c)
        c2["_sys"] = "ALL"
        self.assertIs(summary(None, c2)["enabled"], True)


class ConfigShipsEnabled(unittest.TestCase):
    """실제로 배포되는 config 가 켜져 있어야 한다.

    ★껐다가 되돌리는 걸 잊어서 하루치가 통째로 비었다. 이 시험이 그걸 잡는다.
      성능 때문에 줄여야 하면 enabled 를 끄지 말고 every_min 을 늘리거나
      max_per_cycle 을 줄여라 — 그러면 데이터는 계속 쌓인다.
    """

    def test_분당_판단이_켜져_있다(self):
        with open(os.path.join(_ROOT, "config.json"), encoding="utf-8-sig") as f:
            c = json.load(f)
        pm = c["llm"]["per_minute"]
        self.assertTrue(
            pm.get("enabled"),
            "llm.per_minute.enabled 가 꺼져 있다 — LLM 판단 일치가 영영 빈다. "
            "느리면 every_min 을 늘리거나 max_per_cycle 을 줄여라.")
        self.assertGreater(int(pm.get("every_min", 0)), 0, "every_min 이 0 이면 안 돈다")

    def test_설정값이_화면_선택지_안에_있다(self):
        """정책 화면 드롭다운에 없는 값이 파일에 있으면 저장할 때 튕긴다."""
        with open(os.path.join(_ROOT, "config.json"), encoding="utf-8-sig") as f:
            c = json.load(f)
        pm = c["llm"]["per_minute"]
        self.assertIn(int(pm.get("every_min", 1)), (1, 2, 5, 10, 15))
        self.assertIn(int(pm.get("max_per_cycle", 3)), (1, 2, 3, 5, 10))


class CardTellsTruth(unittest.TestCase):
    """대시보드가 그 상태를 실제로 읽어 쓰는지 (문구가 코드에 있는지)."""

    def setUp(self):
        with open(os.path.join(_ROOT, "static", "dashboard.html"), encoding="utf-8") as f:
            self.html = f.read()

    def test_꺼짐_상태를_카드가_본다(self):
        self.assertIn("a.enabled === false", self.html,
                      "renderAcc 가 enabled 를 안 본다 — 또 '20분 뒤 채점' 이라 할 것이다")

    def test_켜는_길을_알려_준다(self):
        self.assertIn("정책 탭에서 켜기", self.html)
        self.assertIn("function goPolicyTab", self.html,
                      "링크만 있고 그 함수가 없으면 눌러도 아무 일이 없다")

    def test_정책_화면도_전체_중지를_경고한다(self):
        self.assertIn("lp-offwarn", self.html)
        self.assertIn("function lpMasterHint", self.html)


if __name__ == "__main__":
    unittest.main()
