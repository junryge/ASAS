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


WIKI_MD = os.path.join(util.BASE, "LLM_WIKI_MCP", "버츄얼 아바타")


class 올릴_md_가_실제로_읽힌다(unittest.TestCase):
    """저장소에 넣어 둔 md 를 **위키 파서로 직접** 돌려 본다.

    ★머리말이 한 줄만 어긋나도 페이지가 아니라 소스로 들어간다. 그러면
      서윤이 readPage 로 못 읽어 "위키에 그런 내용이 없어요" 가 된다 —
      실제로 겪은 증상이다. 올리기 전에 여기서 잡는다.
    """

    def setUp(self):
        if not os.path.isdir(WIKI_MD):
            raise unittest.SkipTest("버츄얼 아바타 폴더가 없다")
        self.f = _load_pure()["parse_md_front"]
        self.files = sorted(n for n in os.listdir(WIKI_MD)
                            if n.endswith(".md") and not n.startswith("00_"))

    def test_올릴_문서가_있다(self):
        self.assertGreaterEqual(len(self.files), 4)

    def test_전부_머리말이_붙어_있다(self):
        for n in self.files:
            with open(os.path.join(WIKI_MD, n), encoding="utf-8") as fp:
                meta, body = self.f(fp.read())
            self.assertTrue(meta.get("title"), n + " : title 이 없다 → 소스로 들어간다")
            self.assertIn(meta.get("type"), ("concept", "entity"),
                          n + " : type 이 위키가 아는 값이 아니다")
            self.assertTrue(meta.get("domain"), n + " : domain 이 없다")
            self.assertTrue(meta.get("summary"), n + " : summary 가 없다")
            self.assertGreater(len(body), 200, n + " : 본문이 너무 짧다")

    def test_제목이_겹치지_않는다(self):
        """★같은 제목이면 위키가 **덮어쓴다**(upsert). 딴 문서끼리 겹치면
        하나가 사라진다."""
        seen = {}
        for n in self.files:
            with open(os.path.join(WIKI_MD, n), encoding="utf-8") as fp:
                t = self.f(fp.read())[0].get("title")
            self.assertNotIn(t, seen, "제목이 겹친다: %s ↔ %s" % (n, seen.get(t)))
            seen[t] = n

    def test_AMOS_문서가_다_있다(self):
        titles = set()
        for n in self.files:
            with open(os.path.join(WIKI_MD, n), encoding="utf-8") as fp:
                titles.add(self.f(fp.read())[0].get("title"))
        for t in ("AMOS 개요와 메뉴", "AMOS 모니터링 화면", "AMOS 이상 감지",
                  "AMOS Alarm 과 연락처", "AMOS AI Agent Chatbot"):
            self.assertIn(t, titles, t + " 문서가 없다")

    def test_링크가_실제_제목을_가리킨다(self):
        """★[[제목]] 이 없는 페이지를 가리키면 죽은 링크가 된다."""
        titles, links = set(), []
        for n in self.files:
            with open(os.path.join(WIKI_MD, n), encoding="utf-8") as fp:
                raw = fp.read()
            titles.add(self.f(raw)[0].get("title"))
            links += [(n, m) for m in re.findall(r"\[\[([^\]]+)\]\]", raw)]
        for n, t in links:
            self.assertIn(t, titles, "%s 안의 [[%s]] 가 없는 페이지다" % (n, t))

    def test_담당은_화면에서_고른다고_적어_둔다(self):
        """★upload() 는 폼의 domain_id 로 넣는다 — upsert_md_page 는
        meta['domain'] 을 **읽지 않는다.** 프론트매터를 고치라고 적어 두면
        사람이 헛수고를 한다 (전에 그렇게 적혀 있었다)."""
        src = _src()
        i = src.index("def upsert_md_page")
        body = src[i:src.index("@app.route(\"/upload\"")]
        self.assertNotIn("meta.get(\"domain\")", body)
        self.assertNotIn("meta['domain']", body)
        g = os.path.join(WIKI_MD, "00_등록방법.md")
        if not os.path.isfile(g):
            self.skipTest("등록방법이 없다")
        with open(g, encoding="utf-8") as fp:
            doc = fp.read()
        self.assertIn("업로드 화면에서 고른 것이 정해진다", doc)

    def test_지금_수치가_아니라고_적어_둔다(self):
        """★AMOS 는 화면 설명이다. 서윤이 이걸 실시간 값으로 읽으면
        "AMOS 가 Site 이상을 보여 준다" 를 "지금 이상이 있다" 로 답한다."""
        p = os.path.join(WIKI_MD, "06_AMOS-개요와-메뉴.md")
        if not os.path.isfile(p):
            self.skipTest("개요 문서가 없다")
        with open(p, encoding="utf-8") as fp:
            raw = fp.read()
        self.assertIn("지금 수치가 아니다", raw)


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
