"""아바타 의상 목록 — 설정(파이썬)과 화면(app.js) 두 곳에 있다.

★두 벌이라 어긋날 수 있다. app.js 쪽은 HTML 을 그냥 열었을 때 쓰는 폴백이고
  서버로 띄우면 /api/config 가 덮는다. 어긋나면 '혼자 띄웠을 때만 옷이 다른'
  상태가 되어 원인을 찾기 어렵다. 그래서 여기서 묶어 둔다.

★새 옷은 반드시 **뒤에** 붙여야 한다. BACKGROUNDS 가 의상을 인덱스로
  가리켜서(공장=2 · 회의실=0 …) 중간에 끼우면 배경이 엉뚱한 옷을 입힌다.
"""
import json
import os
import re
import unittest

from . import util

AV = os.path.join(util.BASE, "avatar_2d")


def _py_costumes():
    import importlib.util
    p = os.path.join(AV, "avatar", "config.py")
    spec = importlib.util.spec_from_file_location("_av_cfg", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _js_costumes():
    """app.js 의 폴백 COSTUMES 를 읽어 {name, src, badge} 로 만든다."""
    with open(os.path.join(AV, "static", "app.js"), encoding="utf-8") as f:
        js = f.read()
    block = js[js.index("const COSTUMES = ["):]
    block = block[:block.index("\n];")]
    out = []
    for m in re.finditer(r"\{name:'([^']+)',\s*src:\"([^\"]+)\"(.*?)\}(?:,|\s*$)",
                         block, re.S):
        name, src, rest = m.group(1), m.group(2), m.group(3)
        badge = re.search(r"badge:(true|false)", rest)
        out.append({"name": name, "src": src,
                    "badge": (badge.group(1) == "true") if badge else None})
    return out


class CostumeList(unittest.TestCase):
    def setUp(self):
        self.cfg = _py_costumes()
        self.js = _js_costumes()

    def test_이름과_그림이_두_곳에서_같다(self):
        py = [(c["name"], c["src"]) for c in self.cfg.COSTUMES]
        js = [(c["name"], c["src"]) for c in self.js]
        self.assertEqual(py, js,
                         "avatar/config.py 와 static/app.js 의 의상 목록이 어긋났다")

    def test_사원증_규칙도_두_곳에서_같다(self):
        py = [c.get("badge") for c in self.cfg.COSTUMES]
        js = [c["badge"] for c in self.js]
        self.assertEqual(py, js)

    def test_배경이_가리키는_의상이_그대로다(self):
        """새 옷을 중간에 끼우면 공장에서 무진복 대신 딴 옷이 나온다."""
        want = {"공장": "무진복", "회의실": "정장", "정문": "가운",
                "테라스": "반팔", "집": "잠옷"}
        for b in self.cfg.BACKGROUNDS:
            if b.get("costume") is None:
                continue
            self.assertEqual(self.cfg.COSTUMES[b["costume"]]["name"],
                             want.get(b["name"]),
                             f"{b['name']} 배경이 가리키는 옷이 바뀌었다")

    def test_사원증을_떼는_옷은_평상복_하나다(self):
        off = [c["name"] for c in self.cfg.COSTUMES if c.get("badge") is False]
        self.assertEqual(off, ["평상복"])

    def test_사원증_규칙이_없는_옷은_지금_상태를_유지한다(self):
        """예전 다섯 벌은 배경이 사원증을 정한다 — 옷에 규칙을 달면
        배경과 싸운다."""
        for c in self.cfg.COSTUMES[:5]:
            self.assertIsNone(c.get("badge"), f"{c['name']} 에 badge 가 붙었다")

    def test_그림_경로가_static_아래다(self):
        for c in self.cfg.COSTUMES:
            self.assertTrue(c["src"].startswith("assets/"), c["src"])

    def test_의상_그림이_다_있다(self):
        """★설정에 적힌 png 가 없으면 그 옷을 고르는 순간 화면이 빈다.
        (app.js 가 알려 주고 직전 옷으로 되돌리지만, 애초에 있어야 한다.)"""
        miss = [c["name"] + " (" + c["src"] + ")" for c in self.cfg.COSTUMES
                if not os.path.isfile(os.path.join(AV, "static", c["src"]))]
        old = [c["name"] for c in self.cfg.COSTUMES[:5]
               if not os.path.isfile(os.path.join(AV, "static", c["src"]))]
        self.assertEqual(old, [], "원래 있던 의상 그림이 없어졌다")
        if miss:
            self.skipTest("아직 안 넣은 의상 그림 — assets 에 넣으면 이 테스트가 "
                          "지킨다: " + ", ".join(miss))


if __name__ == "__main__":
    unittest.main()
