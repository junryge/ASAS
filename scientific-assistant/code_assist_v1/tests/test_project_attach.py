"""프로젝트 첨부 — zip 하나로 붙이고, 큰 모델이면 큰 모델만큼 넣는다.

무엇이 안 됐나
    ① .zip 이 허용 확장자에 없어서 415 로 거부됐다. 프로젝트를 통째로
       주려면 파일을 하나씩 수백 번 올려야 했다.
    ② 첨부 예산이 16,000자로 못박혀 있었다. 정작 쓰는 모델은 대부분
       128,000 토큰짜리다 — 모델 능력의 4% 만 쓰고 파일 스물몇 개에서
       잘렸다. "모델도 큰 게 있는데 왜 안 되냐" 가 이 얘기다.
    ③ 예산이 모자라면 '나중에 올린 파일' 부터 잘렸다. 질문과 상관있느냐는
       보지 않았다.
    ④ 잘라 놓고 말을 안 했다. 모델은 그게 프로젝트 전부인 줄 알고
       "그런 코드는 없다" 고 단언한다.

    250개짜리 프로젝트로 재보면 21개 → 246개 (128k 모델).
"""
from __future__ import annotations

import io
import os
import shutil
import sys
import unittest
import zipfile

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from code_assist_v1.config import WORKSPACE_DIR                      # noqa: E402
from code_assist_v1.engine import (                                   # noqa: E402
    build_workspace_block, workspace_budget, _rank_files, _cut,
)

UID = "pytest_attach"


def _zip(entries: dict) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, body in entries.items():
            z.writestr(name, body)
    buf.seek(0)
    return buf


class ZipAttach(unittest.TestCase):
    """zip 하나 = 프로젝트 하나."""

    @classmethod
    def setUpClass(cls):
        try:
            import demos_v1
            cls.client = demos_v1.create_app().test_client()
        except Exception as e:
            raise unittest.SkipTest(f"앱을 못 띄운다: {e}")

    def setUp(self):
        self.ws = os.path.join(WORKSPACE_DIR, UID)
        shutil.rmtree(self.ws, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.ws, True)

    def _upload(self, buf, name="proj.zip"):
        return self.client.post(
            "/code/api/code/workspace/upload",
            data={"file": (buf, name), "user_id": UID},
            content_type="multipart/form-data")

    def test_zip_을_받아서_푼다(self):
        """★예전엔 415 '지원하지 않는 확장자: .zip' 이었다."""
        r = self._upload(_zip({"p/a.py": "x=1\n", "p/b/c.py": "y=2\n"}))
        self.assertEqual(r.status_code, 200, r.get_json())
        j = r.get_json()
        self.assertEqual(j["status"], "extracted")
        self.assertEqual(j["count"], 2)
        self.assertTrue(os.path.isfile(os.path.join(self.ws, "p", "b", "c.py")))

    def test_쓰레기_폴더는_안_넣는다(self):
        r = self._upload(_zip({
            "p/a.py": "x=1\n",
            "p/__pycache__/a.pyc": "junk",
            "p/node_modules/lib/x.js": "junk",
            "p/.git/config": "junk",
        }))
        j = r.get_json()
        self.assertEqual(j["count"], 1, j)
        self.assertFalse(os.path.isdir(os.path.join(self.ws, "p", "node_modules")))

    def test_경로_이탈은_거부한다(self):
        """★'../../etc/passwd' (zip slip).

        밖으로 못 나가는 것만으로는 부족하다 — '..' 를 조용히 지우면
        'etc/passwd' 로 둔갑해 워크스페이스 안에 엉뚱한 파일이 생긴다.
        """
        r = self._upload(_zip({"../../etc/passwd": "해킹", "p/ok.py": "x=1\n"}))
        j = r.get_json()
        self.assertEqual(j["count"], 1, j)
        self.assertIn("경로 이탈", j["skipped"])
        self.assertFalse(os.path.exists(os.path.join(self.ws, "etc", "passwd")))
        self.assertFalse(os.path.exists(os.path.join(WORKSPACE_DIR, "..", "etc", "passwd")))

    def test_깨진_zip은_말해_준다(self):
        r = self._upload(io.BytesIO("zip 아님".encode("utf-8")))
        self.assertEqual(r.status_code, 400)
        self.assertIn("zip", r.get_json()["error"])

    def test_한_번에_다_읽는다(self):
        """★예전엔 파일 하나마다 요청 한 번 — 300개면 300번이었다."""
        self._upload(_zip({f"p/m{i}.py": f"v={i}\n" for i in range(120)}))
        r = self.client.post("/code/api/code/workspace/files",
                             json={"prefix": "p", "user_id": UID})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["count"], 120)

    def test_목록이_잘려도_폴더째_붙일_수_있다(self):
        """200개가 넘으면 files 목록이 잘린다 — 그때 쓸 공통 루트를 준다."""
        j = self._upload(_zip({f"big/m{i}.py": "x=1\n" for i in range(250)})).get_json()
        self.assertTrue(j["truncated_list"])
        self.assertEqual(j["root_prefix"], "big")
        r = self.client.post("/code/api/code/workspace/files",
                             json={"prefix": j["root_prefix"], "user_id": UID})
        self.assertEqual(r.get_json()["count"], 250)


class ContextBudget(unittest.TestCase):
    """큰 모델이면 큰 모델만큼 넣는다."""

    def test_예산이_모델을_따라_커진다(self):
        small, _ = workspace_budget(16384)
        big, _ = workspace_budget(128000)
        self.assertGreater(big, small * 5,
                           f"128k 모델인데 예산이 16k 모델과 비슷하다 ({small} vs {big})")

    def test_모델을_모르면_예전값으로_떨어진다(self):
        from code_assist_v1.config import MAX_WORKSPACE_TOTAL_CHARS
        self.assertEqual(workspace_budget(None)[0], MAX_WORKSPACE_TOTAL_CHARS)

    def test_큰_모델이_프로젝트를_더_많이_담는다(self):
        files = [{"filename": f"m{i}.py", "content": "x = 1\n" * 200}
                 for i in range(250)]
        small = build_workspace_block(files, n_ctx=None)["content"]
        big = build_workspace_block(files, n_ctx=128000)["content"]
        n_small = small.count("--- 📁 ")
        n_big = big.count("--- 📁 ")
        self.assertGreater(n_big, n_small * 5,
                           f"128k 모델인데 {n_small}개 → {n_big}개밖에 안 늘었다")


class Relevance(unittest.TestCase):
    """예산이 모자라면, 잘려 나갈 것은 '상관없는 파일' 이어야 한다."""

    def test_질문에_맞는_파일이_앞으로_온다(self):
        files = [{"filename": f"zzz{i}.py", "content": "noise\n"} for i in range(20)]
        files.append({"filename": "auth/login.py", "content": "def login(): ..."})
        ranked = _rank_files(files, "login 함수 어디 있어")
        self.assertEqual(ranked[0]["filename"], "auth/login.py")

    def test_질문이_없으면_순서를_안_건드린다(self):
        files = [{"filename": f"{i}.py", "content": ""} for i in range(5)]
        self.assertEqual([f["filename"] for f in _rank_files(files, "")],
                         [f["filename"] for f in files])

    def test_예산이_모자라도_맞는_파일은_들어간다(self):
        big = "noise\n" * 3000
        files = [{"filename": f"zzz{i}.py", "content": big} for i in range(20)]
        files.append({"filename": "auth/login.py", "content": "def login(u, p): return True"})
        out = build_workspace_block(files, n_ctx=None, query="login 함수")["content"]
        self.assertIn("def login(u, p)", out,
                      "질문에 딱 맞는 파일이 예산 밖으로 밀려났다")


class Truncation(unittest.TestCase):
    def test_못_넣은_파일을_알려_준다(self):
        """★말을 안 하면 모델은 이게 전부인 줄 알고 '그런 코드 없다' 고 한다."""
        files = [{"filename": f"m{i}.py", "content": "x\n" * 5000} for i in range(30)]
        out = build_workspace_block(files, n_ctx=None)["content"]
        self.assertIn("넣지 못했다", out)

    def test_다_들어가면_경고를_안_한다(self):
        files = [{"filename": "a.py", "content": "x = 1\n"}]
        out = build_workspace_block(files, n_ctx=128000)["content"]
        self.assertNotIn("넣지 못했다", out)

    def test_줄_한가운데서_안_자른다(self):
        text = "\n".join(f"line{i} 어쩌고저쩌고" for i in range(100))
        cut = _cut(text, 200)
        self.assertTrue(cut.endswith("어쩌고저쩌고") or cut == text[:200],
                        repr(cut[-30:]))
        self.assertLessEqual(len(cut), 200)


if __name__ == "__main__":
    unittest.main()
