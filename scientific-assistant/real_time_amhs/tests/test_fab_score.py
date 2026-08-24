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

    def test_융합_공식이_전체_점수를_재현한다(self):
        ok = [r for r in rows() if F.fuse_check(r)["match"]]
        self.assertGreaterEqual(len(ok), 3,
                                "실물 형식 행에서 전체 점수가 재현돼야 한다")
        for r in ok:
            fc = F.fuse_check(r)
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

    def test_M16B_는_가중치와_흐름노드_때문에_최대로도_못_간다(self):
        cfg = load_config()
        warn = grade_cuts(cfg)[0]
        t = F.solo_ceiling("M16B", cfg, "typical")
        m = F.solo_ceiling("M16B", cfg, "max")
        self.assertEqual(t["weight"], 0.5)
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
        self.assertEqual(names, {"M16", "M16_PKT", "M16_WT"})

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

    def test_ALL_에는_임계도_단독상한도_없다(self):
        """ALL 은 영역이 아니다 — 자기 임계로 룰을 켜지 않고, 자기가 전체라
        '단독으로 몇 점' 이라는 개념이 없다. 있는 척하면 안 된다."""
        a = F.all_row(rows()[0])
        self.assertNotIn("solo", a)
        self.assertNotIn("readings", a)
        self.assertNotIn("area", a)
        self.assertEqual(F.watch("ALL"), {})

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
