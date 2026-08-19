"""변경분만 받기 — 프로젝트를 통째로 다시 받는 건 낭비다.

무엇이 없었나
    수정을 적용해도 결과를 가져갈 방법이 아예 없었다. 워크스페이스에는
    쓰였는데, 그걸 내 PC 로 가져오려면 파일을 하나씩 열어 복사해야 했다.

    그리고 300개짜리 프로젝트에서 두 파일을 고쳤을 때 300개를 통째로 다시
    받는 건 낭비다. 실측: 변경분 zip 은 전체의 **0.37%**.

★파일 mtime 만으로는 '내가 고친 것' 과 '올릴 때부터 있던 것' 을 구분할 수
  없다 (zip 을 풀면 전부 방금 시각이 된다). 그래서 적용할 때 직접 남긴다.
"""
from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from code_assist_v1.edits import (                                   # noqa: E402
    parse_edits, apply_edits, changed_files, read_changes, CHANGES_FILE,
)


def _safe_join(root: str, *paths: str) -> str | None:
    t = os.path.normpath(os.path.join(root, *paths))
    return t if t.startswith(os.path.normpath(root)) else None


def _blk(path, search, replace):
    return (f"```edit:{path}\n<<<<<<< SEARCH\n{search}\n=======\n"
            f"{replace}\n>>>>>>> REPLACE\n```")


class Tracking(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def _write(self, rel, body):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(body)

    def _apply(self, text):
        return apply_edits(parse_edits(text), self.root, _safe_join)

    def test_고친_파일을_기록한다(self):
        self._write("a.py", "x = 1\n")
        self._apply(_blk("a.py", "x = 1", "x = 2"))
        ch = changed_files(self.root)
        self.assertEqual([c["path"] for c in ch], ["a.py"])
        self.assertEqual(ch[0]["kind"], "수정")

    def test_새_파일도_기록한다(self):
        self._apply("```write:new/x.py\nprint(1)\n```")
        ch = changed_files(self.root)
        self.assertEqual(ch[0]["kind"], "새 파일")

    def test_안_고친_파일은_기록에_없다(self):
        """★올릴 때부터 있던 파일까지 '변경' 이면 변경분이 전체가 된다."""
        self._write("a.py", "x = 1\n")
        self._write("b.py", "y = 1\n")
        self._apply(_blk("a.py", "x = 1", "x = 2"))
        self.assertEqual([c["path"] for c in changed_files(self.root)], ["a.py"])

    def test_같은_파일을_여러_번_고쳐도_한_줄이다(self):
        """★다섯 번 고쳤다고 목록에 다섯 줄 나오면 못 읽는다 — 횟수로 센다."""
        self._write("a.py", "1\n2\n3\n")
        self._apply(_blk("a.py", "1", "one"))
        self._apply(_blk("a.py", "2", "two"))
        ch = changed_files(self.root)
        self.assertEqual(len(ch), 1)
        self.assertEqual(ch[0]["count"], 2)

    def test_거절된_수정은_기록에_없다(self):
        """★적용 안 된 걸 '변경' 으로 세면 받아 봐야 옛 내용이다."""
        self._write("a.py", "x = 1\n")
        self._apply(_blk("a.py", "없는코드", "y"))
        self.assertEqual(changed_files(self.root), [])

    def test_지워진_파일은_목록에서_빠진다(self):
        """받을 게 없는 걸 목록에 두면 zip 이 비어 나온다."""
        self._apply("```write:gone.py\nx=1\n```")
        os.remove(os.path.join(self.root, "gone.py"))
        self.assertEqual(changed_files(self.root), [])

    def test_기록이_무한정_쌓이지_않는다(self):
        self._write("a.py", "0\n")
        for i in range(1, 60):
            self._apply(_blk("a.py", str(i - 1), str(i)))
        self.assertLessEqual(len(read_changes(self.root)), 500)

    def test_미리보기는_기록하지_않는다(self):
        """★파일을 안 건드렸는데 '변경' 으로 세면 안 된다."""
        self._write("a.py", "x = 1\n")
        apply_edits(parse_edits(_blk("a.py", "x = 1", "x = 2")),
                    self.root, _safe_join, dry_run=True)
        self.assertEqual(changed_files(self.root), [])


class DownloadRoutes(unittest.TestCase):
    UID = "pytest_dl"

    @classmethod
    def setUpClass(cls):
        try:
            import demos_v1
            cls.client = demos_v1.create_app().test_client()
        except Exception as e:
            raise unittest.SkipTest(f"앱을 못 띄운다: {e}")

    def setUp(self):
        from code_assist_v1.config import WORKSPACE_DIR
        self.ws = os.path.join(WORKSPACE_DIR, self.UID)
        shutil.rmtree(self.ws, ignore_errors=True)
        os.makedirs(self.ws, exist_ok=True)
        self.addCleanup(shutil.rmtree, self.ws, True)

    def _upload(self, entries):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for k, v in entries.items():
                z.writestr(k, v)
        buf.seek(0)
        return self.client.post("/code/api/code/workspace/upload",
                                data={"file": (buf, "p.zip"), "user_id": self.UID},
                                content_type="multipart/form-data")

    def _names(self, resp):
        return sorted(zipfile.ZipFile(io.BytesIO(resp.data)).namelist())

    def test_전체를_받는다(self):
        self._upload({"p/a.py": "x=1\n", "p/b.py": "y=1\n"})
        r = self.client.get(f"/code/api/code/workspace/download?user_id={self.UID}")
        self.assertEqual(r.status_code, 200, r.data[:200])
        self.assertEqual(self._names(r), ["p/a.py", "p/b.py"])

    def test_고친_것만_받는다(self):
        """★핵심. 300개 중 둘을 고쳤으면 둘만."""
        self._upload({f"p/m{i}.py": f"v = {i}\n" for i in range(20)})
        self.client.post("/code/api/code/edits/apply", json={
            "user_id": self.UID,
            "text": _blk("p/m3.py", "v = 3", "v = 33") + "\n```write:p/new.py\nz=1\n```"})
        r = self.client.get(
            f"/code/api/code/workspace/download?user_id={self.UID}&changed=1")
        self.assertEqual(r.status_code, 200, r.data[:200])
        self.assertEqual(self._names(r), ["p/m3.py", "p/new.py"])

    def test_고친_게_없으면_그렇다고_한다(self):
        """★빈 zip 을 주면 '고장' 으로 읽힌다."""
        self._upload({"p/a.py": "x=1\n"})
        r = self.client.get(
            f"/code/api/code/workspace/download?user_id={self.UID}&changed=1")
        self.assertEqual(r.status_code, 404)
        self.assertIn("고친 파일이 없", r.get_json()["error"])

    def test_내부_기록은_안_들어간다(self):
        """.edits.json 은 우리 살림이지 사용자 코드가 아니다."""
        self._upload({"p/a.py": "x=1\n"})
        self.client.post("/code/api/code/edits/apply", json={
            "user_id": self.UID, "text": _blk("p/a.py", "x=1", "x=2")})
        r = self.client.get(f"/code/api/code/workspace/download?user_id={self.UID}")
        self.assertNotIn(CHANGES_FILE, self._names(r))

    def test_파일_하나만_받는다(self):
        self._upload({"p/a.py": "x=1\n"})
        r = self.client.get(
            f"/code/api/code/workspace/download?user_id={self.UID}&path=p/a.py")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data.decode(), "x=1\n")

    def test_워크스페이스_밖은_못_받는다(self):
        r = self.client.get(
            f"/code/api/code/workspace/download?user_id={self.UID}&path=../../etc/passwd")
        self.assertEqual(r.status_code, 404)

    def test_변경_목록_엔드포인트(self):
        self._upload({"p/a.py": "x=1\n"})
        self.client.post("/code/api/code/edits/apply", json={
            "user_id": self.UID, "text": _blk("p/a.py", "x=1", "x=2")})
        d = self.client.get(
            f"/code/api/code/workspace/changes?user_id={self.UID}").get_json()
        self.assertEqual(d["count"], 1)
        self.assertEqual(d["items"][0]["path"], "p/a.py")
        self.assertGreater(d["items"][0]["size"], 0)


class PromptAndUi(unittest.TestCase):
    """전체 코드를 다시 뱉지 말라고 계약에 박아 뒀는지."""

    def test_바뀐_부분만_내놓으라고_시킨다(self):
        from code_assist_v1.prompts import EDIT_PROTOCOL
        self.assertIn("바뀌는 부분만", EDIT_PROTOCOL)
        self.assertIn("전체 코드 보여줘", EDIT_PROTOCOL,
                      "사용자가 직접 요청할 때만 전문을 보여 주라고 해야 한다")

    def test_길면_접는다(self):
        """★프롬프트로 시켜도 모델이 어길 수 있다 — 화면 쪽 안전장치."""
        p = os.path.join(_ROOT, "code_assist_v1", "static", "chat.js")
        with open(p, encoding="utf-8") as f:
            js = f.read()
        self.assertIn("function collapseLongCode", js)
        self.assertIn("CODE_FOLD_LINES", js)

    def test_적용_후_바로_받을_수_있다(self):
        p = os.path.join(_ROOT, "code_assist_v1", "static", "chat.js")
        with open(p, encoding="utf-8") as f:
            js = f.read()
        self.assertIn("고친 파일만 받기", js)
        self.assertIn("download?changed=1", js)


if __name__ == "__main__":
    unittest.main()


class 받기버튼이_안_사라진다(unittest.TestCase):
    """★받기 링크가 '그 메시지' 안에 DOM 으로만 붙어 있었다. 세션을 다시
    열면 Chat.clear() 로 메시지를 통째로 지우고 저장된 본문만 다시 그리므로,
    받기 줄은 같이 사라졌다. 새로고침도 마찬가지다 — 다시 받을 방법이 없었다.

    화면 동작이라 브라우저로 확인했고, 여기서는 그 구조가 되돌아가지 않게
    잠근다 (정적 검사임을 밝혀 둔다).
    """

    @classmethod
    def setUpClass(cls):
        base = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "static")
        cls.src = {}
        for name in ("index.html", "chat.js", "sessions.js", "workspace.js",
                     "app.js", "app.css"):
            with open(os.path.join(base, name), encoding="utf-8") as f:
                cls.src[name] = f.read()

    def test_메시지_밖에_고정_자리가_있다(self):
        self.assertIn('id="chatDlBar"', self.src["index.html"])

    def test_서버_상태를_보고_그린다(self):
        """★DOM 에만 있으면 새로고침에 사라진다. 워크스페이스에 물어야 한다."""
        js = self.src["chat.js"]
        self.assertIn("Chat.refreshDownloadBar", js)
        self.assertIn("api/code/workspace/changes", js)

    def test_사라지는_길목마다_다시_그린다(self):
        for name, why in (("app.js", "새로고침·새 세션"),
                          ("sessions.js", "세션 복원"),
                          ("workspace.js", "워크스페이스 갱신")):
            self.assertIn("refreshDownloadBar", self.src[name],
                          f"{why} 뒤에 받기 바를 다시 안 그린다")

    def test_세션_복원때_수정제안도_되살린다(self):
        """본문에 ```edit:``` 이 남아 있으므로 다시 그릴 수 있다."""
        self.assertIn("Chat.offerEdits", self.src["sessions.js"])

    def test_window에_없는_객체를_찾지_않는다(self):
        """★이 파일들은 일반 스크립트다 — 최상위 const 는 window 에 안 붙는다.
        window.Workspace?.refresh() 는 한 번도 실행되지 않았고, 그래서 수정을
        적용해도 워크스페이스 트리와 '고친 파일' 목록이 갱신되지 않았다."""
        for name in ("chat.js", "workspace.js", "app.js", "sessions.js"):
            for obj in ("Chat", "Workspace", "Skills", "Sessions", "Knowledge"):
                self.assertNotIn(f"window.{obj}?.", self.src[name],
                                 f"{name}: window.{obj} 는 항상 undefined 다")

    def test_이미_적용된_제안에도_받기가_붙는다(self):
        """★적용 버튼이 안 만들어지면 그 아래 받기 줄도 안 생겼다.
        이미 적용한 대화를 다시 열면 "이미 적용했습니다" 만 있고 받을
        데가 없었다."""
        js = self.src["chat.js"]
        i = js.index("if (doneList.length && !okList.length)")
        j = js.index("if (okList.length)", i)
        self.assertIn("addDownloadRow", js[i:j],
                      "이미 적용된 제안에 받기 줄을 안 붙인다")

    def test_바에_스타일이_있다(self):
        self.assertIn(".chat-dl", self.src["app.css"])
