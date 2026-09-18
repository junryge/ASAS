# -*- coding: utf-8 -*-
"""'⬢ 아이소메트리' — three.js 3D 보기가 월드모델파생 화면에 제대로 붙었나.

고객이 준 이식 세트(oht3d_port: three.js r169 + oht3d.js)를 '유사 3D' 옆 세 번째
단추로 붙였다. 지키는 것:
  · 기본은 그대로 2D. 3D 는 단추를 눌러야 받는다(동적 import).
  · 3D 는 2D 와 **같은 데이터**를 쓴다 — 레이아웃은 /api/layout-graph, 차량은
    updateUI 의 그 프레임. 3D 만의 조회 길을 내지 않는다.
  · 폐쇄망: three.js 는 CDN 이 아니라 static/ 에서 나간다. 서버가 /static 을
    서빙하고, PyInstaller 번들에도 static/ 이 들어간다.
  · 점수·재생 엔진·2D 그리기는 안 건드린다.
"""
import os
import re
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)


def _read(*p):
    with open(os.path.join(APP, *p), encoding="utf-8") as fh:
        return fh.read()


class 정적파일(unittest.TestCase):
    def test_세트가_static_에_있다(self):
        for f in ("oht3d.js", "three.module.min.js"):
            self.assertTrue(os.path.isfile(os.path.join(APP, "static", "js", "oht3d", f)), f + " 가 없다")

    def test_three_는_r169(self):
        s = _read("static", "js", "oht3d", "three.module.min.js")
        self.assertIn('const t="169"', s, "세트가 준 three.js r169 그대로여야 한다 (REVISION 상수)")
        self.assertIn("Copyright 2010-2024 Three.js Authors", s[:400])

    def test_뷰어가_ES_모듈로_파싱된다(self):
        node = _node()
        if not node:
            self.skipTest("node 가 없다 (폐쇄망)")
        p = subprocess.run([node, "-e", "import('file://%s').then(m=>{if(!m.createOHT3D)process.exit(2)})"
                            % os.path.join(APP, "static", "js", "oht3d", "oht3d.js").replace("\\", "/")],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr[-600:])


class 뷰어에_보탠_것(unittest.TestCase):
    """원본 세트와 다른 곳 — 아이소메트리 카메라 · OBS · 테마 · setActive."""

    @classmethod
    def setUpClass(cls):
        cls.s = _read("static", "js", "oht3d", "oht3d.js")
        cls.h = _read("dashboard.html")

    def test_아이소메트리_직교_카메라(self):
        self.assertIn("new T.OrthographicCamera(", self.s, "원본은 원근뿐이었다 — 등각(직교)이 있어야 '아이소메트리' 다")
        self.assertIn("ISO_AZ = Math.PI / 4", self.s)
        self.assertIn("ISO_EL = Math.atan(1 / Math.SQRT2)", self.s, "등각 = 35.264°")
        self.assertIn("projection: 'persp'", self.s, "기본은 원본대로 원근 — 화면 쪽이 'iso' 로 연다")
        self.assertIn("setProjection(mode)", self.s)

    def test_직교_절두체는_dist_로_잡는다(self):
        # 원근용 시점 계산(allView·zoneView·withPanel·라벨)이 그대로 맞으려면 반높이 = dist·tan(16°)
        self.assertIn("const hh = o.dist * Math.tan(HALF_FOV)", self.s)
        m = re.search(r"const pm5 = this\.cam\.isPerspectiveCamera \? [^\n]*1 / Math\.tan\(HALF_FOV\)", self.s)
        self.assertIsNotNone(m, "직교에서는 라벨 겹침 계산이 투영행렬[5] 를 쓰면 안 된다")

    def test_시점_각도는_투영을_따른다(self):
        # 원본은 az -2.3 을 세 군데 박아 두었다 — 아이소에서 그리로 날아가면 등각이 깨진다
        for fn in ("zoneView(zi)", "allView()", "hotView(zi = -1)"):
            body = self.s[self.s.index(fn + " {"):]
            body = body[:body.index("\n  }")]
            self.assertNotIn("az: -2.3", body, fn + " 에 -2.3 이 박혀 있다")
            self.assertIn("...this.ang(", body, fn + " 은 ang() 으로 각도를 받아야 한다")
        self.assertEqual(self.s.count("az: -2.3"), 2, "원근 기본 각도는 orbit 초기값과 ang() 두 곳뿐")

    def test_OBS_가_다섯째_상태(self):
        self.assertIn("const ST_NAME = ['운행', '적재', '정지', 'JAM', 'OBS'];", self.s)
        self.assertIn("OBS: 4, OBS_BZ_STOP: 4", self.s)
        self.assertIn("st = clamp(st | 0, 0, ST_MAX);", self.s, "3 으로 자르면 OBS 가 JAM 이 된다")
        self.assertIn("c: [0, 0, 0, 0, 0]", self.s, "존 통계도 다섯")
        self.assertIn("obs: s.c[4]", self.s)
        self.assertEqual(self.s.count("'#f97316'"), 1, "OBS 기본색")

    def test_테마와_색을_나중에_바꿀_수_있다(self):
        for need in ("if (p.projection != null) this.setProjection(p.projection);",
                     "if (p.dark !== undefined)", "if (p.background)",
                     "if (Array.isArray(p.stateColors)"):
            self.assertIn(need, self.s, need)

    def test_숨겨진_동안_쉰다(self):
        self.assertIn("setActive: on =>", self.s)
        self.assertIn("if (!this.G || !this.active) return;", self.s)

    def test_벽을_뺄_수_있다(self):
        self.assertIn("walls: true,", self.s, "기본은 원본대로 벽 있음")
        self.assertIn("this.walls = this.o.walls === false ? [] :", self.s, "walls:false 면 외곽 벽도 안 세워야 한다")
        # ★바닥이 0.8 m 상자면 그 옆면이 낮은 벽처럼 둘러싼다 — 벽을 뺄 땐 평면이어야 한다
        self.assertIn("const noWall = this.o.walls === false;", self.s)
        self.assertIn("? new T.Mesh(new T.PlaneGeometry(W, D), this.mat(0xd6d9dc, { r: 0.9 }))", self.s)

    def test_레일이_평행_간격보다_좁다(self):
        """실물 M14A: 평행 레일 사이 중앙값 0.30 m. 판 0.56 m 를 그대로 쓰면 83% 가 겹친다.

        ★숫자를 못박지 않는다 — 고객이 화면에서 맞춰 정한다(지금 0.20).
          지켜야 할 것은 '판 0.56 m × 배수 < 0.30 m' 하나다.
        """
        m = re.search(r"railScale:\s*([\d.]+)", self.s)
        self.assertIsNotNone(m, "railScale 기본값이 없다")
        rs = float(m.group(1))
        self.assertLess(0.56 * rs, 0.30,
                        f"판 폭 {0.56 * rs:.2f} m 가 평행 간격 0.30 m 보다 넓다 — 한 줄로 뭉쳐 보인다")
        self.assertIn("this.local(0, 0.1 * rs, 0, len + 0.04, 0.05 * rs, 0.56 * rs);", self.s,
                      "판·바 둘 다 배수를 타야 한다")
        self.assertIn("buildRails() {", self.s, "굵기를 바꾸면 다시 세워야 한다")

    def test_크기_패널은_코드에_남아_있다(self):
        """고객: "아이소메트리 [안에] 만들어야되" — 2D 설정과 섞지 않는다.

        ★2026-09: 크기를 정하고 나서 패널은 **안 띄운다**(sizeUI:false). 코드는
          남겨 둔다 — 다시 맞출 때 sizeUI 만 켜면 슬라이더가 그대로 나온다.
        """
        self.assertIn('data-a="size"', self.s)
        self.assertIn("class = 'o3d-size'", self.s.replace('className', 'class'))
        for k in ("['rs', '레일 굵기'", "['vs', '차량'", "['ps', '설비'", "['ts', '글자'"):
            self.assertIn(k, self.s, k)
        self.assertIn("[data-s=reset]", self.s, "기본값 단추")
        self.assertIn("this.emit('sizechange'", self.s, "화면이 저장할 수 있게 알려야 한다")

    def test_크기는_2D_설정과_섞지_않는다(self):
        """★2026-09: 크기를 고객이 정하고 패널을 닫으면서 '이 브라우저에 저장'
        도 그만뒀다. 저장해 둔 옛 값이 정해 준 기본값을 덮으면 안 되기 때문이다
        (자세한 것은 화면에서_정한_기본값). 여기서는 2D 설정(⚙)과 섞이지
        않았다는 것만 본다 — 2D 는 px 배수, 3D 는 m 배수라 뜻이 다르다."""
        self.assertNotIn("mapSettings.vehicleRadius", self.h.split("createOHT3D(box, {")[1][:900],
                         "3D 에 2D 의 px 크기를 넘기면 안 된다")
        self.assertIn("sizeUI: false,", self.h)

    def test_네_색만_준_옛_호출도_산다(self):
        self.assertIn("if (o.colors.state.length < ST_NAME.length)", self.s)


class 서버(unittest.TestCase):
    def test_static_을_서빙한다(self):
        s = _read("main.py")
        self.assertIn("from fastapi.staticfiles import StaticFiles", s)
        self.assertIn('_STATIC_DIR = bundled_dir() / "static"', s, "번들(_MEIPASS)에서도 찾으려면 bundled_dir 기준")
        # ★2026-09-18: 그냥 StaticFiles 면 Cache-Control 이 안 붙어 브라우저가
        #   묻지도 않고 옛 파일을 쓴다 — oht3d.js 를 올려도 3D 가 그대로였다.
        self.assertIn('app.mount("/static", _NoCacheStatic(directory=str(_STATIC_DIR)), name="static")', s)
        self.assertIn("if _STATIC_DIR.is_dir():", s, "폴더가 없어도 서버는 떠야 한다")

    def test_번들에_static_이_들어간다(self):
        s = _read("oht_world.spec")
        self.assertIn("('static', 'static')", s, "exe 로 묶으면 static 이 빠져 3D 가 안 뜬다")

    def test_재생_엔진은_안_건드렸다(self):
        for f in ("replay_engine.py", "world_model.py", "data_loader.py"):
            self.assertNotIn("oht3d", _read(f).lower(), f)


class 화면(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = _read("dashboard.html")

    def test_유사3D_옆에_아이소메트리_단추(self):
        m = re.search(r'<button id="btn-iso"[^\n]*\n\s*<button id="btn-3d"[^>]*onclick="setMapView\(\'3d\'\)"[^>]*>⬢ 아이소메트리</button>', self.h)
        self.assertIsNotNone(m, "단추가 유사 3D 바로 옆이 아니거나 글자가 다르다")

    def test_기본은_그대로_2D(self):
        self.assertIn('<button id="btn-2d"  class="toggle-btn on"', self.h)
        self.assertIn('<button id="btn-3d"  class="toggle-btn"    ', self.h)
        self.assertIn("let show3D = false", self.h)

    def test_3D_는_2D_캔버스와_같은_자리(self):
        m = re.search(r'<canvas id="map-canvas"></canvas>\s*<!--[^\n]*-->\s*<div id="map-3d"></div>', self.h)
        self.assertIsNotNone(m)
        self.assertIn("#map-3d { display:none; position:absolute; inset:0; }", self.h)
        self.assertIn("#map-container { flex:1; position:relative;", self.h, "부모가 relative 여야 inset:0 이 맞는다")

    def test_보기_전환이_셋을_안다(self):
        m = re.search(r"function setMapView\(mode\) \{[\s\S]*?\n\}", self.h)
        self.assertIsNotNone(m)
        blk = m.group(0)
        for need in ("three = (mode === '3d')", "if (three) open3D(); else close3D();",
                     "on('btn-3d', show3D)", "on('btn-2d', !showIso && !show3D)", "if (!show3D) drawMap();"):
            self.assertIn(need, blk, need)
        # 표시 토글도 단추 불을 셋으로 맞춘다
        self.assertIn("on('btn-2d', !showIso && !show3D); on('btn-3d', show3D);", self.h)

    def test_같은_프레임이_3D_로_간다(self):
        # updateUI 가 mapData.vehicles 를 놓은 직후 — 3D 만의 조회 길이 없다
        self.assertIn("mapData.hotspots = d.hotspots || [];\n  push3D(d);", self.h)
        self.assertNotIn("/api/oht3d", self.h, "3D 전용 API 를 내지 않는다")

    def test_2D_그리기는_3D_동안_쉰다(self):
        self.assertIn("function drawMap() {\n  if (show3D) return;", self.h)

    def test_선택과_전체보기가_3D_로_간다(self):
        self.assertIn("if (show3D) { if (v3d) v3d.focusVehicle(vid); renderOHTList(); return; }", self.h)
        self.assertIn("if (show3D) { if (v3d) v3d.focusZone(z3dId(z)); renderZoneList(); return; }", self.h)
        self.assertIn("if (show3D && v3d) { v3d.focusZone(-1, false); v3d.viewAll(); }", self.h)

    def test_테마와_FAB_전환이_3D_에도_간다(self):
        self.assertIn("if (typeof sync3DTheme === 'function') sync3DTheme();", self.h)
        self.assertIn("if (v3d) sync3DLayout();", self.h)

    def test_TDZ_상태_선언은_applyPageTheme_보다_앞(self):
        # applyPageTheme() 는 스크립트 앞쪽에서 바로 불린다 — 그 안이 v3d 를 본다
        i_let = self.h.index("let show3D = false, v3d = null")
        i_call = self.h.index("\napplyPageTheme();")
        self.assertLess(i_let, i_call, "let 이 뒤에 있으면 로드 때 ReferenceError")

    def test_뷰어는_눌러야_받고_static_경로가_서버와_같다(self):
        m = re.search(r"async function open3D\(\) \{[\s\S]*?\n\}", self.h)
        self.assertIsNotNone(m)
        # 주소에 판 번호가 붙는다 — 이미 브라우저에 박힌 옛 파일을 지나치기 위해
        self.assertIn("await import('/static/js/oht3d/oht3d.js?v=' + V3D_BUILD)", m.group(0))
        self.assertIn("projection: 'iso'", m.group(0), "단추 이름이 아이소메트리다 — 등각으로 열어야 한다")
        self.assertIn("walls: false,", m.group(0), "벽 없이 연다 (고객: 벽 필요없다)")
        self.assertIn("coordScale: V3D_SCALE", m.group(0))
        self.assertIn("const V3D_SCALE = 0.01;", self.h)
        self.assertIn("class=\"v3d-err\"", m.group(0), "못 받으면 왜인지 화면에 적어야 한다")

    def test_절_표식(self):
        self.assertIn("// ===== 3D 아이소메트리 (시작) =====", self.h)
        self.assertIn("// ===== 3D 아이소메트리 (끝) =====", self.h)


def _node():
    for c in ("/opt/node22/bin/node", "node", "nodejs"):
        try:
            subprocess.run([c, "-v"], capture_output=True, check=True)
            return c
        except (OSError, subprocess.CalledProcessError):
            continue
    return None


class 데이터층_실행(unittest.TestCase):
    """layout3D · vehicle3D · state3D 를 **그대로 떼어** 돌린다 (tests/iso3d.js)."""

    def test_iso3d_js(self):
        node = _node()
        if not node:
            self.skipTest("node 가 없다 (폐쇄망)")
        p = subprocess.run([node, os.path.join(HERE, "iso3d.js")], capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, (p.stdout + p.stderr)[-1200:])


class 화면에서_정한_기본값(unittest.TestCase):
    """2026-09 고객이 화면에서 맞춰 보고 정한 값 — 이 값으로 열려야 한다.

        레일 굵기 0.20 · 차량 0.40 · 설비 0.40 · 글자 0.80
    '크기' 패널은 안 띄운다. 값이 사람마다 달라지면 같은 화면을 봤다고 말할 수
    없다 — 다시 맞출 일이 생기면 sizeUI:true 로 슬라이더를 꺼내면 된다.
    """

    @classmethod
    def setUpClass(cls):
        cls.j = _read("static", "js", "oht3d", "oht3d.js")
        cls.h = _read("dashboard.html")

    def test_크기_기본값(self):
        for k, v in (("railScale", "0.20"), ("vehicleScale", "0.40"),
                     ("portScale", "0.40"), ("textScale", "0.80")):
            self.assertRegex(self.j, r"%s:\s*%s\s*," % (k, re.escape(v)), k)

    def test_크기_패널은_안_띄운다(self):
        self.assertRegex(self.j, r"sizeUI:\s*false")
        self.assertIn("if (o.sizeUI) this._buildSizePanel(r, o);", self.j)
        # 단추도 sizeUI 일 때만
        self.assertIn("${o.sizeUI ? '<button class=\"o3d-btn\" data-a=\"size\"", self.j)
        self.assertIn("sizeUI: false,", self.h, "화면에서도 끈 채로 연다")

    def test_옛_저장값이_기본값을_덮지_않는다(self):
        """★'정책을 바꿨는데 화면이 그대로' 와 같은 결. 패널을 없앴으니
        예전에 그 패널로 저장해 둔 값은 지우고 다시 안 읽는다."""
        self.assertIn("localStorage.removeItem(V3D_SIZE_KEY)", self.h)
        self.assertNotIn("v3dSizeLoad()", self.h)
        self.assertNotIn("v3dSizeSave", self.h)

    def test_뷰어_안_패널은_아예_안_만든다(self):
        """고객: "아이소메트리 패널 빼라".

        화면 오른쪽 사이드바에 같은 목록(OHT 상태 · HID Zone)이 이미 있다.
        둘을 같이 띄우면 맵이 양쪽에서 잘리고, 같은 표가 둘이라 어느 쪽이
        맞는지 헷갈린다 — 사이드바 하나로 2D · 유사3D · 아이소메트리를 다 본다."""
        self.assertIn("panel: false,", self.h, "월드모델파생은 뷰어 패널을 안 만든다")
        self.assertRegex(self.j, r"panelOpen:\s*true")   # 뷰어 자체 기본은 예전 그대로
        self.assertIn("o.panelOpen === false || r.clientWidth <= 700", self.j)

    def test_뷰어에는_패널_길이_남아_있다(self):
        """다른 데서 쓸 수 있게 코드는 남긴다 — 안 쓸 뿐이다."""
        self.assertIn("data-a=\"panel\"", self.j)
        self.assertIn("_buildPanel(r, bar)", self.j)


class 설비_끄고_켜기(unittest.TestCase):
    """고객이 사진으로 짚은 것 — 바닥에 선 회색 상자 + 기둥 + 초록 상태등.
    그게 **설비(포트)** 다. 그것만 끄고 켠다 (다른 건 안 건드린다)."""

    @classmethod
    def setUpClass(cls):
        cls.j = _read("static", "js", "oht3d", "oht3d.js")

    def test_단추가_있다(self):
        self.assertIn('data-a="ports"', self.j)
        self.assertRegex(self.j, r"ports:\s*true")
        self.assertIn(">설비</button>", self.j)

    def test_설비_묶음_하나만_끈다(self):
        i = self.j.index("applyPorts() {")
        body = self.j[i:i + 260]
        self.assertIn("this.portGroup.visible = this.opt.ports !== false", body)

    def test_다른_것은_안_건드린다(self):
        """바닥판·격자·존 바닥판·레일·차량은 그대로여야 한다."""
        i = self.j.index("applyPorts() {")
        body = self.j[i:i + 260]
        for k in ("zoneMeshes", "railGroup", "vehGroup", "floor", "grid"):
            self.assertNotIn(k, body, k + " 를 건드리면 안 된다")
        self.assertNotIn("floorParts", self.j, "바닥을 끄는 길은 안 만든다")
        self.assertNotIn('data-a="floor"', self.j)

    def test_다시_세워도_꺼진_채로_남는다(self):
        """설비 크기를 바꾸면 buildPorts 가 다시 세운다 — 그때 되살아나면 안 된다."""
        i = self.j.index("this._buildPortBodies(X, Z, this.opt.ps || 1);\n    this.applyPorts();")
        self.assertGreater(i, 0)
        self.assertIn("this.portGroup.visible = this.opt.ports !== false;", self.j)

    def test_setOptions_로도_된다(self):
        self.assertIn("if (p.ports != null) { this.opt.ports = !!p.ports; this.applyPorts(); }", self.j)


class 정체_지점_표시(unittest.TestCase):
    """고객: "정체지점 클릭하면 위치좀 빨간색으로 표시좀 해주라 — 빨간색 뿌옇게"."""

    @classmethod
    def setUpClass(cls):
        cls.j = _read("static", "js", "oht3d", "oht3d.js")

    def test_빨갛다(self):
        i = self.j.index("_hotTex() {")
        tex = self.j[i:i + 900]
        self.assertIn("rgba(239,68,68,0.85)", tex, "가운데는 진한 빨강")
        self.assertIn("rgba(239,68,68,0.00)", tex, "가장자리는 투명")

    def test_뿌옇다(self):
        """테두리가 또렷하면 '구역' 처럼 보여 존 바닥판과 헷갈린다."""
        i = self.j.index("_hotTex() {")
        self.assertIn("createRadialGradient", self.j[i:i + 900])
        b = self.j[self.j.index("buildHotMark() {"):]
        self.assertIn("transparent: true", b[:1400])
        self.assertIn("depthWrite: false", b[:1400], "이게 없으면 레일·설비가 가려진다")

    def test_정체가_있을_때만_표시한다(self):
        """없는데 표시하면 '여기가 정체' 라고 거짓말하는 것이다."""
        i = self.j.index("markHot() {")
        body = self.j[i:i + 400]
        self.assertIn("if (!h) { this.clearHot(); return false; }", body)
        # [x, y, 대수, 구역번호] — 구역은 이름표에 쓴다
        self.assertIn("this.hotAt = best ? [best[0], best[1], bc, bz] : null;", self.j)

    def test_어디인지_이름표를_띄운다(self):
        """고객: "뿌연 빨간색에 어디 HID인지 위에 표시해줘; 구역을"."""
        self.assertIn("this.hotLabel = L;", self.j)
        self.assertIn("drawHotLabel(zi, n)", self.j)
        self.assertIn("'구역 밖'", self.j, "구역을 모르면 그렇게 적는다")

    def test_정체_지점_단추가_표시까지_한다(self):
        i = self.j.index("if (a === 'hot') {")
        body = self.j[i:i + 400]
        self.assertIn("this.hotView(this.sel)", body)
        self.assertIn("this.markHot()", body)
        self.assertLess(body.index("markHot"), body.index("flyTo"),
                        "표시를 먼저 놓고 날아가야 도착했을 때 이미 보인다")

    def test_전체를_누르면_지운다(self):
        i = self.j.index("if (a === 'all')")
        self.assertIn("this.clearHot()", self.j[i:i + 250])

    def test_바닥판_위에_뜬다(self):
        """존 바닥판(0.02)·격자(0.005) 아래 깔리면 안 보인다."""
        i = self.j.index("buildHotMark() {")
        self.assertIn("disc.position.y = 0.06;", self.j[i:i + 1400])




if __name__ == "__main__":
    unittest.main()
