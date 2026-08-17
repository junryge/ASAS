"""FAB 별 실시간 관제 — ALL 과 같은 구조로, 각 FAB 의 fab분리 CSV 를 쓴다.

★핵심 규칙 (실물 CSV 로 확인한 사실):
  · FAB 파일에도 unified_risk_score(전체 점수)와 hot_area(전체 기준,
    보통 M16HUB)가 **그대로** 들어 있다. 그 FAB 자신의 점수는 area_score.
  · 그래서 받는 순간 정규화한다 — area_score→unified_risk_score,
    hot_area→FAB 코드. 안 하면 M14 화면이 전체 점수로 등급을 매기고
    케이스가 M16HUB 로 찍힌다 (남의 데이터를 보게 된다).
  · 저장은 data/{FAB}/ 아래로 완전히 분리 — ALL 과 섞이면 안 된다.
"""
import json
import os
import re
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
from lp_client import fab_codes, load_config, sys_cfg

MOCK = os.path.join(util.BASE, "tests", "mock_jupyter.py")
PORT = 9917
PW = "테스트비번!1"
FABS = ["M14", "M14B", "M16A", "M16B", "M16HUB"]


class SysCfg(unittest.TestCase):
    """sys_cfg — 저장 위치·파일 경로만 바뀐 얕은 설정 뷰."""

    def setUp(self):
        self.cfg = deepcopy(load_config())
        self.cfg["storage"]["daily_csv_dir"] = "data"
        self.cfg["source"]["jupyter"]["fab_path"] = \
            "/files/x/fab분리/{day}_발동이벤트_{fab}.csv"
        self.cfg["source"]["jupyter"]["fabs"] = {f: f for f in FABS}

    def test_ALL_은_그대로(self):
        self.assertIs(sys_cfg(self.cfg, "ALL"), self.cfg)
        self.assertIs(sys_cfg(self.cfg, None), self.cfg)

    def test_저장이_전부_FAB_폴더로_갈라진다(self):
        c = sys_cfg(self.cfg, "M14")
        st = c["storage"]
        for key in ("daily_csv_dir", "dir", "cases", "reports"):
            self.assertIn(os.path.join("data", "M14"), st[key],
                          f"storage.{key} 가 data/M14 아래가 아닙니다: {st[key]}")
        # 원본 설정은 안 다친다
        self.assertEqual(self.cfg["storage"]["daily_csv_dir"], "data")

    def test_파일_경로는_fab_접미사로(self):
        c = sys_cfg(self.cfg, "M16B")
        self.assertEqual(c["source"]["jupyter"]["path"],
                         "/files/x/fab분리/{day}_발동이벤트_M16B.csv")

    def test_접미사는_config_로_바꿀_수_있다(self):
        """파일명이 화면 코드와 다르면 fabs 값 한 줄만 바꾸면 된다."""
        self.cfg["source"]["jupyter"]["fabs"]["M16HUB"] = "M14HUB"
        c = sys_cfg(self.cfg, "M16HUB")
        self.assertIn("_M14HUB.csv", c["source"]["jupyter"]["path"])

    def test_공유_설정은_같은_객체다(self):
        """★깊은 복사면 안 된다 — 대시보드에서 수집 주기를 바꾸면 FAB 도
        즉시 따라와야 한다. 실제로 analysis 쪽 deepcopy 버릇대로 만들었다가
        FAB 만 옛 주기로 얼어붙는 걸 이 테스트가 잡는다."""
        c = sys_cfg(self.cfg, "M14")
        self.assertIs(c["query"], self.cfg["query"])
        self.cfg["query"]["poll_interval_s"] = 12345
        self.assertEqual(c["query"]["poll_interval_s"], 12345)

    def test_fab_codes_는_config_순서(self):
        self.assertEqual(fab_codes(self.cfg), FABS)


class Normalize(unittest.TestCase):
    """받는 순간의 정규화 — 여기 한 곳이 전부다."""

    ROW = {"datetime": "2026-08-14 00:01", "unified_risk_score": "44",
           "unified_risk_level": "경계", "hot_area": "M16HUB",
           "area_score": "72", "area_level": "위험"}

    def test_FAB_점수와_구역으로_바뀐다(self):
        r = J._fab_rows([dict(self.ROW)], "M14")[0]
        self.assertEqual(r["unified_risk_score"], "72")   # area_score
        self.assertEqual(r["unified_risk_level"], "위험")
        self.assertEqual(r["hot_area"], "M14")
        # 원본은 all_* 로 남는다 (전체 대비 비교용)
        self.assertEqual(r["all_score"], "44")
        self.assertEqual(r["all_hot_area"], "M16HUB")
        self.assertEqual(r["all_level"], "경계")

    def test_area_score_가_없으면_전체_점수를_그대로_둔다(self):
        """파일이 이상해도 0점으로 뭉개지 않는다."""
        row = {"datetime": "2026-08-14 00:01", "unified_risk_score": "44",
               "hot_area": "M16HUB"}
        r = J._fab_rows([dict(row)], "M14")[0]
        self.assertEqual(r["unified_risk_score"], "44")
        self.assertEqual(r["hot_area"], "M14")

    def test_빈_area_score_는_0(self):
        r = J._fab_rows([{"area_score": "", "unified_risk_score": "44"}], "M14")[0]
        self.assertEqual(r["unified_risk_score"], "0")


def _up(port, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/login", timeout=1).read()
            return True
        except Exception:
            time.sleep(0.15)
    return False


class FabFetch(unittest.TestCase):
    """가짜 주피터로 끝단까지 — FAB 파일을 받아 data/{FAB}/ 에 쌓는다."""

    @classmethod
    def setUpClass(cls):
        env = dict(os.environ, MOCK_PW=PW)
        cls.srv = subprocess.Popen([sys.executable, MOCK, str(PORT)], env=env,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.STDOUT)
        if not _up(PORT):
            cls.srv.terminate()
            raise unittest.SkipTest("가짜 주피터 서버가 안 뜸")

    @classmethod
    def tearDownClass(cls):
        cls.srv.terminate()
        cls.srv.wait(timeout=5)

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rtfab")
        self.cfg = deepcopy(load_config())
        self.cfg["source"] = {"mode": "jupyter", "jupyter": {
            "enabled": True, "base_url": f"http://127.0.0.1:{PORT}",
            "path": "/files/x/{day}_발동이벤트.csv",
            "fab_path": "/files/x/fab분리/{day}_발동이벤트_{fab}.csv",
            "fabs": {f: f for f in FABS},
            "password": PW, "save_raw": False}}
        self.cfg.setdefault("storage", {})["daily_csv_dir"] = self.tmp
        self.cfg["storage"]["cases"] = os.path.join(self.tmp, "cases.json")
        self.cfg.setdefault("llm", {})["enabled"] = False

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_FAB_파일을_받아_자기_폴더에_쌓는다(self):
        c = sys_cfg(self.cfg, "M14")
        r = J.fetch_day("20260814", c, verbose=False)
        self.assertTrue(r.get("ok"), r.get("error"))
        p = os.path.join(self.tmp, "M14", "20260814_TOTAL.CSV")
        self.assertTrue(os.path.isfile(p), "data/M14/ 에 저장돼야 한다")
        # ALL 파일과 섞이지 않는다
        self.assertFalse(os.path.isfile(os.path.join(self.tmp, "20260814_TOTAL.CSV")))

    def test_받은_행이_정규화돼_있다(self):
        c = sys_cfg(self.cfg, "M16B")
        rows = J.fetch_day("20260814", c, verbose=False)["data"]
        self.assertTrue(rows)
        for r in rows:
            self.assertEqual(r["hot_area"], "M16B")
        # 전체 점수(44)가 아니라 그 FAB 의 area_score 가 스코어다
        scores = sorted(float(r["unified_risk_score"]) for r in rows)
        self.assertEqual(scores, [5.0, 55.0, 72.0, 88.0])
        self.assertTrue(all(r["all_score"] == "44" for r in rows))

    def test_케이스가_FAB_이름으로_잡힌다(self):
        """scan_once 까지 이어서 — 임계(50) 넘는 3행이 M16A 케이스가 된다."""
        from sentinel import CaseStore, scan_once
        c = sys_cfg(self.cfg, "M16A")
        store = CaseStore(c)
        res = scan_once(store, cfg=c)
        self.assertTrue(res.get("ok"), res.get("error"))
        # 오늘 파일이 mock 에 있으므로 fetch 는 되지만 행 날짜가 다르다 —
        # 날짜를 콕 집어 다시: fetch_day 데이터로 직접 스캔
        rows = J.fetch_day("20260814", c, verbose=False)["data"]
        res = scan_once(store, rows=rows, cfg=c)
        areas = {store.by_id(cid)["area"] for cid in res.get("cases") or []}
        self.assertEqual(areas, {"M16A"},
                         "케이스 area 는 hot_area(M16HUB)가 아니라 FAB 코드여야 한다")

    def test_ALL_은_그대로_통합_파일(self):
        r = J.fetch_day("20260811", self.cfg, verbose=False)
        self.assertTrue(r.get("ok"), r.get("error"))
        self.assertTrue(os.path.isfile(
            os.path.join(self.tmp, "20260811_TOTAL.CSV")))
        # ALL 행은 정규화 대상이 아니다
        self.assertNotIn("all_score", r["data"][0])


class FabMetrics(unittest.TestCase):
    """추이 그래프 지표 — 실제 컬럼명으로 표시돼야 한다.

    스코어만 예외로 area_score 를 그대로 두고(그 FAB 자기 점수라는 표시),
    나머지는 실제 AMOS 지표 컬럼명이다. 특히 반송시간은 구역마다
    QUE.TIME / QUE.LOAD 가 갈린다 — 여기서 틀리면 화면의 '실제지표' 칸이
    존재하지 않는 컬럼명을 보여준다.
    """

    def _amos(self, sys):
        from lp_client import _fab_groups
        gs = _fab_groups(sys)
        self.assertEqual([g["id"] for g in gs], ["amos", "csv"],
                         "ALL 과 같은 두 묶음(AMOS/CSV)이어야 한다")
        return {m["key"]: m["raw"] for m in gs[0]["metrics"]}, \
               {m["key"]: m["raw"] for m in gs[1]["metrics"]}

    def test_스코어는_area_score_그대로(self):
        for s in FABS:
            amos, csv = self._amos(s)
            self.assertEqual(amos["unified_risk_score"], "area_score")
            self.assertEqual(csv["unified_risk_score"], "area_score")

    def test_반송시간_실제_컬럼명(self):
        """★TIME/LOAD 구분 — 발동이벤트_요약.py 의 _RA_RAW 와 같은 표."""
        want = {"M16HUB": "M16HUB.QUE.TIME.AVGTOTALTIME1MIN",
                "M14":    "M14.QUE.LOAD.AVGLOADTIME1MIN",
                "M14B":   "M14B.QUE.TIME.AVGTOTALTIME1MIN",
                "M16A":   "M16A.QUE.LOAD.AVGLOADTIME1MIN",
                "M16B":   "M16B.QUE.LOAD.AVGLOADTIME1MIN"}
        for s, raw in want.items():
            amos, _ = self._amos(s)
            self.assertEqual(amos[f"{s}_ra"], raw)

    def test_SLA_소터_OHT_실제_컬럼명(self):
        amos, _ = self._amos("M16B")
        self.assertEqual(amos["sla_M16B"], "M16B.QUE.ALL.TRANSPORT4MINOVERRATIO")
        self.assertEqual(amos["sorter_M16B"], "M16B.SORTER.ABN.SORTERWAITCOUNTOVER")
        self.assertEqual(amos["M16B_rd_oht"], "M16B.QUE.OHT.OHTUTIL")

    def test_허브룸_전용_지표(self):
        amos, _ = self._amos("M16HUB")
        self.assertEqual(amos["M16HUB_rd_fab"], "M16HUB.STRATE.ALL.FABSTORAGERATIO")
        self.assertEqual(amos["M16HUB_stb_util"], "M16HUB.STRATE.STB.3F_STORAGE_UTIL")
        self.assertEqual(amos["M16HUB_rev_count"], "M16HUB.QUE.LFT.3F_LFT_REVERSALCNT")
        self.assertNotIn("M16HUB_rd_oht", amos, "허브룸엔 rd_oht 가 없다")

    def test_CSV_묶음은_컬럼명_그대로(self):
        _, csv = self._amos("M14")
        self.assertEqual(csv["M14_ra"], "M14_ra")
        self.assertEqual(csv["sla_M14"], "sla_M14")
        self.assertIn("M14_cnv_skew", csv, "cnv_skew 는 M14 에만 있는 실제 컬럼")

    def test_sys_cfg_가_묶음을_붙인다(self):
        cfg = deepcopy(load_config())
        c = sys_cfg(cfg, "M16A")
        gs = c["ui"]["metric_groups"]
        self.assertEqual([g["id"] for g in gs], ["amos", "csv"])
        keys = {m["key"] for m in gs[0]["metrics"]}
        self.assertIn("M16A_ra", keys)
        self.assertIn("M16A_sorter_fail", keys)


class DashboardSync(unittest.TestCase):
    """화면 목록과 서버(config) 목록이 어긋나면 고르는 순간 빈 화면이 된다."""

    def test_화면_SYSTEMS_와_config_fabs_가_같다(self):
        with open(os.path.join(util.BASE, "static", "dashboard.html"),
                  encoding="utf-8") as f:
            js = f.read().split("<script>", 1)[1]
        block = js.split("const SYSTEMS", 1)[1].split("];", 1)[0]
        codes = re.findall(r"code:\s*'([^']+)'", block)
        self.assertEqual(codes[0], "ALL")
        with open(os.path.join(util.BASE, "config.json"),
                  encoding="utf-8-sig") as f:
            fabs = list(json.load(f)["source"]["jupyter"]["fabs"].keys())
        self.assertEqual(codes[1:], fabs,
                         "dashboard SYSTEMS 와 config.source.jupyter.fabs 불일치")


if __name__ == "__main__":
    unittest.main()
