"""모델이 낸 수정을 실제 파일에 반영 — 코딩 '에이전트' 의 나머지 반쪽.

읽기(프로젝트 첨부)는 되는데 쓰기가 없었다. 모델이 코드를 뱉으면 사람이
눈으로 골라 손으로 붙여 넣었다 — 그건 채팅이다.

★여기서 제일 중요한 건 '적용된다' 가 아니라 **'애매하면 안 한다'** 다.
  모델 출력은 못 믿는다. 경로가 워크스페이스 밖일 수도, SEARCH 가 원본과
  다를 수도, 여러 군데 걸릴 수도 있다. 엉뚱한 자리를 조용히 고쳐 놓는 것이
  제일 나쁜 결과다 — 사람이 알아채지 못한다.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from code_assist_v1 import edits as E                             # noqa: E402
from code_assist_v1.edits import parse_edits, apply_edits          # noqa: E402


def _safe_join(root: str, *paths: str) -> str | None:
    target = os.path.normpath(os.path.join(root, *paths))
    if not target.startswith(os.path.normpath(root)):
        return None
    return target


def _blk(path, search, replace):
    return (f"```edit:{path}\n<<<<<<< SEARCH\n{search}\n=======\n"
            f"{replace}\n>>>>>>> REPLACE\n```")


class Parse(unittest.TestCase):
    def test_수정_블록을_뽑는다(self):
        text = "설명입니다.\n\n" + _blk("a.py", "old", "new") + "\n\n더 설명."
        e = parse_edits(text)
        self.assertEqual(len(e), 1)
        # 줄 단위로 다루므로 끝 개행은 붙어 온다 (그래야 줄 경계로 맞춘다)
        self.assertEqual((e[0].kind, e[0].path, e[0].search, e[0].replace),
                         ("edit", "a.py", "old\n", "new\n"))

    def test_통짜_쓰기도_뽑는다(self):
        e = parse_edits("```write:new/x.py\nprint(1)\n```")
        self.assertEqual(e[0].kind, "write")
        self.assertEqual(e[0].content, "print(1)\n")

    def test_한_파일에_여러_군데(self):
        text = (_blk("a.py", "aaa", "AAA") + "\n" + _blk("a.py", "bbb", "BBB"))
        self.assertEqual(len(parse_edits(text)), 2)

    def test_평범한_코드블록은_안_건드린다(self):
        """```python 은 그냥 보여 주는 코드다 — 파일에 쓰면 안 된다."""
        self.assertEqual(parse_edits("```python\nprint(1)\n```"), [])

    def test_수정_없는_답변은_빈_목록(self):
        self.assertEqual(parse_edits("고칠 것 없습니다."), [])

    def test_형식이_어긋나면_거절한다(self):
        """edit 라 해 놓고 SEARCH/REPLACE 가 없으면 통짜로 덮어쓰지 않는다."""
        e = parse_edits("```edit:a.py\n그냥 코드\n```")
        self.assertEqual(len(e), 1)
        self.assertFalse(e[0].ok)
        self.assertIn("SEARCH", e[0].reason)


class Apply(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def _write(self, rel, body):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(body)
        return p

    def _read(self, rel):
        with open(os.path.join(self.root, rel), encoding="utf-8") as f:
            return f.read()

    def _apply(self, text, dry_run=False):
        return apply_edits(parse_edits(text), self.root, _safe_join, dry_run=dry_run)

    def test_실제로_고친다(self):
        self._write("a.py", "def f():\n    return 1\n")
        r = self._apply(_blk("a.py", "    return 1", "    return 2"))
        self.assertEqual(r.applied, 1, r.to_json())
        self.assertEqual(self._read("a.py"), "def f():\n    return 2\n")

    def test_미리보기는_파일을_안_건드린다(self):
        self._write("a.py", "x = 1\n")
        r = self._apply(_blk("a.py", "x = 1", "x = 2"), dry_run=True)
        self.assertEqual(r.applied, 1)
        self.assertTrue(r.edits[0].diff, "diff 가 비었다")
        self.assertEqual(self._read("a.py"), "x = 1\n", "미리보기인데 파일이 바뀌었다")

    def test_새_파일을_만든다(self):
        r = self._apply("```write:pkg/new.py\nprint(1)\n```")
        self.assertEqual(r.applied, 1)
        self.assertEqual(self._read("pkg/new.py"), "print(1)\n")

    # ── 여기부터가 핵심: 애매하면 안 한다 ──

    def test_원본과_다르면_거절한다(self):
        self._write("a.py", "x = 1\n")
        r = self._apply(_blk("a.py", "y = 99", "y = 100"))
        self.assertEqual(r.applied, 0)
        self.assertIn("다르다", r.edits[0].reason)
        self.assertEqual(self._read("a.py"), "x = 1\n")

    def test_여러_군데_걸리면_거절한다(self):
        """★첫 번째를 고르면 엉뚱한 자리를 고친다. 사람이 못 알아챈다."""
        self._write("a.py", "log()\nfoo()\nlog()\n")
        r = self._apply(_blk("a.py", "log()", "trace()"))
        self.assertEqual(r.applied, 0)
        self.assertIn("2군데", r.edits[0].reason)
        self.assertEqual(self._read("a.py"), "log()\nfoo()\nlog()\n")

    def test_워크스페이스_밖은_거절한다(self):
        r = self._apply("```write:../../evil.py\n해킹\n```")
        self.assertEqual(r.applied, 0)
        self.assertIn("밖", r.edits[0].reason)
        self.assertFalse(os.path.exists(os.path.join(self.root, "..", "evil.py")))

    def test_경로_검사가_safe_join에만_기대지_않는다(self):
        """★두 겹으로 막는다 — 바깥쪽(safe_join)이 뚫려도 안쪽이 잡아야 한다.

        safe_join 은 호출부가 넘겨 주는 물건이라 언젠가 약한 게 들어올 수
        있다. 느슨한 join 을 일부러 넣어 안쪽 검사만 시험한다.
        """
        # ★탈출 목표를 내가 만든 임시 폴더 안으로 둔다. '/evil.py' 같은
        #   전역 경로로 재면, 앞선 실행이 남긴 찌꺼기 때문에 멀쩡한 코드가
        #   실패한다(실제로 그렇게 한 번 헛짚었다).
        outer = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outer, True)
        inner = os.path.join(outer, "a", "b")
        os.makedirs(inner)
        loose = lambda root, *p: os.path.normpath(os.path.join(root, *p))  # noqa: E731
        r = apply_edits(parse_edits("```write:../../evil.py\n해킹\n```"),
                        inner, loose)
        self.assertEqual(r.applied, 0, r.to_json())
        self.assertIn("밖", r.edits[0].reason)
        self.assertFalse(os.path.exists(os.path.join(outer, "evil.py")))

    def test_없는_파일은_edit_못_한다(self):
        r = self._apply(_blk("없다.py", "a", "b"))
        self.assertEqual(r.applied, 0)
        self.assertIn("없는 파일", r.edits[0].reason)

    def test_한_파일_여러_수정이_쌓인다(self):
        self._write("a.py", "aaa\nbbb\n")
        r = self._apply(_blk("a.py", "aaa", "AAA") + "\n" + _blk("a.py", "bbb", "BBB"))
        self.assertEqual(r.applied, 2, r.to_json())
        self.assertEqual(self._read("a.py"), "AAA\nBBB\n")

    def test_하나가_실패해도_나머지는_적용된다(self):
        self._write("a.py", "aaa\n")
        self._write("b.py", "bbb\n")
        r = self._apply(_blk("a.py", "aaa", "AAA") + "\n" + _blk("b.py", "없는내용", "x"))
        self.assertEqual((r.applied, r.failed), (1, 1), r.to_json())
        self.assertEqual(self._read("a.py"), "AAA\n")
        self.assertEqual(self._read("b.py"), "bbb\n")

    def test_줄_끝_공백만_다르면_봐준다(self):
        """모델이 뒤쪽 공백을 흘리는 건 흔하다 — 이건 같은 코드다."""
        self._write("a.py", "def f():   \n    return 1\n")
        r = self._apply(_blk("a.py", "def f():\n    return 1", "def f():\n    return 2"))
        self.assertEqual(r.applied, 1, r.to_json())
        self.assertIn("return 2", self._read("a.py"))

    def test_들여쓰기가_다르면_거절한다(self):
        """★앞쪽 들여쓰기는 파이썬에서 뜻이 다르다 — 봐주면 안 된다."""
        self._write("a.py", "if x:\n        deep()\n")
        r = self._apply(_blk("a.py", "    deep()", "    shallow()"))
        self.assertEqual(r.applied, 0, r.to_json())

    def test_바뀐_게_없으면_그렇다고_한다(self):
        self._write("a.py", "x = 1\n")
        r = self._apply(_blk("a.py", "x = 1", "x = 1"))
        self.assertEqual(r.edits[0].reason, "바뀐 것 없음")

    def test_무엇이_바뀌는지_diff로_보여_준다(self):
        self._write("a.py", "x = 1\n")
        r = self._apply(_blk("a.py", "x = 1", "x = 2"), dry_run=True)
        d = r.edits[0].diff
        self.assertIn("-x = 1", d)
        self.assertIn("+x = 2", d)


class Endpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import demos_v1
            cls.client = demos_v1.create_app().test_client()
        except Exception as e:
            raise unittest.SkipTest(f"앱을 못 띄운다: {e}")

    def setUp(self):
        from code_assist_v1.config import WORKSPACE_DIR
        self.ws = os.path.join(WORKSPACE_DIR, "pytest_edits")
        shutil.rmtree(self.ws, ignore_errors=True)
        os.makedirs(self.ws, exist_ok=True)
        self.addCleanup(shutil.rmtree, self.ws, True)
        with open(os.path.join(self.ws, "a.py"), "w", encoding="utf-8") as f:
            f.write("x = 1\n")

    def test_미리보기_그리고_적용(self):
        text = _blk("a.py", "x = 1", "x = 2")
        p = self.client.post("/code/api/code/edits/preview",
                             json={"text": text, "user_id": "pytest_edits"}).get_json()
        self.assertEqual(p["applied"], 1, p)
        self.assertTrue(p["dry_run"])
        with open(os.path.join(self.ws, "a.py"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "x = 1\n", "미리보기인데 파일이 바뀌었다")

        a = self.client.post("/code/api/code/edits/apply",
                             json={"text": text, "user_id": "pytest_edits"}).get_json()
        self.assertEqual(a["applied"], 1, a)
        with open(os.path.join(self.ws, "a.py"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "x = 2\n")

    def test_수정_블록이_없으면_그렇다고_한다(self):
        r = self.client.post("/code/api/code/edits/apply",
                             json={"text": "그냥 설명", "user_id": "pytest_edits"}).get_json()
        self.assertEqual(r["applied"], 0)
        self.assertIn("없다", r["message"])


if __name__ == "__main__":
    unittest.main()


class 적용_기록(unittest.TestCase):
    """★한 번 적용한 수정을 또 적용하면 안 된다.

    edit 는 SEARCH 가 이미 바뀌어 있어 "파일 내용과 다르다" 로 실패하고 —
    사람은 그걸 보고 '고장났나' 한다. write 는 더 나쁘다: 그 뒤에 손으로
    고친 것을 조용히 덮어쓴다.
    """

    BLOCK = (
        "```edit:app/main.py\n"
        "<<<<<<< SEARCH\n"
        "def hello():\n"
        "    return 1\n"
        "=======\n"
        "def hello():\n"
        "    return 2\n"
        ">>>>>>> REPLACE\n"
        "```\n"
    )

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="applied_")
        os.makedirs(os.path.join(self.root, "app"), exist_ok=True)
        with open(os.path.join(self.root, "app", "main.py"), "w",
                  encoding="utf-8") as f:
            f.write("def hello():\n    return 1\n")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def apply(self, text=None, **kw):
        return E.apply_edits(E.parse_edits(text or self.BLOCK),
                             self.root, _safe_join, **kw)

    def test_처음엔_적용된다(self):
        r = self.apply()
        self.assertEqual(r.applied, 1)
        self.assertFalse(r.edits[0].already)
        with open(os.path.join(self.root, "app", "main.py"), encoding="utf-8") as f:
            self.assertIn("return 2", f.read())

    def test_두_번째는_이미_적용됨으로_넘어간다(self):
        self.apply()
        r = self.apply()
        e = r.edits[0]
        self.assertTrue(e.already)
        self.assertEqual(e.reason, "이미 적용됨")
        self.assertEqual(r.to_json()["already"], 1)

    def test_두_번째에_파일을_안_건드린다(self):
        """★write 였다면 그 뒤 손수정을 덮어썼을 자리다."""
        self.apply()
        p = os.path.join(self.root, "app", "main.py")
        with open(p, "w", encoding="utf-8") as f:
            f.write("def hello():\n    return 2  # 사람이 손으로 덧붙임\n")
        before = open(p, encoding="utf-8").read()
        self.apply()
        self.assertEqual(open(p, encoding="utf-8").read(), before,
                         "이미 적용한 수정이 손수정을 덮어썼다")

    def test_write도_두_번_안_쓴다(self):
        w = "```write:app/new.py\nx = 1\n```\n"
        self.assertEqual(self.apply(w).applied, 1)
        p = os.path.join(self.root, "app", "new.py")
        with open(p, "w", encoding="utf-8") as f:
            f.write("x = 1\ny = 2  # 사람이 덧붙임\n")
        self.apply(w)
        self.assertIn("사람이 덧붙임", open(p, encoding="utf-8").read())

    def test_미리보기에도_이미_적용됨이_보인다(self):
        """화면이 '적용' 버튼을 다시 띄우면 안 된다."""
        self.apply()
        r = self.apply(dry_run=True)
        self.assertTrue(r.edits[0].already)

    def test_force면_다시_적용한다(self):
        """일부러 되돌리고 싶은 사람은 있을 수 있다 — 길은 남겨 둔다."""
        self.apply()
        p = os.path.join(self.root, "app", "main.py")
        with open(p, "w", encoding="utf-8") as f:
            f.write("def hello():\n    return 1\n")
        r = self.apply(force=True)
        self.assertFalse(r.edits[0].already)
        self.assertIn("return 2", open(p, encoding="utf-8").read())

    def test_다른_수정은_안_막는다(self):
        self.apply()
        other = self.BLOCK.replace("return 2", "return 3")
        self.assertFalse(self.apply(other).edits[0].already)

    def test_기록이_사라져도_안_죽는다(self):
        self.apply()
        os.remove(E.applied_path(self.root))
        self.assertIsInstance(E.applied_sigs(self.root), set)

    def test_기록_파일은_내려받기에_안_들어간다(self):
        """내부 기록이지 사용자 코드가 아니다."""
        self.apply()
        self.assertTrue(os.path.isfile(E.applied_path(self.root)))
        self.assertEqual(E.APPLIED_FILE, ".applied.json")
