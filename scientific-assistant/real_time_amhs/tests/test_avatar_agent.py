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
import re
import shutil
import subprocess
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

from avatar import commands, config as acfg, llm as allm, sentinel, \
    skills, terms  # noqa: E402

# 근거·화면에 남으면 안 되는 룰 코드 (관제는 이 말을 모른다)
_CODE_LEAK = re.compile(
    r"\bR[-‑]?(?:A_sus|B_fast|A′|A'|A|B|C|D)\b|\b(?:RA_sus|RB_fast|RA|RB|RC|RD)\b")

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
        sentinel._cache.update(at=0.0, compare=None, err="", good_at=0.0)
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
        sentinel._cache.update(at=0.0, compare=None, good_at=0.0)   # 캐시 무효화


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

    def test_한_번_삐끗한_것은_끊김이_아니다(self):
        """타임아웃 한 번마다 끊김/복구가 번갈아 뜨던 현장 증상의 수정.
        성공 직후의 실패는 유예(60초) 안이면 마지막 성공값으로 버틴다 —
        degraded 표시와 몇 초 전 값인지를 같이 준다."""
        self.feed(fake_compare(at=now_kst(1)))
        self.assertTrue(sentinel.compare(force=True)["ok"])
        # ★feed() 는 캐시를 지운다 — 유예는 '성공 기록이 있는' 상태에서의
        #   실패라서, 캐시는 살려 두고 _get 만 실패로 바꿔야 한다
        sentinel._get = lambda path: (None, "timed out")
        r = sentinel.compare(force=True)
        self.assertTrue(r["ok"], "유예 안의 실패가 끊김으로 나갔다")
        self.assertTrue(r["degraded"])
        # 다음 폴링(5초 캐시 창이 지난 뒤)에도 끊김이 아니라 유지여야 한다
        sentinel._cache["at"] = 0.0
        w = sentinel.watch()
        self.assertTrue(w["ok"])
        self.assertTrue(w["degraded"])
        self.assertEqual([a["fab"] for a in w["alarms"]], ["M16HUB"],
                         "유지 중에도 알람 상태는 그대로 보여야 한다")

    def test_유예가_지나면_진짜_끊김이다(self):
        self.feed(fake_compare(at=now_kst(1)))
        sentinel.compare(force=True)
        sentinel._cache["good_at"] = time.time() - sentinel.GRACE_S - 1
        sentinel._get = lambda path: (None, "timed out")
        r = sentinel.compare(force=True)
        self.assertFalse(r["ok"], "유예가 끝났는데 옛 값으로 산 척했다")

    def test_성공한_적이_없으면_유예도_없다(self):
        """산 척 금지 — 시작부터 죽어 있으면 바로 죽었다고 한다."""
        self.feed(None, "connection refused")
        self.assertFalse(sentinel.compare(force=True)["ok"])

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
        # 가드가 룰 코드·용어를 손보므로 같은 객체가 아니라 같은 내용이다
        self.assertEqual(Handler._guard(dummy, good, ev), good)


class 근거_텍스트(_Sentinel):
    def test_화면_숫자가_전부_들어간다(self):
        self.feed(fake_compare(at=now_kst(1)))
        ev = sentinel.evidence()
        self.assertTrue(ev["ok"])
        # ★'RA+RD' 같은 코드 나열은 일부러 없앴다 — 실제 컬럼으로 말해야 한다
        self.assertNotIn("켜진룰 RA+RD", ev["text"])
        # 룰은 코드가 아니라 한글 이름으로 나온다 (관제는 'R-A' 를 모른다)
        for must in ("31.0", "72", "36.0", "60", "71", "85", "15.98",
                     "M16HUB", "반송지연", "M16B"):
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


class 시각_표시와_과거_조회(_Sentinel):
    """점수만 던지면 어제 값을 지금 값으로 읽는다 — 시각을 반드시 말한다."""

    def test_상태_요약에_지금과_데이터_시각이_다_있다(self):
        at = now_kst(1)
        self.feed(fake_compare(at=at))
        s = sentinel.plain_status()
        self.assertIn("지금 ", s)
        self.assertIn("데이터 {} 기준".format(at), s)

    def test_근거에_두_시각과_말하라는_지시가_있다(self):
        self.feed(fake_compare(at=now_kst(1)))
        t = sentinel.evidence()["text"]
        self.assertIn("지금 시각:", t)
        self.assertIn("데이터 시각:", t)
        self.assertIn("이 시각을 말하라", t)

    def test_과거_표현_읽기(self):
        self.assertIsNone(sentinel.parse_when("지금 상태 어때"))
        self.assertIsNone(sentinel.parse_when("3시간 동안 정체였어?"),
                          "'3시간' 의 '시' 는 시각이 아니다")
        self.assertIsNone(sentinel.parse_when("점수 알려줘"))
        d, a = sentinel.parse_when("2026-08-23 08:20 상태")
        self.assertEqual((d, a), ("20260823", "2026-08-23 08:20"))
        d, a = sentinel.parse_when("8월 23일 오후 2시 상태")
        self.assertEqual((d, a[-5:]), ("20260823", "14:00"))
        d, a = sentinel.parse_when("어제 상태 어땠어")
        self.assertIsNone(a)              # 시각 없음 → 그날 마지막 행

    def test_과거_조회는_요청시각과_찾은시각을_다_밝힌다(self):
        asked = []

        def fake(path):
            asked.append(path)
            return fake_compare(at="2026-08-23 08:20"), ""
        sentinel._get = fake
        ev = sentinel.evidence_at("20260823", "2026-08-23 08:30")
        self.assertTrue(ev["ok"])
        self.assertIn("물은 시각: 2026-08-23 08:30", ev["text"])
        self.assertIn("실제 찾은 데이터 시각: 2026-08-23 08:20", ev["text"])
        self.assertIn("day=20260823", asked[0])
        self.assertIn("08%3A30", asked[0])          # at 이 쿼리로 나갔다
        # 과거 조회 요약도 두 시각을 밝힌다
        s = sentinel.plain_status_at("20260823", "2026-08-23 08:30")
        self.assertIn("물은 시각", s)
        self.assertIn("2026-08-23 08:20", s)

    def test_상태_명령의_과거_조회(self):
        sentinel._get = lambda path: (fake_compare(at="2026-08-23 08:20"), "")
        store = skills.SkillStore(Path(self.tmp.name) / "sk")
        r = commands.handle("/상태 2026-08-23 8시 30분", store)
        self.assertIn("과거 조회", r["text"])
        self.assertIn("2026-08-23 08:20", r["text"])
        r2 = commands.handle("/상태 아무말이나", store)
        self.assertIn("시각을 못 읽었", r2["text"])


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


class 룰을_실제_컬럼으로_말한다(_Sentinel):
    """'RA+RD' 는 내부 코드다 — 관제는 그게 뭔지 모른다 (실제 지적)."""

    @staticmethod
    def _rich(hub_fired=("RA", "RD")):
        d = fake_compare(at=now_kst(1))
        hub = d["rows"][1]
        hub["fired"] = list(hub_fired)
        hub["pts"] = {"RA": 10, "RD": 7}
        hub["readings"] = [
            {"rule": "RA", "label": "반송시간", "unit": "분", "op": ">=",
             "thr": 9.0, "value": 15.98, "over": True, "has_value": True,
             "amos": "M16HUB.QUE.TIME.AVGTOTALTIME1MIN"},
            {"rule": "RD", "label": "FAB 저장율", "unit": "%", "op": ">=",
             "thr": 25.75, "value": 1.18, "over": False, "has_value": True,
             "amos": "M16HUB.STRATE.ALL.FABSTORAGERATIO"},
            {"rule": "RD", "label": "3F→3F MLUD", "unit": "건", "op": ">=",
             "thr": 50, "value": None, "over": None, "has_value": False,
             "amos": "M16HUB.QUE.ALL.3F_TO_3F_MLUD_JOB"},
        ]
        d["rules"] = [
            {"code": "RA", "pts": 10, "label": "반송지연",
             "when": "최근 10분 중 1회라도 임계 이상"},
            {"code": "RD", "pts": 7, "label": "Storage FULL",
             "when": "조건 하나만 걸려도 켜짐"},
        ]
        return d

    def test_근거에_컬럼과_임계와_실측값이_나온다(self):
        self.feed(self._rich())
        t = sentinel.evidence()["text"]
        self.assertIn("M16HUB.QUE.TIME.AVGTOTALTIME1MIN", t)
        self.assertIn("반송지연", t)      # 현장 공식 한글명
        self.assertIn("임계 ≥9분", t)
        self.assertIn("값 15.98분", t)
        self.assertIn("넘음", t)
        self.assertIn("M16HUB.STRATE.ALL.FABSTORAGERATIO", t)
        # 코드만 나열하던 옛 형식은 사라져야 한다
        self.assertNotIn("켜진룰 RA+RD", t)

    def test_창_판정이면_왜_켜졌는지_밝힌다(self):
        """값은 임계 미만인데 룰이 켜지는 경우 — 설명 없으면 '값 낮은데 왜?'"""
        d = self._rich(hub_fired=("RA",))
        d["rows"][1]["readings"][0].update(value=5.0, over=False)
        self.feed(d)
        t = sentinel.evidence()["text"]
        self.assertIn("임계 미만인데 룰이 켜졌다", t)
        self.assertIn("최근 10분 중 1회", t)

    def test_CSV에_값이_없는_조건이면_그렇게_말한다(self):
        """R-D 처럼 조건 일부가 CSV 에 안 오면 '판정 방식' 얘기가 아니라
        '값이 안 오는 조건에서 걸렸다' 가 맞는 설명이다."""
        self.feed(self._rich(hub_fired=("RD",)))
        t = sentinel.evidence()["text"]
        self.assertIn("CSV 에 값이 안 오는 조건", t)
        self.assertIn("CSV 에 값 없음", t)

    def test_상태_요약도_컬럼_값으로_말한다(self):
        """LLM 을 안 거치고 그대로 화면에 나가는 경로 — 여기 코드가 새면
        그대로 보인다."""
        self.feed(self._rich())
        s = sentinel.plain_status()
        self.assertIn("임계 넘은 값", s)
        self.assertIn("반송시간 15.98분", s)
        self.assertNotIn("RA", s)
        self.assertNotIn("RD", s)

    def test_프롬프트가_룰코드_사용을_금지한다(self):
        self.assertIn("룰 코드", allm.AGENT_RULES)
        self.assertIn("쓰지 마라", allm.AGENT_RULES)
        self.assertIn("AMOS", allm.AGENT_RULES)

    def test_프롬프트_자신이_룰코드를_안_적는다(self):
        """★'RA, RB, RD 를 쓰지 마라' 라고 적으면 그 코드를 **가르치는** 것이다.
        실제로 근거·스킬을 다 막았는데도 대답에 R-D 가 나왔다."""
        self.assertEqual(terms.CODE_RE.findall(allm.AGENT_RULES), [],
                         "금지 규칙이 금지할 코드를 그대로 적어 뒀다")

    def test_프롬프트가_현장_용어를_쓴다(self):
        for banned in ("허브룸", "역증가", "저장공간 포화"):
            self.assertNotIn("\n" + banned, allm.AGENT_RULES)
        self.assertIn("Storage FULL", allm.AGENT_RULES)
        self.assertIn("HUBROOM", allm.AGENT_RULES)


class 줄바꿈(unittest.TestCase):
    """응답이 한 덩어리로 붙어 나오던 문제 — 프롬프트와 파싱 양쪽."""

    def test_프롬프트가_줄바꿈을_시킨다(self):
        """안 시키면 모델이 전부 붙여 쓴다 (실제 증상). 지시가 세 군데
        다 있어야 한다 — 출력규칙·스키마 설명·에이전트 규칙."""
        self.assertIn("줄바꿈", allm.RULES_TEXT)
        self.assertIn("\\n", allm.RULES_TEXT)
        self.assertIn("줄바꿈", allm.SCHEMA["properties"]["text"]["description"])
        self.assertIn("줄바꿈", allm.AGENT_RULES)
        # '1~3문장' 만 시키면 데이터 답까지 뭉친다 — 길어도 된다고 해야 한다
        self.assertIn("길어도 된다",
                      allm.SCHEMA["properties"]["text"]["description"])

    def test_이스케이프된_줄바꿈이_살아난다(self):
        raw = ('{"emotion":"smile","intensity":0.6,"motion":"nod",'
               '"text":"첫 줄\\n- M16HUB 72점"}')
        self.assertEqual(allm.finalize(raw)["text"], "첫 줄\n- M16HUB 72점")

    def test_날것_줄바꿈도_살려낸다(self):
        """모델이 JSON 문자열 안에 진짜 개행을 넣으면 json.loads 는 깨진다.
        그때 통째로 버리면 답이 사라진다 — 부분 파서가 건져야 한다."""
        raw = ('{"emotion":"smile","intensity":0.6,"motion":"nod",'
               '"text":"첫 줄\n- M16HUB 72점"}')
        self.assertEqual(allm.finalize(raw)["text"], "첫 줄\n- M16HUB 72점")

    def test_스트리밍_중에도_줄바꿈이_보인다(self):
        part = ('{"emotion":"smile","intensity":0.6,"motion":"nod",'
                '"text":"첫 줄\\n- M16')
        self.assertEqual(allm.partial_parse(part)["text"], "첫 줄\n- M16")

    def test_말풍선도_줄바꿈을_살린다(self):
        """speakable() 이 \\s+ 로 전부 뭉개서 말풍선이 한 줄로 붙어 나왔다.
        말풍선 CSS 는 white-space:pre-wrap 이라 \\n 만 남기면 갈라진다."""
        import re as _re
        js = os.path.join(AV, "static", "app.js")
        with open(js, encoding="utf-8") as f:
            src = f.read()
        # 다듬기는 sayText 가 한다 (speakable 은 그 결과를 자를 뿐)
        body = src[src.index("function sayText("):]
        body = body[:body.index("\nfunction speakable(")]
        # 줄바꿈까지 죽이는 치환이 남아 있으면 안 된다
        self.assertNotIn(r"\s+/g,' '", body,
                         "\\s+ 치환이 줄바꿈을 뭉갠다")
        self.assertIn(r"[ \t]+", body, "줄 안의 공백만 정리해야 한다")
        # 말풍선 CSS 가 pre-wrap 이어야 \n 이 보인다
        css = os.path.join(AV, "static", "app.css")
        with open(css, encoding="utf-8") as f:
            c = f.read()
        blk = c[c.index("#bubble{"):]
        blk = blk[:blk.index("}")]
        self.assertIn("pre-wrap", blk + c[c.index("#bubble{") - 400:
                                          c.index("#bubble{")],
                      "말풍선에 white-space:pre-wrap 이 없다")


class 룰코드가_한_글자도_안_샌다(_Sentinel):
    """'R-D 룰이 켜졌다' 는 관제가 모르는 말이다 (실제 지적).

    ★프롬프트로 "쓰지 마라" 부탁하는 것으로는 못 막는다 — 재료에 있으면
      모델은 베낀다. 그래서 **근거 텍스트에서 코드를 없앤다.**
    """

    def test_모든_표기법을_한글로_바꾼다(self):
        f = sentinel._no_code
        self.assertEqual(f("R-A 가 켜짐"), "반송지연 가 켜짐")
        self.assertEqual(f("RA_sus"), "반송지연 지속")
        self.assertEqual(f("R-B fast"), "Queue 누적 fast")
        self.assertEqual(f("R-C 와 R-D"), "리프터 정체 와 Storage FULL")
        self.assertEqual(f("임계는 R-A 의 70%"), "임계는 반송지연 의 70%")
        # ★프라임(R-A′)은 정규식이 놓치기 쉽다 — ′ 가 단어문자가 아니라서
        #   경계가 깨지고 "반송지연′" 처럼 꼬리가 남는다
        self.assertEqual(f("R-A′ 지속"), "반송지연 지속 지속")
        self.assertEqual(f("R-A' 판정"), "반송지연 지속 판정")

    def test_코드가_아닌_말은_안_건드린다(self):
        """'RATIO' 안의 RA, 컬럼명 안의 R-D 비슷한 토막을 지우면 근거가 망가진다."""
        f = sentinel._no_code
        self.assertEqual(f("M16HUB.STRATE.ALL.FABSTORAGERATIO"),
                         "M16HUB.STRATE.ALL.FABSTORAGERATIO")
        self.assertEqual(f("RACK 상태"), "RACK 상태")
        self.assertEqual(f("정상"), "정상")

    def test_근거_전문에_룰코드가_없다(self):
        d = 룰을_실제_컬럼으로_말한다._rich()
        # 판정 설명에도 코드를 심어 둔다 — 여기가 옛날에 새던 자리
        d["rules"][0]["when"] = "최근 10분 중 1회 · R-A 기준"
        d["rules"][1]["when"] = "임계는 R-B 의 30%"
        self.feed(d)
        t = sentinel.evidence()["text"]
        leaked = _CODE_LEAK.findall(t)
        self.assertEqual(leaked, [], "근거에 룰 코드가 남았다: %r" % (leaked,))
        self.assertIn("반송지연", t)
        self.assertIn("Storage FULL", t)

    def test_읽은_값이_없는_룰의_판정설명에도_없다(self):
        """★변이 검증에서 살아남은 구멍 — 조건(readings)이 하나도 없는 룰은
        다른 갈래를 탄다. 거기 판정 설명에 코드가 그대로 실려 나갔다."""
        d = 룰을_실제_컬럼으로_말한다._rich(hub_fired=("RA_sus",))
        d["rows"][1]["readings"] = []          # CSV 매핑이 없는 룰
        d["rules"] = [{"code": "RA_sus", "pts": 5, "label": "반송지연 지속",
                       "when": "최근 5분 중 3분 이상 · 임계는 R-A 의 70%"}]
        self.feed(d)
        t = sentinel.evidence()["text"]
        self.assertIn("판정:", t, "판정 설명 갈래를 안 탔다 — 시험이 헛돈다")
        self.assertEqual(_CODE_LEAK.findall(t), [],
                         "값 없는 룰의 판정 설명으로 코드가 샌다")
        self.assertIn("반송지연 의 70%", t)

    def test_상태_요약에도_없다(self):
        """LLM 을 안 거치고 그대로 화면에 나가는 경로."""
        self.feed(룰을_실제_컬럼으로_말한다._rich())
        self.assertEqual(_CODE_LEAK.findall(sentinel.plain_status()), [])

    def test_배점표_원본에도_코드가_없다(self):
        """근거는 fab_score.RULES 의 when 을 그대로 실어 나른다 — 원본이
        깨끗해야 다른 경로(문서·API)로도 안 샌다."""
        import fab_score
        for r in fab_score.RULES:
            for k in ("label", "when"):
                v = str(r.get(k) or "")
                self.assertEqual(_CODE_LEAK.findall(v), [],
                                 "RULES[%s].%s 에 코드가 있다: %r"
                                 % (r["code"], k, v))


class 말풍선은_간단히_채팅창은_전부(unittest.TestCase):
    """캐릭터가 긴 답을 말풍선에 밀어 넣으면 중간에서 잘려 '말하다 만' 것처럼
    보인다 (실제 지적). 캐릭터는 머리말만, 항목 나열은 채팅창이 맡는다."""

    @classmethod
    def setUpClass(cls):
        js = os.path.join(AV, "static", "app.js")
        with open(js, encoding="utf-8") as f:
            cls.src = f.read()

    def _brief(self, text):
        """app.js 의 briefFor 를 그대로 떼어 node 로 돌린다 — 소스만 보고
        '있는 것 같다' 하는 검사는 동작을 보장하지 못한다."""
        node = shutil.which("node")
        if not node:
            self.skipTest("node 없음 — 소스 검사만 수행")
        s = self.src
        # sayText 부터 떼야 한다 — speakable 이 그걸 부른다
        body = s[s.index("function sayText("):s.index("\nfunction push(")]
        prog = (body + "\nconst __in=JSON.parse(process.argv[2]);"
                "process.stdout.write(briefFor(__in));")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                         encoding="utf-8") as f:
            f.write(prog)
            p = f.name
        try:
            out = subprocess.run([node, p, json.dumps(text)],
                                 capture_output=True, timeout=20)
            self.assertEqual(out.returncode, 0, out.stderr.decode("utf-8", "replace"))
            return out.stdout.decode("utf-8")
        finally:
            os.unlink(p)

    LONG = ("2026-08-06 23:59 데이터 기준으로 M16HUB 구역에서 반송·적재 시간 "
            "초과가 감지돼요.\n"
            "- M16HUB.QUE.TIME.AVGTOTALTIME1MIN 임계 ≥9분 · 값 15.98분\n"
            "- M16HUB.STRATE.ALL.FABSTORAGERATIO 임계 ≥25.75% · 값 1.18%\n"
            "- M16HUB.QUE.ALL.3F_TO_3F_MLUD_JOB CSV 에 값 없음\n"
            "- M14 는 정상이에요\n")

    SCORED = ("2026-08-06 23:59 데이터 기준으로 말씀드리면, M16HUB 는 72점 위험 "
              "이고 M14 는 36점 정상이에요.\n"
              "- M16HUB.QUE.TIME.AVGTOTALTIME1MIN 임계 ≥9분 · 값 15.98분\n"
              "- M16HUB.STRATE.ALL.FABSTORAGERATIO 임계 ≥25.75% · 값 1.18%\n"
              "- 30분 변화 +8 · 전체 경보(경계 60점)에는 아직 못 갑니다\n")

    def test_날짜와_등급만_말한다(self):
        """★말풍선이 할 일은 '언제·무슨 등급' 둘 뿐이다. 점수·컬럼은 채팅창."""
        b = self._brief(self.SCORED)
        self.assertEqual(
            b, "2026-08-06 23:59 · M16HUB 위험 · M14 정상\n상세한 내용은 채팅창에 있어요")

    def test_점수_숫자는_말풍선에_안_들어간다(self):
        b = self._brief(self.SCORED).replace("2026-08-06 23:59", "")
        for n in ("72", "36", "15.98", "99.3", "60", "점"):
            self.assertNotIn(n, b, n)

    def test_임계_설명을_등급으로_읽지_않는다(self):
        """'경계 60점' 은 컷 설명이지 지금 등급이 아니다."""
        b = self._brief("2026-08-24 09:00 데이터 기준입니다.\n"
                        "- 전체 경보(경계 60점)에는 아직 못 갑니다\n"
                        "- 지켜볼 구간은 M16HUB 입니다\n")
        self.assertNotIn("경계", b)

    def test_FAB_없이_등급만_말해도_잡는다(self):
        b = self._brief("2026-08-24 09:00 기준입니다.\n"
                        "- 지금은 전 구역 정상이에요\n"
                        "- 지켜볼 것도 없습니다\n")
        self.assertTrue(b.startswith("2026-08-24 09:00 · 정상"), b)

    def test_한글_날짜도_읽는다(self):
        b = self._brief("8월 23일 08:20 데이터로 보면 M16HUB 는 위험이에요.\n"
                        "- 반송지연이 걸렸고\n- Storage FULL 도 같이 걸렸습니다\n")
        self.assertTrue(b.startswith("8월 23일 08:20 · M16HUB 위험"), b)

    def test_FAB_이_넷_이상이면_셋까지만(self):
        b = self._brief("2026-08-24 09:00 기준으로 M14 정상, M14B 정상, "
                        "M16A 정상, M16B 정상, M16HUB 위험 입니다. 자세한 값은 아래에.")
        self.assertEqual(b.split("\n")[0].count("·"), 3)   # 날짜 + FAB 셋
        self.assertIn("M14 정상", b)

    def test_짧은_한_줄은_손대지_않는다(self):
        """★"지금은 전 구역 정상이에요" 를 "정상" 으로 줄이면 말이 아니라 표다."""
        one = "지금은 전 구역 정상이에요."
        self.assertEqual(self._brief(one), one)
        self.assertEqual(self._brief("M16HUB 위험"), "M16HUB 위험")

    def test_머리말_줄바꿈은_살린다(self):
        b = self._brief("첫 줄이에요.\n둘째 줄이에요.")
        self.assertEqual(b, "첫 줄이에요.\n둘째 줄이에요.")

    def test_전부_항목이어도_말은_한다(self):
        """머리말이 없다고 말풍선이 비면 캐릭터가 벙어리가 된다."""
        b = self._brief("- M16HUB 위험\n- M14 정상\n- M14B 정상\n")
        self.assertTrue(b.strip(), "말풍선이 비었다")
        self.assertIn("M16HUB 위험", b)

    def test_항목_안의_등급도_읽어_낸다(self):
        """등급이 표·목록 안에 있어도 결론은 결론이다."""
        b = self._brief("- M16HUB 72점 위험\n- M14 36점 정상\n- 나머지는 정상\n")
        self.assertTrue(b.startswith("M16HUB 위험 · M14 정상"), b)

    def test_날짜도_등급도_없는_답은_머리말만(self):
        """오류·설명처럼 등급이 없는 답도 말은 해야 한다."""
        b = self._brief(
            "관제 서버에 연결이 안 돼서 지금 값을 못 읽고 있어요. 서버가 떠 있는지 봐 주세요.\n"
            "- server.py 가 옛 버전이면 이 API 가 없습니다\n"
            "- 포트 8989 가 막혀 있을 수도 있어요\n")
        self.assertIn("연결이 안", b)
        self.assertNotIn("8989", b, "말풍선이 항목까지 읽으려 든다")
        self.assertIn("채팅창", b, "덜 말한 게 아니라 나눠 맡았다고 알려야 한다")

    def test_한_줄만_길어도_잘린_티를_낸다(self):
        b = self._brief("가" * 400)
        self.assertLess(len(b), 400)
        self.assertIn("…", b)

    def test_말하는_경로가_전부_요약을_쓴다(self):
        """한 군데라도 speakable 을 그대로 쓰면 거기서만 긴 말이 새 나온다."""
        s = self.src
        self.assertNotIn("speak(speakable(", s)
        self.assertIn("speak(briefFor(", s)
        # 스트리밍 중에도 같아야 한다 (스트림은 pushStream 이 그린다)
        blk = s[s.index("function pushStream("):s.index("function endStream(")]
        self.assertIn("briefFor(t)", blk)
        # 말풍선 유지 시간도 '실제로 보이는 길이' 기준이어야 한다
        blk2 = s[s.index("function endStream("):]
        blk2 = blk2[:blk2.index("\nfunction ")]
        self.assertIn("briefFor(t).length", blk2)

    def test_채팅창은_원문_그대로_받는다(self):
        """말풍선을 줄인 김에 채팅창까지 줄이면 정보가 사라진다."""
        s = self.src
        blk = s[s.index("async function send("):]
        blk = blk[:blk.index("\nfunction ") if "\nfunction " in blk else len(blk)]
        self.assertIn("push('ai', r.text", blk,
                      "채팅창에 원문(r.text)이 아니라 요약이 들어간다")


class 소형창_사이드바_서랍(unittest.TestCase):
    """창이 작다고 기능을 없애면 안 된다 — 지난 대화·감정·설정을 서랍으로."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(AV, "static", "app.js"), encoding="utf-8") as f:
            cls.js = f.read()
        with open(os.path.join(AV, "static", "app.css"), encoding="utf-8") as f:
            cls.css = f.read()
        with open(os.path.join(AV, "static", "index.html"), encoding="utf-8") as f:
            cls.html = f.read()

    def test_여닫이_버튼과_덮개가_있다(self):
        self.assertIn('id="drawerBtn"', self.html)
        self.assertIn('id="drawerMask"', self.html)

    def test_서랍_안에_세_탭이_다_있다(self):
        """사이드바를 따로 만들지 않고 **원래 사이드바를 서랍으로** 민다 —
        탭이 갈라지면 소형창에서만 기능이 달라진다."""
        self.assertIn("body.mini #side{", self.css)
        blk = self.css[self.css.index("body.mini #side{"):]
        blk = blk[:blk.index("}")]
        self.assertIn("translateX(100%)", blk, "닫힌 상태가 없다")
        self.assertIn("body.mini.drawer #side{transform:translateX(0)}", self.css)
        for tab in ("대화", "감정", "설정"):
            self.assertIn(tab, self.html)

    def test_덮개가_채팅_위에_온다(self):
        """★z-index 115 였을 때 채팅 <p> 가 클릭을 먹어 서랍이 안 닫혔다."""
        m = re.search(r"body\.mini\.drawer #drawerMask\{[^}]*z-index:(\d+)", self.css)
        self.assertIsNotNone(m, "덮개 z-index 를 못 찾았다")
        self.assertGreaterEqual(int(m.group(1)), 9000)
        # 서랍 본체와 버튼은 덮개보다 위여야 누를 수 있다
        side = int(re.search(r"body\.mini #side\{[^}]*z-index:(\d+)",
                             self.css).group(1))
        btn = int(re.search(r"body\.mini #drawerBtn\{[^}]*z-index:(\d+)",
                            self.css).group(1))
        mask = int(m.group(1))
        self.assertGreater(side, mask)
        self.assertGreater(btn, side)

    def test_닫는_길이_세_가지다(self):
        blk = self.js[self.js.index("function setDrawer("):]
        blk = blk[:blk.index("(function initMini(")]
        self.assertIn("drawerMask", blk, "덮개를 눌러 닫기가 없다")
        self.assertIn("Escape", blk, "ESC 로 닫기가 없다")
        self.assertIn("setDrawer(!document.body.classList.contains('drawer'))", blk,
                      "버튼이 토글이 아니다")

    def test_서랍을_열면_지난_대화를_불러온다(self):
        blk = self.js[self.js.index("function setDrawer("):]
        blk = blk[:blk.index("(function initDrawer(")]
        self.assertIn("loadSessions()", blk,
                      "열어도 다른 PC 세션이 안 보이면 서랍을 만든 뜻이 없다")

    def test_소형창을_끄면_서랍도_닫힌다(self):
        """큰 화면으로 돌아왔는데 서랍 상태가 남으면 사이드바가 겹쳐 보인다."""
        blk = self.js[self.js.index("function setMini("):]
        blk = blk[:blk.index("\n/*")]
        self.assertIn("classList.remove('drawer')", blk)


class _NoDocs:
    """자료 없음 — 규칙 조립만 보려는 테스트용."""

    def context(self, *a, **k):
        return ""


class 에이전트_규칙_보기와_수정(unittest.TestCase):
    """페르소나 말고 '서버가 항상 붙이는 규칙' — 코드에만 있으면 무엇을
    가르쳤는지 아무도 모른다."""

    def setUp(self):
        from avatar import settings as aset
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "settings.json"
        self.aset = aset
        self.st = aset.Settings(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_기본은_코드의_규칙(self):
        self.assertEqual(allm.agent_rules(None), allm.AGENT_RULES)
        self.assertEqual(allm.agent_rules({}), allm.AGENT_RULES)

    def test_고친_규칙이_실제로_쓰인다(self):
        """설정 화면에서 고쳤는데 프롬프트가 안 바뀌면 '보여주기'일 뿐이다."""
        mine = "1. 무조건 한 문장으로만 답한다."
        self.assertEqual(allm.agent_rules({"agentRules": mine}), mine)
        msgs = allm.build_messages("페르소나", "지금 상태?", [], _NoDocs(),
                                   {"agentRules": mine, "docBudget": 6000,
                                    "keepMsgs": 12})
        sysmsg = msgs[0]["content"]
        self.assertIn(mine, sysmsg)
        self.assertNotIn(allm.AGENT_RULES, sysmsg, "기본 규칙이 같이 붙었다")

    def test_비우면_기본값으로_돌아간다(self):
        """'기본값으로' 버튼은 빈 문자열을 보낸다 — 그게 곧 되돌리기다."""
        for blank in ("", "   ", "\n\n", None):
            self.assertEqual(allm.agent_rules({"agentRules": blank}),
                             allm.AGENT_RULES, repr(blank))

    def test_규칙은_숫자로_변환되지_않는다(self):
        """★KEYS 에 넣으면 int() 를 타서 규칙이 통째로 버려진다."""
        self.assertIn("agentRules", self.aset.Settings.TEXT_KEYS)
        self.assertNotIn("agentRules", self.aset.Settings.KEYS)
        d = self.st.update({"agentRules": "1. 규칙 123 번"})
        self.assertEqual(d["agentRules"], "1. 규칙 123 번")

    def test_저장하면_다시_켜도_남는다(self):
        """다른 PC 에서도 같은 규칙이어야 한다 — 서버 파일에 남는다."""
        self.st.update({"agentRules": "내가 고친 규칙"})
        again = self.aset.Settings(self.path)
        self.assertEqual(again.get("agentRules"), "내가 고친 규칙")
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))
                         ["agentRules"], "내가 고친 규칙")

    def test_다른_설정을_고쳐도_규칙은_안_날아간다(self):
        self.st.update({"agentRules": "내 규칙"})
        self.st.update({"temperature": 0.5})
        self.assertEqual(self.st.get("agentRules"), "내 규칙")
        self.assertEqual(self.st.get("temperature"), 0.5)

    def test_너무_긴_규칙은_잘라_담는다(self):
        self.st.update({"agentRules": "가" * 50000})
        self.assertLessEqual(len(self.st.get("agentRules")), 20000)

    def test_설정_API_가_기본값도_같이_준다(self):
        """'기본값으로' 버튼이 기본값을 모르면 되돌릴 수가 없다."""
        with open(os.path.join(AV, "avatar", "server.py"), encoding="utf-8") as f:
            src = f.read()
        blk = src[src.index('if path == "/api/settings":'):]
        # GET/POST 두 갈래 모두에서 채워 줘야 한다
        self.assertEqual(src.count("agentRulesDefault"), 2, src.count("agentRulesDefault"))
        self.assertEqual(src.count("agentRulesCustom"), 2)
        self.assertIn("llm.agent_rules", blk)

    def test_화면에_보이고_고칠_수_있다(self):
        with open(os.path.join(AV, "static", "index.html"), encoding="utf-8") as f:
            html = f.read()
        self.assertIn('id="agentRules"', html)
        self.assertIn('id="rulesSave"', html)
        self.assertIn('id="rulesReset"', html)
        with open(os.path.join(AV, "static", "app.js"), encoding="utf-8") as f:
            js = f.read()
        self.assertIn("agentRulesDefault", js)
        blk = js[js.index("(function initAgentRules("):]
        blk = blk[:blk.index("/* 소형창 사이드바 서랍")]
        self.assertIn("method:'POST'", blk, "저장이 서버로 안 간다")
        self.assertIn("confirm(", blk, "되돌리기에 확인이 없다 — 되돌리면 원본이 사라진다")


class 첫_인사(unittest.TestCase):
    def test_관제_에이전트로_인사한다(self):
        """'나 움직이지? 말 걸어봐' 는 데모 문구다 — 무엇을 물어보면 되는지
        말해 줘야 사용자가 첫 질문을 던진다."""
        with open(os.path.join(AV, "static", "app.js"), encoding="utf-8") as f:
            js = f.read()
        self.assertIn("안녕하세요", js)
        self.assertIn("FAB 관련 질문", js)
        self.assertNotIn("말 걸어봐", js)


class 현장_스킬을_그대로_쓴다(unittest.TestCase):
    """★이름을 지어내면 안 된다 — m16_hub_skills 에 공식 한글명·용어 표준이
    이미 있다. 우리가 따로 쓰면 두 벌이 어긋난다 (실제 지적)."""

    HUB = os.path.join(os.path.dirname(util.BASE), "m16_hub_skills")

    def test_룰_한글명이_카파시_스킬_표와_같다(self):
        """m16_hub_카파시 §4 '9개 룰' 표가 원본이다."""
        path = os.path.join(self.HUB, "m16_hub_카파시_v3.5.md")
        if not os.path.isfile(path):
            self.skipTest("현장 스킬 없음")
        with open(path, encoding="utf-8") as f:
            md = f.read()
        # 표에 적힌 한글명이 우리 표에도 있어야 한다 (용어 표준 적용 후 이름 포함)
        for want in ("반송지연", "4분초과"):
            self.assertIn(want, md, "원본 표가 바뀌었다 — 우리 표도 봐야 한다")
            self.assertIn(want, terms.KO.values())

    def test_용어_표준_금지어를_안_쓴다(self):
        """결과해석 스킬이 '역증가·역류·역방향' 을 **금지** 라고 못박았다."""
        import fab_score
        names = list(terms.KO.values()) + [r["label"] for r in fab_score.RULES]
        for n in names:
            for banned in ("역증가", "역류", "역방향", "저장공간 포화", "허브룸"):
                self.assertNotIn(banned, n, "금지 용어가 룰 이름에 있다: " + n)

    def test_배점표_라벨과_한글명이_한_벌이다(self):
        """fab_score.RULES 와 terms.KO 가 어긋나면 근거와 대답이 딴말을 한다."""
        import fab_score
        for r in fab_score.RULES:
            self.assertEqual(r["label"], terms.KO[r["code"]], r["code"])

    def test_용어_표준으로_바로잡는다(self):
        self.assertEqual(terms.house_style("리프터 역증가로 허브룸 적체"),
                         "리프터 정체로 HUBROOM 정체")
        self.assertEqual(terms.house_style("저장공간 포화"), "Storage FULL")
        self.assertEqual(terms.house_style("M16 허브룸"), "M16 HUBROOM")


class 스킬_시드(unittest.TestCase):
    """현장 스킬이 에이전트 안에 들어와 있어야 한다 — '거기 내용이 전부 있다'."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = skills.SkillStore(Path(self.tmp.name) / "skills")
        self.base = Path(util.BASE) / "avatar_2d"

    def tearDown(self):
        self.tmp.cleanup()

    def test_서버가_켜질_때_현장_스킬을_심는다(self):
        """심는 코드가 있어도 부르지 않으면 에이전트는 아무것도 모른다."""
        with open(os.path.join(AV, "avatar", "server.py"), encoding="utf-8") as f:
            src = f.read()
        blk = src[src.index("cls.skill_store = skills.SkillStore"):]
        blk = blk[:blk.index("sentinel.init(")]
        self.assertIn("skills.seed_hub_skills(cls.skill_store, base_dir)", blk)
        self.assertIn("skills.seed_fab_score(cls.skill_store, base_dir)", blk)

    def test_원래_자리가_없어도_동봉본으로_심는다(self):
        """★현장에서 real_time_amhs 만 풀어 쓰면 원래 자리가 없다 —
        그때 스킬이 하나도 안 심기면 에이전트가 도메인을 통째로 모른다."""
        import shutil as _sh
        fake = Path(self.tmp.name) / "wrap" / "real_time_amhs" / "avatar_2d"
        fake.mkdir(parents=True)
        (fake.parent / "m16_hub_skills").mkdir()
        src = Path(util.BASE) / "m16_hub_skills"
        if not src.is_dir():
            src = Path(util.BASE).parent / "m16_hub_skills"
        if not src.is_dir():
            self.skipTest("현장 스킬 폴더 없음")
        for f in src.glob("*.md"):
            _sh.copy(f, fake.parent / "m16_hub_skills" / f.name)
        self.assertEqual(set(skills.seed_hub_skills(self.store, fake)),
                         set(skills.HUB_SKILLS))

    def test_원래_자리가_있으면_그쪽이_먼저다(self):
        """현장에서 고친 스킬이 동봉본에 덮이면 안 된다."""
        wrap = Path(self.tmp.name) / "sa"
        base = wrap / "real_time_amhs" / "avatar_2d"
        base.mkdir(parents=True)
        (wrap / "m16_hub_skills").mkdir()
        (base.parent / "m16_hub_skills").mkdir()
        self.assertEqual(skills._hub_dir(base), str(wrap / "m16_hub_skills"))

    def test_현장_스킬_네_개를_심는다(self):
        got = skills.seed_hub_skills(self.store, self.base)
        if not got:
            self.skipTest("현장 스킬 폴더 없음")
        self.assertEqual(set(got), set(skills.HUB_SKILLS))
        md = self.store.read("m16-hub-threshold")
        self.assertIn("AVGTOTALTIME1MIN", md, "임계-컬럼 표가 안 들어왔다")

    def test_두_번_심어도_덮지_않는다(self):
        if not skills.seed_hub_skills(self.store, self.base):
            self.skipTest("현장 스킬 폴더 없음")
        self.assertEqual(skills.seed_hub_skills(self.store, self.base), [])

    def test_설명은_원본의_description_을_쓴다(self):
        if not skills.seed_hub_skills(self.store, self.base):
            self.skipTest("현장 스킬 폴더 없음")
        d = [x for x in self.store.list() if x["name"] == "m16-hub-threshold"][0]
        self.assertIn("임계", d["description"])

    def test_룰코드가_남은_fab_score_스킬은_다시_심는다(self):
        """옛 시드에 'R-A' 표가 그대로 있었다 — 사용자가 고쳤든 아니든 결함이다."""
        self.store.save("fab-score", skills.compose(
            "fab-score", "옛 시드", "| `R-A` | 10 | 반송지연 |"))
        skills.seed_fab_score(self.store, self.base)
        self.assertFalse(terms.has_code(self.store.read("fab-score")))

    def test_깨끗한_스킬은_안_건드린다(self):
        mine = skills.compose("fab-score", "내가 고친 것", "내 메모")
        self.store.save("fab-score", mine)
        self.assertFalse(skills.seed_fab_score(self.store, self.base))
        self.assertEqual(self.store.read("fab-score"), mine)


class 룰코드를_세_자리에서_막는다(unittest.TestCase):
    """근거만 막았더니 스킬 문서에서 새어 나왔다 (실제 증상:
    "저장·설비 포화 룰(R-D) 활성화"). 재료·대답 양쪽을 다 막는다."""

    class _Store:
        def __init__(self, text):
            self.text = text

        def context(self, *a, **k):
            return self.text

    SKILL_TABLE = ("| `R-A` | 10 | 반송지연 | 최근 10분 중 1회 |\n"
                   "| `R-D` | 7 | Storage FULL | STB 저장율 |\n"
                   "| 영역 | 임계 | 컬럼 |\n"
                   "| M16HUB | 9.0 | AVGTOTALTIME1MIN |")

    def _sys(self, **kw):
        kw.setdefault("doc_store", self._Store(""))
        msgs = allm.build_messages(
            "페르소나", "지금 상태?", [], kw.pop("doc_store"),
            {"docBudget": 6000, "keepMsgs": 12}, **kw)
        return msgs[0]["content"]

    def test_스킬_표의_코드가_프롬프트에_안_들어간다(self):
        sysmsg = self._sys(skill_store=self._Store(self.SKILL_TABLE))
        self.assertEqual(terms.CODE_RE.findall(sysmsg), [],
                         "스킬에서 룰 코드가 프롬프트로 새 들어갔다")
        # 실제 컬럼은 **살아 있어야** 한다 — 그게 대답에 나와야 할 내용이다
        self.assertIn("AVGTOTALTIME1MIN", sysmsg)
        self.assertIn("반송지연", sysmsg)

    def test_참고_자료의_코드도_막는다(self):
        sysmsg = self._sys(doc_store=self._Store(self.SKILL_TABLE))
        self.assertEqual(terms.CODE_RE.findall(sysmsg), [])

    def test_첨부_파일의_코드도_막는다(self):
        sysmsg = self._sys(attach=("표.md", self.SKILL_TABLE))
        self.assertEqual(terms.CODE_RE.findall(sysmsg), [])

    def test_대답에_섞여_나와도_바꿔서_내보낸다(self):
        """재료를 다 막아도 모델은 **예전 대화**를 보고 코드를 다시 꺼낸다."""
        from avatar.server import Handler
        reply = {"text": "저장·설비 포화 룰(R-D) 활성화, R-A 도 켜졌어요",
                 "emotion": "fear", "intensity": 0.8, "motion": "none"}
        out = Handler._guard(object.__new__(Handler), reply,
                             {"ok": False, "numbers": set()})
        self.assertEqual(terms.CODE_RE.findall(out["text"]), [])
        self.assertIn("Storage FULL", out["text"])
        self.assertIn("반송지연", out["text"])


class 대화_복사(unittest.TestCase):
    """★현장은 http://<사내 IP> 로 연다 — navigator.clipboard 가 아예 없다.
    그래서 [복사] 를 눌러도 아무 일도 안 일어났다 (실제 증상)."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(AV, "static", "app.js"), encoding="utf-8") as f:
            cls.js = f.read()
        with open(os.path.join(AV, "static", "app.css"), encoding="utf-8") as f:
            cls.css = f.read()
        with open(os.path.join(AV, "static", "index.html"), encoding="utf-8") as f:
            cls.html = f.read()

    def test_보안_컨텍스트가_아니면_옛_방식으로_복사한다(self):
        blk = self.js[self.js.index("async function copyText("):]
        blk = blk[:blk.index("/* 복사 버튼 하나")]
        self.assertIn("window.isSecureContext", blk,
                      "http 에서 clipboard 가 없다는 걸 확인하지 않는다")
        self.assertIn("legacyCopy", blk, "대비책이 없다")
        self.assertIn("execCommand", self.js)

    def test_실패하면_실패라고_말한다(self):
        """조용히 아무 일도 안 일어나는 게 제일 나쁘다."""
        blk = self.js[self.js.index("function copyBtn("):]
        blk = blk[:blk.index("\nfunction push(")]
        self.assertIn("복사 실패", blk)
        self.assertIn("Ctrl+C", blk)

    def test_내_질문도_복사할_수_있다(self):
        """길게 쓴 질문을 다시 못 쓰는 건 불편이 아니라 일이 막히는 것이다."""
        blk = self.js[self.js.index("function push(who,text,tag,meta,replaying)"):]
        blk = blk[:blk.index("\n  logEl.appendChild(d);")]
        me = blk[blk.index("if(who==='me'){"):]
        me = me[:me.index("if(who==='ai'){")]
        self.assertIn("copyBtn", me, "내 질문에는 복사 버튼이 안 붙는다")

    def test_대화_전체_복사_버튼이_있다(self):
        self.assertIn('id="sessCopy"', self.html)
        self.assertIn("$('#sessCopy').onclick", self.js)
        blk = self.js[self.js.index("$('#sessCopy').onclick"):]
        blk = blk[:blk.index("$('#sessDel')")]
        self.assertIn("sessionToMarkdown", blk)

    def test_복사_버튼이_늘_보인다(self):
        """★opacity:0 + hover 로만 띄우면 소형창·터치에선 못 누른다."""
        m = re.search(r"\.msg \.copy\{[^}]*opacity:([\d.]+)", self.css)
        self.assertIsNotNone(m)
        self.assertGreater(float(m.group(1)), 0.0, "복사 버튼이 보이지 않는다")
        self.assertIn(".msg:hover .copy{opacity:1}", self.css)
        self.assertIn(".msg{position:relative}", self.css,
                      "내 질문(.msg.me)에 붙은 복사 버튼이 엉뚱한 데 뜬다")


class 노벨_대사창(unittest.TestCase):
    """말풍선은 캐릭터 옆이라 자리가 좁아 요약할 수밖에 없었다 —
    "전부 다 이야기를 안 하네" 가 거기서 나왔다. 대사창은 화면 폭을 다 쓰고
    쪽 넘김이 있으니 **응답 전문**을 보여 줄 수 있다."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(AV, "static", "app.js"), encoding="utf-8") as f:
            cls.js = f.read()
        with open(os.path.join(AV, "static", "app.css"), encoding="utf-8") as f:
            cls.css = f.read()
        with open(os.path.join(AV, "static", "index.html"), encoding="utf-8") as f:
            cls.html = f.read()

    def _run(self, expr, arg=None):
        """app.js 의 sayText/vnSplit 을 떼어 node 로 실제 돌린다."""
        node = shutil.which("node")
        if not node:
            self.skipTest("node 없음")
        s = self.js
        body = s[s.index("function sayText("):s.index("\nfunction push(")]
        body += s[s.index("const VN_PAGE ="):s.index("function vnHide(")]
        body = body.replace("const vnEl=$('#vn'), vnText=$('#vnText'), "
                            "vnPage=$('#vnPage'), vnTip=$('#vnTip');", "")
        prog = (body + "\nconst A=JSON.parse(process.argv[2]);"
                "process.stdout.write(JSON.stringify(" + expr + "));")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                         encoding="utf-8") as f:
            f.write(prog)
            path = f.name
        try:
            r = subprocess.run([node, path, json.dumps(arg)],
                               capture_output=True, timeout=20)
            self.assertEqual(r.returncode, 0,
                             r.stderr.decode("utf-8", "replace"))
            return json.loads(r.stdout.decode("utf-8"))
        finally:
            os.unlink(path)

    LONG = ("2026-08-06 23:59 데이터 기준입니다.\n"
            + "\n".join("- M16HUB.QUE.TIME.COL{} 임계 >=9분 · 값 15.98분".format(i)
                        for i in range(30))
            + "\n조치: STB 적재를 줄여 주세요.")

    def test_대사창은_자르지_않는다(self):
        """★speakable 의 260자 컷이 섞여 있어 뒷부분을 통째로 잃었다."""
        out = self._run("sayText(A)", self.LONG)
        self.assertIn("조치: STB 적재를 줄여 주세요.", out)
        self.assertNotIn("…", out)
        self.assertGreater(len(out), 800)

    def test_말풍선은_여전히_짧게_자른다(self):
        """대사창을 고치면서 말풍선까지 길어지면 캐릭터를 덮는다."""
        out = self._run("speakable(A)", self.LONG)
        self.assertLessEqual(len(out), 300)
        self.assertIn("…", out)

    def test_쪽을_나눠도_내용이_안_사라진다(self):
        """★쪽 나누기에서 한 줄이라도 빠지면 '다 안 말한' 것이 된다."""
        pages = self._run("vnSplit(sayText(A))", self.LONG)
        joined = "\n".join(pages)
        for line in self._run("sayText(A)", self.LONG).split("\n"):
            self.assertIn(line, joined, line[:40])

    def test_쪽은_줄_중간에서_안_끊긴다(self):
        """문장 중간에서 쪽이 갈리면 읽다 만 것처럼 보인다."""
        src = self._run("sayText(A)", self.LONG).split("\n")
        for p in self._run("vnSplit(sayText(A))", self.LONG):
            for line in p.split("\n"):
                self.assertIn(line, src, line[:40])

    def test_짧은_답은_한_쪽(self):
        self.assertEqual(self._run("vnSplit(A)", "M16HUB 위험이에요."),
                         ["M16HUB 위험이에요."])

    def test_표는_지우지_말고_펴서_보여준다(self):
        """표 행을 통째로 지우면 그만큼 내용이 사라진다."""
        out = self._run("sayText(A)",
                        "| 영역 | 임계 | 컬럼 |\n|---|---|---|\n"
                        "| M16HUB | 9.0 | AVGTOTALTIME1MIN |")
        self.assertIn("AVGTOTALTIME1MIN", out)
        self.assertIn("M16HUB · 9.0 · AVGTOTALTIME1MIN", out)
        self.assertNotIn("|", out)

    def test_화면에_대사창이_있다(self):
        for i in ('id="vn"', 'id="vnName"', 'id="vnText"', 'id="vnPage"',
                  'id="vnPrev"', 'id="vnNext"', 'id="vnClose"'):
            self.assertIn(i, self.html, i)

    def test_대사창은_전문을_받는다(self):
        """★여기서 speakable(요약본)을 쓰면 대사창을 만든 뜻이 없다."""
        seen = 0
        for line in self.js.split("\n"):
            if "sayMode==='novel'" in line and "vnShow(" in line:
                seen += 1
                self.assertNotIn("briefFor", line, line)
                self.assertNotIn("speakable(", line, line + " ← 요약본을 넘긴다")
        self.assertGreaterEqual(seen, 3, "대사창으로 가는 길이 너무 적다")

    def test_대사_방식은_세_가지고_노벨이_기본(self):
        self.assertIn("const SAY_MODES = ['novel', 'bubble', 'off'];", self.js)
        self.assertIn("let sayMode='novel'", self.js)
        blk = self.js[self.js.index("$('#bubbleChip').onclick"):]
        blk = blk[:blk.index("\n};")]
        self.assertIn("SAY_MODES.indexOf(sayMode)+1", blk, "칩이 순환하지 않는다")
        self.assertIn("saveSettings()", blk, "고른 방식이 안 저장된다")
        self.assertIn("sayMode:sayMode", self.js)
        self.assertIn("o.ui.sayMode", self.js, "저장한 방식을 다시 안 읽는다")

    def test_옛_설정에서는_꺼_뒀던_것만_존중한다(self):
        """★bubble:true 는 '말풍선을 고른 것' 이 아니라 옛 기본값이다.
        그걸 말풍선 모드로 읽어서 기존 사용자가 대사창을 영영 못 봤다."""
        self.assertIn("if(o.ui.bubble === false) sayMode = 'off';", self.js)
        self.assertNotIn("o.ui.bubble ? 'bubble' : 'off'", self.js,
                         "옛 기본값을 '말풍선 선택' 으로 읽으면 노벨이 안 뜬다")

    def test_넘기기_규칙이_노벨답다(self):
        blk = self.js[self.js.index("function vnAdvance("):]
        blk = blk[:blk.index("vnEl.onclick")]
        self.assertIn("if(VN.typing){ vnRender(true); return; }", blk,
                      "타자기 도중 누르면 즉시 완성되어야 한다")
        key = self.js[self.js.index("if(!vnEl.classList.contains('on')) return;"):]
        key = key[:key.index("\n});")]
        self.assertIn("Escape", key)
        self.assertIn("ArrowLeft", key)
        self.assertIn("tag==='TEXTAREA'", key, "입력 중에 스페이스가 쪽을 넘긴다")


class 알람_패널_위치(unittest.TestCase):
    """대사창이 아래를 쓰므로 알람은 위로. 그리고 평소엔 안 거슬리게."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(AV, "static", "app.css"), encoding="utf-8") as f:
            cls.css = f.read()

    def _box(self):
        i = self.css.index("#alarmBox{position:absolute")
        return self.css[i:self.css.index("}", i)]

    def test_위로_올라갔다(self):
        blk = self._box()
        self.assertIn("top:12px", blk)
        self.assertNotIn("bottom:", blk, "아래에 있으면 대사창과 겹친다")

    def test_평소에는_흐리고_울릴_때만_또렷하다(self):
        m = re.search(r"opacity:([\d.]+);transition", self._box())
        self.assertIsNotNone(m, "평소 흐리게 하는 설정이 없다")
        self.assertLess(float(m.group(1)), 1.0)
        self.assertIn("#alarmBox.on{opacity:1", self.css,
                      "경계 이상인데도 흐리면 알람 노릇을 못 한다")
        self.assertIn("#alarmBox:hover{opacity:1", self.css)

    def test_소형창에서_서랍_버튼과_안_겹친다(self):
        m = re.search(r"body\.mini #alarmBox\{right:(\d+)px", self.css)
        self.assertIsNotNone(m, "소형창 위치 조정이 없다")
        self.assertGreaterEqual(int(m.group(1)), 42,
                                "☰ 버튼(우상단 34px)과 겹친다")


class 화면이_뜨는가(unittest.TestCase):
    """★두 번째 방문부터 화면이 아예 안 뜨던 사고의 재발 방지.

    app.js 는 시작하면서 저장된 설정(localStorage)을 바로 읽는다. 그때 쓰는
    이름이 **파일 아래쪽에서 const 로 선언**돼 있으면, 선언 줄을 지나기 전이라
    ReferenceError 가 나고 **스크립트 전체가 죽는다** — 캐릭터도 대사창도
    아무것도 안 뜬다.

    처음 방문엔 저장값이 없어 그 줄을 안 타므로 멀쩡하다. 설정이 한 번
    저장된 뒤부터 죽는다 — 그래서 개발 중엔 안 보이고 현장에서 터진다.
    """

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(AV, "static", "app.js"), encoding="utf-8") as f:
            cls.js = f.read()

    @staticmethod
    def _code_only(js):
        """주석과 문자열을 지운다 — 거기 적힌 낱말은 변수가 아니다."""
        js = re.sub(r"/\*[\s\S]*?\*/", " ", js)
        js = re.sub(r"//[^\n]*", " ", js)
        js = re.sub(r"'(?:\\.|[^'\\\n])*'", "''", js)
        js = re.sub(r'"(?:\\.|[^"\\\n])*"', '""', js)
        return js

    def _top_decls(self):
        """파일 맨 왼쪽(들여쓰기 없음)에 선언된 const/let → 선언 위치."""
        out = {}
        for m in re.finditer(r"^(?:const|let)\s+([A-Za-z_$][\w$]*)", self.js, re.M):
            out.setdefault(m.group(1), m.start())
        return out

    def test_설정을_읽을_때_쓰는_이름이_먼저_선언돼_있다(self):
        js = self.js
        start = js.index("function applySettings(o, live){")
        body = self._code_only(js[start:js.index("\nfunction loadSettings(", start)])
        init = js.index("const RESTORED = loadSettings();")
        late = []
        for name, at in self._top_decls().items():
            if at <= init:
                continue                      # 이미 선언을 지난 뒤다 — 안전
            # o.ui.bubble 처럼 **속성 이름**은 변수가 아니다 — 앞의 점을 뺀다
            if re.search(r"(?<![.\w$])" + re.escape(name) + r"\b", body):
                late.append((name, js[:at].count("\n") + 1))
        self.assertEqual(
            late, [],
            "설정을 읽는 자리에서 아직 선언 안 된 이름을 쓴다 "
            "(두 번째 방문부터 화면이 안 뜬다): %r" % (late,))

    def test_대사_표시_방식_선언이_설정_읽기보다_위다(self):
        """실제로 터졌던 그 짝 — 값으로도 한 번 더 못박는다."""
        js = self.js
        self.assertLess(js.index("const SAY_MODES"),
                        js.index("const RESTORED = loadSettings();"))
        self.assertLess(js.index("const SAY_LABEL"),
                        js.index("const RESTORED = loadSettings();"))

    def test_선언이_한_번씩만_있다(self):
        """위로 옮기면서 아래 것을 안 지우면 'already declared' 로 또 죽는다."""
        for name in ("SAY_MODES", "SAY_LABEL"):
            self.assertEqual(
                len(re.findall(r"^const " + name + r"\s*=", self.js, re.M)), 1,
                name + " 선언이 두 번 있다")

    def test_문법이_깨지지_않았다(self):
        """구문 오류 하나로도 화면 전체가 안 뜬다 — node 로 한 번 훑는다."""
        node = shutil.which("node")
        if not node:
            self.skipTest("node 없음")
        for f in ("app.js",):
            r = subprocess.run([node, "--check", os.path.join(AV, "static", f)],
                               capture_output=True, timeout=30)
            self.assertEqual(r.returncode, 0,
                             r.stderr.decode("utf-8", "replace"))


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
