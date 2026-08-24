"""버추얼 에이전트 (avatar_2d) — 관제 연결 · 근거 우선 대화 · 스킬 · 알람 이력

지키려는 것
  ① 헛소리 차단 — 대답의 숫자는 근거에 있는 것만. 근거가 없으면 없다고.
  ② 관제가 죽으면 죽었다고 말한다. 옛 캐시로 산 척하지 않는다.
  ③ 스킬 md 는 '완전하게' 나온다 — 자르지 않는다.
  ④ 부작용(생성·삭제)은 슬래시 명령으로만 — 자연어 추측 금지.
  ⑤ 알람은 서버가 기억한다. 정상 복귀 후 60분 관찰 유지(사건 닫힘 규칙).
"""
import io
import json
import os
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path

from . import util  # noqa: F401

AV = os.path.join(util.BASE, "avatar_2d")
if AV not in sys.path:
    sys.path.insert(0, AV)

from avatar import commands, config as acfg, llm as allm, sentinel, skills  # noqa: E402

# 진짜 _get — 테스트들이 몽키패치하기 전에 잡아 둔다 (오염 방지)
_REAL_GET = sentinel._get


# ── 가짜 관제 응답 (실물 /api/fab/compare 형태 축약) ─────────────────────
def fake_compare(at="2026-08-24 05:00", hub_level="위험", hub_risk=72):
    return {"ok": True, "at": at,
            "cuts": {"warn": 60, "danger": 71, "critical": 85},
            "area_cap": 50, "delta_min": 30, "blind": ["M16B"],
            "rows": [
                {"is_all": True, "fab": "ALL", "score": 31.0, "level": "정상",
                 "hot_area": "M16HUB", "stage_name": "1단계 조기경보",
                 "fuse": {"areas": 55.0, "flow": 0.0, "sla": 2.5,
                          "sorter": 0.0, "maxcapa": 10.0, "raw": 67.5}},
                {"is_all": False, "fab": "M16HUB", "area": 36.0, "risk": hub_risk,
                 "score": hub_risk, "level": hub_level, "fired": ["RA", "RD"],
                 "delta": 8.0, "mismatch": "",
                 "readings": [{"label": "반송시간", "value": 15.98, "unit": "분",
                               "op": ">=", "thr": 9.0, "over": True}]},
                {"is_all": False, "fab": "M14", "area": 5.0, "risk": 10,
                 "score": 10, "level": "정상", "fired": ["RA_sus"],
                 "delta": None, "mismatch": "", "readings": []},
            ]}


def now_kst(offset_min=0):
    return time.strftime("%Y-%m-%d %H:%M",
                         time.localtime(time.time() - offset_min * 60))


class _Sentinel(unittest.TestCase):
    """sentinel 모듈 테스트 공통 — 캐시·이력을 매번 깨끗이."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        sentinel._cache.update(at=0.0, compare=None, err="")
        sentinel._cols_cache.update(at=0.0, columns=None, err="")
        sentinel._alog_path = None
        sentinel._alog = []
        sentinel._last_levels = {}
        sentinel.init(self.tmp.name)
        self._orig_get = sentinel._get

    def tearDown(self):
        sentinel._get = self._orig_get
        self.tmp.cleanup()

    def feed(self, payload, err=""):
        sentinel._get = lambda path: (payload, err)
        sentinel._cache.update(at=0.0, compare=None)   # 캐시 무효화


class 관제_읽기(_Sentinel):
    def test_죽어_있으면_죽었다고_한다(self):
        self.feed(None, "URLError: 연결 거부")
        w = sentinel.watch()
        self.assertFalse(w["ok"])
        self.assertIn("URLError", w["err"])
        # ★핵심: 못 읽는데 alarms=[] 만 주고 ok=True 면 화면이 '정상' 으로 속는다
        s = sentinel.plain_status()
        self.assertIn("연결이 안", s)
        self.assertIn("알 수 없", s)

    def test_경계_이상만_알람으로_나쁜_순서(self):
        d = fake_compare()
        d["rows"][2]["level"] = "경계"
        self.feed(d)
        w = sentinel.watch()
        self.assertTrue(w["ok"])
        self.assertEqual([a["fab"] for a in w["alarms"]], ["M16HUB", "M14"])
        self.assertEqual(w["alarms"][0]["level"], "위험")

    def test_오래된_데이터는_stale(self):
        self.feed(fake_compare(at="2026-07-28 08:20"))
        w = sentinel.watch()
        self.assertTrue(w["stale"])
        self.feed(fake_compare(at=now_kst(2), hub_level="정상"))
        self.assertFalse(sentinel.watch()["stale"])


class 숫자_가드(unittest.TestCase):
    ALLOWED = {31.0, 72.0, 36.0, 60.0, 71.0, 85.0, 15.98, 9.0}

    def test_근거에_있는_숫자는_통과(self):
        ok, bad = sentinel.check_numbers(
            "M16HUB 위험도 72점이고 반송시간 15.98분이 임계 9.0을 넘었어요", self.ALLOWED)
        self.assertTrue(ok, bad)

    def test_지어낸_숫자는_걸린다(self):
        ok, bad = sentinel.check_numbers("지금 88점 초위험이에요!", self.ALLOWED)
        self.assertFalse(ok)
        self.assertIn(88.0, bad)

    def test_반올림은_봐준다(self):
        ok, _ = sentinel.check_numbers("반송시간이 16분쯤 돼요", self.ALLOWED)
        self.assertTrue(ok)          # 15.98 → 16

    def test_작은_개수_숫자는_봐준다(self):
        ok, _ = sentinel.check_numbers("문제가 2가지 있어요", self.ALLOWED)
        self.assertTrue(ok)

    def test_서버_가드가_지어낸_답을_실측_요약으로_바꾼다(self):
        from avatar.server import Handler
        dummy = types.SimpleNamespace(_say=lambda *_: None)
        ev = {"ok": True, "numbers": self.ALLOWED}
        bad_reply = {"text": "지금 88점 초위험!", "emotion": "fear",
                     "intensity": 1.0, "motion": "shiver"}
        out = Handler._guard(dummy, bad_reply, ev)
        self.assertNotIn("88", out["text"])
        self.assertIn("계산된 값", out["text"])
        good = {"text": "위험도 72점이에요", "emotion": "fear",
                "intensity": 0.9, "motion": "none"}
        self.assertIs(Handler._guard(dummy, good, ev), good)


class 근거_텍스트(_Sentinel):
    def test_화면_숫자가_전부_들어간다(self):
        self.feed(fake_compare(at=now_kst(1)))
        ev = sentinel.evidence()
        self.assertTrue(ev["ok"])
        for must in ("31.0", "72", "36.0", "60", "71", "85", "15.98",
                     "M16HUB", "RA+RD", "M16B"):
            self.assertIn(must, ev["text"], must)
        for n in (31.0, 72.0, 15.98):
            self.assertIn(n, ev["numbers"])

    def test_오래된_데이터_경고가_박힌다(self):
        self.feed(fake_compare(at="2026-07-28 08:20"))
        self.assertIn("오래된 데이터", sentinel.evidence()["text"])

    def test_알람_이력이_근거에_붙는다(self):
        self.feed(fake_compare(at=now_kst(1)))
        sentinel.watch()                       # 이력 기록
        self.assertIn("M16HUB 위험 발생", sentinel.evidence()["text"])


class 알람_이력과_유지(_Sentinel):
    def test_등급_변화만_기록한다(self):
        self.feed(fake_compare(at=now_kst(1)))
        sentinel.watch()
        sentinel.watch()                       # 같은 상태 반복 폴링
        h = sentinel.history()
        self.assertEqual(len(h), 1, "변화 없는 폴링이 이력을 부풀렸다")
        self.assertEqual((h[0]["fab"], h[0]["level"], h[0]["kind"]),
                         ("M16HUB", "위험", "on"))

    def test_해제와_등급변화가_남는다(self):
        self.feed(fake_compare(at=now_kst(1), hub_level="위험"))
        sentinel.watch()
        self.feed(fake_compare(at=now_kst(1), hub_level="초위험", hub_risk=90))
        sentinel.watch()
        self.feed(fake_compare(at=now_kst(1), hub_level="정상", hub_risk=10))
        sentinel.watch()
        kinds = [e["kind"] for e in sentinel.history()]
        self.assertEqual(kinds, ["on", "change", "off"])

    def test_정상_복귀_후_60분_관찰_유지(self):
        self.feed(fake_compare(at=now_kst(1)))
        sentinel.watch()
        self.feed(fake_compare(at=now_kst(1), hub_level="정상", hub_risk=10))
        w = sentinel.watch()
        self.assertEqual(w["alarms"], [])
        self.assertIsNotNone(w["hold"], "복귀 직후에는 관찰 유지여야 한다")
        self.assertEqual(w["hold"]["fab"], "M16HUB")
        self.assertLessEqual(w["hold"]["left_min"], sentinel.HOLD_MIN)

    def test_한_시간_지나면_유지가_풀린다(self):
        stamp = time.strftime("%Y-%m-%d %H:%M",
                              time.localtime(time.time() - 61 * 60))
        sentinel._alog = [
            {"t": stamp, "fab": "M16HUB", "level": "위험", "kind": "on",
             "score": 72},
            {"t": stamp, "fab": "M16HUB", "level": "정상", "kind": "off",
             "prev": "위험", "score": None}]
        self.feed(fake_compare(at=now_kst(1), hub_level="정상", hub_risk=10))
        self.assertIsNone(sentinel.watch()["hold"])

    def test_이력이_파일에_남는다(self):
        self.feed(fake_compare(at=now_kst(1)))
        sentinel.watch()
        p = os.path.join(self.tmp.name, "alarms.json")
        with open(p, encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved[0]["fab"], "M16HUB")


class 진단(_Sentinel):
    def test_불일치와_오래된_데이터를_짚는다(self):
        d = fake_compare(at="2026-07-28 08:20")
        d["rows"][1]["mismatch"] = "룰 배점 합 36 ≠ 저장된 M16HUB_score 55"
        self.feed(d)
        sentinel._cols_cache.update(at=time.time(), columns={"ok": True, "fabs": {}})
        txt = sentinel.diagnose_text()
        self.assertIn("분 전 것", txt)
        self.assertIn("재현 불일치", txt)
        self.assertIn("조치:", txt)

    def test_문제_없으면_없다고_한다(self):
        self.feed(fake_compare(at=now_kst(1)))
        sentinel._cols_cache.update(at=time.time(), columns={"ok": True, "fabs": {}})
        self.assertIn("문제가 없어요", sentinel.diagnose_text())


class 스킬(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = skills.SkillStore(Path(self.tmp.name) / "skills")

    def tearDown(self):
        self.tmp.cleanup()

    def test_만들고_전문_그대로_읽는다(self):
        # ★일부러 크게 만든다 — 짧은 본문으로는 '자르기' 변이를 못 잡는다
        #   (실제로 read()[:2000] 변이가 1500자 본문 테스트를 통과했다)
        md = skills.compose("oht-check", "OHT 가동률 점검법",
                            "# 절차\n" + "\n".join(
                                "- 단계 {} — 점검 항목과 임계값을 확인한다".format(i)
                                for i in range(400)))
        self.assertGreater(len(md), 10000)
        ok, errors, _ = self.store.save("oht-check", md)
        self.assertTrue(ok, errors)
        back = self.store.read("oht-check")
        self.assertEqual(back, md, "전문이 잘리거나 변형되면 안 된다")

    def test_검증_잘못된_이름과_꺾쇠(self):
        ok, errors, _ = skills.validate(skills.compose("한글이름", "설명", "x"))
        self.assertFalse(ok)
        ok, errors, _ = skills.validate(
            skills.compose("ok-name", "설명에 <태그>", "x"))
        self.assertFalse(ok)
        self.assertTrue(any("꺾쇠" in e for e in errors))

    def test_머리말_없으면_거부(self):
        ok, errors, _ = skills.validate("그냥 본문")
        self.assertFalse(ok)

    def test_질문_매칭_주입(self):
        self.store.save("banso", skills.compose(
            "banso", "반송시간 임계", "M16HUB 반송시간 임계는 문서를 봐라"))
        self.store.save("cook", skills.compose(
            "cook", "요리", "라면 끓이는 법"))
        ctx = self.store.context("반송시간 임계가 얼마야?")
        self.assertIn("banso", ctx)
        self.assertNotIn("라면", ctx)
        self.assertEqual(self.store.context(""), "")

    def test_html_은_이스케이프된_단독_파일(self):
        md = skills.compose("t-1", "설명", "# 제목\n`<script>` 조심\n| a | b |\n| --- | --- |\n| 1 | 2 |")
        self.store.save("t-1", md)
        html = skills.to_html("t-1", md)
        self.assertIn("<!doctype html", html)
        self.assertNotIn("<script>", html)          # 이스케이프됐어야 한다
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("<table>", html)
        self.assertNotIn("http://", html)            # 사내망 — 외부 자원 금지

    def test_시드_있으면_안_덮는다(self):
        base = Path(AV)
        first = skills.seed_fab_score(self.store, base)
        self.assertTrue(first, "docs/FAB별_위험도_스코어.md 가 있으면 심어야 한다")
        self.store.save("fab-score", skills.compose(
            "fab-score", "사용자가 고친 것", "수정본"))
        self.assertFalse(skills.seed_fab_score(self.store, base))
        self.assertIn("수정본", self.store.read("fab-score"))


class 명령(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = skills.SkillStore(Path(self.tmp.name) / "skills")
        sentinel._get = lambda path: (fake_compare(at=now_kst(1)), "")
        sentinel._cache.update(at=0.0, compare=None)
        sentinel._alog, sentinel._last_levels, sentinel._alog_path = [], {}, None

    def tearDown(self):
        sentinel._get = _REAL_GET
        self.tmp.cleanup()

    def test_명령이_아니면_None(self):
        self.assertIsNone(commands.handle("안녕", self.store))
        self.assertIsNone(commands.handle("스킬 만들어줘", self.store),
                          "자연어는 명령이 아니다 — 추측 오발 금지")

    def test_상태는_LLM_없이_실측값(self):
        r = commands.handle("/상태", self.store)
        self.assertIn("M16HUB", r["text"])
        self.assertIn("72", r["text"])
        self.assertEqual(r["emotion"], "fear")     # 위험 알람 중

    def test_스킬_보기는_전문(self):
        md = skills.compose("t-2", "설명", "본문내용 " * 3000)   # 15000자+
        self.assertGreater(len(md), 10000)
        self.store.save("t-2", md)
        r = commands.handle("/스킬 보기 t-2", self.store)
        self.assertEqual(r["text"], md, "전문을 자르면 안 된다")

    def test_만들기는_게이트웨이_없으면_정직하게(self):
        r = commands.handle("/스킬 만들기 new-one", self.store)
        self.assertIn("게이트웨이", r["text"])
        self.assertIsNone(self.store.read("new-one"))

    def test_만들기_이름_검증(self):
        r = commands.handle("/스킬 만들기 한글이름", self.store)
        self.assertIn("소문자", r["text"])

    def test_알람기록(self):
        sentinel.watch()
        r = commands.handle("/알람기록", self.store)
        self.assertIn("M16HUB 위험 발생", r["text"])


class 대화_조립(unittest.TestCase):
    class _Docs:
        def context(self, q, b):
            return ""

    def test_데이터_질문_감지(self):
        self.assertTrue(allm.is_data_question("지금 M16HUB 점수 어때?"))
        self.assertTrue(allm.is_data_question("알람 왜 울려?"))
        self.assertFalse(allm.is_data_question("오늘 저녁 뭐 먹지"))

    def test_근거가_스킬보다_앞(self):
        class _Sk:
            def context(self, q, b):
                return "### 스킬: x\n지식"
        msgs = allm.build_messages("페르소나", "점수 어때", [], self._Docs(),
                                   {"docBudget": 6000, "keepMsgs": 12},
                                   skill_store=_Sk(), evidence_text="근거블록")
        sysmsg = msgs[0]["content"]
        self.assertLess(sysmsg.find("[관제 근거]"), sysmsg.find("[스킬"),
                        "실측이 문서보다 앞이어야 한다")
        self.assertIn("근거에 없는 숫자를 만들면", sysmsg.replace("\n", ""))

    def test_첨부는_통째로_들어가고_잘리면_밝힌다(self):
        msgs = allm.build_messages("p", "이 파일 봐줘", [], self._Docs(),
                                   {"docBudget": 100, "keepMsgs": 4},
                                   attach=("a.csv", "x" * 500))
        s = msgs[0]["content"]
        self.assertIn("[방금 첨부한 파일: a.csv]", s)
        self.assertIn("잘렸다고 밝혀라", s)
        msgs2 = allm.build_messages("p", "이 파일 봐줘", [], self._Docs(),
                                    {"docBudget": 6000, "keepMsgs": 4},
                                    attach=("a.csv", "짧은 내용"))
        self.assertNotIn("잘렸다고", msgs2[0]["content"])


class 첨부_CSV_분석(unittest.TestCase):
    """발동이벤트 CSV 첨부 — 원문을 자르지 말고 서버가 계산해서 답한다."""

    @staticmethod
    def _csv(n=180):
        rows = ["datetime,unified_risk_score,hot_area,stage_name,M16HUB_score"]
        for i in range(n):
            # 08:00~08:59 사이에 산 하나: 최고 88점, 60 이상 구간 하나
            sc = 20
            if 60 <= i < 90:
                sc = 60 + min(28, i - 60)          # 60..88
            rows.append("2026-08-23 {:02d}:{:02d},{},M16HUB,1단계,{}".format(
                7 + i // 60, i % 60, sc, min(50, sc // 2)))
        return "\n".join(rows)

    def test_계산이_맞는다(self):
        from avatar import csvdata
        a = csvdata.analyze("발동이벤트.csv", self._csv(), (60, 71, 85))
        self.assertTrue(a["ok"], a["error"])
        s = a["summary"]
        self.assertIn("행 180개", s)
        self.assertIn("최고점: 88점", s)
        self.assertIn("2026-08-23 07:00 ~ 2026-08-23 09:59", s)
        self.assertIn("경계(60) 이상 구간 1곳", s)
        self.assertIn("2026-08-23 08:00 ~ 2026-08-23 08:29", s)
        self.assertIn("M16HUB 최고 44점", s)
        # 등급 분포 — 60..70 이 경계 11분, 71..84 가 위험 14분, 85+ 5분
        self.assertIn("경계 11분 · 위험 14분 · 초위험 5분", s)
        for n in (88.0, 180.0, 60.0):
            self.assertIn(n, a["numbers"])

    def test_점수_컬럼이_없으면_없다고_한다(self):
        from avatar import csvdata
        a = csvdata.analyze("x.csv", "a,b\n1,2\n3,4", (60, 71, 85))
        self.assertTrue(a["ok"])
        self.assertIn("점수 컬럼", a["summary"])
        self.assertIn("못 합니다", a["summary"])

    def test_깨진_파일은_실패라고_한다(self):
        from avatar import csvdata
        a = csvdata.analyze("x.csv", "", (60, 71, 85))
        self.assertFalse(a["ok"])

    def test_업로드_후_첨부하면_분석이_근거로_들어간다(self):
        """400KB 제한으로 CSV 를 거절 → LLM 이 '파일을 못 본다' 하던
        흐름의 회귀 테스트. 업로드→분석→attach 로 요약이 잡혀야 한다."""
        from avatar.server import App, Handler
        with tempfile.TemporaryDirectory() as tmp:
            App.init(Path(tmp))
            sentinel._get = lambda path: (None, "죽음")     # 관제 없이도 돼야 함
            sentinel._cols_cache.update(at=time.time(), columns=None)
            App.uploads_dir = Path(tmp) / "up"
            App.uploads_dir.mkdir()
            App.uploads = {}
            (App.uploads_dir / "발동이벤트.csv").write_text(
                self._csv(), encoding="utf-8")
            dummy = types.SimpleNamespace(_say=lambda *_: None,
                                          _cuts=lambda: (60, 71, 85))
            up = Handler._upload_of(
                types.SimpleNamespace(_say=lambda *_: None,
                                      _cuts=lambda: (60, 71, 85)),
                "발동이벤트.csv")
            del dummy
            self.assertIsNotNone(up)
            self.assertIn("최고점: 88점", up["summary"])
            self.assertIn(88.0, up["numbers"])

    def test_가드_폴백이_첨부_분석을_쓴다(self):
        """첨부 분석 대화에서 헛숫자가 나오면 관제 요약이 아니라
        그 파일의 분석 요약으로 바꿔야 한다."""
        from avatar.server import Handler
        dummy = types.SimpleNamespace(_say=lambda *_: None)
        ev = {"ok": True, "numbers": {88.0, 180.0},
              "fallback": "[첨부 데이터 분석 — x.csv]\n최고점: 88점"}
        bad = {"text": "최고점이 95점이네요!", "emotion": "joy",
               "intensity": 0.8, "motion": "none"}
        out = Handler._guard(dummy, bad, ev)
        self.assertIn("최고점: 88점", out["text"])
        self.assertNotIn("95", out["text"])


class 옛_관제_서버_안내(unittest.TestCase):
    def test_404_는_버전_문제라고_말한다(self):
        """'연결 안 됨' 이라고 하면 네트워크만 뒤진다 — 실제로 그랬다.
        404 = 서버는 떠 있는데 API 가 없다 = server.py 가 옛 버전."""
        # 진짜 _get 의 404 분기를 확인한다 — 404 만 주는 서버를 띄워서
        import http.server
        import threading

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *a):
                pass
        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            import avatar.config as ac
            old = dict(ac.SENTINEL)
            ac.SENTINEL["url"] = "http://127.0.0.1:{}".format(srv.server_port)
            sentinel._get = _REAL_GET
            sentinel._cache.update(at=0.0, compare=None)
            r = sentinel.compare(force=True)
            self.assertFalse(r["ok"])
            self.assertIn("옛 버전", r["err"])
            self.assertIn("server.py", r["err"])
            ac.SENTINEL.update(old)
        finally:
            srv.shutdown()


class 세션_공유(unittest.TestCase):
    """두 PC 가 같은 서버를 쓸 때 세션이 서로를 지우면 안 된다."""

    def setUp(self):
        from avatar import sessions as asess
        self.tmp = tempfile.TemporaryDirectory()
        self.store = asess.SessionStore(Path(self.tmp.name) / "sessions.json")

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def _s(sid, ts, title="t"):
        return {"id": sid, "ts": ts, "title": title,
                "msgs": [{"who": "me", "text": "질문"},
                         {"who": "ai", "text": "답", "tag": ""}]}

    def test_다른_PC_세션을_덮어_지우지_않는다(self):
        """★예전 버그 그대로 — PC-A 가 저장한 뒤 PC-B(자기 목록만 앎)가
        저장하면 A 의 세션이 사라졌다. 병합이면 둘 다 남는다."""
        self.store.put_all([self._s("a1", "2026-08-24 05:00")])
        self.store.put_all([self._s("b1", "2026-08-24 05:10")])
        ids = {s["id"] for s in self.store.get_all()}
        self.assertEqual(ids, {"a1", "b1"},
                         "나중에 저장한 PC 가 먼저 PC 의 세션을 지웠다")

    def test_같은_세션은_보낸_쪽이_이긴다(self):
        self.store.put_all([self._s("a1", "2026-08-24 05:00", "옛날")])
        self.store.put_all([self._s("a1", "2026-08-24 05:00", "고침")])
        self.assertEqual(len(self.store.get_all()), 1)
        self.assertEqual(self.store.get_all()[0]["title"], "고침")

    def test_삭제는_명시해야_지워진다(self):
        self.store.put_all([self._s("a1", "2026-08-24 05:00")])
        self.store.put_all([], deleted=None)
        self.assertEqual(len(self.store.get_all()), 1,
                         "목록에서 빠진 것을 삭제로 해석하면 남의 세션이 죽는다")
        self.store.put_all([], deleted=["a1"])
        self.assertEqual(self.store.get_all(), [])

    def test_최신이_먼저다(self):
        self.store.put_all([self._s("old", "2026-08-24 04:00"),
                            self._s("new", "2026-08-24 06:00")])
        self.assertEqual([s["id"] for s in self.store.get_all()],
                         ["new", "old"])

    def test_html_공유본이_나온다(self):
        md = self.store.to_markdown(self._s("a1", "2026-08-24 05:00"))
        html = skills.to_html("대화 기록", md)
        self.assertIn("<!doctype html", html)
        self.assertIn("질문", html)
        self.assertNotIn("http://", html)    # 사내망 — 외부 자원 금지


class 설정_일치(unittest.TestCase):
    def test_아바타_FAB_목록이_관제와_같다(self):
        """아바타 FABS 가 관제 시스템(ALL + FAB 5)과 어긋나면 그 FAB 알람을
        못 그린다 — 실제로 그랬다 (M14/M16HUB/M16 3개뿐이었다)."""
        import fab_score
        want = ["ALL"] + fab_score.fabs()
        got = [f["key"] for f in acfg.FABS]
        self.assertEqual(sorted(got), sorted(want))

    def test_등급_이름이_관제와_같다(self):
        self.assertEqual([l["name"] for l in acfg.LEVELS],
                         ["경계", "위험", "초위험"])

    def test_그림은_전부_실제_파일(self):
        assets = os.path.join(AV, "static")
        for f in acfg.FABS:
            self.assertTrue(os.path.isfile(os.path.join(assets, f["img"])),
                            f["img"])


if __name__ == "__main__":
    unittest.main()
