"""ML 조기예측 수집 — 따로 받아서 따로 둔다.

무엇인가
    반송시간 10분평균이 임계(14.765분)를 넘을 확률을 1분마다 내는 별도
    시스템(chronos-2). 우리 룰베이스와 서로의 판정을 입력으로 쓰지 않는
    독립 판단이라, 같은 사건을 각각 언제 알렸는지 비교할 수 있다.

★TOTAL.CSV 에 합치지 않는 이유가 이 파일의 절반이다:
    ① 눈금이 다르다 — 우리는 점수 0~100(컷 60/71/85), ML 은 분(分).
       한 그래프에 겹치면 거짓말이 된다.
    ② 행 구조가 다르다 — ML 행에는 prediction_for_10m 이라는 미래 시각이 있다.
    ③ 출처가 다르다 — 한쪽이 죽어도 다른 쪽은 그대로 돌아야 한다.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import ml_feed                                    # noqa: E402

DAY = "20260819"

# 문서에 실린 실제 운영 행 (2026-08-19 13:21)
REAL_ROW = {
    "datetime": "2026-08-19 13:21:00",
    "prediction_for_10m": "2026-08-19 13:31:00",
    "prediction_for_30m": "2026-08-19 13:51:00",
    "ml_score_10m": "0.0000", "ml_score_30m": "0.0000",
    "ml_level_10m": "", "ml_level_30m": "",
    "raw_value": "7.725", "smoothed": "7.302", "threshold": "14.765",
    "stage": "0", "stage_name": "정상", "lead_min": "",
    "reason": "정상", "backend": "chronos_2",
}


def _row(dt, p10, p30, sm, stage, lead="", name="", reason=""):
    return {**REAL_ROW, "datetime": dt,
            "ml_score_10m": f"{p10:.4f}", "ml_score_30m": f"{p30:.4f}",
            "smoothed": f"{sm:.3f}", "stage": stage, "lead_min": lead,
            "stage_name": name or REAL_ROW["stage_name"],
            "reason": reason or REAL_ROW["reason"]}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        with open(os.path.join(_ROOT, "config.json"), encoding="utf-8-sig") as f:
            self.cfg = json.load(f)
        self.cfg.setdefault("storage", {})["daily_csv_dir"] = self.tmp
        self.cfg["storage"]["dir"] = self.tmp


class Config(Base):
    def test_주피터_설정을_그대로_쓰고_경로만_바꾼다(self):
        """★같은 서버·같은 비밀번호다. 로그인·인코딩을 다시 만들 이유가 없다."""
        c = ml_feed.cfg_of(self.cfg)
        j = self.cfg["source"]["jupyter"]
        self.assertEqual(c["base_url"], j["base_url"])
        self.assertEqual(c.get("encoding"), j.get("encoding"))
        self.assertNotEqual(c["path"], j["path"])
        self.assertIn("ml_predict", c["path"])
        self.assertIn("{day}", c["path"])

    def test_비밀번호를_따로_들고_있지_않는다(self):
        """★비밀번호는 주피터 설정 한 곳에만 있어야 한다."""
        ml = self.cfg.get("ml", {})
        for k in ("password", "token", "api_key"):
            self.assertNotIn(k, ml, f"ml 블록에 {k} 가 있으면 안 된다")

    def test_배포_설정이_켜져_있다(self):
        with open(os.path.join(_ROOT, "config.json"), encoding="utf-8-sig") as f:
            c = json.load(f)
        self.assertTrue(c["ml"]["enabled"])
        self.assertTrue(c["ml"]["path"])

    def test_문턱이_ML쪽_기준과_같다(self):
        """★화면 설명이 '30%부터 선제경보' 라고 하는데 값이 다르면 거짓말이다.
        ML 쪽 model_config: P_ON=0.30, 히스테리시스 해제 0.20."""
        with open(os.path.join(_ROOT, "config.json"), encoding="utf-8-sig") as f:
            c = json.load(f)
        self.assertAlmostEqual(c["ml"]["p_on"], 0.30)
        self.assertAlmostEqual(c["ml"]["p_off"], 0.20)
        self.assertLess(c["ml"]["p_off"], c["ml"]["p_on"], "해제 문턱이 더 낮아야 깜빡임을 막는다")


class Storage(Base):
    def test_TOTAL과_다른_파일에_쓴다(self):
        """★눈금이 달라 합치면 안 된다."""
        from store_csv import day_path
        self.assertNotEqual(ml_feed.ml_path(DAY, self.cfg), day_path(DAY, self.cfg))
        self.assertTrue(ml_feed.ml_path(DAY, self.cfg).endswith("_ML.CSV"))

    def test_쓰고_읽는다(self):
        ml_feed._write(DAY, [REAL_ROW], self.cfg)
        got = ml_feed.read_day(DAY, self.cfg)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["datetime"], REAL_ROW["datetime"])
        self.assertEqual(got[0]["backend"], "chronos_2")

    def test_없는_날은_빈_목록(self):
        self.assertEqual(ml_feed.read_day("20990101", self.cfg), [])

    def test_칸을_원본_그대로_남긴다(self):
        """나중에 ML 팀과 대조할 때 원본이 아니면 못 믿는다."""
        ml_feed._write(DAY, [REAL_ROW], self.cfg)
        got = ml_feed.read_day(DAY, self.cfg)[0]
        for k, v in REAL_ROW.items():
            self.assertEqual(got[k], v, f"{k} 가 바뀌었다")


class Latest(Base):
    def test_실제_운영행을_읽는다(self):
        """★문서에 실린 그 줄이 그대로 화면 값이 돼야 한다."""
        ml_feed._write(DAY, [REAL_ROW], self.cfg)
        L = ml_feed.latest(DAY, self.cfg)
        self.assertEqual(L["p10"], 0.0)
        self.assertEqual(L["smoothed"], 7.302)
        self.assertEqual(L["threshold"], 14.765)
        self.assertEqual(L["stage_name"], "정상")

    def test_빈_등급은_정상으로_읽는다(self):
        """확률이 낮으면 ml_level 이 빈칸으로 온다 — 빈칸을 그대로 띄우면 안 된다."""
        ml_feed._write(DAY, [REAL_ROW], self.cfg)
        self.assertEqual(ml_feed.latest(DAY, self.cfg)["level10"], "정상")

    def test_가장_최근_줄을_고른다(self):
        ml_feed._write(DAY, [
            _row("2026-08-19 10:00:00", 0.0, 0.0, 6.5, "0"),
            _row("2026-08-19 12:00:00", 0.4, 0.7, 14.0, "2", lead="8"),
            _row("2026-08-19 11:00:00", 0.0, 0.0, 6.6, "0"),
        ], self.cfg)
        self.assertEqual(ml_feed.latest(DAY, self.cfg)["datetime"], "2026-08-19 12:00:00")

    def test_없으면_None(self):
        self.assertIsNone(ml_feed.latest("20990101", self.cfg))


class Summary(Base):
    def _day(self):
        rows = [_row(f"2026-08-19 {h:02d}:{m:02d}:00", 0.0, 0.0, 6.5, "0")
                for h in (9,) for m in range(5)]
        rows += [_row("2026-08-19 09:05:00", 0.35, 0.50, 14.0, "2", lead="8"),
                 _row("2026-08-19 09:06:00", 0.40, 0.60, 14.4, "2", lead="6"),
                 _row("2026-08-19 09:07:00", 1.0, 1.0, 15.1, "3"),
                 _row("2026-08-19 09:08:00", 0.0, 0.0, 8.0, "0")]
        ml_feed._write(DAY, rows, self.cfg)
        return ml_feed.summary(DAY, self.cfg)

    def test_단계별로_분을_센다(self):
        s = self._day()
        self.assertEqual(s["by_stage"]["0"], 6)
        self.assertEqual(s["by_stage"]["2"], 2)
        self.assertEqual(s["by_stage"]["3"], 1)

    def test_경보_구간을_하나로_묶는다(self):
        """★분 단위로 흩어 놓으면 '몇 번 있었나' 를 셀 수 없다."""
        s = self._day()
        self.assertEqual(len(s["spans"]), 1, s["spans"])
        sp = s["spans"][0]
        self.assertEqual(sp["from"], "2026-08-19 09:05:00")
        self.assertEqual(sp["to"], "2026-08-19 09:07:00")
        self.assertEqual(sp["stage"], "3", "예보였다가 실제로 넘어갔으면 진행중으로 남아야 한다")

    def test_평온한_날은_구간이_없다(self):
        ml_feed._write(DAY, [REAL_ROW], self.cfg)
        self.assertEqual(ml_feed.summary(DAY, self.cfg)["spans"], [])

    def test_최고_확률을_남긴다(self):
        s = self._day()
        self.assertEqual(s["max_p10"], 1.0)
        self.assertEqual(s["max_p30"], 1.0)


class Ingest(Base):
    """받아 넣기 — 중복이 안 쌓이고 빠진 분은 저절로 메워진다."""

    def _fake_download(self, rows):
        import io, csv as _csv
        buf = io.StringIO()
        w = _csv.DictWriter(buf, fieldnames=ml_feed.COLS, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
        data = buf.getvalue().encode("utf-8-sig")
        import jupyter_csv as jc
        orig = jc.download
        jc.download = lambda day, cfg=None: (data, "")
        self.addCleanup(lambda: setattr(jc, "download", orig))

    def test_받아서_저장한다(self):
        self._fake_download([REAL_ROW])
        r = ml_feed.fetch_day(DAY, self.cfg)
        self.assertEqual((r["rows"], r["added"], r["error"]), (1, 0 + 1, ""))
        self.assertEqual(len(ml_feed.read_day(DAY, self.cfg)), 1)

    def test_같은_분은_두_번_안_쌓인다(self):
        """★매 분 파일을 통째로 받는다 — 중복을 안 막으면 하루에 수천 행이 된다."""
        self._fake_download([REAL_ROW])
        ml_feed.fetch_day(DAY, self.cfg)
        r2 = ml_feed.fetch_day(DAY, self.cfg)
        self.assertEqual(r2["added"], 0)
        self.assertEqual(len(ml_feed.read_day(DAY, self.cfg)), 1)

    def test_빠진_분이_다음에_메워진다(self):
        self._fake_download([REAL_ROW])
        ml_feed.fetch_day(DAY, self.cfg)
        self._fake_download([REAL_ROW, _row("2026-08-19 13:22:00", 0.0, 0.0, 7.3, "0")])
        r = ml_feed.fetch_day(DAY, self.cfg)
        self.assertEqual(r["added"], 1)
        self.assertEqual(len(ml_feed.read_day(DAY, self.cfg)), 2)

    def test_시각순으로_저장된다(self):
        self._fake_download([_row("2026-08-19 13:22:00", 0, 0, 7.3, "0")])
        ml_feed.fetch_day(DAY, self.cfg)
        self._fake_download([REAL_ROW])          # 더 이른 시각이 나중에 도착
        ml_feed.fetch_day(DAY, self.cfg)
        got = [r["datetime"] for r in ml_feed.read_day(DAY, self.cfg)]
        self.assertEqual(got, sorted(got))

    def test_받기_실패는_조용히_알린다(self):
        """★관제는 계속 돌아야 한다 — 예외를 던지면 수집 루프가 멈춘다."""
        import jupyter_csv as jc
        orig = jc.download
        jc.download = lambda day, cfg=None: (None, "HTTP 404")
        self.addCleanup(lambda: setattr(jc, "download", orig))
        r = ml_feed.fetch_day(DAY, self.cfg)
        self.assertEqual(r["added"], 0)
        self.assertIn("404", r["error"])


class Range(Base):
    """기간 조회·내려받기 — 연구·대조에 쓰려면 하루 단위로는 못 쓴다."""

    def test_날짜_목록을_만든다(self):
        self.assertEqual(ml_feed.day_range("20260817", "20260819"),
                         ["20260817", "20260818", "20260819"])

    def test_하루짜리도_된다(self):
        self.assertEqual(ml_feed.day_range("20260819", "20260819"), ["20260819"])

    def test_거꾸로_넣어도_바로잡는다(self):
        """★화면에서 실수하기 쉬운 자리다 — 빈 결과를 주면 '고장' 으로 읽힌다."""
        self.assertEqual(ml_feed.day_range("20260819", "20260817"),
                         ["20260817", "20260818", "20260819"])

    def test_달을_넘어간다(self):
        got = ml_feed.day_range("20260830", "20260902")
        self.assertEqual(got, ["20260830", "20260831", "20260901", "20260902"])

    def test_이상한_날짜는_빈_목록(self):
        self.assertEqual(ml_feed.day_range("", "20260819"), [])
        self.assertEqual(ml_feed.day_range("20261399", "20261399"), [])

    def test_너무_긴_기간은_잘린다(self):
        """★실수로 10년을 넣어도 파일서버를 3650번 두드리면 안 된다."""
        self.assertLessEqual(len(ml_feed.day_range("20200101", "20301231")), 400)

    def test_여러_날을_시각순으로_합친다(self):
        ml_feed._write("20260818", [_row("2026-08-18 23:00:00", 0, 0, 6.5, "0")], self.cfg)
        ml_feed._write("20260819", [_row("2026-08-19 01:00:00", 0, 0, 6.6, "0")], self.cfg)
        got = ml_feed.read_range("20260818", "20260819", self.cfg)
        self.assertEqual([r["datetime"] for r in got],
                         ["2026-08-18 23:00:00", "2026-08-19 01:00:00"])

    def test_없는_날은_건너뛴다(self):
        ml_feed._write("20260819", [REAL_ROW], self.cfg)
        self.assertEqual(len(ml_feed.read_range("20260810", "20260819", self.cfg)), 1)

    def test_CSV로_뽑는다(self):
        ml_feed._write("20260819", [REAL_ROW], self.cfg)
        out = ml_feed.export_csv("20260819", "20260819", self.cfg)
        lines = out.strip().splitlines()
        self.assertEqual(lines[0].split(",")[0], "datetime")
        self.assertIn("chronos_2", lines[1])
        self.assertEqual(len(lines), 2)

    def test_CSV_머리글이_원본_칸_그대로다(self):
        """★분석에 바로 쓰려면 칸 이름이 ML 쪽과 같아야 한다."""
        out = ml_feed.export_csv("20260819", "20260819", self.cfg)
        self.assertEqual(out.splitlines()[0].split(","), ml_feed.COLS)

    def test_빈_기간도_머리글은_준다(self):
        """빈 파일을 받으면 '고장' 으로 보인다 — 머리글은 있어야 한다."""
        out = ml_feed.export_csv("20200101", "20200101", self.cfg)
        self.assertTrue(out.startswith("datetime,"))


class FetchRange(Base):
    def _fake(self, ok=True):
        import jupyter_csv as jc
        import io, csv as _csv
        def dl(day, cfg=None):
            if not ok:
                return None, "HTTP 404"
            buf = io.StringIO()
            w = _csv.DictWriter(buf, fieldnames=ml_feed.COLS, extrasaction="ignore")
            w.writeheader()
            w.writerow({**REAL_ROW, "datetime": f"{day[:4]}-{day[4:6]}-{day[6:]} 09:00:00"})
            return buf.getvalue().encode("utf-8-sig"), ""
        orig = jc.download
        jc.download = dl
        self.addCleanup(lambda: setattr(jc, "download", orig))

    def test_기간을_받아온다(self):
        self._fake()
        r = ml_feed.fetch_range("20260817", "20260819", self.cfg)
        self.assertEqual((r["days"], r["fetched"], r["failed"]), (3, 3, 0))
        self.assertEqual(len(ml_feed.read_range("20260817", "20260819", self.cfg)), 3)

    def test_이미_받은_지난날은_건너뛴다(self):
        """★한 달치를 다시 받느라 파일서버를 몇 십 번 두드릴 이유가 없다."""
        self._fake()
        # 오늘은 규칙이 다르므로(아래 시험) 확실한 과거로 잡는다
        ml_feed.fetch_range("20200101", "20200103", self.cfg)
        r2 = ml_feed.fetch_range("20200101", "20200103", self.cfg)
        self.assertEqual(r2["skipped"], 3)
        self.assertEqual(r2["fetched"], 0)

    def test_오늘은_이미_있어도_다시_받는다(self):
        """★오늘 파일은 지금도 쌓이는 중이다 — 건너뛰면 새 분이 안 들어온다."""
        from datetime import datetime as _dt
        today = _dt.now().strftime("%Y%m%d")
        self._fake()
        ml_feed.fetch_range(today, today, self.cfg)
        r2 = ml_feed.fetch_range(today, today, self.cfg)
        self.assertEqual(r2["skipped"], 0, "오늘을 건너뛰면 갱신이 멈춘다")
        self.assertEqual(r2["fetched"], 1)

    def test_다시받기를_고르면_다시_받는다(self):
        self._fake()
        ml_feed.fetch_range("20260817", "20260819", self.cfg)
        r2 = ml_feed.fetch_range("20260817", "20260819", self.cfg, skip_existing=False)
        self.assertEqual(r2["fetched"], 3)

    def test_일부_실패해도_나머지는_받는다(self):
        """★하루가 없다고 기간 전체가 실패하면 안 된다."""
        import jupyter_csv as jc
        import io, csv as _csv
        def dl(day, cfg=None):
            if day == "20260818":
                return None, "HTTP 404"
            buf = io.StringIO()
            w = _csv.DictWriter(buf, fieldnames=ml_feed.COLS, extrasaction="ignore")
            w.writeheader()
            w.writerow({**REAL_ROW, "datetime": f"{day[:4]}-{day[4:6]}-{day[6:]} 09:00:00"})
            return buf.getvalue().encode("utf-8-sig"), ""
        orig = jc.download
        jc.download = dl
        self.addCleanup(lambda: setattr(jc, "download", orig))
        r = ml_feed.fetch_range("20260817", "20260819", self.cfg)
        self.assertEqual((r["fetched"], r["failed"]), (2, 1))
        self.assertTrue(r["errors"])
        self.assertIn("20260818", r["errors"][0])


class DashboardWiring(unittest.TestCase):
    """화면이 실제로 그 기능을 부르는지 (문구·호출이 코드에 있는지)."""

    def setUp(self):
        with open(os.path.join(_ROOT, "static", "dashboard.html"), encoding="utf-8") as f:
            self.html = f.read()

    def test_실시간_관제_바로_다음_탭이다(self):
        i_live = self.html.index('data-tab="live"')
        i_ml = self.html.index('data-tab="ml"')
        i_past = self.html.index('data-tab="past"')
        self.assertLess(i_live, i_ml)
        self.assertLess(i_ml, i_past, "ML 탭이 '실시간 관제' 바로 뒤여야 한다")

    def test_자동_갱신을_한다(self):
        """★관제 화면이다 — 띄워 둔 채로 값이 멈춰 있으면 안 된다."""
        self.assertIn("function mlAutoRefresh", self.html)
        self.assertIn("ML_TIMER", self.html)

    def test_다른_탭이면_자동_갱신을_멈춘다(self):
        """★하루 종일 켜 두는 화면이라, 안 보는 탭이 요청을 계속 던지면 낭비다."""
        self.assertIn("if(b.dataset.tab !== 'ml') mlAutoRefresh(false)", self.html)

    def test_과거_날짜를_고를_수_있다(self):
        self.assertIn('id="mlday"', self.html)
        self.assertIn("function mlDay", self.html)
        self.assertIn("'/api/ml' + qs", self.html)

    def test_과거_날짜는_자동_갱신을_끈다(self):
        """지난 날짜는 더 안 변한다 — 계속 다시 읽으면 화면만 깜빡인다."""
        self.assertIn("mlAutoRefresh(mlIsToday())", self.html)

    def test_기간으로_받는다(self):
        """★하루씩 눌러 한 달치를 모을 수는 없다 — 기간이 기본이어야 한다."""
        self.assertIn('id="mlfrom"', self.html)
        self.assertIn('id="mlto"', self.html)
        self.assertIn('id="mlexport"', self.html)
        self.assertIn('id="mlbackfill"', self.html)
        self.assertIn("/api/ml/export?from=", self.html)

    def test_기간_단축_버튼이_있다(self):
        """날짜 두 개를 매번 손으로 고르게 하면 안 쓴다."""
        self.assertIn("function mlSetRange", self.html)
        self.assertIn('id="mlrange7"', self.html)
        self.assertIn('id="mlrange30"', self.html)

    def test_기간이_비면_알려_준다(self):
        self.assertIn("function mlRangeReady", self.html)
        self.assertIn("시작일과 종료일", self.html)

    def test_왜_비었는지_말해_준다(self):
        """★빈 화면만 보여 주면 '기다리는 중' 인지 '로그인 실패' 인지 모른다."""
        self.assertIn("아직 한 번도 받지 않았습니다", self.html)
        self.assertIn("function mlFetchNow", self.html)
        self.assertIn("시도한 주소", self.html)


class Endpoints(unittest.TestCase):
    """엔드포인트를 실제로 불러 본다.

    ★함수만 시험하면 라우트의 import 누락 같은 건 못 잡는다. 실제로
      Response 를 import 안 해서 500 이 났고, 단위 시험 247개가 전부
      통과하는데 화면에서만 죽었다.
    """

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("JUPYTER_PASSWORD", "x")
        try:
            import server
            cls.client = server.app.test_client()
        except Exception as e:
            raise unittest.SkipTest(f"서버를 못 띄운다: {e}")

    def test_기간_CSV가_내려온다(self):
        r = self.client.get("/api/ml/export?from=20200101&to=20200102")
        self.assertEqual(r.status_code, 200, r.data[:200])
        self.assertIn("text/csv", r.headers.get("Content-Type", ""))
        self.assertIn("attachment", r.headers.get("Content-Disposition", ""))
        self.assertTrue(r.data.decode("utf-8-sig").startswith("datetime,"))

    def test_기간_이름이_파일명에_들어간다(self):
        r = self.client.get("/api/ml/export?from=20200101&to=20200103")
        self.assertIn("20200101", r.headers.get("Content-Disposition", ""))
        self.assertIn("20200103", r.headers.get("Content-Disposition", ""))

    def test_이상한_기간은_400(self):
        self.assertEqual(self.client.get("/api/ml/export?from=&to=").status_code, 400)

    def test_기간_받아오기_엔드포인트(self):
        r = self.client.post("/api/ml/backfill", json={"from": "20200101", "to": "20200102"})
        self.assertEqual(r.status_code, 200, r.data[:200])
        self.assertIn("days", r.get_json())

    def test_지금_받기_엔드포인트가_사유를_준다(self):
        r = self.client.post("/api/ml/fetch")
        self.assertEqual(r.status_code, 200, r.data[:200])
        d = r.get_json()
        self.assertIn("url", d)          # 실패해도 시도한 주소는 알려 줘야 한다
        self.assertIn("ok", d)

    def test_요약_엔드포인트(self):
        r = self.client.get("/api/ml")
        self.assertEqual(r.status_code, 200, r.data[:200])
        self.assertIn("by_stage", r.get_json())


class DownloadRoute(unittest.TestCase):
    """/api/data/<day>_ML.csv 가 ML 파일을 준다."""

    def test_ML과_LLM을_안_헷갈린다(self):
        """★'LLM' 안에도 'LM' 이 있다 — 밑줄까지 봐야 구분된다.
        여기서 헷갈리면 ML 을 눌렀는데 LLM 파일이 내려온다."""
        with open(os.path.join(_ROOT, "server.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn('if "_ML" in up:', src)
        i_ml = src.index('if "_ML" in up:')
        i_llm = src.index('elif "LLM" in up:')
        self.assertLess(i_ml, i_llm, "_ML 검사가 먼저여야 한다")


if __name__ == "__main__":
    unittest.main()
