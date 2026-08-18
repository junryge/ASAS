"""날짜 CSV 읽기·피드 응답 캐시 — 현장에서 /api/feed 가 34초 걸렸다.

화면이 3초마다 부르는데 그때마다 하루치 CSV 를 통째로 다시 읽고, 수백 행을
매번 가공·직렬화했다. 계산 자체는 0.06초라 병목은 **파일 읽기**였다
(현장 디스크·백신·네트워크 드라이브). 요청이 줄줄이 밀려 "데이터가 안 뜬다"·
"저장이 오래 걸린다" 로 나타났다.

★캐시가 오래된 값을 보여주면 그게 더 나쁘다 — 파일이 바뀌면 **즉시** 새로
  읽는지가 이 파일의 핵심이다.
"""
import csv
import os
import shutil
import tempfile
import unittest
from copy import deepcopy

from . import util  # noqa: F401
import store_csv
from lp_client import load_config

COLS = ["datetime", "date", "time", "unified_risk_score", "hot_area", "reason"]


def _row(i, score="44"):
    return {"datetime": f"2026-08-18 {i//60:02d}:{i%60:02d}",
            "date": "2026-08-18", "time": f"{i//60:02d}:{i%60:02d}",
            "unified_risk_score": score, "hot_area": "M16HUB",
            "reason": "발동: M16HUB[R-C]"}


class ReadDayCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rtfeed")
        self.cfg = deepcopy(load_config())
        self.cfg["storage"]["daily_csv_dir"] = self.tmp
        self.path = store_csv.day_path("20260818", self.cfg)
        with open(self.path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLS)
            w.writeheader()
            for i in range(50):
                w.writerow(_row(i))
        store_csv._day_cache.clear()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        store_csv._day_cache.clear()

    def test_같은_파일은_다시_안_읽는다(self):
        a = store_csv.read_day("20260818", self.cfg)
        b = store_csv.read_day("20260818", self.cfg)
        self.assertEqual(len(a), 50)
        self.assertIs(a, b, "같은 객체를 돌려줘야 재파싱을 안 한 것")

    def test_행이_늘면_즉시_새로_읽는다(self):
        """★실시간 관제다. 오래된 값을 보여주면 캐시가 없느니만 못하다."""
        before = len(store_csv.read_day("20260818", self.cfg))
        with open(self.path, "a", encoding="utf-8-sig", newline="") as f:
            csv.DictWriter(f, fieldnames=COLS).writerow(_row(50, "88"))
        rows = store_csv.read_day("20260818", self.cfg)
        self.assertEqual(len(rows), before + 1)
        self.assertEqual(rows[-1]["unified_risk_score"], "88")

    def test_내용이_바뀌어도_새로_읽는다(self):
        """크기가 같아도 mtime 이 바뀌면 다시 읽는다."""
        store_csv.read_day("20260818", self.cfg)
        with open(self.path, "r", encoding="utf-8-sig") as f:
            body = f.read()
        import time
        time.sleep(0.01)
        with open(self.path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(body.replace("44", "99"))
        rows = store_csv.read_day("20260818", self.cfg)
        self.assertTrue(all(r["unified_risk_score"] == "99" for r in rows))

    def test_파일이_지워지면_빈_목록(self):
        store_csv.read_day("20260818", self.cfg)
        os.unlink(self.path)
        self.assertEqual(store_csv.read_day("20260818", self.cfg), [])

    def test_캐시가_무한히_커지지_않는다(self):
        for d in range(1, 9):
            p = store_csv.day_path(f"202608{d:02d}", self.cfg)
            with open(p, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=COLS)
                w.writeheader(); w.writerow(_row(0))
            store_csv.read_day(f"202608{d:02d}", self.cfg)
        self.assertLessEqual(len(store_csv._day_cache), store_csv._DAY_CACHE_MAX)


class FeedResponseCache(unittest.TestCase):
    """/api/feed 응답 캐시 — 원본이 그대로면 재생성하지 않는다."""

    def setUp(self):
        import server
        self.server = server
        self.client = server.app.test_client()
        self.tmp = tempfile.mkdtemp(prefix="rtfeed2")
        self._saved = deepcopy(server.CFG.get("storage"))
        server.CFG["storage"] = dict(server.CFG["storage"],
                                     daily_csv_dir=self.tmp)
        server.CTX.clear()
        server.FEED_CACHE.clear()
        store_csv._day_cache.clear()
        from datetime import datetime
        day = datetime.now().strftime("%Y%m%d")
        self.path = store_csv.day_path(day, server.CFG)
        with open(self.path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLS)
            w.writeheader()
            for i in range(30):
                w.writerow(_row(i))

    def tearDown(self):
        self.server.CFG["storage"] = self._saved
        self.server.CTX.clear()
        self.server.FEED_CACHE.clear()
        store_csv._day_cache.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_반복_호출이_같은_결과(self):
        a = self.client.get("/api/feed?sys=ALL").get_json()
        b = self.client.get("/api/feed?sys=ALL").get_json()
        self.assertEqual(a["total"], 30)
        self.assertEqual(a["total"], b["total"])
        self.assertEqual(len(self.server.FEED_CACHE), 1, "캐시에 담겨야 한다")

    def test_새_행이_들어오면_바로_보인다(self):
        before = self.client.get("/api/feed?sys=ALL").get_json()["total"]
        with open(self.path, "a", encoding="utf-8-sig", newline="") as f:
            csv.DictWriter(f, fieldnames=COLS).writerow(_row(31, "88"))
        after = self.client.get("/api/feed?sys=ALL").get_json()
        self.assertEqual(after["total"], before + 1, "캐시가 새 데이터를 막으면 안 된다")
        self.assertEqual(after["counts"]["초위험"], 1)


if __name__ == "__main__":
    unittest.main()
