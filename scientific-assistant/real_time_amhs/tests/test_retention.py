# -*- coding: utf-8 -*-
"""과거 파일 정리 — 보관 기간 (정책 탭).

고객: "주기적으로 데이터 삭제 필요하네" · "정책에서 과거 파일 정리 기간 해주라"
· "설정할수 있게".

★지우는 것은 이름에 날짜가 박힌 파일(TOTAL · LLM 판단 · ML · raw)뿐이다.
  케이스·리포트·설정·모르는 파일은 그대로 둔다.
★보관 기간 N일 = 오늘 포함 N일을 남긴다. 0 이면 아무것도 안 지운다 (기본).
★지우기는 되돌릴 수 없다 — 저장만으로는 안 지우고, 화면은 지울 것을 먼저 보여 준다.
"""
import json
import os
import re
import shutil
import tempfile
import unittest
from datetime import datetime
from unittest import mock

import store_csv

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
TODAY = datetime(2026, 9, 28, 9, 0)


def _touch(p, body="datetime,unified_risk_score\n2026-01-01 00:00,1\n"):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(body)


class 보관_기간을_넘긴_날짜_파일만_지운다(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.cfg = {"storage": {"daily_csv_dir": self.dir}}
        for c in (store_csv._rows_cache, store_csv._day_cache,
                  store_csv._keys_cache, store_csv._fields_cache):
            c.clear()
        j = lambda *a: os.path.join(self.dir, *a)          # noqa: E731
        # 지울 것 — 30일이면 2026-08-30 부터 남는다
        self.old = [j("20260829_TOTAL.CSV"), j("20260829_LLM.CSV"), j("20260829_ML.CSV"),
                    j("20260101_TOTAL.CSV"), j("raw", "20260829_발동이벤트.csv"),
                    j("20250505_total.csv")]
        # 남길 것 — 기간 안의 날 · 날짜 파일이 아닌 것 · 모르는 이름
        self.keep = [j("20260830_TOTAL.CSV"), j("20260928_TOTAL.CSV"), j("20260928_LLM.CSV"),
                     j("raw", "20260830_발동이벤트.csv"),
                     j("cases.json"), j("reports", "20260101_report.html"),
                     j("20260101_TOTAL.CSV.bak"), j("20261399_TOTAL.CSV"),
                     j("20260101_메모.CSV"), j("M14", "20260101_TOTAL.CSV")]
        for p in self.old + self.keep:
            _touch(p)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_남기는_첫_날은_오늘_포함_N일(self):
        self.assertEqual(store_csv.keep_from(30, TODAY), "20260830")
        self.assertEqual(store_csv.keep_from(1, TODAY), "20260928")
        self.assertEqual(store_csv.keep_from(7, TODAY), "20260922")

    def test_넘긴_날만_지우고_나머지는_그대로(self):
        r = store_csv.prune_days(30, self.cfg, today=TODAY)
        for p in self.old:
            self.assertFalse(os.path.exists(p), f"안 지워졌다: {p}")
        for p in self.keep:
            self.assertTrue(os.path.exists(p), f"지우면 안 되는 것을 지웠다: {p}")
        self.assertEqual(r["files"], len(self.old))
        self.assertEqual(r["days"], 3)                    # 20250505 · 20260101 · 20260829
        self.assertEqual((r["first"], r["last"]), ("20250505", "20260829"))
        self.assertEqual(r["keep_from"], "20260830")
        self.assertEqual(r["failed"], 0)

    def test_FAB_폴더는_그_시스템_설정으로_따로_정리한다(self):
        """ALL 폴더 정리가 FAB 하위 폴더까지 들어가면 안 된다 — FAB 는 FAB 설정으로."""
        store_csv.prune_days(30, self.cfg, today=TODAY)
        fab = os.path.join(self.dir, "M14", "20260101_TOTAL.CSV")
        self.assertTrue(os.path.exists(fab))
        store_csv.prune_days(30, {"storage": {"daily_csv_dir": os.path.join(self.dir, "M14")}},
                             today=TODAY)
        self.assertFalse(os.path.exists(fab))

    def test_0_이면_아무것도_안_지운다(self):
        for keep in (0, -3, None, "abc"):
            r = store_csv.prune_days(keep, self.cfg, today=TODAY)
            self.assertEqual(r["files"], 0, keep)
        for p in self.old + self.keep:
            self.assertTrue(os.path.exists(p))

    def test_미리_보기는_세기만_한다(self):
        dry = store_csv.prune_days(30, self.cfg, dry_run=True, today=TODAY)
        for p in self.old:
            self.assertTrue(os.path.exists(p), "미리 보기가 지웠다")
        real = store_csv.prune_days(30, self.cfg, today=TODAY)
        for k in ("files", "bytes", "days", "first", "last", "keep_from"):
            self.assertEqual(dry[k], real[k], k)

    def test_못_지운_파일은_건너뛰고_적는다(self):
        locked = self.old[0]
        real_remove = os.remove

        def remove(p):
            if p == locked:
                raise PermissionError("다른 프로그램이 쓰는 중")
            return real_remove(p)
        with mock.patch.object(store_csv.os, "remove", side_effect=remove):
            r = store_csv.prune_days(30, self.cfg, today=TODAY)
        self.assertTrue(os.path.exists(locked))
        self.assertEqual(r["failed"], 1)
        self.assertEqual(r["files"], len(self.old) - 1)
        self.assertIn("20260829_TOTAL.CSV", r["errors"][0])

    def test_지운_파일은_기억에서도_뺀다(self):
        """★안 빼면 같은 날을 다시 받을 때 '이미 쓴 줄' 로 착각하거나 목록에 옛 줄 수가 남는다."""
        p = self.old[0]
        store_csv.list_days(self.cfg)
        store_csv.read_day("20260829", self.cfg)
        store_csv._keys_cache[p] = {"x"}
        store_csv._fields_cache[p] = ["datetime"]
        store_csv.prune_days(30, self.cfg, today=TODAY)
        for c in (store_csv._rows_cache, store_csv._day_cache,
                  store_csv._keys_cache, store_csv._fields_cache):
            self.assertNotIn(p, c)
        self.assertNotIn("20260829", [x["day"] for x in store_csv.list_days(self.cfg)])

    def test_LLM_접미사_설정을_따른다(self):
        cfg = {"storage": {"daily_csv_dir": self.dir},
               "llm": {"per_minute": {"csv_suffix": "_JUDGE"}}}
        judge = os.path.join(self.dir, "20260101_JUDGE.CSV")
        _touch(judge)
        store_csv.prune_days(30, cfg, today=TODAY)
        self.assertFalse(os.path.exists(judge))

    def test_없는_폴더는_만들지_않는다(self):
        nowhere = os.path.join(self.dir, "없는폴더")
        cfg = {"storage": {"daily_csv_dir": nowhere}}
        self.assertEqual(store_csv.prune_days(30, cfg, today=TODAY)["files"], 0)
        self.assertEqual(store_csv.usage(cfg)["files"], 0)
        self.assertFalse(os.path.exists(nowhere), "정리가 빈 폴더를 만들었다")

    def test_쌓인_양(self):
        u = store_csv.usage(self.cfg)
        self.assertEqual(u["files"], 10)         # 지울 것 6 + 기간 안 4 (모르는 이름·하위 폴더는 안 셈)
        self.assertEqual(u["days"], 5)
        self.assertEqual(u["oldest"], "20250505")


class 서버_보관_기간_설정(unittest.TestCase):
    """flask 가 없는 곳에서도 돌도록 소스로 확인한다 (다른 서버 시험과 같은 방식)."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(APP, "server.py"), encoding="utf-8") as fh:
            cls.src = fh.read()

    def test_경로와_범위(self):
        self.assertIn('@app.route("/api/retention", methods=["GET", "POST"])', self.src)
        self.assertIn("RETENTION_MIN, RETENTION_MAX = 7, 3650", self.src)
        self.assertIn("보관 기간은 0(끔) 또는", self.src)

    def test_기본은_끔(self):
        m = re.search(r"def _retention_days\(\).*?return 0", self.src, re.S)
        self.assertTrue(m)
        self.assertIn('.get("retention_days", 0)', m.group(0))

    def test_하루_한_번_수집_루프에서_따로_떼어_돈다(self):
        loop = self.src[self.src.index("def _poll_loop()"):]
        loop = loop[:loop.index("\ndef ", 10)]
        self.assertIn("_retention_tick()", loop)
        tick = self.src[self.src.index("def _retention_tick()"):]
        tick = tick[:tick.index("\n\n\n")]
        self.assertIn('_RET.get("day") == today', tick)
        self.assertIn("threading.Thread(target=_run_retention", tick)
        self.assertLess(tick.index('_RET["day"] = today'), tick.index("keep <= 0"),
                        "끈 날도 '오늘은 봤다' 로 적어야 저장 직후 바로 지우지 않는다")

    def test_config_json_은_한_칸만_고친다(self):
        fn = self.src[self.src.index("def _persist_retention()"):]
        fn = fn[:fn.index("\n\n\n")]
        self.assertIn('st["retention_days"] = _retention_days()', fn)
        self.assertIn("os.replace(tmp, CONFIG_PATH)", fn)
        self.assertNotIn("disk = {", fn, "파일을 통째로 새로 쓰면 손으로 고친 설정이 날아간다")

    def test_ALL_과_FAB_전부(self):
        fn = self.src[self.src.index("def _retention_cfgs()"):]
        fn = fn[:fn.index("\n\n\n")]
        self.assertIn('["ALL"] + [x for x in fab_codes(CFG)', fn)


class 서버_보관_기간_실제로_부르기(unittest.TestCase):
    """flask 가 있으면 실제로 불러 본다 (현장 · 개발 PC)."""

    def setUp(self):
        try:
            import server                                   # noqa: F401
        except ImportError as e:                            # flask 없음
            self.skipTest(f"flask 없음: {e}")
        import lp_client
        import server
        self.server = server
        self.client = server.app.test_client()
        self.dir = tempfile.mkdtemp()
        self.st = server.CFG.setdefault("storage", {})
        self._saved = dict(self.st)
        self._fabs = server.fab_codes
        server.fab_codes = lambda cfg=None: []              # 이 시험은 ALL 폴더 하나로
        self.st["daily_csv_dir"] = self.dir
        self.st.pop("retention_days", None)
        self._cfg_path = lp_client.CONFIG_PATH
        fd, self.tmp_cfg = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"storage": {"daily_csv_dir": "data", "손으로": "고친 값"}}, f)
        lp_client.CONFIG_PATH = self.tmp_cfg
        self.lp = lp_client
        _touch(os.path.join(self.dir, "20200101_TOTAL.CSV"))
        _touch(os.path.join(self.dir, datetime.now().strftime("%Y%m%d") + "_TOTAL.CSV"))

    def tearDown(self):
        self.lp.CONFIG_PATH = self._cfg_path
        os.unlink(self.tmp_cfg)
        self.server.fab_codes = self._fabs
        self.st.clear()
        self.st.update(self._saved)
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_기본은_끔이고_미리보기만_한다(self):
        d = self.client.get("/api/retention").get_json()
        self.assertEqual(d["days"], 0)
        self.assertEqual(d["have"]["files"], 2)
        self.assertEqual(d["preview"]["files"], 0)
        p = self.client.get("/api/retention?days=30").get_json()
        self.assertEqual(p["preview"]["files"], 1)
        self.assertTrue(os.path.exists(os.path.join(self.dir, "20200101_TOTAL.CSV")))

    def test_범위_밖은_거절(self):
        for bad in (3, 5000, "x"):
            r = self.client.post("/api/retention", json={"days": bad, "save": True})
            self.assertEqual(r.status_code, 400, bad)

    def test_저장은_config_의_그_칸만_바꾸고_바로_지우지_않는다(self):
        r = self.client.post("/api/retention", json={"days": 30, "save": True})
        self.assertEqual(r.status_code, 200, r.get_json())
        with open(self.tmp_cfg, encoding="utf-8") as fh:
            disk = json.load(fh)
        self.assertEqual(disk["storage"]["retention_days"], 30)
        self.assertEqual(disk["storage"]["손으로"], "고친 값")
        self.assertTrue(os.path.exists(os.path.join(self.dir, "20200101_TOTAL.CSV")))

    def test_자동_정리는_하루_한_번_저장_직후에는_안_돈다(self):
        srv = self.server
        saved = dict(srv._RET)
        started = []
        try:
            with mock.patch.object(srv.threading, "Thread") as T:
                T.return_value.start.side_effect = lambda: started.append(1)
                srv._RET["day"] = None
                self.st["retention_days"] = 0
                srv._retention_tick()                  # 끔 — 안 돈다 (그래도 '오늘은 봤다')
                self.st["retention_days"] = 30         # 낮에 저장했다
                srv._retention_tick()
                self.assertEqual(started, [], "저장 직후 바로 지우면 안 된다")
                srv._RET["day"] = None                 # 날이 바뀌었다 (또는 서버를 켰다)
                srv._retention_tick()
                srv._retention_tick()
                self.assertEqual(started, [1], "하루에 한 번만")
        finally:
            srv._RET.clear()
            srv._RET.update(saved)

    def test_지금_정리(self):
        self.assertEqual(self.client.post("/api/retention", json={"run": True}).status_code,
                         400, "0(끔)이면 지우지 않는다")
        self.client.post("/api/retention", json={"days": 30, "save": True})
        d = self.client.post("/api/retention", json={"run": True}).get_json()
        self.assertEqual(d["ran"]["files"], 1)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "20200101_TOTAL.CSV")))
        self.assertEqual(d["have"]["files"], 1, "오늘 파일은 남는다")


class 정책_탭_카드(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(APP, "static", "dashboard.html"), encoding="utf-8") as fh:
            cls.html = fh.read()

    def test_카드와_칸(self):
        self.assertIn("과거 파일 정리 — 보관 기간", self.html)
        for i in ('id="rtrow"', 'id="rt-save"', 'id="rt-run"', 'id="rt-now"', 'id="rtnote"'):
            self.assertIn(i, self.html)

    def test_LLM_판단_모델_카드_앞(self):
        self.assertLess(self.html.index("과거 파일 정리 — 보관 기간 <span"),
                        self.html.index("LLM 판단 모델 <span"))

    def test_정책_탭을_열면_불러온다(self):
        m = re.search(r"b\.dataset\.tab==='policy'\)\{(.*?)\}", self.html, re.S)
        self.assertTrue(m)
        self.assertIn("initRetention();", m.group(1))

    def test_지우기_전에_묻는다(self):
        js = self.html[self.html.index("async function initRetention()"):]
        js = js[:js.index("\nfunction renderPolicy")]
        self.assertEqual(js.count("confirm("), 2, "저장 · 지금 정리 둘 다 물어야 한다")
        self.assertIn("되돌릴 수 없습니다", js)
        self.assertIn("/api/retention?days=", js, "묻기 전에 지울 것을 새로 센다")

    def test_새_디자인_없이_있는_모양을_쓴다(self):
        card = self.html[self.html.index("과거 파일 정리 — 보관 기간 <span"):]
        card = card[:card.index("LLM 판단 모델 <span")]
        self.assertNotIn("<style", card)
        self.assertIn('class="pol"', card)
        self.assertIn('class="act pri"', card)


if __name__ == "__main__":
    unittest.main()
