# -*- coding: utf-8 -*-
"""느린 화면 — 같은 것을 두 번 만들지 않게 했나.

2026-09-18 현장 로그: /api/feed 7~17초, /api/fab/compare 18~20초.
개발 PC 에서 하루치(1440행)로 재 보니 계산 자체는 ~300ms 였다. 느린 이유는
셋이었다 —
  ① 캐시가 적중해도 1.5MB 를 매번 다시 직렬화했다 (dict 를 캐시했으니까)
  ② 화면은 3초마다 묻는데 데이터는 60초에 한 번 바뀐다 (헛걸음 19/20)
  ③ 파일이 바뀌는 순간 화면 셋이 **동시에** 같은 것을 만들었다
여기서는 그 셋이 실제로 막혔는지만 본다 — 점수·등급·판정은 안 건드린다.
"""
import gzip
import json
import os
import threading
import time
import unittest

import http_cache

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)


def _read(*p):
    with open(os.path.join(APP, *p), encoding="utf-8") as fh:
        return fh.read()


class 글자로_들고_있는다(unittest.TestCase):
    def test_한글은_그대로_담는다(self):
        """★ensure_ascii 면 한글 한 글자가 여섯 자가 된다 — 1.5MB 가 3MB 넘게
        부푼다. 그대로 담고 charset=utf-8 로 내보낸다."""
        b = http_cache.dumps({"말": "가나다"})
        self.assertIn("가나다".encode("utf-8"), b)
        self.assertNotIn(b"\\u", b)

    def test_공백을_안_넣는다(self):
        self.assertEqual(http_cache.dumps({"a": 1, "b": 2}), b'{"a":1,"b":2}')

    def test_지문은_내용이_같으면_같다(self):
        a = http_cache.dumps({"x": [1, 2, 3]})
        self.assertEqual(http_cache.etag_of(a), http_cache.etag_of(bytes(a)))
        self.assertNotEqual(http_cache.etag_of(a), http_cache.etag_of(a + b" "))


class 두_번_만들지_않는다(unittest.TestCase):
    def test_지문이_같으면_안_만든다(self):
        c, n = http_cache.JsonCache("t"), [0]

        def build():
            n[0] += 1
            return {"n": n[0]}
        c.get_or_build("k", (1, 2), build)
        c.get_or_build("k", (1, 2), build)
        c.get_or_build("k", (1, 2), build)
        self.assertEqual(n[0], 1)

    def test_지문이_바뀌면_다시_만든다(self):
        c, n = http_cache.JsonCache("t"), [0]

        def build():
            n[0] += 1
            return {"n": n[0]}
        c.get_or_build("k", (1, 2), build)
        c.get_or_build("k", (9, 9), build)
        self.assertEqual(n[0], 2)

    def test_키가_다르면_따로_들고_있는다(self):
        c = http_cache.JsonCache("t")
        a = c.get_or_build("ALL", (1,), lambda: {"s": "ALL"})
        b = c.get_or_build("M14", (1,), lambda: {"s": "M14"})
        self.assertNotEqual(a.etag, b.etag)
        self.assertEqual(c.get_or_build("ALL", (1,), lambda: {"s": "X"}).body, a.body)

    def test_지문이_없으면_캐시를_안_쓴다(self):
        """원본 파일을 못 읽은 상황. 옛 값을 새 값인 척 내면 안 된다."""
        c, n = http_cache.JsonCache("t"), [0]

        def build():
            n[0] += 1
            return {"n": n[0]}
        c.get_or_build("k", None, build)
        c.get_or_build("k", None, build)
        self.assertEqual(n[0], 2)

    def test_동시에_들어와도_한_번만_만든다(self):
        """★캐시 우르르(stampede) — 파일이 바뀌는 순간 화면 셋이 같이 들어온다.
        예전엔 셋이 각자 1.5MB 를 만들었다."""
        c, n, lk = http_cache.JsonCache("t"), [0], threading.Lock()

        def build():
            with lk:
                n[0] += 1
            time.sleep(0.25)               # 무거운 계산 흉내
            return {"big": "가" * 1000}
        ts = [threading.Thread(target=lambda: c.get_or_build("k", (1,), build))
              for _ in range(12)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(n[0], 1, "동시 요청 12개가 각자 만들면 안 된다")
        self.assertEqual(c.stats()["joined"], 11)

    def test_만드는_중에_터져도_다음_요청이_산다(self):
        c = http_cache.JsonCache("t")

        def boom():
            raise ValueError("계산 실패")
        with self.assertRaises(ValueError):
            c.get_or_build("k", (1,), boom)
        e = c.get_or_build("k", (1,), lambda: {"ok": 1})
        self.assertIn(b'"ok":1', e.body)


class 브라우저가_이미_갖고_있으면(unittest.TestCase):
    def setUp(self):
        self.e = http_cache.Entry((1,), http_cache.dumps({"가": "나" * 9000}))

    def test_지문이_같으면_304_본문없음(self):
        code, body, hdr = http_cache.negotiate(self.e, self.e.etag, "gzip")
        self.assertEqual(code, 304)
        self.assertEqual(body, b"")
        self.assertEqual(hdr["ETag"], self.e.etag)

    def test_여러_지문을_보내와도_알아본다(self):
        inm = 'W/"aaa", %s' % self.e.etag
        self.assertEqual(http_cache.negotiate(self.e, inm, None)[0], 304)

    def test_지문이_다르면_200(self):
        self.assertEqual(http_cache.negotiate(self.e, 'W/"다른것"', None)[0], 200)

    def test_no_cache_를_붙인다(self):
        """★'쓰지 마라' 가 아니라 '쓰기 전에 물어봐라'. 그래야 브라우저가
        If-None-Match 를 들고 와서 304 를 받는다."""
        self.assertEqual(http_cache.negotiate(self.e, None, None)[2]["Cache-Control"],
                         "no-cache")

    def test_gzip_을_받으면_눌러_보낸다(self):
        code, body, hdr = http_cache.negotiate(self.e, None, "gzip, deflate, br")
        self.assertEqual(code, 200)
        self.assertEqual(hdr["Content-Encoding"], "gzip")
        self.assertEqual(hdr["Vary"], "Accept-Encoding")
        self.assertLess(len(body), len(self.e.body) / 3, "눌렀는데 별로 안 줄었다")
        self.assertEqual(gzip.decompress(body), self.e.body)
        self.assertEqual(hdr["Content-Length"], str(len(body)))

    def test_gzip_은_한_번만_누른다(self):
        self.e.gz()
        g1 = self.e.gz()
        self.assertIs(g1, self.e.gz())

    def test_gzip_을_못_받으면_원문(self):
        _, body, hdr = http_cache.negotiate(self.e, None, None)
        self.assertNotIn("Content-Encoding", hdr)
        self.assertEqual(body, self.e.body)

    def test_작은_것은_안_누른다(self):
        e = http_cache.Entry((1,), b'{"a":1}')
        self.assertIsNone(e.gz())
        self.assertNotIn("Content-Encoding", http_cache.negotiate(e, None, "gzip")[2])


class 서버에_제대로_붙었나(unittest.TestCase):
    """server.py 를 import 하려면 flask 가 있어야 한다 — 글로 확인한다."""

    @classmethod
    def setUpClass(cls):
        cls.s = _read("server.py")

    def test_feed_가_글자캐시를_쓴다(self):
        self.assertIn('FEED_CACHE = http_cache.JsonCache("feed")', self.s)
        self.assertIn('return _cached_json(FEED_CACHE, C["sys"], _sig, _build)', self.s)
        self.assertNotIn("FEED_CACHE[C[\"sys\"]] = (_sig, payload)", self.s,
                         "dict 를 캐시하던 옛 길이 남아 있다")

    def test_compare_는_시간이_아니라_파일지문으로_잡는다(self):
        """★예전 TTL 3초. 아바타는 10초마다 묻는다 — 한 번도 안 맞았다."""
        self.assertNotIn("_FAB_CMP_TTL", self.s)
        self.assertIn('CMP_CACHE = http_cache.JsonCache("fab_compare")', self.s)
        i = self.s.index("def api_fab_compare(")
        body = self.s[i:i + 3000]
        self.assertIn("fab_score.files_sig(day, cfg)", body, "FAB 분리 파일도 지문에")
        self.assertIn("_st.st_mtime_ns", body, "ALL 파일도 지문에")
        self.assertIn("return _cached_json(CMP_CACHE,", body)

    def test_나머지_api_도_304_를_쓴다(self):
        i = self.s.index("def _etag(resp):")
        body = self.s[i:i + 1800]
        self.assertIn('request.method != "GET"', body, "POST 는 건드리면 안 된다")
        self.assertIn('resp.status_code != 200', body)
        self.assertIn('resp.headers.get("ETag")', body, "이미 지문이 붙었으면 건너뛴다")
        self.assertIn("resp.status_code = 304", body)
        self.assertIn("Content-Encoding", body)

    def test_캐시_상태를_볼_수_있다(self):
        self.assertIn('"caches": [c.stats() for c in (FEED_CACHE, CMP_CACHE)]', self.s)

    def test_수집이_어디서_느린지_나눠_적는다(self):
        """'48초 걸렸다' 만으로는 우리 코드인지 주피터인지 모른다."""
        j = _read("jupyter_csv.py")
        self.assertIn("def last_timing(", j)
        for k in ('"net"', '"parse"', '"save"'):
            self.assertIn(k, j)
        self.assertIn("last_timing", self.s)
        self.assertIn("받기 ", self.s)

    def test_폴더는_한_번만_만든다(self):
        c = _read("store_csv.py")
        self.assertIn("_MADE: set = set()", c)
        i = c.index("def data_dir(")
        self.assertIn("if d not in _MADE:", c[i:i + 900])


class 점수는_안_건드린다(unittest.TestCase):
    def test_계산_파일에_캐시_코드가_없다(self):
        for f in ("fab_score.py", "sentinel.py", "alarm_count.py"):
            self.assertNotIn("http_cache", _read(f), f + " 는 이번 변경과 무관해야 한다")


if __name__ == "__main__":
    unittest.main()
