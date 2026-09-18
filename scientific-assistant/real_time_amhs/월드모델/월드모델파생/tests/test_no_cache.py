# -*- coding: utf-8 -*-
"""브라우저가 옛 화면을 붙들고 있으면 안 된다.

현장: "서버에서는 잘 적용이 되는데 접속하는 html 에서 적용이 안 되네".
파일은 새로 올라갔는데 화면이 예전 것이었다. 원인은 **캐시 헤더가 하나도
없었던 것**이다 —

  · Cache-Control 을 안 붙이면 브라우저가 제 마음대로(휴리스틱) 캐시한다.
    그 기간이 '마지막 수정 이후 지난 시간의 10%' 라, 오래된 파일일수록 더
    오래 붙들고 있는다. **묻지도 않고** 옛 것을 쓴다.
  · StaticFiles 는 ETag·Last-Modified 는 붙이지만 Cache-Control 은 안 붙인다.
    그래서 oht3d.js 를 새로 올려도 3D 가 예전 모습 그대로였다.

지키는 것
  · dashboard.html — 아예 저장하지 마라 (no-store). 한 장이라 부담이 없다.
  · /static — 쓰기 전에 **물어보고** 써라 (no-cache). 안 바뀌었으면 304 한 줄이라
    통신량은 거의 그대로다 (three.js 690KB 도 다시 안 받는다).
  · 이미 박혀 있는 옛 파일은 그 헤더를 받아 본 적이 없다 → 주소에 판 번호를
    붙여 '다른 파일' 로 만든다. 사용자가 Ctrl+Shift+R 을 안 눌러도 된다.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)


def _read(*p):
    with open(os.path.join(APP, *p), encoding="utf-8") as fh:
        return fh.read()


class 화면_HTML(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _read("main.py")

    def test_저장하지_말라고_말한다(self):
        i = self.m.index("async def dashboard():")
        body = self.m[i:i + 1400]
        self.assertIn("HTMLResponse(f.read(), headers=", body,
                      "글자만 돌려주면 헤더를 못 붙인다")
        for k in ("no-store", "no-cache", "must-revalidate", "max-age=0"):
            self.assertIn(k, body, k + " 가 없다")
        self.assertIn('"Pragma": "no-cache"', body, "옛 브라우저용")

    def test_왜_그랬는지_적어_뒀다(self):
        """다음 사람이 '한 장인데 왜 캐시를 끄지' 하고 되돌리면 또 겪는다."""
        i = self.m.index("async def dashboard():")
        self.assertIn("휴리스틱", self.m[i:i + 1400])


class 정적파일(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _read("main.py")

    def test_늘_물어보게_한다(self):
        self.assertIn("class _NoCacheStatic(StaticFiles):", self.m)
        i = self.m.index("class _NoCacheStatic(StaticFiles):")
        body = self.m[i:i + 1200]
        self.assertIn("def file_response(self, *a, **k):", body)
        self.assertIn('r.headers["Cache-Control"] = "no-cache, must-revalidate"', body)

    def test_실제로_그걸_쓴다(self):
        """클래스만 만들어 두고 안 쓰면 아무 일도 안 일어난다."""
        self.assertIn('app.mount("/static", _NoCacheStatic(directory=str(_STATIC_DIR))', self.m)
        self.assertNotIn('app.mount("/static", StaticFiles(', self.m, "옛 길이 남아 있다")

    def test_no_store_가_아니다(self):
        """★정적 파일까지 no-store 로 막으면 three.js 690KB 를 **매번** 받는다.
        no-cache 는 '쓰기 전에 물어봐라' 라 안 바뀌었으면 304 로 끝난다."""
        i = self.m.index("class _NoCacheStatic(StaticFiles):")
        self.assertNotIn("no-store", self.m[i:i + 1200])


class 이미_박힌_옛_파일(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = _read("dashboard.html")

    def test_주소에_판_번호를_붙인다(self):
        self.assertRegex(self.h, r"const V3D_BUILD = '[\w.-]+';")
        self.assertIn("import('/static/js/oht3d/oht3d.js?v=' + V3D_BUILD)", self.h)

    def test_three_는_판_번호를_안_탄다(self):
        """three.js 는 oht3d.js 안에서 상대경로로 부른다 — 690KB 를 매번 받으면 안 된다."""
        j = _read("static", "js", "oht3d", "oht3d.js")
        self.assertIn("threeUrl: './three.module.min.js'", j)
        self.assertNotIn("three.module.min.js?v=", self.h)
        self.assertNotIn("three.module.min.js?v=", j)

    def test_올릴_때_같이_올리라고_적어_뒀다(self):
        self.assertIn("고쳐 올릴 때 이 숫자를 같이 올려라", self.h)


if __name__ == "__main__":
    unittest.main()
