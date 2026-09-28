# -*- coding: utf-8 -*-
"""
화이트보드 추가팩 설치기 — 데모스 · 코딩 어시스턴트에 '답변 속 그림 보기'를 붙인다.

  python whiteboard_install.py            무엇을 할지 보여 주고, y 를 누르면 설치
  python whiteboard_install.py --yes      묻지 않고 설치
  python whiteboard_install.py --check    보여 주기만 (파일은 그대로)
  python whiteboard_install.py --remove   되돌리기
  python whiteboard_install.py --dir D:\\demos     app.py 가 있는 폴더 (안 주면 이 파일 둘레에서 찾는다)

★기존 파일은 통째로 덮어쓰지 않는다 — 정해진 자리에 몇 줄씩 끼워 넣는다. 사람마다
  index.html 이 조금씩 달라서, 덮어쓰면 그 사람이 고친 것이 사라진다.
★고치기 전 파일은 옆에 <이름>.wb_backup 으로 한 번 남긴다. --remove 는 이것으로 되돌린다.
★이미 들어 있으면 건너뛴다(두 번 돌려도 같다). 끼워 넣을 자리를 못 찾은 파일은 건드리지 않고
  '손으로' 라고 알려 준다 — 넣을 줄은 snippets/ 폴더에 그대로 있다.
★줄바꿈(CRLF)과 BOM 은 원래 파일 그대로 둔다.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shutil
import sys

TAG = "20260928a"            # 이 추가팩의 판 — 코딩 어시스턴트가 고친 chat.js · app.css 를 새로 받게 하는 꼬리표
HERE = os.path.dirname(os.path.abspath(__file__))
SNIP_DIR = os.path.join(HERE, "snippets")
FILES_DIR = os.path.join(HERE, "files")
BAK = ".wb_backup"

NEW_FILES = ["demos_v1/wb_render.py", "demos_v1/whiteboard.py", "demos_v1/static/whiteboard.js"]
TEST_FILE = "code_assist_v1/tests/test_whiteboard.py"


def _snip(name: str) -> str:
    with open(os.path.join(SNIP_DIR, name), encoding="utf-8", newline="") as f:
        return f.read()


def _line(text: str) -> str:
    return "^[ \\t]*" + re.escape(text)


class Doc:
    """글 파일 하나 — 줄바꿈(CRLF)과 BOM 을 지켜서 읽고 쓴다. 안에서는 \\n 으로만 다룬다."""

    def __init__(self, path: str):
        self.path = path
        with open(path, "rb") as f:
            raw = f.read()
        self.bom = raw.startswith(b"\xef\xbb\xbf")
        text = raw.decode("utf-8-sig")
        self.crlf = "\r\n" in text
        self.text = text.replace("\r\n", "\n")
        self.orig = self.text

    @property
    def changed(self) -> bool:
        return self.text != self.orig

    def save(self):
        t = self.text.replace("\n", "\r\n") if self.crlf else self.text
        with open(self.path, "wb") as f:
            f.write((b"\xef\xbb\xbf" if self.bom else b"") + t.encode("utf-8"))


# ── 끼워 넣기 ──
def _line_start(text: str, pos: int) -> int:
    return text.rfind("\n", 0, pos) + 1


def _before_line(doc: Doc, patterns, snippet: str, last: bool = False) -> bool:
    """patterns 중 처음 맞는 줄 앞에 넣는다. 그 줄이 여럿이면 last=True 일 때만 마지막 것 앞에."""
    for pat in patterns:
        ms = list(re.finditer(pat, doc.text, re.M))
        if not ms:
            continue
        if len(ms) > 1 and not last:
            return False                      # 자리가 둘 이상 — 어느 쪽인지 모른다
        i = _line_start(doc.text, ms[-1].start())
        doc.text = doc.text[:i] + snippet + doc.text[i:]
        return True
    return False


def _after_line(doc: Doc, pattern: str, snippet: str) -> bool:
    ms = list(re.finditer(pattern, doc.text, re.M))
    if len(ms) != 1:
        return False
    j = ms[0].end()
    if doc.text[j:j + 1] == "\n":
        j += 1
    doc.text = doc.text[:j] + snippet + doc.text[j:]
    return True


def _before_func_end(doc: Doc, head: str, snippet: str) -> bool:
    """함수 head 의 끝(맨 앞 칸의 '}' 줄) 바로 앞에 넣는다."""
    if doc.text.count(head) != 1:
        return False
    j = doc.text.find("\n}\n", doc.text.index(head))
    if j < 0:
        return False
    doc.text = doc.text[:j + 1] + snippet + doc.text[j + 1:]
    return True


def _before_body_end(doc: Doc, snippet: str) -> bool:
    i = doc.text.rfind("</body>")
    if i < 0:
        return False
    ls = _line_start(doc.text, i)
    if doc.text[ls:i].strip():                # </body> 앞에 다른 글이 있는 줄 — 줄을 나눠 넣는다
        doc.text = doc.text[:i] + "\n" + snippet + doc.text[i:]
    else:
        doc.text = doc.text[:ls] + snippet + doc.text[ls:]
    return True


def _swap(doc: Doc, old: str, new: str) -> bool:
    if doc.text.count(old) != 1:
        return False
    doc.text = doc.text.replace(old, new, 1)
    return True


# ── 할 일 목록: (파일, 무엇, 들어 있으면 보이는 글, 넣는 법, 조각) ──
def _steps():
    return [
        ("demos_v1/__init__.py", "서버에 그림 주소(/api/whiteboard/render) 등록",
         "register_whiteboard_routes", "demos_init.txt",
         lambda d, s: _before_line(d, [_line("# code_assist_v1 통합"), _line("_routes_registered = True")], s, last=True)),
        ("demos_v1/templates/index.html", "답변 변환기가 mermaid 원문을 쪼개지 않게",
         "s=s.replace(/```mermaid", "demos_rendermd.txt",
         lambda d, s: _before_line(d, [_line("// 2c) 일반 코드블록"),
                                       _line("s=s.replace(/```(\\w*)\\s*([\\s\\S]*?)```/g")], s)),
        ("demos_v1/templates/index.html", "데모스 채팅에 whiteboard.js 싣기",
         "/static/whiteboard.js", "demos_tail.txt", lambda d, s: _before_body_end(d, s)),
        ("demos_v1/templates/agent_window.html", "개인 에이전트 창에 whiteboard.js 싣기",
         "/static/whiteboard.js", "agent_tail.txt", lambda d, s: _before_body_end(d, s)),
        ("code_assist_v1/static/index.html", "코딩 어시스턴트에 whiteboard.js 싣기",
         "/static/whiteboard.js", "code_tail.txt", lambda d, s: _before_body_end(d, s)),
        ("code_assist_v1/static/chat.js", "지난 세션을 열 때도 그림으로",
         "WB.renderIn(c)", "code_append.txt",
         lambda d, s: _after_line(d, r"^[ \t]*else c\.innerHTML = renderMd\(content\);[ \t]*$", s)),
        ("code_assist_v1/static/chat.js", "대체 변환기가 mermaid 원문을 쪼개지 않게",
         "t = t.replace(/```mermaid", "code_mini.txt",
         lambda d, s: _before_line(d, [_line("// 코드블록") + "[ \\t]*$",
                                       _line("t = t.replace(/```(\\w*)\\n([\\s\\S]*?)```/g")], s)),
        ("code_assist_v1/static/chat.js", "답변이 끝나면 그림으로",
         "WB.renderIn(root)", "code_attach.txt",
         lambda d, s: _before_func_end(d, "function attachCopyButtons(", s)),
    ]


CSS_FILE = "code_assist_v1/static/app.css"
CODE_INDEX = "code_assist_v1/static/index.html"


def _bump(doc: Doc) -> None:
    """코딩 어시스턴트가 고친 chat.js · app.css 를 캐시 대신 새로 받게."""
    for name in ("chat.js", "app.css"):
        doc.text = re.sub(r"(static/" + re.escape(name) + r"\?v=)[\w.-]+", r"\g<1>" + TAG, doc.text)


def _backup(path: str) -> None:
    if not os.path.exists(path + BAK):
        shutil.copy2(path, path + BAK)


def patch(root: str, write: bool = True) -> list:
    """끼워 넣기. 돌려주는 것: [(파일, 무엇, 상태)] — 상태: 넣음 · 있음 · 손으로 · 파일 없음."""
    rows, docs = [], {}
    code_touched = False
    for rel, what, sig, snip, put in _steps():
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            rows.append((rel, what, "파일 없음"))
            continue
        doc = docs.setdefault(rel, Doc(path))
        if sig in doc.text:
            rows.append((rel, what, "있음"))
            continue
        if put(doc, _snip(snip)):
            rows.append((rel, what, "넣음"))
            code_touched = code_touched or rel.startswith("code_assist_v1/")
        else:
            rows.append((rel, what, "손으로"))
    # 선택: 코딩 어시스턴트 '수정 제안' 카드 색을 테마 변수로 (라이트 테마에서 그림 틀 머리 글자가 보이게)
    path = os.path.join(root, CSS_FILE)
    what = "라이트 테마에서 그림 틀 머리 글자가 보이게 (선택)"
    if os.path.isfile(path):
        doc = docs.setdefault(CSS_FILE, Doc(path))
        new = _snip("code_css_new.txt")
        if new in doc.text:
            rows.append((CSS_FILE, what, "있음"))
        elif _swap(doc, _snip("code_css_old.txt"), new):
            rows.append((CSS_FILE, what, "넣음"))
            code_touched = True
        else:
            rows.append((CSS_FILE, what, "건너뜀"))
    if code_touched and os.path.isfile(os.path.join(root, CODE_INDEX)):
        doc = docs.setdefault(CODE_INDEX, Doc(os.path.join(root, CODE_INDEX)))
        _bump(doc)
    if write:
        for doc in docs.values():
            if doc.changed:
                _backup(doc.path)
                doc.save()
    return rows


def unpatch(root: str) -> list:
    """되돌리기 — 백업이 있으면 그것으로, 없으면 넣었던 줄을 그대로 뺀다."""
    rows, done = [], set()
    files = sorted({rel for rel, *_ in _steps()} | {CSS_FILE})
    for rel in files:
        path = os.path.join(root, rel)
        if os.path.isfile(path + BAK):
            shutil.copy2(path + BAK, path)
            os.remove(path + BAK)
            rows.append((rel, "백업으로 되돌림"))
            done.add(rel)
    docs = {}
    for rel, what, sig, snip, put in _steps():
        path = os.path.join(root, rel)
        if rel in done or not os.path.isfile(path):
            continue
        doc = docs.setdefault(rel, Doc(path))
        s = _snip(snip)
        if s in doc.text:
            doc.text = doc.text.replace(s, "", 1)
    path = os.path.join(root, CSS_FILE)
    if CSS_FILE not in done and os.path.isfile(path):
        doc = docs.setdefault(CSS_FILE, Doc(path))
        _swap(doc, _snip("code_css_new.txt"), _snip("code_css_old.txt"))
    for rel, doc in docs.items():
        if doc.changed:
            doc.save()
            rows.append((rel, "넣었던 줄을 뺌"))
    return rows


# ── 새 파일 ──
def copy_files(root: str, write: bool = True) -> list:
    rows = []
    items = list(NEW_FILES)
    if os.path.isdir(os.path.join(root, "code_assist_v1", "tests")):
        items.append(TEST_FILE)
    for rel in items:
        src, dst = os.path.join(FILES_DIR, rel), os.path.join(root, rel)
        if not os.path.isfile(src):
            rows.append((rel, "추가팩에 없음" if not os.path.isfile(dst) else "있음"))
            continue
        with open(src, "rb") as f:
            new = f.read()
        if os.path.isfile(dst):
            with open(dst, "rb") as f:
                if f.read() == new:
                    rows.append((rel, "같음"))
                    continue
            state = "새 판으로 바꿈"
        else:
            state = "새로 넣음"
        if write:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.isfile(dst):
                _backup(dst)
            with open(dst, "wb") as f:
                f.write(new)
        rows.append((rel, state))
    return rows


def remove_files(root: str) -> list:
    rows = []
    for rel in NEW_FILES + [TEST_FILE]:
        p = os.path.join(root, rel)
        if os.path.isfile(p + BAK):                # 추가팩 전에 있던 판이 있으면 그것으로
            shutil.copy2(p + BAK, p)
            os.remove(p + BAK)
            rows.append((rel, "전 판으로 되돌림"))
        elif os.path.isfile(p):
            os.remove(p)
            rows.append((rel, "지움"))
    d = os.path.join(root, "demos_v1", "static")
    if os.path.isdir(d) and not os.listdir(d):
        os.rmdir(d)
    return rows


def self_test(root: str) -> str:
    path = os.path.join(root, "demos_v1", "wb_render.py")
    spec = importlib.util.spec_from_file_location("wb_render_check", path)
    mod = importlib.util.module_from_spec(spec)
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True    # 확인만 — __pycache__ 를 남기지 않는다
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = keep
    r = mod.render("flowchart TD\n    A[설치] --> B{확인}\n    B -->|예| C[완료]")
    if not r.get("ok"):
        raise RuntimeError(r.get("error"))
    return f"그림 엔진 확인: 흐름도 한 장 {r['w']:.0f}×{r['h']:.0f}"


def find_root(arg: str | None) -> str | None:
    cands = [arg] if arg else [os.getcwd(), os.path.dirname(HERE), HERE, os.path.dirname(os.path.dirname(HERE))]
    for c in cands:
        if c and os.path.isfile(os.path.join(c, "demos_v1", "__init__.py")):
            return os.path.abspath(c)
    return None


def _print_rows(title, rows):
    print(f"\n{title}")
    w = max((len(r[0]) for r in rows), default=10)
    for r in rows:
        print(f"  {r[0]:<{w}}  {'  '.join(r[1:])}")


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="화이트보드 추가팩 설치기 — 답변 속 ```mermaid 를 그림으로")
    ap.add_argument("--dir", help="app.py 가 있는 폴더 (demos_v1/ 가 들어 있는 곳)")
    ap.add_argument("--check", action="store_true", help="무엇을 할지 보여 주기만")
    ap.add_argument("--remove", action="store_true", help="되돌리기")
    ap.add_argument("--yes", action="store_true", help="묻지 않고 설치")
    a = ap.parse_args(argv)
    if sys.version_info < (3, 7):
        print("파이썬 3.7 이상이 필요합니다.")
        return 2
    root = find_root(a.dir)
    if not root:
        print("데모스 폴더를 못 찾았습니다 — app.py 와 demos_v1/ 이 있는 폴더에서 돌리거나 --dir 로 알려 주세요.")
        return 2
    print(f"데모스 폴더: {root}")

    if a.remove:
        rows = unpatch(root) + remove_files(root)
        _print_rows("되돌림", rows or [("(할 것 없음)", "")])
        print("\n데모스를 다시 켜면 그림 보기가 빠집니다.")
        return 0

    rows_f = copy_files(root, write=False)
    rows_p = patch(root, write=False)
    _print_rows("새 파일", rows_f)
    _print_rows("끼워 넣기", [(r[0], r[2], r[1]) for r in rows_p])
    manual = [r for r in rows_p if r[2] == "손으로"]
    if any(r[1] == "추가팩에 없음" for r in rows_f):
        print("\n※ 추가팩의 files/ 폴더가 없습니다 — 압축을 폴더째 풀었는지 확인해 주세요.")
        return 2
    if a.check:
        return 0
    if not a.yes:
        try:
            if input("\n설치할까요? [y/N] ").strip().lower() not in ("y", "yes", "ㅛ"):
                print("그만뒀습니다. 바뀐 파일은 없습니다.")
                return 1
        except EOFError:
            print("\n묻지 못해서 그만뒀습니다 — --yes 를 붙여 돌려 주세요.")
            return 1
    copy_files(root)
    patch(root)
    try:
        print("\n" + self_test(root))
    except Exception as e:                                          # noqa: BLE001
        print(f"\n그림 엔진 확인 실패: {type(e).__name__}: {e}")
        return 3
    if manual:
        print("\n※ 자리를 못 찾아 넣지 못한 곳이 있습니다 — snippets/ 의 같은 이름 조각을 손으로 넣어 주세요:")
        for rel, what, _ in manual:
            print(f"   {rel} — {what}")
    print("\n끝. 데모스를 한 번 다시 켜고, 브라우저에서 Ctrl+F5 를 누르세요.")
    print("콘솔에 '화이트보드 라우트 등록 완료' 가 보이면 된 것입니다. 되돌리기: --remove")
    return 0


if __name__ == "__main__":
    code = main()
    if sys.platform == "win32" and len(sys.argv) == 1 and sys.stdin and sys.stdin.isatty():
        try:
            input("\n엔터를 누르면 창이 닫힙니다.")
        except EOFError:
            pass
    sys.exit(code)
