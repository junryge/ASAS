"""출처를 주피터로 두면 **로그프레소를 한 번도 안 친다**.

★실제로 이랬다 — config 를 jupyter 로 바꿔도 기동 확보(_bootstrap_today)와
  리포트 재조회가 각자 fetch_amos() 를 직접 불러서 로그프레소를 쳤다.
  확보 경로가 여러 군데로 갈라져 있으면 한 곳만 고쳐도 티가 안 난다.

그래서 여기서는 fetch_amos 를 **터지게 바꿔 놓고** 각 경로를 돌린다.
로그프레소를 조금이라도 건드리면 즉시 실패한다.
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
import lp_query
import sentinel
from lp_client import load_config

MOCK = os.path.join(util.BASE, "tests", "mock_jupyter.py")
FIXTURE = os.path.join(util.BASE, "fixtures", "발동이벤트_샘플.csv")
PORT = 9921
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


class _Tripwire(Exception):
    """로그프레소를 쳤다 — 주피터 모드에선 있으면 안 된다."""


@unittest.skipUnless(os.path.isfile(FIXTURE), "샘플 CSV 없음")
class NoLogpressoInJupyterMode(unittest.TestCase):
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
        self.tmp = tempfile.mkdtemp(prefix="src")
        self.cfg = deepcopy(load_config())
        self.cfg["source"] = {"mode": "jupyter", "jupyter": {
            "enabled": True, "base_url": f"http://127.0.0.1:{PORT}",
            "path": "/files/x/{day}_발동이벤트.csv", "password": PW}}
        self.cfg.setdefault("storage", {})["daily_csv_dir"] = self.tmp
        self.cfg.setdefault("llm", {})["enabled"] = False

        # ★지뢰 — 로그프레소를 부르면 터진다
        self._real = lp_query.fetch_amos

        def boom(*a, **k):
            raise _Tripwire("주피터 모드인데 로그프레소를 쳤습니다")
        lp_query.fetch_amos = boom
        import collect
        self._real_c = collect.fetch_amos
        collect.fetch_amos = boom
        self._collect = collect

    def tearDown(self):
        lp_query.fetch_amos = self._real
        self._collect.fetch_amos = self._real_c
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_구간_확보(self):
        r = self._collect.collect("20260811000000", "20260811235959",
                                  self.cfg, verbose=False)
        self.assertTrue(r["ok"], r.get("error"))
        self.assertEqual(r["source"], "jupyter")
        self.assertGreater(r["rows"], 0)

    def test_하루_확보(self):
        r = self._collect.collect_day("20260811", self.cfg)
        self.assertTrue(r["ok"], r.get("error"))
        self.assertEqual(r["source"], "jupyter")

    def test_기동_확보(self):
        """서버 기동 때 한 번 도는 자리 — 여기가 로그프레소를 치고 있었다."""
        import server
        old_cfg = server.CFG
        server.CFG = self.cfg
        try:
            server._bootstrap_today()
        finally:
            server.CFG = old_cfg
        self.assertIsNot(server.STATE.get("bootstrap"), None)

    def test_스캔(self):
        store = sentinel.CaseStore(self.cfg)
        res = sentinel.scan_once(store, cfg=self.cfg)
        self.assertTrue(res["ok"], res.get("error"))
        self.assertEqual(res["source"], "jupyter")

    def test_리포트_구간조회(self):
        """저장분이 없을 때 리포트가 직접 로그프레소를 치던 자리."""
        from report import cases_from_query
        cases, err = cases_from_query("20260811000000", "20260811235959", self.cfg)
        self.assertIsNone(err, err)
        self.assertIsInstance(cases, list)

    def test_일일_리포트(self):
        """저장분이 없으면 그 날짜를 확보한 뒤 만든다 — 여기도 로그프레소였다."""
        from report import build_day_report
        cfg = deepcopy(self.cfg)
        cfg["llm"]["enabled"] = False
        rep = build_day_report("20260811", cfg, use_llm=False)
        self.assertIsInstance(rep, dict)

    def test_지뢰가_진짜_터지는지(self):
        """이 테스트가 의미 있으려면 지뢰가 실제로 작동해야 한다."""
        with self.assertRaises(_Tripwire):
            lp_query.fetch_amos(from_dt="1", to_dt="2")


if __name__ == "__main__":
    unittest.main()
