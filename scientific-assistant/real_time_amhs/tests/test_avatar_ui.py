# -*- coding: utf-8 -*-
"""화면이 **실제로** 보이는가 — 진짜 브라우저로 연다.

왜 따로 있나
    "화면 안 나오는데??", "FAB 정상 팝업 없어졌다", "그래프 안 보여주는데"
    — 세 번 다 소스는 멀쩡했다. 문법 검사도, 함수 단위 검사도 통과했다.
    화면에서 안 보이는 이유는 늘 **배치와 겹침**이었다:
      · 저장해 둔 자리가 화면 밖이라 통째로 잘림 (#stageWrap 은 overflow:hidden)
      · 대사창(bottom:0, 34vh)이 아래를 다 먹어 그래프가 절반만 보임
      · z-index 가 낮아 다른 상자에 덮임
    이건 좌표를 재야만 잡힌다. 그래서 여기서만 브라우저를 띄운다.

없으면 건너뛴다 — 사내망 PC 에 playwright/chromium 이 없을 수 있다.
그때도 나머지 테스트는 그대로 돈다.
"""
import functools
import http.server
import json
import os
import socketserver
import threading
import unittest

from . import util

BASE = os.path.join(util.BASE, "avatar_2d", "static")

# 관제가 살아 있을 때의 응답 모양 그대로 (sentinel.chart() 반환값)
CHART = {
    "ok": True, "at": "2026-07-28 08:20", "age_min": 40780,
    "age_text": "28일 7시간 전", "stale": True, "live": False,
    "cuts": {"warn": 60, "danger": 71, "critical": 85}, "area_cap": 50,
    "delta_min": 30, "blind": ["M16B"],
    "fabs": [
        {"fab": "M16HUB", "score": 72, "level": "위험", "delta": 8.0,
         "area": 36.0, "fired": ["반송지연 지속", "Storage FULL"], "readings": [
             {"label": "반송시간", "amos": "M16HUB.QUE.TIME.AVGTOTALTIME1MIN",
              "unit": "분", "op": ">=", "thr": 9.0, "value": 15.98,
              "has_value": True, "over": True},
             {"label": "3층 대기", "amos": "M16HUB.QUE.ALL.3F_TO_3F_MLUD_JOB",
              "unit": "건", "op": ">=", "thr": 12.0, "value": None,
              "has_value": False, "over": False}]},
        {"fab": "M14", "score": 10, "level": "정상", "delta": None,
         "area": 5.0, "fired": [], "readings": []}],
}


def _need_browser(case):
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except Exception:                                     # noqa: BLE001
        case.skipTest("playwright 없음 — 화면 검사 건너뜀")


class _Page(unittest.TestCase):
    """정적 파일을 http 로 띄우고(=file:// 이면 SERVER 가 꺼진다) 브라우저로 연다."""

    @classmethod
    def setUpClass(cls):
        _need_browser(cls)
        H = functools.partial(http.server.SimpleHTTPRequestHandler,
                              directory=BASE)
        H.log_message = lambda *a, **k: None
        cls.srv = socketserver.TCPServer(("127.0.0.1", 0), H)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}/index.html".format(
            cls.srv.server_address[1])

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "srv", None):
            cls.srv.shutdown()

    # ★설정은 localStorage 에서 읽는다 (/api/settings 가 아니다) — 여기를
    #   틀리면 '옮겨 둔 자리' 를 심지 못해 테스트가 그냥 통과해 버린다.
    STORE = "avatar2d.settings.v2"

    def open(self, chart=None, ui=None, ctx=None):
        """브라우저를 열고 (page, 콘솔오류목록) 을 준다. /api/* 는 전부 가짜."""
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        exe = "/opt/pw-browsers/chromium"
        try:
            self.br = self._pw.chromium.launch(
                executable_path=exe if os.path.exists(exe) else None)
        except Exception as e:                            # noqa: BLE001
            self._pw.stop()
            self.skipTest("chromium 못 띄움: {}".format(e))
        self.addCleanup(self._pw.stop)
        self.addCleanup(self.br.close)
        pg = self.br.new_page(viewport={"width": 1280, "height": 800})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console",
              lambda m: errs.append(m.text) if m.type == "error" else None)

        if ui:
            pg.add_init_script("try{ localStorage.setItem(%s, %s); }catch(e){}"
                               % (json.dumps(self.STORE),
                                  json.dumps(json.dumps({"ui": ui},
                                                        ensure_ascii=False))))

        def api(route):
            u = route.request.url
            if "/api/fab/chart" in u:
                body = chart if chart is not None else CHART
            elif "/api/fab/status" in u:
                body = {"ok": True, "alarms": [], "at": CHART["at"],
                        "stale": bool(CHART.get("stale")), "hold": None,
                        "hold_min": 60, "degraded": False, "held_s": 0,
                        "age_min": CHART.get("age_min"), "err": ""}
            elif u.rstrip("/").endswith("/api/ctx"):
                # ★계측은 페이지가 뜨자마자 나간다 — goto 뒤에 route 를 걸면
                #   이미 지나간 뒤라 안 걸린다 (그래서 로컬 근사값이 보였다)
                body = ctx if ctx is not None else {"ok": False, "err": "stub"}
            else:
                body = {"ok": False, "err": "stub"}
            route.fulfill(status=200, content_type="application/json",
                          body=(body if isinstance(body, str)
                                else json.dumps(body, ensure_ascii=False)))
        pg.route("**/api/**", api)
        pg.goto(self.url)
        pg.wait_for_timeout(800)
        return pg, errs

    @staticmethod
    def rect(pg, sel):
        return pg.eval_on_selector(sel, """e=>{
            const r=e.getBoundingClientRect(), s=getComputedStyle(e);
            return {l:r.left,t:r.top,r:r.right,b:r.bottom,w:r.width,h:r.height,
                    shown:s.display!=='none'&&s.visibility!=='hidden'};}""")

    @staticmethod
    def overlap(a, b):
        return (max(0, min(a["r"], b["r"]) - max(a["l"], b["l"]))
                * max(0, min(a["b"], b["b"]) - max(a["t"], b["t"])))


class FAB_알람_패널이_화면에_있다(_Page):
    """★"fab 정상 팝업 없어졌다;;;실시간 확인하는거" — 실제 지적."""

    def test_기본으로_보인다(self):
        pg, errs = self.open()
        r = self.rect(pg, "#alarmBox")
        self.assertTrue(r["shown"])
        self.assertGreater(r["w"], 50)
        self.assertEqual(errs, [])

    def test_넓은_화면에서_옮겨_둔_자리여도_안_사라진다(self):
        """★설정은 서버에 있어 PC 를 오간다. 1920 폭 PC 에서 오른쪽 끝에
        옮겨 두면, 1280 폭 PC 에서는 #stageWrap 밖이라 통째로 잘렸다."""
        pg, _ = self.open(ui={"alarmPos": {"l": "1750px", "t": "40px"}})
        pg.wait_for_timeout(400)
        st = self.rect(pg, "#stageWrap")
        r = self.rect(pg, "#alarmBox")
        self.assertTrue(r["shown"])
        self.assertLessEqual(r["r"], st["r"] + 1, "패널이 화면 밖으로 잘렸다")
        self.assertGreaterEqual(r["l"], st["l"] - 1)

    def test_잃어버려도_칩으로_되찾는다(self):
        pg, _ = self.open(ui={"alarmPos": {"l": "1750px", "t": "40px"}})
        pg.click("#alarmChip")
        pg.wait_for_timeout(300)
        st = self.rect(pg, "#stageWrap")
        r = self.rect(pg, "#alarmBox")
        self.assertTrue(r["shown"])
        self.assertLess(st["r"] - r["r"], 40, "제자리(우상단)로 안 돌아왔다")


class 알람_패널에_실시간_수치가_보인다(_Page):
    """★"fab 정상 팝업창 어디있냐" — 패널은 있었는데 opacity .62 라 배경에
    묻혔고, 정상일 땐 'FAB 정상' 글자뿐이라 볼 것도 없었다."""

    def test_또렷하다(self):
        pg, _ = self.open()
        op = pg.eval_on_selector("#alarmBox", "e=>getComputedStyle(e).opacity")
        self.assertEqual(float(op), 1.0, "흐리면 배경에 묻혀 안 보인다")

    def test_FAB별_점수가_실제로_그려진다(self):
        pg, errs = self.open()
        pg.wait_for_timeout(1600)          # 폴링 한 바퀴
        self.assertTrue(self.rect(pg, "#alarmLive")["shown"],
                        "실시간 줄이 안 그려졌다")
        txt = pg.inner_text("#alarmLive")
        self.assertIn("M16HUB", txt)
        self.assertIn("72", txt)
        # 이 자료는 오래된 것이라 시각 대신 경고가 뜬다 — 그것도 실시간
        # 확인의 일부다 ("지금 값이 아니다" 를 못 보면 옛 값을 현재로 읽는다)
        self.assertIn("28일 7시간 전", txt)
        self.assertEqual(errs, [])

    def test_그래프를_안_열어도_보인다(self):
        """★그래프를 닫아 놨다고 볼 게 없어지면 '실시간 확인' 이 안 된다."""
        pg, _ = self.open()
        pg.wait_for_timeout(1600)
        self.assertFalse(self.rect(pg, "#chartWrap")["shown"])
        self.assertTrue(self.rect(pg, "#alarmLive")["shown"])


class 현재_상태_그래프가_보인다(_Page):
    """★"그래프 안 보여주는데;;; ui 화면에 띄워서" — 실제 지적."""

    def _open_chart(self, chart=None):
        pg, errs = self.open(chart=chart)
        pg.click("#chartChip")
        pg.wait_for_timeout(500)
        return pg, errs

    def test_열리고_오류가_없다(self):
        pg, errs = self._open_chart()
        self.assertTrue(self.rect(pg, "#chartWrap")["shown"])
        self.assertEqual(errs, [])

    def test_대사창에_안_먹힌다(self):
        """★대사창은 bottom:0 에서 34vh 까지 큰다 — 좌하단에 뒀더니 그래프
        아래 절반이 그대로 가려졌다 (스크린샷으로 확인한 실제 증상)."""
        pg, _ = self._open_chart()
        c = self.rect(pg, "#chartWrap")
        for sel in ("#vn", "#alarmBox"):
            other = self.rect(pg, sel)
            if not other["shown"]:
                continue
            self.assertEqual(self.overlap(c, other), 0,
                             "{} 와 겹친다".format(sel))

    def test_상자가_화면_안에_다_들어간다(self):
        pg, _ = self._open_chart()
        st, c = self.rect(pg, "#stageWrap"), self.rect(pg, "#chartWrap")
        self.assertGreaterEqual(c["t"], st["t"] - 1)
        self.assertLessEqual(c["b"], st["b"] + 1)
        self.assertLessEqual(c["r"], st["r"] + 1)

    def test_막대가_점수만큼_그려진다(self):
        pg, _ = self._open_chart()
        bars = pg.eval_on_selector_all(".cbar", """els=>els.map(e=>({
            name:e.querySelector('.cname').textContent,
            w:e.querySelector('.cfill').getBoundingClientRect().width,
            track:e.querySelector('.ctrack').getBoundingClientRect().width}))""")
        self.assertEqual([b["name"] for b in bars], ["M16HUB", "M14"])
        hub, m14 = bars
        self.assertAlmostEqual(hub["w"] / hub["track"], 0.72, delta=0.02)
        self.assertAlmostEqual(m14["w"] / m14["track"], 0.10, delta=0.02)

    def test_실제_컬럼_이름이_보인다(self):
        pg, _ = self._open_chart()
        txt = pg.inner_text("#chartBody")
        self.assertIn("M16HUB.QUE.TIME.AVGTOTALTIME1MIN", txt)
        self.assertIn("15.98분", txt)
        self.assertIn("반송지연 지속", txt)

    def test_값이_없는_조건은_막대를_안_그린다(self):
        pg, _ = self._open_chart()
        w = pg.eval_on_selector(
            ".cread.novalue .cfill", "e=>e.getBoundingClientRect().width")
        self.assertEqual(w, 0, "값이 없는데 막대를 그렸다 — 0 으로 보인다")
        self.assertIn("값 없음", pg.inner_text(".cread.novalue"))

    def test_오래된_값을_사람이_읽게_적는다(self):
        """★"지금 40780분 전 값??" — 분으로 적으면 아무도 못 읽는다."""
        pg, _ = self._open_chart()
        txt = pg.inner_text("#chartWrap")
        self.assertIn("28일 7시간 전", txt)
        self.assertNotIn("40780", txt)

    def test_관제가_죽으면_빈_막대를_안_그린다(self):
        """★0 점 막대는 '정상' 으로 읽힌다 — 못 본다고 말해야 한다."""
        pg, _ = self._open_chart(chart={"ok": False, "err": "URLError: 연결 거부",
                                        "fabs": [], "at": ""})
        self.assertEqual(pg.eval_on_selector_all(".cbar", "e=>e.length"), 0)
        self.assertIn("못 읽었습니다", pg.inner_text("#chartBody"))

    def test_닫으면_사라진다(self):
        pg, _ = self._open_chart()
        pg.click("#chartClose")
        pg.wait_for_timeout(200)
        self.assertFalse(self.rect(pg, "#chartWrap")["shown"])


CTX = {"persona": 120, "rules": 900, "evidence": 400, "attach": 1500,
       "skills": 2200, "docs": 1800, "history": 300, "input": 12,
       "total": 7232, "limit": 32768, "pct": 22}


class 컨텍스트_사용량_화면(_Page):
    """★"컨텍스트 파업에 참고자료 MD 가 왜 등록이 안 되어 있지?" — 실제 지적.

    자료는 실리고 있었는데 화면에 칸이 없었다. 이제 서버가 재 준 칸을
    그대로 그리는지 브라우저로 본다.
    """

    def _ctx(self, body):
        """/api/ctx 가 이 값을 줄 때 화면이 어떻게 그리는지."""
        pg, errs = self.open(ctx=body)
        pg.fill("#say", "반송시간 임계 얼마야")   # 입력이 바뀌면 다시 잰다
        pg.wait_for_timeout(1200)
        return pg, errs

    def test_모든_칸이_표에_나온다(self):
        pg, errs = self._ctx(json.dumps(CTX))
        rows = pg.inner_text("#ctxTable")
        for label in ("참고 자료", "스킬", "관제 근거", "첨부 파일",
                      "에이전트 규칙", "페르소나", "대화 기록", "입력"):
            self.assertIn(label, rows, label)
        self.assertEqual(errs, [])

    def test_자료가_실리면_0이_아니다(self):
        """★서버가 준 값을 그대로 그리는가 — 예전엔 스킬·근거·첨부 칸이
        없어서, 실려 있어도 화면에서는 '없는 것' 으로 보였다."""
        pg, errs = self.open()
        pg.evaluate("c=>{ SRV_CTX=c; renderCtx(); }", CTX)
        got = pg.eval_on_selector_all("#ctxTable .ctxRow", """els=>{
            const o={}; els.forEach(e=>{o[e.querySelector('span').textContent]=
              e.querySelector('b').textContent}); return o;}""")
        self.assertEqual(got.get("참고 자료"), "1,800", got)
        self.assertEqual(got.get("스킬"), "2,200", got)
        self.assertEqual(got.get("첨부 파일"), "1,500", got)
        self.assertEqual(errs, [])

    def test_서버가_없어도_안_죽는다(self):
        """★칸이 빠진 응답에도 화면이 살아 있어야 한다 — 여기서 터지면
        renderCtx 뒤가 통째로 안 돌아 화면이 멈춘다 (실제로 그랬다)."""
        pg, errs = self._ctx("{}")
        self.assertEqual(errs, [])
        self.assertTrue(self.rect(pg, "#alarmBox")["shown"])


if __name__ == "__main__":
    unittest.main()
