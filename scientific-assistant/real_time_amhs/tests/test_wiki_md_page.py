# -*- coding: utf-8 -*-
"""위키에 md 를 넣으면 **페이지**로 등록된다 (소스가 아니라).

왜 이걸 못 박나
    실제로 겪었다. md 를 위키에 올렸는데 활동 로그가 이랬다:

        2026-09-01 08:45  upload  Virtual_Avatar **소스** 1건  FAB 간 연결 경로

    소스로 들어간 것이다. 그런데 위키에서 페이지와 소스는 **읽는 도구가
    다르다**(readPage · readSource). 서윤은 페이지만 읽고 있어서
    "위키에 그런 내용이 없어요" 라고 답했다 — 멀쩡히 올려 뒀는데.

    소스는 원본 자료 자리다. 화면 편집도, [[링크]]도, 린트도 안 된다.
    머리말(title/summary/tags)이 붙은 md 는 사람이 **페이지로 쓰라고** 쓴
    글이므로 페이지로 넣는다.

★app.py 는 flask 를 쓴다 — 없는 곳에서는 순수 함수만 본다.
"""
import os
import re
import unittest

from . import util

APP = os.path.join(util.BASE, "LLM_WIKI_MCP", "amhs-llm-wiki", "app.py")


def _src():
    if not os.path.isfile(APP):
        raise unittest.SkipTest("위키 app.py 가 없다")
    with open(APP, encoding="utf-8") as f:
        return f.read()


def _load_pure():
    """flask 없이 **머리말 파서만** 떼어 온다 (app.py 를 통째로 import 하면
    flask 가 필요하다 — 폐쇄망 시험 PC 에는 없을 수 있다)."""
    src = _src()
    i = src.index("MD_FM_RE = re.compile")
    j = src.index("def upsert_md_page")
    ns = {"re": re}
    exec(compile(src[i:j], APP, "exec"), ns)      # noqa: S102
    return ns


class 머리말을_읽는다(unittest.TestCase):

    def setUp(self):
        self.f = _load_pure()["parse_md_front"]

    def test_제목_타입_태그_요약을_나눈다(self):
        meta, body = self.f("---\ntitle: 반송 장치 종류와 역할\ntype: concept\n"
                            "domain: Virtual_Avatar\n"
                            "tags: [VHL, OHT, LFT]\nsummary: 한 줄 요약\n"
                            "---\n\n## 핵심 용어\nLFT 는 리프터다.")
        self.assertEqual(meta["title"], "반송 장치 종류와 역할")
        self.assertEqual(meta["type"], "concept")
        self.assertEqual(meta["tags"], "VHL, OHT, LFT")
        self.assertEqual(meta["summary"], "한 줄 요약")
        self.assertTrue(body.startswith("## 핵심 용어"))
        self.assertNotIn("title:", body, "머리말이 본문에 섞였다")

    def test_머리말이_없으면_빈_손으로_준다(self):
        """★제목을 지어내면 안 된다. 없으면 없다고 해야 소스로 넘어간다."""
        meta, body = self.f("그냥 메모다\n\n두 번째 줄")
        self.assertEqual(meta, {})
        self.assertIn("그냥 메모다", body)

    def test_빈_머리말도_안_터진다(self):
        meta, _b = self.f("---\n---\n본문")
        self.assertEqual(meta, {})

    def test_이상한_줄은_지나친다(self):
        meta, _b = self.f("---\ntitle: 가\n# 주석\n이건 콜론이 없다\n---\n본문")
        self.assertEqual(meta["title"], "가")

    def test_따옴표와_대괄호를_벗긴다(self):
        meta, _b = self.f("---\ntitle: '따옴표'\ntags: ['가', \"나\"]\n---\nx")
        self.assertEqual(meta["title"], "따옴표")
        self.assertEqual(meta["tags"], "가, 나")


class 페이지로_넣는_길이_있다(unittest.TestCase):
    """소스 코드로 확인 — flask 없이 돌아야 하므로 동작은 위 파서만 본다."""

    def test_업로드가_md_를_페이지로_돌린다(self):
        s = _src()
        i = s.index('def upload():')
        blk = s[i:i + 3000]
        self.assertIn("md_as_page", blk, "페이지로 넣는 길이 없다")
        self.assertIn("parse_md_front", blk)
        self.assertIn("upsert_md_page", blk)
        self.assertIn('(".md", ".markdown")', blk)

    def test_같은_제목이면_고친다(self):
        """★새로 만들기만 하면 두 번 올릴 때마다 쌍둥이가 생긴다."""
        s = _src()
        i = s.index("def upsert_md_page")
        blk = s[i:i + 2500]
        self.assertIn("SELECT id FROM pages WHERE domain_id=? AND title=?", blk)
        self.assertIn("UPDATE pages SET", blk)
        self.assertIn("INSERT INTO pages", blk)

    def test_이력과_색인을_같이_남긴다(self):
        """★DB 만 고치면 화면 검색에서 안 나온다 (색인이 안 따라간다)."""
        s = _src()
        i = s.index("def upsert_md_page")
        blk = s[i:i + 2500]
        self.assertIn("INSERT INTO revisions", blk)
        self.assertIn("write_page_file(pid)", blk)

    def test_머리말이_없으면_소스로_넣고_말해_준다(self):
        """★제목을 지어내면 안 된다. 소스로 넣되 왜 그런지 알려 준다."""
        s = _src()
        i = s.index('def upload():')
        blk = s[i:i + 3000]
        self.assertIn("머리말", blk)
        self.assertIn("f.stream.seek(0)", blk, "파일을 다 읽고 소스로 넘겼다")

    def test_로그에_페이지라고_적는다(self):
        """★무엇을 넣어도 '소스 N건' 이면 활동 로그로 확인이 안 된다 —
        이번 사고를 알아챈 것이 바로 그 로그였다."""
        s = _src()
        self.assertIn('add_log("page-import"', s)

    def test_화면에_그_칸이_있다(self):
        s = _src()
        self.assertIn('name="md_as_page"', s)
        self.assertIn("페이지로</b> 등록", s)
        # 이미지 설명이 왜 필수인지도 적어 둔다 (그림은 텍스트가 없다)
        self.assertIn("이미지는 필수", s)


if __name__ == "__main__":
    unittest.main()
