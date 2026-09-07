# -*- coding: utf-8 -*-
"""위키에서 MD 다운로드가 안 되던 것.

무슨 일이었나
    「MD 다운로드」를 눌러도 아무 일도 안 났다. 까닭은 한 줄이다:

        slugify 가 한글을 살려 둔다        → 파일 이름이 '리센느.md'
        Content-Disposition 을 f-string 으로 손수 만들었다
        응답 머리는 latin-1 로만 실린다     (WSGI 규칙 · PEP 3333)
        → UnicodeEncodeError → 500

    한글 제목 페이지에서만 터지니 "가끔 안 된다" 로 보였다.

    RFC 6266/5987 이 이걸 위해 있다 — 옛 브라우저용 ASCII 이름(filename=)과
    진짜 이름(filename*=UTF-8'') 을 **둘 다** 준다.

★app.py 는 flask 를 쓴다 — 없는 곳에서는 순수 함수만 떼어 본다
  (test_wiki_md_page.py 와 같은 방법).
"""
import os
import re
import unittest
import urllib.parse

from . import util

APP = os.path.join(util.BASE, "LLM_WIKI_MCP", "amhs-llm-wiki", "app.py")


def _src():
    if not os.path.isfile(APP):
        raise unittest.SkipTest("위키 app.py 가 없다")
    with open(APP, encoding="utf-8") as f:
        return f.read()


def _load():
    """attach() 와 slugify() 만 떼어 온다."""
    src = _src()
    i = src.index("_ASCII_NAME = re.compile")
    j = src.index("def unique_page_slug")
    ns = {"re": re, "urllib": urllib}
    exec(compile(src[i:j], APP, "exec"), ns)        # noqa: S102
    return ns


class 머리에_실을_수_있어야_한다(unittest.TestCase):
    """WSGI 는 응답 머리를 latin-1 로 싣는다. 한 글자라도 벗어나면 500."""

    def setUp(self):
        self.ns = _load()

    def _h(self, name):
        return self.ns["attach"](name)["Content-Disposition"]

    def test_한글_이름이_터지지_않는다(self):
        for name in ("리센느.md", "RTX PRO 6000 Blackwell.md",
                     "버추얼 아바타 · 서윤.md", "M16HUB 임계값.md"):
            h = self._h(name)
            try:
                h.encode("latin-1")
            except UnicodeEncodeError as e:      # pragma: no cover
                self.fail("머리에 못 싣는다 ({}): {}".format(name, e))

    def test_예전_방식은_실제로_터진다(self):
        """고친 것이 맞는지 — 옛 코드를 그대로 재현해 본다."""
        with self.assertRaises(UnicodeEncodeError):
            "attachment; filename=리센느.md".encode("latin-1")

    def test_진짜_이름을_같이_준다(self):
        h = self._h("리센느.md")
        self.assertIn("filename*=UTF-8''", h)
        # 브라우저가 여기서 원래 이름을 되살린다
        got = h.split("filename*=UTF-8''", 1)[1]
        self.assertEqual(urllib.parse.unquote(got), "리센느.md")

    def test_옛_브라우저용_이름도_준다(self):
        h = self._h("리센느.md")
        m = re.search(r'filename="([^"]*)"', h)
        self.assertTrue(m, "filename= 이 없다: " + h)
        m.group(1).encode("latin-1")             # 여기가 터지면 안 된다
        self.assertNotEqual(m.group(1), "")

    def test_따옴표와_빈칸이_이름을_안_깬다(self):
        """따옴표를 안 감싸면 빈칸에서 이름이 잘린다."""
        h = self._h('RTX PRO 6000 "Blackwell".md')
        m = re.search(r'filename="([^"]*)"', h)
        self.assertTrue(m)
        self.assertNotIn('"', m.group(1))        # 감싼 따옴표를 깨면 안 된다
        self.assertNotIn(" ", m.group(1))

    def test_이름이_비면_기본값을_쓴다(self):
        for bad in ("", "   ", None, "한글", "···", ".md"):
            h = self.ns["attach"](bad, "page.md")["Content-Disposition"]
            m = re.search(r'filename="([^"]*)"', h)
            self.assertTrue(m.group(1), "ASCII 이름이 비었다: " + h)

    def test_확장자를_안_잃는다(self):
        """통째로 깎으면 '리센느.md' 가 'md' 가 된다 — 옛 브라우저에서
        확장자 없는 파일로 떨어진다."""
        for name in ("리센느.md", "버추얼 아바타 · 서윤.md"):
            h = self.ns["attach"](name, "page.md")["Content-Disposition"]
            a = re.search(r'filename="([^"]*)"', h).group(1)
            self.assertTrue(a.endswith(".md"), "확장자를 잃었다: " + a)
            self.assertNotEqual(a, "md")

    def test_영문이_섞여_있으면_살린다(self):
        h = self.ns["attach"]("M16HUB 임계값.md")["Content-Disposition"]
        a = re.search(r'filename="([^"]*)"', h).group(1)
        self.assertEqual(a, "M16HUB.md")

    def test_슬래시가_섞여도_경로가_안_된다(self):
        """받는 쪽에서 엉뚱한 자리에 떨어지면 안 된다."""
        h = self._h("../../etc/shadow-example.md")
        m = re.search(r'filename="([^"]*)"', h)
        self.assertNotIn("/", m.group(1))
        self.assertNotIn("..", m.group(1))


class 손으로_만든_머리가_안_남아_있다(unittest.TestCase):
    """한 군데라도 f-string 으로 다시 만들면 같은 사고가 돌아온다."""

    def test_전부_attach_를_쓴다(self):
        """주석은 빼고 **코드에서** 이 머리를 만드는 자리는 attach() 하나뿐."""
        code = [ln for ln in _src().splitlines()
                if not ln.strip().startswith("#")]
        hits = [ln for ln in code if "Content-Disposition" in ln]
        self.assertEqual(len(hits), 1,
                         "손으로 만든 머리가 남아 있다:\n  "
                         + "\n  ".join(h.strip()[:80] for h in hits))
        self.assertIn("return {\"Content-Disposition\":", hits[0],
                      "attach() 밖에서 만들고 있다: " + hits[0].strip())

    def test_원본_다운로드가_진짜_내려받는다(self):
        """as_attachment 를 안 주면 inline 이 된다 — 단추에는 '다운로드'
        라고 써 있는데 브라우저는 화면에 띄운다."""
        src = _src()
        i = src.index("def source_file")
        self.assertIn("as_attachment=True", src[i:i + 900])

    def test_파일_이름을_제목으로_준다(self):
        """slug 는 주소용으로 깎인 말이다 — 받아 놓고 보면 뭔지 모른다."""
        src = _src()
        i = src.index("def page_raw")
        blk = src[i:i + 800]
        self.assertIn('p["title"]', blk)


if __name__ == "__main__":
    unittest.main()
