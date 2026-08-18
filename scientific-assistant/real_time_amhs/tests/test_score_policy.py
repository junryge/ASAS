"""정책 탭의 스코어 등급 컷 — /api/score_policy, 시스템 6개 각각.

FAB 마다 점수 분포가 달라 등급 경계가 다를 수 있다 (예: M14 는 55부터
경계, M16HUB 는 65부터). 컷은 grade.by_sys 에 살고, 등급·알람 임계·그래프
밴드가 전부 여기서 나온다.
"""
import copy
import json
import os
import tempfile
import unittest

from . import util  # noqa: F401
import lp_client
import server
from lp_client import sys_cfg
from sentinel import alarm_floor, grade, grade_cuts


class PerSysGrade(unittest.TestCase):
    """sentinel.grade / alarm_floor 가 시스템별 컷을 따라간다."""

    def setUp(self):
        self.g = server.CFG.setdefault("grade", {})
        self._saved = copy.deepcopy(self.g)
        self.g["by_sys"] = {"M14": {"warn": 50, "danger": 65, "critical": 80}}

    def tearDown(self):
        self.g.clear()
        self.g.update(self._saved)

    def test_같은_점수가_시스템마다_다른_등급(self):
        m14 = sys_cfg(server.CFG, "M14")
        self.assertEqual(grade(55, server.CFG)["level"], "정상", "ALL 은 60부터 경계")
        self.assertEqual(grade(55, m14)["level"], "경계", "M14 는 50부터 경계")
        self.assertEqual(grade(70, m14)["level"], "위험")
        self.assertEqual(grade(80, m14)["level"], "초위험")

    def test_알람_임계도_시스템별(self):
        self.assertEqual(alarm_floor(sys_cfg(server.CFG, "M14")), 50)
        self.assertEqual(alarm_floor(server.CFG), 60)

    def test_컷_조회(self):
        self.assertEqual(grade_cuts(sys_cfg(server.CFG, "M14")), (50, 65, 80))
        self.assertEqual(grade_cuts(server.CFG), (60, 71, 85))
        self.assertEqual(grade_cuts(sys_cfg(server.CFG, "M16B")), (60, 71, 85),
                         "오버라이드 없는 시스템은 기본값")

    def test_그래프_밴드도_따라간다(self):
        import graphs
        bands = graphs._bands_of(sys_cfg(server.CFG, "M14"))
        self.assertEqual([b[:2] for b in bands],
                         [(0, 50), (50, 65), (65, 80), (80, 100)])


class ScorePolicyApi(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.g = server.CFG.setdefault("grade", {})
        self._saved = copy.deepcopy(self.g)
        self._cfg_path = lp_client.CONFIG_PATH
        fd, self.tmp_cfg = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"grade": {"normal_max": 59}}, f)
        lp_client.CONFIG_PATH = self.tmp_cfg

    def tearDown(self):
        lp_client.CONFIG_PATH = self._cfg_path
        os.unlink(self.tmp_cfg)
        self.g.clear()
        self.g.update(self._saved)

    def test_조회는_시스템_6개(self):
        d = self.client.get("/api/score_policy").get_json()
        self.assertEqual([s["sys"] for s in d["systems"]],
                         ["ALL", "M14", "M14B", "M16A", "M16B", "M16HUB"])
        for s in d["systems"]:
            self.assertTrue(1 <= s["warn"] < s["danger"] < s["critical"] <= 100)

    def test_저장하면_바로_반영되고_파일에도_남는다(self):
        r = self.client.post("/api/score_policy", json={
            "by_sys": {"M16HUB": {"warn": 65, "danger": 75, "critical": 90}},
            "save": True})
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertTrue(r.get_json()["saved"])
        # ① 즉시 반영 — 등급·알람이 새 컷으로
        hub = sys_cfg(server.CFG, "M16HUB")
        self.assertEqual(grade(63, hub)["level"], "정상")
        self.assertEqual(alarm_floor(hub), 65)
        # ② 파일에도
        with open(self.tmp_cfg, encoding="utf-8") as f:
            disk = json.load(f)
        self.assertEqual(disk["grade"]["by_sys"]["M16HUB"],
                         {"warn": 65, "danger": 75, "critical": 90})

    def test_기본으로_되돌리기(self):
        self.client.post("/api/score_policy", json={
            "by_sys": {"M14": {"warn": 50, "danger": 65, "critical": 80}}})
        self.assertEqual(grade_cuts(sys_cfg(server.CFG, "M14")), (50, 65, 80))
        self.client.post("/api/score_policy", json={"by_sys": {"M14": None}})
        self.assertEqual(grade_cuts(sys_cfg(server.CFG, "M14")), (60, 71, 85))

    def test_순서가_어긋나면_400(self):
        for row in ({"warn": 70, "danger": 65, "critical": 85},   # 경계>위험
                    {"warn": 60, "danger": 71, "critical": 71},   # 위험=초위험
                    {"warn": 0, "danger": 71, "critical": 85},    # 0점
                    {"warn": 60, "danger": 71, "critical": 101},  # 100 초과
                    {"warn": "많이"}):
            r = self.client.post("/api/score_policy",
                                 json={"by_sys": {"M14": row}})
            self.assertEqual(r.status_code, 400, row)

    def test_공유_객체가_유지된다(self):
        """★grade 블록도 sys_cfg 뷰들이 공유한다 — 갈아끼우면 안 된다."""
        before = server.CFG["grade"]
        self.client.post("/api/score_policy", json={
            "by_sys": {"M14": {"warn": 50, "danger": 65, "critical": 80}}})
        self.assertIs(server.CFG["grade"], before)


if __name__ == "__main__":
    unittest.main()
