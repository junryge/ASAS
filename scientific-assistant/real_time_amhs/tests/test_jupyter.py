"""주피터 CSV 수집 — 로그프레소 없이 실시간으로 받는 경로.

가짜 주피터 서버(진짜와 같은 로그인 흐름)로 끝단까지 확인한다.
  GET  /login → _xsrf 쿠키 → POST /login → 세션 쿠키 → GET /files/…csv
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from copy import deepcopy

from . import util  # noqa: F401
import jupyter_csv as J
import sentinel
from jupyter_csv import backfill as backfill_days
from lp_client import load_config

MOCK = os.path.join(util.BASE, "tests", "mock_jupyter.py")
FIXTURE = os.path.join(util.BASE, "fixtures", "발동이벤트_샘플.csv")
PORT = 9913
PW = "테스트비번!1"


def _up(port, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/login", timeout=1).read()
            return True
        except Exception:
            time.sleep(0.15)
    return False


@unittest.skipUnless(os.path.isfile(FIXTURE), "샘플 CSV 없음")
class JupyterFetch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = dict(os.environ, MOCK_PW=PW, MOCK_CSV=FIXTURE)
        cls.srv = subprocess.Popen([sys.executable, MOCK, str(PORT)], env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        if not _up(PORT):
            cls.srv.terminate()
            raise unittest.SkipTest("가짜 주피터 서버가 안 뜸")

    @classmethod
    def tearDownClass(cls):
        cls.srv.terminate()
        cls.srv.wait(timeout=5)

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rtjup")
        # ★load_config() 는 **캐시된 같은 dict** 를 돌려준다. 그대로 고치면
        #   프로세스 전체(다른 테스트 포함)가 오염된다. 반드시 복사해서 쓴다.
        self.cfg = deepcopy(load_config())
        self.cfg["source"] = {"mode": "jupyter", "jupyter": {
            "enabled": True, "base_url": f"http://127.0.0.1:{PORT}",
            "path": "/files/x/{day}_발동이벤트.csv", "password": PW,
            "save_raw": True}}
        self.cfg.setdefault("storage", {})["daily_csv_dir"] = self.tmp
        self.cfg.setdefault("llm", {})["enabled"] = False

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_로그인해서_받는다(self):
        raw, err = J.download("20260811", self.cfg)
        self.assertEqual(err, "")
        self.assertGreater(len(raw), 1000)
        self.assertNotIn(b"<html", raw[:200].lower())

    def test_비밀번호가_틀리면_알려준다(self):
        bad = deepcopy(self.cfg)
        bad["source"] = {"mode": "jupyter",
                         "jupyter": dict(self.cfg["source"]["jupyter"],
                                         password="틀림")}
        raw, err = J.download("20260811", bad)
        self.assertIsNone(raw)
        self.assertIn("비밀번호", err)

    def test_HTML_이_오면_CSV_로_안_받는다(self):
        """로그인 실패 시 로그인 페이지가 온다 — 조용히 넘기면 안 된다."""
        c = J.cfg_of(self.cfg)
        self.assertFalse(J.parse_csv(b"<!DOCTYPE html><html>login</html>", c))

    def test_날짜_파일이_없으면_404_로_알려준다(self):
        raw, err = J.download("19990101", self.cfg)
        self.assertIsNone(raw)
        self.assertIn("404", err)

    def test_받아서_CSV_에_저장한다(self):
        r = J.fetch_day("20260811", self.cfg, verbose=False)
        self.assertTrue(r["ok"], r.get("error"))
        self.assertEqual(r["written"], r["rows"])
        self.assertTrue(os.path.isfile(
            os.path.join(self.tmp, "20260811_TOTAL.CSV")))

    def test_또_받아도_중복이_안_쌓인다(self):
        """★매 폴링마다 통째로 받는다 — 중복을 걸러야 증분 수집이 된다."""
        a = J.fetch_day("20260811", self.cfg, verbose=False)
        b = J.fetch_day("20260811", self.cfg, verbose=False)
        self.assertEqual(b["written"], 0)
        self.assertEqual(b["skipped"], a["rows"])

    def test_컬럼이_안_깎인다(self):
        """예측기가 만든 143컬럼(룰별 점수 45개 포함)이 그대로 남아야 한다."""
        r = J.fetch_day("20260811", self.cfg, verbose=False)
        rows = r["data"]
        self.assertGreaterEqual(len(rows[0]), 140)
        self.assertEqual(sum(1 for k in rows[0] if "_pts_" in k), 45)
        for k in ("unified_risk_score", "hot_area", "reason", "datetime"):
            self.assertIn(k, rows[0])

    def test_원본을_그대로_남긴다(self):
        r = J.fetch_day("20260811", self.cfg, verbose=False)
        self.assertTrue(os.path.isfile(r["raw_path"]))
        with open(FIXTURE, "rb") as f:
            src = f.read()
        with open(r["raw_path"], "rb") as f:
            self.assertEqual(f.read(), src)

    def test_scan_once_가_주피터로_돈다(self):
        store = sentinel.CaseStore(self.cfg)
        res = sentinel.scan_once(store, cfg=self.cfg)
        self.assertTrue(res["ok"], res.get("error"))
        self.assertEqual(res["source"], "jupyter")
        self.assertGreater(res["rows"], 0)

    def test_받은_행을_그대로_쓴다(self):
        """파일명 날짜와 행의 날짜가 달라도(자정 전후) 0행이 되면 안 된다."""
        store = sentinel.CaseStore(self.cfg)
        res = sentinel.scan_once(store, cfg=self.cfg)
        self.assertGreater(res["rows"], 0, "받아 놓고 못 읽었다")


class SourceMode(unittest.TestCase):
    def test_기본은_로그프레소(self):
        self.assertEqual(sentinel.source_mode({"source": {}}), "logpresso")
        self.assertEqual(sentinel.source_mode({"source": {"mode": ""}}), "logpresso")

    def test_jupyter_로_바꿀_수_있다(self):
        self.assertEqual(sentinel.source_mode(
            {"source": {"mode": "jupyter"}}), "jupyter")

    def test_enabled_false_면_로그프레소로_되돌아간다(self):
        self.assertEqual(sentinel.source_mode(
            {"source": {"mode": "jupyter",
                        "jupyter": {"enabled": False}}}), "logpresso")

    def test_모르는_값은_로그프레소(self):
        self.assertEqual(sentinel.source_mode({"source": {"mode": "이상한값"}}),
                         "logpresso")


class UrlHelper(unittest.TestCase):
    REAL = ("http://aiu-amhas-prediction-que.aipp01.skhynix.com/files/pjt_shared_pool/"
            "job/m16a_hubroom_event_prediction/predict_tobe/20260811_발동이벤트.csv"
            "?_xsrf=2|4890535b|8e263ee2342f25cb291d1a91b315563f|1784093584")

    def test_브라우저_URL_에서_설정값을_뽑는다(self):
        base, path = J.split_url(self.REAL)
        self.assertEqual(base, "http://aiu-amhas-prediction-que.aipp01.skhynix.com")
        self.assertIn("{day}", path)
        self.assertNotIn("_xsrf", path)      # 세션 것이라 떼어낸다

    def test_한글_파일명을_인코딩한다(self):
        url = J.file_url("20260811", {
            "base_url": "http://x", "path": "/files/{day}_발동이벤트.csv"})
        self.assertIn("20260811_%EB%B0%9C", url)
        self.assertNotIn("발동", url)

    def test_설정이_비면_알려준다(self):
        with self.assertRaises(ValueError):
            J.file_url("20260811", {"base_url": "", "path": ""})


class KeysCache(unittest.TestCase):
    """중복 판정 캐시 — 실시간 관제가 데이터를 조용히 버리면 안 된다.

    ★예전엔 캐시 키가 **날짜**였다. 저장 폴더가 바뀌거나 파일이 지워지면
      '이미 있다' 고 착각해 새 파일에 한 줄도 안 쓰였다.
    """

    ROW = {"datetime": "2026-08-11 00:00", "hot_area": "M16HUB",
           "unified_risk_score": "31", "file": "a.csv"}

    def _cfg(self, d):
        c = deepcopy(load_config())
        c.setdefault("storage", {})["daily_csv_dir"] = d
        return c

    def test_저장_폴더가_바뀌면_새로_쓴다(self):
        import store_csv
        a, b = tempfile.mkdtemp(prefix="ka"), tempfile.mkdtemp(prefix="kb")
        try:
            r1 = store_csv.append_rows([dict(self.ROW)], self._cfg(a))
            r2 = store_csv.append_rows([dict(self.ROW)], self._cfg(b))
            self.assertEqual(r1["written"], 1)
            self.assertEqual(r2["written"], 1, "폴더가 다른데 중복으로 버렸다")
        finally:
            shutil.rmtree(a, ignore_errors=True)
            shutil.rmtree(b, ignore_errors=True)

    def test_같은_폴더면_중복을_거른다(self):
        import store_csv
        d = tempfile.mkdtemp(prefix="kc")
        try:
            cfg = self._cfg(d)
            self.assertEqual(store_csv.append_rows([dict(self.ROW)], cfg)["written"], 1)
            self.assertEqual(store_csv.append_rows([dict(self.ROW)], cfg)["written"], 0)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_파일이_지워지면_다시_쓴다(self):
        """외부에서 CSV 를 지웠는데 캐시 때문에 영원히 안 쓰이면 안 된다."""
        import store_csv
        d = tempfile.mkdtemp(prefix="kd")
        try:
            cfg = self._cfg(d)
            store_csv.append_rows([dict(self.ROW)], cfg)
            os.remove(os.path.join(d, "20260811_TOTAL.CSV"))
            self.assertEqual(store_csv.append_rows([dict(self.ROW)], cfg)["written"], 1)
        finally:
            shutil.rmtree(d, ignore_errors=True)


class WidenColumns(unittest.TestCase):
    """컬럼이 늘어나면 파일을 넓혀서 다시 쓴다.

    ★로그프레소(90컬럼)로 만들어진 그날 파일에 주피터(143컬럼) 행이 들어오면,
      예전엔 DictWriter(extrasaction="ignore") 가 새 컬럼 53개를 **아무 말 없이
      버렸다**. 룰별 점수(*_pts_*) 45개가 통째로 사라진다.
    """

    OLD = {"datetime": "2026-08-11 00:00", "hot_area": "M16HUB",
           "unified_risk_score": "31", "file": "a.csv"}
    NEW = {"datetime": "2026-08-11 00:01", "hot_area": "M16HUB",
           "unified_risk_score": "62", "file": "a.csv",
           "stage": "3", "M16HUB_pts_RA": "25", "M16HUB_pts_RC": "10",
           "continuity_min": "2"}

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="widen")
        self.cfg = deepcopy(load_config())
        self.cfg.setdefault("storage", {})["daily_csv_dir"] = self.tmp
        self.path = os.path.join(self.tmp, "20260811_TOTAL.CSV")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _read(self):
        import csv as _csv
        with open(self.path, encoding="utf-8-sig", newline="") as f:
            return list(_csv.DictReader(f))

    def test_새_컬럼이_안_버려진다(self):
        import store_csv
        store_csv.append_rows([dict(self.OLD)], self.cfg)
        store_csv.append_rows([dict(self.NEW)], self.cfg)
        rows = self._read()
        self.assertEqual(len(rows), 2)
        for k in ("stage", "M16HUB_pts_RA", "M16HUB_pts_RC", "continuity_min"):
            self.assertIn(k, rows[1], f"{k} 가 버려졌다")
        self.assertEqual(rows[1]["M16HUB_pts_RA"], "25")

    def test_기존_행은_빈칸으로_남는다(self):
        import store_csv
        store_csv.append_rows([dict(self.OLD)], self.cfg)
        store_csv.append_rows([dict(self.NEW)], self.cfg)
        rows = self._read()
        self.assertEqual(rows[0]["unified_risk_score"], "31")   # 기존 값 보존
        self.assertEqual(rows[0]["M16HUB_pts_RA"], "")          # 새 컬럼은 빈칸

    def test_컬럼이_같으면_다시_쓰지_않는다(self):
        import store_csv
        store_csv.append_rows([dict(self.OLD)], self.cfg)
        before = os.path.getmtime(self.path)
        time.sleep(0.02)
        store_csv.append_rows([dict(self.OLD, datetime="2026-08-11 00:02")], self.cfg)
        rows = self._read()
        self.assertEqual(len(rows[0]), len(self.OLD))
        self.assertEqual(len(rows), 2)
        self.assertGreaterEqual(os.path.getmtime(self.path), before)


@unittest.skipUnless(os.path.isfile(FIXTURE), "샘플 CSV 없음")
class Backfill(unittest.TestCase):
    """과거 날짜 한꺼번에 받기 — 없는 날은 건너뛰고 계속해야 한다."""

    @classmethod
    def setUpClass(cls):
        env = dict(os.environ, MOCK_PW=PW, MOCK_CSV=FIXTURE)
        cls.srv = subprocess.Popen([sys.executable, MOCK, str(PORT + 1)], env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        if not _up(PORT + 1):
            cls.srv.terminate()
            raise unittest.SkipTest("가짜 주피터 서버가 안 뜸")

    @classmethod
    def tearDownClass(cls):
        cls.srv.terminate()
        cls.srv.wait(timeout=5)

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bf")
        self.cfg = deepcopy(load_config())
        self.cfg["source"] = {"mode": "jupyter", "jupyter": {
            "enabled": True, "base_url": f"http://127.0.0.1:{PORT + 1}",
            "path": "/files/x/{day}_발동이벤트.csv", "password": PW}}
        self.cfg.setdefault("storage", {})["daily_csv_dir"] = self.tmp

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_구간을_받는다(self):
        r = backfill_days(["20260809", "20260810", "20260811"], self.cfg)
        self.assertTrue(r["ok"], r["failed"])
        self.assertEqual(len(r["days"]), 3)
        self.assertGreater(r["written"], 0)

    def test_없는_날짜는_건너뛰고_계속한다(self):
        """중간에 파일 없는 날이 있어도 멈추면 안 된다."""
        r = backfill_days(["19990101", "20260811", "19990102"], self.cfg)
        self.assertTrue(r["ok"], r["failed"])
        self.assertEqual(r["days"], ["20260811"])
        self.assertEqual(len(r["missing"]), 2)


@unittest.skipUnless(os.path.isfile(FIXTURE), "샘플 CSV 없음")
class ListDays(unittest.TestCase):
    """서버에 어느 날짜가 있는지 — 과거를 받기 전에 이걸 먼저 봐야 헛돌지 않는다."""

    @classmethod
    def setUpClass(cls):
        env = dict(os.environ, MOCK_PW=PW, MOCK_CSV=FIXTURE)
        cls.srv = subprocess.Popen([sys.executable, MOCK, str(PORT + 2)], env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        if not _up(PORT + 2):
            cls.srv.terminate()
            raise unittest.SkipTest("가짜 주피터 서버가 안 뜸")

    @classmethod
    def tearDownClass(cls):
        cls.srv.terminate()
        cls.srv.wait(timeout=5)

    def _cfg(self, path="/files/x/{day}_발동이벤트.csv"):
        c = deepcopy(load_config())
        c["source"] = {"mode": "jupyter", "jupyter": {
            "enabled": True, "base_url": f"http://127.0.0.1:{PORT + 2}",
            "path": path, "password": PW}}
        c.setdefault("storage", {})["daily_csv_dir"] = tempfile.mkdtemp(prefix="ld")
        return c

    def test_날짜_목록을_받는다(self):
        items, err = J.list_days(self._cfg())
        self.assertEqual(err, "")
        self.assertEqual([i["day"] for i in items],
                         ["20260809", "20260810", "20260811"])

    def test_CSV_아닌_파일은_뺀다(self):
        items, _ = J.list_days(self._cfg())
        self.assertTrue(all(i["name"].endswith(".csv") for i in items))

    def test_files_접두를_떼고_목록_API_를_부른다(self):
        """/files/… 는 다운로드 경로다. 목록은 /api/contents/… 를 쓴다."""
        items, err = J.list_days(self._cfg("/files/pjt/job/{day}_발동이벤트.csv"))
        self.assertEqual(err, "", err)
        self.assertTrue(items)

    def test_설정이_비면_알려준다(self):
        c = deepcopy(load_config())
        c["source"] = {"mode": "jupyter", "jupyter": {"base_url": "", "path": ""}}
        items, err = J.list_days(c)
        self.assertEqual(items, [])
        self.assertIn("base_url", err)


if __name__ == "__main__":
    unittest.main()
