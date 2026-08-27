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


class ChromaKey(unittest.TestCase):
    """초록 배경(크로마키) 빼기 — 화면 쪽(app.js) 을 글자로 검사한다.

    기존 의상 다섯 벌은 **배경이 투명**이고 440x630 틀에 맞춰져 있다
    (재 보니 위 여백 2.7% · 아래는 딱 붙음). 새로 받는 그림은 초록 배경이라
    그대로 쓰면 초록 네모가 화면에 붙는다.
    """

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(AV, "static", "app.js"), encoding="utf-8") as f:
            cls.js = f.read()

    def _fn(self, name):
        m = re.search(r"function " + name + r"\(.*?\n\}", self.js, re.S)
        self.assertIsNotNone(m, name + " 이(가) 없다")
        return m.group(0)

    def test_기존_의상은_배경이_투명하다(self):
        """새 그림을 맞출 기준 — 흰색이 아니라 투명이다."""
        import struct
        import zlib
        p = os.path.join(AV, "static", "assets", "suit.png")
        d = open(p, "rb").read()
        w, h, _bd, ct = struct.unpack(">IIBB", d[16:26])
        self.assertEqual((w, h), (440, 630), "기준 틀이 바뀌었다")
        self.assertEqual(ct, 6, "RGBA 가 아니다 — 투명 배경일 수 없다")

    def test_틀_크기가_기존과_같다(self):
        self.assertIn("ART_W = 440", self.js)
        self.assertIn("ART_H = 630", self.js)

    def test_색으로_싹_지우지_않고_테두리에서_번져_들어간다(self):
        """옷에 있는 초록(금장미 자수의 잎사귀)까지 지워지면 안 된다 —
        바깥과 이어져 있는 초록만 배경이다."""
        f = self._fn("_keyOut")
        self.assertIn("stack", f, "번져 들어가는(flood fill) 방식이 아니다")
        # 테두리 전체를 시작점으로 넣는가
        self.assertIn("(h-1)*w", f)
        self.assertIn("y*w+w-1", f)

    def test_이미_투명한_그림은_안_건드린다(self):
        """기존 의상을 다시 넣어도 그대로여야 한다."""
        f = self._fn("_chromaOf")
        self.assertIn("d[o+3] < 200", f, "이미 투명한 테두리를 크로마로 본다")

    def test_초록이_옅으면_크로마로_안_본다(self):
        f = self._fn("_chromaOf")
        self.assertIn("< 40", f, "문턱값이 없다 — 아무 그림이나 배경을 뚫는다")

    def test_초록_번짐을_눌러_준다(self):
        """안 하면 인물 둘레에 초록 테가 남는다."""
        self.assertIn("번진 초록", self._fn("_keyOut"))

    def test_아래는_딱_붙이고_위만_여백을_둔다(self):
        """기존 다섯 벌이 그렇다 (아래 여백 0.000)."""
        f = self._fn("_fit")
        self.assertIn("ART_H-dh", f)
        self.assertIn("ART_TOP", self.js)

    def test_넣을_때_자동으로_거친다(self):
        m = re.search(r"async function addCostumeFile\(f\)\{.*?\n\}",
                      self.js, re.S).group(0)
        self.assertIn("normalizeCostume(", m)


class Calibration(unittest.TestCase):
    """의상별 캘리브레이션(patch) — 그림에서 재서 넣은 값이다.

    ★그림마다 인물이 있는 자리가 다르다. 기본값 그대로 두면 눈 깜빡임이
      엉뚱한 데서 일어나고 팔이 허공을 잡는다.
    """

    def setUp(self):
        self.cfg = _py_costumes()

    def _by(self, name):
        return next(c for c in self.cfg.COSTUMES if c['name'] == name)

    def test_새_의상은_모두_손_위치를_갖는다(self):
        for n in ('평상복', '셔츠', '자켓', '테크자켓', '민소매'):
            p = self._by(n).get('patch') or {}
            self.assertIn('armA', p, n + ' 에 손 위치가 없다')
            self.assertIn('armB', p, n + ' 에 손 위치가 없다')

    def test_왼손이_오른손보다_왼쪽이다(self):
        for c in self.cfg.COSTUMES:
            p = c.get('patch') or {}
            if 'armA' in p:
                self.assertLess(p['armA'][0], p['armB'][0],
                                c['name'] + ' 의 두 팔이 뒤집혔다')

    def test_손_위치가_그림_안이다(self):
        for c in self.cfg.COSTUMES:
            p = c.get('patch') or {}
            for k in ('armA', 'armB'):
                if k in p:
                    x, y = p[k]
                    self.assertTrue(0.05 < x < 0.95, f"{c['name']} {k} x={x}")
                    self.assertTrue(0.4 < y < 0.95, f"{c['name']} {k} y={y}")

    def test_맞잡은_손은_영역을_좁게_잡는다(self):
        """두 팔 영역이 겹치면 손가락이 찢어진다 (잠옷에서 겪은 것)."""
        for n in ('잠옷', '테크자켓'):
            p = self._by(n)['patch']
            gap = p['armB'][0] - p['armA'][0]
            self.assertLess(p['armA_rad'][0] * 2, gap,
                            n + ' 의 두 팔 영역이 겹친다')

    def test_얼굴이_내려간_만큼_눈도_내렸다(self):
        """새 그림은 인물이 기존보다 아래에 있다. 얼굴만 옮기고 눈을 안
        옮기면 눈 깜빡임이 이마에서 일어난다."""
        for n in ('평상복', '자켓', '테크자켓', '민소매'):
            p = self._by(n)['patch']
            self.assertIn('faceC', p, n)
            self.assertIn('eyeL', p, n)
            # 눈은 얼굴보다 위에 있어야 한다
            self.assertLess(p['eyeL'][1], p['faceC'][1], n)
            self.assertLess(p['eyeL'][1], p['mouth'][1], n)

    @staticmethod
    def _js_patches():
        """app.js 폴백 목록에서 이름별 patch 를 숫자로 뽑는다.

        중괄호 짝을 세어 자른다 — 키가 늘면 문자열로 자르던 방식은 깨진다.
        """
        with open(os.path.join(AV, "static", "app.js"), encoding="utf-8") as f:
            raw = f.read()
        blk = raw[raw.index("const COSTUMES = ["):]
        blk = blk[:blk.index("\n];")]
        out = {}
        for m in re.finditer(r"name:'([^']+)'", blk):
            name = m.group(1)
            nxt = blk.find("name:'", m.end())
            seg = blk[m.end():nxt if nxt > 0 else len(blk)]
            j = seg.find("patch:{")
            if j < 0:
                out[name] = {}
                continue
            i, depth = j + 6, 0
            while i < len(seg):
                if seg[i] == '{':
                    depth += 1
                elif seg[i] == '}':
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            body = seg[j + 7:i]
            vals = {}
            for km in re.finditer(r"(\w+)\s*:\s*\[([-\d.,\s]+)\]", body):
                vals[km.group(1)] = [float(x) for x in km.group(2).split(",")]
            for km in re.finditer(r"(\w+)\s*:\s*([-\d.]+)\s*(?=[,}])", body):
                vals.setdefault(km.group(1), float(km.group(2)))
            out[name] = vals
        return out

    def test_화면_폴백에도_같은_값이_있다(self):
        """두 곳이 어긋나면 혼자 띄웠을 때만 팔이 딴 데를 잡는다.
        (실제로 무진복이 그랬다 — config.py 에만 patch 가 있었다.)"""
        got = self._js_patches()
        for c in self.cfg.COSTUMES:
            want = c.get("patch") or {}
            if not want:
                continue
            have = got.get(c["name"], {})
            for k, v in want.items():
                self.assertIn(k, have, f"{c['name']} 의 {k} 가 app.js 에 없다")
                if isinstance(v, list):
                    self.assertEqual([round(x, 4) for x in v],
                                     [round(x, 4) for x in have[k]],
                                     f"{c['name']} 의 {k} 값이 다르다")
                else:
                    self.assertAlmostEqual(v, have[k], places=4,
                                           msg=f"{c['name']} 의 {k} 값이 다르다")


if __name__ == "__main__":
    unittest.main()
