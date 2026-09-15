# -*- coding: utf-8 -*-
"""장애분석 문서가 **센 숫자**만 쓰는지.

고객에게 나가는 문서라 여기 적힌 수가 틀리면 그대로 잘못된 판단이 된다.
이 문서를 쓰다 세 번 틀렸고, 세 번 다 '자료를 안 세고 가정한 것' 이었다.

  · 등급 컷을 코드 기본값(60/71/85)으로 짐작했다 → 화면은 다르게 매긴다
  · 화면 점수 = 영역 × 1.43 이라고 상수로 봤다 → 상한에 닿은 값만 ×1.58
  · 컨베이어 상한이 "줄어 있었다" 고만 쓰고 **얼마나** 를 안 적었다

그래서 이 시험은 '문장이 있나' 가 아니라 **자료를 바꾸면 숫자가 따라
바뀌나** 를 본다. 하드코딩이면 여기서 걸린다.
"""
import importlib.util
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)

_spec = importlib.util.spec_from_file_location(
    "_inc", os.path.join(_BASE, "장애분석_문서.py"))
inc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inc)


def _row(t, **kw):
    r = {"datetime": "2026-09-13 %s:00" % t, "date": "2026-09-13", "time": t,
         "hot_area": "M14", "stage_name": "1단계 조기경보",
         "predicted_fault_type": "", "incident_state": "IDLE",
         "continuity_min": "0", "refire_count": "0",
         "maxcapa_signals": "", "M14_score": "5", "M14_score_raw": "5"}
    r.update(kw)
    return r


class 조사(unittest.TestCase):
    def test_받침에_맞춰_붙는다(self):
        # "초위험 가 아니라" 가 그대로 나갔었다.
        self.assertEqual(inc.josa("초위험", "이가"), "이")
        self.assertEqual(inc.josa("경계", "이가"), "가")
        self.assertEqual(inc.josa("초위험"), "은")
        self.assertEqual(inc.josa("경계"), "는")

    def test_영문_숫자로_끝나도_안_깨진다(self):
        # 룰 이름에 'Storage FULL' 처럼 한글이 아닌 것이 섞여 있다.
        self.assertEqual(inc.josa("FULL", "이가"), "가")
        self.assertEqual(inc.josa(""), "는")


class 컨베이어_상한(unittest.TestCase):
    """룰 원본에서 정상치를 읽어 오는가 — 문서에 손으로 적으면 어긋난다."""

    def test_정상치는_룰_원본에서_온다(self):
        import fab_score
        spec = (fab_score.WATCH.get("M14") or {}).get("MAXCAPA") or []
        self.assertTrue(spec, "M14 에 MAXCAPA 감시 컬럼이 있어야 한다")
        self.assertIsNotNone(spec[0].get("normal"),
                             "정상치(normal)가 룰 원본에 있어야 문서가 "
                             "'정상 대비 몇 %' 를 셀 수 있다")
        self.assertIsNotNone(spec[0].get("thr"))

    def test_정상_대비_비율은_임계가_아니라_정상치로_잰다(self):
        # 112/150 = 75% 가 아니라 112/244 = 46% 다. 여기를 한 번 틀렸다.
        import fab_score
        sp = fab_score.WATCH["M14"]["MAXCAPA"][0]
        self.assertGreater(sp["normal"], sp["thr"],
                           "정상치가 임계보다 커야 '임계 이하로 내려갔다' 가 "
                           "말이 된다")


class 문서_숫자(unittest.TestCase):
    """자료를 바꾸면 문서 숫자도 바뀌는가."""

    def _build(self, rows, scr):
        import csv
        import tempfile
        d = tempfile.mkdtemp()
        sp = os.path.join(d, "s.csv")
        fp = os.path.join(d, "f.csv")
        with open(fp, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=sorted(rows[0]))
            w.writeheader()
            for r in rows:
                w.writerow(r)
        with open(sp, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["시간", "등급", "종합점수"])
            for t, g, v in scr:
                w.writerow(["2026-09-13 %s" % t, g, v])
        return inc.build(fp, "M14", "11:38", "14:30", "t", screen=sp)

    def test_등급_경계는_자료에서_읽는다(self):
        rows = [_row("%02d:%02d" % (i // 60, i % 60)) for i in range(0, 10)]
        scr = [("00:00", "정상", "9"), ("00:01", "정상", "12"),
               ("00:02", "경계", "41"), ("00:03", "위험", "66")]
        d = self._build(rows, scr)
        got = {g: (mn, mx) for g, mn, mx, _n in d["grade_obs"]}
        self.assertEqual(got["정상"], (9, 12))
        self.assertEqual(got["경계"], (41, 41))
        self.assertEqual(got["위험"], (66, 66))
        self.assertNotIn("초위험", got, "안 뜬 등급을 지어내면 안 된다")

    def test_상한에_닿은_배수를_따로_센다(self):
        # 영역 20 → 화면 29 (×1.45) 와 상한 50 → 79 (×1.58) 를 섞지 않는다.
        rows = [_row("00:00", M14_score="20"), _row("00:01", M14_score="50")]
        scr = [("00:00", "정상", "29"), ("00:01", "초위험", "79")]
        d = self._build(rows, scr)
        self.assertAlmostEqual(d["r_norm"], 29 / 20, places=3)
        self.assertAlmostEqual(d["r_cap"], 79 / 50, places=3)
        self.assertGreater(d["r_cap"], d["r_norm"],
                           "상한에 닿은 쪽이 더 커진다는 것이 이 문서의 지적")

    def test_상한_값이_없으면_평균도_없다(self):
        rows = [_row("00:00", M14_score="20")]
        scr = [("00:00", "정상", "29")]
        d = self._build(rows, scr)
        self.assertIsNone(d["r_cap"], "안 나온 값을 0 으로 채우면 안 된다")

    def test_상한_비율은_자료를_바꾸면_따라_바뀐다(self):
        rows = [_row("00:00", M14_score="50")]
        d = self._build(rows, [("00:00", "초위험", "90")])
        self.assertAlmostEqual(d["r_cap"], 90 / 50, places=3)


if __name__ == "__main__":
    unittest.main()
