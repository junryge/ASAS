# -*- coding: utf-8 -*-
"""서윤 오른쪽 어깨 위 햄스터 (hamster_hbm4_live.html 에서 가져온 그림).

★캐릭터는 WebGL 캔버스라 **붙일 뼈가 없다.** 말풍선과 같은 길을 쓴다 —
  imgToCss() 로 이미지 좌표를 화면 좌표로 옮겨 얹는다. 그래서 자리·크기가
  코드에 있고, 여기서 그 규칙을 못 박는다.

여기서 지키는 것
  · 그림에 **배경이 없다** (원본은 그린스크린 위에 그려져 있었다)
  · 크기가 **캐릭터에 비례**한다 (px 로 박으면 창을 줄였을 때 서윤보다 커진다)
  · 자리가 **오른쪽 어깨** 다 (머리 아래 · 오른팔 위)
  · 규칙이 전부 #pet 아래에 갇혀 있다 (.body/.head 는 흔한 이름이다)
"""
import base64
import os
import re
import unittest

from . import util

CSS = os.path.join(util.BASE, "avatar_2d", "static", "assets", "hamster.css")
HTML = os.path.join(util.BASE, "avatar_2d", "static", "index.html")
JS = os.path.join(util.BASE, "avatar_2d", "static", "app.js")


def _read(p):
    if not os.path.isfile(p):
        raise unittest.SkipTest("{} 가 없다".format(p))
    with open(p, encoding="utf-8") as f:
        return f.read()


class 그림(unittest.TestCase):

    def setUp(self):
        self.css = _read(CSS)

    def test_그림이_들어_있다(self):
        self.assertIn("--art:url(\"data:image/webp;base64,", self.css)

    def test_배경이_없는_그림이다(self):
        """★원본은 **그린스크린(11,144,56) 위에** 그려져 있었다. 그대로
        얹으면 어깨 위에 초록 네모가 붙는다 — 크로마키로 빼고 알파를 넣었다.

        webp 파일 머리에서 알파 유무를 읽는다:
            RIFF....WEBP VP8X  → 확장 헤더, 4번째 바이트 bit4 가 알파
            RIFF....WEBP VP8L  → 무손실, 알파 가능
            RIFF....WEBP VP8   → 손실 단독, **알파 없음**
        """
        m = re.search(r'--art:url\("data:image/webp;base64,([^"]+)"\)', self.css)
        self.assertIsNotNone(m, "그림을 못 찾았다")
        raw = base64.b64decode(m.group(1))
        self.assertEqual(raw[:4], b"RIFF")
        self.assertEqual(raw[8:12], b"WEBP")
        fourcc = raw[12:16]
        self.assertIn(fourcc, (b"VP8X", b"VP8L"),
                      "알파가 없는 webp 다 — 배경이 그대로 붙는다")
        if fourcc == b"VP8X":
            self.assertTrue(raw[20] & 0x10,
                            "VP8X 인데 알파 비트가 꺼져 있다")

    def test_규칙이_pet_안에_갇혀_있다(self):
        """★원본은 .body/.head/.eye 같은 흔한 이름을 쓴다. 그대로 가져오면
        아바타 화면의 다른 것들과 부딪친다."""
        for m in re.finditer(r"(?m)^([.#][^{@\n]*)\{", self.css):
            sel = m.group(1).strip()
            for one in sel.split(","):
                one = one.strip()
                if one:
                    self.assertTrue(one.startswith("#pet"),
                                    "#pet 밖으로 새는 규칙: " + one)

    def test_원본의_페이지_배치를_안_가져왔다(self):
        """★620px 상한이 남아 있으면 창을 줄여도 햄스터만 그대로 버틴다.

        ★주석은 빼고 본다 — 무엇을 왜 지웠는지 주석에 적어 두었더니
          그 글이 잡혔다 (같은 자리를 전에도 밟았다).
        """
        code = re.sub(r"/\*.*?\*/", " ", self.css, flags=re.S)
        for w in ("620px", ".rail", "<button", "aspect-ratio"):
            self.assertNotIn(w, code, w)

    def test_어깨_위라_크게_안_움직인다(self):
        """★원본 세기(--amp:1)로 흔들면 어깨 위에서는 과하다."""
        m = re.search(r"--amp:\s*([\d.]+)", self.css)
        self.assertIsNotNone(m)
        self.assertLessEqual(float(m.group(1)), 0.7)

    def test_움직임_줄이기_설정을_지킨다(self):
        self.assertIn("prefers-reduced-motion", self.css)


class 자리와_크기(unittest.TestCase):

    def setUp(self):
        self.js = _read(JS)
        i = self.js.index("function placePet()")
        self.body = self.js[i:self.js.index("function setPet(")]

    def test_캐릭터에_비례한다(self):
        """★px 로 박으면 창을 줄였을 때 햄스터만 남아 서윤보다 커진다."""
        self.assertIn("IMG_W * VIEW.scale", self.body)
        self.assertIn("PET.w", self.body)

    def test_작다(self):
        m = re.search(r"PET\s*=\s*\{[^}]*w:\s*([\d.]+)", self.js)
        self.assertIsNotNone(m)
        self.assertLessEqual(float(m.group(1)), 0.25,
                             "캐릭터 폭의 1/4 을 넘는다 — 작게 해달라고 했다")

    def test_어깨_자리를_따로_잡아_둔다(self):
        """★armB·clothTop 으로 계산하면 안 된다 — **가슴에 뜬다.**

        실제 그림에 점을 찍어 보고 알았다:
            armB     [0.615, 0.835]  어깨가 아니라 **손**이다
            clothTop  0.62           옷깃이 아니라 **가슴 한복판**이다
        그래서 어깨 기준점(shoulderR)을 따로 두고, 그림 위에서 눈으로
        고른 값을 적어 뒀다. 의상마다 어깨선이 다르니 patch 로 덮는다.
        """
        self.assertIn("CFG.shoulderR", self.body)
        self.assertNotIn("CFG.armB", self.body, "손으로 계산하고 있다")
        self.assertNotIn("CFG.clothTop", self.body, "가슴으로 계산하고 있다")

    def test_어깨_자리가_어깨에_있다(self):
        """머리 아래 · 손보다 위 · 몸 오른쪽. 그림에서 잰 값과 맞는지 본다."""
        for m in re.finditer(r"shoulderR:\[([\d.]+),\s*([\d.]+)\]", self.js):
            sx, sy = float(m.group(1)), float(m.group(2))
            self.assertGreater(sx, 0.60, "가운데다 — 어깨가 아니다")
            self.assertLess(sx, 0.82, "너무 바깥이다 (팔 밖)")
            self.assertGreater(sy, 0.42, "머리에 겹친다")
            self.assertLess(sy, 0.56, "가슴이다 — 어깨가 아니다")
        self.assertGreaterEqual(
            len(re.findall(r"shoulderR:", self.js)), 2,
            "CFG_ANIME·CFG_REAL 둘 다 있어야 한다")

    def test_캐릭터가_뜨기_전엔_안_보인다(self):
        """★서윤보다 햄스터가 먼저 뜨면 허공에 떠 있다."""
        self.assertIn("texReady", self.body)

    def test_매_프레임_따라간다(self):
        """캐릭터가 움직이고 창이 바뀐다 — 한 번 놓고 마는 게 아니다."""
        i = self.js.index("function draw(){")
        self.assertIn("placePet()", self.js[i:i + 300])

    def test_안_바뀌었으면_다시_안_쓴다(self):
        """★60번/초 style 을 다시 쓰면 그때마다 레이아웃이 다시 잡힌다."""
        self.assertIn("PET.lw", self.body)
        self.assertIn("!==", self.body)

    def test_매_프레임_DOM_을_안_찾는다(self):
        self.assertIn("PET.el ||", self.body)


class 화면(unittest.TestCase):

    def setUp(self):
        self.h = _read(HTML)

    def test_무대_안에_있다(self):
        """★#stageWrap 밖에 두면 캐릭터를 따라다니지 못한다 (소형창 포함)."""
        i = self.h.index('id="stageWrap"')
        j = self.h.index('id="bubble"')
        self.assertIn('id="pet"', self.h[i:j])

    def test_클릭을_안_막는다(self):
        css = _read(CSS)
        i = css.index("#pet{")
        self.assertIn("pointer-events:none", css[i:i + 400])

    def test_말풍선을_안_가린다(self):
        css = _read(CSS)
        i = css.index("#pet{")
        z = re.search(r"z-index:\s*(\d+)", css[i:i + 400])
        self.assertIsNotNone(z)
        self.assertLess(int(z.group(1)), 9)

    def test_끄고_켤_수_있다(self):
        self.assertIn('id="petChip"', self.h)
        js = _read(JS)
        self.assertIn("function setPet", js)
        self.assertIn("localStorage.setItem('pet'", js)
        # 저장값과 칩 불빛이 어긋나면 안 된다
        self.assertIn("$('#petChip').classList.toggle('on', PET.on)", js)

    def test_그림을_따로_읽는다(self):
        """★base64 100KB 를 index.html 에 넣으면 화면 열 때마다 같이 받는다.
        CSS 는 브라우저가 캐시한다."""
        self.assertIn('href="assets/hamster.css"', self.h)
        self.assertNotIn("data:image/webp;base64", self.h)


APPCSS = os.path.join(util.BASE, "avatar_2d", "static", "app.css")


class 자리바꿈(unittest.TestCase):
    """서햄터를 두 번 누르면 **서윤이 화면에서 사라지고** 서햄터만 남는다.
    돌아오는 길은 오른쪽 아래 팝업(#petBack)의 서윤을 누르는 것이다.

    ★전에는 서윤을 어깨 위로 줄여 올렸다. "아예 서윤이 빼라, 서햄터만
      보이게" 라고 해서 감추는 쪽으로 바꿨다. 감추면 **돌아올 길이 없어지는
      것**이 이 변경의 진짜 위험이라, 팝업이 있는지를 여기서 못 박는다.
    """

    def setUp(self):
        self.js = _read(JS)
        self.h = _read(HTML)
        self.css = _read(APPCSS)

    # ── 서윤을 감춘다 ────────────────────────────────────────────────
    def test_서윤을_감춘다(self):
        m = re.search(r"#stageWrap\.petswap[^{]*\{([^}]*)\}", self.css)
        self.assertIsNotNone(m, "자리바꿈 때 캔버스를 감추는 규칙이 없다")
        self.assertIn("visibility:hidden", m.group(1).replace(" ", ""))

    def test_감출_때_display_none_을_안_쓴다(self):
        """★placePet() 이 캔버스 상자로 무대 크기를 잰다. display:none 이면
        그 상자가 0×0 이 되어 서햄터까지 사라진다."""
        m = re.search(r"#stageWrap\.petswap[^{]*\{([^}]*)\}", self.css)
        self.assertIsNotNone(m)
        self.assertNotIn("display:none", m.group(1).replace(" ", ""))

    def test_캔버스_둘_다_감춘다(self):
        """#gl 만 감추면 #fx(눈물·효과)가 허공에 남는다."""
        i = self.css.index("#stageWrap.petswap")
        blk = self.css[i:self.css.index("}", i)]
        self.assertIn("#gl", blk)
        self.assertIn("#fx", blk)

    def test_서윤을_VIEW_로_줄이지_않는다(self):
        """★VIEW 를 건드리면 말풍선·손잡이·마우스 추적이 전부 따라 움직인다.
        이제는 감추기만 하므로 computeView 에 자리바꿈 분기가 없어야 한다."""
        i = self.js.index("function computeView(")
        body = self.js[i:i + 2500]
        self.assertNotIn("PET.swap", body, "computeView 가 아직 서윤을 줄인다")

    # ── 돌아오는 길 ─────────────────────────────────────────────────
    def test_되돌아가기_팝업이_있다(self):
        """서윤이 화면에 없으므로, 이게 없으면 돌아올 길이 막힌다."""
        self.assertIn('id="petBack"', self.h)
        self.assertIn("$('#petBack').onclick = ()=>setSwap(false)", self.js)

    def test_팝업이_무대_안에_있다(self):
        i = self.h.index('id="stageWrap"')
        j = self.h.index('id="bubble"')
        self.assertIn('id="petBack"', self.h[i:j])

    def test_팝업이_자리바꿈_중에만_뜬다(self):
        m = re.search(r"#petBack\{([^}]*)\}", self.css)
        self.assertIsNotNone(m)
        self.assertIn("display:none", m.group(1).replace(" ", ""))
        self.assertIn("#petBack.on{display:flex}", self.css.replace(" ", ""))
        self.assertIn("pb.classList.toggle('on', on)", self.js)

    def test_팝업을_서햄터가_안_덮는다(self):
        """★서햄터가 무대를 크게 덮는다. 팝업이 그 아래로 들어가면 눌러도
        서햄터가 클릭을 먹어 영영 못 돌아온다."""
        pet = re.search(r"#pet\.swap\{[^}]*z-index:\s*(\d+)", _read(CSS))
        back = re.search(r"#petBack\{[^}]*z-index:\s*(\d+)", self.css)
        self.assertIsNotNone(pet)
        self.assertIsNotNone(back)
        self.assertGreater(int(back.group(1)), int(pet.group(1)))

    def test_팝업이_클릭을_받는다(self):
        m = re.search(r"#petBack\{([^}]*)\}", self.css)
        self.assertIsNotNone(m)
        self.assertNotIn("pointer-events:none", m.group(1).replace(" ", ""))
        self.assertIn("cursor:pointer", m.group(1).replace(" ", ""))

    # ── 팝업 얼굴 ───────────────────────────────────────────────────
    def test_팝업_얼굴을_의상에서_잘라_온다(self):
        """★자를 자리를 CSS 에 박으면 옷을 갈아입을 때 턱·어깨가 나온다.
        의상마다 머리 위치(CFG.headC)와 크기(headRad)가 다르다."""
        i = self.js.index("function petBackFace()")
        body = self.js[i:self.js.index("function setSwap(")]
        self.assertIn("CFG.headC", body)
        self.assertIn("CFG.headRad", body)
        self.assertIn("COSTUMES[costumeIdx]", body)

    def test_팝업_얼굴이_의상을_따라_바뀐다(self):
        i = self.js.index("function setCostume(")
        self.assertIn("petBackFace()", self.js[i:self.js.index("function buildCostumeChips(")])

    def test_잘린_그림이_상자_밖으로_안_나간다(self):
        """★머리 중심을 가운데로 맞추다 보면 그림 위/옆이 상자 밖으로 밀려
        빈 칸이 생긴다. Math.min(0,…)/Math.max(B-…) 로 가둔다."""
        i = self.js.index("function petBackFace()")
        body = self.js[i:self.js.index("function setSwap(")]
        self.assertIn("Math.min(0,", body.replace(" ", "").replace("Math.min(0,", "Math.min(0,"))
        self.assertIn("Math.max(B - W", body)
        self.assertIn("Math.max(B - H", body)

    # ── 손잡이 ─────────────────────────────────────────────────────
    def test_서햄터_더블클릭으로_바꾼다(self):
        i = self.js.index("function onPetPointer(")
        body = self.js[i:self.js.index("if($('#petChip'))")]
        self.assertIn("setSwap(!PET.swap)", body)
        self.assertIn("!dbl", body, "한 번 클릭에도 자리가 바뀐다")

    def test_없는_서윤을_좌표로_찾지_않는다(self):
        """★자리바꿈 중 서윤은 화면에 없다. 그 자리를 재서 갈라 주던 예전
        코드가 남아 있으면, 무대 아무 데나 눌러도 되돌아가 버린다."""
        i = self.js.index("function onPetPointer(")
        body = self.js[i:self.js.index("if($('#petChip'))")]
        self.assertNotIn("cssToImg", body)
        self.assertNotIn("onSeoyun", body)

    def test_사원증을_끈다(self):
        """★서윤이 없는 동안 사원증만 허공에 남으면 안 된다. 돌아올 때 원래대로."""
        i = self.js.index("function setSwap(")
        body = self.js[i:self.js.index("function onPetPointer(")]
        self.assertIn("_badgeBeforeSwap", body)
        self.assertIn("badgeOn = false", body)

    def test_서햄터를_끄면_자리도_되돌린다(self):
        """★끈 채로 자리바꿈이 남아 있으면 서윤도 서햄터도 없는 빈 무대가 된다."""
        i = self.js.index("function setPet(")
        body = self.js[i:self.js.index("/* ══════════ 자리바꿈")]
        self.assertIn("setSwap(false)", body)

    def test_이름이_서햄터다(self):
        self.assertIn("const PET_NAME = '서햄터'", self.js)
        self.assertIn("서햄터", self.h)


if __name__ == "__main__":
    unittest.main()
