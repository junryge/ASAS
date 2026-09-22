#!/usr/bin/env python3
"""FAB 화면은 그 FAB 것만 — 2026-09-22 고객 요청.

  "실시간 관제, 과거 데이터 조회 ALL 숨기자 … 오프닝 화면에서도 ALL 화면 숨겨
   각 FAB 만 보이면 되"
  "더블 클릭하면 모니터링 보이는 것도 스코어는 보이고 관련된 그래프만"
  "PIO_ERROR 경우 [경로 컬럼] 이거 보여줘, 다른 PIO 보여주지 말고! 관련 FAB 만"
  "발동률도 각 FAB 에 해당하는 것만, 실제지표도 마찬가지 … PIO_ERROR 몇 개가
   생겼는지 이야기 해 주면 돼, 데이터에 나와 있어"
  "area_pio_wsum1 이거 보지 말고 [경로 컬럼] 이걸 봐야 돼"
  "잘 모르겠으면 이거 봐 — 컬럼흐름 상세도(FAB별 HTML)"

★무엇이 틀렸었나 — FAB 분리 파일에도 reason 은 **전체 것**이 실려 온다.
  ① 발동 룰: 그 FAB 블록이 없으면 남의 첫 블록을 빌려 와 이름만 바꿔 붙였다.
  ② 실제지표: 그 FAB 블록이 없으면 reason 전체를 봤고, R-D 를 FAB 과 상관없이
     M16HUB 적재율로 적었다(상세도: M14·M14B·M16A·M16B 의 R-D 는 OHT 가동률).
  ③ 더블클릭 그래프: fab 을 받아 놓고 PIO 에만 써서 남의 반송시간 칸이 섰다.
★기준표는 컬럼흐름 상세도 2026-09-21 판(FAB별 HTML) — 2절 룰↔원본 컬럼,
  4-P-1 경로, 5절 계산식의 임계.
"""
import datetime as _dt
import os
import re
import unittest

from . import util

import fab_score as F                                          # noqa: E402
import graphs as G                                             # noqa: E402
import sentinel as S                                           # noqa: E402

# 여러 FAB 이 한꺼번에 걸린 전체 reason — FAB 분리 파일에도 이대로 실려 온다
R = ("hot_area=M16HUB; S2확정; 발동: "
     "M16HUB[R-A_sus,R-C'(역증가4개:6ABL6021,6ABL6032,6ABL0121,6ABL0122),"
     "R-D(FAB저장=0.8%,STB=99.1%)]; "
     "M14[R-A_sus,R-C,R-D,Sorter(425LOT)]; "
     "M16A[R-B,MAXCAPA1개변경,SLA(9.9%4분초과)]; "
     "M16B[R-D]; "
     "PIO(M14A<-M14B=9건/10분,M16HUB<-M16A=4건/10분,M16A->M16B=3건/10분,합22)")

# 고객이 준 경로 컬럼 (첫 목록 12개 — 뒤 두 목록엔 M14A->M10A 가 빠져 있지만
# 첫 목록과 M14 상세도 4-P-1 에 M14 직접 경로로 있다)
PATHS12 = ["M16HUB->MLUD", "M16HUB->M14B", "M16HUB<-M14B", "M16HUB->M14A",
           "M16HUB<-M14A", "M16HUB->M16A", "M16HUB<-M16A", "M16A->M16B",
           "M16B->M16A", "M14A->M14B", "M14A<-M14B", "M14A->M10A"]

# 상세도 4-P-1 — FAB 이 보는 경로 (원본 컬럼에서 _PIOERROR_DEPOSITED 를 뗀 것)
HTML_PATHS = {
    "M16HUB": {"M16HUB->MLUD", "M16HUB->M14B", "M16HUB->M14A", "M16HUB->M16A",
               "M16HUB<-M16A", "M16HUB<-M14A", "M16HUB<-M14B"},
    "M14": {"M16HUB<-M14A", "M14A->M14B", "M14A->M10A", "M16HUB->M14A", "M14A<-M14B"},
    "M14B": {"M14A<-M14B", "M16HUB<-M14B", "M16HUB->M14B"},
    "M16A": {"M16HUB<-M16A", "M16A->M16B", "M16HUB->M16A", "M16B->M16A"},
    "M16B": {"M16B->M16A", "M16A->M16B"},
}


def _row(fab, **pio):
    """FAB 분리 파일 행 — all_score 가 있고 hot_area 가 그 FAB 코드다."""
    r = {"all_score": "50", "hot_area": fab, "reason": R}
    for p, n in pio.items():
        r[p + "_PIOERROR_DEPOSITED"] = str(n)
    return r


def _pio(**kw):
    """경로 이름에 <- · -> 가 있어 키워드로 못 넘긴다 — 짧은 이름으로 받는다."""
    names = {"a_b": "M16A->M16B", "b_a": "M16B->M16A", "m14ab": "M14A<-M14B",
             "hub_16a": "M16HUB<-M16A", "m10": "M14A->M10A", "hub_mlud": "M16HUB->MLUD",
             "hub_14b": "M16HUB->M14B", "hub_14b_in": "M16HUB<-M14B",
             "hub_14a": "M16HUB->M14A", "hub_14a_in": "M16HUB<-M14A"}
    return {names[k]: v for k, v in kw.items()}


class 경로_배정은_상세도와_같다(unittest.TestCase):
    def test_열두_경로가_고객_목록_그대로(self):
        got = {x["path"] for f in F.fabs() for x in F.pio_paths_of(f)}
        self.assertEqual(got, set(PATHS12))

    def test_FAB별_경로가_상세도_4P1_과_같다(self):
        for f, want in HTML_PATHS.items():
            self.assertEqual({x["path"] for x in F.pio_paths_of(f)}, want, f)


class 발동_룰은_그_FAB_것만(unittest.TestCase):
    def test_M16B_는_남의_룰을_안_빌린다(self):
        """예전: 'M16B 반송지연 지속 · Storage FULL …' — 그건 M16HUB 가 발동한 것."""
        t = S.fab_reason(R, "M16B", _row("M16B"))
        self.assertEqual(t, "M16B OHT 가동률")
        for bad in ("반송지연", "Storage FULL", "리프터", "분류기", "22개"):
            self.assertNotIn(bad, t)

    def test_R_D_는_FAB_마다_이름이_다르다(self):
        """상세도: M16HUB R-D 는 적재율·STB·MLUD·CNV, 나머지는 OHT 가동률 하나."""
        self.assertIn("Storage FULL", S.fab_reason(R, "M16HUB", _row("M16HUB")))
        self.assertIn("OHT 가동률", S.fab_reason(R, "M14", _row("M14")))
        self.assertNotIn("Storage FULL", S.fab_reason(R, "M14", _row("M14")))

    def test_M14_의_R_C_는_컨베이어_편중(self):
        t = S.fab_reason(R, "M14", _row("M14"))
        self.assertIn("컨베이어 편중", t)
        self.assertNotIn("리프터", t)

    def test_실데이터_표기를_놓치지_않는다(self):
        """'MAXCAPA1개변경'(뒤에 글자가 붙음)·'Sorter(…)'(대소문자) 가 빠졌었다."""
        self.assertIn("운영자 용량변경", S.fab_reason(R, "M16A", _row("M16A")))
        self.assertIn("분류기 대기", S.fab_reason(R, "M14", _row("M14")))

    def test_R_A_sus_를_R_A_로_두_번_세지_않는다(self):
        t = S.fab_reason("발동: M14[R-A_sus]", "M14", {})
        self.assertEqual(t, "M14 반송지연 지속")

    def test_그_FAB_것이_없으면_빈칸(self):
        """표가 '정상 운영'/'–' 로 채운다 — 남의 것을 끌어오지 않는다."""
        self.assertEqual(S.fab_reason("발동: M14[R-A_sus]", "M16B", {}), "")
        self.assertEqual(S.fab_reason("", "M16B", {}), "")

    def test_ALL_은_예전_그대로(self):
        self.assertEqual(S.fab_reason(R, "ALL"), S.summarize_reason(R, "ALL"))
        self.assertEqual(S.fab_reason(R, ""), S.summarize_reason(R, ""))


class PIO_ERROR_개수는_경로_컬럼에서(unittest.TestCase):
    """고객: "PIO_ERROR 몇 개가 생겼는지 … 데이터에 나와 있어" ·
    "area_pio_wsum1 이거 보지 말고 [경로 컬럼] 이걸 봐야 돼"."""

    def test_그_분_그_FAB_경로_합(self):
        r = _row("M16A", **_pio(a_b=2, b_a=1, m14ab=5, hub_16a=0))
        self.assertEqual(S.fab_pio(r, "M16A"),
                         {"n": 3, "paths": [("M16A->M16B", 2), ("M16B->M16A", 1)]})

    def test_남의_경로는_안_센다(self):
        """M14A<-M14B 5개는 M16A 것이 아니다."""
        r = _row("M16A", **_pio(m14ab=5))
        self.assertEqual(S.fab_pio(r, "M16A")["n"], 0)
        self.assertEqual(S.fab_reason("발동: M16A[R-B]", "M16A", r), "M16A Queue 누적")

    def test_reason_의_10분_개수는_안_쓴다(self):
        """reason 의 PIO(…=N건/10분) 는 상위 경로만 적혀 와서 그 FAB 경로가 빠질 수
        있다 — 읽는 곳은 경로 컬럼 하나다."""
        self.assertEqual(S.fab_pio(_row("M16B"), "M16B")["n"], 0)
        self.assertNotIn("PIO", S.fab_reason(R, "M16B", _row("M16B")))

    def test_가중합_컬럼은_안_본다(self):
        r = _row("M16B", **_pio(a_b=1))
        r.update({"area_pio_wsum1": "9", "area_pio_wsum10": "30", "area_pio_score": "5"})
        self.assertEqual(S.fab_pio(r, "M16B")["n"], 1)
        raws = [m["raw"] for m in S.fab_metrics(R, "M16B", r)]
        self.assertFalse([x for x in raws if "wsum" in x or "area_pio" in x], raws)

    def test_문구(self):
        r = _row("M16A", **_pio(a_b=2, b_a=1))
        self.assertEqual(S.fab_pio_text(r, "M16A"),
                         "PIO_ERROR 3개/1분 (M16A->M16B 2, M16B->M16A 1)")

    def test_셋이_넘으면_외_N(self):
        r = _row("M16HUB", **_pio(hub_mlud=1, hub_14b=2, hub_14b_in=3, hub_14a=4,
                                  hub_14a_in=5))
        self.assertEqual(S.fab_pio_text(r, "M16HUB"),
                         "PIO_ERROR 15개/1분 (M16HUB<-M14A 5, M16HUB->M14A 4, "
                         "M16HUB<-M14B 3 외 2)")

    def test_M14A_M10A_는_M14_경로다(self):
        r = _row("M14", **_pio(m10=2))
        self.assertIn("M14A->M10A 2", S.fab_reason(R, "M14", r))

    def test_표가_줄을_끊어도_괄호가_안_쪼개진다(self):
        """reasonCell 은 ' · ' 에서 줄을 끊는다 — 괄호 안은 쉼표여야 한다."""
        r = _row("M16A", **_pio(a_b=2, b_a=1))
        for part in re.split(r"\s*·\s*|\r?\n", S.fab_reason(R, "M16A", r)):
            self.assertEqual(part.count("("), part.count(")"), part)


class 실제지표는_그_FAB_원본_컬럼(unittest.TestCase):
    """상세도 2절 — 룰마다 그 FAB 이 실제로 읽는 원본 컬럼."""

    def _raws(self, fab, **pio):
        return [m["raw"] for m in S.fab_metrics(R, fab, _row(fab, **_pio(**pio)))]

    def test_M16B_는_OHT_가동률과_자기_경로만(self):
        self.assertEqual(self._raws("M16B", a_b=2, m14ab=5),
                         ["M16B.QUE.OHT.OHTUTIL", "M16A->M16B_PIOERROR_DEPOSITED"])

    def test_남의_FAB_컬럼이_없다(self):
        for f in F.fabs():
            for raw in self._raws(f, a_b=1, b_a=1, m14ab=1, hub_16a=1, m10=1):
                if raw.endswith("_PIOERROR_DEPOSITED"):
                    p = raw[:-len("_PIOERROR_DEPOSITED")]
                    self.assertIn(p, HTML_PATHS[f], (f, raw))
                else:
                    self.assertTrue(raw.startswith(f + "."), (f, raw))

    def test_전체_합과_가중합을_안_올린다(self):
        for f in F.fabs():
            raws = self._raws(f, a_b=3)
            self.assertNotIn("PIO.DEPOSIT.10MIN.CNT", raws, f)
            self.assertFalse([x for x in raws if x.startswith("PIO.DEPOSIT.")], (f, raws))

    def test_R_D_는_상세도_컬럼(self):
        self.assertIn("M14.QUE.OHT.OHTUTIL", self._raws("M14"))
        self.assertNotIn("M16HUB.STRATE.ALL.FABSTORAGERATIO", self._raws("M14"))
        hub = self._raws("M16HUB")
        self.assertIn("M16HUB.STRATE.ALL.FABSTORAGERATIO", hub)   # 괄호 안 FAB저장
        self.assertIn("M16HUB.STRATE.STB.3F_STORAGE_UTIL", hub)   # 괄호 안 STB

    def test_R_C_는_FAB_마다_다른_컬럼(self):
        m14 = self._raws("M14")
        self.assertIn("M14.QUE.CNV.M14ATONORTHCURRENTQCNT", m14)
        self.assertIn("M14.QUE.CNV.M14ATOSOUTHCURRENTQCNT", m14)
        hub = self._raws("M16HUB")
        # R-C'(역증가4개:…) 에 적힌 리프터만
        for x in ("6ABL6021", "6ABL6032", "6ABL0121", "6ABL0122"):
            self.assertIn(f"M16HUB.LFT.{x}.TOTAL_CURRENTQCNT", hub)
        self.assertNotIn("M16HUB.LFT.6ABL6011.TOTAL_CURRENTQCNT", hub)

    def test_R_B_는_대기_물량_컬럼(self):
        self.assertIn("M16A.QUE.ALL.6F_TO_HUB_JOB", self._raws("M16A"))

    def test_MAXCAPA_는_걸린_컬럼만(self):
        r = _row("M16A")
        r["maxcapa_signals"] = "M16A:2F_LFT_MAXCAPA=36(<=40)"
        raws = [m["raw"] for m in S.fab_metrics(R, "M16A", r)]
        self.assertIn("M16A.QUE.LFT.2F_LFT_MAXCAPA", raws)
        self.assertNotIn("M16A.QUE.LFT.6F_LFT_MAXCAPA", raws)

    def test_SLA_와_SORT_는_두_컬럼(self):
        raws = self._raws("M16A")
        self.assertIn("M16A.QUE.ALL.TRANSPORT4MINOVERRATIO", raws)
        self.assertIn("M16A.QUE.ALL.TRANSPORT4MINOVERCNT", raws)
        m14 = self._raws("M14")
        self.assertIn("M14.SORTER.ABN.SORTERWAITCOUNTOVER", m14)

    def test_실제지표_컬럼은_상세도_원본_컬럼_목록_안에_있다(self):
        """상세도 2절에 없는 이름을 지어내지 않는다 (M16HUB 리프터 묶음 이름 제외)."""
        known = set()
        for f in F.fabs():
            for items in F.WATCH[f].values():
                known |= {it["amos"] for it in items}
        known |= {"M14.QUE.CNV.M14ATONORTHCURRENTQCNT", "M14.QUE.CNV.M14ATOSOUTHCURRENTQCNT"}
        known |= {f"M16HUB.LFT.{x}.TOTAL_CURRENTQCNT" for x in S._HUB_LIFTERS}
        known |= {raw for _k, raw, _l, _u in S._HUB_RD}
        for f in F.fabs():
            for raw in self._raws(f):
                if not raw.endswith("_PIOERROR_DEPOSITED"):
                    self.assertIn(raw, known, (f, raw))

    def test_ALL_은_예전_그대로(self):
        self.assertEqual(S.fab_metrics(R, "ALL"), S.reason_metrics(R, "ALL"))


class 더블클릭_그래프는_그_FAB_것만(unittest.TestCase):
    def _lb(self, fab):
        return [m["label"] for m in G.parse_reason_metrics(R, fab)]

    def test_남의_반송시간_칸이_안_선다(self):
        for f in ("M16B", "M14B", "M16A"):
            lb = self._lb(f)
            self.assertFalse([x for x in lb if "반송시간" in x], (f, lb))
        self.assertIn("M14 반송시간", self._lb("M14"))
        self.assertNotIn("M16HUB 반송시간", self._lb("M14"))

    def test_M16HUB_전용_칸은_M16HUB_화면에서만(self):
        for f in ("M14", "M14B", "M16A", "M16B"):
            lb = self._lb(f)
            self.assertFalse([x for x in lb if x.startswith("M16HUB ")], (f, lb))
        self.assertIn("M16HUB 리프터 정체", self._lb("M16HUB"))

    def test_R_D_와_R_C_는_그_FAB_컬럼으로(self):
        self.assertIn("M16B OHT가동률", self._lb("M16B"))
        self.assertIn("M14 OHT가동률", self._lb("M14"))
        self.assertIn("M14 컨베이어 편중", self._lb("M14"))

    def test_ALL_은_예전_그대로(self):
        lb = self._lb("")
        for want in ("M16HUB 반송시간", "M14 반송시간", "M16A 4분초과율",
                     "M16HUB 리프터 정체", "PIO 반송실패 10분 합"):
            self.assertIn(want, lb)
        self.assertFalse([x for x in lb if "OHT가동률" in x or "Queue 증감" in x], lb)

    def test_그린_그래프에도_남의_반송시간이_없다(self):
        base = _dt.datetime(2026, 9, 22, 9, 0)
        rows = []
        for i in range(40):
            rows.append({"datetime": (base + _dt.timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M:%S"),
                         "unified_risk_score": str(30 + i % 20), "area_score": str(30 + i % 20),
                         "all_score": "55", "hot_area": "M16B", "reason": R,
                         "M16HUB_ra": str(7 + i % 4), "M14_ra": str(3 + i % 2),
                         "M16B_rd_oht": str(80 + i % 5),
                         "M16A->M16B_PIOERROR_DEPOSITED": str(i % 2)})
        svg = G.render(rows, base + _dt.timedelta(minutes=30), minutes=30)
        self.assertNotIn("M16HUB 반송시간", svg)
        self.assertNotIn("M14 반송시간", svg)
        self.assertIn("M16B OHT가동률", svg)


class 임계는_상세도_5절_계산식(unittest.TestCase):
    """컬럼흐름 상세도 2026-09-21 판 5절 계산식의 값. 화면의 '값/임계 · ▲배수'·
    '넘음' 표시가 이걸 쓴다 — 점수는 예측기가 CSV 에 적은 값이라 안 바뀐다."""
    WANT = {
        "M16HUB": {"RA": 9.0, "RA_sus": 6.62, "RB": 100, "RB_fast": 30, "SORT": 30},
        "M14":    {"RA": 3.3, "RA_sus": 2.96, "RB": 80, "RB_fast": 24, "RD": 93.18,
                   "SLA": 25.45, "SORT": 388},
        "M14B":   {"RA": 4.35, "RA_sus": 3.77, "RB": 32, "RB_fast": 10, "RD": 96.6,
                   "SORT": 323},
        "M16A":   {"RA": 2.95, "RA_sus": 2.6, "RB": 84, "RB_fast": 38, "RD": 86.06,
                   "SLA": 10.67, "SORT": 49},
        "M16B":   {"RA": 3.12, "RA_sus": 2.64, "RB": 21, "RB_fast": 15, "RD": 82.19,
                   "SLA": 12.81, "SORT": 27},
    }

    def test_첫_항목_임계(self):
        for f, rules in self.WANT.items():
            for code, v in rules.items():
                self.assertEqual(F.WATCH[f][code][0]["thr"], v, (f, code))

    def test_SLA_건수증가_기준(self):
        """상세도 5절: M16A 26 · M16B 35 (2절 표의 +20 은 옛 글이 남은 것)."""
        want = {"M16HUB": 20, "M14": 20, "M16A": 26, "M16B": 35}
        for f, v in want.items():
            self.assertEqual(F.WATCH[f]["SLA"][1]["thr"], v, f)

    def test_이재_실패는_1건(self):
        for f in ("M16A", "M16B"):
            self.assertEqual(F.WATCH[f]["SORT"][1]["thr"], 1, f)

    def test_그래프_임계도_따라온다(self):
        th = G.thresholds()
        self.assertEqual(th["M16B_ra"][0], 3.12)
        self.assertEqual(th["M16B_rd_oht"][0], 82.19)

    def test_점수는_CSV_값_그대로(self):
        """임계를 바꿔도 area_score 는 {FAB}_pts_* 합이다 — 임계로 다시 재지 않는다."""
        r = {"M16B_pts_RA": "10", "M16B_pts_RD": "7", "M16B_ra": "3.0",
             "M16B_rd_oht": "80"}
        self.assertEqual(F.area_score(r, "M16B")["area"], 17)


class 피드가_FAB_화면에서_쓰는_함수(unittest.TestCase):
    """server.api_feed — flask 가 없는 곳에서도 볼 수 있게 글자로 본다."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(util.BASE, "server.py"), encoding="utf-8") as f:
            src = f.read()
        i = src.index("def api_feed(")
        cls.body = src[i:src.index("\n@app.route", i)]

    def test_FAB_화면이면_fab_함수(self):
        self.assertIn("fab_reason(raw_reason, _fab_sys, r) if _fab_sys", self.body)
        self.assertIn("fab_metrics(raw_reason, _fab_sys, r) if _fab_sys", self.body)

    def test_ALL_은_예전_함수(self):
        self.assertIn("else summarize_reason(raw_reason, area)", self.body)
        self.assertIn("else reason_metrics(raw_reason, area, r)", self.body)
        self.assertIn('_fab_sys = "" if (_fab_sys in ("", "ALL") or fab_reason is None) '
                      'else _fab_sys', self.body)

    def test_sentinel_이_옛것이어도_피드가_안_깨진다(self):
        """배포가 파일 단위다 — server.py 만 먼저 올라가도 예전 함수로 돈다."""
        self.assertIn("from sentinel import fab_metrics, fab_reason", self.body)
        self.assertIn("except ImportError:", self.body)
        self.assertIn("fab_reason = fab_metrics = None", self.body)


if __name__ == "__main__":
    unittest.main()
