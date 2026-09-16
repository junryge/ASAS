# -*- coding: utf-8 -*-
"""하루치 CSV 를 매번 통째로 받지 않는다 — 꼬리만 받는다.

무엇이 문제였나
    예측 잡이 1분에 한 줄씩 **덧붙이는** 파일을, 수집은 매 주기마다 처음부터
    끝까지 다시 받고 있었다. 오후가 되면 한 파일이 1.5MB 쯤 되고 시스템이
    여섯이라, 1분에 9MB 를 받아 새 줄 여섯 개를 얻었다. 하루 13GB 다.
    "데이터 들어오는 게 느리다" 의 실체가 이것이다.

무엇을 조심해야 하나
    그냥 이어 붙이면 위험하다 — 예측 잡이 파일을 통째로 다시 썼다면 앞부분이
    달라져 있는데 우리는 모르고 꿰맨다. 그래서 **이미 가진 꼬리를 같이 받아**
    그 자리가 똑같은지 확인한다. 하나라도 어긋나면 전체를 다시 받는다.
    틀린 데이터보다 느린 게 낫다.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from copy import deepcopy

from . import util  # noqa: F401
import jupyter_csv as J
from lp_client import load_config

MOCK = os.path.join(util.BASE, "tests", "mock_jupyter.py")
FIXTURE = os.path.join(util.BASE, "fixtures", "발동이벤트_샘플.csv")
PORT = 9917
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


def _mock(what, **q):
    qs = ("?" + "&".join(f"{k}={urllib.request.quote(str(v))}"
                         for k, v in q.items())) if q else ""
    with urllib.request.urlopen(
            f"http://127.0.0.1:{PORT}/mock/{what}{qs}", timeout=3) as r:
        return json.loads(r.read())


@unittest.skipUnless(os.path.isfile(FIXTURE), "샘플 CSV 없음")
class 꼬리만_받는다(unittest.TestCase):
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
        self.tmp = tempfile.mkdtemp(prefix="rttail")
        self.cfg = deepcopy(load_config())
        self.cfg["source"] = {"mode": "jupyter", "jupyter": {
            "enabled": True, "base_url": f"http://127.0.0.1:{PORT}",
            "path": "/files/x/{day}_발동이벤트.csv", "password": PW,
            "save_raw": False}}
        self.cfg.setdefault("storage", {})["daily_csv_dir"] = self.tmp
        self.cfg.setdefault("llm", {})["enabled"] = False
        # 세션·본문 캐시는 프로세스 전역이다 — 시험마다 깨끗하게 시작한다
        J._SESS.clear()
        J._BODY.clear()
        J._LAST_WIRE.clear()
        _mock("reset")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        J._BODY.clear()

    # ── 본 줄기 ──────────────────────────────────────────────────────
    def test_두_번째부터는_새로_붙은_만큼만_받는다(self):
        a, err = J.download("20260811", self.cfg)
        self.assertEqual(err, "")
        first, _tot = J.wire_bytes(J.cfg_of(self.cfg))
        _mock("append", line="새줄," * 10)
        b, err = J.download("20260811", self.cfg)
        self.assertEqual(err, "")
        wire, total = J.wire_bytes(J.cfg_of(self.cfg))
        self.assertEqual(first, len(a), "처음엔 전체를 받는다")
        self.assertLess(wire, total // 3, f"꼬리만 받아야 한다 {wire}/{total}")
        self.assertEqual(total, len(b))

    def test_이어_붙인_결과가_전체를_받은_것과_같다(self):
        """줄어드는 건 통신량뿐이어야 한다 — 바이트가 다르면 아래가 전부 흔들린다."""
        J.download("20260811", self.cfg)
        _mock("append", line="1,2,3")
        spliced, _ = J.download("20260811", self.cfg)
        J._BODY.clear()                       # 캐시를 버리고 전체로 다시
        whole, _ = J.download("20260811", self.cfg)
        self.assertEqual(spliced, whole)

    def test_Range_를_실제로_보낸다(self):
        J.download("20260811", self.cfg)
        _mock("append", line="a")
        J.download("20260811", self.cfg)
        self.assertTrue(any(h.startswith("bytes=") for h in _mock("append")["hits"]),
                        _mock("append")["hits"])

    # ── 안전 장치 — 틀린 데이터보다 느린 게 낫다 ───────────────────────
    def test_같은_길이로_다시_쓰면_전체를_다시_받는다(self):
        """★이게 제일 위험한 경우다. 길이가 그대로면 꼬리도 그대로라 겹침
        검사를 통과한다 — 그리고 우리는 옛 본문을 그대로 들고 있게 된다.
        시험을 쓰다가 실제로 잡았다. 그래서 '자랐는가' 를 같이 본다."""
        J.download("20260811", self.cfg)
        _mock("rewrite")                      # 앞 한 글자가 바뀐다 (길이 그대로)
        got, err = J.download("20260811", self.cfg)
        self.assertEqual(err, "")
        wire, total = J.wire_bytes(J.cfg_of(self.cfg))
        self.assertEqual(wire, total, "안 자랐으면 이어 붙일 근거가 없다")
        self.assertTrue(got.startswith(b"X"), got[:20])

    def test_꼬리가_어긋나면_전체를_다시_받는다(self):
        J.download("20260811", self.cfg)
        _mock("rewrite")                      # 앞부분이 바뀌고
        _mock("append", line="새줄")           # 자라기까지 한 경우
        # 꼬리 512바이트 안이 달라지면 그 자리에서 잡힌다. 그 밖이면 아래
        # '몇 번에 한 번은 전체' 가 따라잡는다 — 매번 확인할 길은 없다.
        J.download("20260811", self.cfg)
        J._BODY.clear()
        got, err = J.download("20260811", self.cfg)
        self.assertEqual(err, "")
        self.assertTrue(got.startswith(b"X"), got[:20])

    def test_몇_번에_한_번은_전체를_다시_읽는다(self):
        """'자라면서 앞부분도 바뀐' 경우까지 매번 확인할 길은 없다.
        주기적으로 맞춰 놓아, 어긋나도 그 몇 분 안에 제자리로 돌아온다."""
        self.cfg["source"]["jupyter"]["tail_full_every"] = 3
        J.download("20260811", self.cfg)
        fulls = 0
        for i in range(6):
            _mock("append", line=f"줄{i}")
            J.download("20260811", self.cfg)
            wire, total = J.wire_bytes(J.cfg_of(self.cfg))
            if wire == total:
                fulls += 1
        self.assertEqual(fulls, 2, "3번마다 한 번은 전체여야 한다")

    def test_파일이_줄어들면_전체를_다시_받는다(self):
        J.download("20260811", self.cfg)
        _mock("truncate")
        got, err = J.download("20260811", self.cfg)
        self.assertEqual(err, "")
        self.assertEqual(len(got), _mock("append")["size"] - len("x\n"))

    def test_서버가_Range_를_무시해도_돈다(self):
        """모든 파일서버가 Range 를 받는 건 아니다. 받으면 좋고, 아니면 그만이다."""
        J.download("20260811", self.cfg)
        _mock("norange")
        _mock("append", line="a,b")
        got, err = J.download("20260811", self.cfg)
        self.assertEqual(err, "")
        self.assertEqual(len(got), _mock("append")["size"] - len("x\n"))

    def test_설정으로_끌_수_있다(self):
        """현장에서 이상하면 되돌릴 손잡이가 있어야 한다."""
        self.cfg["source"]["jupyter"]["tail_fetch"] = False
        J.download("20260811", self.cfg)
        _mock("append", line="a")
        J.download("20260811", self.cfg)
        wire, total = J.wire_bytes(J.cfg_of(self.cfg))
        self.assertEqual(wire, total)

    def test_날짜가_바뀌면_이어_붙이지_않는다(self):
        """자정을 넘기면 다른 파일이다 — 어제 꼬리에 오늘을 붙이면 안 된다."""
        J.download("20260811", self.cfg)
        got, err = J.download("20260810", self.cfg)
        self.assertEqual(err, "")
        wire, total = J.wire_bytes(J.cfg_of(self.cfg))
        self.assertEqual(wire, total)

    def test_받아서_저장까지_그대로_된다(self):
        r = J.fetch_day("20260811", self.cfg, verbose=False)
        self.assertTrue(r["ok"], r.get("error"))
        n1 = r["rows"]
        r2 = J.fetch_day("20260811", self.cfg, verbose=False)
        self.assertTrue(r2["ok"], r2.get("error"))
        self.assertEqual(r2["rows"], n1, "꼬리로 받아도 하루치 전부가 나와야 한다")
        self.assertEqual(r2["written"], 0, "같은 분은 다시 안 쌓인다")


@unittest.skipUnless(os.path.isfile(FIXTURE), "샘플 CSV 없음")
class 로그인은_한_번만(unittest.TestCase):
    """여섯 시스템을 동시에 받기 시작하면 캐시가 빈 순간 여섯이 같이
    로그인하러 간다 — 왕복 두 번짜리가 여섯 벌이다."""

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

    def test_여섯이_동시에_와도_한_번(self):
        cfg = deepcopy(load_config())
        cfg["source"] = {"mode": "jupyter", "jupyter": {
            "enabled": True, "base_url": f"http://127.0.0.1:{PORT + 1}",
            "path": "/files/x/{day}_발동이벤트.csv", "password": PW}}
        J._SESS.clear()
        c = J.cfg_of(cfg)
        n, lock = [0], threading.Lock()
        real = J._login_fresh

        def counted(cc):
            with lock:
                n[0] += 1
            return real(cc)

        J._login_fresh = counted
        try:
            ths = [threading.Thread(target=lambda: J.login(c)) for _ in range(6)]
            for t in ths:
                t.start()
            for t in ths:
                t.join(10)
        finally:
            J._login_fresh = real
        self.assertEqual(n[0], 1, f"로그인이 {n[0]}번 일어났다")


if __name__ == "__main__":
    unittest.main()
