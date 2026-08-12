"""선행 감지 — 판정 규칙 + 사후 채점.

★핵심 불변식: 실시간 predict() 와 사후 채점 score() 가 **같은 _decide()** 를
  쓴다. 두 곳에 규칙을 따로 쓰면 채점 결과가 화면과 어긋나고, 그러면 그
  채점을 믿고 임계를 조정할 수 없다. 여기서 그걸 지킨다.
"""
import random
import unittest
from datetime import datetime, timedelta

from . import util  # noqa: F401
import forecast as F
import store_csv
from lp_client import load_config

T0 = datetime(2026, 7, 28, 0, 0)


def rows_from(scores, extra=None):
    """분단위 점수 목록 → CSV 행. extra={key: [값…]} 로 지표도 같이."""
    out = []
    for i, v in enumerate(scores):
        r = {"datetime": (T0 + timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M:%S"),
             "unified_risk_score": f"{v:.1f}", "hot_area": "M16HUB"}
        for k, arr in (extra or {}).items():
            r[k] = f"{arr[i]:.2f}"
        out.append(r)
    return out


def ramp(a, b, n, jitter=0.0, rnd=None):
    rnd = rnd or random.Random(0)
    return [a + (b - a) * i / max(1, n - 1) + rnd.uniform(-jitter, jitter)
            for i in range(n)]


def quiet(n, rnd=None, lo=9, hi=17):
    rnd = rnd or random.Random(0)
    return [rnd.uniform(lo, hi) for _ in range(n)]


class Decide(unittest.TestCase):
    """창 하나로 내리는 판정 — 조건을 하나씩 확인."""

    F = {"window_min": 20, "horizon_min": 15, "min_slope": 0.6, "sustain_min": 5,
         "min_points": 8, "quiet_below": 20,
         "multi": {"enabled": False, "min_rising": 2, "rise_pct": 25,
                   "assist_slope": 0.25, "assist_horizon_min": 30,
                   "require_for_warn": False}}

    def pts(self, vals):
        n = len(vals)
        return [(-(n - 1 - i), v) for i, v in enumerate(vals)]

    def test_표본_부족이면_경보_안_함(self):
        d = F._decide(self.pts([30, 32, 34]), 50, self.F)
        self.assertFalse(d["warn"])
        self.assertIn("표본 부족", d["reason"])

    def test_이미_임계_이상이면_예보_아님(self):
        d = F._decide(self.pts([55] * 12), 50, self.F)
        self.assertFalse(d["warn"])
        self.assertIn("이미 임계", d["reason"])

    def test_조용한_구간은_생략(self):
        d = F._decide(self.pts([12] * 12), 50, self.F)
        self.assertFalse(d["warn"])
        self.assertIn("조용한 구간", d["reason"])

    def test_상승세_약하면_경보_안_함(self):
        vals = [30 + i * 0.2 for i in range(12)]      # 분당 +0.2 (기준 0.6 미만)
        d = F._decide(self.pts(vals), 50, self.F)
        self.assertFalse(d["warn"])
        self.assertIn("상승세 약함", d["reason"])

    def test_조건_충족하면_경보(self):
        vals = [30 + i * 1.5 for i in range(12)]
        d = F._decide(self.pts(vals), 50, self.F)
        self.assertTrue(d["warn"], d["reason"])
        self.assertGreater(d["eta_min"], 0)
        self.assertGreater(d["confidence"], 0)

    def test_스파이크_하나에_안_흔들린다(self):
        """Theil-Sen 을 쓰는 이유 — 1분 튐으로 경보가 나가면 아무도 안 믿는다."""
        vals = [30] * 11 + [95]
        d = F._decide(self.pts(vals), 50, self.F)
        self.assertFalse(d["warn"], d["reason"])

    def test_다지표_보조_더_일찍_뜬다(self):
        """기울기가 기준 미달이어도 선행 지표가 같이 오르면 경보.

        분당 +0.4 (기준 0.6 미달) 로 현재 42점 → 도달 예상 20분.
        기본 예보 범위(15분) 밖이지만 보조 범위(30분) 안이다.
        """
        vals = [36.4 + i * 0.4 for i in range(15)]    # 끝값 42점, 기울기 0.4
        f = dict(self.F, multi=dict(self.F["multi"], enabled=True))
        without = F._decide(self.pts(vals), 50, f, {"n": 0, "names": [], "checked": 3})
        withsig = F._decide(self.pts(vals), 50, f,
                            {"n": 2, "names": ["STB저장율", "반송시간"], "checked": 3})
        self.assertFalse(without["warn"], without["reason"])
        self.assertTrue(withsig["warn"], withsig["reason"])
        self.assertTrue(withsig["assisted"])
        self.assertEqual(withsig["lead_n"], 2)

    def test_다지표_필수면_신호_없는_경보_억제(self):
        vals = [30 + i * 1.5 for i in range(12)]      # 기울기는 충분
        f = dict(self.F, multi=dict(self.F["multi"], enabled=True,
                                    require_for_warn=True))
        d = F._decide(self.pts(vals), 50, f, {"n": 0, "names": [], "checked": 3})
        self.assertFalse(d["warn"])
        self.assertIn("선행 지표", d["reason"])


class Score(unittest.TestCase):
    """저장된 하루를 되감아 적중/오보/놓침을 센다."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = load_config()
        cls.cfg["forecast"] = dict(cls.cfg.get("forecast") or {},
                                   multi={"enabled": False})
        rnd = random.Random(7)
        p = quiet(60, rnd)
        p += ramp(22, 70, 25, 1.2, rnd)      # ① 올라서 돌파 → 적중
        p += ramp(70, 12, 30, 1.0, rnd)
        p += quiet(60, rnd)
        p += ramp(22, 46, 18, 0.8, rnd)      # ② 46점에서 꺾임 → 오보
        p += ramp(46, 12, 18, 0.8, rnd)
        p += quiet(40, rnd)
        p += [12, 75, 78, 74, 20]            # ③ 1분 급발진 → 놓침
        p += quiet(30, rnd)
        cls.rows = rows_from(p)
        cls._orig = store_csv.read_day
        store_csv.read_day = lambda d, c=None: cls.rows

    @classmethod
    def tearDownClass(cls):
        store_csv.read_day = cls._orig

    def test_적중_오보_놓침을_각각_센다(self):
        r = F.score("20260728", self.cfg)
        self.assertTrue(r["ok"], r.get("error"))
        self.assertEqual(r["hit"], 1, r["warnings"])
        self.assertEqual(r["false"], 1, r["warnings"])
        self.assertEqual(r["miss"], 1, r["crossings"])

    def test_선행_시간을_잰다(self):
        r = F.score("20260728", self.cfg)
        hit = [w for w in r["warnings"] if w["verdict"] == "적중"][0]
        self.assertIsNotNone(hit["lead_min"])
        self.assertGreater(hit["lead_min"], 0)
        self.assertLessEqual(hit["lead_min"], r["params"]["horizon_min"])

    def test_연속_경보는_한_묶음(self):
        """사건 1건에 경보 10건이 잡히면 적중률이 부풀려진다."""
        r = F.score("20260728", self.cfg)
        self.assertEqual(len(r["warnings"]), 2)      # 적중 1 + 오보 1
        self.assertGreater(r["warnings"][0]["n"], 1)  # 실제로는 여러 분 연속

    def test_예고_없는_돌파는_놓침(self):
        r = F.score("20260728", self.cfg)
        missed = [c for c in r["crossings"] if not c["warned"]]
        self.assertEqual(len(missed), 1)

    def test_임계를_풀면_경보가_늘어난다(self):
        """튜닝이 실제로 판정을 바꾸는지 — 격자 탐색이 의미 있으려면."""
        loose = F.score("20260728", self.cfg, {"min_slope": 0.2, "sustain_min": 3})
        tight = F.score("20260728", self.cfg, {"min_slope": 2.5, "sustain_min": 8})
        self.assertGreaterEqual(len(loose["warnings"]), len(tight["warnings"]))

    def test_데이터_부족이면_실패로_알린다(self):
        store_csv.read_day = lambda d, c=None: self.rows[:3]
        try:
            r = F.score("20260728", self.cfg)
            self.assertFalse(r["ok"])
            self.assertIn("부족", r["error"])
        finally:
            store_csv.read_day = lambda d, c=None: self.rows


class MultiCompare(unittest.TestCase):
    """다지표를 켜면 정말 나아지는가 — A/B 가 숫자로 답해야 한다."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = load_config()
        rnd = random.Random(11)
        p, stb, ra = [], [], []

        def q(n):
            for _ in range(n):
                p.append(rnd.uniform(9, 17))
                stb.append(90 + rnd.uniform(-1, 1))
                ra.append(2.5 + rnd.uniform(-0.2, 0.2))
        q(90)
        for i in range(15):                  # 지표가 먼저 오른다 (점수는 완만)
            p.append(17 + i * 0.35 + rnd.uniform(-1, 1))
            stb.append(90 + i * 0.55)
            ra.append(2.5 + i * 0.12)
        for i in range(20):                  # 점수 본격 상승 → 돌파
            p.append(23 + i * 1.5 + rnd.uniform(-1, 1))
            stb.append(98 + rnd.uniform(-0.3, 0.3))
            ra.append(4.3 + i * 0.06)
        for i in range(30):
            p.append(max(10, 53 - i * 1.6))
            stb.append(97 - i * 0.25)
            ra.append(max(2.5, 5.4 - i * 0.1))
        for i in range(20):                  # 점수만 튀는 헛경보 (지표 조용)
            p.append(22 + i * 1.1)
            stb.append(90 + rnd.uniform(-1, 1))
            ra.append(2.5 + rnd.uniform(-0.2, 0.2))
        for i in range(25):
            p.append(max(10, 44 - i * 1.4))
            stb.append(90 + rnd.uniform(-1, 1))
            ra.append(2.5 + rnd.uniform(-0.2, 0.2))
        q(60)
        cls.rows = rows_from(p, {"M16HUB_stb_util": stb, "M16HUB_ra": ra})
        cls._orig_r, cls._orig_l = store_csv.read_day, store_csv.list_days
        store_csv.read_day = lambda d, c=None: cls.rows
        store_csv.list_days = lambda c=None: [{"day": "20260728"}]
        cls.cfg["forecast"] = dict(cls.cfg.get("forecast") or {}, multi={
            "enabled": True, "metrics": ["M16HUB_stb_util", "M16HUB_ra"],
            "min_rising": 2, "rise_pct": 25, "assist_slope": 0.25,
            "assist_horizon_min": 30, "require_for_warn": False})
        F._SIG_CACHE.clear()
        F._LEAD_PICK.update(at=0, keys=None)

    @classmethod
    def tearDownClass(cls):
        store_csv.read_day, store_csv.list_days = cls._orig_r, cls._orig_l
        F._SIG_CACHE.clear()
        F._LEAD_PICK.update(at=0, keys=None)

    def test_다지표가_더_일찍_띄운다(self):
        r = F.compare(["20260728"], self.cfg)
        self.assertTrue(r["ok"])
        self.assertGreater(r["on"]["median_lead"], r["off"]["median_lead"],
                           f"off={r['off']} on={r['on']}")

    def test_선행신호_필수는_오보를_줄인다(self):
        r = F.compare(["20260728"], self.cfg)
        self.assertLess(r["strict"]["false"], r["on"]["false"],
                        f"on={r['on']} strict={r['strict']}")

    def test_세_방식_다_돌려준다(self):
        r = F.compare(["20260728"], self.cfg)
        for k in ("off", "on", "strict"):
            self.assertIn(k, r)
        self.assertIn(r["best"], ("off", "on", "strict"))


if __name__ == "__main__":
    unittest.main()
