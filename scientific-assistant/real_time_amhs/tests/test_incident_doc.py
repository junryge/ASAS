# -*- coding: utf-8 -*-
"""장애분석 문서가 **센 숫자**만 쓰는지.

고객에게 나가는 문서라 여기 적힌 수가 틀리면 그대로 잘못된 판단이 된다.
이 문서를 쓰면서 같은 자리를 세 번 틀렸고, 마지막은 고객이 잡아 줬다.

  · 등급 컷을 코드 기본값(60/71/85)으로 짐작했다
  · 그다음엔 자료의 관측 최소·최대를 컷인 양 적었다 — 그것도 컷이 아니다
  · "화면 = 영역 × 1.43, 상한에 닿으면 ×1.58" 이라고 썼다. **틀렸다.**
    배수가 둘인 게 아니라 **재는 대상이 둘** 이다 —
      발동이벤트 {fab}_score = min(상한, Σ룰)    ← ALL 융합용, 자른 값
      화면 종합점수          = round(Σ룰 ÷ 분모 × 100)  ← 안 자른 값
    fab_score.risk_of() 주석이 "상한은 점수 분모가 아니다" 라고 이미
    경고해 두고 있었는데 읽고도 가정으로 덮었다.
  · 컨베이어 상한이 "줄어 있었다" 고만 쓰고 **얼마나** 를 안 적었다

그래서 이 시험은 '문장이 있나' 가 아니라 **자료·설정을 바꾸면 숫자가 따라
바뀌나** 를 본다. 하드코딩이면 여기서 걸린다.
"""
import csv
import importlib.util
import os
import sys
import tempfile
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
         "continuity_min": "0", "refire_count": "0", "maxcapa_signals": "",
         "M14_score": "5", "M14_score_raw": "5"}
    r.update(kw)
    return r


def _build(rows, scr, cuts=inc.CUTS):
    """작은 자료 두 장을 만들어 build() 에 그대로 넣는다."""
    d = tempfile.mkdtemp()
    fp, sp = os.path.join(d, "f.csv"), os.path.join(d, "s.csv")
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
    return inc.build(fp, "M14", "11:38", "14:30", "t", screen=sp, cuts=cuts)


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

    def test_값과_지속분을_자료에서_센다(self):
        rows = [_row("00:00", maxcapa_signals="M14:3F_CNV_MAXCAPA=112(<=150)"),
                _row("00:01", maxcapa_signals="M14:3F_CNV_MAXCAPA=112(<=150)"),
                _row("00:02", maxcapa_signals="M14:3F_CNV_MAXCAPA=44(<=150)")]
        d = _build(rows, [("00:00", "정상", "7")])
        got = {v: (n, pct) for _sig, v, n, pct in d["capa_rows"]}
        self.assertEqual(got[112][0], 2)
        self.assertEqual(got[44][0], 1)
        # 정상치 244 기준 — 임계 150 기준이면 75%/29% 로 나온다
        self.assertAlmostEqual(got[112][1], 112 / 244.0, places=4)
        self.assertAlmostEqual(got[44][1], 44 / 244.0, places=4)


class 등급_컷(unittest.TestCase):
    def test_컷은_밖에서_받는다(self):
        # 코드에 박으면 시스템 설정이 바뀔 때 문서가 거짓말한다.
        rows = [_row("00:00", M14_score="30", M14_score_raw="30")]
        d = _build(rows, [("00:00", "경계", "43")], cuts=(36, 52, 72))
        self.assertEqual(d["cuts"], (36, 52, 72))
        got = {g: (lo, hi) for g, lo, hi, _m, _x, _n in d["grade_rows"]}
        self.assertEqual(got["정상"], (0, 35))
        self.assertEqual(got["경계"], (36, 51))
        self.assertEqual(got["위험"], (52, 71))
        self.assertEqual(got["초위험"], (72, 100))

        d2 = _build(rows, [("00:00", "경계", "43")], cuts=(60, 71, 85))
        got2 = {g: (lo, hi) for g, lo, hi, _m, _x, _n in d2["grade_rows"]}
        self.assertEqual(got2["경계"], (60, 70), "컷을 바꾸면 표도 따라가야 한다")

    def test_컷이_자료와_어긋나면_센다(self):
        # 문서가 "어긋난 분 0" 이라고 쓰려면 정말 0이어야 한다.
        rows = [_row("00:00"), _row("00:01")]
        scr = [("00:00", "정상", "30"), ("00:01", "경계", "40")]
        self.assertEqual(_build(rows, scr, cuts=(36, 52, 72))["cut_bad"], 0)
        self.assertEqual(_build(rows, scr, cuts=(20, 52, 72))["cut_bad"], 1,
                         "30점이 경계가 되어 화면의 '정상' 과 어긋난다")


class 두_자료의_점수(unittest.TestCase):
    def test_화면은_상한을_쓰지_않는다(self):
        # 여기를 틀렸었다. 상한 50 은 ALL 융합용이지 화면 점수 분모가 아니다.
        rows = [_row("00:00", M14_score="50", M14_score_raw="55")]
        d = _build(rows, [("00:00", "초위험", "79")])
        self.assertEqual(d["scale_bad"], 0,
                         "화면 = round(안 자른 값 ÷ 분모 × 100) 이 맞아야 한다")
        self.assertEqual(len(d["split_rows"]), 1)
        _t, raw, area, shown, if_cap = d["split_rows"][0]
        self.assertEqual((raw, area, shown), (55, 50, 79))
        self.assertEqual(if_cap, 71, "잘랐다면 71 — 초위험 컷 72 바로 아래다")

    def test_상한_아래에서는_두_값이_같다(self):
        rows = [_row("00:00", M14_score="45", M14_score_raw="45")]
        d = _build(rows, [("00:00", "위험", "64")])
        self.assertEqual(d["split_rows"], [], "갈라질 일이 없는 분이다")
        self.assertEqual(d["scale_bad"], 0)

    def test_환산이_어긋나면_센다(self):
        rows = [_row("00:00", M14_score="45", M14_score_raw="45")]
        d = _build(rows, [("00:00", "위험", "63")])       # 64 가 맞다
        self.assertEqual(d["scale_bad"], 1)


class 몇_개가_켜져야(unittest.TestCase):
    """고객 물음 3) 의 뿌리 — 한 지표가 심해도 왜 고점이 안 나오나."""

    def setUp(self):
        self.d = _build([_row("00:00", M14_score="45", M14_score_raw="45")],
                        [("00:00", "위험", "64")])

    def test_한_지표만으로는_경계에도_못_간다(self):
        self.assertIsNotNone(self.d["solo_max"])
        self.assertLess(self.d["solo_max"], self.d["cuts"][0],
                        "가장 큰 배점 하나만 켜져도 경계 컷에 못 미친다 — "
                        "이게 고객이 말한 한계다")

    def test_등급이_높을수록_더_많이_켜져야_한다(self):
        ks = [k for _nm, _c, _v, k in self.d["need_rows"] if k]
        self.assertTrue(ks)
        self.assertEqual(ks, sorted(ks), "뒤집히면 계산이 틀린 것이다")
        self.assertGreaterEqual(ks[-1], 2, "초위험이 룰 하나로 되면 안 된다")

    def test_필요_룰합은_컷을_실제로_넘는_가장_작은_값이다(self):
        den = self.d["denom"]
        for _nm, cut, need, _k in self.d["need_rows"]:
            if need is None:
                continue
            self.assertGreaterEqual(round(need * 100.0 / den), cut)
            self.assertLess(round((need - 1) * 100.0 / den), cut,
                            "한 점 낮추면 컷 아래여야 '가장 작은 값' 이다")

    def test_최대로_켜도_100점은_안_나올_수_있다(self):
        tot = sum(p for _c, _l, p in self.d["rule_pts"])
        self.assertEqual(self.d["screen_max"],
                         min(100, round(tot * 100.0 / self.d["denom"])))


if __name__ == "__main__":
    unittest.main()
