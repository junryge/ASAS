# -*- coding: utf-8 -*-
"""관제 목록 → OHT 월드모델 잇기 — world_link.

관제에서 행을 더블클릭하면 그 1분의 구간 그래프가 뜬다. 거기서 FAB 을
누르면 **그 1분 동안 OHT 가 실제로 어떻게 움직였나**를 월드모델이 재생한다.
이 화면은 현재 상태의 **증거 자료**로 쓰인다.

★이 파일이 지키는 것
  · 구간은 그 분의 00초부터 딱 1분 (10:35:47 을 눌러도 103500~103600)
  · M16 은 A·BR·E 세 레이아웃이 있다 — A 와 BR 만 쓴다. E 를 고르면
    통째로 다른 구역의 맵 위에 OHT 를 그리게 된다
  · 월드모델이 죽어 있으면 그 사실과 띄우는 법을 말한다
"""
import http.server
import json
import os
import re
import threading
import unittest
from datetime import datetime

from . import util  # noqa: F401
import world_link as W


class 대응표(unittest.TestCase):
    """★현장에서 받은 표 그대로여야 한다. 한 글자 틀리면 없는 테이블을 친다."""

    TABLE = {
        "M14":    "oht_data_m14a",
        "M14B":   "oht_data_m14b",
        "M16A":   "oht_data_m16A",
        "M16B":   "oht_data_m16B",
        "M16HUB": "oht_data_m16br",
    }
    # OHT_MAP/cache 에 있는 레이아웃과 1:1 —
    #   M14A_A · M14B_A · M16A_A · M16A_BR · M16A_E · M16B_B
    LAYOUT = {
        "M14":    ("M14A", "A"),
        "M14B":   ("M14B", "A"),
        "M16A":   ("M16A", "A"),
        "M16B":   ("M16B", "B"),
        "M16HUB": ("M16A", "BR"),
    }

    def test_테이블_이름이_받은_그대로다(self):
        for fab, tbl in self.TABLE.items():
            self.assertEqual(W.target(fab)["table"], tbl, fab)

    def test_대소문자까지_그대로다(self):
        """oht_data_m16A 는 A 가 대문자다 — 소문자로 바꾸면 안 된다."""
        self.assertEqual(W.target("M16A")["table"], "oht_data_m16A")
        self.assertEqual(W.target("M16B")["table"], "oht_data_m16B")

    def test_맵은_FAB_과_prefix_로_고른다(self):
        for fab, (wf, pre) in self.LAYOUT.items():
            t = W.target(fab)
            self.assertEqual((t["fab"], t["prefix"]), (wf, pre), fab)

    def test_M16HUB_은_BR_레이아웃이다(self):
        """★허브룸은 M16A 폴더 아래의 BR 이다 (M16BR). A 를 쓰면 안 된다."""
        t = W.target("M16HUB")
        self.assertEqual(t["fab"], "M16A")
        self.assertEqual(t["prefix"], "BR")
        self.assertEqual(t["table"], "oht_data_m16br")

    def test_M16_의_E_는_안_쓴다(self):
        """★M16A 아래에 A·BR·E 가 있다. E 를 고르면 다른 구역 맵이 뜬다."""
        for fab in W.fabs():
            self.assertNotEqual(W.target(fab)["prefix"], "E", fab)

    def test_M16A_와_M16HUB_가_서로_다른_맵이다(self):
        """둘 다 M16A 폴더지만 prefix 가 다르다 — 같이 쓰면 하나가 틀린다."""
        a, hub = W.target("M16A"), W.target("M16HUB")
        self.assertEqual(a["fab"], hub["fab"])
        self.assertNotEqual(a["prefix"], hub["prefix"])

    def test_버튼은_다섯_개_표_순서대로(self):
        self.assertEqual(W.fabs(),
                         ["M14", "M14B", "M16A", "M16B", "M16HUB"])

    def test_모르는_이름은_None(self):
        """주소창에 아무 이름이나 넣어도 없는 테이블을 치면 안 된다."""
        for bad in ("M99", "", None, "ALL", "'; drop table"):
            self.assertIsNone(W.target(bad), repr(bad))

    def test_소문자로_눌러도_찾는다(self):
        self.assertEqual(W.target("m16hub")["table"], "oht_data_m16br")


class 딱_1분(unittest.TestCase):
    """★사람이 화면에서 본 '10:35 한 칸' 과 구간이 어긋나면 증거가 안 된다."""

    def test_초를_버리고_그_분의_00초부터(self):
        self.assertEqual(W.window("2026-08-31T10:35:47", 1),
                         ("20260831103500", "20260831103600"))

    def test_1분만_본다(self):
        f, t = W.window("2026-08-31T10:35:00", 1)
        self.assertEqual(
            (datetime.strptime(t, W.FMT) - datetime.strptime(f, W.FMT)).seconds, 60)

    def test_자정을_넘어도_맞는다(self):
        self.assertEqual(W.window("2026-08-31 23:59:30", 1),
                         ("20260831235900", "20260901000000"))

    def test_14자리다(self):
        """월드모델이 14자리가 아니면 400 을 낸다."""
        for x in W.window("2026-08-31T10:35:00", 1):
            self.assertEqual(len(x), 14)
            self.assertTrue(x.isdigit())

    def test_여러_형식을_읽는다(self):
        want = ("20260831103500", "20260831103600")
        for s in ("2026-08-31T10:35:00", "2026-08-31 10:35:00",
                  "2026-08-31 10:35", "20260831103500"):
            self.assertEqual(W.window(s, 1), want, s)

    def test_못_읽는_시각은_거부한다(self):
        """조용히 지금 시각으로 넘어가면 엉뚱한 구간을 증거로 남긴다."""
        for bad in ("", "어제", "2026-13-45", None):
            with self.assertRaises(ValueError):
                W.window(bad, 1)

    def test_설정으로_늘릴_수_있다(self):
        c = {"world_model": {"minutes": 3}}
        x = W.link("M14", "2026-08-31T10:35:00", c)
        self.assertEqual((x["from"], x["to"]),
                         ("20260831103500", "20260831103800"))


class 주소(unittest.TestCase):
    def _q(self, url):
        from urllib.parse import parse_qs, urlparse
        u = urlparse(url)
        return u, {k: v[0] for k, v in parse_qs(u.query).items()}

    def test_월드모델이_알아야_할_것을_다_싣는다(self):
        x = W.link("M16HUB", "2026-08-31T10:35:00", {}, "10.139.31.203:8989")
        _, q = self._q(x["url"])
        self.assertEqual(q["table"], "oht_data_m16br")
        self.assertEqual((q["fab"], q["prefix"]), ("M16A", "BR"))
        self.assertEqual((q["from"], q["to"]),
                         ("20260831103500", "20260831103600"))
        self.assertEqual(q["auto"], "1")

    def test_화면이_보고_있는_host_를_쓴다(self):
        """★localhost 를 박으면 다른 PC 에서 관제를 열었을 때 그 사람 PC 를 찾아간다."""
        u, _ = self._q(W.link("M14", "2026-08-31T10:35:00", {},
                              "10.139.31.203:8989")["url"])
        self.assertEqual(u.hostname, "10.139.31.203")
        self.assertEqual(u.port, 10005)

    def test_설정에_박아_두면_그것을_쓴다(self):
        u, _ = self._q(W.link("M14", "2026-08-31T10:35:00",
                              {"world_model": {"base": "http://10.40.42.99:9999"}},
                              "10.139.31.203:8989")["url"])
        self.assertEqual((u.hostname, u.port), ("10.40.42.99", 9999))

    def test_증거_라벨을_같이_보낸다(self):
        """★며칠 뒤에 그 그림만 봐서는 무슨 건이었는지 알 수 없다."""
        label = "2026-08-31 10:35 · M16HUB · 12점 🟢 정상"
        _, q = self._q(W.link("M16HUB", "2026-08-31T10:35:00", {}, "", label)["url"])
        self.assertEqual(q["case"], label)

    def test_라벨이_없으면_안_붙인다(self):
        _, q = self._q(W.link("M14", "2026-08-31T10:35:00", {})["url"])
        self.assertNotIn("case", q)

    def test_한글과_점이_깨지지_않는다(self):
        _, q = self._q(W.link("M14", "2026-08-31T10:35:00", {}, "",
                              "구역 · 12점")["url"])
        self.assertEqual(q["case"], "구역 · 12점")

    def test_다섯_개_전부_만든다(self):
        rows = W.links("2026-08-31T10:35:00", {}, "127.0.0.1:8989")
        self.assertEqual([r["fab"] for r in rows], W.fabs())
        self.assertEqual(len({r["table"] for r in rows}), 5, "테이블이 겹친다")


class 월드모델이_떠_있나(unittest.TestCase):
    """★죽어 있는데 버튼만 열어 두면 빈 팝업이 뜬다."""

    def setUp(self):
        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                b = json.dumps({"running": False}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.server_close)   # 소켓까지 닫는다
        self.addCleanup(self.srv.shutdown)
        self.cfg = {"world_model": {"base": f"http://127.0.0.1:{self.port}"}}

    def test_떠_있으면_ok(self):
        d = W.alive(self.cfg)
        self.assertTrue(d["ok"])
        self.assertIn("running", d["status"])

    def test_꺼져_있으면_띄우는_법까지_말한다(self):
        self.srv.shutdown()
        d = W.alive({"world_model": {"base": "http://127.0.0.1:1"}})
        self.assertFalse(d["ok"])
        self.assertIn("main.py", d["how"])

    def test_확인이_대화를_막지_않는다(self):
        """월드모델이 없어도 관제는 그대로 돌아야 한다 — 예외가 새면 안 된다."""
        d = W.alive({"world_model": {"base": "http://127.0.0.1:1",
                                     "timeout_s": 0.2}})
        self.assertIn("error", d)


class 화면(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(util.BASE, "static", "dashboard.html"),
                  encoding="utf-8") as f:
            cls.h = f.read()

    def test_구간_그래프에_OHT_줄이_있다(self):
        self.assertIn('id="ohtbar"', self.h)
        self.assertIn('id="ohtbtns"', self.h)
        self.assertIn("그 1분 OHT 재생", self.h)

    def test_팝업으로_띄운다(self):
        """관제 화면을 덮지 않고 나란히 두고 본다."""
        m = re.search(r"async function fillOht\(at, label\)\{[\s\S]*?\n\}", self.h)
        self.assertIsNotNone(m, "OHT 버튼 처리가 없다")
        self.assertIn("window.open", m.group(0))
        self.assertIn("팝업이 막혀", m.group(0), "팝업 차단을 안 알려 준다")

    def test_더블클릭한_행의_시각과_제목을_넘긴다(self):
        m = re.search(r"async function openGraph\(at\)\{[\s\S]*?\n\}", self.h)
        self.assertIsNotNone(m)
        self.assertIn("fillOht(", m.group(0))
        self.assertIn("title", m.group(0), "증거 라벨을 안 넘긴다")

    def test_월드모델이_죽으면_버튼을_잠근다(self):
        m = re.search(r"async function fillOht\(at, label\)\{[\s\S]*?\n\}", self.h)
        body = m.group(0)
        self.assertIn("disabled = true", body)
        self.assertIn("안 떠 있습니다", body)


class 월드모델_화면(unittest.TestCase):
    """관제에서 넘어온 주소를 월드모델이 실제로 읽어야 한다."""

    @classmethod
    def setUpClass(cls):
        p = os.path.join(util.BASE, "월드모델", "월드모델파생", "dashboard.html")
        if not os.path.isfile(p):
            raise unittest.SkipTest("월드모델 화면이 없다")
        with open(p, encoding="utf-8") as f:
            cls.h = f.read()

    def test_주소의_인자를_읽는다(self):
        self.assertIn("autoFromQuery", self.h)
        self.assertIn("URLSearchParams", self.h)

    def test_맵을_먼저_맞추고_조회한다(self):
        """★M16 은 레이아웃이 셋이다. 맵을 안 맞추면 다른 구역 위에 그린다."""
        m = re.search(r"async function autoFromQuery\(\)\s*\{[\s\S]*?\n\}", self.h)
        self.assertIsNotNone(m)
        body = m.group(0)
        self.assertLess(body.index("applyFab"), body.index("logpressoLoad"),
                        "조회를 맵보다 먼저 한다")

    def test_증거_라벨을_화면에_띄운다(self):
        self.assertIn("showCaseBanner", self.h)
        self.assertIn("관제 연동", self.h)

    def test_인자가_모자라면_조용히_넘어간다(self):
        """그냥 월드모델만 열었을 때 엉뚱한 조회가 나가면 안 된다."""
        m = re.search(r"async function autoFromQuery\(\)\s*\{[\s\S]*?\n\}", self.h)
        self.assertIn("auto", m.group(0))
        self.assertIn("return", m.group(0))

    # ── 여기서부터는 **부르는 순서** 다. 위의 시험들은 글자가 있나만 봐서,
    #    아래 두 가지로 아무 일도 안 일어나는 동안에도 전부 통과했다.

    @staticmethod
    def _nocomment(js):
        """// 주석을 지운다 — 길이는 유지해서 위치가 안 밀리게.

        ★주석에 적어 둔 설명(\"여기서 autoFromQuery() 를 부르면 안 된다\")이
          호출문으로 잡혔다. 코드만 본다.
        """
        return re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), js)

    def test_currentFab_선언보다_먼저_부르지_않는다(self):
        """★TDZ. currentFab 은 let 이다 — 선언 전에 읽으면 ReferenceError 다.

        autoFromQuery 는 async 라 그 오류가 거부된 프로미스로 삼켜진다.
        화면에는 아무 일도 안 일어나고, 콘솔을 열어야 알 수 있었다.
        """
        code = self._nocomment(self.h)
        decl = code.index("let currentFab")
        calls = [m.start() for m in re.finditer(r"(?<!function )\bautoFromQuery\b", code)]
        self.assertTrue(calls, "autoFromQuery 를 아무도 안 부른다")
        for at in calls:
            self.assertGreater(at, decl,
                               "let currentFab 선언보다 먼저 autoFromQuery 를 부른다")

    def test_부팅이_끝난_뒤에_돈다(self):
        """★부팅이 currentFab 과 lp-table 을 초기 FAB 으로 되돌린다.

        순서가 반대면, 관제가 지정한 맵·테이블을 초기값이 도로 덮어써서
        엉뚱한 FAB 의 빈 화면이 뜬다. 사람이 다시 고르게 만들면 안 된다.
        """
        self.assertRegex(self.h, r"bootFabs\(\)\s*\.then\(\s*autoFromQuery",
                         "부팅 뒤에 이어 붙지 않았다")
        # 부팅과 무관하게 혼자 도는 호출이 남아 있으면 안 된다
        self.assertNotRegex(self._nocomment(self.h), r"(?m)^\s*autoFromQuery\(\)\s*;",
                            "부팅과 따로 도는 autoFromQuery() 가 남아 있다")

    def test_입력칸은_맵을_바꾼_뒤에_채운다(self):
        """★applyFab 이 syncLogpressoTable() 로 lp-table 을 덮어쓴다."""
        body = re.search(r"async function autoFromQuery\(\)\s*\{[\s\S]*?\n\}",
                         self.h).group(0)
        self.assertLess(body.index("applyFab"), body.index("lp-from"),
                        "입력칸을 먼저 채우면 맵 전환이 테이블명을 덮어쓴다")

    def test_실패를_화면에_말한다(self):
        """★안 되면 안 된다고 화면이 말해야 한다 — 콘솔만 보면 모른다."""
        body = re.search(r"async function autoFromQuery\(\)\s*\{[\s\S]*?\n\}",
                         self.h).group(0)
        self.assertIn("autoNote", body)
        self.assertIn("catch", body)
        note = re.search(r"function autoNote\([\s\S]*?\n\}", self.h)
        self.assertIsNotNone(note, "autoNote 가 없다")
        self.assertIn("case-note", note.group(0))


if __name__ == "__main__":
    unittest.main()
