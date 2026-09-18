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

    def test_화면_파일도_늘_물어보게_한다(self):
        """현장: "서버에서는 잘 적용이 되는데 접속하는 html 에서 적용이 안 되네".
        Cache-Control 을 안 붙이면 브라우저가 제 마음대로(휴리스틱) 캐시해서
        **묻지도 않고** 옛 파일을 쓴다. no-cache 는 '쓰기 전에 물어봐라' 라
        안 바뀌었으면 304 한 줄로 끝난다."""
        i = self.s.index("def _etag(resp):")
        body = self.s[i:i + 900]
        self.assertIn('request.path.startswith("/static/")', body)
        self.assertIn('"no-cache, must-revalidate"', body)

    def _fn(self, name):
        """그 함수의 **코드만** — 다음 @app.route 앞까지, 설명(독스트링)은 뺀다.
        (설명에 옛 방식을 적어 둔 것까지 잡으면 시험이 거짓말을 한다)"""
        i = self.s.index(name)
        body = self.s[i:].split("\n@app.")[0]
        if '"""' in body:
            head, _, rest = body.partition('"""')
            body = head + rest.partition('"""')[2]
        return body

    def test_화면_한_장도_안_바뀌었으면_304(self):
        """★예전에는 no-store 로 아예 못 쓰게 막았다. 새 화면이 안 나오는
        사고는 막았지만, **안 바뀌었어도 매번 354KB 를 통째로** 다시 받았다.
        고객: "로드 할때 ... 느려져".

        no-cache 는 '쓰지 마라' 가 아니라 '쓰기 전에 물어봐라' 다 — 안
        바뀌었으면 304 한 줄(0 바이트), 바뀌었으면 새로 받는다. 새 화면이
        안 나오는 사고는 그대로 막힌다."""
        body = self._fn("def index():")
        self.assertIn('"no-cache, must-revalidate"', body)
        self.assertNotIn("no-store", body, "no-store 면 304 가 안 된다")
        self.assertIn("_HTML_CACHE.get_or_build", body, "파일을 매번 다시 읽는다")
        self.assertIn("http_cache.negotiate", body, "지문·304·gzip 을 안 탄다")
        self.assertIn('_HTML_CACHE = http_cache.JsonCache(', self.s)

    def test_바이트도_그대로_담긴다(self):
        """HTML 한 장처럼 JSON 이 아닌 응답도 같은 캐시를 쓸 수 있어야 한다."""
        self.assertIs(type(http_cache.dumps(b"<html>")), bytes)
        self.assertEqual(http_cache.dumps(b"<html>"), b"<html>")
        e = http_cache.JsonCache("h").get_or_build("k", (1, 2), lambda: b"<html>hi")
        self.assertEqual(e.body, b"<html>hi")

    def test_케이스_목록도_캐시를_탄다(self):
        """★화면이 **3초마다** 부른다. 캐시가 없어서 부를 때마다 케이스 전부를
        다시 직렬화하고 지문까지 내고는, 대개 304 라 그대로 버렸다.
        재 본 값(800건 = 2.9MB): 29.1ms × 20회/분 × 사람 수
        → 열이 보면 **오직 이것 하나에** 5.8초/분. 고객: "여러명이 들어오면 느려져"."""
        body = self._fn("def api_cases():")
        self.assertIn("_cached_json(CASES_CACHE", body)
        self.assertIn("st.rev", body, "판번호로 '바뀌었나' 를 가려야 한다")
        self.assertNotIn("jsonify(", body, "아직 매번 새로 만든다")
        self.assertIn('CASES_CACHE = http_cache.JsonCache(', self.s)
        sen = _read("sentinel.py")
        self.assertIn("self.rev = 0", sen)
        self.assertIn("self.rev += 1", sen, "저장할 때마다 판번호가 올라야 한다")

    def test_캐시_상태를_볼_수_있다(self):
        """어느 캐시가 잘 맞고 있는지 화면에서 볼 수 있어야 한다 — 안 그러면
        '캐시가 도는 건가' 를 또 추측으로 답하게 된다."""
        i = self.s.index('"caches":')
        line = self.s[i:i + 300]
        for c in ("FEED_CACHE", "CMP_CACHE", "CASES_CACHE",
                  "GRAPH_CACHE", "CONTRIB_CACHE", "_HTML_CACHE"):
            self.assertIn(c, line, c)

    def test_더블클릭_두_요청도_캐시를_탄다(self):
        """고객: "더블클릭할때 느려져". 구간 그래프(18.8ms·91KB)와
        기여도(17.7ms)를 같은 자리에서 다시 열 때마다 새로 만들었다."""
        for fn, cache in (("def api_graph():", "GRAPH_CACHE"),
                          ("def api_contrib():", "CONTRIB_CACHE")):
            body = self._fn(fn)
            self.assertIn("_cached_json(", body, fn)
            self.assertIn(cache, body, fn)
            self.assertIn("_days_sig(", body, fn + " — 원본이 바뀌면 다시 만들어야 한다")
            self.assertIn("ctype=", body, fn + " — JSON 이 아니다")
        # ★파일이 없으면 캐시를 안 쓴다 (없는 것을 '그대로' 라고 하면 안 된다)
        d = self._fn("def _days_sig(")
        self.assertIn("return None", d)

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
