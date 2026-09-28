# -*- coding: utf-8 -*-
"""날짜 목록(list_days)이 옛 파일을 매번 다시 읽지 않나.

고객: "원인을 알았다 속도가 늦은 이유!!" · "파일을 전에 것까지 같이 읽어 들이나 보네.
그래서 느리네" · "과거 파일 읽어 들이는 부분은 그대로 하자".

★list_days 가 부를 때마다 모든 날짜 파일을 끝까지 읽어 줄 수를 셌다. UI대쉬보드
  한 화면이 30초마다 6번 부르니 날짜가 쌓일수록 느려졌다(180일치에서 2.4초).
★안 바뀐 파일은 세어 둔 줄 수를 쓴다. 목록·줄 수는 전과 같아야 하고, 과거 날짜를
  여는 read_day 는 그대로여야 한다.
"""
import os
import shutil
import tempfile
import unittest
from unittest import mock

import store_csv

HEAD = "datetime,unified_risk_score\n"


def _write(p, n):
    with open(p, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(HEAD)
        for i in range(n):
            fh.write(f"2026-09-01 00:{i % 60:02d},{i}\n")


class 날짜_목록은_안_바뀐_파일을_다시_안_읽는다(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.cfg = {"storage": {"daily_csv_dir": self.dir}}
        store_csv._rows_cache.clear()
        for day, n in (("20260901", 5), ("20260902", 7), ("20260903", 3)):
            _write(os.path.join(self.dir, f"{day}_TOTAL.CSV"), n)
        with open(os.path.join(self.dir, "20260903_LLM.CSV"), "w", encoding="utf-8") as fh:
            fh.write("x\n")                              # TOTAL 이 아닌 파일은 목록에 안 든다

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)
        store_csv._rows_cache.clear()

    def _opens(self):
        """store_csv 안에서 open 이 몇 번 불렸나 세는 도구."""
        return mock.patch.object(store_csv, "open", create=True, side_effect=open)

    def test_목록과_줄_수는_전과_같다(self):
        got = store_csv.list_days(self.cfg)
        self.assertEqual([x["day"] for x in got], ["20260903", "20260902", "20260901"])   # 최신순
        self.assertEqual([x["rows"] for x in got], [3, 7, 5])
        for x in got:
            self.assertEqual(x["bytes"], os.path.getsize(os.path.join(self.dir, x["file"])))

    def test_두번째부터는_아무_파일도_안_연다(self):
        with self._opens() as op:
            store_csv.list_days(self.cfg)
            self.assertEqual(op.call_count, 3)
        with self._opens() as op:
            again = store_csv.list_days(self.cfg)
            self.assertEqual(op.call_count, 0, "안 바뀐 파일을 또 읽었다")
        self.assertEqual([x["rows"] for x in again], [3, 7, 5])

    def test_바뀐_파일만_다시_센다(self):
        store_csv.list_days(self.cfg)
        with open(os.path.join(self.dir, "20260903_TOTAL.CSV"), "a", encoding="utf-8", newline="") as fh:
            fh.write("2026-09-03 00:59,9\n")             # 수집이 한 줄 붙였다
        with self._opens() as op:
            got = store_csv.list_days(self.cfg)
            self.assertEqual(op.call_count, 1, "바뀐 오늘 파일 하나만 다시 세야 한다")
        self.assertEqual(got[0]["rows"], 4)

    def test_못_읽은_파일은_기억하지_않는다(self):
        """★백신·잠금으로 한 번 못 읽었다고 0행이 굳으면 그 날이 목록에서 빈 날이 된다."""
        bad = os.path.join(self.dir, "20260902_TOTAL.CSV")

        def flaky(p, *a, **k):
            if p == bad:
                raise PermissionError("잠김")
            return open(p, *a, **k)
        with mock.patch.object(store_csv, "open", create=True, side_effect=flaky):
            first = store_csv.list_days(self.cfg)
        self.assertEqual(first[1]["rows"], 0)
        self.assertEqual(store_csv.list_days(self.cfg)[1]["rows"], 7)

    def test_지운_날은_목록에서_빠진다(self):
        store_csv.list_days(self.cfg)
        os.remove(os.path.join(self.dir, "20260901_TOTAL.CSV"))
        self.assertEqual([x["day"] for x in store_csv.list_days(self.cfg)], ["20260903", "20260902"])

    def test_최근_날과_최근_N일도_그대로(self):
        _write(os.path.join(self.dir, "20260904_TOTAL.CSV"), 0)      # 머리글만 있는 오늘
        self.assertEqual(store_csv.latest_day(self.cfg), "20260903", "빈 파일은 최신이 아니다")
        self.assertEqual(store_csv.recent_days(2, self.cfg), ["20260903", "20260904"])

    def test_과거_날짜를_여는_read_day_는_그대로(self):
        rows = store_csv.read_day("20260901", self.cfg)
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["unified_risk_score"], "0")


if __name__ == "__main__":
    unittest.main()
