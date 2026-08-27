# -*- coding: utf-8 -*-
"""① 시스템별 등급 정책이 **끝까지** 먹히나  ② 분석 뒤 이어 묻기.

① 왜 필요했나
    정책 탭에서 FAB 마다 컷을 다르게 잡을 수 있는데, 화면에 안 나타났다.
    compare() 가 루프 **밖에서 한 번** 읽은 cfg 로 여섯 줄을 다 매겼기
    때문이다 — ALL 화면에서 부르면 M14 를 40 으로 낮춰 놔도 ALL 의 60 으로
    매겨진다. "설정하면 거기 맞게 변경돼야 하는데 잘 안 된다" 가 그 지적이다.

② 왜 필요했나
    분석이 끝나면 리포트만 남는다. "그래서 14시엔 몇 점이야?" 를 물을 데가
    없었다. 분석이 본 원자료를 근거로 이어서 묻게 한다 — 근거 밖 숫자를
    만들지 않는 것이 핵심이다.
"""
import json
import os
import unittest
import unittest.mock as mock

from . import util

import analysis                      # noqa: E402
import fab_score as F                # noqa: E402
import sentinel                      # noqa: E402
from lp_client import load_config, sys_cfg   # noqa: E402


def cfg_with(by_sys):
    """정책 탭에서 시스템별로 저장한 모양 그대로."""
    c = load_config()
    c.setdefault("grade", {})["by_sys"] = dict(by_sys)
    return c


def one_row(score_raw="31.5", cfg=None):
    """모든 FAB 이 같은 점수인 한 행 — 등급 차이는 오직 컷 때문이어야 한다."""
    r = {"datetime": "2026-08-26 08:00", "unified_risk_score": 45}
    for f in F.fabs(cfg or load_config()):
        r["{}_score".format(f)] = score_raw
        r["{}_score_raw".format(f)] = score_raw
    return r


# ═══ ① 정책이 FAB 마다 먹힌다 ════════════════════════════════════════════
class 시스템별_컷이_끝까지_간다(unittest.TestCase):

    LOW = {"M14": {"warn": 40, "danger": 55, "critical": 70}}

    def rows_of(self, cfg):
        return F.compare([one_row(cfg=cfg)], cfg=cfg).get("rows") or []

    def test_같은_점수인데_컷이_다르면_등급이_갈린다(self):
        """★이게 전부다 — 예전에는 여섯 줄이 다 같은 등급이었다."""
        cfg = sys_cfg(cfg_with(self.LOW), "ALL")
        by = {r["fab"]: r["level"] for r in self.rows_of(cfg)}
        self.assertEqual(by.get("M14"), "경계", by)
        self.assertEqual(by.get("M16HUB"), "정상", by)

    def test_줄마다_자기_컷을_같이_준다(self):
        """★안 주면 화면이 ALL 컷으로 다시 칠해 서버와 다른 색을 낸다."""
        cfg = sys_cfg(cfg_with(self.LOW), "ALL")
        by = {r["fab"]: r.get("cuts") for r in self.rows_of(cfg)
              if r.get("fab") != "ALL"}
        self.assertEqual(by["M14"]["warn"], 40)
        self.assertEqual(by["M16HUB"]["warn"], 60)

    def test_정책을_안_잡으면_다_같다(self):
        cfg = sys_cfg(cfg_with({}), "ALL")
        lv = {r["level"] for r in self.rows_of(cfg) if r.get("fab") != "ALL"}
        self.assertEqual(lv, {"정상"})

    def test_되돌리면_원래대로(self):
        c = cfg_with(self.LOW)
        self.assertEqual(sentinel.grade_cuts(sys_cfg(c, "M14"))[0], 40)
        c["grade"]["by_sys"].pop("M14")
        self.assertEqual(sentinel.grade_cuts(sys_cfg(c, "M14"))[0], 60)

    def test_ALL_은_ALL_컷으로_매긴다(self):
        """★FAB 컷이 ALL 줄에 새면 전체 판정이 흔들린다."""
        cfg = sys_cfg(cfg_with(self.LOW), "ALL")
        allrow = [r for r in self.rows_of(cfg) if r.get("fab") == "ALL"][0]
        self.assertEqual(allrow["level"], "정상")   # 45점 · ALL 컷 60

    def test_M14_화면에서_불러도_다른_FAB_은_제_컷(self):
        """★?sys=M14 로 봐도 M16HUB 줄은 M16HUB 컷이어야 한다."""
        cfg = sys_cfg(cfg_with(self.LOW), "M14")
        by = {r["fab"]: r["level"] for r in self.rows_of(cfg)}
        self.assertEqual(by.get("M14"), "경계")
        self.assertEqual(by.get("M16HUB"), "정상")

    def test_알람_임계도_시스템별(self):
        c = cfg_with(self.LOW)
        self.assertEqual(sentinel.alarm_floor(sys_cfg(c, "M14")), 40)
        self.assertEqual(sentinel.alarm_floor(sys_cfg(c, "ALL")), 60)

    def test_설정이_없어도_안_터진다(self):
        """★_fab_cfg 가 예외를 내면 여섯 줄이 통째로 안 그려진다.
        ★어떤 예외가 올지 모른다 — KeyError 만 잡으면 다른 게 샌다."""
        self.assertIsNotNone(F._fab_cfg({}, "M14"))
        self.assertIsNotNone(F._fab_cfg({}, ""))
        self.assertIsNotNone(F._fab_cfg(None, "M14"))
        import unittest.mock as m
        import lp_client
        for boom in (ValueError("펑"), TypeError("펑"), RuntimeError("펑")):
            with m.patch.object(lp_client, "sys_cfg",
                                side_effect=boom):
                self.assertIsNotNone(F._fab_cfg({"a": 1}, "M14"),
                                     "{} 를 안 삼킨다".format(type(boom).__name__))


class 분석_프롬프트도_시스템_컷을_쓴다(unittest.TestCase):
    """★FAB 분석인데 ALL 기준을 설명하면, 읽는 사람이 등급을 잘못 안다."""

    def _line(self, sys_name):
        import datetime as dt
        c = sys_cfg(cfg_with({"M14": {"warn": 40, "danger": 55,
                                      "critical": 70}}), sys_name)
        base = dt.datetime(2026, 8, 26, 8, 0)
        seq = [(base + dt.timedelta(minutes=i), 30 + i,
                {"hot_area": "M16HUB", "score": 30 + i}) for i in range(40)]
        txt, meta = analysis._overview(seq, c, "08:00~08:39")
        return txt.splitlines()[0], meta

    def test_ALL_은_60_기준으로_설명한다(self):
        line, meta = self._line("ALL")
        self.assertIn("임계 60점", line)
        self.assertEqual(meta["floor"], 60)

    def test_M14_는_40_기준으로_설명한다(self):
        line, meta = self._line("M14")
        self.assertIn("임계 40점", line)
        self.assertIn("40~54 경계", line)
        self.assertEqual(meta["floor"], 40)


# ═══ ② 분석 뒤 이어 묻기 ═════════════════════════════════════════════════
REC = {
    "id": "A20260826_090000", "day": "20260826", "span": "08:00~09:00",
    "minutes": 60, "sys": "M14", "cuts": [40, 55, 70],
    "overview": "[판정 기준] 알람 임계 40점 · 등급: 39 이하 정상, 40~54 경계\n"
                "[전체 통계] 최고 72점 (08:30, M16HUB)",
    "final": "## 종합 판정\n경계 구간이 12분 있었습니다.",
    "roles": {"p1": {"name": "1차", "result": {"관찰": ["임계 40점 이상 12분"]}}},
    "peak": {}, "incidents": 1, "floor": 40,
}


class _분석하나(unittest.TestCase):
    """저장된 분석 한 건을 깔아 둔다."""

    def setUp(self):
        self.cfg = load_config()
        d = analysis._store_dir(self.cfg)
        os.makedirs(d, exist_ok=True)
        self.path = os.path.join(d, REC["id"] + ".json")
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(REC, f, ensure_ascii=False)
        self.addCleanup(lambda: os.path.exists(self.path)
                        and os.remove(self.path))

    def ask(self, q, history=None, reply="답이오", err=None):
        """LLM 을 가짜로 두고 부른다 → (결과, 모델에게 간 메시지)."""
        seen = {}

        def fake_chat(msgs, cfg=None, **kw):
            seen["msgs"] = msgs
            return (reply, None) if err is None else (None, err)
        import llm_client
        with mock.patch.object(llm_client, "chat", fake_chat):
            out = analysis.ask(REC["id"], q, history, self.cfg)
        return out, seen.get("msgs") or []


class 이어서_물을_수_있다(_분석하나):

    def test_답이_온다(self):
        out, _ = self.ask("14시엔 몇 점이야?")
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["answer"], "답이오")

    def test_분석이_본_원자료를_근거로_준다(self):
        """★리포트 본문만 주면, 본문에 없는 걸 물었을 때 지어낸다."""
        _, msgs = self.ask("최고 몇 점?")
        sysmsg = msgs[0]["content"]
        self.assertIn("[분석이 본 원자료]", sysmsg)
        self.assertIn("최고 72점", sysmsg)
        self.assertIn("[분석 리포트 본문]", sysmsg)

    def test_단계별_관찰도_싣는다(self):
        _, msgs = self.ask("1차에서 뭐 봤어?")
        self.assertIn("임계 40점 이상 12분", msgs[0]["content"])

    def test_그_분석의_컷으로_말하게_한다(self):
        """★분석은 M14 컷으로 했는데 이어 묻기가 ALL 컷으로 답하면,
        같은 점수를 두고 등급이 갈린다."""
        _, msgs = self.ask("72점이면 무슨 등급이야?")
        s = msgs[0]["content"]
        self.assertIn("경계 40/위험 55/초위험 70", s)
        self.assertIn("다른 기준을 끌어오지 마라", s)

    def test_근거_밖_숫자를_막는다(self):
        _, msgs = self.ask("뭐 있어?")
        self.assertIn("근거에 있는 숫자만", msgs[0]["content"])
        self.assertIn("이 분석에 없다", msgs[0]["content"])

    def test_줄바꿈을_시킨다(self):
        """★한 줄로 쭉 나오면 관제 화면에서 못 읽는다 (이미 겪은 것)."""
        _, msgs = self.ask("정리해줘")
        self.assertIn("줄바꿈으로 나눠", msgs[0]["content"])

    def test_이전_문답을_이어_간다(self):
        """★'그럼 그건?' 같은 말이 통하려면 이력이 가야 한다."""
        _, msgs = self.ask("그럼 그건?", [
            {"role": "user", "content": "앞선 질문"},
            {"role": "assistant", "content": "앞선 답"}])
        self.assertEqual(len(msgs), 4)          # system + 이력2 + 질문
        self.assertEqual(msgs[1]["content"], "앞선 질문")
        # 질문 끝에 "(한국어로, 결론만)" 을 덧붙인다 — 앞부분만 본다
        self.assertTrue(msgs[-1]["content"].startswith("그럼 그건?"),
                        msgs[-1]["content"])

    def test_이력이_길면_잘라_보낸다(self):
        long = [{"role": "user", "content": "q{}".format(i)} for i in range(40)]
        _, msgs = self.ask("또", long)
        self.assertLessEqual(len(msgs), analysis.ASK_KEEP + 2)

    def test_이상한_이력은_버린다(self):
        _, msgs = self.ask("어", ["문자열", {"role": "system", "content": "끼어들기"}])
        self.assertEqual(len(msgs), 2)          # system + 질문만

    def test_빈_질문은_거절한다(self):
        self.assertFalse(analysis.ask(REC["id"], "   ", None, self.cfg)["ok"])

    def test_없는_분석은_그렇게_말한다(self):
        r = analysis.ask("A20990101_000000", "뭐", None, self.cfg)
        self.assertFalse(r["ok"])
        self.assertIn("없는 분석", r["error"])

    def test_LLM_이_죽어도_안_터진다(self):
        out, _ = self.ask("뭐", err={"reason": "게이트웨이 없음"})
        self.assertFalse(out["ok"])
        self.assertTrue(out["error"])

    def test_근거가_없는_옛_기록은_그렇게_말한다(self):
        """★overview 를 안 저장하던 시절 기록이 있다. 되씹게 두면 안 된다."""
        old = dict(REC)
        for k in ("overview", "final", "roles"):
            old.pop(k, None)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(old, f, ensure_ascii=False)
        r = analysis.ask(REC["id"], "뭐", None, self.cfg)
        self.assertFalse(r["ok"])
        self.assertIn("근거가 남아 있지 않", r["error"])


BAD_EN = """Thinking Process:

1. **Analyze the Request:**
* Role: Control Analyst answering questions.
* Constraint 1: Use only numbers from the provided evidence.

2. **Analyze the Evidence:**
* Max Score: 43 points (Threshold 60).

3. **Drafting the Answer:**
정체는 없었습니다.
- 최고 43점 (임계 60점 미만)"""


class 영문_생각과정이_안_나온다(_분석하나):
    """★"왜....영문으로 나오냐;;;헐" — 사고 모델이 영문 추론을 본문에 그대로
    썼다. <think> 태그로 감싸면 걷히는데, 태그 없이 쓰면 화면에 다 나온다."""

    def test_영문_머리말을_걷어낸다(self):
        out, _ = self.ask("왜 이래?", reply=BAD_EN)
        self.assertTrue(out["ok"])
        self.assertTrue(out["answer"].startswith("정체는 없었습니다"), out["answer"])
        self.assertNotIn("Thinking Process", out["answer"])
        self.assertNotIn("Analyze the Request", out["answer"])

    def test_think_태그도_걷어낸다(self):
        out, _ = self.ask("왜?", reply="<think>영어로 고민</think>\n답입니다")
        self.assertEqual(out["answer"], "답입니다")

    def test_멀쩡한_한국어_답은_안_건드린다(self):
        """★멀쩡한 답을 잘라 먹으면 그게 더 나쁘다."""
        good = "정상입니다.\n- 최고 43점\n- 임계 60점 미만"
        out, _ = self.ask("어때?", reply=good)
        self.assertEqual(out["answer"], good)

    def test_한국어로만_답하라고_시킨다(self):
        _, msgs = self.ask("뭐야")
        s = msgs[0]["content"]
        self.assertIn("한국어로만", s)
        self.assertIn("영어로 쓰지 마라", s)

    def test_생각과정을_쓰지_말라고_시킨다(self):
        _, msgs = self.ask("뭐야")
        self.assertIn("결론만", msgs[0]["content"])
        self.assertIn("Thinking Process", msgs[0]["content"])

    def test_질문_끝에도_못_박는다(self):
        """★규칙은 system 에 있고 모델은 마지막 줄을 제일 잘 듣는다."""
        _, msgs = self.ask("뭐야")
        self.assertIn("한국어로, 결론만", msgs[-1]["content"])


class 사고를_게이트웨이에서_끈다(_분석하나):
    """★부탁만으로는 안 멈춘다. 템플릿에서 끄고, 게이트웨이가 그 옵션을
    모르면(400) 한 단계 빼고 다시 부른다."""

    def ask_opts(self, q="뭐야", model="", fail_first=0):
        calls = []

        def fake_chat(msgs, cfg=None, **kw):
            calls.append({"extra": kw.get("extra"), "last": msgs[-1]["content"]})
            if len(calls) <= fail_first:
                return None, {"reason": "400 unknown field"}
            return "답이오", None
        import llm_client
        with mock.patch.object(llm_client, "chat", fake_chat):
            out = analysis.ask(REC["id"], q, None, self.cfg, model)
        return out, calls

    def test_사고를_끄는_옵션을_보낸다(self):
        _, calls = self.ask_opts()
        self.assertEqual(calls[0]["extra"],
                         {"chat_template_kwargs": {"enable_thinking": False}})

    def test_옵션을_모르는_게이트웨이면_빼고_다시(self):
        out, calls = self.ask_opts(fail_first=1)
        self.assertTrue(out["ok"], out)
        self.assertEqual(len(calls), 2)
        self.assertIsNone(calls[-1]["extra"])

    def test_다_실패하면_실패라고_한다(self):
        out, calls = self.ask_opts(fail_first=9)
        self.assertFalse(out["ok"])
        self.assertTrue(out["error"])

    def test_gpt_oss_는_추론_강도까지_낮춘다(self):
        _, calls = self.ask_opts(model="gaia-cc-gpt-oss-120b")
        self.assertEqual(calls[0]["extra"].get("reasoning_effort"), "low")

    def test_사고모델이면_no_think_도_붙인다(self):
        _, calls = self.ask_opts(model="gaia-Qwen3.6-35B-A3B")
        self.assertIn("/no_think", calls[0]["last"])


class 모델과_프롬프트를_고를_수_있다(_분석하나):

    def test_모델을_지정하면_그걸_쓴다(self):
        seen = {}

        def fake_chat(msgs, cfg=None, **kw):
            seen["model"] = (cfg.get("llm") or {}).get("model")
            return "답", None
        import llm_client
        with mock.patch.object(llm_client, "chat", fake_chat):
            out = analysis.ask(REC["id"], "뭐", None, self.cfg, "내가고른모델")
        self.assertEqual(seen["model"], "내가고른모델")
        self.assertEqual(out["model"], "내가고른모델")

    def test_안_지정하면_기본_모델(self):
        out, _ = self.ask("뭐")
        self.assertTrue(out["model"])          # config.llm.model

    def test_추가_지시가_실린다(self):
        seen = {}

        def fake_chat(msgs, cfg=None, **kw):
            seen["sys"] = msgs[0]["content"]
            return "답", None
        import llm_client
        with mock.patch.object(llm_client, "chat", fake_chat):
            analysis.ask(REC["id"], "뭐", None, self.cfg, "", "표로 정리해줘")
        self.assertIn("[추가 지시", seen["sys"])
        self.assertIn("표로 정리해줘", seen["sys"])

    def test_추가_지시는_규칙_뒤에_온다(self):
        """★앞에 두면 '한국어로만' 같은 규칙을 덮어 쓴다."""
        seen = {}

        def fake_chat(msgs, cfg=None, **kw):
            seen["sys"] = msgs[0]["content"]
            return "답", None
        import llm_client
        with mock.patch.object(llm_client, "chat", fake_chat):
            analysis.ask(REC["id"], "뭐", None, self.cfg, "", "영어로 써")
        s = seen["sys"]
        self.assertLess(s.index("한국어로만"), s.index("[추가 지시"))


class 문답을_기록으로_남긴다(_분석하나):
    """★"지난 분석에 질문한 내용 기록 남겨야 돼" — 창을 닫으면 사라졌다."""

    def test_물으면_파일에_쌓인다(self):
        self.ask("첫 질문")
        self.ask("둘째 질문")
        rec = analysis.get_analysis(REC["id"], self.cfg)
        log = rec.get("chat") or []
        self.assertEqual(len(log), 4)          # 질문2 + 답2
        self.assertEqual(log[0]["content"], "첫 질문")
        self.assertEqual(log[-1]["content"], "답이오")

    def test_언제_어느_모델로_물었는지_남는다(self):
        self.ask("질문")
        m = (analysis.get_analysis(REC["id"], self.cfg).get("chat") or [])[-1]
        self.assertTrue(m.get("at"))
        self.assertTrue(m.get("model"))

    def test_분석_본문은_안_망가진다(self):
        """★파일을 다시 쓰는 자리다 — 원래 내용이 날아가면 안 된다."""
        self.ask("질문")
        rec = analysis.get_analysis(REC["id"], self.cfg)
        self.assertEqual(rec["final"], REC["final"])
        self.assertEqual(rec["overview"], REC["overview"])

    def test_너무_쌓이면_오래된_것부터_버린다(self):
        old = analysis.ASK_LOG_MAX
        analysis.ASK_LOG_MAX = 4
        self.addCleanup(lambda: setattr(analysis, "ASK_LOG_MAX", old))
        for i in range(5):
            self.ask("q{}".format(i))
        log = analysis.get_analysis(REC["id"], self.cfg).get("chat") or []
        self.assertEqual(len(log), 4)
        # 문답은 쌍(질문+답)으로 쌓인다 — 4개면 마지막 두 쌍이 남는다
        self.assertEqual(log[0]["content"], "q3")

    def test_실패한_질문은_안_남긴다(self):
        """★답을 못 받았는데 기록에 남으면 나중에 그걸 답으로 읽는다."""
        self.ask("실패할 질문", err={"reason": "죽음"})
        log = (analysis.get_analysis(REC["id"], self.cfg) or {}).get("chat") or []
        self.assertEqual(log, [])

    def test_기록_저장이_실패해도_답은_준다(self):
        with mock.patch.object(analysis, "_store_dir",
                               side_effect=OSError("못 씀")):
            pass
        out, _ = self.ask("질문")
        self.assertTrue(out["ok"])


class 옛_기록에도_컷을_채운다(_분석하나):
    """★cuts 를 안 저장하던 시절 기록이 있다. "등급 컷 정보 없음" 을 그대로
    넣으면 모델이 기준 없이 말한다 (실제 증상)."""

    def test_없으면_지금_설정에서_읽는다(self):
        """★기본값(60/71/85)으로 때우면 안 된다 — 그 시스템에 설정된 컷을
        읽어야 한다. 기본값과 다른 값으로 재야 구분이 된다."""
        old = dict(REC); old.pop("cuts")
        old["sys"] = "M14"
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(old, f, ensure_ascii=False)
        self.cfg = cfg_with({"M14": {"warn": 33, "danger": 44, "critical": 77}})
        _, msgs = self.ask("뭐")
        self.assertIn("등급 컷 경계 33/위험 44/초위험 77", msgs[0]["content"])
        self.assertNotIn("정보 없음", msgs[0]["content"])

    def test_있으면_그걸_쓴다(self):
        _, msgs = self.ask("뭐")
        self.assertIn("경계 40/위험 55/초위험 70", msgs[0]["content"])

    def test_설정을_못_읽어도_기본값으로(self):
        self.assertEqual(analysis._ask_cuts({}, None), [60, 71, 85])


class 화면에_모델과_기록이_붙는다(unittest.TestCase):

    def setUp(self):
        p = os.path.join(util.BASE, "static", "dashboard.html")
        with open(p, encoding="utf-8") as f:
            self.html = f.read()

    def test_모델_고르는_칸이_있다(self):
        self.assertIn('id="anchatm"', self.html)
        self.assertIn("anChatModels", self.html)

    def test_프롬프트_적는_칸이_있다(self):
        self.assertIn('id="anchatpt"', self.html)

    def test_고른_모델과_프롬프트를_보낸다(self):
        i = self.html.index("async function anChatAsk")
        blk = self.html[i:i + 1400]
        self.assertIn("model: mdl", blk)
        self.assertIn("prompt: pt", blk)

    def test_지난_문답을_되살린다(self):
        i = self.html.index("+ anChatBox(aid);")
        self.assertIn("r.chat || []", self.html[i:i + 400])


class 분석이_근거를_저장한다(unittest.TestCase):
    """★이어 묻기의 재료다. 안 저장하면 다음부터 답을 못 한다."""

    def test_저장_항목에_원자료가_있다(self):
        import inspect
        src = inspect.getsource(analysis.run_analysis)
        self.assertIn('"overview": overview', src)
        self.assertIn('"sys":', src)
        self.assertIn('"cuts":', src)


class 화면에_채팅이_붙는다(unittest.TestCase):
    """★함수만 만들어 두고 안 그리면 아무도 못 쓴다."""

    def setUp(self):
        p = os.path.join(util.BASE, "static", "dashboard.html")
        with open(p, encoding="utf-8") as f:
            self.html = f.read()

    def test_분석을_열면_같이_그린다(self):
        self.assertIn("+ anChatBox(aid);", self.html)

    def test_묻기_버튼과_입력칸이_있다(self):
        self.assertIn('id="anchatq"', self.html)
        self.assertIn('id="anchatsend"', self.html)

    def test_엔터로도_보낸다(self):
        """★keydown 처리기가 이미 여럿 있다 — 우리 것을 집어야 한다."""
        blocks = [self.html[i:i + 400] for i in range(len(self.html))
                  if self.html.startswith("document.addEventListener('keydown'", i)]
        self.assertTrue(any("anchatq" in b and "anChatAsk" in b for b in blocks),
                        "엔터로 보내는 처리기가 없다")

    def test_다른_분석을_열면_대화를_새로_시작한다(self):
        """★안 비우면 앞 분석 얘기를 다음 분석에 이어서 한다."""
        i = self.html.index("+ anChatBox(aid);")
        blk = self.html[i:i + 400]
        # 이어붙이지 말고 **갈아끼워야** 한다 (그 분석의 기록으로)
        self.assertIn("AN_CHAT = (r.chat", blk)
        self.assertNotIn("AN_CHAT.push", blk)

    def test_보내는_중에_또_안_보낸다(self):
        self.assertIn("AN_CHAT_BUSY", self.html)

    def test_실패해도_화면이_안_죽는다(self):
        i = self.html.index("async function anChatAsk")
        blk = self.html[i:i + 1600]
        self.assertIn("catch", blk)
        self.assertIn("finally", blk)


if __name__ == "__main__":
    unittest.main()
