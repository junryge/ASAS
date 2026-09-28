# -*- coding: utf-8 -*-
"""
화이트보드 추가팩 묶기 — 저장소의 실제 파일로 공유용 zip 을 만든다.

    python tools/whiteboard_addon/make_addon.py [나갈_곳.zip]

zip 을 풀면 '화이트보드_추가팩' 폴더 하나가 나온다.
    화이트보드_안내.html     한 장 소개 — 무엇인지 · 모습 · 묻는 법 · 넣는 법
    whiteboard_install.py    설치기 — 확인(--check) · 설치 · 되돌리기(--remove)
    snippets/                설치기가 끼워 넣는 줄 (자리를 못 찾으면 손으로 넣을 때도 이것)
    files/                   새 파일 — 그림 엔진 · 서버 경로 · 화면 스크립트 · 시험

★files/ 는 묶을 때마다 저장소에서 새로 가져온다 — 저장소 판과 추가팩 판이 어긋나지 않게.
"""
from __future__ import annotations

import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # scientific-assistant (app.py 가 있는 곳)
sys.path.insert(0, HERE)
import whiteboard_install as inst  # noqa: E402

TOP = "화이트보드_추가팩"


def items() -> list:
    out = [("화이트보드_안내.html", os.path.join(HERE, "화이트보드_안내.html")),
           ("whiteboard_install.py", os.path.join(HERE, "whiteboard_install.py"))]
    for n in sorted(os.listdir(os.path.join(HERE, "snippets"))):
        out.append(("snippets/" + n, os.path.join(HERE, "snippets", n)))
    for rel in inst.NEW_FILES + [inst.TEST_FILE]:
        out.append(("files/" + rel, os.path.join(ROOT, rel)))
    return out


def build(dest: str) -> list:
    got = items()
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, src in got:
            z.write(src, f"{TOP}/{arc}")
    return got


if __name__ == "__main__":
    dest = sys.argv[1] if len(sys.argv) > 1 else f"whiteboard_addon_{inst.TAG}.zip"
    for arc, _ in build(dest):
        print(f"  {TOP}/{arc}")
    print(f"→ {dest} ({os.path.getsize(dest) // 1024} KB)")
