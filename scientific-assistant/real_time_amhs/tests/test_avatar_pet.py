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


class 자리바꿈이_바꾸는_것(unittest.TestCase):
    """자리를 바꾸면 **말하는 사람이 바뀐다.** 얼굴만 햄스터인데 서윤이
    말하면 어긋난다 — 이름표·페르소나·설정 저장이 같이 따라가야 한다.

    ★"배경 변경하게 되면 겹치면서 나오는데" — applyBg() 가 무대의 class 를
      통째로 지워서 자리바꿈(petswap)까지 날아갔다. 감춰 뒀던 서윤이
      되살아나 서햄터와 겹쳤다. 여기서 그 자리를 못 박는다.
    """

    def setUp(self):
        self.js = _read(JS)
        self.css = _read(APPCSS)

    def _swap(self):
        i = self.js.index("function setSwap(")
        return self.js[i:self.js.index("function onPetPointer(")]

    # ── 배경을 바꿔도 자리바꿈이 살아 있다 ──────────────────────────
    def test_배경을_바꿔도_서윤이_안_돌아온다(self):
        """★applyBg() 의 wrap.className='' 이 petswap 을 지웠다."""
        for fn in ("function applyBg()", "chip[data-bg]"):
            i = self.js.index(fn)
            blk = self.js[i:i + 500]
            self.assertNotIn("wrap.className = ''", blk, fn + " 가 class 를 통째로 지운다")
            self.assertNotIn("wrap.className=''", blk, fn + " 가 class 를 통째로 지운다")

    def test_지울_때_남길_것을_적어_둔다(self):
        i = self.js.index("function wrapReset()")
        blk = self.js[i:i + 300]
        self.assertIn("WRAP_KEEP", blk)
        self.assertIn("'petswap'", self.js[self.js.index("const WRAP_KEEP"):][:80])

    # ── 이름 ───────────────────────────────────────────────────────
    def test_이름표가_서햄터가_된다(self):
        """agentName() 이 페르소나의 "이름:" 을 읽는다 — 페르소나를 갈아
        끼우면 "버추얼 에이전트 서햄터" 가 따라온다."""
        i = self.js.index("const PERSONA_HAMTER")
        head = self.js[i:i + 200]
        self.assertIn("이름: 서햄터", head)
        m = re.search(r"function agentName\(\)[\s\S]{0,300}?이름", self.js)
        self.assertIsNotNone(m, "agentName 이 페르소나의 이름을 안 읽는다")
        self.assertIn("paintAgentName()", self._swap(), "자리를 바꿔도 이름표가 그대로다")

    def test_이름표를_한_곳에서_그린다(self):
        """★두 군데서 그리면 한쪽만 고쳐서 어긋난다 — vnShow 가 따로
        그리고 있어서, 말을 걸기 전에는 서윤 이름이 그대로 남았다."""
        self.assertEqual(self.js.count("vnName"), 1,
                         "이름표를 여러 곳에서 그린다 — paintAgentName() 하나여야 한다")
        i = self.js.index("function paintAgentName(")
        self.assertIn("vnName", self.js[i:i + 250])

    def test_인사말_조사를_받침으로_고른다(self):
        """★그냥 붙였더니 "서햄터이에요" 가 나왔다."""
        i = self.js.index("안녕하세요! 버추얼 에이전트")
        blk = self.js[i:i + 200]
        self.assertIn("josa(", blk)
        self.assertNotIn("'이에요.", blk, "조사가 박혀 있다")

    # ── 페르소나 ───────────────────────────────────────────────────
    def test_페르소나가_같이_바뀐다(self):
        b = self._swap()
        self.assertIn("PERSONA_HAMTER", b)
        self.assertIn("_personaBeforeSwap", b)

    def test_서윤_페르소나를_안_잃는다(self):
        """★사용자가 직접 고친 페르소나다. 기본값으로 되돌리면 안 되고,
        복원 중에 두 번 들어와도 덮어쓰면 안 된다."""
        b = self._swap()
        self.assertIn("if(_personaBeforeSwap === null) _personaBeforeSwap = pe.value", b,
                      "이미 보관된 것을 덮어쓴다 — 서윤 페르소나가 사라진다")
        self.assertIn("pe.value = _personaBeforeSwap", b, "돌아올 때 안 되돌린다")

    def test_궁예와_보관함이_다르다(self):
        """★궁예 모드도 페르소나를 갈아 끼운다. 같은 변수를 쓰면 둘이 엉킨다."""
        i = self.js.index("$('#patchChip').onclick")
        blk = self.js[i:i + 900]
        self.assertIn("personaBackup", blk)
        self.assertNotIn("_personaBeforeSwap", blk)

    # ── 저장 ───────────────────────────────────────────────────────
    def test_저장하면_서햄터가_유지된다(self):
        i = self.js.index("function collectSettings(")
        self.assertIn("pet:petSaveState()", self.js[i:i + 1800])
        i2 = self.js.index("function applySettings(")
        self.assertIn("PET_SAVED=o.ui.pet", self.js[i2:i2 + 3000])
        self.assertIn("setSwap(true, true)", self.js, "다시 열 때 자리바꿈을 안 되살린다")

    def test_저장값을_늦게_푼다(self):
        """★loadSettings() 는 PET 선언보다 **위**에서 돈다. 거기서 PET 을
        건드리면 TDZ 로 죽는다 — 값만 받아 두고 아래에서 푼다."""
        self.assertLess(self.js.index("let PET_SAVED"), self.js.index("const PET ="))
        self.assertLess(self.js.index("const RESTORED = loadSettings()"),
                        self.js.index("const PET ="))

    def test_저장할_때_사원증_뜻을_지킨다(self):
        """★자리바꿈 중 badgeOn 은 늘 false 다. 그대로 저장하면 사원증
        설정이 지워진다 — 돌아왔을 때의 값을 저장한다."""
        i = self.js.index("function collectSettings(")
        self.assertIn("badge:badgeIntent()", self.js[i:i + 1800])

    def test_사원증을_창구로만_건드린다(self):
        """★자리바꿈 중에 배경·의상이 사원증을 켜면 서윤 없는 허공에
        사원증만 그려진다. setBadge() 가 그때는 보관만 한다."""
        for fn in ("function setBg(", "function setCostume("):
            i = self.js.index(fn)
            blk = self.js[i:i + 1400]
            self.assertNotIn("badgeOn=b.badge", blk, fn)
            self.assertNotIn("badgeOn = c.badge", blk, fn)
        i = self.js.index("function setBadge(")
        self.assertIn("petSwapped()", self.js[i:i + 300])

    def test_PET_이_없어도_안_죽는다(self):
        """★setCostume() 은 화면이 처음 뜰 때 PET 선언보다 먼저 지나간다."""
        i = self.js.index("function petSwapped()")
        self.assertIn("catch", self.js[i:i + 150])
        i2 = self.js.index("function petSaveState()")
        self.assertIn("catch", self.js[i2:i2 + 250])

    # ── 렌더링 ─────────────────────────────────────────────────────
    def test_렌더링_설정이_서햄터에도_걸린다(self):
        """★서윤에게만 걸리면, 자리를 바꾼 동안 줌·상하 위치를 움직여도
        아무 일도 안 일어난다."""
        i = self.js.index("function placePet()")
        body = self.js[i:self.js.index("function petBackAvoidVn()")]
        j = body.index("if(PET.swap){")
        swap = body[j:body.index("}else{")]
        self.assertIn("view.zoom", swap)
        self.assertIn("view.oy", swap)

    def test_팝업이_대사창을_안_덮는다(self):
        """★대사창은 무대 아래를 가로로 다 쓰고 쪽 넘김 단추(◀ ▶ ✕)가
        오른쪽 끝에 있다 — 그냥 bottom:14px 로 두면 그 단추를 덮는다."""
        m = re.search(r"#petBack\{([^}]*)\}", self.css)
        self.assertIsNotNone(m)
        self.assertIn("--vnH", m.group(1))
        i = self.js.index("function petBackAvoidVn()")
        blk = self.js[i:i + 600]
        self.assertIn("'--vnH'", blk)
        self.assertIn("getElementById('vn')", blk)


class 입(unittest.TestCase):
    """말할 때 서햄터 입술 아래가 벌어진다.

    ★그림에는 다문 입만 그려져 있다. 캐릭터가 WebGL 인 서윤과 달리
      서햄터는 그림 한 장이라 워핑할 메쉬가 없다 — 입술선 아래에 벌어지는
      모양을 하나 덧그리고, 벌어짐만 app.js 가 --talk 로 넣는다.
    ★신호는 서윤과 **같은 것**(talkEnv)을 쓴다. 따로 흔들면 둘이 어긋난다.
    """

    def setUp(self):
        self.css = _read(CSS)
        self.js = _read(JS)
        self.h = _read(HTML)

    def test_입이_있다(self):
        self.assertIn('<div class="mouth">', self.h)
        self.assertIn("#pet .mouth{", self.css)

    def test_머리_마스크_밖에_둔다(self):
        """★.head 에는 머리만 남기는 원형 마스크가 걸려 있다
        (19%×20% @ 48.9% 18.6%). 그 안에 넣으면 입 자리는 흐려져 사라진다."""
        i = self.h.index('id="pet"')
        blk = self.h[i:self.h.index('id="petBack"')]
        head = blk[blk.index('class="head"'):blk.index('class="jaw"')]
        self.assertNotIn("mouth", head, "입이 머리 마스크 안에 들어가 있다")
        self.assertIn('<div class="jaw"><div class="mouth">', blk)
        jaw = self.css[self.css.index("#pet .jaw{"):]
        jaw = jaw[:jaw.index("}")]
        self.assertNotIn("mask", jaw)

    def test_머리와_같이_흔들린다(self):
        """★.head 와 같은 흔들림(breathe·bob)을 물려받아야 머리에 붙어 보인다."""
        jaw = self.css[self.css.index("#pet .jaw{"):]
        jaw = jaw[:jaw.index("}")]
        for a in ("breathe", "bob"):
            self.assertIn(a, jaw, a + " 가 없다 — 입만 제자리에 남는다")

    def test_입술선_아래에서_벌어진다(self):
        """★그림에 눈금을 대고 쟀다 — 입술선이 만나는 꼭짓점이
        (49.1%, 29.3%) 다. 그보다 위에 놓으면 인중을 덮어 얼룩이 된다."""
        blk = self.css[self.css.index("#pet .mouth{"):]
        blk = blk[:blk.index("}")]
        top = float(re.search(r"top:([\d.]+)%", blk).group(1))
        left = float(re.search(r"left:([\d.]+)%", blk).group(1))
        wid = float(re.search(r"width:([\d.]+)%", blk).group(1))
        self.assertGreaterEqual(top, 28.5, "인중을 덮는다 — 입술선보다 위다")
        self.assertLessEqual(top, 30.5, "턱까지 내려갔다")
        self.assertAlmostEqual(left + wid / 2, 49.1, delta=1.0, msg="입이 가운데가 아니다")
        self.assertIn("transform-origin:50% 0%", blk, "위(입술선)를 축으로 안 벌어진다")
        self.assertIn("scaleY(var(--talk", blk)

    def test_서윤과_같은_신호로_움직인다(self):
        """★talkEnv 는 음절 타이머가 만드는 봉투다. 따로 흔들면 어긋난다."""
        i = self.js.index("function petMouth(")
        blk = self.js[i:i + 900]
        self.assertIn("talkEnv", blk)
        self.assertIn("view.mouthMax", blk, "'입 벌림 최대' 가 서햄터엔 안 걸린다")

    def test_어깨_위에서는_안_움직인다(self):
        """★그때 말하는 사람은 서윤이다."""
        i = self.js.index("function petMouth(")
        self.assertIn("PET.swap", self.js[i:i + 900])

    def test_매_프레임_따라간다(self):
        i = self.js.index("function placePet()")
        self.assertIn("petMouth(", self.js[i:self.js.index("function petMouth(")])

    def test_안_바뀌었으면_다시_안_쓴다(self):
        """★60번/초 커스텀 속성을 다시 쓰면 그때마다 #pet 아래가 다시 계산된다."""
        i = self.js.index("function petMouth(")
        self.assertIn("PET.lm", self.js[i:i + 900])

    def test_움직임_줄이기가_입을_안_끈다(self):
        """★흔들림이 아니라 **말하고 있다는 표시**다. 끄면 멈춘 것처럼 보인다."""
        i = self.css.index("prefers-reduced-motion")
        blk = self.css[i:i + 400]
        self.assertIn("#pet .jaw", blk, "입 흔들림은 같이 꺼야 한다")
        self.assertNotIn("#pet .mouth", blk, "입까지 꺼 버린다")


class 자리바꿈_인사(unittest.TestCase):
    """자리를 바꿀 때 서윤이 한 마디 한다 — 나갈 때와 돌아올 때."""

    def setUp(self):
        self.js = _read(JS)

    def test_두_대사가_있다(self):
        self.assertIn("계약직에서 해고된", self.js)
        self.assertIn("돌아왔어요", self.js)
        self.assertIn("const PET_BYE", self.js)
        self.assertIn("const PET_HI", self.js)

    def test_자리를_바꿀_때_말한다(self):
        i = self.js.index("function setSwap(")
        blk = self.js[i:self.js.index("function onPetPointer(")]
        self.assertIn("speak(on ? PET_BYE : PET_HI)", blk)

    def test_조용히_복원할_때는_말_안_한다(self):
        """★화면을 열자마자 작별 인사가 뜨면 안 된다."""
        i = self.js.index("function setSwap(")
        blk = self.js[i:self.js.index("function onPetPointer(")]
        self.assertLess(blk.index("if(quiet) return;"), blk.index("speak(on ?"))

    def test_나가는_인사에_서윤_이름이_붙는다(self):
        """★speak() 가 대사창을 그리면서 이름표를 지금 페르소나(서햄터)로
        덮는다 — 서햄터 이름을 달고 서윤이 작별하면 이상하다."""
        i = self.js.index("function setSwap(")
        blk = self.js[i:self.js.index("function onPetPointer(")]
        self.assertIn("const leaving = agentName()", blk)
        self.assertIn("paintAgentName(leaving)", blk)
        self.assertLess(blk.index("const leaving"), blk.index("pe.value = PERSONA_HAMTER"),
                        "페르소나를 바꾼 뒤에 이름을 읽는다 — 서햄터가 나온다")


if __name__ == "__main__":
    unittest.main()
