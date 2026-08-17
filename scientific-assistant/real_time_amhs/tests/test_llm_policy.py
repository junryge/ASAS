"""정책 탭의 'LLM 판단 일치' 설정 — /api/llm_policy, 시스템 6개 각각.

'LLM 판단 일치'(1분 추론+사후검증)가 무겁게 느껴질 때 화면에서 시스템별로
줄일 수 있어야 한다. 저장 버튼 하나가 두 가지를 다 한다:
  ① 메모리 즉시 적용 — pm_cfg / _llm_on 이 매 주기 다시 읽는다
  ② config.json 기록 — 재시작해도 유지
"""
import copy
import json
import os
import tempfile
import unittest

from . import util  # noqa: F401
import lp_client
import server
from accuracy import pm_cfg
from lp_client import sys_cfg


class LlmPolicyApi(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        # ★llm 블록은 시스템 컨텍스트들이 같은 객체를 공유한다 — 통째로
        #   갈아끼우면 참조가 끊어지므로, 내용만 복사해 두고 내용만 되돌린다.
        self.lc = server.CFG.setdefault("llm", {})
        self._saved = copy.deepcopy(self.lc)
        # 저장(save)이 진짜 config.json 을 건드리면 안 된다 — 임시 사본으로
        self._cfg_path = lp_client.CONFIG_PATH
        fd, self.tmp_cfg = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"llm": {"per_minute": {"enabled": True}}}, f)
        lp_client.CONFIG_PATH = self.tmp_cfg

    def tearDown(self):
        lp_client.CONFIG_PATH = self._cfg_path
        os.unlink(self.tmp_cfg)
        self.lc.clear()
        self.lc.update(self._saved)

    def test_조회는_시스템_6개(self):
        d = self.client.get("/api/llm_policy").get_json()
        self.assertEqual([s["sys"] for s in d["systems"]],
                         ["ALL", "M14", "M14B", "M16A", "M16B", "M16HUB"])
        for s in d["systems"]:
            self.assertIn(s["mode"], ("on", "watched", "off"))

    def test_시스템별로_다르게_적용된다(self):
        r = self.client.post("/api/llm_policy", json={"by_sys": {
            "ALL": {"mode": "on", "every_min": 1, "max_per_cycle": 3},
            "M14": {"mode": "off"},
            "M16B": {"mode": "watched", "every_min": 5, "max_per_cycle": 1},
        }})
        self.assertEqual(r.status_code, 200, r.get_json())
        # ① 스케줄 게이트
        self.assertTrue(server._llm_on({"sys": "ALL", "watched": 0.0}, 60))
        self.assertFalse(server._llm_on({"sys": "M14", "watched": 0.0}, 60))
        self.assertFalse(server._llm_on({"sys": "M16B", "watched": 0.0}, 60),
                         "watched — 안 보고 있으면 안 돈다")
        # ② run_minute 이 읽는 pm_cfg — 그 시스템 값이 덮인다
        pm = pm_cfg(sys_cfg(server.CFG, "M16B"))
        self.assertEqual((pm["every_min"], pm["max_per_cycle"]), (5, 1))
        self.assertFalse(pm_cfg(sys_cfg(server.CFG, "M14"))["enabled"],
                         "off 면 그 시스템의 추론 자체가 꺼진다")
        self.assertEqual(pm_cfg(server.CFG)["every_min"], 1, "ALL 은 그대로")

    def test_저장하면_파일에_남고_바로_반영된다(self):
        r = self.client.post("/api/llm_policy", json={
            "by_sys": {"M14B": {"mode": "watched", "every_min": 10,
                                "max_per_cycle": 2}},
            "save": True})
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertTrue(r.get_json()["saved"])
        with open(self.tmp_cfg, encoding="utf-8") as f:
            disk = json.load(f)
        row = disk["llm"]["per_minute"]["by_sys"]["M14B"]
        self.assertEqual(row, {"mode": "watched", "every_min": 10,
                               "max_per_cycle": 2})
        # 파일에만 쓰고 메모리에 반영 안 되는 사고 방지
        self.assertEqual(server._llm_mode("M14B"), "watched")

    def test_잘못된_값은_400(self):
        for body in ({"by_sys": {"M14": {"mode": "sometimes"}}},
                     {"by_sys": {"없는시스템": {"mode": "on"}}},
                     {"by_sys": {"M14": {"every_min": 7}}},
                     {"by_sys": {"M14": {"max_per_cycle": 99}}},
                     {"by_sys": "on"}):
            r = self.client.post("/api/llm_policy", json=body)
            self.assertEqual(r.status_code, 400, body)

    def test_공유_객체가_유지된다(self):
        """★sys_cfg 뷰들이 들고 있는 llm 참조가 끊기면 FAB 만 옛 설정으로
        돈다 — 엔드포인트가 dict 를 갈아끼우지 않고 내용만 고쳐야 한다."""
        before = server.CFG["llm"]
        self.client.post("/api/llm_policy",
                         json={"by_sys": {"M14": {"mode": "on"}}})
        self.assertIs(server.CFG["llm"], before)


if __name__ == "__main__":
    unittest.main()
