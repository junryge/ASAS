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
        self.assertIn("rgba(239,68,68,0.00)", body, "가장자리는 투명이어야 한다")

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
    def test_아이소메트리는_안_따른다(self):
        """고객: "아이소메트리 그냥 나둬라". 거기 '정체 지점' 은 예전대로
        늘 JAM+OBS(st >= 3) 다 — ⚙ 설정이 거기까지 가지 않는다."""
        self.assertNotIn("jamStates3D", self.h, "3D 로 넘기는 길이 남아 있다")
        j = _read("static", "js", "oht3d", "oht3d.js")
        self.assertIn("sl.st >= 3", j, "뷰어는 제 기준을 그대로 써야 한다")
        self.assertNotIn("jamStates", j, "뷰어에 설정을 심지 않는다")
        # 설정창에도 그렇게 적어야 한다 — 안 적으면 "왜 다르냐" 가 또 나온다
        self.assertIn("아이소메트리는 이 설정을 안 따릅니다", self.h)


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
        self.assertIn("drawHotLabel(zi, n)", self.j)
        self.assertIn("this.drawHotLabel(h[3], h[2]);", self.j)
        self.assertIn("this.hotAt = best ? [best[0], best[1], bc, bz] : null;", self.j)
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
