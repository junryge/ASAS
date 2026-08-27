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


class SaveCostumeImage(unittest.TestCase):
    """끌어다 놓은 의상 그림 저장 — avatar/server.save_costume_image().

    ★예전엔 data URL 로 메모리에만 들고 있어서 새로고침하면 사라졌다.
      이제 assets/ 에 파일로 남고, config.py 에 미리 적어 둔 의상이면
      그 자리(slot)를 채운 것으로 알려 준다.
    ★브라우저가 주는 파일 이름은 **믿지 않는다** — 이 창은 로컬이지만
      이름 하나로 저장 폴더 밖에 파일을 쓰게 두면 안 된다.
    """

    PNG = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
           "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

    def setUp(self):
        import base64
        import importlib.util
        import sys
        import tempfile
        self.b64 = base64.b64encode
        self.raw = base64.b64decode(self.PNG)
        self.tmp = tempfile.mkdtemp(prefix="avcos")
        if AV not in sys.path:
            sys.path.insert(0, AV)
        from avatar import server as S
        self.S = S

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _save(self, name, blob=None):
        return self.S.save_costume_image(
            self.tmp, name, self.b64(self.raw if blob is None else blob).decode())

    def _files(self):
        d = os.path.join(self.tmp, "assets")
        return sorted(os.listdir(d)) if os.path.isdir(d) else []

    def test_저장되고_경로를_돌려준다(self):
        r = self._save("casual.png")
        self.assertTrue(r.get("ok"), r)
        self.assertEqual(r["src"], "assets/casual.png")
        self.assertEqual(self._files(), ["casual.png"])

    def test_설정에_적어_둔_의상이면_그_자리를_알려준다(self):
        """새 칩을 또 만들면 같은 그림인데 칩이 두 개가 된다."""
        cfg = _py_costumes()
        want = next(i for i, c in enumerate(cfg.COSTUMES)
                    if c["src"] == "assets/casual.png")
        self.assertEqual(self._save("casual.png")["slot"], want)

    def test_모르는_이름이면_자리가_없다(self):
        self.assertEqual(self._save("처음보는옷.png")["slot"], -1)

    def test_data_URL_그대로_줘도_된다(self):
        r = self.S.save_costume_image(
            self.tmp, "shirt.png",
            "data:image/png;base64," + self.b64(self.raw).decode())
        self.assertTrue(r.get("ok"), r)

    def test_저장_폴더_밖으로_못_나간다(self):
        """브라우저가 '../../avatar/config.py' 를 줘도 assets 안에만 쓴다."""
        r = self._save("../../avatar/config.py")
        self.assertTrue(r.get("ok"), r)
        self.assertTrue(r["src"].startswith("assets/"), r["src"])
        self.assertEqual(self._files(), ["config.png"])
        # 상위 어디에도 새 파일이 생기지 않았다
        self.assertEqual(sorted(os.listdir(self.tmp)), ["assets"])

    def test_이름만_png_인_것은_거른다(self):
        """확장자를 믿으면 스크립트가 assets 에 남는다 — 앞머리로 본다."""
        r = self._save("evil.png", b"<?php echo 1; ?>")
        self.assertIn("error", r)
        self.assertEqual(self._files(), [])

    def test_jpg_와_webp_는_받는다(self):
        self.assertTrue(self._save("a.jpg", b"\xff\xd8\xff" + b"0" * 20).get("ok"))
        self.assertTrue(self._save("b.webp", b"RIFF" + b"0" * 20).get("ok"))

    def test_너무_크면_거른다(self):
        r = self._save("big.png", b"\x89PNG\r\n\x1a\n" + b"0" * (13 * 1024 * 1024))
        self.assertIn("error", r)
        self.assertEqual(r.get("code"), 413)

    def test_빈_것과_깨진_것을_거른다(self):
        self.assertIn("error", self.S.save_costume_image(self.tmp, "x.png", ""))
        self.assertIn("error", self.S.save_costume_image(self.tmp, "x.png", "!!!not base64!!!"))
        self.assertEqual(self._files(), [])

    def test_이름이_비어도_저장은_된다(self):
        r = self._save("")
        self.assertTrue(r.get("ok"), r)
        self.assertEqual(r["src"], "assets/costume.png")


class DropHandler(unittest.TestCase):
    """끌어다 놓기 — 화면 쪽(app.js)을 글자로 검사한다."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(AV, "static", "app.js"), encoding="utf-8") as f:
            cls.js = f.read()

    def _drop(self, code_only=False):
        m = re.search(r"wrap\.addEventListener\('drop'.*?\n\}\);", self.js, re.S)
        self.assertIsNotNone(m, "drop 처리가 없다")
        d = m.group(0)
        # 주석에 옛 코드를 적어 두면(왜 바꿨는지) 검사에 걸린다 — 걷고 본다
        return re.sub(r"/\*.*?\*/|//[^\n]*", "", d, flags=re.S) if code_only else d

    def test_한_번에_여러_장을_받는다(self):
        """예전엔 files[0] 만 봐서 다섯 벌을 넣으려면 다섯 번 끌어야 했고
        나머지 넉 장은 말없이 버려졌다."""
        d = self._drop(code_only=True)
        self.assertIn("Array.from", d)
        self.assertNotIn("files[0]", d, "첫 장만 보고 나머지를 버린다")

    def test_그림을_하나씩_차례로_넣는다(self):
        """한꺼번에 보내면 자리(slot) 배정이 섞인다."""
        d = self._drop()
        self.assertIn("for(const f of imgs)", d)
        self.assertIn("await addCostumeFile(f)", d)

    def test_못_넣은_것을_말해준다(self):
        """조용히 버리면 왜 안 들어갔는지 알 수 없다."""
        self.assertIn("못 넣은 것", self._drop())

    def test_서버로_띄웠으면_파일로_저장한다(self):
        m = re.search(r"async function addCostumeFile\(f\)\{.*?\n\}",
                      self.js, re.S).group(0)
        self.assertIn("window.SERVER", m)
        self.assertIn("'/api/costume'", m)

    def test_설정에_있는_자리면_새_칩을_안_만든다(self):
        """같은 그림인데 칩이 두 개가 되면 안 된다."""
        m = re.search(r"async function addCostumeFile\(f\)\{.*?\n\}",
                      self.js, re.S).group(0)
        self.assertIn("r.slot >= 0", m)


if __name__ == "__main__":
    unittest.main()
