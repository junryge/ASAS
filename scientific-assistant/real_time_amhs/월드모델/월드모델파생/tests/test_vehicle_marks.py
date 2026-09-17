# -*- coding: utf-8 -*-
"""차량 표시 — 현장 HMI 와 같은 규칙으로 동그라미 둘 · 나머지 세모.

고객 요청(2026-09):
  · ● 검은 동그라미 = FOUP 을 들고 이동하는 상태
  · ● 흰 동그라미   = FOUP 을 가지러 가는 상태 (Assigned 되어 Source 포트로)
  · ▲ 나머지 전부   = 세모

가장 확실한 신호는 UDP/로그프레소의 **VEHICLE_EXECUTE_CYCLE**(차량 실행 사이클)
이다 — 2 = ACQUIRE_MOVING, 4 = DEPOSIT_MOVING. 화면까지 그 값이 오도록
data_loader → world_model → /ws 프레임 → dashboard 로 이어 둔다.

★아이소메트리(3D)는 이번 변경에서 뺐다 (회의 뒤). 3D 색이 2D 를 따라가면
  적재 차가 어두운 바닥에 검게 묻으므로 예전 색으로 고정했다 — tests/iso3d.js.
★점수·재생 엔진·예측은 안 건드린다.
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


class 실행사이클이_화면까지_온다(unittest.TestCase):
    """데이터에는 늘 있던 값이다. 아무도 안 읽어서 화면까지 못 왔을 뿐이다."""

    @classmethod
    def setUpClass(cls):
        cls.dl = _read("data_loader.py")
        cls.wm = _read("world_model.py")
        cls.h = _read("dashboard.html")

    def test_파싱본에서_읽는다(self):
        i = self.dl.index("def parse_oht_data_m14a_row(")
        body = self.dl[i:i + 1400]
        self.assertIn("'vhlCycle': _to_int(row.get('VEHICLE_EXECUTE_CYCLE'))", body)

    def test_원본_UDP_에서도_읽고_있었다(self):
        # fields[11] = VEHICLE_EXECUTE_CYCLE — 예전부터 읽던 자리다. 그대로 둔다.
        self.assertIn("vhl_cycle = int(fields[11])", self.dl)
        self.assertIn("'vhlCycle': vhl_cycle", self.dl)

    def test_빈칸이어도_안_터진다(self):
        """간소(agg30) 조회는 이 컬럼을 안 준다 — 빈칸/없음으로 온다."""
        ns = {}
        i = self.dl.index("def _to_int(")
        exec(self.dl[i:self.dl.index("def parse_oht_data_m14a_row(")], ns)
        f = ns["_to_int"]
        self.assertEqual(f("4"), 4)
        self.assertEqual(f(" 2 "), 2)
        self.assertEqual(f(""), 0)
        self.assertEqual(f(None), 0)
        self.assertEqual(f("NULL"), 0)
        self.assertEqual(f(3.7, 9), 9, "실수 글자도 기본값으로")

    def test_월드모델이_들고_간다(self):
        self.assertIn("vhlCycle: int = 0", self.wm, "PredVehicle 에 자리가 있어야 한다")
        self.assertIn("vhlCycle=vdata.get('vhlCycle', 0),", self.wm)
        self.assertIn("'vhlCycle': v.vhlCycle,", self.wm, "맵으로 나가는 dict 에도 실어야 한다")

    def test_기본값이_있어_옛_코드도_안_터진다(self):
        """파일 하나씩 올리는 현장이다. world_model.py 만 먼저 올라가도 돌아야 한다."""
        self.assertRegex(self.wm, r"vhlCycle: int = 0")
        self.assertIn("vdata.get('vhlCycle', 0)", self.wm)

    def test_화면이_프레임에서_받는다(self):
        self.assertIn("vehicleDisplay[v.vid].vhlCycle = v.vhlCycle;", self.h, "갱신 경로")
        self.assertIn("vhlCycle:v.vhlCycle,", self.h, "새로 생길 때 경로")


class 동그라미_둘_나머지_세모(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = _read("dashboard.html")

    def test_기본값(self):
        for k, v in (("colorLoaded", "'#111111'"), ("colorAssign", "'#ffffff'"),
                     ("shapeLoaded", "'circle'"), ("shapeAssign", "'circle'")):
            self.assertRegex(self.h, r"%s:\s*%s" % (k, re.escape(v)), k)
        for k in ("shapeEmpty", "shapeObs", "shapeStop", "shapeJam"):
            self.assertRegex(self.h, r"%s:\s*'triangle'" % k, k + " 는 세모")

    def test_저장_키를_올렸다(self):
        """★기본값만 바꾸면, 한 번이라도 ⚙ 를 저장한 사람은 옛 값이 덮어
        '바꿨다는데 화면은 그대로' 가 된다. 이 프로젝트에서 이미 한 번 겪었다."""
        self.assertIn("const MAP_SETTINGS_KEY = 'oht_world_map_settings_v2';", self.h)

    def test_설정창에_두_줄이_있다(self):
        self.assertIn('id="ms-colorAssign"', self.h)
        self.assertIn('id="ms-shapeAssign"', self.h)
        self.assertIn('id="ms-colorLoaded"', self.h)
        self.assertIn('id="ms-shapeLoaded"', self.h)
        # 설정창은 DEFAULT_MAP_SETTINGS 의 키 이름으로 입력을 찾는다 — 짝이 맞아야 한다
        i = self.h.index("const DEFAULT_MAP_SETTINGS = {")
        keys = set(re.findall(r"^\s{2}(\w+):", self.h[i:self.h.index("\n};", i)], re.M))
        for k in ("colorAssign", "shapeAssign"):
            self.assertIn(k, keys, k + " 가 DEFAULT_MAP_SETTINGS 에 없다")

    def test_간소로는_동그라미가_안_보인다고_적었다(self):
        """눌러 보고 알면 늦다 — 설정창과 주석 둘 다에."""
        self.assertIn("상세", self.h)
        self.assertIn("동그라미를 보려면", self.h)

    def test_아이소메트리는_안_건드렸다(self):
        """회의 뒤로 미룬 것 — 3D 색은 예전 값으로 고정."""
        self.assertIn("const V3D_COLORS_BEFORE = ['#22c55e', '#22d3ee', '#9ca3af', '#ef4444', '#f59e0b'];", self.h)
        i = self.h.index("function v3dColors()")
        self.assertNotIn("mapSettings", self.h[i:i + 200], "3D 가 2D 설정을 따라가면 적재 차가 검게 묻는다")

    def test_점수_예측은_안_건드린다(self):
        for f in ("replay_engine.py", "predictor.py"):
            p = os.path.join(APP, f)
            if os.path.isfile(p):
                self.assertNotIn("vhlCycle", _read(f), f + " 는 이번 변경과 무관해야 한다")


class 떼어_돌리기(unittest.TestCase):
    """vehCarry() 와 drawMap 판정을 배포되는 그 코드 그대로 (tests/vehicle_marks.js)."""

    def test_vehicle_marks_js(self):
        node = _node()
        if not node:
            self.skipTest("node 가 없다 (폐쇄망)")
        p = subprocess.run([node, os.path.join(HERE, "vehicle_marks.js")],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, (p.stdout + p.stderr)[-1500:])


if __name__ == "__main__":
    unittest.main()
