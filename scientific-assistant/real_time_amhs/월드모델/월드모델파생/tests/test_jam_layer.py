# -*- coding: utf-8 -*-
"""정체 구간 붉은 표시 — 2D · 유사 3D.

고객: "2D, 유사3D도 정체구간 표시 빨간색 뿌옇게 하는거 기능 집어 넣어주라
       버튼 만들어서" · "옵션 같이 써야지 2D, 유사3D" · "위에 버튼 만들어라"

  · 단추는 위 표시 줄에 하나. 2D 와 유사 3D 가 **같이 쓴다** (보기를 바꿔도 유지)
  · 3D 의 '정체 지점' 은 제일 심한 한 곳으로 날아가는 단추다. 2D 는 맵 전체가
    들어오므로 **몰린 곳을 전부** 칠한다
  · 붉고 뿌옇게 — 테두리가 또렷하면 HID Zone 구역과 헷갈린다
  · 차량 **밑에** 깐다. 위에 덮으면 세모가 붉게 묻혀 안 보인다
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


def _node():
    for c in ("/opt/node22/bin/node", "node", "nodejs"):
        try:
            subprocess.run([c, "-v"], capture_output=True, check=True)
            return c
        except (OSError, subprocess.CalledProcessError):
            continue
    return None


class 단추(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = _read("dashboard.html")

    def test_위_표시_줄에_있다(self):
        m = re.search(r'<button id="btn-hotspot"[\s\S]{0,400}?<button id="btn-jam"[^>]*>정체</button>', self.h)
        self.assertIsNotNone(m, "표시 레이어 줄에 '정체' 단추가 없다")
        self.assertIn("toggleLayer('jam')", m.group(0))

    def test_기본은_꺼짐(self):
        """늘 켜 두면 정체가 없는 날에도 화면이 붉게 보인다."""
        self.assertIn("let showJam = false;", self.h)
        self.assertNotRegex(self.h, r'id="btn-jam" class="toggle-btn on"')

    def test_2D_와_유사3D_가_같이_쓴다(self):
        """보기를 바꿨다고 표시가 꺼지면 '같이 쓰는 옵션' 이 아니다."""
        m = re.search(r"function setMapView\(mode\) \{[\s\S]*?\n\}", self.h)
        self.assertIsNotNone(m)
        self.assertNotIn("showJam", m.group(0))
        # 그리는 곳은 한 군데 — 두 보기가 같은 캔버스·같은 투영(toS)을 쓴다
        self.assertEqual(self.h.count("drawJamBlobs(mapCtx, toS, sc)"), 1)

    def test_3D_단추와_헷갈리지_않게(self):
        """3D 툴바의 '정체 지점' 은 날아가는 단추, 여기 '정체' 는 표시 레이어다."""
        self.assertIn('title="정체(JAM) 구간을 붉게 뿌옇게 — 2D·유사 3D 같이 씁니다"', self.h)


class 그리기(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = _read("dashboard.html")

    def test_차량_밑에_깐다(self):
        i = self.h.index("if (showJam) drawJamBlobs(mapCtx, toS, sc);")
        j = self.h.index("for (const vid in vehicleDisplay) {", i)
        self.assertGreater(j, i, "차량보다 먼저 그려야 세모가 안 묻힌다")

    def test_묶는_크기가_3D_와_같다(self):
        """같은 상황을 두 화면이 다르게 '한 무리' 라고 하면 안 된다."""
        self.assertIn("const JAM_R = 1200;", self.h)          # 도면 1단위 = 10mm → 12 m
        j = _read("static", "js", "oht3d", "oht3d.js")
        self.assertIn("Math.hypot(a.p.x - b.p.x, a.p.y - b.p.y) < 12", j, "3D 는 m 단위로 12")

    def test_뿌옇다(self):
        i = self.h.index("function drawJamBlobs(")
        body = self.h[i:i + 2000]
        self.assertIn("createRadialGradient", body)
        self.assertIn("rgba(${rgb},0)", body, "가장자리는 투명이어야 한다")

    def test_몇_대_이상인지_직접_적는다(self):
        """고객: "정체 판정 직접 숫자로 기입하게 해야지 · 니가 정하면 우짜노 ·
        0이면 아무 효과 없는거구 · 멈춰선차는 제일 마지막 숫자로 하고".

        고른 목록(드롭다운)이 아니라 **직접 적는 숫자 세 칸**이다."""
        for k, v in (("jamMinJam", "1"), ("jamMinObs", "0"), ("jamMinStop", "0")):
            self.assertRegex(self.h, r"%s:\s*%s," % (k, v), k + " 기본값")
        for i in ("ms-jamMinJam", "ms-jamMinObs", "ms-jamMinStop"):
            self.assertIn('<input type="number" id="%s"' % i, self.h,
                          i + " 는 고르는 상자가 아니라 적는 칸이어야 한다")
        self.assertNotIn("jamStates", self.h, "옛 문자열 설정이 남아 있다")
        self.assertGreater(self.h.index('id="ms-jamMinStop"'), self.h.index('id="ms-jamMinObs"'),
                           "멈춘 차가 제일 마지막")
        self.assertIn("{ key: 'jamMinStop', name: '멈춘 차'", self.h)

    def test_0_이면_아무_효과_없다(self):
        i = self.h.index("function jamClusters(")
        body = self.h[i:i + 700]
        self.assertIn("if (!mins.some(n => n > 0)) return [];", body,
                      "셋 다 0 이면 아무것도 안 잡아야 한다")
        self.assertIn("if (k >= 0 && mins[k] > 0) js.push", body,
                      "0 인 종류는 후보에도 안 넣는다")
        j = self.h.index("function jamMins()")
        self.assertIn("(isNaN(n) || n < 0) ? 0 : n", self.h[j:j + 400],
                      "빈칸·글자·음수도 0 으로")

    def test_어느_한_종류라도_넘으면_정체(self):
        """3·5·0 = JAM 3대 이상 **또는** OBS 5대 이상."""
        i = self.h.index("function jamClusters(")
        self.assertIn("if (!cnt.some((c, i) => mins[i] > 0 && c >= mins[i])) continue;",
                      self.h[i:i + 2400])

    def test_저장된다(self):
        """★⚙ 의 다른 값과 같은 길로 저장된다 — 저장 + 적용이면 끝."""
        i = self.h.index("function applyMapSettings()")
        body = self.h[i:i + 700]
        self.assertIn("for (const k of Object.keys(DEFAULT_MAP_SETTINGS))", body)
        self.assertIn("typeof DEFAULT_MAP_SETTINGS[k] === 'number'", body,
                      "숫자 칸은 숫자로 읽어야 한다")
        self.assertIn("saveMapSettings();", body)
    def test_아이소메트리도_같은_설정을_따른다(self):
        """고객: "아이소메트리 정체 판정 만들어야되;;;있어야겠네;;"

        한동안은 뷰어가 제 기준(JAM+OBS·대수 무관)을 썼다. 이제 ⚙ 설정의
        '몇 대 이상' 세 칸이 jamMin 으로 넘어간다 — 세 화면이 한 기준이다."""
        self.assertIn("jamMin: jamMins()", self.h, "뷰어를 열 때 넘겨야 한다")
        i = self.h.index("function sync3DTheme()")
        self.assertIn("jamMin: jamMins()", self.h[i:i + 500],
                      "설정을 바꿨을 때도 다시 넘겨야 한다 (안 그러면 새로고침해야 먹는다)")
        j = _read("static", "js", "oht3d", "oht3d.js")
        self.assertIn("jamMin: null,", j, "뷰어 기본은 null — 다른 데서 열면 예전 규칙")
        self.assertIn("const JAM_ST = [3, 4, 2];", j,
                      "3D 상태 코드로 JAM·OBS·멈춘 차 (0 운행·1 적재·2 정지·3 JAM·4 OBS)")
        self.assertIn("if (p.jamMin !== undefined)", j, "설정이 바뀌면 받아야 한다")
        # 설정창에도 그렇게 적어야 한다 — 안 적으면 "왜 다르냐" 가 또 나온다
        self.assertIn("2D · 유사 3D · 아이소메트리", self.h)
        self.assertNotIn("아이소메트리는 이 설정을 안 따릅니다", self.h)

    def test_한_종류라도_넘으면_정체_규칙이_아이소메트리에도_있다(self):
        j = _read("static", "js", "oht3d", "oht3d.js")
        i = j.index("hotView(zi = -1)")
        body = j[i:i + 2200]
        self.assertIn("mins && !cnt.some((v, i) => mins[i] > 0 && v >= mins[i])", body,
                      "어느 한 종류라도 넘으면 정체 — 2D 와 같은 규칙")
        self.assertIn("continue", body, "못 넘긴 무리는 버려야 한다")

    def test_설정을_바꾸면_찍어_둔_표시를_지운다(self):
        """옛 기준으로 그려 둔 붉은 표시가 남아 있으면 '설정을 바꿨는데 그대로'
        가 된다. 다시 누르면 새 기준으로 잡힌다."""
        j = _read("static", "js", "oht3d", "oht3d.js")
        i = j.index("if (p.jamMin !== undefined)")
        self.assertIn("this.clearHot()", j[i:i + 400])


class 대수마다_세기가_다르다(unittest.TestCase):
    """고객: "2D,유사3D,아이소메트리 전부다 뿌연 빨간색인데 대수마다 뿌연도
    다르게 해야되...20대이상이 제일 심하게 히트맵 비전 알지 그걸로 해야되."

    몇 대가 몰렸나로 **색과 진하기가 같이** 간다 — 노랑(옅음) → 주황 → 빨강 →
    짙은 적. 20대에서 꼭대기고 그 위로는 더 진해지지 않는다(눈금이 있어야
    '여기가 저기보다 심하다' 를 말할 수 있다).
    ★세 화면이 **같은 숫자**를 써야 한다. 한 화면만 다르면 같은 정체를 보고
      두 사람이 다른 말을 한다.
    """

    @classmethod
    def setUpClass(cls):
        cls.h = _read("dashboard.html")
        cls.j = _read("static", "js", "oht3d", "oht3d.js")

    @staticmethod
    def _ramp(src):
        m = re.search(r"const JAM_RAMP = \[[\s\S]*?\n\];", src)
        if not m:
            return None
        body = re.sub(r"//[^\n]*", "", m.group(0))          # 주석은 달라도 된다
        return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", body)]

    def test_두_파일의_눈금이_같다(self):
        a, b = self._ramp(self.h), self._ramp(self.j)
        self.assertIsNotNone(a, "dashboard.html 에 JAM_RAMP 가 없다")
        self.assertIsNotNone(b, "oht3d.js 에 JAM_RAMP 가 없다")
        self.assertEqual(a, b, "2D 와 아이소메트리의 세기 눈금이 다르다")

    def test_20대에서_꼭대기(self):
        for src, nm in ((self.h, "dashboard.html"), (self.j, "oht3d.js")):
            self.assertIn("const JAM_HOT_N = 20;", src, nm)

    def test_눈금은_옅은_데서_짙은_데로(self):
        r = self._ramp(self.h)
        rows = [r[i:i + 5] for i in range(0, len(r), 5)]
        self.assertGreaterEqual(len(rows), 3, "단이 너무 적다")
        self.assertEqual(rows[0][0], 0.0)
        self.assertEqual(rows[-1][0], 1.0)
        for i in range(1, len(rows)):
            self.assertGreater(rows[i][0], rows[i - 1][0], "비율이 거꾸로다")
            self.assertGreater(rows[i][4], rows[i - 1][4], "뒤로 갈수록 진해야 한다")
            self.assertLess(rows[i][2], rows[i - 1][2], "노랑(초록 성분)이 줄며 붉어져야 한다")

    def test_2D_는_대수로_색을_정한다(self):
        i = self.h.index("function drawJamBlobs(")
        body = self.h[i:i + 2000]
        self.assertIn("jamHeat(c.n)", body, "무리의 대수로 색을 정해야 한다")
        self.assertNotIn("rgba(239,68,68,0.50)", body, "고정 붉은색이 남아 있다")

    def test_아이소메트리도_대수로_색을_정한다(self):
        i = self.j.index("markHot() {")
        body = self.j[i:i + 900]
        self.assertIn("jamHeat(h[2])", body, "무리의 대수로 색을 정해야 한다")
        self.assertIn("this.hotDisc.material.color", body)
        self.assertIn("this.hotDisc.material.opacity", body, "진하기도 같이 가야 한다")

    def test_무늬는_흰색으로_굽는다(self):
        """★색을 무늬에 구워 버리면 무리 하나 바뀔 때마다 캔버스를 다시
        그려야 한다. 흰색으로 굽고 재료에서 색을 입힌다."""
        i = self.j.index("_hotTex() {")
        body = self.j[i:i + 700]
        self.assertIn("rgba(255,255,255,1.00)", body)
        self.assertNotIn("rgba(239,68,68", body, "붉은색이 무늬에 구워져 있다")


class 어느_HID_구역인가(unittest.TestCase):
    """고객: "2D, 유사3D 도 동일하게 설정 하고 있고 어디 HID인지 표시 해주라" ·
    (아이소메트리) "뿌연 빨간색에 어디 HID인지 위에 표시해줘; 구역을"."""

    @classmethod
    def setUpClass(cls):
        cls.h = _read("dashboard.html")
        cls.j = _read("static", "js", "oht3d", "oht3d.js")

    def test_2D_는_레인_좌표로_구역_상자를_만든다(self):
        self.assertIn("function zoneBoxes()", self.h)
        self.assertIn("function zoneAt(x, y)", self.h)
        self.assertIn("_zoneBoxG === railGraph", self.h, "레이아웃마다 한 번만 만들어야 한다")

    def test_2D_무리마다_구역을_붙인다(self):
        self.assertIn("zone: zoneAt(bx, by) });", self.h)
        self.assertIn("c.zone ? z3dId(c.zone) : '구역 밖'", self.h,
                      "모르면 '구역 밖' — 엉뚱한 이름을 적는 게 더 나쁘다")

    def test_겹치면_안쪽_구역(self):
        i = self.h.index("function zoneAt(x, y)")
        self.assertIn("b.area < best.area", self.h[i:i + 400])

    def test_3D_는_이름표를_띄운다(self):
        self.assertIn("drawHotLabel(zi, n, kinds)", self.j)
        self.assertIn("this.drawHotLabel(h[3], h[2], h[4]);", self.j,
                      "구역 · 대수 · 종류별 대수를 다 넘겨야 한다")
        self.assertIn("this.hotAt = best ? [best[0], best[1], bc, bz, bk] : null;", self.j)
        # 한 무리가 두 구역에 걸칠 수 있다 — 제일 많이 든 구역을 쓴다
        self.assertIn("for (const [z, n] of zc) if (n > bn) { bn = n; bz = z; }", self.j)
        self.assertIn("'구역 밖'", self.j)


    def test_몇_군데든_다_그린다(self):
        """★도는 횟수를 임의로 자르면 정체가 많은 날 몇 군데가 말없이 빠진다."""
        i = self.h.index("function jamClusters(")
        body = self.h[i:i + 1600]
        self.assertIn("for (let guard = 0; guard < js.length; guard++)", body)
        self.assertNotIn("guard < 60", body)


class 떼어_돌리기(unittest.TestCase):
    def test_jam2d_js(self):
        node = _node()
        if not node:
            self.skipTest("node 가 없다 (폐쇄망)")
        p = subprocess.run([node, os.path.join(HERE, "jam2d.js")],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, (p.stdout + p.stderr)[-1500:])


if __name__ == "__main__":
    unittest.main()
