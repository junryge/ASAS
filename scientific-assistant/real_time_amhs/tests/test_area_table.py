"""관제 목록의 **FAB 다섯 점수 컬럼** — fab_score.area_table().

화면이 요구한 것: ALL 목록에 종합점수 옆으로 HI_FAB 과 FAB 다섯의
area_score 를 같이 세운다.

★이 파일이 지키는 것은 '빠르다' 가 아니라 **어느 수를 보여주는가** 다.
  · 다섯 점수의 원본은 FAB 분리 파일의 area_score 다 (예측기가 적어 준 값).
    없을 때만 통합 파일의 배점 합으로 되계산한다 — compare() 와 같은 순서.
  · 모르는 FAB 은 **0 이 아니라 빈 칸**이다. 0 으로 채우면 화면이 그 FAB 을
    '정상' 으로 읽는다.
  · 남의 FAB 점수를 집어오면 안 된다 (M14 분리 파일의 area_score 는 M14 것).
"""
import csv
import os
import re
import shutil
import tempfile
import unittest
from copy import deepcopy

from . import util  # noqa: F401
import fab_score as F
import store_csv
from lp_client import load_config

DAY = "20260811"
FABS = ["M14", "M14B", "M16A", "M16B", "M16HUB"]


def _all_row(minute, pts):
    """통합(ALL) 파일 한 행 — {FAB}_pts_RA 로 배점을 준다."""
    r = {"datetime": f"2026-08-11 00:{minute:02d}", "unified_risk_score": "31",
         "hot_area": "M16HUB"}
    for f, v in pts.items():
        r[f"{f}_pts_RA"] = str(v)
        r[f"{f}_score"] = str(v)
    return r


def _write(path, rows, cols):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


class AreaTable(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rtarea")
        self.cfg = deepcopy(load_config())
        self.cfg["storage"]["daily_csv_dir"] = self.tmp
        self.rows = [_all_row(0, {"M14": 5, "M14B": 5, "M16A": 15,
                                  "M16B": 10, "M16HUB": 25})]
        cols = ["datetime", "unified_risk_score", "hot_area"] + \
               [f"{f}_pts_RA" for f in FABS] + [f"{f}_score" for f in FABS]
        _write(store_csv.day_path(DAY, self.cfg), self.rows, cols)
        store_csv._day_cache.clear()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        store_csv._day_cache.clear()

    def _fab_file(self, fab, area, level=""):
        """FAB 분리 파일 하나 놓기 — data/{FAB}/{day}_TOTAL.CSV"""
        from lp_client import sys_cfg
        p = store_csv.day_path(DAY, sys_cfg(self.cfg, fab))
        _write(p, [{"datetime": "2026-08-11 00:00", "area_score": str(area),
                    "area_level": level}],
               ["datetime", "area_score", "area_level"])
        store_csv._day_cache.clear()

    def _one(self, day=DAY):
        t = F.area_table(self.rows, day=day, cfg=self.cfg)
        return t, t["rows"]["2026-08-11T00:00:00"]

    # ── 되계산 (분리 파일이 없을 때) ────────────────────────────────
    def test_분리파일이_없으면_통합파일_배점으로_되계산한다(self):
        _t, r = self._one()
        # raw 25 × 100 ÷ 분모 70 = 36
        self.assertEqual(r["s"]["M16HUB"], 36)
        self.assertEqual(r["s"]["M14"], 7)

    def test_되계산도_다섯_FAB_을_모두_채운다(self):
        _t, r = self._one()
        self.assertEqual(sorted(r["s"]), sorted(FABS))

    # ── 분리 파일 우선 ──────────────────────────────────────────────
    def test_FAB_분리파일의_area_score_가_되계산보다_우선한다(self):
        self._fab_file("M16HUB", 88)
        _t, r = self._one()
        self.assertEqual(r["s"]["M16HUB"], 88,
                         "예측기가 적어 준 area_score 를 그대로 써야 한다")
        self.assertEqual(r["s"]["M14"], 7, "나머지는 되계산 그대로")

    def test_다른_FAB_을_보는_중에도_다섯을_다_읽어온다(self):
        """M14 화면에서도 다섯 점수가 나와야 한다 — 원본이 분리 파일이라
        지금 보는 시스템과 무관하게 읽을 수 있다."""
        for f, v in zip(FABS, (11, 22, 33, 44, 55)):
            self._fab_file(f, v)
        # rows 를 M14 분리 파일 행처럼 (남의 FAB 컬럼이 하나도 없는 행) 줘도
        fabrow = [{"datetime": "2026-08-11 00:00", "area_score": "11",
                   "unified_risk_score": "31"}]
        t = F.area_table(fabrow, day=DAY, cfg=self.cfg)
        r = t["rows"]["2026-08-11T00:00:00"]
        self.assertEqual([r["s"][f] for f in FABS], [11, 22, 33, 44, 55])
        self.assertEqual(r["hi"], "M16HUB")

    # ── 오염 방지 ──────────────────────────────────────────────────
    def test_남의_FAB_점수를_집어오지_않는다(self):
        """M14 분리 파일 행의 area_score 는 M14 것이다. 그 행에서 M16A 를
        물으면 _stored_area 가 area_score 로 물러서서 M14 점수를 M16A 것으로
        집어왔다 — 그러면 다섯 칸이 전부 같은 수가 된다."""
        fabrow = [{"datetime": "2026-08-11 00:00", "area_score": "77",
                   "area_level": "위험", "hot_area": "M14",
                   "unified_risk_score": "31"}]
        t = F.area_table(fabrow, day=None, cfg=self.cfg)   # 분리 파일 안 읽음
        r = t["rows"]["2026-08-11T00:00:00"]
        self.assertNotIn("M16A", r["s"], "근거 없는 FAB 은 비어 있어야 한다")
        self.assertEqual(r["s"], {})

    def test_모르는_FAB_은_0_이_아니라_빠진다(self):
        """0 으로 채우면 화면이 '그 FAB 정상' 으로 읽는다."""
        t = F.area_table([{"datetime": "2026-08-11 00:00"}], day=None, cfg=self.cfg)
        r = t["rows"]["2026-08-11T00:00:00"]
        self.assertEqual(r["s"], {})
        self.assertEqual(r["hi"], "")
        self.assertEqual(r["hi_score"], 0)

    # ── HI_FAB ────────────────────────────────────────────────────
    def test_HI_FAB_은_제일_높은_FAB(self):
        _t, r = self._one()
        self.assertEqual(r["hi"], "M16HUB")
        self.assertEqual(r["hi_score"], 36)

    def test_HI_FAB_은_통합파일의_hot_area_와_같다(self):
        """예측기가 지목한 hot_area 와 우리가 고른 최고점이 어긋나면
        둘 중 하나가 틀린 것이다."""
        _t, r = self._one()
        self.assertEqual(r["hi"], self.rows[0]["hot_area"])

    def test_다_0_이면_HI_FAB_은_비운다(self):
        rows = [_all_row(0, {f: 0 for f in FABS})]
        t = F.area_table(rows, day=None, cfg=self.cfg)
        r = t["rows"]["2026-08-11T00:00:00"]
        self.assertEqual(r["hi"], "", "아무 데도 안 걸린 분에 FAB 을 지목하면 오보다")

    # ── 등급·컷 ───────────────────────────────────────────────────
    def test_FAB_마다_자기_컷을_준다(self):
        self.cfg.setdefault("grade", {}).setdefault("by_sys", {})["M14"] = \
            {"warn": 40, "danger": 50, "critical": 60}
        t, _r = self._one()
        self.assertEqual(t["cuts"]["M14"]["warn"], 40)
        self.assertNotEqual(t["cuts"]["M16A"]["warn"], 40,
                            "한 FAB 의 컷이 다른 FAB 에 번지면 안 된다")

    def test_예측기_등급이_컷_판정과_다르면_알려준다(self):
        self._fab_file("M16HUB", 30, level="위험")     # 30 점인데 위험이라고?
        _t, r = self._one()
        self.assertEqual(r["lv"]["M16HUB"], "위험",
                         "우리가 조용히 다시 매기면 등급 기준이 두 벌이 된다")

    def test_예측기_등급이_같으면_싣지_않는다(self):
        self._fab_file("M16HUB", 30, level="정상")     # 컷대로면 30 은 정상
        _t, r = self._one()
        self.assertNotIn("M16HUB", r.get("lv", {}),
                         "같은 값을 행마다 실으면 하루치가 그만큼 무거워진다")

    def test_FAB_목록은_설정_순서를_따른다(self):
        t, _r = self._one()
        self.assertEqual(t["fabs"], F.fabs(self.cfg))


class FeedWiring(unittest.TestCase):
    """/api/feed 가 area_table 결과를 행에 붙일 때 쓰는 **키가 맞는가**.

    서버는 행마다 dt.replace(second=0, microsecond=0).isoformat() 로 찾고,
    area_table 은 같은 규칙으로 넣는다. 한쪽만 바뀌면 컬럼이 조용히 전부
    빈 칸이 된다 — 화면은 멀쩡해 보이는데 값만 안 나온다.
    """

    def test_서버가_찾는_키로_반드시_잡힌다(self):
        from sentinel import _row_dt
        cfg = deepcopy(load_config())
        rows = [{"datetime": "2026-08-11 00:00:00", "M14_pts_RA": "5"},
                {"datetime": "2026-08-11 00:01", "M14_pts_RA": "5"},
                {"date": "2026-08-11", "time": "00:02", "M14_pts_RA": "5"}]
        t = F.area_table(rows, day=None, cfg=cfg)
        for r in rows:
            dt = _row_dt(r)
            key = dt.replace(second=0, microsecond=0).isoformat()   # server.py 와 같은 식
            self.assertIn(key, t["rows"], f"{r} 의 점수를 못 찾는다")

    def test_시각이_없는_행은_양쪽_다_건너뛴다(self):
        cfg = deepcopy(load_config())
        t = F.area_table([{"M14_pts_RA": "5"}], day=None, cfg=cfg)
        self.assertEqual(t["rows"], {})


class DashboardFabCols(unittest.TestCase):
    """화면 — 브라우저를 띄우지 않고 HTML 을 글자로 본다
    (test_dashboard_open.py 와 같은 방식: 공장 서버에 깔 게 늘면 안 된다)."""

    @classmethod
    def setUpClass(cls):
        import os
        with open(os.path.join(util.BASE, "static", "dashboard.html"),
                  encoding="utf-8") as f:
            cls.h = f.read()

    def test_HI_FAB_머리글을_만든다(self):
        self.assertIn("HI_FAB", self.h)

    def test_ALL_이면_종합점수로_적는다(self):
        self.assertIn("'종합점수'", self.h)

    def test_FAB_머리글은_서버가_준_목록으로_만든다(self):
        """코드를 HTML 에 박아 두면 config 의 fabs 를 바꿨을 때 머리글만
        옛 이름으로 남는다."""
        self.assertIn("FABS.forEach(f => add(", self.h)

    def test_정상은_흰색이다(self):
        """다섯 FAB 은 늘 떠 있는 컬럼이라 정상까지 칠하면 색이 정보를 잃는다."""
        m = re.search(r"const lvTx = .*?;", self.h, re.S)
        self.assertIsNotNone(m, "lvTx 가 없다")
        self.assertIn("var(--tx)", m.group(0))
        self.assertNotIn("var(--ok)", m.group(0), "정상을 초록으로 칠하면 안 된다")

    def test_등급색_네_가지를_다_쓴다(self):
        m = re.search(r"const lvTx = .*?;", self.h, re.S).group(0)
        for c in ("var(--crit)", "var(--major)", "var(--minor)", "var(--tx)"):
            self.assertIn(c, m)

    def test_FAB_컷으로_칠한다(self):
        """ALL 컷(CUTS)으로 칠하면 정책 탭에서 FAB 별로 바꾼 값이 안 나타난다."""
        m = re.search(r"function fabCells\(r\)\{.*?\n\}", self.h, re.S)
        self.assertIsNotNone(m, "fabCells 가 없다")
        self.assertIn("FCUTS[f]", m.group(0))
        self.assertNotIn("CUTS.warn", m.group(0))

    def test_모르는_FAB_은_빈칸으로_그린다(self):
        m = re.search(r"function fabCells\(r\)\{.*?\n\}", self.h, re.S).group(0)
        self.assertIn("undefined", m, "값이 없을 때를 구분해야 한다")
        self.assertIn("–", m)

    def test_실시간과_과거_두_탭_모두_컬럼을_받는다(self):
        self.assertEqual(self.h.count("setFabs(fd);"), 2,
                         "실시간·과거 두 탭에서 각각 한 번씩 받아야 한다")

    def test_빈_목록_colspan_이_컬럼_수를_따라간다(self):
        """7 로 박아 두면 FAB 컬럼이 붙는 순간 '데이터 없음' 칸이 어긋난다."""
        m = re.search(r"function rowsHtml\(.*?\n\}", self.h, re.S).group(0)
        self.assertIn("const ncol = 7 +", m)
        self.assertIn('colspan="${ncol}"', m)

    def test_행에_HI_FAB_과_FAB_칸을_넣는다(self):
        m = re.search(r"function rowsHtml\(.*?\n\}", self.h, re.S).group(0)
        self.assertIn("${hiCell(r)}${fabCells(r)}", m)


class FilesSig(unittest.TestCase):
    """피드 캐시 서명 — FAB 분리 파일이 바뀐 것도 잡아야 한다.

    화면 캐시는 '지금 보는 날짜 파일' 의 mtime 만 보고 있었다. 그런데 FAB
    다섯 점수는 분리 파일에서 읽으므로, 그 파일만 갱신되면 컬럼이 옛 값에
    얼어붙는다. 오래된 값을 보여주는 것이 안 보여주는 것보다 나쁘다.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rtsig")
        self.cfg = deepcopy(load_config())
        self.cfg["storage"]["daily_csv_dir"] = self.tmp

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _put(self, fab, area):
        from lp_client import sys_cfg
        _write(store_csv.day_path(DAY, sys_cfg(self.cfg, fab)),
               [{"datetime": "2026-08-11 00:00", "area_score": str(area)}],
               ["datetime", "area_score"])

    def test_FAB_파일이_없어도_자리를_남긴다(self):
        sig = F.files_sig(DAY, self.cfg)
        self.assertEqual(len(sig), len(F.fabs(self.cfg)))

    def test_FAB_파일이_생기면_서명이_바뀐다(self):
        before = F.files_sig(DAY, self.cfg)
        self._put("M16HUB", 40)
        self.assertNotEqual(before, F.files_sig(DAY, self.cfg))

    def test_FAB_파일_내용이_바뀌면_서명이_바뀐다(self):
        self._put("M16HUB", 40)
        before = F.files_sig(DAY, self.cfg)
        self._put("M16HUB", 999999)          # 길이가 달라진다
        self.assertNotEqual(before, F.files_sig(DAY, self.cfg))

    def test_아무것도_안_바뀌면_서명이_같다(self):
        self._put("M16HUB", 40)
        self.assertEqual(F.files_sig(DAY, self.cfg), F.files_sig(DAY, self.cfg))


if __name__ == "__main__":
    unittest.main()
