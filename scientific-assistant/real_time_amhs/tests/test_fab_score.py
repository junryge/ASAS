"""FAB 별 위험도 스코어와 FAB 간 비교 — fab_score.py / fab_score_doc.py

여기서 지키려는 것 세 가지
  ① 이 숫자들은 **재현**이지 추정이 아니다. 실물 형식 CSV 한 줄에서
     {FAB}_pts_* 를 더하면 저장된 {FAB}_score 가 나오고, 융합 공식을 거치면
     저장된 unified_risk_score 가 나온다. 안 나오면 조용히 한쪽을 고르지 않고
     mismatch 로 알린다.
  ② 비교는 **절대 눈금**이어야 한다. 과거 이력을 아무리 바꿔도 그 1분의
     점수와 순위는 변하지 않아야 한다. 상대편차(contrib.py 의 robust-z)를
     여기 끌어들이면 늘 나쁜 FAB 이 '정상' 으로 보인다.
  ③ 임계는 지어내지 않는다. 문서에 없으면 None 이고, 화면·문서에 '미정의'
     라고 뜬다. 0 으로 채우면 '항상 켜짐' 이 되어 정반대 거짓말이 된다.
"""
import csv
import json
import os
import subprocess
import sys
import unittest
from copy import deepcopy
from datetime import datetime, timedelta

from . import util  # noqa: F401
import fab_score as F
from lp_client import load_config
from sentinel import grade_cuts

FIX = os.path.join(util.BASE, "fixtures", "발동이벤트_샘플.csv")


def rows():
    with open(FIX, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def header():
    with open(FIX, encoding="utf-8-sig") as f:
        return set(next(csv.reader(f)))


class 배점표(unittest.TestCase):
    """스코어 산출 문서의 STEP 2 표 그대로인가."""

    def test_룰_아홉개(self):
        self.assertEqual(len(F.RULES), 9)
        self.assertEqual(F.RULE_ORDER,
                         ["RA", "RA_sus", "RB", "RB_fast", "RC", "RD",
                          "SLA", "SORT", "MAXCAPA"])

    def test_배점이_문서와_같다(self):
        want = {"RA": 10, "RA_sus": 5, "RB": 10, "RB_fast": 5, "RC": 8,
                "RD": 7, "SLA": 5, "SORT": 3, "MAXCAPA": 10}
        self.assertEqual({r["code"]: r["pts"] for r in F.RULES}, want)

    def test_전부_켜지면_63점이고_50에서_잘린다(self):
        # 문서: "허브에서 9개 룰이 모두 켜진 경우 10+5+10+5+8+7+5+3+10 = 63 → 50"
        self.assertEqual(sum(r["pts"] for r in F.RULES), 63)
        self.assertEqual(F.AREA_CAP, 50)
        self.assertEqual(F.RAW_FULL, 220)

    def test_상한을_넘겨도_50(self):
        row = {f"M16HUB_pts_{c}": str(F.RULE_BY_CODE[c]["pts"])
               for c in F.RULE_ORDER}
        a = F.area_score(row, "M16HUB")
        self.assertEqual(a["raw"], 63)
        self.assertEqual(a["area"], 50)
        self.assertTrue(a["capped"])


class 임계값(unittest.TestCase):
    def test_다섯_FAB_전부_아홉룰_칸이_있다(self):
        for f in F.fabs():
            w = F.watch(f)
            self.assertEqual(set(w), set(F.RULE_ORDER), f)

    def test_RA_sus_는_RA_의_70퍼센트(self):
        """문서가 '임계는 R-A 의 70%' 라고 적어 둔 관계. 어긋나면 둘 중
        하나를 잘못 옮긴 것이다."""
        for f in F.fabs():
            ra = F.watch(f)["RA"][0]["thr"]
            sus = F.watch(f)["RA_sus"][0]["thr"]
            self.assertIsNotNone(ra, f)
            self.assertAlmostEqual(sus, round(ra * 0.7, 2), places=2, msg=f)

    def test_RB_fast_는_RB_의_30퍼센트(self):
        for f in F.fabs():
            rb = F.watch(f)["RB"][0]["thr"]
            fast = F.watch(f)["RB_fast"][0]["thr"]
            # 문서 값이 정수로 반올림돼 있다 (84×0.3=25.2 → 25)
            self.assertLessEqual(abs(fast - rb * 0.3), 0.6, f)

    def test_문서에_없는_임계는_지어내지_않는다(self):
        """M14B 의 SLA 는 컬럼은 있는데 스코어 산출 문서에 임계가 없다.
        0 으로 채우면 '항상 켜짐' 이 되어 정반대다."""
        sla = F.watch("M14B")["SLA"]
        self.assertTrue(sla, "컬럼 자체는 있어야 한다")
        self.assertIsNone(sla[0]["thr"])
        self.assertTrue(sla[0]["csv"], "CSV 컬럼은 실려 온다")

    def test_반송시간은_QUE_TIME_과_QUE_LOAD_로_갈린다(self):
        time_side = {"M16HUB", "M14B"}
        for f in F.fabs():
            amos = F.watch(f)["RA"][0]["amos"]
            if f in time_side:
                self.assertIn("QUE.TIME.AVGTOTALTIME1MIN", amos, f)
            else:
                self.assertIn("QUE.LOAD.AVGLOADTIME1MIN", amos, f)

    def test_가리키는_CSV_컬럼이_실물_스키마에_전부_있다(self):
        """WATCH 가 없는 컬럼을 가리키면 화면의 '실제지표' 칸이 영원히 빈다."""
        hdr = header()
        for f in F.fabs():
            for rule, items in F.watch(f).items():
                for it in items:
                    if it.get("csv"):
                        self.assertIn(it["csv"], hdr, f"{f}.{rule}")

    def test_pts_컬럼이_실물_스키마에_전부_있다(self):
        hdr = header()
        for f in F.fabs():
            for c in F.RULE_ORDER:
                self.assertIn(f"{f}_pts_{c}", hdr)


class 설정으로_임계를_덮는다(unittest.TestCase):
    """thresholds.json 이 바뀌면 파이썬이 아니라 config 를 고쳐야 한다."""

    def test_임계를_넣으면_문서와_계산이_같이_따라간다(self):
        cfg = deepcopy(load_config())
        before = F.max_area("M14B", cfg)
        self.assertIsNone(F.watch("M14B", cfg)["SLA"][0]["thr"])

        cfg.setdefault("fab_score", {}).setdefault("thresholds", {})["M14B"] = {
            "SLA": [12.5]}
        self.assertEqual(F.watch("M14B", cfg)["SLA"][0]["thr"], 12.5)
        after = F.max_area("M14B", cfg)
        # SLA 5점을 받을 수 있게 되므로 천장이 올라간다
        self.assertEqual(after["possible"] - before["possible"], 5)

    def test_원본_WATCH_는_안_망가진다(self):
        """watch() 가 사본을 주지 않으면 한 번 덮은 설정이 프로세스 내내
        남아 다른 시스템 화면까지 오염된다."""
        cfg = deepcopy(load_config())
        cfg.setdefault("fab_score", {})["thresholds"] = {"M16HUB": {"RA": [999]}}
        F.watch("M16HUB", cfg)
        self.assertEqual(F.WATCH["M16HUB"]["RA"][0]["thr"], 9.0)
        self.assertEqual(F.watch("M16HUB", {})["RA"][0]["thr"], 9.0)


class 재현(unittest.TestCase):
    """실물 형식 CSV 로 — 추정이 아니라 재현인지."""

    def test_pts_합이_저장된_영역점수와_같다(self):
        checked = 0
        for r in rows():
            for f in F.fabs():
                a = F.area_score(r, f)
                if a["stored"] is None or a["stored"] > F.AREA_CAP:
                    continue          # 상한 넘긴 행은 아래 별도 테스트에서 다룬다
                self.assertEqual(a["area"], a["stored"], f"{r.get('datetime')} {f}")
                self.assertEqual(a["mismatch"], "")
                checked += 1
        self.assertGreaterEqual(checked, 15, "실제로 확인한 칸이 너무 적다")

    # ★고정 자료(fixture)는 **2026-08 이전** 예측기가 낸 것이다. 그때는
    #   M16B 가중이 0.5 였다 (지금은 1.0 으로 복원). 융합 공식이 맞는지는
    #   그 자료를 만든 가중치로 확인해야 한다 — 지금 가중치로 재면
    #   "공식이 틀렸다" 가 아니라 "가중치가 바뀌었다" 를 보는 셈이다.
    OLD_CFG = None

    @classmethod
    def _old_cfg(cls):
        if cls.OLD_CFG is None:
            c = deepcopy(load_config())
            c.setdefault("fab_score", {})["area_weight"] = {"M16B": 0.5}
            cls.OLD_CFG = c
        return cls.OLD_CFG

    def test_융합_공식이_전체_점수를_재현한다(self):
        cfg = self._old_cfg()
        ok = [r for r in rows() if F.fuse_check(r, cfg)["match"]]
        self.assertGreaterEqual(len(ok), 3,
                                "실물 형식 행에서 전체 점수가 재현돼야 한다")
        for r in ok:
            fc = F.fuse_check(r, cfg)
            self.assertEqual(fc["calc"], int(fc["stored"]))

    def test_signals_텍스트와_켜진_룰이_맞는다(self):
        """{FAB}_signals 는 예측기가 적어 준 룰 이름이다. 우리가 pts>0 으로
        고른 목록과 어긋나면 배점 컬럼을 잘못 읽고 있는 것이다."""
        seen = 0
        for r in rows():
            for f in F.fabs():
                a = F.area_score(r, f)
                sig = a["signals"]
                if not sig:
                    self.assertEqual(a["fired"], [], f"{f} signals 없는데 룰이 켜짐")
                    continue
                names = {p.split("*")[0] for p in sig.split("+")}
                self.assertEqual(set(a["fired"]), names, f"{r.get('datetime')} {f}")
                seen += 1
        self.assertGreater(seen, 10)

    def test_어긋나면_조용히_넘기지_않는다(self):
        """저장값과 다르면 한쪽을 골라 맞는 척하지 말고 알려야 한다."""
        row = {f"M16HUB_pts_{c}": "0" for c in F.RULE_ORDER}
        row["M16HUB_pts_RA"] = "10"
        row["M16HUB_score"] = "99"
        a = F.area_score(row, "M16HUB")
        self.assertEqual(a["area"], 10)
        self.assertIn("99", a["mismatch"])
        self.assertIn("M16HUB_score", a["mismatch"])

    def test_pts_컬럼이_없는_옛_파일은_저장된_점수를_쓴다(self):
        """90컬럼 시절 파일에는 pts 가 없다. 0 으로 처리하면 그 날 화면이
        통째로 0점이 된다."""
        a = F.area_score({"M16HUB_score": "25", "M16HUB_score_raw": "25"}, "M16HUB")
        self.assertFalse(a["has_pts"])
        self.assertEqual(a["area"], 25)
        self.assertEqual(a["mismatch"], "")


class 비교는_절대_눈금(unittest.TestCase):
    """이 시스템의 핵심 성질 — 과거를 바꿔도 그 1분의 점수는 안 변한다."""

    def _row(self, at, **pts):
        r = {"datetime": at.strftime("%Y-%m-%d %H:%M"), "unified_risk_score": "40"}
        for f in F.fabs():
            for c in F.RULE_ORDER:
                r[f"{f}_pts_{c}"] = "0"
        for key, v in pts.items():
            f, c = key.split("__")
            r[f"{f}_pts_{c}"] = str(v)
        return r

    def test_이력을_바꿔도_점수와_순위가_그대로다(self):
        """M14 를 '하루 종일 나빴던 FAB' 으로 만들어도, 그 1분의 점수는
        똑같아야 한다. 기준선을 쓰면 여기서 순위가 뒤집힌다."""
        t0 = datetime(2026, 8, 20, 10, 0)
        now = self._row(t0 + timedelta(minutes=60),
                        M14__RA=10, M14__RA_sus=5, M16A__RA=10)
        calm = [self._row(t0 + timedelta(minutes=i)) for i in range(60)]
        busy = [self._row(t0 + timedelta(minutes=i), M14__RA=10, M14__RB=10,
                          M14__RD=7) for i in range(60)]

        a = F.compare(calm + [now], t0 + timedelta(minutes=60))
        b = F.compare(busy + [now], t0 + timedelta(minutes=60))
        self.assertTrue(a["ok"] and b["ok"])
        pick = lambda d: {x["fab"]: (x["area"], x["rank"]) for x in d["fabs"]}
        self.assertEqual(pick(a), pick(b),
                         "과거 이력이 그 1분의 점수·순위를 바꿨다 — 상대 눈금이 섞였다")

    def test_같은_배점이면_FAB_이_달라도_같은_점수(self):
        t = datetime(2026, 8, 20, 10, 0)
        r = self._row(t, M14__RA=10, M16B__RA=10)
        self.assertEqual(F.area_score(r, "M14")["area"],
                         F.area_score(r, "M16B")["area"])

    def test_영역점수는_그_행_하나로_정해진다(self):
        """area_score 는 이력을 받지 않는다 — 서명 자체로 못 쓰게 막는다."""
        import inspect
        params = list(inspect.signature(F.area_score).parameters)
        self.assertEqual(params, ["row", "fab", "cfg"])

    def test_변화량은_그때_행이_없으면_None_이지_0_이_아니다(self):
        t = datetime(2026, 8, 20, 10, 0)
        d = F.compare([self._row(t, M14__RA=10)], t)
        self.assertIsNone(d["fabs"][0]["delta"],
                          "30분 전 데이터가 없는데 '변화 없음(0)' 이라고 하면 안 된다")


class 눈금과_등급(unittest.TestCase):
    def test_위험도는_영역점수를_두배로_편_것(self):
        self.assertEqual(F.risk(0), 0)
        self.assertEqual(F.risk(25), 50)
        self.assertEqual(F.risk(50), 100)
        self.assertEqual(F.risk(30), 60)      # 경계 컷과 맞물리는 지점

    def test_상한_밖의_값도_0에서_100_사이(self):
        self.assertEqual(F.risk(-5), 0)
        self.assertEqual(F.risk(80), 100)

    def test_등급_컷은_config_에서_읽는다(self):
        """2026-08 에 경계가 50 → 60 으로 올라갔다. 코드에 박아 두면
        다음에 또 바뀔 때 화면과 문서가 갈라진다."""
        cfg = deepcopy(load_config())
        self.assertEqual(grade_cuts(cfg)[0], 60)
        cfg["grade"] = deepcopy(cfg["grade"])
        cfg["grade"]["bands"] = deepcopy(cfg["grade"]["bands"])
        cfg["grade"]["bands"][0] = dict(cfg["grade"]["bands"][0], min=70)
        self.assertEqual(grade_cuts(cfg)[0], 70)

    def test_천장이_낮은_FAB_은_등급도_못_올라간다(self):
        cfg = load_config()
        crit = grade_cuts(cfg)[2]
        m = F.max_area("M14B", cfg)
        self.assertLess(m["risk_max"], crit,
                        "M14B 는 R-C·MAXCAPA 가 없고 SLA 임계도 없어 초위험에 못 간다")
        self.assertEqual(F.max_area("M14", cfg)["risk_max"], 100)


class 단독_상한(unittest.TestCase):
    """이 문서를 만든 이유 — 한 FAB 만으로는 전체 경보가 안 난다."""

    def test_통상_조건에서는_다섯_FAB_전부_경계에_못_간다(self):
        cfg = load_config()
        warn = grade_cuts(cfg)[0]
        for f in F.fabs(cfg):
            s = F.solo_ceiling(f, cfg, "typical")["score"]
            self.assertLess(s, warn, f"{f} 단독 상한 {s} 가 경계 {warn} 를 넘었다")

    def test_예측기_검증표의_44점과_맞는다(self):
        """스코어 산출 문서가 예측기를 직접 호출해 낸 '허브 한 곳 + 흐름
        심각 = 44점'. 우리 계산은 영역합을 상한 50 으로 잡아 45점이 나온다.
        2점 이상 벌어지면 융합 공식을 잘못 읽은 것이다."""
        s = F.solo_ceiling("M16HUB", load_config(), "typical")["score"]
        self.assertLessEqual(abs(s - 44), 2, f"허브 단독 상한이 {s} — 문서는 44")

    def test_M16B_는_흐름노드가_하나라_최대로도_못_간다(self):
        """★2026-08 — M16B 가중 0.5 는 취소됐다(전 영역 1.0). 그런데도
        흐름 노드가 1개뿐이라 단독으로는 40점, 경계 60 에 못 닿는다.
        (FAB 비교 문서: "가중치는 1.0 으로 복원됐지만 그래도 60 에는
        닿지 못합니다")"""
        cfg = load_config()
        warn = grade_cuts(cfg)[0]
        t = F.solo_ceiling("M16B", cfg, "typical")
        m = F.solo_ceiling("M16B", cfg, "max")
        self.assertEqual(t["weight"], 1.0, "M16B 가중이 아직 0.5 다")
        self.assertEqual(t["flow_nodes"], 1)
        self.assertEqual(t["score"], m["score"], "흐름 노드 1개·MAXCAPA 0 이라 같다")
        self.assertLess(m["score"], warn)

    def test_최대_시나리오가_통상보다_낮을_수는_없다(self):
        cfg = load_config()
        for f in F.fabs(cfg):
            self.assertGreaterEqual(F.solo_ceiling(f, cfg, "max")["score"],
                                    F.solo_ceiling(f, cfg, "typical")["score"], f)

    def test_가정을_숨기지_않는다(self):
        c = F.solo_ceiling("M16HUB", load_config(), "typical")
        self.assertTrue(c["assume"])
        self.assertIn("parts", c)
        self.assertAlmostEqual(sum(c["parts"].values()), c["raw"], places=1)


class 비교_결과(unittest.TestCase):
    def test_실물_한_줄로_다섯_FAB_이_순위대로_나온다(self):
        rs = rows()
        d = F.compare(rs, None)
        self.assertTrue(d["ok"], d.get("error"))
        self.assertEqual(len(d["fabs"]), 5)
        areas = [x["area"] for x in d["fabs"]]
        self.assertEqual(areas, sorted(areas, reverse=True), "순위대로 정렬돼야 한다")
        self.assertEqual([x["rank"] for x in d["fabs"]], [1, 2, 3, 4, 5])

    def test_전체_점수와_컷을_같이_돌려준다(self):
        d = F.compare(rows(), None)
        self.assertIn("unified", d)
        self.assertEqual(d["cuts"]["warn"], grade_cuts(load_config())[0])

    def test_점수만_있는_영역_셋도_같이_나온다(self):
        d = F.compare(rows(), None)
        names = {x["area_name"] for x in d["extra_areas"]}
        # ★M16_PKT 제외 (2026-08) — 예측기에서 영역 자체가 빠졌다
        self.assertEqual(names, {"M16", "M16_WT"})

    def test_그_FAB_이_보는_값이_읽혀_나온다(self):
        d = F.compare(rows(), None)
        hub = next(x for x in d["fabs"] if x["fab"] == "M16HUB")
        by = {r["csv"]: r for r in hub["readings"] if r["csv"]}
        self.assertIn("M16HUB_ra", by)
        self.assertIsNotNone(by["M16HUB_ra"]["value"])
        # CSV 에 값이 없는 컬럼도 빠지지 않고 목록에 남아야 한다
        self.assertTrue(any(not r["has_value"] for r in hub["readings"]))

    def test_데이터가_없으면_지어내지_않는다(self):
        self.assertFalse(F.compare([], None)["ok"])
        far = datetime(2001, 1, 1, 0, 0)
        self.assertFalse(F.compare(rows(), far)["ok"])

    def test_MAXCAPA_는_signals_텍스트에서_읽는다(self):
        """MAXCAPA 는 값 컬럼이 CSV 에 없다 — maxcapa_signals 가 유일한 근거다."""
        r = dict(rows()[0])
        self.assertEqual(F._maxcapa_hits(r, "M16A"), ["2F_LFT_MAXCAPA=36(<=40)"])
        self.assertEqual(F._maxcapa_hits(r, "M14"), [])


class ALL_도_비교_대상(unittest.TestCase):
    """★ALL 을 빼먹었던 버그를 여기서 못 돌아오게 막는다.

    관제 화면은 ALL + FAB 다섯을 고르게 되어 있다. 비교표에 ALL 이 없으면
    "내가 보는 시스템이 표에 없다" 가 된다.
    """

    def test_화면의_시스템_목록과_비교표가_같다(self):
        """dashboard.html 의 SYSTEMS 코드 목록을 그대로 읽어 맞춘다.
        화면에만 시스템을 추가하고 비교표를 안 고치면 여기서 걸린다."""
        import re
        path = os.path.join(util.BASE, "static", "dashboard.html")
        with open(path, encoding="utf-8") as f:
            body = f.read()
        block = re.search(r"const SYSTEMS\s*=\s*\[(.*?)\];", body, re.S)
        self.assertTrue(block, "dashboard.html 에서 SYSTEMS 를 못 찾았다")
        screen = re.findall(r"code:'([^']+)'", block.group(1))
        self.assertIn("ALL", screen)

        d = F.compare(rows(), None)
        # 순서는 다르다 — FAB 은 점수 순으로 세운다(그게 비교의 목적). 다만
        # **빠지거나 더 있으면** 안 된다.
        self.assertEqual(set(x["fab"] for x in d["rows"]), set(screen),
                         "화면 시스템 목록과 비교표 줄이 어긋난다")
        self.assertEqual(len(d["rows"]), len(screen), "중복 줄이 있다")
        self.assertEqual(d["rows"][0]["fab"], "ALL", "ALL 이 첫 줄이어야 한다")

    def test_첫_줄이_ALL_이다(self):
        d = F.compare(rows(), None)
        self.assertTrue(d["rows"][0]["is_all"])
        self.assertEqual(d["rows"][0]["fab"], "ALL")
        self.assertEqual(d["rows"][0]["rank"], 0)
        self.assertFalse(any(x["is_all"] for x in d["rows"][1:]))

    def test_ALL_점수는_전체_점수_그대로다(self):
        for r in rows():
            a = F.all_row(r)
            self.assertEqual(a["score"], float(r["unified_risk_score"]))

    def test_ALL_에는_영역점수도_단독상한도_없다(self):
        """ALL 은 영역이 아니다 — 영역점수도, '단독으로 몇 점' 도 없다.
        ★있는 척해서도 안 되지만, **보는 컬럼이 없다고 해서도 안 된다.**"""
        a = F.all_row(rows()[0])
        self.assertNotIn("solo", a)
        self.assertNotIn("area", a)
        self.assertNotIn("pts", a)

    def test_ALL_도_보는_컬럼이_있다(self):
        """융합 단계에서 보는 것이 따로 있다 — 흐름 노드 10개와 집계 컬럼들.
        '영역 룰이 없다' 와 '보는 컬럼이 없다' 는 전혀 다른 말이다."""
        w = F.watch("ALL")
        self.assertTrue(w, "ALL 의 감시 컬럼이 비어 있다")
        self.assertEqual(len(w["FLOW"]), 10, "흐름 노드는 10개다")
        for key in ("sla_score_total", "sorter_score_total", "mc_score_total",
                    "flow_score", "unified_risk_score"):
            self.assertTrue(
                any(it.get("csv") == key for items in w.values() for it in items),
                f"{key} 가 ALL 감시 목록에 없다")
        rd = F.all_row(rows()[0])["readings"]
        self.assertGreaterEqual(len(rd), 18)
        self.assertTrue(any(r["has_value"] for r in rd))

    def test_흐름_노드는_임계가_아니라_배수로_판정한다(self):
        """30분 평균 대비 배수라서 영역별 기준값이 없다. 임계를 지어내면
        안 된다."""
        for it in F.watch("ALL")["FLOW"]:
            self.assertIsNone(it["thr"])
            self.assertEqual(it["op"], "ratio30")

    def test_흐름_노드_수가_한_곳에서만_정해진다(self):
        """FLOW_NODES 를 손으로 또 적으면 FLOW_COLS 와 갈라진다."""
        for area, n in F.FLOW_NODES.items():
            self.assertEqual(
                n, sum(1 for a, _x, _y in F.FLOW_COLS if a == area), area)
        self.assertEqual(sum(F.FLOW_NODES.values()), len(F.FLOW_COLS))

    def test_ALL_만_가진_것이_들어있다(self):
        a = F.all_row(rows()[0])
        self.assertIn("fuse", a)
        self.assertIn("per_rule", a)
        self.assertEqual(set(a["per_rule"]), set(F.RULE_ORDER))
        self.assertTrue(a["hot_area"])

    def test_룰별_걸린_영역_수가_pts_와_맞는다(self):
        r = rows()[0]
        a = F.all_row(r)
        for c in F.RULE_ORDER:
            want = sum(1 for f in F.fabs()
                       if (F._num(r.get(f"{f}_pts_{c}")) or 0) > 0)
            self.assertEqual(a["per_rule"][c], want, c)

    def test_여섯_줄_모두_무엇을_잰_값인지_적혀_있다(self):
        """같은 0~100 인데 뜻이 다르다. 안 적으면 ALL 60 과 FAB 60 을
        같은 뜻으로 읽는다."""
        d = F.compare(rows(), None)
        for x in d["rows"]:
            self.assertTrue(x.get("measures"), x["fab"])
            self.assertIn("score", x)
            self.assertTrue(0 <= x["score"] <= 100)

    def test_ALL_변화량도_데이터_없으면_None(self):
        t = datetime(2026, 8, 20, 10, 0)
        r = {"datetime": t.strftime("%Y-%m-%d %H:%M"), "unified_risk_score": "40"}
        d = F.compare([r], t)
        self.assertIsNone(d["rows"][0]["delta"])

    def test_옛_이름도_그대로_남는다(self):
        """unified 키를 쓰는 화면이 이미 있다 — 이름을 바꾸면 조용히 깨진다."""
        d = F.compare(rows(), None)
        self.assertEqual(d["unified"]["score"], d["all"]["score"])
        self.assertEqual(d["unified"]["hot_area"], d["all"]["hot_area"])
        self.assertEqual(len(d["fabs"]), 5)


class 점수_컬럼_이름(unittest.TestCase):
    """★이 시스템은 이미 area_score 라는 이름을 쓰고 있다. 새 이름을 지어내지
    않고 쓰던 이름을 따라간다."""

    def test_통합_파일은_FAB_score_를_쓴다(self):
        v, col = F._stored_area({"M14_score": "15"}, "M14")
        self.assertEqual((v, col), (15.0, "M14_score"))

    def test_FAB_분리_파일은_area_score_를_쓴다(self):
        """fab분리 CSV 에는 {FAB}_score 가 없고 area_score 가 그 자리다."""
        v, col = F._stored_area({"area_score": "22"}, "M14")
        self.assertEqual((v, col), (22.0, "area_score"))

    def test_정규화된_행은_unified_risk_score_가_그_FAB_점수다(self):
        """jupyter_csv._fab_rows 가 area_score 를 거기로 옮긴다.
        (lp_client._fab_strip 도 이 키를 raw='area_score' 로 그린다)"""
        row = {"unified_risk_score": "30", "all_score": "72", "hot_area": "M14"}
        v, col = F._stored_area(row, "M14")
        self.assertEqual(v, 30.0)
        self.assertIn("area_score", col)

    def test_정규화된_행에서_남의_FAB_점수를_집지_않는다(self):
        """hot_area 가 M14 인 행에 M16B 를 물으면 30 을 주면 안 된다."""
        row = {"unified_risk_score": "30", "all_score": "72", "hot_area": "M14"}
        self.assertEqual(F._stored_area(row, "M16B"), (None, ""))

    def test_ALL_은_정규화된_행에서_all_score_를_본다(self):
        """정규화된 행의 unified_risk_score 는 그 FAB 점수다. 그대로 읽으면
        한 FAB 점수를 전체 점수라고 화면에 띄우게 된다."""
        row = {"unified_risk_score": "30", "all_score": "72", "hot_area": "M14"}
        a = F.all_row(row)
        self.assertEqual(a["score"], 72.0)
        self.assertTrue(a["from_fab_file"])
        self.assertEqual(a["score_col"], "all_score")

    def test_통합_행은_그대로_unified_risk_score(self):
        a = F.all_row({"unified_risk_score": "44", "hot_area": "M16HUB"})
        self.assertEqual(a["score"], 44.0)
        self.assertFalse(a["from_fab_file"])

    def test_어긋났다고_할_때_어느_이름인지_밝힌다(self):
        a = F.area_score({"M14_pts_RA": "10", "area_score": "99"}, "M14")
        self.assertIn("area_score", a["mismatch"])
        self.assertEqual(a["stored_col"], "area_score")


class 컬럼_정의는_이미_있는_것을_쓴다(unittest.TestCase):
    """★화면 지표 목록을 이 파일이 새로 정하면 두 곳이 갈라진다."""

    def test_ALL_은_config_ui_metric_groups_에서_가져온다(self):
        cfg = load_config()
        got = [m["key"] for m in F.screen_metrics("ALL", cfg)]
        want = [m["key"] for g in cfg["ui"]["metric_groups"]
                if g.get("id") == "amos" for m in g["metrics"] if m.get("key")]
        self.assertEqual(got, want)
        self.assertGreater(len(got), 10)

    def test_FAB_은_lp_client_fab_strip_에서_가져온다(self):
        from lp_client import _fab_strip
        cfg = load_config()
        for f in F.fabs(cfg):
            self.assertEqual([m["key"] for m in F.screen_metrics(f, cfg)],
                             [m["key"] for m in _fab_strip(f)], f)

    def test_화면_지표와_룰이_붙는다(self):
        cfg = load_config()
        j = F.join_columns("M14", cfg)
        by = {m["key"]: m for m in j["metrics"]}
        self.assertEqual(by["M14_ra"]["rules"], ["RA", "RA_sus"])
        self.assertEqual(by["M14_ra"]["thr"], [3.3, 2.31])
        self.assertFalse(by["M14_ra_count"]["used"], "참고 표시용 지표다")

    def test_ALL_화면에_점수를_만드는_항이_빠져_있다(self):
        """실제로 확인된 구멍 — flow/sla/sorter/mc 합계가 ALL 화면 지표
        목록에 없다. 없어졌다고 조용히 넘기지 말고 표시해야 한다."""
        j = F.join_columns("ALL", load_config())
        missing = {x["key"] for x in j["only_rule"]}
        for k in ("flow_score", "sla_score_total", "sorter_score_total",
                  "mc_score_total"):
            self.assertIn(k, missing)

    def test_CSV_에_값이_없는_컬럼도_숨기지_않는다(self):
        j = F.join_columns("M16HUB", load_config())
        self.assertTrue(j["no_csv"], "MAXCAPA 등은 CSV 에 값이 안 온다")
        self.assertTrue(all(x["raw"] for x in j["no_csv"]))

    def test_compare_API_는_짧은_캐시로_CSV_재읽기를_막는다(self):
        """아바타가 5초마다 두드린다 — 매번 하루 CSV 를 다시 읽으면 수집·LLM
        과 겹칠 때 응답이 늘어져 저쪽에서 '끊김' 으로 보인다 (현장 증상)."""
        import server
        import store_csv
        server._FAB_CMP_CACHE.update(key=None, at=0.0, out=None)
        calls = {"n": 0}
        orig = store_csv.read_day

        def counting(day, cfg):
            calls["n"] += 1
            return orig(day, cfg)
        store_csv.read_day = counting
        try:
            c = server.app.test_client()
            r1 = json.loads(c.get("/api/fab/compare").get_data())
            first = calls["n"]
            r2 = json.loads(c.get("/api/fab/compare").get_data())
            self.assertTrue(r1["ok"] and r2["ok"])
            # 한 번 계산할 때 ALL 파일 + FAB 분리 파일들을 읽는다
            # (store_csv.read_day 는 mtime·크기가 같으면 파일을 안 다시 연다)
            self.assertGreaterEqual(first, 1)
            self.assertEqual(calls["n"], first,
                             "두 번째 호출이 CSV 를 또 읽었다 — 캐시가 안 탄다")
            self.assertEqual(r1["at"], r2["at"])
        finally:
            store_csv.read_day = orig
            server._FAB_CMP_CACHE.update(key=None, at=0.0, out=None)

    def test_API_도_ALL_을_준다(self):
        """화면이 여섯 시스템인데 API 가 다섯만 주면 화면이 ALL 을 못 그린다."""
        import server
        c = server.app.test_client()
        d = json.loads(c.get("/api/fab/columns").get_data())
        self.assertTrue(d["ok"], d.get("error"))
        self.assertEqual(d["systems"][0], "ALL")
        self.assertEqual(set(d["fabs"]), set(["ALL"] + F.fabs(load_config())))
        self.assertTrue(d["fabs"]["ALL"]["is_all"])
        self.assertTrue(d["fabs"]["ALL"]["watch"], "ALL 감시 컬럼이 비었다")
        self.assertNotIn("solo", d["fabs"]["ALL"], "ALL 에는 단독 상한이 없다")
        self.assertIn("solo", d["fabs"]["M14"])


class 상한과_등급컷은_다른_숫자(unittest.TestCase):
    """50 은 영역점수 상한, 60 은 경계 컷. 붙어 다녀서 헷갈리기 쉽다."""

    def test_상한은_등급컷과_무관하다(self):
        cfg = deepcopy(load_config())
        warn = grade_cuts(cfg)[0]
        self.assertNotEqual(F.AREA_CAP, warn,
                            "우연히 같아지면 이 구분이 안 보인다")
        # 경계 컷을 바꿔도 상한은 그대로여야 한다
        cfg["grade"] = deepcopy(cfg["grade"])
        cfg["grade"]["bands"] = deepcopy(cfg["grade"]["bands"])
        cfg["grade"]["bands"][0] = dict(cfg["grade"]["bands"][0], min=50)
        row = {f"M16HUB_pts_{c}": str(F.RULE_BY_CODE[c]["pts"])
               for c in F.RULE_ORDER}
        self.assertEqual(F.area_score(row, "M16HUB", cfg)["area"], F.AREA_CAP)

    def test_경계는_영역점수_30_에서_시작한다(self):
        """위험도 60 = 영역점수 30. 화면에서 '몇 점부터 경계냐' 를 물으면
        이 환산을 대야 한다."""
        cfg = load_config()
        warn = grade_cuts(cfg)[0]
        self.assertEqual(F.risk(30), warn)
        self.assertLess(F.risk(25), warn)

    def test_문서가_둘을_구분해_적는다(self):
        import fab_score_doc as D
        html = D.build(load_config())
        cfg = load_config()
        warn = grade_cuts(cfg)[0]
        self.assertIn("등급 컷이 아닙니다", html)
        self.assertIn(f"경계 <b>{warn}</b>", html)


class 문서_생성(unittest.TestCase):
    def test_생성되고_핵심_숫자가_들어간다(self):
        import fab_score_doc as D
        html = D.build(load_config())
        cfg = load_config()
        warn, danger, crit = grade_cuts(cfg)
        self.assertIn("<title>", html)
        # 등급 컷이 코드에 박히지 않고 config 값으로 들어갔나
        self.assertIn(f"{warn} / {danger} / {crit}", html)
        self.assertNotIn("50/71/85 로 등급", html)
        # 다섯 FAB 전부 실렸나
        for f in F.fabs(cfg):
            self.assertIn(f, html)
        # 임계 미정의를 숨기지 않았나
        self.assertIn("임계 미정의", html)
        # 단독 상한 숫자가 실제 계산과 같은가
        self.assertIn(str(F.solo_ceiling("M16B", cfg, "typical")["score"]), html)

    def test_외부_자원을_안_불러온다(self):
        """사내망엔 인터넷이 없다. CDN 을 물면 현장에서 스타일이 다 깨진다."""
        import fab_score_doc as D
        html = D.build(load_config())
        for bad in ("http://", "https://", "<script"):
            self.assertNotIn(bad, html, f"{bad} 가 들어 있다")

    def test_MD_에도_ALL_이_들어간다(self):
        """에이전트 학습용 md. HTML 쪽만 고치고 md 를 안 고치면
        에이전트가 옛 사실을 배운다."""
        import fab_score_doc as D
        cfg = load_config()
        md = D.build_md(cfg)
        warn, danger, crit = grade_cuts(cfg)
        self.assertIn("| 룰 | ALL |", md, "컬럼 표에 ALL 열이 없다")
        for f in F.fabs(cfg):
            self.assertIn(f"`{f}`", md, f)
        self.assertIn("area_score", md)
        self.assertIn("all_score", md)
        self.assertIn(f"{warn}", md)
        self.assertIn(f"영역점수 상한 {F.AREA_CAP}", md)

    def test_MD_숫자가_코드와_같다(self):
        """md 를 손으로 고치면 코드와 갈라진다 — 생성물이어야 한다."""
        import fab_score_doc as D
        cfg = load_config()
        md = D.build_md(cfg)
        for f in F.fabs(cfg):
            t = F.solo_ceiling(f, cfg, "typical")
            mx = F.max_area(f, cfg)
            self.assertIn(f"| `{f}` |", md)
            row = next(l for l in md.splitlines() if l.startswith(f"| `{f}` | "))
            self.assertIn(f"**{t['score']}**", row, f"{f} 통상 단독상한")
            self.assertIn(f"{mx['area_max']}/{F.AREA_CAP}", row, f"{f} 영역 천장")
        # 임계값도 코드에서 나온 값이어야 한다
        self.assertIn("≥ 9분", md)        # M16HUB R-A
        self.assertIn("임계 미정의", md)   # M14B SLA

    def test_MD_는_생성물이라고_밝힌다(self):
        import fab_score_doc as D
        md = D.build_md(load_config())
        self.assertIn("생성", md.splitlines()[2])
        self.assertIn("손으로 고치지 마라", md)

    def test_MD_에_확인_안_된_것이_남아_있다(self):
        """모르는 걸 아는 척하면 에이전트가 그걸 사실로 배운다."""
        import fab_score_doc as D
        md = D.build_md(load_config())
        self.assertIn("아직 확인 안 된 것", md)
        self.assertIn("M14B", md.split("아직 확인 안 된 것")[1])

    def test_MD_마크다운이_깨지지_않는다(self):
        """겹친 ** 나 열 수가 안 맞는 표는 에이전트가 잘못 읽는다."""
        import re
        import fab_score_doc as D
        md = D.build_md(load_config())
        for i, line in enumerate(md.splitlines(), 1):
            if line.startswith("#"):
                self.assertEqual(line.count("**"), 0, f"{i}행 제목에 겹친 굵게: {line}")
            self.assertEqual(line.count("**") % 2, 0, f"{i}행 ** 짝이 안 맞음")
            # ★'**a **b****' 처럼 굵게가 겹치면 짝수라 위 검사를 통과한다.
            #   굵게 안에 다시 ** 가 들어간 경우를 직접 잡는다.
            for m in re.finditer(r"\*\*(.+?)\*\*", line):
                self.assertNotIn("**", m.group(1),
                                 f"{i}행 굵게 안에 굵게: {line[:70]}")

    def test_MD_규칙이_제목으로_뽑혀_있다(self):
        """에이전트가 규칙 하나하나에 앵커를 잡을 수 있어야 한다.
        굵은 글씨 한 줄로 두면 목차에도 안 잡히고 인용도 안 된다."""
        import re
        import fab_score_doc as D
        md = D.build_md(load_config())
        # ★"## 8." 로 자르면 "### 8." 에서도 잘린다 — 줄 시작으로 맞춘다
        body = md.split("\n## 8. ")[1].split("\n## 9. ")[0]
        heads = re.findall(r"^### (\d+)\. (.+)$", body, re.M)
        self.assertGreaterEqual(len(heads), 8, "규칙이 ### 제목으로 안 나왔다")
        self.assertEqual([n for n, _t in heads],
                         [str(i) for i in range(1, len(heads) + 1)])
        for _n, t in heads:
            self.assertNotIn("*", t, f"제목에 마크업이 섞였다: {t}")
        # 규칙마다 ✅ 가 있고, 대부분 ❌ 도 같이 있어야 한다
        self.assertEqual(body.count("✅"), len(heads))
        self.assertGreaterEqual(body.count("❌"), len(heads) - 1)
        # 표마다 헤더/구분선/본문 열 수가 같아야 한다
        lines = md.splitlines()
        for i, line in enumerate(lines):
            if not line.startswith("| ---"):
                continue
            n = line.count("|")
            self.assertEqual(lines[i - 1].count("|"), n, f"{i}행 표 헤더 열 수")
            j = i + 1
            while j < len(lines) and lines[j].startswith("|"):
                self.assertEqual(lines[j].count("|"), n,
                                 f"{j + 1}행 표 본문 열 수: {lines[j][:60]}")
                j += 1

    def test_명령줄로_MD_가_만들어진다(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "x.md")
            r = subprocess.run([sys.executable, "fab_score_doc.py", "--md", out],
                               cwd=util.BASE, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertGreater(os.path.getsize(out), 8000)
            with open(out, encoding="utf-8") as f:
                self.assertIn("# M16 HUBROOM", f.read())

    def test_명령줄로_파일이_만들어진다(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "x.html")
            r = subprocess.run([sys.executable, "fab_score_doc.py", out],
                               cwd=util.BASE, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertGreater(os.path.getsize(out), 20000)


if __name__ == "__main__":
    unittest.main()
