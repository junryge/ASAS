# -*- coding: utf-8 -*-
"""여럿이 같이 봐도 서로 안 섞인다 — 접속자마다 제 상태.

고객: "월드모델파생 여러사람이 접속할껀데 지금 1사람이 접속하면 다른사람이
       접속하면 1사람이 한내용이 보여. 그런게 안되게해줘."

무엇이 문제였나
  엔진(ReplayEngine)·고른 FAB/prefix·조회 번호가 **모듈 전역 하나**였다.
  한 대 서버에 여럿이 붙으면
    · A 가 부른 날짜를 B 가 보고
    · B 가 누른 정지가 A 의 재생을 멈추고
    · 한 사람이 '조회 멈춤' 을 누르면 그때 돌던 **남의 조회까지** 죽었다
    · 한 사람이 FAB 을 바꾸면 다른 사람 맵까지 넘어갔다

어떻게 보나
  ★이 환경에는 fastapi 가 없다(폐쇄망 배포본만 있으면 된다). 그래서 글자로만
    보지 않고, main.py 의 **세션 부분을 그대로 떼어** 가짜 엔진과 함께 돌린다
    (tests/iso3d.js·cut_color.js 와 같은 수법 — 베낀 코드가 아니라 배포되는
    그 코드를 본다).
"""
import os
import re
import shutil
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)


def _read(*p):
    with open(os.path.join(APP, *p), encoding="utf-8") as fh:
        return fh.read()


MAIN = _read("main.py")


def _session_code():
    """main.py 의 세션 절 — SESSION_COOKIE 부터 미들웨어 직전까지,
    그리고 뒤쪽에 따로 있는 조회 멈춤 판정(_lp_should_cancel)."""
    i = MAIN.index("SESSION_COOKIE = ")
    j = MAIN.index('@app.middleware("http")')
    k = MAIN.index("def _lp_should_cancel(")
    lp = MAIN[k:MAIN.index("\n\n\n", k)]
    return MAIN[i:j] + "\n\n" + lp


class _FakeEngine:
    """가짜 엔진 — 누구 것인지만 알면 된다."""
    _n = 0

    def __init__(self, layout, hid):
        _FakeEngine._n += 1
        self.id = _FakeEngine._n
        self.layout = layout
        self.hid = hid
        self.stopped = False
        self.loaded = None

    def stop(self):
        self.stopped = True

    def load_date(self, key, cfg=None):
        self.loaded = key
        return {"ok": True}


class _Env:
    """세션 절을 돌릴 한 벌. 시험마다 새로 만든다(전역이 안 새게)."""

    def __init__(self, tmp, ttl=3600, mx=24):
        self.loads = []                       # _load_fab 이 몇 번 불렸나
        g = {
            "os": os, "shutil": shutil, "secrets": __import__("secrets"),
            "threading": __import__("threading"), "_time": time,
            "print": lambda *a, **k: None,
            "Request": object,
            "ReplayEngine": _FakeEngine,
            "DEFAULT_FAB": "M14A", "DEFAULT_PREFIX": "A",
            "LOGPRESSO_CACHE_DIR": tmp,
            "_load_fab": self._load_fab,
        }
        code = _session_code()
        # 환경변수 대신 시험이 정한 값으로
        code = code.replace('int(os.environ.get("OHT_SESSION_TTL", 3600))', str(ttl))
        code = code.replace('int(os.environ.get("OHT_SESSION_MAX", 24))', str(mx))
        exec(compile(code, "main.py[session]", "exec"), g)
        self.g = g

    def _load_fab(self, fab, prefix):
        self.loads.append((fab, prefix))
        return ({"fab": fab, "prefix": prefix}, {"hid": fab})

    def __getattr__(self, k):
        return self.g[k]


class 사람마다_제_엔진(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ohtsess")
        self.e = _Env(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_다른_사람은_다른_엔진(self):
        a, fa = self.e.get_session(None)
        b, fb = self.e.get_session(None)
        self.assertTrue(fa and fb, "둘 다 새로 만들어져야 한다")
        self.assertNotEqual(a.sid, b.sid)
        self.assertIsNot(a.engine, b.engine, "★엔진을 같이 쓰면 남의 화면이 보인다")

    def test_같은_사람은_같은_엔진(self):
        a, _ = self.e.get_session(None)
        again, fresh = self.e.get_session(a.sid)
        self.assertIs(again, a)
        self.assertFalse(fresh, "이미 있는 사람에게 새 쿠키를 주면 안 된다")

    def test_모르는_쿠키는_새로_만든다(self):
        s, fresh = self.e.get_session("없는쿠키")
        self.assertTrue(fresh)
        self.assertNotEqual(s.sid, "없는쿠키", "남이 준 값을 그대로 쓰면 안 된다")

    def test_한_사람이_부른_날짜가_남에게_안_보인다(self):
        a, _ = self.e.get_session(None)
        b, _ = self.e.get_session(None)
        a.engine.load_date("20260916")
        self.assertEqual(a.engine.loaded, "20260916")
        self.assertIsNone(b.engine.loaded, "★남이 부른 데이터가 내 화면에 있다")

    def test_한_사람이_FAB_을_바꿔도_남은_그대로(self):
        a, _ = self.e.get_session(None)
        b, _ = self.e.get_session(None)
        old_b = b.engine
        a.select_fab("M16A", "A")
        self.assertEqual(a.fab, "M16A")
        self.assertEqual(b.fab, "M14A", "★남이 바꾼 FAB 이 내 화면에 왔다")
        self.assertIs(b.engine, old_b, "남의 엔진을 갈아치웠다")
        self.assertIs(b.layout, self.e.get_layout("M14A", "A")[0])

    def test_FAB_을_바꾸면_제_엔진은_다시_세운다(self):
        a, _ = self.e.get_session(None)
        old = a.engine
        a.select_fab("M16A", "A")
        self.assertIsNot(a.engine, old)
        self.assertTrue(old.stopped, "옛 엔진을 세우지 않으면 뒤에서 계속 돈다")

    def test_로그프레소_폴더도_사람마다(self):
        """같은 구간을 둘이 조회하면 한 파일을 서로 덮어쓴다 — 반쯤 쓰인 것을 읽는다."""
        a, _ = self.e.get_session(None)
        b, _ = self.e.get_session(None)
        self.assertNotEqual(a.cache_dir, b.cache_dir)
        self.assertTrue(a.cache_dir.startswith(self.tmp))


class 레이아웃은_같이_쓴다(unittest.TestCase):
    """★한 번 읽고 고치지 않는 자료다(ReplayEngine·WorldModel 은 읽기만 한다).
    M14A 만 해도 노드 9,403 · 엣지 10,424 — 사람마다 따로 읽으면 접속할 때마다
    수백 MB 와 수 초가 그냥 날아간다."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ohtsess")
        self.e = _Env(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_한_번만_읽는다(self):
        a, _ = self.e.get_session(None)
        b, _ = self.e.get_session(None)
        c, _ = self.e.get_session(None)
        self.assertEqual(self.e.loads.count(("M14A", "A")), 1,
                         "접속할 때마다 다시 읽는다 — 느리고 메모리를 먹는다")
        self.assertIs(a.layout, b.layout)
        self.assertIs(b.layout, c.layout)

    def test_FAB_마다_한_벌(self):
        a, _ = self.e.get_session(None)
        a.select_fab("M16A", "A")
        b, _ = self.e.get_session(None)
        b.select_fab("M16A", "A")
        self.assertEqual(self.e.loads.count(("M16A", "A")), 1)
        self.assertIs(a.layout, b.layout)


class 조회_멈춤은_제_것만(unittest.TestCase):
    """★전역 번호 하나였을 때는 한 사람이 멈춤을 누르면 그때 돌던 남의 조회까지
    같이 죽었다. 조회가 5분씩 걸리는 화면이라 이건 그냥 사고다."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ohtsess")
        self.e = _Env(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_내_멈춤이_남의_조회를_안_죽인다(self):
        a, _ = self.e.get_session(None)
        b, _ = self.e.get_session(None)
        a.lp["gen"] += 1
        stop_a = self.e._lp_should_cancel(a, a.lp["gen"])
        b.lp["gen"] += 1
        stop_b = self.e._lp_should_cancel(b, b.lp["gen"])
        self.assertFalse(stop_a())
        self.assertFalse(stop_b())
        a.lp["stop_upto"] = a.lp["gen"]            # A 가 멈춤을 눌렀다
        self.assertTrue(stop_a(), "제 조회는 멈춰야 한다")
        self.assertFalse(stop_b(), "★남의 조회까지 죽는다")

    def test_다시_조회하면_옛_조회만_멎는다(self):
        """멈춤을 누른 사람은 곧바로 다시 조회한다 — 그때 새 조회가 되살아나면 안 된다."""
        a, _ = self.e.get_session(None)
        a.lp["gen"] += 1
        old = self.e._lp_should_cancel(a, a.lp["gen"])
        a.lp["stop_upto"] = a.lp["gen"]
        a.lp["gen"] += 1                            # 새 조회
        new = self.e._lp_should_cancel(a, a.lp["gen"])
        self.assertTrue(old(), "옛 조회는 멎어야 한다")
        self.assertFalse(new(), "새 조회가 옛 멈춤에 걸렸다")


class 오래_안_오면_치운다(unittest.TestCase):
    """★한 사람이 하루치를 부르면 프레임이 통째로 메모리에 남는다. 안 치우면
    접속만 쌓여도 서버가 먹통이 된다."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ohtsess")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_시간이_지나면_치운다(self):
        e = _Env(self.tmp, ttl=1)
        a, _ = e.get_session(None)
        os.makedirs(a.cache_dir, exist_ok=True)
        a.seen -= 5                                  # 5초 전에 마지막으로 왔다
        b, _ = e.get_session(None)                   # 누가 오면 그때 쓸어낸다
        self.assertNotIn(a.sid, e.SESSIONS, "오래 안 온 사람이 남아 있다")
        self.assertIn(b.sid, e.SESSIONS)
        self.assertTrue(a.engine.stopped, "엔진을 안 세우면 뒤에서 계속 돈다")
        self.assertFalse(os.path.isdir(a.cache_dir), "그 사람 CSV 폴더도 같이 지워야 한다")

    def test_아직_보고_있으면_안_치운다(self):
        e = _Env(self.tmp, ttl=1)
        a, _ = e.get_session(None)
        a.touch()
        e.get_session(None)
        self.assertIn(a.sid, e.SESSIONS, "★보고 있는 사람 화면을 끊으면 안 된다")

    def test_수가_넘치면_제일_오래_안_온_사람부터(self):
        e = _Env(self.tmp, mx=3)
        ss = []
        for i in range(3):
            s, _ = e.get_session(None)
            s.seen = time.time() - (10 - i)         # 0 번이 제일 오래됐다(그래도 TTL 안)
            ss.append(s)
        new, _ = e.get_session(None)                # 네 번째
        self.assertNotIn(ss[0].sid, e.SESSIONS, "가장 오래 안 온 사람을 안 치웠다")
        self.assertIn(ss[1].sid, e.SESSIONS)
        self.assertIn(ss[2].sid, e.SESSIONS)
        self.assertIn(new.sid, e.SESSIONS)
        self.assertLessEqual(len(e.SESSIONS), 3)


class 서버_코드에_전역이_안_남았다(unittest.TestCase):
    """떼어 돌린 것만으로는 '엔드포인트가 그 세션을 쓰는지' 를 못 본다 —
    거기는 글자로 본다."""

    def test_전역_엔진이_없다(self):
        self.assertNotRegex(MAIN, r"(?m)^engine = ReplayEngine\(",
                            "모듈 전역 엔진이 되살아났다 — 모두가 같은 화면을 본다")
        self.assertNotRegex(MAIN, r"(?m)^current_fab = ",
                            "모듈 전역 FAB 이 되살아났다")
        self.assertNotIn("LP_RUN", MAIN, "전역 조회 번호가 되살아났다")

    def test_엔드포인트가_제_세션을_쓴다(self):
        """@app.get/@app.post 로 붙은 핸들러 몸통에 **맨 이름 engine.** 이 있으면
        전역을 보는 것이다 (웹소켓은 제 세션에서 꺼낸 지역 이름이라 뺀다)."""
        blocks = re.split(r"(?m)^@app\.(?:get|post)\(", MAIN)[1:]
        bad = []
        for b in blocks:
            body = b.split("\n@app.")[0]
            name = body.split("async def ", 1)[1].split("(", 1)[0] if "async def " in body else "?"
            if re.search(r"(?<![\w.])engine\.", body):
                bad.append(name)
        self.assertEqual(bad, [], "이 엔드포인트가 전역 엔진을 본다: %s" % bad)

    def test_모든_핸들러가_요청을_받는다(self):
        """세션을 가리려면 Request 가 있어야 한다."""
        blocks = re.split(r"(?m)^@app\.(?:get|post)\(", MAIN)[1:]
        bad = []
        for b in blocks:
            body = b.split("\n@app.")[0]
            if "async def " not in body:
                continue
            head = body.split("async def ", 1)[1]
            name, args = head.split("(", 1)[0], head.split("(", 1)[1].split(")", 1)[0]
            if name == "dashboard":       # HTML 한 장 — 세션을 안 본다(미들웨어가 쿠키만 준다)
                continue
            if "request: Request" not in args:
                bad.append(name)
        self.assertEqual(bad, [], "Request 를 안 받는 핸들러: %s" % bad)

    def test_쿠키를_준다(self):
        i = MAIN.index('@app.middleware("http")')
        mw = MAIN[i:i + 1400]
        self.assertIn("resp.set_cookie(SESSION_COOKIE", mw)
        self.assertIn("httponly=True", mw)
        self.assertNotIn("secure=True", mw,
                         "폐쇄망은 http 로 뜬다 — secure 를 붙이면 쿠키가 아예 안 간다")
        self.assertIn('request.url.path.startswith("/static/")', mw,
                      "정적 파일마다 세션을 만들 이유가 없다")

    def test_웹소켓도_같은_쿠키를_본다(self):
        """미들웨어는 http 요청에만 붙는다 — 웹소켓은 제가 읽어야 한다."""
        i = MAIN.index("async def websocket_endpoint")
        ws = MAIN[i:i + 2600]
        self.assertIn("websocket.cookies.get(SESSION_COOKIE)", ws)
        self.assertIn("engine = _s.engine", ws, "매 바퀴 제 세션에서 꺼내야 한다")
        self.assertIn("_s.touch()", ws, "재생 중인 사람은 살아 있는 사람이다")

    def test_화면은_손대지_않았다(self):
        """★쿠키 한 줄로 끝낸다 — dashboard.html 에 세션 코드를 넣으면
        배포할 파일이 하나 더 늘고, 옛 화면이 캐시로 남으면 섞인다."""
        h = _read("dashboard.html")
        self.assertNotIn("oht_sid", h)


if __name__ == "__main__":
    unittest.main()
