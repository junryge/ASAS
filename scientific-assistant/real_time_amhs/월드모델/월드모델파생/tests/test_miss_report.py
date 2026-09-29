# -*- coding: utf-8 -*-
"""미보고 · HT_STOP 정체 판정 (2026-09-29, 고객이 현장에서 고쳐 보낸 판).

  · 미보고 — 차가 MISS_SEC(50초) 넘게 상태 보고(MSG_ID=2)가 없으면. 30분(IDLE_SEC) 넘으면
    '운휴'(정비·휴차)라 미보고로 세지 않는다. 상세 · 간소(25초) 둘 다 같은 50초 기준.
  · OHT 판정 — 보고가 살아 있는 차 기준으로 센 미보고 · JAM · HT_STOP 으로
    정상 / 전조 / 경보 / 확정 / 수집누락 (기준값 config.OHT_ALERT)
  · 화면 — 오른쪽 'OHT 상태' 탭 맨 위 한 줄, ⚙ 정체 판정 칸 둘(미보고 · HT_STOP),
    OHT 목록 '미보고' 필터

★pandas 없이 돌아야 한다 — 모듈을 import 하지 않고 판정 함수와 기준값만 떼어 돌린다.
"""
import ast
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)


def _read(*p):
    with open(os.path.join(APP, *p), encoding="utf-8") as fh:
        return fh.read()


def _config_values(*names):
    ns = {}
    for node in ast.parse(_read("config.py")).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) in names for t in node.targets):
            exec(compile(ast.Module(body=[node], type_ignores=[]), "config.py", "exec"), ns)
    return ns


def _alert_fn():
    ns = {"OHT_ALERT": _config_values("OHT_ALERT")["OHT_ALERT"]}
    for node in ast.parse(_read("replay_engine.py")).body:
        if isinstance(node, ast.FunctionDef) and node.name == "oht_alert_level":
            exec(compile(ast.Module(body=[node], type_ignores=[]), "replay_engine.py", "exec"), ns)
    return ns["oht_alert_level"]


class 기준값(unittest.TestCase):
    def test_50초_미보고_30분_운휴(self):
        c = _config_values("MISS_SEC", "IDLE_SEC", "OHT_ALERT")
        self.assertEqual(c["MISS_SEC"], 50)
        self.assertEqual(c["IDLE_SEC"], 1800)
        self.assertEqual(c["OHT_ALERT"]["pre_ht"], 1)

    def test_예전_config_에서도_돈다(self):
        """replay_engine 은 config 에 값이 없어도 같은 기본값으로 돈다 (ImportError 대비)."""
        src = _read("replay_engine.py")
        self.assertIn("from config import MISS_SEC, IDLE_SEC, OHT_ALERT", src)
        self.assertIn("MISS_SEC, IDLE_SEC = 50, 1800", src)


class OHT_판정(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f = staticmethod(_alert_fn())

    def test_단계(self):
        f = self.f
        self.assertEqual(f(0, 0, 0, 500), "정상")
        self.assertEqual(f(4, 30, 0, 500), "경보")            # JAM 30 은 경보(20+)
        self.assertEqual(f(5, 10, 0, 500), "전조")            # 미보고 5 + JAM 10 동시
        self.assertEqual(f(5, 9, 0, 500), "정상")             # 둘 중 하나만이면 아니다
        self.assertEqual(f(0, 0, 1, 500), "전조")             # HT_STOP 1대
        self.assertEqual(f(30, 0, 0, 500), "경보")
        self.assertEqual(f(0, 0, 10, 500), "경보")
        self.assertEqual(f(100, 1, 0, 500), "확정")           # 미보고 100 + JAM 동반
        self.assertEqual(f(100, 0, 0, 500), "경보")           # 동반이 없으면 확정이 아니다
        self.assertEqual(f(0, 40, 0, 500), "확정")
        self.assertEqual(f(0, 0, 30, 500), "확정")

    def test_수집누락(self):
        """거의 다(90%+) 동시에 미보고인데 JAM · HT 가 0 이면 차가 아니라 수집이 멈춘 것."""
        self.assertEqual(self.f(450, 0, 0, 500), "수집누락")
        self.assertEqual(self.f(450, 1, 0, 500), "확정")
        self.assertEqual(self.f(0, 0, 0, 0), "정상")


class 화면_연결(unittest.TestCase):
    def test_서버가_세서_넘긴다(self):
        src = _read("replay_engine.py")
        for k in ("p['missing']", "p['idle']", "p['missSec']", "vehicle_stats['missing']",
                  "vehicle_stats['ht_stop']", "vehicle_stats['ohtAlert']", "'miss': miss_count"):
            self.assertIn(k, src)

    def test_화면에_보이는_자리(self):
        h = _read("dashboard.html")
        for i in ("r-miss", "r-jam", "r-ht", "r-oht-alert", "s-miss", "s-ht", "s-oht-alert"):
            self.assertIn('id="%s"' % i, h)
        self.assertIn("filterOHT('miss',this)", h)
        self.assertIn("ohtFilter === 'miss'", h)
        self.assertIn("미보고 ${v.missSec}초", h)
        self.assertIn("jamMinMiss:     3,", h)
        self.assertIn("jamMinHt:       1,", h)

    def test_3D_뷰어도_같은_기준(self):
        js = _read("static", "js", "oht3d", "oht3d.js")
        self.assertIn("const JAM_NAME = ['JAM', 'OBS', '멈춘 차', '미보고', 'HT_STOP'];", js)
        self.assertIn("this.jamKind(sl.st, sl)", js)
        h = _read("dashboard.html")
        self.assertIn("V3D_BUILD = '20260929a'", h)                     # 브라우저가 새 oht3d.js 를 받게


if __name__ == "__main__":
    unittest.main()
