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
        """실물 M14A: 평행 레일 사이 중앙값 0.30 m. 판 0.56 m 를 그대로 쓰면 83% 가 겹친다."""
        self.assertIn("railScale: 0.45,", self.s, "기본이 1.0 이면 레일이 한 덩어리로 뭉친다")
        self.assertIn("this.local(0, 0.1 * rs, 0, len + 0.04, 0.05 * rs, 0.56 * rs);", self.s,
                      "판·바 둘 다 배수를 타야 한다")
        self.assertIn("buildRails() {", self.s, "굵기를 바꾸면 다시 세워야 한다")

    def test_크기_패널이_3D_안에_있다(self):
        # 고객: "아이소메트리 [안에] 만들어야되" — 2D 설정과 섞지 않는다
        self.assertIn('data-a="size"', self.s)
        self.assertIn("class = 'o3d-size'", self.s.replace('className', 'class'))
        for k in ("['rs', '레일 굵기'", "['vs', '차량'", "['ps', '설비'", "['ts', '글자'"):
            self.assertIn(k, self.s, k)
        self.assertIn("[data-s=reset]", self.s, "기본값 단추")
        self.assertIn("this.emit('sizechange'", self.s, "화면이 저장할 수 있게 알려야 한다")

    def test_크기_저장은_2D_와_따로(self):
        self.assertIn("const V3D_SIZE_KEY = 'oht_world_v3d_size_v1';", self.h)
        self.assertIn("inst.on('sizechange', v3dSizeSave);", self.h)
        self.assertIn("...v3dSizeLoad(),", self.h, "다음에 열 때 그 크기로")

    def test_네_색만_준_옛_호출도_산다(self):
        self.assertIn("if (o.colors.state.length < ST_NAME.length)", self.s)


class 서버(unittest.TestCase):
    def test_static_을_서빙한다(self):
        s = _read("main.py")
        self.assertIn("from fastapi.staticfiles import StaticFiles", s)
        self.assertIn('_STATIC_DIR = bundled_dir() / "static"', s, "번들(_MEIPASS)에서도 찾으려면 bundled_dir 기준")
        self.assertIn('app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")', s)
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
        self.assertIn("await import('/static/js/oht3d/oht3d.js')", m.group(0))
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


if __name__ == "__main__":
    unittest.main()
