# -*- coding: utf-8 -*-
"""컬럼 → 점수 문서 — 예측기 소스에서 직접 읽는다.

왜 생성하나
    "FAB 별로 어느 컬럼을 쓰고, 그게 어떻게 점수가 되나" 를 손으로 적어 두면
    임계 하나 바뀔 때 문서만 옛날 값으로 남는다. 그 문서가 고객에게 나간다.

무엇을 지키나
    ① 예측기를 **import 하지 않는다** — ast 로 읽는다. 문서 하나 만들자고
       로그 폴더를 만들고 업로더를 붙일 이유가 없다
    ② 못 읽은 값은 '읽지 못함' 이라고 적는다 — 지어내지 않는다
    ③ 소스를 못 찾아도 문서는 나온다 (어디를 봐야 하는지 알려 준다)
"""
import io
import os
import re
import unittest

from . import util

DOC = os.path.join(util.BASE, "컬럼흐름_문서.py")


def _mod():
    import importlib.util
    import sys
    if not os.path.isfile(DOC):
        raise unittest.SkipTest("컬럼흐름_문서.py 가 없다")
    sys.path.insert(0, util.BASE)
    spec = importlib.util.spec_from_file_location("컬럼흐름", DOC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SRC = '''
WINDOW_MIN = 90
TH_RA = _TD('TH_RA', {'M16HUB': 9.0, 'M14': 3.3})
TH_FLOW_X3_0 = _T('TH_FLOW_X3_0', 3.0)
TH_FLOW_X2_0 = _T('TH_FLOW_X2_0', 2.0)
TH_FLOW_X1_5 = _T('TH_FLOW_X1_5', 1.5)
RA_COL = {'M16HUB': 'M16HUB.QUE.TIME.AVGTOTALTIME1MIN'}
EVENT_FIELDS = ['datetime', 'unified_risk_score', 'M14_score']

def iter_unified_rows(filepath):
    for row in []:
        d = {}
        g = row.get
        d['M16HUB'] = {
            'ra': safe_float(g('M16HUB.QUE.TIME.AVGTOTALTIME1MIN')),
            'rd_fab': safe_float(g('M16HUB.STRATE.ALL.FABSTORAGERATIO')),
            'lifters': {lid: safe_int(g(f'M16HUB.LFT.{lid}.TOTAL_CURRENTQCNT'))
                        for lid in LIFTER_IDS},
        }
        yield d

def eval_area_rules(area, window):
    ra_pts = 10 if out['ra_trig'] else 0
    rd_pts = 7 if out['rd_trig'] else 0
    mc_pts = 10 * out['maxcapa_changed_n']
    out['area_score'] = min(50, s)

def evaluate_unified(t, area_results, flow_result, propagation_history):
    for node, info in flow_result.items():
        if info['level'] == '심각':
            flow_score += 30
        elif info['level'] == '위험':
            flow_score += 15
        elif info['level'] == '주의':
            flow_score += 5
    sla_score = sum(5 for r in area_results.values() if r.get('sla_trig'))
    sorter_score = sum(3 for r in area_results.values() if r.get('sorter_trig'))
    mc_score += 10 * n
    unified_risk_score = min(500, layer1_total + flow_score)
    if unified_risk_score >= 250:
        unified_risk_level = '매우위험'
    elif unified_risk_score >= 30:
        unified_risk_level = '관심'
    else:
        unified_risk_level = '정상'
    avg_window = list(flow_history)[-30:]
# =
'''


class 소스에서_읽는다(unittest.TestCase):

    def setUp(self):
        self.m = _mod()

    def test_TD_는_두번째_인자가_기본값이다(self):
        """_TD('TH_RA', {…}) — 첫 인자는 열쇠 이름이고 값이 아니다."""
        C = self.m.read_consts(SRC)
        self.assertEqual(C["TH_RA"], {"M16HUB": 9.0, "M14": 3.3})
        self.assertEqual(C["WINDOW_MIN"], 90)
        self.assertEqual(C["RA_COL"]["M16HUB"],
                         "M16HUB.QUE.TIME.AVGTOTALTIME1MIN")

    def test_FAB별로_읽는_컬럼을_뽑는다(self):
        ex = self.m.read_extract_map(SRC)
        self.assertIn("M16HUB", ex)
        keys = {i["key"] for i in ex["M16HUB"]}
        self.assertEqual(keys, {"ra", "rd_fab", "lifters"})
        ra = next(i for i in ex["M16HUB"] if i["key"] == "ra")
        self.assertIn("M16HUB.QUE.TIME.AVGTOTALTIME1MIN", ra["cols"])
        self.assertEqual(ra["kind"], "실수")

    def test_f문자열_컬럼은_패턴으로_적는다(self):
        """리프터는 호기 번호를 붙여 읽는다 — 컬럼 이름이 하나가 아니다."""
        ex = self.m.read_extract_map(SRC)
        lf = next(i for i in ex["M16HUB"] if i["key"] == "lifters")
        self.assertTrue(any("패턴" in c for c in lf["cols"]),
                        "f-string 컬럼을 그냥 적어 버렸다: {}".format(lf["cols"]))

    def test_배점을_읽는다(self):
        p = self.m.read_points(SRC)
        self.assertEqual(p["ra_pts"]["pts"], 10)
        self.assertEqual(p["rd_pts"]["pts"], 7)
        self.assertEqual(p["mc_pts"]["pts"], 10)
        self.assertEqual(p["_cap"], 50)

    def test_융합_규칙을_읽는다(self):
        u = self.m.read_unified(SRC)
        self.assertEqual(u["flow"], {"심각": 30, "위험": 15, "주의": 5})
        self.assertEqual(u["sla"], 5)
        self.assertEqual(u["sorter"], 3)
        self.assertEqual(u["mc"], 10)
        self.assertEqual(u["cap"], 500)
        self.assertIn((250, "매우위험"), u["levels"])
        self.assertIn((0, "정상"), u["levels"])

    def test_흐름_배수를_읽는다(self):
        f = self.m.read_flow_th(SRC)
        self.assertEqual(f["심각"], 3.0)
        self.assertEqual(f["위험"], 2.0)
        self.assertEqual(f["주의"], 1.5)
        self.assertEqual(f["_avg"], 30)


class 예측기를_돌리지_않는다(unittest.TestCase):
    """예측기를 import 하면 로그 폴더를 만들고 thresholds.json 을 찾아 읽고
    업로더를 붙인다. 문서 하나 만들자고 그럴 이유가 없다."""

    def test_import_안_한다(self):
        src = io.open(DOC, encoding="utf-8").read()
        self.assertNotIn("import hubroom_predictor", src)
        self.assertNotIn("exec_module", src)
        self.assertIn("ast.parse", src)


class 문서가_나온다(unittest.TestCase):

    def test_실제_소스로_만들어진다(self):
        m = _mod()
        d = m.build()
        h = m.render(d)
        for t in ("area_score", "unified_risk_score", "M16A_HUBROOM_PR.CSV",
                  "영역분리", "iter_unified_rows"):
            self.assertIn(t, h, "문서에 없다: " + t)
        if d["ok"]:
            # 소스를 찾았으면 숫자가 채워져 있어야 한다
            self.assertNotIn("읽지 못함", h, "값을 못 읽은 자리가 있다")
            self.assertIn("min(50", h)
            self.assertIn("min(500", h)
            self.assertGreaterEqual(len(d["extract"]), 5)

    def test_소스가_없어도_문서는_나온다(self):
        """못 찾았다고 빈손으로 끝나면 안 된다 — 어디를 봐야 하는지 알려준다."""
        m = _mod()
        old = m.RULE_DIRS
        try:
            m.RULE_DIRS = ["없는폴더"]
            os.environ.pop("RULE_SRC", None)
            d = m.build()
            self.assertFalse(d["ok"])
            h = m.render(d)
            self.assertIn("RULE_SRC", h)
        finally:
            m.RULE_DIRS = old

    def test_두_자가_다르다고_밝힌다(self):
        """ALL 0~500 · FAB 0~50 을 같은 자로 비교하면 안 된다."""
        m = _mod()
        h = m.render(m.build())
        self.assertIn("같은 자로 비교하지 마십시오", h)


if __name__ == "__main__":
    unittest.main()
