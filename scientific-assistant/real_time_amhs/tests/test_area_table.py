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

    # ── 추이 그래프에 FAB 겹쳐보기 ──────────────────────────────────
    def test_겹쳐보기_체크박스가_실시간과_과거_모두_있다(self):
        self.assertIn('id="stripfab"', self.h)
        self.assertIn('id="pstripfab"', self.h)

    def test_FAB_선_색은_재서_고른_값이다(self):
        """눈으로 고른 색이 아니다. 이 배경(#0D1119)에서 다섯이 서로, 그리고
        본선(시안)·등급 점(노랑·주황·빨강)과도 구분되는지 OKLab ΔE 로 재서
        고른 값이다 — 적록색약 8.1 · 정상시야 15.9 · 등급 밴드 위 대비
        3.08:1 이상. 바꾸려면 눈대중 말고 다시 재고 이 표도 같이 고칠 것:
        파랑과 보라는 눈에는 달라 보여도 적록색약에서 ΔE 1.3 까지 붙는다."""
        want = {"M14": "#3f93f7", "M14B": "#3d8f40", "M16A": "#824df9",
                "M16B": "#b973c6", "M16HUB": "#d7038b"}
        m = re.search(r"const FAB_COLOR = \{(.*?)\};", self.h, re.S)
        self.assertIsNotNone(m, "FAB_COLOR 표가 없다")
        flat = m.group(1).replace(" ", "").replace("\n", "")
        for f, c in want.items():
            self.assertIn(f"{f}:'{c}'", flat)

    def test_상태색을_FAB_선에_쓰지_않는다(self):
        """관제 화면에서 노랑·주황·빨강은 '등급' 이라는 뜻이고 시안은 전체
        점수다. FAB 선에 그 색을 쓰면 그냥 선인데 경보로 읽힌다."""
        flat = re.search(r"const FAB_COLOR = \{(.*?)\};", self.h, re.S).group(1).lower()
        for c in ("#f2d338", "#ff9f2e", "#ff4d5e", "#3ddbe8"):
            self.assertNotIn(c, flat)

    def test_스코어일_때만_겹쳐_그린다(self):
        """분·건·% 같은 지표에 0~100 점수를 얹으면 y축이 두 개인 그래프가
        된다 — 읽는 사람이 반드시 잘못 읽는다."""
        m = re.search(r"function fabPaths\(.*?\n\}", self.h, re.S)
        self.assertIsNotNone(m, "fabPaths 가 없다")
        self.assertIn("mt.bands", m.group(0))

    def test_FAB_선이_본선보다_가늘다(self):
        """색이 아니라 굵기로도 '무엇이 전체 점수인지' 가 구분돼야 한다."""
        fp = re.search(r"function fabPaths\(.*?\n\}", self.h, re.S).group(0)
        fw = float(re.search(r'stroke-width="([\d.]+)"', fp).group(1))
        main = float(re.search(r'stroke="\$\{mt\.color\}" stroke-width="([\d.]+)"',
                               self.h).group(1))
        self.assertLess(fw, main)

    def test_FAB_선은_본선_면채움_뒤에_그린다(self):
        """본선 면채움(opacity .13)이 나중에 덮이면 FAB 색이 그만큼 물든다."""
        m = re.search(r"opacity=\"\.13\".*?fabPaths.*?stroke=\"\$\{mt\.color\}\"",
                      self.h, re.S)
        self.assertIsNotNone(m, "면채움 → FAB → 본선 순서가 아니다")

    def test_체크박스는_색만으로_구분하지_않는다(self):
        """색약이거나 흑백으로 인쇄해도 어느 FAB 인지 알아야 한다."""
        m = re.search(r"function fillFabSel\(.*?\n\}", self.h, re.S)
        self.assertIsNotNone(m, "fillFabSel 이 없다")
        self.assertIn("${esc(f)}</label>", m.group(0))

    # ── 속도 ────────────────────────────────────────────────────────
    def test_바뀐_게_없으면_표를_다시_그리지_않는다(self):
        """폴링은 3초마다인데 데이터는 1분에 한 번 바뀐다. 스무 번 중
        열아홉 번은 똑같은 표를 다시 그리는 것이었다 — 하루치 1440행을
        통째로 갈아치우면 브라우저가 214ms 멎는다(실측). 스크롤 위치도
        그때마다 날아갔다."""
        m = re.search(r"async function pollCases\(\)\{.*?\n\}", self.h, re.S)
        self.assertIsNotNone(m, "pollCases 가 없다")
        body = m.group(0)
        self.assertIn("feedSig(", body, "서명 없이 매번 그린다")
        self.assertIn("RENDER_SIG", body)
        # 서명이 같으면 innerHTML 을 건드리지 않아야 한다
        guard = body[body.index("RENDER_SIG"):]
        self.assertIn("$('#cases').innerHTML", guard)

    def test_서명에_표를_바꾸는_것이_다_들어있다(self):
        """하나라도 빠지면 화면이 옛것에 머문다."""
        m = re.search(r"function feedSig\(.*?\n\}", self.h, re.S)
        self.assertIsNotNone(m, "feedSig 가 없다")
        b = m.group(0)
        for k in ("fd.day", "fd.latest", "fd.total", "filter", "cap", "newAt",
                  "counts", "last_seen"):
            self.assertIn(k, b, f"서명에 {k} 가 없다")

    def test_한_번에_그리는_행에_상한이_있다(self):
        """1440행 x 13칸 = 18,720칸을 통째로 그리면 브라우저가 멎는다."""
        self.assertIn("const ROW_STEP", self.h)
        m = re.search(r"function rowsHtml\(list, byId, newAt, cap\)", self.h)
        self.assertIsNotNone(m, "rowsHtml 이 상한을 안 받는다")
        body = re.search(r"function rowsHtml\(.*?\n\}", self.h, re.S).group(0)
        self.assertIn("list.slice(0, cap)", body)
        self.assertIn("data-more", body, "잘린 뒤 더 보는 길이 없다")

    def test_남은_행이_몇_개인지_밝힌다(self):
        """말없이 자르면 '데이터가 없어졌다' 로 읽힌다."""
        body = re.search(r"function rowsHtml\(.*?\n\}", self.h, re.S).group(0)
        self.assertIn("행 표시 중", body)

    def test_필터를_바꾸면_상한을_처음으로_되돌린다(self):
        """경계만 보다가 전체로 갔는데 상한이 그대로면 '왜 아래가 잘렸지'
        가 된다."""
        self.assertIn("ROW_CAP = ROW_STEP; pollCases();", self.h)
        self.assertIn("PROW_CAP = ROW_STEP; paintPast();", self.h)

    def test_추이도_바뀔_때만_다시_그린다(self):
        m = re.search(r"async function pollCases\(\)\{.*?\n\}", self.h, re.S).group(0)
        self.assertIn("STRIP_SIG", m)

    def test_FAB_칸에_네모를_두르지_않는다(self):
        """등급은 글자색이 이미 말한다. 칸마다 상자가 생기면 표가 시끄럽고,
        어느 FAB 이 제일 높은지는 바로 왼쪽 HI_FAB 칸이 이름으로 말해 준다."""
        css = re.search(r"table\.cases td\.fcol\.\w+[^}]*\}", self.h)
        if css:
            body = css.group(0)
            self.assertNotIn("box-shadow", body, "FAB 칸에 테두리가 있다")
            self.assertNotIn("background", body, "FAB 칸에 배경 상자가 있다")

    def test_최고_FAB_표시가_글자색을_덮지_않는다(self):
        """등급을 말하는 것이 그 색이다. 여기서 덮으면 정작 필요한 것을 지운다."""
        m = re.search(r"table\.cases td\.fcol\.hifab b\{([^}]*)\}", self.h)
        self.assertIsNotNone(m, "최고 FAB 표시 규칙이 없다")
        self.assertNotIn("color", m.group(1))

    def test_표_전용_클래스가_다른_규칙과_안_겹친다(self):
        """★'top' 을 쓰다가 상단 바(.top — display:flex · background)가 그대로
        걸려서 숫자마다 네모가 생겼다. 표에서 만드는 이름은 다른 데서 쓰지
        않는 것이어야 한다."""
        for cls in ("hifab", "fcol", "hcol", "rcol", "rln", "morerow"):
            # 그 이름으로 시작하는 최상위 규칙(.이름{)이 있으면 겹친 것이다
            bare = re.findall(r"\n\s*\.%s[\s,{]" % cls, self.h)
            self.assertEqual(bare, [], f".{cls} 가 표 밖 규칙과 겹친다")

    def test_구간_그래프에도_켠_FAB_을_넘긴다(self):
        """추이에 겹쳐 놓고 더블클릭했는데 거기서 사라지면 안 된다."""
        m = re.search(r"function graphFabs\(\)\{.*?\n\}", self.h, re.S)
        self.assertIsNotNone(m, "graphFabs 가 없다")
        self.assertIn("fabs=", m.group(0))
        self.assertIn("graphFabs()", self.h)

    def test_보고_있는_탭의_선택을_넘긴다(self):
        """실시간과 과거는 따로 고른다 — 과거를 보는데 실시간 선택이 가면
        화면에 없는 선이 그래프에만 뜬다."""
        m = re.search(r"function graphFabs\(\)\{.*?\n\}", self.h, re.S).group(0)
        self.assertIn("FABSEL", m)
        self.assertIn("PFABSEL", m)

    def test_표_글자가_본문보다_크지_않다(self):
        """컬럼이 늘어난 표다. 어느 칸이든 본문(13.5px)보다 커지면 한 행이
        높아져서 한 화면에 들어오는 행 수가 줄어든다."""
        for name, pat in (("종합점수", r"\.ttl\{[^}]*font-size:([\d.]+)px"),
                          ("FAB 점수", r"td\.fcol b\{[^}]*font-size:([\d.]+)px"),
                          ("HI_FAB", r"td\.hcol b\{[^}]*font-size:([\d.]+)px"),
                          ("reason", r"td\.rcol\{[^}]*font-size:([\d.]+)px")):
            m = re.search(pat, self.h)
            self.assertIsNotNone(m, f"{name} 글자 크기 지정이 없다")
            self.assertLessEqual(float(m.group(1)), 13.5, f"{name} 가 본문보다 크다")

    def test_FAB_머리글과_숫자가_같은_정렬이다(self):
        """머리글(M14)과 그 아래 숫자가 다른 쪽으로 붙으면 어느 칸의 수인지
        눈으로 잇기 어렵다. 좁은 칸 다섯이 나란히 있어서 더 그렇다."""
        th = re.search(r"th\.fcol\{[^}]*text-align:(\w+)", self.h)
        td = re.search(r"td\.fcol\{[^}]*text-align:(\w+)", self.h)
        self.assertIsNotNone(th, "FAB 머리글 정렬 지정이 없다")
        self.assertIsNotNone(td, "FAB 숫자 정렬 지정이 없다")
        self.assertEqual(th.group(1), td.group(1), "머리글과 숫자가 따로 논다")
        self.assertEqual(td.group(1), "center")

    def test_자릿수가_달라도_세로줄이_맞는다(self):
        """7 / 36 / 100 이 섞여도 흔들리지 않게."""
        m = re.search(r"td\.fcol\{[^}]*\}", self.h, re.S)
        self.assertIn("tabular-nums", m.group(0))

    def test_reason_을_룰_단위로_끊는다(self):
        """한 줄로 흘리면 좁아진 칸에서 룰 이름 가운데가 갈라진다."""
        m = re.search(r"function reasonCell\(r\)\{.*?\n\}", self.h, re.S)
        self.assertIsNotNone(m, "reasonCell 이 없다")
        self.assertIn("·", m.group(0), "' · ' 로 이어진 것을 끊어야 한다")
        self.assertIn(r"\r?\n", m.group(0), "진짜 개행도 같이 끊어야 한다")

    def test_reason_원문은_툴팁에_남는다(self):
        """요약만 보이고 원문(reason_raw)을 잃으면 근거를 확인할 수 없다."""
        m = re.search(r"function reasonCell\(r\)\{.*?\n\}", self.h, re.S).group(0)
        self.assertIn("reason_raw", m)

    def test_reason_칸을_rowsHtml_이_쓴다(self):
        m = re.search(r"function rowsHtml\(.*?\n\}", self.h, re.S).group(0)
        self.assertIn("${reasonCell(r)}", m)

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


class GraphOverlay(unittest.TestCase):
    """구간 그래프(더블클릭)에도 체크한 FAB 을 같이 그린다.

    추이에 겹쳐 놓고 더블클릭했는데 거기서 사라지면 같은 것을 두 번 골라야
    한다 — 두 화면이 같은 것을 보여주는 게 이 기능의 요점이다.
    """

    def setUp(self):
        import datetime as _dt
        self.cfg = deepcopy(load_config())
        self.rows, t0 = [], _dt.datetime(2026, 8, 11, 12, 0)
        for i in range(40):
            t = t0 + _dt.timedelta(minutes=i)
            r = {"datetime": t.strftime("%Y-%m-%d %H:%M"),
                 "unified_risk_score": "40", "hot_area": "M16HUB",
                 "reason": "발동: M16HUB[R-A_sus]"}
            for k, v in (("M14", 7), ("M14B", 5), ("M16A", 14),
                         ("M16B", 9), ("M16HUB", 25)):
                r[f"{k}_pts_RA"] = str(v)
                r[f"{k}_score"] = str(v)
            self.rows.append(r)
        self.center = t0 + _dt.timedelta(minutes=20)

    def _svg(self, fabs):
        import graphs
        return graphs.render(self.rows, self.center, minutes=40,
                             cfg=self.cfg, fabs=fabs)

    def _fab_lines(self, svg):
        return svg.count('stroke-width="1.15"')

    def test_체크한_수만큼_선이_늘어난다(self):
        self.assertEqual(self._fab_lines(self._svg(None)), 0)
        self.assertEqual(self._fab_lines(self._svg(["M16HUB"])), 1)
        self.assertEqual(self._fab_lines(self._svg(["M14", "M16A", "M16HUB"])), 3)

    def test_안_주면_예전과_똑같이_그린다(self):
        """겹쳐보기를 안 켠 사람에게는 화면이 그대로여야 한다."""
        self.assertEqual(self._svg(None), self._svg([]))

    def test_모르는_FAB_이름은_무시한다(self):
        """주소창에 아무 이름이나 넣어도 그래프는 나와야 한다."""
        svg = self._svg(["M99", "', 'DROP", "M16HUB"])
        self.assertEqual(self._fab_lines(svg), 1)

    def test_FAB_선이_전체_점수선보다_가늘다(self):
        """전체 점수가 기준선이라는 게 굵기로도 보여야 한다."""
        svg = self._svg(["M16HUB"])
        self.assertIn('stroke-width="1.6"', svg)          # 전체 점수
        self.assertIn('stroke-width="1.15"', svg)         # FAB

    def test_범례에_이름을_적는다(self):
        """색만으로 구분하면 색약·흑백 인쇄에서 어느 FAB 인지 모른다."""
        svg = self._svg(["M16HUB"])
        self.assertIn("M16HUB", svg)
        self.assertIn("area_score", svg)

    def test_점수는_목록과_같은_함수로_낸다(self):
        """여기서 따로 계산하면 같은 시각인데 화면마다 다른 수가 나온다."""
        import graphs
        t = F.area_table(self.rows, day=None, cfg=self.cfg)
        want = t["rows"]["2026-08-11T12:00:00"]["s"]["M16HUB"]
        series = graphs._fab_series(
            [(__import__("sentinel")._row_dt(r), r) for r in self.rows],
            ["M16HUB"], self.cfg)
        self.assertEqual(int(series[0][1][0][1]), want)


class ColorTable(unittest.TestCase):
    """FAB 선 색은 파이썬(fab_score)과 화면(dashboard.html) 두 곳에 있다.

    ★두 벌이라 어긋날 수 있다. 어긋나면 추이 그래프와 구간 그래프가 같은
      FAB 을 다른 색으로 그린다 — 보는 사람은 다른 FAB 인 줄 안다.
      그래서 여기서 묶어 둔다.
    """

    def test_화면과_서버의_색표가_같다(self):
        import os
        with open(os.path.join(util.BASE, "static", "dashboard.html"),
                  encoding="utf-8") as f:
            h = f.read()
        m = re.search(r"const FAB_COLOR = \{(.*?)\};", h, re.S)
        self.assertIsNotNone(m, "화면에 FAB_COLOR 표가 없다")
        web = dict(re.findall(r"(\w+)\s*:\s*'(#[0-9a-fA-F]{6})'", m.group(1)))
        self.assertEqual({k: v.lower() for k, v in web.items()},
                         {k: v.lower() for k, v in F.FAB_COLOR.items()},
                         "dashboard.html 과 fab_score.FAB_COLOR 가 어긋났다")

    def test_모르는_FAB_도_색이_나온다(self):
        """설정에 FAB 이 하나 늘어도 그래프가 터지면 안 된다."""
        self.assertTrue(F.fab_color("M99").startswith("#"))


class Download(unittest.TestCase):
    """과거 데이터 내려받기.

    ★원본 CSV(130컬럼짜리 기계 파일) 링크는 원래 있었지만, 툴바 끝에 'CSV'
      한 글자라 못 찾았고 — 찾아도 **화면에서 보던 표가 아니다**. 사람이
      받고 싶은 건 방금 보고 있던 그 표다."""

    @classmethod
    def setUpClass(cls):
        import os
        with open(os.path.join(util.BASE, "static", "dashboard.html"),
                  encoding="utf-8") as f:
            cls.h = f.read()
        m = re.search(r"function viewCsv\(list\)\{.*?\n\}", cls.h, re.S)
        assert m, "viewCsv 가 없다"
        cls.v = m.group(0)

    def test_고를_수_있게_메뉴로_둔다(self):
        """'CSV' 글자 하나로는 있는 줄도 모른다."""
        m = re.search(r'<select id="pdl".*?</select>', self.h, re.S)
        self.assertIsNotNone(m, "내려받기 메뉴가 없다")
        for v in ("view", "total", "llm", "ml"):
            self.assertIn('value="%s"' % v, m.group(0))

    def test_화면의_표를_그대로_받는다(self):
        """컬럼이 표와 어긋나면 '내가 보던 것' 이 아니다."""
        for col in ("시간", "CASE", "종합점수", "HI_FAB", "reason",
                    "실제지표", "AMOS HID구역", "AMOS QUEUE지표"):
            self.assertIn("'%s'" % col, self.v, col)
        self.assertIn("...FABS", self.v, "FAB 다섯이 서버 목록을 안 따라간다")

    def test_색으로만_말하던_것을_글자로_푼다(self):
        """표에서는 등급이 칩 색이고 reason 원문은 툴팁이다 — 파일에는 안 남는다."""
        self.assertIn("'등급'", self.v)
        self.assertIn("'reason 원문'", self.v)

    def test_모르는_FAB_은_0_이_아니라_빈칸(self):
        """★0 으로 채우면 받아 본 사람이 그 FAB 을 '정상' 으로 읽는다."""
        self.assertRegex(self.v, r"v == null \? '' : v")

    def test_엑셀이_한글을_안_깬다(self):
        """★BOM 이 없으면 엑셀이 cp949 로 읽어 전부 깨진다."""
        m = re.search(r"function csvText\(head, rows\)\{.*?\n\}", self.h, re.S)
        self.assertIsNotNone(m)
        self.assertIn("\\ufeff", m.group(0))

    def test_쉼표와_따옴표를_감싼다(self):
        """reason 원문에는 쉼표가 흔하다 — 안 감싸면 컬럼이 밀린다."""
        m = re.search(r"function csvCell\(v\)\{.*?\n\}", self.h, re.S)
        self.assertIsNotNone(m)
        body = m.group(0)
        self.assertIn('replace(/"/g', body, "따옴표를 두 번으로 안 바꾼다")
        self.assertRegex(body, r'test\(t\)')

    def test_몇_행_받는지_메뉴에_박는다(self):
        """★코드는 늘 전부 담는데 화면이 그렇게 말을 안 해서, '더 보기' 를
        눌러야 다 받는 줄 아셨다. 숫자를 적어 의심할 여지를 없앤다."""
        m = re.search(r"function pdlLabel\(\)\{.*?\n\}", self.h, re.S)
        self.assertIsNotNone(m, "받을 행수를 메뉴에 안 적는다")
        body = m.group(0)
        self.assertIn("applyFilter(PFEED, PFILTER", body)
        self.assertNotIn("PROW_CAP", body, "라벨에 화면 상한이 섞였다")
        self.assertIn("전부", body)
        # 값이 바뀌는 자리에서 다시 그려야 숫자가 안 어긋난다
        self.assertGreaterEqual(len(re.findall(r"pdlLabel\(\)", self.h)), 3,
                                "라벨을 갱신하는 자리가 모자라다")

    def test_서버가_자른_날은_말해_준다(self):
        """하루가 limit 을 넘으면 파일도 그만큼만 담긴다 — 말 없이 주면 안 된다."""
        m = re.search(r"\$\('#pdl'\).onchange = function\(\)\{.*?\n\};",
                      self.h, re.S).group(0)
        self.assertIn("PTOTAL", m)
        self.assertIn("PSHOWN", m)

    def test_화면_상한을_파일에_걸지_않는다(self):
        """'더 보기' 는 화면을 가볍게 하려는 것이다. 파일까지 300행에서
        끊으면 받은 사람은 그게 전부인 줄 안다."""
        m = re.search(r"\$\('#pdl'\).onchange = function\(\)\{.*?\n\};",
                      self.h, re.S)
        self.assertIsNotNone(m, "내려받기 처리가 없다")
        # ★주석은 걷고 본다 — '상한을 안 본다' 는 설명에도 그 이름이 나온다
        code = re.sub(r"//.*", "", m.group(0))
        self.assertNotIn("PROW_CAP", code, "파일에 화면 상한이 걸렸다")
        self.assertIn("applyFilter(PFEED, PFILTER", code,
                      "보고 있는 필터가 파일에 안 걸린다")


class StickyHead(unittest.TestCase):
    """머리글 고정 — 하루치 1440행을 내리면 지금 보는 숫자가 M14 인지
    M16B 인지 알 수 없어진다. 컬럼 이름이 화면에 남아 있어야 한다.

    ★브라우저로 재서 확인한 값(1600×900, 400행): 상단 바 62px, 어디까지
      내려도 머리글 top 62 · 상단 바 아래끝 62 — 딱 맞물린다. 13칸 모두
      본문 칸과 x 가 어긋나지 않는다."""

    @classmethod
    def setUpClass(cls):
        import os
        with open(os.path.join(util.BASE, "static", "dashboard.html"),
                  encoding="utf-8") as f:
            cls.h = f.read()
        m = re.search(r"table\.cases th\{([^}]*)\}", cls.h)
        assert m, "table.cases th 규칙이 없다"
        cls.th = m.group(1)

    def test_머리글이_따라_내려온다(self):
        self.assertIn("position:sticky", self.th)

    def test_상단_바_바로_아래에_선다(self):
        """0 으로 두면 상단 바가 머리글을 덮는다."""
        self.assertIn("top:var(--topbar)", self.th)
        self.assertRegex(self.h, r"--topbar:\s*\d+px", ":root 에 기본값이 없다")

    def test_상단_바_높이를_눈대중으로_적지_않는다(self):
        """글꼴이 대체되거나 창이 좁아 탭이 줄바꿈되면 바 높이가 달라진다.
        숫자를 박아 두면 그때 머리글이 바에 먹히거나 떠 버린다."""
        m = re.search(r"function syncTopbar\(\)\{.*?\n\}", self.h, re.S)
        self.assertIsNotNone(m, "상단 바 높이를 재는 함수가 없다")
        body = m.group(0)
        self.assertIn("getBoundingClientRect", body)
        self.assertIn("--topbar", body)
        self.assertIn("ResizeObserver", self.h)

    def test_상단_바가_한_화면에서_끝나지_않는다(self):
        """★sticky 는 **자기 상자 안에서만** 멈춘다. body 가 height:100% 면
        상자가 화면 한 장에서 끝나 상단 바가 같이 밀려 올라가고, 그 자리에
        빈 띠가 생겨 행이 머리글 위를 지나간다."""
        self.assertNotRegex(self.h, r"\n\s*html,\s*body\{height:100%\}")
        self.assertRegex(self.h, r"\n\s*body\{min-height:100%\}")

    def test_행이_머리글에_비치지_않는다(self):
        """반투명이면 밑으로 지나가는 행이 컬럼 이름과 겹쳐 읽힌다."""
        m = re.search(r"background:(var\(--\w+\)|#[0-9a-fA-F]{3,8})", self.th)
        self.assertIsNotNone(m, "머리글에 불투명 배경이 없다")
        self.assertNotIn("rgba", self.th)
        self.assertNotIn("transparent", self.th)

    def test_붙어_있는_동안에도_아래_줄이_보인다(self):
        """border-collapse:collapse 인 표는 칸 테두리를 표가 대신 그려서,
        붙어 있는 머리글의 border-bottom 이 같이 따라오지 않는다."""
        self.assertIn("border-collapse:collapse", self.h)
        self.assertIn("box-shadow:inset 0 -1px 0", self.th)

    def test_상단_바와_모달을_가리지_않는다(self):
        """상단 바 30 · 모달 50 · 오프닝 100 — 그 사이로 끼면 안 된다."""
        z = re.search(r"z-index:(\d+)", self.th)
        self.assertIsNotNone(z, "머리글에 z-index 가 없다 (행이 위로 올라온다)")
        self.assertLess(int(z.group(1)), 30, "머리글이 상단 바를 덮는다")
        self.assertGreater(int(z.group(1)), 0, "행이 머리글 위로 올라온다")

    def test_실시간과_과거_둘_다_고정된다(self):
        """규칙을 table.cases 에 걸어 두 표가 같이 받는다."""
        self.assertEqual(len(re.findall(r'<table class="cases">', self.h)), 2)
        self.assertNotIn("#cases thead th", self.h)



class 이_점수가_어디서_왔나(unittest.TestCase):
    """/api/fab/why — "현장에선 70 인데 관제는 아니라고 한다" 를 가르는 자리.

    ★갈릴 수 있는 곳이 셋이다. 셋 다 한 화면에 적혀야 사람이 짚을 수 있다.
        ① 어느 파일의 어느 컬럼을 읽었나
        ② 지금 이 시스템의 등급 컷이 얼마인가 (정책 탭 · 시스템별)
        ③ 예측기가 적어 둔 등급과 지금 정책이 다른가
    """

    def src(self):
        p = os.path.join(util.BASE, "server.py")
        with open(p, encoding="utf-8") as f:
            return f.read()

    def test_길이_있다(self):
        s = self.src()
        self.assertIn('@app.route("/api/fab/why")', s)
        self.assertIn("def api_fab_why", s)

    def test_셋을_다_말한다(self):
        s = self.src()
        i = s.index("def api_fab_why")
        j = s.index("@app.route(\"/api/fab/columns\")")
        body = s[i:j]
        self.assertIn("score_col", body)          # ① 어느 컬럼
        self.assertIn("cuts", body)               # ② 등급 컷
        self.assertIn("level_mismatch", body)     # ③ 예측기와 어긋남
        self.assertIn("file_value", body)         # 안 쓴 값도 말한다
        self.assertIn("FAB 분리 파일", body)
        self.assertIn("되계산", body)

    def test_사람이_읽을_글로_준다(self):
        """★JSON 만 주면 현장에서 못 본다. 한 줄로 읽히게 낸다."""
        s = self.src()
        i = s.index("def api_fab_why")
        self.assertIn('"text"', s[i:i + 4000])
        self.assertIn('"help"', s[i:i + 4000])


if __name__ == "__main__":
    unittest.main()
