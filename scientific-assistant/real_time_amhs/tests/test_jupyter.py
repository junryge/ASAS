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


class 로그인_세션을_재사용한다(unittest.TestCase):
    """★파일 하나 받을 때마다 로그인을 다시 하고 있었다.

    기동 한 번에 일곱 개(ALL + FAB 다섯 + ML)를 받는데, login() 은 왕복 두 번
    (GET /login 으로 _xsrf, POST /login)이다. 내려받기 전에 왕복 열네 번을
    먼저 하고 있었다. 쿠키는 한 번 받으면 그대로 쓸 수 있다.
    """

    def setUp(self):
        import jupyter_csv as J
        self.J = J
        J._SESS.clear()
        self.c = {"base_url": "http://x", "password": "pw", "timeout_s": 5}
        self.calls = []

        def fake(c):
            self.calls.append(1)
            return object(), ""
        self._orig = J._login_fresh
        J._login_fresh = fake

    def tearDown(self):
        self.J._login_fresh = self._orig
        self.J._SESS.clear()

    def test_두_번째부터는_다시_로그인_안_한다(self):
        for _ in range(7):
            self.J.login(self.c)
        self.assertEqual(len(self.calls), 1,
                         "일곱 번 받는데 로그인을 %d번 했다" % len(self.calls))

    def test_비밀번호가_바뀌면_새로_로그인한다(self):
        """★주소만으로 묶었더니 비밀번호를 고쳐도 옛 세션을 썼다."""
        self.J.login(self.c)
        self.J.login(dict(self.c, password="다른것"))
        self.assertEqual(len(self.calls), 2)

    def test_비밀번호를_열쇠에_그대로_안_넣는다(self):
        self.J.login(self.c)
        for k in self.J._SESS:
            self.assertNotIn("pw", k, "열쇠에 비밀번호가 그대로 들어 있다")

    def test_버리면_다시_로그인한다(self):
        """쿠키는 만료된다 — 캐시만 두고 갱신을 안 두면 그때부터 영영 실패한다."""
        self.J.login(self.c)
        self.J._drop_session(self.c)
        self.J.login(self.c)
        self.assertEqual(len(self.calls), 2)

    def test_fresh_면_캐시를_무시한다(self):
        self.J.login(self.c)
        self.J.login(self.c, fresh=True)
        self.assertEqual(len(self.calls), 2)


class 세션을_나눠_써도_제_파일을_받는다(unittest.TestCase):
    """★로그인 세션을 재사용하게 고친 뒤, 시스템끼리 파일이 섞이지 않는지.

    ALL 과 FAB 다섯이 같은 서버·같은 비밀번호라 세션을 하나로 쓴다. 파일을
    가르는 것은 세션이 아니라 경로(sys_cfg 가 fab_path 로 갈아끼운다)인데,
    그 둘을 헷갈리면 모든 화면이 같은 파일을 보게 된다 — 값이 0 이나 남의
    FAB 점수로 보이는 사고다. 가짜 주피터를 띄워 끝까지 확인한다.
    """

    def setUp(self):
        import http.server
        import socketserver
        import threading
        import urllib.parse
        self.hits = []
        hits = self.hits

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                p = urllib.parse.unquote(self.path)
                hits.append(("GET", p))
                if p.startswith("/login"):
                    self.send_response(200)
                    self.send_header("Set-Cookie", "_xsrf=tok")
                    self.end_headers()
                    self.wfile.write(b"<html>login</html>")
                    return
                name = p.rsplit("/", 1)[-1]
                body = ("file,datetime,date,time,unified_risk_score,hot_area,reason\n"
                        f"{name},2026-09-12 00:00,2026-09-12,00:00,42,M16HUB,"
                        "발동: M16HUB[R-A_sus]\n").encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/csv")
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                hits.append(("POST", self.path))
                n = int(self.headers.get("Content-Length") or 0)
                self.rfile.read(n)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")

        self.srv = socketserver.TCPServer(("127.0.0.1", 0), H)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        import jupyter_csv as J
        self.J = J
        J._SESS.clear()
        self.cfg = {"source": {"jupyter": {
            "enabled": True, "base_url": f"http://127.0.0.1:{self.port}",
            "path": "/files/x/{day}_발동이벤트.csv",
            "fab_path": "/files/x/fab분리/{day}_발동이벤트_{fab}.csv",
            "fabs": {"M14": "M14", "M16HUB": "M16HUB"},
            "password": "pw", "timeout_s": 5, "save_raw": False}}}

    def tearDown(self):
        self.srv.shutdown()
        self.J._SESS.clear()

    def _get(self, s):
        from lp_client import sys_cfg
        c = self.cfg if s == "ALL" else sys_cfg(self.cfg, s)
        raw, err = self.J.download("20260912", c)
        self.assertFalse(err, f"{s}: {err}")
        return raw.decode().splitlines()[1].split(",")[0]

    def test_시스템마다_다른_파일을_받는다(self):
        got = {s: self._get(s) for s in ("ALL", "M14", "M16HUB")}
        self.assertTrue(got["ALL"].endswith("발동이벤트.csv"), got)
        self.assertIn("M14", got["M14"])
        self.assertIn("M16HUB", got["M16HUB"])
        self.assertNotEqual(got["M14"], got["M16HUB"], "FAB 파일이 섞였다")
        self.assertNotEqual(got["ALL"], got["M14"], "ALL 과 FAB 이 섞였다")

    def test_로그인은_한_번만_한다(self):
        for s in ("ALL", "M14", "M16HUB"):
            self._get(s)
        posts = [h for h in self.hits if h[0] == "POST"]
        self.assertEqual(len(posts), 1,
                         "세 번 받는데 로그인을 %d번 했다" % len(posts))


class 모르는_것을_0으로_채우지_않는다(unittest.TestCase):
    """★"실시간에 일부가 0으로 나온다" 의 원인.

    FAB 파일을 정규화할 때 area_score 가 비면 "0" 으로 채우고 있었다.
    그러면 **모르는 분이 화면에 '0점 정상' 으로 뜬다**. 모르는 것과 괜찮은
    것은 다르다 — fab_score 도 같은 이유로 근거 없는 FAB 은 아예 안 넣는다.
    더 나쁜 쪽은 area_score 컬럼이 아예 없을 때였다: 전체 점수가 그대로
    남아 M14 화면에 M16HUB 점수가 떴다.
    """

    def setUp(self):
        import jupyter_csv as J
        self.J = J

    def _one(self, **kw):
        r = {"hot_area": "M16HUB", "unified_risk_score": "55"}
        r.update(kw)
        return self.J._fab_rows([r], "M14")

    def test_값이_있으면_그_FAB_점수로_바꾼다(self):
        got = self._one(area_score="33")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["unified_risk_score"], "33")
        self.assertEqual(got[0]["hot_area"], "M14")
        self.assertEqual(got[0]["all_score"], "55", "전체 점수를 잃으면 안 된다")
        self.assertEqual(got[0]["all_hot_area"], "M16HUB")

    def test_빈_값을_0으로_채우지_않는다(self):
        for v in ("", "   ", None):
            got = self._one(area_score=v)
            self.assertEqual(got, [], "area_score=%r 을 0 으로 채웠다" % v)

    def test_버린_수를_센다(self):
        """조용히 사라지면 그게 더 나쁘다."""
        rows = [{"hot_area": "M16HUB", "unified_risk_score": "55", "area_score": v}
                for v in ("10", "", "20", "", "")]
        got = self.J._fab_rows(rows, "M14")
        self.assertEqual(len(got), 2)
        self.assertEqual(self.J._fab_rows.dropped, 3)

    def test_0_은_진짜_0_이니_남긴다(self):
        """빈 값과 0 은 다르다 — 0 은 '근거가 있고 0점' 이다."""
        got = self._one(area_score="0")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["unified_risk_score"], "0")

    def test_컬럼이_없으면_그_파일을_안_쓴다(self):
        """남의 FAB 점수를 보여 주느니 안 보여 주는 게 낫다.

        ★'컬럼이 없다' 와 '값이 전부 비었다' 는 둘 다 행 0개가 되지만 뜻이
          다르다. 앞은 파일이 틀린 것이고 뒤는 그 시간에 근거가 없는 것이다.
          fetch_day 가 그 둘을 dropped 로 가른다(오류 vs 경고).
        """
        self.J._fab_rows.dropped = 999
        self.assertEqual(self._one(), [])
        self.assertEqual(self.J._fab_rows.dropped, 999,
                         "컬럼이 없는데 '버렸다' 로 세면 경고 문구가 틀려진다")

    def test_값이_전부_비면_버린_수로_센다(self):
        self.assertEqual(self._one(area_score=""), [])
        self.assertEqual(self.J._fab_rows.dropped, 1)

    def test_전체_시스템은_안_건드린다(self):
        """_fab_rows 는 FAB 파일에만 쓴다 — ALL 은 이 길을 안 탄다."""
        import inspect
        src = inspect.getsource(self.J.fetch_day)
        self.assertIn('fab != "ALL"', src)
