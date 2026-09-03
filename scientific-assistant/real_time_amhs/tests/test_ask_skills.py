# -*- coding: utf-8 -*-
"""이어 묻기에 스킬을 얹고 뺀다.

★대화하다 보면 "이 문서 보고 답해" 가 필요해진다. 그런데 한 번 올린 문서가
  대화 끝까지 따라다니면, 다른 것을 물을 때 그게 방해가 된다 — 넣는 것만큼
  **빼는 것**이 있어야 쓸 수 있다.
"""
import os
import re
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import analysis                                             # noqa: E402


def _src(name):
    with open(os.path.join(BASE, name), encoding="utf-8") as f:
        return f.read()


class 프롬프트에_얹는다(unittest.TestCase):

    def test_이름과_본문이_들어간다(self):
        s = analysis._ask_skills_block([{"name": "pio-error", "body": "실패한 결과다"}])
        self.assertIn("### pio-error", s)
        self.assertIn("실패한 결과다", s)

    def test_빈_것은_거른다(self):
        self.assertEqual(analysis._ask_skills_block([{"name": "a", "body": "  "}]), "")
        self.assertEqual(analysis._ask_skills_block(None), "")

    def test_길면_자르되_잘랐다고_적는다(self):
        """★자른 것을 숨기면 '문서에 없다' 를 사실로 말해 버린다."""
        s = analysis._ask_skills_block([{"name": "a", "body": "가" * 99999}])
        self.assertIn("뒤가 잘렸다", s)
        self.assertLess(len(s), analysis.ASK_SKILL_CHARS + 500)

    def test_예산이_다_차면_말해_준다(self):
        s = analysis._ask_skills_block([{"name": "a", "body": "가" * 99999},
                                        {"name": "b", "body": "나" * 100}])
        self.assertIn("예산이 모자라", s)

    def test_근거를_안_밀어낸다(self):
        """★스킬이 커도 분석 근거(overview)가 밀리면 안 된다 — 근거가 없으면
        숫자를 지어낸다."""
        self.assertLessEqual(analysis.ASK_SKILL_CHARS, 20000)

    def test_숫자는_근거에서만_쓰라고_박는다(self):
        """★스킬 문서에 적힌 예시 수치를 이 구간의 값으로 말하는 것이 제일
        나쁘다 (PIO 명세에는 '10분 최대 89' 같은 숫자가 널려 있다)."""
        src = _src("analysis.py")
        i = src.index("sk = _ask_skills_block(skills)")
        blk = src[i:i + 700]
        self.assertIn("근거에 있는 것만", blk)
        self.assertIn("예시 숫자", blk)

    def test_규칙_뒤에_온다(self):
        """★앞에 두면 위 규칙(한국어·근거 밖 숫자 금지)을 덮어 쓴다.

        ★파일 안의 줄 순서가 아니라 **조립 순서**를 본다 — ASK_RULES 는
          ask() 아래에 정의돼 있어서 줄 순서로 재면 거꾸로 나온다.
        """
        src = _src("analysis.py")
        i = src.index("def ask(aid: str")
        body = src[i:src.index("\n\ndef ", i + 10)]
        self.assertLess(body.index("+ ASK_RULES"),
                        body.index("_ask_skills_block(skills)"))
        # 사용자 지시(extra_prompt) 다음이어야 한다 — 둘 다 규칙 뒤다
        self.assertLess(body.index("[추가 지시"),
                        body.index("_ask_skills_block(skills)"))


class 서버에서_넣고_뺀다(unittest.TestCase):

    def setUp(self):
        self.src = _src("server.py")

    def test_세_길이_다_있다(self):
        self.assertIn('@app.route("/api/analysis/skills", methods=["GET"])', self.src)
        self.assertIn('@app.route("/api/analysis/skills", methods=["POST"])', self.src)
        self.assertIn('@app.route("/api/analysis/skills/<sid>", methods=["DELETE"])',
                      self.src)

    def test_전부_빼기가_있다(self):
        """★하나씩만 뺄 수 있으면, 여러 개 올린 뒤 정리가 번거로워 안 뺀다."""
        self.assertIn('sid == "all"', self.src)

    def test_md_txt_만_받는다(self):
        i = self.src.index("def api_ask_skill_add(")
        blk = self.src[i:i + 1200]
        self.assertIn('(".md", ".markdown", ".txt")', blk)

    def test_같은_이름은_바꿔_끼운다(self):
        """★고쳐서 다시 올리는 게 보통이다. 쌓이면 같은 글이 두 벌 실린다."""
        i = self.src.index("def api_ask_skill_add(")
        blk = self.src[i:i + 1600]
        self.assertIn('s_["name"] != name', blk)

    def test_상한이_있다(self):
        self.assertIn("ASK_SKILL_MAX", self.src)
        self.assertIn("ASK_SKILL_KEEP", self.src)

    def test_목록에_본문을_안_보낸다(self):
        """★목록에 본문까지 실으면 화면이 매번 수십 KB 를 받는다."""
        i = self.src.index("def api_ask_skills(")
        blk = self.src[i:i + 500]
        self.assertNotIn('"body"', blk)

    def test_질문에_얹어_보낸다(self):
        self.assertIn("skills=list(ASK_SKILLS)", self.src)


class 화면에서_넣고_뺀다(unittest.TestCase):

    def setUp(self):
        self.h = _src(os.path.join("static", "dashboard.html"))

    def test_단추와_파일칸이_있다(self):
        self.assertIn('id="anchatsk"', self.h)
        self.assertIn('id="anchatskf"', self.h)
        self.assertIn('accept=".md,.markdown,.txt"', self.h)

    def test_빼는_길이_있다(self):
        self.assertIn("anskx", self.h)
        self.assertIn("전부 빼기", self.h)
        self.assertIn("method:'DELETE'", self.h)

    def test_같은_파일을_다시_올릴_수_있다(self):
        """★input[type=file] 은 값이 남아 있으면 change 가 안 난다 —
        고쳐서 같은 이름으로 다시 올릴 때 아무 일도 안 일어난다."""
        i = self.h.index("id === 'anchatskf'")
        self.assertIn("value = ''", self.h[i:i + 300])

    def test_수치는_근거에서만_이라고_적어_둔다(self):
        i = self.h.index('id="anchatskbox"')
        self.assertIn("판단 기준", self.h[i:i + 500])


if __name__ == "__main__":
    unittest.main()
