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


if __name__ == "__main__":
    unittest.main()
