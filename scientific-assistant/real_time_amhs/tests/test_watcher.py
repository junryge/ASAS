# -*- coding: utf-8 -*-
"""상시 감시 — 브라우저가 없어도 서버가 계속 본다.

왜 필요했나
    watch() 는 브라우저가 /api/fab/status 를 폴링할 때만 돌았다. 창을 닫으면
    아무도 안 본다 — 밤에 알람이 떴다 사라져도 이력에 한 줄도 안 남는다.
    "실행시키면 보고 있는 걸로 하면 안 된다" 가 그 지적이다.

여기서 못 박는 것
    1. 서버가 스스로 돈다 (브라우저 요청이 한 번도 없어도)
    2. 이력이 쌓인다 (알람 발생·해제가 기록된다)
    3. 안 죽는다 (관제가 끊겨도, 예외가 나도 계속 본다)
    4. 화면이 알 수 있다 (멎었으면 멎었다고 나온다 — 조용히 멈추면 안 된다)
"""
import os
import sys
import time
import unittest

from . import util

sys.path.insert(0, os.path.join(util.BASE, "avatar_2d"))
from avatar import config, sentinel   # noqa: E402


class _감시(unittest.TestCase):
    """watch() 를 가짜로 바꿔 두고 스레드만 시험한다."""

    def setUp(self):
        self.calls = []
        self._real = sentinel.watch
        self.addCleanup(lambda: setattr(sentinel, "watch", self._real))
        self.addCleanup(sentinel.stop_watch)
        # ★진짜 하한은 2초다 (관제를 두들기지 않게). 시험을 2초 × N 으로
        #   돌리면 몇 분이 걸린다 — 하한만 낮추고 하한 자체는 따로 못 박는다.
        self._minsec = sentinel.WATCH_MIN_SEC
        sentinel.WATCH_MIN_SEC = 0.005
        self.addCleanup(lambda: setattr(sentinel, "WATCH_MIN_SEC",
                                        self._minsec))

    def fake(self, *results):
        """부를 때마다 results 를 차례로 준다 (마지막 것은 계속 반복)."""
        seq = list(results)

        def w():
            self.calls.append(time.time())
            return seq[min(len(self.calls) - 1, len(seq) - 1)]
        sentinel.watch = w

    def start(self, period=0.02, say=None):
        self.said = []
        w = sentinel.start_watch(period, say or self.said.append)
        self.addCleanup(w.stop)
        return w

    def until(self, cond, sec=3.0):
        end = time.time() + sec
        while time.time() < end:
            if cond():
                return True
            time.sleep(0.01)
        return False


OK = {"ok": True, "alarms": [], "at": "2026-08-26 04:00", "err": ""}
BAD = {"ok": False, "alarms": [], "at": "", "err": "관제 안 붙음"}


def alarm(fab, level, score):
    return {"ok": True, "at": "2026-08-26 04:00", "err": "",
            "alarms": [{"fab": fab, "level": level, "score": score}]}


# ═══ 1. 스스로 돈다 ══════════════════════════════════════════════════════
class 브라우저_없이_돈다(_감시):

    def test_요청이_한_번도_없어도_본다(self):
        """★이게 전부다 — 예전에는 여기서 0회였다."""
        self.fake(OK)
        self.start(0.02)
        self.assertTrue(self.until(lambda: len(self.calls) >= 3),
                        "서버가 스스로 안 본다")

    def test_주기대로_본다(self):
        self.fake(OK)
        self.start(0.05)
        self.until(lambda: len(self.calls) >= 4)
        gaps = [b - a for a, b in zip(self.calls, self.calls[1:])]
        self.assertGreater(min(gaps), 0.02, "주기를 안 지키고 몰아친다")

    def test_너무_짧은_주기는_막는다(self):
        """★0.001초를 넣으면 관제 서버를 초당 1000번 두들긴다."""
        sentinel.WATCH_MIN_SEC = self._minsec        # 진짜 하한으로 되돌리고
        self.assertGreaterEqual(sentinel.WATCH_MIN_SEC, 2.0, "하한이 너무 낮다")
        self.fake(OK)
        self.assertGreaterEqual(self.start(0.001).period_s,
                                sentinel.WATCH_MIN_SEC)

    def test_멈추면_그만_본다(self):
        self.fake(OK)
        w = self.start(0.02)
        self.until(lambda: len(self.calls) >= 2)
        w.stop()
        n = len(self.calls)
        time.sleep(0.15)
        self.assertLessEqual(len(self.calls) - n, 1, "멈췄는데 계속 본다")
        self.assertFalse(w.is_alive())

    def test_두_번_켜도_하나만_돈다(self):
        self.fake(OK)
        a = self.start(0.05)
        b = sentinel.start_watch(0.05, lambda *_: None)
        self.assertIs(a, b, "감시 스레드가 두 개 돈다")


# ═══ 2. 안 죽는다 ════════════════════════════════════════════════════════
class 무슨_일이_있어도_안_멎는다(_감시):

    def test_관제가_끊겨도_계속_본다(self):
        """★끊긴 동안 멈추면, 복구된 순간을 아무도 못 본다."""
        self.fake(BAD)
        w = self.start(0.02)
        self.assertTrue(self.until(lambda: w.fails >= 3))
        self.assertTrue(w.is_alive())

    def test_예외가_나도_스레드가_산다(self):
        """★죽으면 소리 없이 감시가 멎고, 화면은 여전히 '보고 있음' 이다."""
        n = [0]

        def boom():
            n[0] += 1
            raise RuntimeError("펑")
        sentinel.watch = boom
        w = self.start(0.02)
        self.assertTrue(self.until(lambda: n[0] >= 3), "한 번 터지고 멎었다")
        self.assertTrue(w.is_alive())
        self.assertEqual(w.fails, n[0])
        self.assertIn("펑", w.last_err)

    def test_끊겼다_붙으면_다시_센다(self):
        self.fake(BAD, BAD, OK)
        w = self.start(0.02)
        self.assertTrue(self.until(lambda: w.last_ok))
        self.assertGreaterEqual(w.fails, 2)


# ═══ 3. 이력이 쌓인다 ════════════════════════════════════════════════════
class 창을_닫아도_이력이_쌓인다(_감시):

    def setUp(self):
        _감시.setUp(self)
        import tempfile
        d = tempfile.mkdtemp()
        sentinel.init(d)
        sentinel._last_levels = {}

    def test_발생이_기록된다(self):
        """★브라우저가 한 번도 안 물어봤는데 이력에 남아야 한다."""
        self.fake(alarm("M16HUB", "위험", 72))
        # watch() 를 가짜로 바꿨으니 _record 는 직접 돈다 — 진짜 경로로 확인
        sentinel.watch = self._real
        real = sentinel.compare
        sentinel.compare = lambda force=False: {
            "ok": True, "err": "", "degraded": False, "held_s": 0,
            "data": {"at": time.strftime("%Y-%m-%d %H:%M"),
                     "rows": [{"fab": "M16HUB", "level": "위험", "score": 72}]}}
        self.addCleanup(lambda: setattr(sentinel, "compare", real))
        self.start(0.02)
        self.assertTrue(self.until(
            lambda: any(e["fab"] == "M16HUB" for e in sentinel.history(20))),
            "상시 감시가 이력을 안 남긴다")
        e = [x for x in sentinel.history(20) if x["fab"] == "M16HUB"][-1]
        self.assertEqual(e["level"], "위험")
        self.assertEqual(e["kind"], "on")


# ═══ 4. 화면이 알 수 있다 ════════════════════════════════════════════════
class 보고_있는지_화면이_안다(_감시):

    def test_안_켰으면_꺼짐으로_나온다(self):
        sentinel.stop_watch()
        st = sentinel.watch_status()
        self.assertFalse(st["on"])
        self.assertEqual(st["ticks"], 0)

    def test_켜면_켜짐으로_나온다(self):
        self.fake(OK)
        self.start(0.02)
        self.assertTrue(self.until(lambda: sentinel.watch_status()["ticks"] >= 2))
        st = sentinel.watch_status()
        self.assertTrue(st["on"])
        self.assertIsNotNone(st["last_ago_s"])

    def test_죽으면_꺼짐으로_나온다(self):
        """★스레드가 죽었는데 화면만 '감시 중' 이면 그냥 넘어간다."""
        self.fake(OK)
        w = self.start(0.02)
        self.until(lambda: w.ticks >= 1)
        w.stop()
        self.assertFalse(sentinel.watch_status()["on"], "죽었는데 켜짐으로 나온다")

    def test_관제가_끊겨도_감시는_켜짐이다(self):
        """★'관제가 죽은 것' 과 '우리가 아예 안 보는 것' 은 다른 사고다."""
        self.fake(BAD)
        self.start(0.02)
        self.assertTrue(self.until(lambda: sentinel.watch_status()["ticks"] >= 2))
        st = sentinel.watch_status()
        self.assertTrue(st["on"])
        self.assertFalse(st["ok"])


# ═══ 5. 등급이 바뀔 때만 말한다 ══════════════════════════════════════════
class 소음을_안_낸다(_감시):

    def test_같은_등급은_한_번만_적는다(self):
        """★폴링마다 적으면 로그가 아니라 소음이다."""
        self.fake(alarm("M14", "경계", 61))
        w = self.start(0.02)
        self.until(lambda: w.ticks >= 5)
        got = [s for s in self.said if "M14" in s]
        self.assertEqual(len(got), 1, "같은 등급을 계속 적는다: {}".format(got))

    def test_등급이_바뀌면_다시_적는다(self):
        self.fake(alarm("M14", "경계", 61), alarm("M14", "위험", 75))
        w = self.start(0.02)
        self.until(lambda: w.ticks >= 3)
        self.assertTrue(any("위험" in s for s in self.said))

    def test_정상_복귀도_적는다(self):
        """★올라간 것만 적고 내려온 걸 안 적으면 언제 풀렸는지 모른다."""
        self.fake(alarm("M14", "경계", 61), OK)
        w = self.start(0.02)
        self.until(lambda: w.ticks >= 3)
        self.assertTrue(any("정상 복귀" in s for s in self.said),
                        "복귀를 안 적는다: {}".format(self.said))


# ═══ 6. 설정·연결 ════════════════════════════════════════════════════════
class 설정과_연결(unittest.TestCase):

    def test_주기가_설정에_있다(self):
        """★코드에만 있으면 '왜 10초냐' 를 아무도 못 고친다."""
        self.assertIn("watch_sec", config.SENTINEL)
        self.assertGreater(float(config.SENTINEL["watch_sec"]), 0)

    def test_서버가_켠다(self):
        import ast
        p = os.path.join(util.BASE, "avatar_2d", "avatar", "server.py")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("sentinel.start_watch(", src, "서버가 감시를 안 켠다")
        ast.parse(src)

    def test_상태를_화면에_준다(self):
        p = os.path.join(util.BASE, "avatar_2d", "avatar", "server.py")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        i = src.index("/api/fab/status")
        self.assertIn("watch_status()", src[i:i + 400],
                      "화면이 감시 상태를 못 받는다")

    def test_화면이_그린다(self):
        p = os.path.join(util.BASE, "avatar_2d", "static", "app.js")
        with open(p, encoding="utf-8") as f:
            js = f.read()
        self.assertIn("s.watching", js, "화면이 감시 상태를 안 읽는다")
        self.assertIn("상시 감시 멈춤", js, "멎은 것을 안 보여 준다")
        # ★TDZ — 선언이 쓰는 곳보다 뒤에 있으면 스크립트 전체가 죽는다
        self.assertLess(js.index("let watching"), js.index("const w = watching"),
                        "watching 을 선언 전에 쓴다 (TDZ)")


if __name__ == "__main__":
    unittest.main()
