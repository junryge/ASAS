# -*- coding: utf-8 -*-
"""'현재 상태' 는 **어느 날** 자료를 보는가.

실제 사고
    8월 25일에 "현재 상태" 를 물으면 **7월 28일** 자료로 답했다.
    data/ 에는 20260728_TOTAL.CSV 와 20260819_TOTAL.CSV 두 개가 있었는데,
    store_csv.list_days() 는 **최신순**이라 days[-1] 이 '가장 오래된 날'
    이었다. 서버가 그걸 '오늘' 로 쓰고 있었다.

    같은 실수가 네 곳(server/contrib/forecast/fab_score)에 있었고,
    forecast 의 `[-limit:]` 는 '최근 N일' 이 아니라 '가장 오래된 N일' 을
    잘라 쓰고 있었다.

여기서 지키는 것
    ① 순서를 몰라도 되게 — latest_day() / recent_days() 로만 고른다
    ② '현재 상태' 는 **오늘**을 먼저 본다
    ③ 오늘이 없으면 물러서되 **물러섰다고 밝힌다** (옛 값을 현재라 하지 않는다)
"""
import os
import re
import tempfile
import unittest
from datetime import datetime

from . import util  # noqa: F401

import store_csv  # noqa: E402

BASE = util.BASE


def _cfg(d):
    """★data_dir 은 BASE_DIR + storage.daily_csv_dir 이다 — 절대경로를 주면
    무시되고 진짜 data/ 를 읽는다 (그러면 테스트가 거짓으로 통과한다)."""
    return {"storage": {"daily_csv_dir": os.path.basename(d)}}


def _write(d, day, rows=3):
    """그날치 CSV 한 장 — 컬럼은 최소한만."""
    p = os.path.join(d, "{}_TOTAL.CSV".format(day))
    head = "datetime,unified_risk_score\n"
    body = "".join("{}-{}-{} 0{}:00,30\n".format(day[:4], day[4:6], day[6:8],
                                                 i) for i in range(rows))
    with open(p, "w", encoding="utf-8") as f:
        f.write(head + body)
    return p


class 날짜_고르기(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._base = store_csv.BASE_DIR
        store_csv.BASE_DIR = self.tmp.name
        self.d = os.path.join(self.tmp.name, "d")
        os.makedirs(self.d, exist_ok=True)

    def tearDown(self):
        store_csv.BASE_DIR = self._base
        self.tmp.cleanup()

    def test_최신순으로_준다(self):
        _write(self.d, "20260728")
        _write(self.d, "20260819")
        got = [x["day"] for x in store_csv.list_days(_cfg(self.d))]
        self.assertEqual(got, ["20260819", "20260728"],
                         "list_days 가 최신순이 아니면 쓰는 쪽이 전부 뒤집힌다")

    def test_latest_day_가_진짜_최신이다(self):
        """★[-1] 을 '최신' 인 줄 알고 쓰던 자리를 이 함수가 대신한다."""
        _write(self.d, "20260728")
        _write(self.d, "20260819")
        self.assertEqual(store_csv.latest_day(_cfg(self.d)), "20260819")

    def test_없으면_None(self):
        self.assertIsNone(store_csv.latest_day(_cfg(self.d)))

    def test_recent_days_는_최근_N일을_오래된_순으로(self):
        """★예전 `[-limit:]` 는 최신순 목록의 뒤쪽 = **가장 오래된 N일** 이었다."""
        for day in ("20260810", "20260811", "20260812", "20260813"):
            _write(self.d, day)
        self.assertEqual(store_csv.recent_days(2, _cfg(self.d)),
                         ["20260812", "20260813"])
        self.assertEqual(store_csv.recent_days(99, _cfg(self.d))[0], "20260810")
        self.assertEqual(store_csv.recent_days(0, _cfg(self.d)), [])


class 현재_상태는_오늘을_본다(unittest.TestCase):
    """★8월에 7월 데이터를 '현재 상태' 로 내놓던 그 자리."""

    def setUp(self):
        import server
        self.srv = server
        self.tmp = tempfile.TemporaryDirectory()
        self._base = store_csv.BASE_DIR
        store_csv.BASE_DIR = self.tmp.name
        self.d = os.path.join(self.tmp.name, "d")
        os.makedirs(self.d, exist_ok=True)
        # ★같은 dict 가 두 번 올 수 있다 (CFG 와 ctx cfg 가 한 객체일 때).
        #   그대로 두면 두 번째가 이미 바뀐 값을 '원래 값' 으로 기억해서
        #   tearDown 이 복구를 못 하고, 뒤 테스트가 엉뚱한 data/ 를 읽는다.
        seen, self._cfgs = set(), []
        for c in (server.CFG, server.get_ctx("ALL")["cfg"]):
            if id(c) in seen:
                continue
            seen.add(id(c))
            self._cfgs.append((c, c.get("storage", {}).get("daily_csv_dir")))
        for c, _prev in self._cfgs:
            c.setdefault("storage", {})["daily_csv_dir"] = "d"
        server._FAB_CMP_CACHE.update(key=None, at=0.0, out=None)
        self.today = datetime.now().strftime("%Y%m%d")

    def tearDown(self):
        for c, prev in self._cfgs:
            if prev is None:
                c["storage"].pop("daily_csv_dir", None)
            else:
                c["storage"]["daily_csv_dir"] = prev
        self.srv._FAB_CMP_CACHE.update(key=None, at=0.0, out=None)
        store_csv.BASE_DIR = self._base
        self.tmp.cleanup()

    def _compare(self):
        self.srv._FAB_CMP_CACHE.update(key=None, at=0.0, out=None)
        return self.srv.app.test_client().get("/api/fab/compare").get_json()

    def test_오늘이_있으면_오늘을_본다(self):
        _write(self.d, "20260728")
        _write(self.d, self.today)
        j = self._compare()
        self.assertEqual(j.get("day"), self.today, j.get("warn"))
        self.assertIsNone(j.get("fallback_day"))
        self.assertFalse(j.get("warn"))

    def test_오늘이_없으면_가장_최근으로_물러선다(self):
        """★예전엔 '가장 오래된 날' 로 물러섰다 — 7월 28일이 그래서 나왔다."""
        _write(self.d, "20260728")
        _write(self.d, "20260819")
        j = self._compare()
        self.assertEqual(j.get("day"), "20260819",
                         "가장 오래된 날을 골랐다 (예전 버그)")

    def test_물러섰으면_반드시_밝힌다(self):
        """★옛 값을 현재라고 내놓는 것이 이 시스템에서 제일 위험하다."""
        _write(self.d, "20260819")
        j = self._compare()
        self.assertEqual(j["fallback_day"]["asked_day"], self.today)
        self.assertEqual(j["fallback_day"]["used_day"], "20260819")
        self.assertIn("실시간이 아닙니다", j["warn"])
        self.assertIn("20260819", j["warn"])

    def test_오늘_파일이_비어_있으면_물러선다(self):
        """파일만 있고 행이 0 이면 '오늘 자료가 있다' 고 하면 안 된다."""
        _write(self.d, "20260819")
        _write(self.d, self.today, rows=0)
        j = self._compare()
        self.assertEqual(j.get("day"), "20260819")
        self.assertTrue(j.get("warn"))


class 옛_실수가_남아_있지_않다(unittest.TestCase):
    """★같은 실수가 네 곳에 있었다 — 다시 생기면 여기서 걸린다."""

    FILES = ("server.py", "contrib.py", "forecast.py", "fab_score.py")

    def test_최신순_목록에서_뒤를_집지_않는다(self):
        bad = []
        for fn in self.FILES:
            with open(os.path.join(BASE, fn), encoding="utf-8") as f:
                src = f.read()
            for m in re.finditer(r"list_days\([^)]*\)[^\n]*\[-\d+", src):
                line = src[:m.start()].count("\n") + 1
                bad.append("{}:{}".format(fn, line))
            for m in re.finditer(r"list_days\([^)]*\)\s*or\s*\[[^\n]*\]\)\[-1\]",
                                 src):
                bad.append("{}:{}".format(fn, src[:m.start()].count("\n") + 1))
        self.assertEqual(bad, [],
                         "list_days 는 최신순이다 — [-1] 은 가장 오래된 날이다: "
                         + ", ".join(bad))

    def test_이름_있는_함수를_쓴다(self):
        with open(os.path.join(BASE, "server.py"), encoding="utf-8") as f:
            src = f.read()
        i = src.index('@app.route("/api/fab/compare")')
        blk = src[i:i + 2600]
        self.assertIn("latest_day(cfg)", blk)
        self.assertIn('datetime.now().strftime("%Y%m%d")', blk)
        self.assertIn("fallback_day", blk)


if __name__ == "__main__":
    unittest.main()
