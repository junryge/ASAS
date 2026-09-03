# -*- coding: utf-8 -*-
"""PIO 반송실패 — 2026-09 에 발동이벤트 CSV 에 늘어난 12경로 컬럼.

무엇이 다른가
    설비 지표(큐 길이·반송시간·가동률)는 **밀리는 중**을 본다 — 아직 실패는
    아니다. PIO 는 **이미 실패한 결과**다. 실측 상관 +0.22 로 거의 안 겹친다.
    그래서 하나가 다른 하나를 대신하지 못한다 — 둘 다 보여 줘야 한다.

여기서 지키는 것
    · reason 의 PIO(…) 를 읽어 한글로 말한다 (영역 블록 밖에 붙어 있다)
    · 실제지표에 PIO 컬럼이 뜬다
    · 1분 값으로 판정하지 않는다 — 10분 합으로만 한다
    · 기준선을 최근 데이터로 다시 계산하지 않는다 (고정)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fab_score                                            # noqa: E402
import sentinel                                             # noqa: E402
from report_graphs import parse_reason_metrics              # noqa: E402

REASON = ("hot_area=M16HUB; S1조기경보; 발동: "
          "M16HUB[R-A'(AVGTOTALTIME1MIN=7.42분/기준9.0),R-A_sus]; "
          "M14[R-A_sus,Sorter(425LOT)]; PIO(M14A<-M14B=4건/10분,합6)")


class reason_에서_읽는다(unittest.TestCase):

    def test_경로와_합을_읽는다(self):
        p = sentinel.pio_of(REASON)
        self.assertEqual(p["paths"], [("M14A<-M14B", 4)])
        self.assertEqual(p["total"], 6)

    def test_없으면_빈_손이다(self):
        """★없는 것과 0 은 다르다. PIO 표기가 아예 없는 행을 '실패 0개' 로
        읽으면, 조회가 안 된 분을 정상으로 말하게 된다."""
        self.assertEqual(sentinel.pio_of("발동: M14[R-A_sus]"), {})

    def test_여러_경로도_읽는다(self):
        p = sentinel.pio_of("PIO(M14A<-M14B=9건/10분,M16HUB<-M16A=3건/10분,합45)")
        self.assertEqual(len(p["paths"]), 2)
        self.assertEqual(p["total"], 45)

    def test_한글_요약에_들어간다(self):
        """★PIO 는 영역 블록 **밖**에 붙는다. 블록만 읽으면 통째로 사라진다."""
        s = sentinel.summarize_reason(REASON, "M16HUB")
        self.assertIn("PIO 반송실패", s)
        self.assertIn("6개", s)   # 표기 단위는 "개" (사용자 요청)

    def test_요약이_룰_코드를_안_흘린다(self):
        s = sentinel.summarize_reason(REASON, "M16HUB")
        for bad in ("R-A", "PIOERROR", "AVGTOTALTIME"):
            self.assertNotIn(bad, s)


class 구간_판정(unittest.TestCase):
    """3일 실측 3,375분 분포. 0~15 가 88.9% 라 16부터가 '평소보다 많다'."""

    def test_구간표(self):
        for n, want in ((0, ""), (15, ""), (16, "조금 많음"), (26, "확실히 많음"),
                        (41, "이상"), (61, "심각"), (81, "최고"), (89, "최고")):
            self.assertEqual(sentinel.pio_band(n), want, n)

    def test_기준선이_고정이다(self):
        """★최근 데이터로 평소치를 다시 계산하면, 설비가 나빠질수록 기준선도
        같이 올라가서 악화를 못 잡는다 (명세가 특히 못 박은 것)."""
        self.assertEqual(fab_score.PIO_10MIN_THR, 16)
        self.assertEqual([t for t, _n in sentinel.PIO_BANDS],
                         [81, 61, 41, 26, 16])


class 실제지표에_뜬다(unittest.TestCase):

    def test_reason_이_컬럼을_짚는다(self):
        cols = [m["col"] for m in parse_reason_metrics(REASON)]
        self.assertIn("pio_10min_cnt", cols)
        self.assertIn("M14A<-M14B_PIOERROR_DEPOSITED", cols)

    def test_영역으로_걸러도_안_사라진다(self):
        """★PIO 는 12경로 지표라 FAB 하나에 속하지 않는다. 영역 필터에서
        같이 잘려서, 어느 영역을 보든 '발동이 지목한 지표' 에서 빠졌다 —
        기여도 추정에서 가중을 못 받아 순위가 밀렸다."""
        for area in ("M16HUB", "M14"):
            cols = [m["col"] for m in sentinel.reason_metrics(REASON, area)]
            self.assertIn("pio_10min_cnt", cols, area)

    def test_감시_컬럼에_들어_있다(self):
        row = {"pio_10min_cnt": "45", "pio_score": "3",
               "M14A<-M14B_PIOERROR_DEPOSITED": "9"}
        rs = [r for r in fab_score.readings(row, "ALL") if r["rule"] == "PIO"]
        self.assertEqual(len(rs), 2 + len(fab_score.PIO_PATHS))
        by = {r["csv"]: r for r in rs}
        self.assertTrue(by["pio_10min_cnt"]["over"])
        self.assertEqual(by["M14A<-M14B_PIOERROR_DEPOSITED"]["value"], 9.0)

    def test_1분_값으로는_판정_안_한다(self):
        """★1분 값은 대부분 0/1 이고 경로마다 평소 수준이 다르다.
        M14A<-M14B 는 10분에 12개(p95)까지가 평소이고 M16HUB->MLUD 는 0 이다.
        한 임계로 묶으면 거짓이 된다 — 값만 보여 주고 판정은 안 한다."""
        row = {"M14A<-M14B_PIOERROR_DEPOSITED": "9"}
        rs = {r["csv"]: r for r in fab_score.readings(row, "ALL")
              if r["rule"] == "PIO"}
        for path, _t, _p in fab_score.PIO_PATHS:
            r = rs[f"{path}_PIOERROR_DEPOSITED"]
            self.assertIsNone(r["thr"], path)
            self.assertTrue(r["record_only"], path)
            self.assertIsNone(r["over"], path)

    def test_평소_수준을_이름표에_적어_둔다(self):
        """★경로마다 평소가 다르다는 것을 사람이 화면에서 바로 봐야 한다."""
        row = {}
        rs = {r["csv"]: r for r in fab_score.readings(row, "ALL")
              if r["rule"] == "PIO"}
        self.assertIn("p95", rs["M14A<-M14B_PIOERROR_DEPOSITED"]["label"])
        self.assertIn("나오면 그 자체로 이상",
                      rs["M14A->M10A_PIOERROR_DEPOSITED"]["label"])

    def test_가산점은_기록만_한다(self):
        """★구간표는 예측기 쪽이 갖고 있다. 우리가 임계를 지어내면 안 된다."""
        rs = {r["csv"]: r for r in fab_score.readings({"pio_score": "3"}, "ALL")
              if r["rule"] == "PIO"}
        self.assertTrue(rs["pio_score"]["record_only"])
        self.assertIsNone(rs["pio_score"]["thr"])


class LLM_이_해석할_수_있다(unittest.TestCase):

    def test_명세가_문서로_있다(self):
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "docs", "PIO_반송실패_연동명세.md")
        self.assertTrue(os.path.isfile(p), "PIO 명세 문서가 없다")
        with open(p, encoding="utf-8") as f:
            body = f.read()
        self.assertTrue(body.startswith("---"), "스킬 머리말이 없다")
        self.assertIn("name: pio-error", body)
        for w in ("+0.22", "10분", "빈칸", "p95"):
            self.assertIn(w, body, w)

    def test_스킬로_심는다(self):
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "avatar_2d", "avatar", "skills.py")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("def seed_pio(", src)
        self.assertIn("PIO_반송실패_연동명세.md", src)

    def test_기여도_후보에_있다(self):
        """★reason 이 PIO 를 지목해도 후보에 없으면 기여도에서 안 보인다."""
        import json
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "config.json")
        with open(p, encoding="utf-8-sig") as f:
            cfg = json.load(f)
        keys = {m.get("key") for g in (cfg["ui"]["metric_groups"])
                for m in g["metrics"] if isinstance(m, dict)}
        self.assertIn("pio_10min_cnt", keys)
        self.assertIn("M14A<-M14B_PIOERROR_DEPOSITED", keys)

    def test_단위는_개로_말한다(self):
        """사용자 표기 요청 — 화면·문장에서는 '건' 이 아니라 '개' 로 쓴다."""
        rs = [r for r in fab_score.readings({"pio_10min_cnt": 6}, "ALL")
              if r["rule"] == "PIO" and r["csv"] != "pio_score"]
        self.assertTrue(rs)
        for r in rs:
            self.assertEqual(r["unit"], "개", r["label"])
            self.assertNotIn("건", r["label"], r["label"])
        for m in parse_reason_metrics(REASON):
            if "PIO" in m["label"]:
                self.assertEqual(m["unit"], "개", m["label"])
        self.assertNotIn("건", sentinel.pio_text(REASON))

    def test_원문은_건으로_와도_읽는다(self):
        """★예측기가 보내는 reason 은 아직 '…=4건' 이다. 표기만 바꾸고
           파서는 건/개 둘 다 받아야 한다 — 안 그러면 PIO 가 통째로 사라진다."""
        for u in ("건", "개"):
            p = sentinel.pio_of(f"PIO(M14A<-M14B=4{u}/10분,합6)")
            self.assertEqual(p.get("total"), 6, u)
            self.assertEqual(p.get("paths"), [("M14A<-M14B", 4)], u)

    def test_LLM_분석_지표에_PIO_가_남는다(self):
        """★config 지표 목록에서 PIO 는 20번째다. _metrics 의 [:8] 에서
           잘리면 LLM 이 PIO 를 한 글자도 못 본다 — 점수가 임계 아래인
           구간은 발동사유 줄조차 안 붙기 때문이다(_chunks 의 floor)."""
        import json
        import analysis
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "config.json")
        with open(p, encoding="utf-8-sig") as f:
            cfg = json.load(f)
        keys = [m["key"] for m in analysis._metrics(cfg)]
        self.assertIn("pio_10min_cnt", keys)
        # 앞머리 8개는 그대로 두고 뒤에 붙였는지 (설비 지표를 밀어내면 안 된다)
        self.assertEqual(len(keys), 9)
        self.assertEqual(keys[-1], "pio_10min_cnt")

    def test_LLM_이_보는_통계에_PIO_줄이_있다(self):
        import datetime as dt
        import json
        import analysis
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "config.json")
        with open(p, encoding="utf-8-sig") as f:
            cfg = json.load(f)
        seq = []
        for i in range(20):
            d = dt.datetime(2026, 9, 4, 7, i)
            seq.append((d, 20.0 + i, {
                "datetime": d.strftime("%Y-%m-%d %H:%M"),
                "unified_risk_score": 20.0 + i, "hot_area": "M16HUB",
                "pio_10min_cnt": 2 + (i % 7), "reason": REASON}))
        txt, _meta = analysis._overview(seq, cfg, "07:00~07:19")
        self.assertIn("pio_10min_cnt", txt)
        self.assertIn("PIO 반송실패 10분 합(개)", txt)


if __name__ == "__main__":
    unittest.main()
