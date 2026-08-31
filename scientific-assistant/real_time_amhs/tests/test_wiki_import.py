# -*- coding: utf-8 -*-
"""마크다운 → 위키 등록 (LLM_WIKI_MCP/wiki_import.py).

왜 만들었나
    지식은 이미 md 로 정리돼 있는데, 위키에 넣으려면 웹 폼에 **한 장씩 손으로
    붙여넣어야** 했다 (프론트매터를 제목·타입·태그·요약 칸에 나눠서). 네 장이면
    네 번이고, 고칠 때마다 또 네 번이다. 그러다 한 칸을 빠뜨린다.

★DB 를 직접 건드리지 않는다
    페이지 하나를 만들면 위키는 slug·revisions·파일쓰기·**청크/임베딩 색인**
    까지 같이 한다. DB 에 INSERT 만 하면 색인이 빠져서, DB 에는 있는데 화면
    검색에는 안 나오는 상태가 된다 — 제일 찾기 어려운 고장이다.
    그래서 사람이 폼에 넣는 것과 **똑같은 길**(POST /page/new · /page/N/edit)로
    보낸다. 이 파일이 그것을 못 박는다.
"""
import importlib.util
import os
import shutil
import sqlite3
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from . import util

WI_PATH = os.path.join(util.BASE, "LLM_WIKI_MCP", "wiki_import.py")
MD_DIR = os.path.join(util.BASE, "LLM_WIKI_MCP", "버츄얼 아바타")


def _load():
    spec = importlib.util.spec_from_file_location("wiki_import", WI_PATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class 가짜_위키(BaseHTTPRequestHandler):
    posts = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n).decode("utf-8")
        type(self).posts.append((self.path, urllib.parse.parse_qs(raw)))
        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()


class _Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(WI_PATH):
            raise unittest.SkipTest("wiki_import.py 가 없다")
        cls.wi = _load()
        cls.httpd = HTTPServer(("127.0.0.1", 0), 가짜_위키)
        cls.base = "http://127.0.0.1:{}".format(cls.httpd.server_address[1])
        cls.th = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.th.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        가짜_위키.posts = []
        self.dir = tempfile.mkdtemp(prefix="wimp")
        self.addCleanup(lambda: shutil.rmtree(self.dir, ignore_errors=True))
        self.db = os.path.join(self.dir, "wiki.db")
        c = sqlite3.connect(self.db)
        c.executescript(
            "CREATE TABLE domains(id INTEGER PRIMARY KEY, slug TEXT, name TEXT,"
            " description TEXT, created_at TEXT);"
            "CREATE TABLE pages(id INTEGER PRIMARY KEY, domain_id INT, title TEXT,"
            " slug TEXT, ptype TEXT, tags TEXT, summary TEXT, body_md TEXT,"
            " author TEXT, source_ids TEXT, created_at TEXT, updated_at TEXT);"
            "INSERT INTO domains VALUES(1,'virtual-avatar','버츄얼 아바타','','');")
        c.commit()
        c.close()
        self._old = os.environ.get("WIKI_DB")
        os.environ["WIKI_DB"] = self.db
        self.addCleanup(lambda: os.environ.__setitem__("WIKI_DB", self._old)
                        if self._old is not None
                        else os.environ.pop("WIKI_DB", None))

    def page(self, pid, title):
        c = sqlite3.connect(self.db)
        c.execute("INSERT INTO pages(id,domain_id,title,slug,ptype) "
                  "VALUES(?,1,?,'x','concept')", (pid, title))
        c.commit()
        c.close()

    def md(self, name, text):
        p = os.path.join(self.dir, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def run_it(self, *args):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = self.wi.main(list(args))
        return rc, buf.getvalue()


class 남의_위키를_조용히_안_고친다(_Base):

    def test_기본은_보기만_한다(self):
        """★--apply 없이 고쳐 버리면, 잘못 돌린 것을 되돌릴 수가 없다."""
        self.md("a.md", "---\ntitle: 가\n---\n본문")
        rc, out = self.run_it(self.dir, "--base", self.base,
                              "--domain", "버츄얼 아바타")
        self.assertEqual(rc, 0)
        self.assertEqual(가짜_위키.posts, [], "마른 실행인데 실제로 보냈다")
        self.assertIn("보기만", out)
        self.assertIn("--apply", out)

    def test_apply_면_실제로_보낸다(self):
        self.md("a.md", "---\ntitle: 가\n---\n본문")
        rc, _ = self.run_it(self.dir, "--base", self.base,
                            "--domain", "버츄얼 아바타", "--apply")
        self.assertEqual(rc, 0)
        self.assertEqual(len(가짜_위키.posts), 1)

    def test_없는_담당은_만들지_않는다(self):
        """★이름을 잘못 적으면 비슷한 담당이 하나 더 생기고, 나중에 어느
        쪽이 진짜인지 모르게 된다. 만들지 말고 멈춘다."""
        self.md("a.md", "---\ntitle: 가\ndomain: 없는담당\n---\n본문")
        rc, out = self.run_it(self.dir, "--base", self.base, "--apply")
        self.assertEqual(rc, 2)
        self.assertEqual(가짜_위키.posts, [])
        self.assertIn("없는 담당", out)
        self.assertIn("버츄얼 아바타", out)      # 있는 담당을 알려 준다


class 폼으로_보낸다(_Base):
    """★DB 에 INSERT 하면 색인(청크·임베딩)이 빠진다 — DB 에는 있는데 화면
    검색에는 안 나오는, 제일 찾기 어려운 상태가 된다."""

    def test_새_페이지는_page_new_로(self):
        self.md("a.md", "---\ntitle: 새 것\n---\n본문")
        self.run_it(self.dir, "--base", self.base, "--domain", "버츄얼 아바타",
                    "--apply")
        self.assertEqual(가짜_위키.posts[0][0], "/page/new")

    def test_이미_있으면_그_페이지를_고친다(self):
        """★같은 제목으로 또 만들면 위키에 쌍둥이가 생긴다."""
        self.page(12, "이미 있음")
        self.md("a.md", "---\ntitle: 이미 있음\n---\n새 본문")
        rc, out = self.run_it(self.dir, "--base", self.base,
                              "--domain", "버츄얼 아바타", "--apply")
        self.assertEqual(가짜_위키.posts[0][0], "/page/12/edit")
        self.assertIn("수정 (#12)", out)

    def test_DB_에_직접_안_쓴다(self):
        self.page(12, "이미 있음")
        self.md("a.md", "---\ntitle: 이미 있음\n---\n새 본문")
        self.run_it(self.dir, "--base", self.base, "--domain", "버츄얼 아바타",
                    "--apply")
        c = sqlite3.connect(self.db)
        body = c.execute("SELECT body_md FROM pages WHERE id=12").fetchone()[0]
        c.close()
        self.assertNotEqual(body, "새 본문", "DB 를 직접 고쳤다 — 색인이 빠진다")

    def test_읽기_전용으로_연다(self):
        with open(WI_PATH, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("mode=ro", src)


class 프론트매터를_제_칸에_넣는다(_Base):

    def fields(self, text, name="a.md"):
        self.md(name, text)
        self.run_it(self.dir, "--base", self.base, "--domain", "버츄얼 아바타",
                    "--apply")
        return 가짜_위키.posts[0][1]

    def test_제목_타입_태그_요약을_나눠_넣는다(self):
        f = self.fields("---\ntitle: 반송 장치\ntype: concept\n"
                        "tags: [VHL, LFT, CNV]\nsummary: 한 줄 요약\n---\n## 본문\n가나다")
        self.assertEqual(f["title"][0], "반송 장치")
        self.assertEqual(f["ptype"][0], "concept")
        self.assertEqual(f["tags"][0], "VHL, LFT, CNV")
        self.assertEqual(f["summary"][0], "한 줄 요약")
        self.assertIn("## 본문", f["body_md"][0])
        self.assertNotIn("title:", f["body_md"][0], "머리말이 본문에 섞였다")

    def test_모르는_타입은_concept_로(self):
        """★위키가 아는 타입이 아니면 저장이 조용히 concept 이 된다 —
        여기서 미리 맞춰 두면 화면과 어긋나지 않는다."""
        f = self.fields("---\ntitle: 가\ntype: 이상한것\n---\n본문")
        self.assertEqual(f["ptype"][0], "concept")

    def test_머리말이_없어도_넣는다(self):
        """★파일명이 제목이 된다. 넣다 말면 안 된다."""
        f = self.fields("그냥 본문만 있다", name="반송 메모.md")
        self.assertEqual(f["title"][0], "반송 메모")
        self.assertEqual(f["body_md"][0], "그냥 본문만 있다")

    def test_안내문은_페이지로_안_만든다(self):
        """★00_등록방법.md 는 사람이 읽는 안내지 지식이 아니다."""
        self.md("00_등록방법.md", "---\ntitle: 등록 방법\n---\n이렇게 하세요")
        self.md("01_진짜.md", "---\ntitle: 진짜\n---\n내용")
        self.run_it(self.dir, "--base", self.base, "--domain", "버츄얼 아바타",
                    "--apply")
        titles = [f["title"][0] for _p, f in 가짜_위키.posts]
        self.assertEqual(titles, ["진짜"])


class 실제_파일로_돌려_본다(_Base):
    """저장소에 들어 있는 '버츄얼 아바타' 네 장을 그대로 넣어 본다."""

    def setUp(self):
        super().setUp()
        if not os.path.isdir(MD_DIR):
            raise unittest.SkipTest("버츄얼 아바타 폴더가 없다")

    def test_네_장이_다_들어간다(self):
        rc, out = self.run_it(MD_DIR, "--base", self.base, "--apply")
        self.assertEqual(rc, 0, out)
        titles = sorted(f["title"][0] for _p, f in 가짜_위키.posts)
        self.assertEqual(titles, sorted([
            "M16 HUBROOM 개요", "반송 장치 종류와 역할",
            "FAB 간 연결 경로", "M16 HUBROOM 유의 지표"]))

    def test_호기명이_안_뭉개진다(self):
        """★`6ABL60~` 를 '6ABL 계열' 로 뭉개면 BM25 가 못 찾는다."""
        self.run_it(MD_DIR, "--base", self.base, "--apply")
        body = "\n".join(f["body_md"][0] for _p, f in 가짜_위키.posts)
        for code in ("4AFC3201", "4AFC3301", "4ALF", "4ABLD", "6ABL60",
                     "6ALF", "6ABL01", "WIS_M16WT", "6FIOB",
                     "SORTERWAITCOUNTOVER"):
            self.assertIn(code, body, code)

    def test_주신_지식이_다_들어_있다(self):
        """★원문에서 빠진 항목이 있으면 여기서 걸린다."""
        self.run_it(MD_DIR, "--base", self.base, "--apply")
        all_text = "\n".join(f["body_md"][0] + f["summary"][0]
                             for _p, f in 가짜_위키.posts)
        for word in ("M14A", "M14B", "M14분석실", "M16A", "M16B", "M16EUV",
                     "M16WT", "R4", "M10A", "HUBROOM",
                     "VHL", "OHT", "LFT", "CNV", "STK", "STB", "Sorter",
                     "MLUD", "ZT", "ZFS", "FIO", "FOSB", "FOUP"):
            self.assertIn(word, all_text, word)


if __name__ == "__main__":
    unittest.main()
