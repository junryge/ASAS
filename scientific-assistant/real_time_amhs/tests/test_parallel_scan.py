# -*- coding: utf-8 -*-
"""여섯 시스템을 한 줄로 세우지 않는다.

무엇이 문제였나
    기동도 수집도 `for sys in systems():` 였다. 한 시스템이 2초 걸리면 한
    바퀴가 12초다 — 주기가 60초라도 화면에 도착하는 시각이 계단처럼 밀리고,
    게이트웨이가 느린 날엔 주기를 통째로 넘겼다. 시스템마다 파일도 저장소도
    다르니 서로 기다릴 이유가 없다.

왜 이렇게 시험하나
    server.py 는 flask 를 module 단에서 부른다 — 이 환경엔 flask 가 없어
    import 가 안 된다. 그래서 _fan_out 의 **소스를 떼어 내** 그 자리에서
    돌린다. 소스만 훑는 시험은 "썼다" 만 보고 "제대로 도는가" 는 못 본다.
"""
import os
import re
import threading
import time
import unittest

from . import util  # noqa: F401

SRV = os.path.join(util.BASE, "server.py")


def _src() -> str:
    return open(SRV, encoding="utf-8").read()


def _func(name: str):
    """server.py 에서 함수 하나만 떼어 내 그 자리에서 쓸 수 있게 만든다."""
    src = _src()
    m = re.search(rf"^def {re.escape(name)}\(.*?(?=^def |\Z)", src,
                  re.S | re.M)
    assert m, name
    ns: dict = {}
    exec(compile(m.group(0), SRV, "exec"), ns)      # noqa: S102
    return ns[name]


class 동시에_돈다(unittest.TestCase):
    def setUp(self):
        self.fan = _func("_fan_out")

    def test_한_줄로_세우지_않는다(self):
        """여섯을 줄 세우면 6×0.2=1.2초, 같이 돌면 0.2초쯤이다."""
        seen = []
        lock = threading.Lock()

        def slow(x):
            time.sleep(0.2)
            with lock:
                seen.append(x)

        t0 = time.time()
        self.fan(slow, list(range(6)))
        el = time.time() - t0
        self.assertEqual(sorted(seen), list(range(6)), "여섯 다 돌아야 한다")
        self.assertLess(el, 0.9, f"줄 세우고 있다 ({el:.2f}초)")

    def test_하나가_터져도_나머지는_간다(self):
        """한 시스템 파일이 없다고 나머지 다섯이 멈추면 안 된다."""
        done = []

        def maybe(x):
            try:
                if x == 2:
                    raise RuntimeError("그 날짜 파일 없음")
            except RuntimeError:
                return                  # 진짜 scan/one 도 자기 예외를 삼킨다
            done.append(x)

        self.fan(maybe, list(range(5)))
        self.assertEqual(sorted(done), [0, 1, 3, 4])

    def test_하나뿐이면_스레드를_안_만든다(self):
        """로그프레소 모드는 ALL 하나다 — 풀을 띄울 이유가 없다."""
        me = threading.current_thread().name
        where = []
        self.fan(lambda x: where.append(threading.current_thread().name), ["ALL"])
        self.assertEqual(where, [me])

    def test_빈_목록도_받는다(self):
        self.fan(lambda x: None, [])


class 줄_세우던_자리가_없다(unittest.TestCase):
    """소스에 옛 for 루프가 남아 있으면 둘 중 하나만 고친 것이다."""

    def setUp(self):
        self.src = _src()

    def test_기동도_수집도_fan_out_을_쓴다(self):
        self.assertEqual(self.src.count("_fan_out("), 3)   # 정의 1 + 부름 2

    def test_옛_직렬_루프가_안_남아_있다(self):
        self.assertNotIn("for sys in ss:", self.src)
        self.assertNotIn("for i, sys in enumerate(systems()):", self.src)

    def test_받은_바이트를_로그에_남긴다(self):
        """'느리다' 는 말에 숫자를 붙일 수 있어야 한다."""
        self.assertIn("def _wire(", self.src)
        self.assertIn("_wire(ctx)", self.src)


if __name__ == "__main__":
    unittest.main()
