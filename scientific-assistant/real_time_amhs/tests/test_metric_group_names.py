# -*- coding: utf-8 -*-
"""실시간 관제 추이 그래프의 지표 묶음 버튼 이름.

고객: "실시관 관제에 AMOS 컬럼 말고 → 스코어컬럼, CSV_컬럼 → CSV스코어데이터 컬럼
으로 변경해주라".

★이름만 바꿨다. id(amos/csv)는 그대로다 — 화면이 id 로 고르고, 다른 시험도 id 를 본다.
★FAB 화면은 lp_client._fab_groups 가, ALL 화면은 config.json 의 ui.metric_groups 가
  이름을 준다. 둘이 어긋나면 화면마다 버튼 이름이 달라진다.
  ※현장 config.json 은 서버가 정책 저장 때 다시 쓰므로 통째로 덮어쓰지 말고 이 두
    이름만 손으로 고친다.
"""
import json
import os
import unittest

import lp_client

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES = ["스코어컬럼", "CSV스코어데이터 컬럼"]


class 지표_묶음_버튼_이름(unittest.TestCase):

    def test_FAB_화면(self):
        for fab in ("M14", "M14B", "M16A", "M16B", "M16HUB"):
            g = lp_client._fab_groups(fab)
            self.assertEqual([x["id"] for x in g], ["amos", "csv"], fab)
            self.assertEqual([x["name"] for x in g], NAMES, fab)

    def test_ALL_화면_config(self):
        with open(os.path.join(APP, "config.json"), encoding="utf-8-sig") as fh:
            cfg = json.load(fh)
        g = cfg["ui"]["metric_groups"]
        self.assertEqual([x["id"] for x in g], ["amos", "csv"])
        self.assertEqual([x["name"] for x in g], NAMES)

    def test_옛_이름은_버튼에_안_남는다(self):
        with open(os.path.join(APP, "config.json"), encoding="utf-8-sig") as fh:
            cfg = json.load(fh)
        names = [x["name"] for x in cfg["ui"]["metric_groups"]]
        names += [x["name"] for x in lp_client._fab_groups("M14")]
        for old in ("AMOS 컬럼", "CSV 컬럼", "CSV_컬럼"):
            self.assertNotIn(old, names)


if __name__ == "__main__":
    unittest.main()
