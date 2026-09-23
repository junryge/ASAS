#!/usr/bin/env python3
"""LLM 최근 판단 카드 위 한 줄 — 2026-09-23 고객 요청.

  "맨 LLM최근 판단 위에 내용 하나 붙여주라 -> 스코어 시스템은 문제 되는 FAB를
   점수 예측(룰베이스기반)을 하고 문제를 파악합니다 이후에 OHT 로드를 통해서
   상태를 확인합니다."

글자는 띄어쓰기·마침표만 고쳤다. 모양은 탭 머리 설명(.tabhead p) 그대로.
"""
import os
import unittest

from . import util

TEXT = ("스코어 시스템은 문제 되는 FAB를 점수 예측(룰베이스 기반)을 하고 문제를 "
        "파악합니다. 이후에 OHT 로드를 통해서 상태를 확인합니다.")


class LLM_카드_위_한_줄(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(util.BASE, "static", "dashboard.html"), encoding="utf-8") as f:
            cls.h = f.read()

    def test_글이_있다(self):
        self.assertIn(TEXT, self.h)

    def test_LLM_최근_판단_카드_바로_위(self):
        i = self.h.index('<div class="livehead">')
        j = self.h.index('<div class="llmcard">', i)
        self.assertIn(TEXT, self.h[i:j], "LLM 카드보다 위(livehead 첫 줄)에 있어야 한다")

    def test_새로_꾸미지_않는다(self):
        """탭 머리 설명과 같은 모양 — .tabhead p 를 그대로 쓴다."""
        i = self.h.index('<div class="tabhead" id="livenote"><p>')
        self.assertIn(TEXT, self.h[i:i + 400])
        self.assertIn(".tabhead p{margin:0;", self.h)

    def test_글자는_빨강(self):
        """고객: "방금 만든 글자색 빨간색으로 눈에 잘 보이게" — 테마별 빨강(--crit)."""
        self.assertIn("#livenote p{color:var(--crit)}", self.h)


if __name__ == "__main__":
    unittest.main()
