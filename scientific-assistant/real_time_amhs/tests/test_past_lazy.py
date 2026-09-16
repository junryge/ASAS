# -*- coding: utf-8 -*-
"""과거 데이터 조회 — 탭을 열기만 해서는 아무것도 읽지 않는다.

왜 고쳤나
    탭을 누르는 순간 initPast() 가 최신 날짜(대개 오늘)를 바로 조회했다.
    그 날은 실시간 화면이 이미 보고 있는 날이라, **같은 하루치(최대 5000행)를
    한 번 더** 받아 표·스트립·그날 LLM 판단까지 그렸다. 볼 날짜를 고르기도
    전에 제일 무거운 일을 하고 있었던 셈이다.

여기서 지키는 것
    · initPast() 는 날짜 목록만 채운다 — 읽지 않는다
    · 날짜를 고르거나 [조회] 를 누르면 그때 읽는다 (길이 세 개 다 살아 있어야
      한다 — 하나만 남기면 "눌러도 안 나온다" 가 된다)
    · 아직 안 읽었다는 것을 화면이 말한다 (빈 표를 '데이터 없음' 으로 읽으면
      안 된다)
"""
import os
import re
import unittest

HTML = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "static", "dashboard.html")


def body(name: str) -> str:
    """async function <name>(){ … } 의 본문만 떼어 온다 (중괄호 세면서)."""
    src = open(HTML, encoding="utf-8").read()
    m = re.search(rf"(?:async\s+)?function\s+{re.escape(name)}\s*\([^)]*\)\s*{{", src)
    assert m, name
    i, depth = m.end(), 1
    while i < len(src) and depth:
        depth += (src[i] == "{") - (src[i] == "}")
        i += 1
    return src[m.end():i - 1]


class 탭을_열어도_안_읽는다(unittest.TestCase):
    def setUp(self):
        self.src = open(HTML, encoding="utf-8").read()
        self.init = body("initPast")

    def test_initPast_는_조회를_하지_않는다(self):
        self.assertNotIn("loadPast(", self.init.replace("loadPastDays(", ""))

    def test_날짜_목록은_채운다(self):
        """고를 것이 없으면 '날짜를 고르세요' 가 무의미하다."""
        self.assertIn("loadPastDays(", self.init)

    def test_아직_안_읽었다고_화면이_말한다(self):
        """빈 표를 '그 날 데이터 없음' 으로 읽으면 안 된다."""
        self.assertIn("날짜를 고르면", self.init)

    def test_읽는_길이_세_개_다_있다(self):
        for sel in ("$('#pload').onclick", "$('#pdate').onchange",
                    "$('#pday').onchange"):
            self.assertIn(sel, self.src, sel)

    def test_탭_전환은_PDAY_가_있을_때만_LLM_을_읽는다(self):
        self.assertIn("if(PDAY) loadPastLlm(PDAY)", self.src)

    def test_등급_다시칠하기도_PDAY_를_본다(self):
        """정책을 바꿔도 아직 안 읽은 과거 탭을 대신 읽어 주지 않는다."""
        self.assertIn("if(PDAY) loadPast(PDAY, {autoFetch:false})", self.src)


if __name__ == "__main__":
    unittest.main()
