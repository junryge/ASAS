# -*- coding: utf-8 -*-
"""차량 표시 — 삼각형 안에 점을 찍는다 (현장 HMI 캡처 그대로).

고객 요청(2026-09):
  · 삼각형은 그대로 두고 **그 안에 점**을 찍는다
  · ● 검은 점 = FOUP 을 들고 이동하는 상태
  · ● 흰 점   = FOUP 을 가지러 가는 상태 (Assigned 되어 Source 포트로)
  · 그 밖에는 점을 안 찍는다
  · 삼각형의 색·모양은 여전히 상태(공차 · 적재 · OBS · 정지 · JAM)가 정한다

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


class 삼각형_안의_점(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = _read("dashboard.html")

    def test_삼각형은_안_건드렸다(self):
        """모양도 색도 예전 그대로다 — 점은 그 **위에** 얹는 표시일 뿐이다."""
        for k in ("shapeEmpty", "shapeLoaded", "shapeObs", "shapeStop", "shapeJam"):
            self.assertRegex(self.h, r"%s:\s*'triangle'" % k, k + " 는 세모")
        self.assertRegex(self.h, r"colorLoaded:\s*'#22d3ee'", "적재 색은 예전 그대로")
        self.assertRegex(self.h, r"colorEmpty:\s*'#22c55e'", "공차 색은 예전 그대로")

    def test_점_기본값(self):
        for k, v in (("carryDot", "'on'"), ("dotLoaded", "'#000000'"),
                     ("dotAssign", "'#ffffff'")):
            self.assertRegex(self.h, r"%s:\s*%s" % (k, re.escape(v)), k)
        self.assertRegex(self.h, r"dotSize:\s*0\.\d+", "점 크기 기본값")

    def test_삼각형을_동그라미로_바꿨던_판이_안_남았다(self):
        """처음에 잘못 읽어 세모를 통째로 동그라미로 바꿨다. 그 찌꺼기가 남으면
        설정창에 죽은 줄이 뜬다."""
        for dead in ("colorAssign", "shapeAssign", "ms-colorAssign", "ms-shapeAssign"):
            self.assertNotIn(dead, self.h, dead + " 가 남아 있다")

    def test_저장_키를_올렸다(self):
        """★기본값만 바꾸면, 한 번이라도 ⚙ 를 저장한 사람은 옛 값이 덮어
        '바꿨다는데 화면은 그대로' 가 된다. 이 프로젝트에서 이미 한 번 겪었다."""
        self.assertIn("const MAP_SETTINGS_KEY = 'oht_world_map_settings_v3';", self.h)

    def test_설정창에_점_묶음이_있다(self):
        for i in ("ms-carryDot", "ms-dotLoaded", "ms-dotAssign", "ms-dotSize"):
            self.assertIn('id="%s"' % i, self.h)
        # 설정창은 DEFAULT_MAP_SETTINGS 의 키 이름으로 입력을 찾는다 — 짝이 맞아야 한다
        i = self.h.index("const DEFAULT_MAP_SETTINGS = {")
        keys = set(re.findall(r"^\s{2}(\w+):", self.h[i:self.h.index("\n};", i)], re.M))
        for k in ("carryDot", "dotLoaded", "dotAssign", "dotSize"):
            self.assertIn(k, keys, k + " 가 DEFAULT_MAP_SETTINGS 에 없다")

    def test_켜고_끄는_값은_글자다(self):
        """설정창 저장 루프가 숫자/글자만 다룬다. 참·거짓으로 두면 저장이 깨진다."""
        self.assertRegex(self.h, r"carryDot:\s*'on'")
        self.assertIn('<option value="on">', self.h)
        self.assertIn('<option value="off">', self.h)

    def test_간소로도_점이_나온다(self):
        """★2026-09-18 — 간소(agg30) 쿼리가 실행 사이클·적재·목적지를 안 가져와서
        간소로 보면 점이 하나도 안 찍혔다 (고객: "간소 옵션 삼각형 그거 안 되네").
        쿼리에 세 컬럼을 더해 상세와 같아졌다."""
        q = _read("logpresso_query.py")
        i = q.index("def _q_agg30(")
        body = q[i:q.index("QUERY_PROFILES", i)]
        for c in ("STOCK_INFO", "VEHICLE_EXECUTE_CYCLE", "DESTINATION"):
            self.assertIn("first(%s) as %s" % (c, c), body, c + " 를 안 가져온다")
        # 묶는 기준·거르는 조건은 그대로 — 행 수가 늘면 간소를 만든 뜻이 없어진다
        self.assertIn("by VEHICLE, _time", body)
        self.assertIn('search MSG_ID == "2"', body)
        self.assertIn('datetrunc(_time, "30s")', body)
        self.assertIn("상세 · 간소 둘 다</b> 나옵니다", self.h, "설정창에도 적어야 한다")

    def test_아이소메트리는_안_건드렸다(self):
        """회의 뒤로 미룬 것. 차량 색은 예전 그대로라 3D 는 건드릴 게 없고,
        점은 2D 에만 찍는다."""
        a = self.h.index("===== 3D 아이소메트리 (시작) =====")
        b = self.h.index("===== 3D 아이소메트리 (끝) =====")
        self.assertNotIn("drawCarryDot", self.h[a:b], "점은 2D 에만")
        self.assertNotIn("V3D_COLORS_BEFORE", self.h, "3D 색을 따로 박아 둘 이유가 없다")

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
