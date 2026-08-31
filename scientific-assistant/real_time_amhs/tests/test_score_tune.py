# -*- coding: utf-8 -*-
"""등급 컷 자동 조정 — score_tune.

★이 파일이 지키는 것은 '똑똑하게 고른다' 가 아니라 **함부로 안 바꾼다** 다.
  등급 컷은 알람이 뜨고 안 뜨고를 가르는 값이다. 모델이 헛발질했을 때
  조용히 망가지지 않는 것이 정확도보다 중요하다.

  · 모델이 죽으면 → 현재 값 유지 (다른 모델로 갈아타지 않는다)
  · 지금 값을 잘못 읽었으면 → 그 제안은 버린다
  · 이유(숫자 근거)를 못 대면 → 안 바꾼다
  · 한 번에 max_step 넘게 못 옮긴다
  · 표본이 모자라면 안 건드린다
  · 유지도 기록한다 — '왜 안 바꿨나' 도 답할 수 있어야 한다
"""
import json
import os
import re
import tempfile
import unittest
from datetime import datetime, timedelta

from . import util  # noqa: F401
import score_tune as T


CUTS = {"warn": 35, "danger": 50, "critical": 70}
FULL = {"n": 480, "min": 3, "max": 78, "avg": 22.4,
        "p50": 18, "p75": 29, "p90": 41, "p95": 52, "p99": 62,
        "pct_warn": 14.2, "pct_danger": 4.1, "pct_crit": 1.0,
        "min_warn": 68, "min_danger": 20, "min_crit": 5}


def snap(n=480, systems=("ALL",)):
    st = dict(FULL, n=n)
    return {s: {"cuts": dict(CUTS), "stats": dict(st)} for s in systems}


def want(**kw):
    """LLM 이 냈다고 치는 제안 한 건 (ALL)."""
    row = {"now": dict(CUTS), "verdict": "변경",
           "warn": 41, "danger": 55, "critical": 72,
           "why": "p90 이 41 인데 경계가 35 라 8시간 중 27% 가 알람이었다"}
    row.update(kw)
    return {"by_sys": {"ALL": row}}


def one(rows, sys="ALL"):
    return next(r for r in rows if r["sys"] == sys)


class 함부로_안_바꾼다(unittest.TestCase):
    def setUp(self):
        self.tc = T.cfg_of({})

    def _decide(self, w, s=None):
        return T.decide(w, s or snap(), self.tc)

    def test_근거가_갖춰지면_바꾼다(self):
        """막기만 하면 아무것도 안 된다 — 제대로 된 제안은 통해야 한다."""
        applied, rows = self._decide(want())
        self.assertEqual(one(rows)["verdict"], "변경")
        self.assertEqual(applied["ALL"]["warn"], 41)

    def test_현재값을_잘못_읽었으면_버린다(self):
        """★지금 값을 잘못 본 모델이 낸 '변경' 은 근거가 없다."""
        applied, rows = self._decide(
            want(now={"warn": 60, "danger": 71, "critical": 85}))
        self.assertEqual(applied, {})
        self.assertEqual(one(rows)["verdict"], "유지")
        self.assertIn("잘못 읽었다", one(rows)["note"])

    def test_현재값을_안_적으면_확인이_안_된다(self):
        applied, rows = self._decide(want(now=None))
        self.assertEqual(applied, {})
        self.assertIn("현재값", one(rows)["note"])

    def test_이유가_없으면_안_바꾼다(self):
        """★근거를 못 대는 변경은 나중에 되짚을 수가 없다."""
        applied, rows = self._decide(want(why=""))
        self.assertEqual(applied, {})
        self.assertIn("이유", one(rows)["note"])

    def test_이유에_숫자가_없으면_안_바꾼다(self):
        applied, rows = self._decide(want(why="좀 높여야 할 것 같습니다"))
        self.assertEqual(applied, {})
        self.assertIn("숫자", one(rows)["note"])

    def test_한_번에_크게_못_옮긴다(self):
        """35 → 60 을 그대로 받으면 한 번의 헛발질로 알람이 통째로 죽는다."""
        applied, rows = self._decide(
            want(warn=60, danger=75, critical=90, why="p90 이 62 라 크게 올린다"))
        step = self.tc["max_step"]
        self.assertEqual(applied["ALL"]["warn"], CUTS["warn"] + step)
        self.assertIn("한 걸음", one(rows)["note"])

    def test_순서가_어긋나면_버린다(self):
        applied, rows = self._decide(
            want(warn=55, danger=45, critical=72, why="p90 이 41 이라 올린다"))
        self.assertEqual(applied, {})

    def test_표본이_모자라면_안_건드린다(self):
        """새벽에 몇 줄 보고 컷을 옮기면 아침에 알람이 안 온다."""
        applied, rows = T.decide(want(), snap(n=12), self.tc)
        self.assertEqual(applied, {})
        self.assertIn("표본", one(rows)["note"])

    def test_유지도_결과로_남긴다(self):
        """★'맞다' 도 알려야 할 결과다 — 안 바꾼 이유를 사람이 알아야 한다."""
        applied, rows = self._decide(want(
            verdict="유지", warn=35, danger=50, critical=70,
            why="경계이상 14.2% 로 적정 범위(10~20%) 안이다"))
        self.assertEqual(applied, {})
        r = one(rows)
        self.assertEqual(r["verdict"], "유지")
        self.assertIn("14.2", r["why"], "왜 맞는지가 안 남았다")

    def test_안_본_시스템은_그대로_둔다(self):
        applied, rows = T.decide(want(), snap(systems=("ALL", "M14")), self.tc)
        self.assertEqual(one(rows, "M14")["verdict"], "유지")
        self.assertNotIn("M14", applied)


class 모델이_안_되면_현재값_유지(unittest.TestCase):
    """★다른 모델로 갈아타지 않는다. 등급 컷을 아무 모델이나 대신 정하면 안 된다."""

    def setUp(self):
        self.cfg = {"llm": {"enabled": True, "model": "관제용-기본모델"},
                    "policy": {"auto_tune": {"model": "gaia-Qwen3.6-35B-A3B"}}}
        self._snap = T.snapshot
        T.snapshot = lambda c, h, sl, now=None: snap(systems=tuple(sl))
        self.addCleanup(lambda: setattr(T, "snapshot", self._snap))
        import llm_client
        self.llm = llm_client
        self._chat = llm_client.chat_json
        self.addCleanup(lambda: setattr(llm_client, "chat_json", self._chat))

    def test_정책_전용_모델로_부른다(self):
        seen = {}

        def spy(msgs, c=None, **kw):
            seen["model"] = (c or {}).get("llm", {}).get("model")
            return json.dumps(want()), None
        self.llm.chat_json = spy
        T.run(self.cfg, ["ALL"], by="시험")
        self.assertEqual(seen["model"], "gaia-Qwen3.6-35B-A3B")

    def test_관제_대화_모델을_안_건드린다(self):
        """★CFG 를 고치면 관제 전체가 그 모델로 바뀐다 (같은 dict 를 공유)."""
        self.llm.chat_json = lambda m, c=None, **kw: (json.dumps(want()), None)
        T.run(self.cfg, ["ALL"], by="시험")
        self.assertEqual(self.cfg["llm"]["model"], "관제용-기본모델")

    def test_모델이_죽으면_아무것도_안_바꾼다(self):
        self.llm.chat_json = lambda m, c=None, **kw: (None, "HTTP 404 model not found")
        rec = T.run(self.cfg, ["ALL", "M14"], by="시험")
        self.assertEqual(rec["applied"], {})
        self.assertIn("현재 컷을 그대로", rec["error"])
        self.assertTrue(rec["rows"], "무슨 일이 있었는지는 남아야 한다")
        for r in rec["rows"]:
            self.assertEqual(r["verdict"], "유지")

    def test_JSON_이_아니면_아무것도_안_바꾼다(self):
        self.llm.chat_json = lambda m, c=None, **kw: ("음... 잘 모르겠습니다", None)
        rec = T.run(self.cfg, ["ALL"], by="시험")
        self.assertEqual(rec["applied"], {})
        self.assertIn("현재 컷을 그대로", rec["error"])

    def test_데이터가_없으면_모델을_안_부른다(self):
        """없는 데이터로 물어봐야 답이 나올 리 없다 — 호출 자체를 아낀다."""
        called = []
        self.llm.chat_json = lambda m, c=None, **kw: (called.append(1), ("{}", None))[1]
        T.snapshot = lambda c, h, sl, now=None: {
            s: {"cuts": dict(CUTS), "stats": {"n": 0}} for s in sl}
        rec = T.run(self.cfg, ["ALL"], by="시험")
        self.assertEqual(called, [])
        self.assertIn("데이터가 없습니다", rec["error"])


class 구간과_주기(unittest.TestCase):
    def test_기본은_8시간_교대_한_텀(self):
        self.assertEqual(T.cfg_of({})["hours"], 8)

    def test_2시간마다_돈다(self):
        """OHT·물류 한 사이클이 대략 120분이다."""
        at = T.cfg_of({})["at"]
        self.assertEqual(len(at), 12, "하루 12번(2시간마다) 이 아니다")
        self.assertEqual(sorted(set(b - a for a, b in zip(at, at[1:]))), [2])

    def test_교대_시작에_맞물린다(self):
        """07·15·23 시(교대 시작)에 반드시 한 번은 돈다."""
        at = T.cfg_of({})["at"]
        for h in (7, 15, 23):
            self.assertIn(h, at)

    def test_교대를_이름으로_남긴다(self):
        for h, name in ((9, "주간"), (17, "저녁"), (2, "야간"), (23, "야간")):
            self.assertIn(name, T.shift_of(datetime(2026, 8, 31, h, 0)))

    def test_기본은_꺼져_있다(self):
        """★자동으로 도는 것을 켜는 판단은 사람이 한다."""
        self.assertFalse(T.cfg_of({})["enabled"])

    def test_설정으로_덮을_수_있다(self):
        c = T.cfg_of({"policy": {"auto_tune": {"hours": 4, "at": [6, 18],
                                               "enabled": True}}})
        self.assertEqual((c["hours"], c["at"], c["enabled"]), (4, [6, 18], True))


class 자정을_넘어도_읽는다(unittest.TestCase):
    """★01시에 돌면 구간이 전날 17시부터다. 하루 파일만 읽으면 야간 조는
    늘 '표본 부족' 이 된다."""

    def test_어제_파일도_읽는다(self):
        seen = []
        import store_csv
        keep = store_csv.read_day
        store_csv.read_day = lambda d, c=None: (seen.append(d), [])[1]
        self.addCleanup(lambda: setattr(store_csv, "read_day", keep))
        T.window_rows(8, {}, now=datetime(2026, 8, 31, 1, 30))
        self.assertEqual(sorted(seen), ["20260830", "20260831"])

    def test_구간_밖은_버린다(self):
        # 12시 기준 8시간 = 04~12시. 같은 날이라 파일은 하나만 읽는다.
        now = datetime(2026, 8, 31, 12, 0)
        rows = [{"datetime": (now - timedelta(hours=h)).strftime("%Y-%m-%d %H:%M"),
                 "unified_risk_score": "10"} for h in (1, 7, 9, 30)]
        import store_csv
        keep = store_csv.read_day
        store_csv.read_day = lambda d, c=None: rows
        self.addCleanup(lambda: setattr(store_csv, "read_day", keep))
        self.assertEqual(len(T.window_rows(8, {}, now=now)), 2,
                         "8시간 밖(9·30시간 전) 행이 섞였다")

    def test_야간에는_두_날을_합쳐_읽는다(self):
        """01시 기준 8시간이면 전날 17시부터다 — 두 파일이 다 필요하다."""
        now = datetime(2026, 8, 31, 1, 0)
        per_day = [
            {"datetime": "2026-08-30 18:00", "unified_risk_score": "10"},
            {"datetime": "2026-08-31 00:30", "unified_risk_score": "20"},
            {"datetime": "2026-08-30 09:00", "unified_risk_score": "30"},  # 구간 밖
        ]
        import store_csv
        keep = store_csv.read_day
        store_csv.read_day = lambda d, c=None: per_day
        self.addCleanup(lambda: setattr(store_csv, "read_day", keep))
        got = T.window_rows(8, {}, now=now)
        # 파일 2개(어제·오늘)를 각각 읽으므로 구간 안 2행 × 2 = 4
        self.assertEqual(len(got), 4)
        self.assertTrue(all("09:00" not in r["datetime"] for r in got))


class 분포를_제대로_센다(unittest.TestCase):
    def _rows(self, vals):
        return [{"unified_risk_score": str(v)} for v in vals]

    def test_비율은_분_단위로_센다(self):
        """'최고 몇 점' 만 보면 하루 한 번 튄 값으로 컷을 정하게 된다."""
        st = T.stats(self._rows([10] * 90 + [40] * 10), (35, 50, 70))
        self.assertEqual(st["n"], 100)
        self.assertEqual(st["min_warn"], 10)
        self.assertEqual(st["pct_warn"], 10.0)
        self.assertEqual(st["pct_danger"], 0.0)

    def test_숫자가_아닌_값은_뺀다(self):
        st = T.stats(self._rows(["", "abc", "20", "40"]), (35, 50, 70))
        self.assertEqual(st["n"], 2)

    def test_빈_구간은_n이_0(self):
        self.assertEqual(T.stats([], (35, 50, 70)), {"n": 0})

    def test_한_줄이어도_안_터진다(self):
        st = T.stats(self._rows([42]), (35, 50, 70))
        self.assertEqual((st["n"], st["p90"]), (1, 42.0))


class 기록을_남긴다(unittest.TestCase):
    """★'왜 컷이 이래?' 에 답할 수 있어야 자동을 켜 둘 수 있다."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.cfg = {"policy": {"auto_tune": {
            "store": os.path.relpath(os.path.join(self.dir, "t.jsonl"),
                                     T.BASE_DIR)}}}

    def test_유지도_남긴다(self):
        """안 바꾼 이유도 남아야 다음에 손댈지 말지 정할 수 있다."""
        T.record({"at": "2026-08-31T09:00:00", "by": "자동 09시",
                  "rows": [{"sys": "ALL", "verdict": "유지",
                            "why": "경계이상 14% 로 적정"}]}, self.cfg)
        h = T.history(self.cfg)
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0]["rows"][0]["verdict"], "유지")

    def test_새_것이_위로_온다(self):
        for i in range(3):
            T.record({"at": f"2026-08-31T0{i}:00:00", "rows": []}, self.cfg)
        self.assertEqual([r["at"][:13] for r in T.history(self.cfg)],
                         ["2026-08-31T02", "2026-08-31T01", "2026-08-31T00"])

    def test_변경만_추릴_수_있다(self):
        T.record({"at": "a", "rows": [{"sys": "ALL", "verdict": "유지"}]}, self.cfg)
        T.record({"at": "b", "rows": [{"sys": "ALL", "verdict": "변경"}]}, self.cfg)
        self.assertEqual([r["at"] for r in T.history(self.cfg, changed_only=True)],
                         ["b"])

    def test_깨진_줄이_있어도_읽는다(self):
        T.record({"at": "a", "rows": []}, self.cfg)
        with open(os.path.join(T.BASE_DIR,
                               self.cfg["policy"]["auto_tune"]["store"]),
                  "a", encoding="utf-8") as f:
            f.write("이건 JSON 이 아니다\n")
        T.record({"at": "b", "rows": []}, self.cfg)
        self.assertEqual(len(T.history(self.cfg)), 2)

    def test_기록이_없으면_빈_목록(self):
        self.assertEqual(T.history({"policy": {"auto_tune": {
            "store": "data/없는파일.jsonl"}}}), [])


class 응답을_너그럽게_읽는다(unittest.TestCase):
    def test_코드펜스를_걷어낸다(self):
        d = T.parse('```json\n{"by_sys": {}}\n```')
        self.assertEqual(d, {"by_sys": {}})

    def test_앞뒤_군말을_걷어낸다(self):
        d = T.parse('생각해 보니 이렇습니다.\n{"note": "ok"}\n이상입니다.')
        self.assertEqual(d["note"], "ok")

    def test_JSON_이_아니면_None(self):
        for bad in ("", "그냥 글", "{망가진", None):
            self.assertIsNone(T.parse(bad))


class 프롬프트를_볼_수_있다(unittest.TestCase):
    """★무엇을 물어보고 있는지 모르면 답을 믿을 수도, 못 믿을 수도 없다."""

    def test_기본_지시문을_준다(self):
        self.assertEqual(T.system_prompt({}), T.SYSTEM)

    def test_설정으로_갈아끼운다(self):
        c = {"policy": {"auto_tune": {"prompt": "내가 쓴 지시문"}}}
        self.assertEqual(T.system_prompt(c), "내가 쓴 지시문")

    def test_비우면_기본으로_돌아간다(self):
        for empty in ("", "   ", None):
            c = {"policy": {"auto_tune": {"prompt": empty}}}
            self.assertEqual(T.system_prompt(c), T.SYSTEM)

    def test_실제로_그_지시문으로_묻는다(self):
        """화면에 보이는 것과 보내는 것이 다르면 보여 주는 의미가 없다."""
        c = {"policy": {"auto_tune": {"prompt": "내가 쓴 지시문"}}}
        m = T.build_messages(snap(), 8, datetime(2026, 8, 31, 9, 0), c)
        self.assertEqual(m[0]["content"], "내가 쓴 지시문")

    def test_붙는_데이터까지_같이_본다(self):
        """지시문만 보여 주면 '왜 이렇게 판단했지' 를 못 짚는다."""
        keep = T.snapshot
        T.snapshot = lambda c, h, sl, now=None: snap(systems=tuple(sl))
        self.addCleanup(lambda: setattr(T, "snapshot", keep))
        d = T.preview({}, ["ALL"], now=datetime(2026, 8, 31, 9, 0))
        self.assertIn("system", d)
        self.assertIn("[ALL]", d["user"], "실제 데이터가 안 붙었다")
        self.assertIn("35", d["user"], "지금 컷이 안 보인다")
        self.assertGreater(d["chars"], 0)


class 화면(unittest.TestCase):
    """브라우저를 안 띄우고 HTML 을 글자로 본다."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(util.BASE, "static", "dashboard.html"),
                  encoding="utf-8") as f:
            cls.h = f.read()

    def test_버튼이_두_개다(self):
        self.assertIn('id="sp-save"', self.h)
        self.assertIn('id="sp-llm"', self.h)
        self.assertRegex(self.h, r'id="sp-save"[^>]*>\s*수동 변경')
        self.assertRegex(self.h, r'id="sp-llm"[\s\S]{0,200}?LLM 스코어 변경')

    def test_자동_켜고_끄기가_있다(self):
        self.assertIn('id="sp-auto"', self.h)
        self.assertIn("2시간마다 자동", self.h)

    def test_변경_로그를_볼_수_있다(self):
        """★'왜 컷이 이래?' 를 화면에서 답할 수 있어야 한다."""
        self.assertIn('id="sp-log"', self.h)
        self.assertIn("변경 로그", self.h)
        self.assertIn("spLoadLog", self.h)

    def test_유지와_변경을_색으로_가른다(self):
        m = re.search(r"const spVer = [\s\S]*?;", self.h)
        self.assertIsNotNone(m, "판정 표시가 없다")
        self.assertIn("var(--ok)", m.group(0))
        self.assertIn("var(--major)", m.group(0))

    def test_안_바꾼_이유도_화면에_적는다(self):
        m = re.search(r"function spRowsHtml\(rows\)\{[\s\S]*?\n\}", self.h)
        self.assertIsNotNone(m)
        self.assertIn("r.why", m.group(0))
        self.assertIn("r.note", m.group(0))

    def test_프롬프트를_화면에서_보고_고친다(self):
        self.assertIn('id="sp-prompt"', self.h)
        self.assertIn('id="sp-psave"', self.h)
        self.assertIn('id="sp-pdef"', self.h, "기본으로 되돌릴 길이 없다")
        self.assertIn('id="sp-pview"', self.h, "보낼 내용을 못 본다")

    def test_고치는_중에_덮어쓰지_않는다(self):
        """로그가 갱신될 때 타이핑하던 지시문이 날아가면 안 된다."""
        m = re.search(r"async function spLoadLog\(\)\{[\s\S]*?\n\}", self.h)
        self.assertIsNotNone(m)
        self.assertIn("activeElement", m.group(0))

    def test_규칙을_화면에_적어_둔다(self):
        """무슨 규칙으로 도는지 모르면 켜 둘 수가 없다."""
        for word in ("8시간", "2시간마다", "10점", "이유"):
            self.assertIn(word, self.h, word)


if __name__ == "__main__":
    unittest.main()
