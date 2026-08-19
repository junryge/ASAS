#!/usr/bin/env python3
"""ML 조기예측 "왜 이랬나" — 근거 계산 + LLM 설명.

무엇이 문제였나
    최근 기록에 확률과 단계만 줄줄이 찍혔다. 03:12 에 선제경보가 떴다는
    것은 알겠는데 **왜** 떴는지가 없었다.

지켜야 할 순서
    1) 근거를 계산으로 먼저 뽑는다 (ML 추이 + 같은 시각 룰베이스 기여 지표).
    2) LLM 에게는 그 근거만 읽힌다 — 원본 CSV 를 던지면 숫자를 지어낸다.
    3) LLM 이 죽어도 근거는 그대로 나온다.
"""
from __future__ import annotations

import csv
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import ml_why                                   # noqa: E402

DAY = "20260819"
AT = datetime(2026, 8, 19, 3, 12)


def _ml_rows():
    """03:00 평온 → 03:05 부터 확률이 올라가 03:10 선제경보."""
    import ml_feed
    out = []
    for k in range(40):                          # 02:45 ~ 03:24
        t = datetime(2026, 8, 19, 2, 45) + timedelta(minutes=k)
        ramp = max(0.0, (k - 20) / 20.0)         # 03:05 부터 상승
        p10 = round(min(0.92, 0.02 + ramp * 1.2), 3)
        sm = round(9.0 + ramp * 6.0, 2)
        stage = "2" if p10 >= 0.30 else ("1" if p10 >= 0.15 else "0")
        out.append({
            "datetime": t.strftime("%Y-%m-%d %H:%M"),
            "prediction_for_10m": (t + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M"),
            "prediction_for_30m": (t + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M"),
            "ml_score_10m": str(p10), "ml_score_30m": str(round(p10 * 0.8, 3)),
            "ml_level_10m": "위험" if p10 >= 0.6 else ("경계" if p10 >= 0.3 else "정상"),
            "ml_level_30m": "정상",
            "raw_value": str(round(sm + 0.4, 2)), "smoothed": str(sm),
            "threshold": "14.765",
            "stage": stage, "stage_name": ml_feed.STAGES[stage][0],
            "lead_min": "10" if stage == "2" else "",
            "reason": "10분 평균이 임계에 접근" if stage != "0" else "",
            "backend": "chronos-2",
        })
    return out


def _rt_rows():
    """같은 시간대 실시간 관제 행 — 03:05 부터 지표가 뛴다.

    ★컬럼명을 지어내면 안 된다. 기여도 분해는 config 의 ui.metric_groups
      키를 그대로 읽는다 — 이름이 다르면 지표가 하나도 안 잡힌다
      (처음에 그렇게 만들었다가 기여 지표가 빈 채로 통과할 뻔했다).
    """
    import random
    rnd = random.Random(7)
    out = []
    for k in range(180):                         # 00:15 ~ 03:14 (평소 구간 확보)
        t = datetime(2026, 8, 19, 0, 15) + timedelta(minutes=k)
        hot = t >= datetime(2026, 8, 19, 3, 5)
        out.append({
            "datetime": t.strftime("%Y-%m-%d %H:%M:%S"),
            "unified_risk_score": f"{74 if hot else rnd.uniform(10, 25):.1f}",
            "hot_area": "M16HUB",
            "reason": ("hot_area=M16HUB; S3확정; 발동: M16HUB[R-A_sus,R-C]"
                       if hot else ""),
            "M16HUB_ra": f"{8.6 if hot else rnd.uniform(2.4, 3.0):.2f}",
            "M16HUB_stb_util": f"{98.6 if hot else 97.9 + rnd.uniform(-.3, .3):.2f}",
            "M16HUB_rev_count": f"{7 if hot else rnd.choice([0, 0, 1]):.0f}",
            "M16HUB_rd_fab": f"{1.24 if hot else 1.15 + rnd.uniform(-.05, .05):.2f}",
        })
    return out


class 근거(unittest.TestCase):
    """LLM 없이도 근거는 나와야 한다."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="mlwhy_")
        import ml_feed
        import store_csv
        from lp_client import load_config
        # ★진짜 설정을 바탕으로 폴더만 임시로 돌린다. 설정을 통째로 지어내면
        #   지표 정의(ui.metric_groups)가 통째로 빠져 근거가 비어 버린다.
        cls.cfg = load_config()
        cls.cfg.setdefault("storage", {})["daily_csv_dir"] = os.path.join(cls.tmp, "rt")
        cls.cfg.setdefault("ml", {}).update(
            {"enabled": True, "sys": "ALL", "p_on": 0.30, "p_off": 0.20})
        os.makedirs(os.path.join(cls.tmp, "rt"), exist_ok=True)
        ml_feed._write(DAY, _ml_rows(), cls.cfg)
        rp = store_csv.day_path(DAY, cls.cfg)
        rows = _rt_rows()
        with open(rp, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def ev(self):
        return ml_why.explain(AT, self.cfg, use_llm=False)

    def test_그_분의_ML값을_찾는다(self):
        ml = self.ev()["ml"]
        self.assertTrue(ml["ok"], ml.get("error"))
        self.assertEqual(ml["at"], "2026-08-19 03:12")
        self.assertGreater(ml["p10"], 0.3)
        self.assertEqual(ml["threshold"], 14.765)

    def test_앞뒤_추이를_같이_준다(self):
        """★값 하나만 보면 '높다' 는 알아도 올라오는 중인지 모른다."""
        ml = self.ev()["ml"]
        self.assertGreaterEqual(len(ml["trend"]), 20)
        self.assertGreater(ml["d_p10"], 0, "상승 중인데 변화량이 0 이하다")
        self.assertGreater(ml["d_smoothed"], 0)

    def test_언제부터_이랬는지_짚는다(self):
        """'언제부터' 가 없으면 관제에서 할 수 있는 게 없다."""
        o = self.ev()["ml"]["onset"]
        self.assertIsNotNone(o, "단계가 올라간 시점을 못 찾았다")
        self.assertEqual(o["to"], "2")
        self.assertLessEqual(o["at"], "03:12")

    def test_임계까지_얼마나_남았나(self):
        ml = self.ev()["ml"]
        self.assertIsNotNone(ml["near_pct"])
        self.assertGreater(ml["near_pct"], 50)

    def test_같은_시각_실시간_근거도_읽는다(self):
        """★ML 이 '넘겠다' 고 할 때 현장에서 무슨 일이 있었는지는 이쪽에만 있다."""
        rule = self.ev()["rule"]
        self.assertTrue(rule["ok"], rule.get("error"))
        self.assertIsNotNone(rule["score"])
        self.assertTrue(rule["items"], "기여 지표가 비었다")

    def test_지표는_컬럼명이_아니라_값을_준다(self):
        """★contrib 의 'raw' 는 값이 아니라 원본 컬럼명이다
        (M16HUB.QUE.TIME.AVGTOTALTIME1MIN). 이걸 값으로 착각해서 화면에
        컬럼명이 찍혔고, LLM 에게도 값 대신 이름을 줄 뻔했다 — 그러면
        LLM 은 숫자를 지어낸다."""
        for i in self.ev()["rule"]["items"]:
            self.assertIsInstance(i["value"], (int, float),
                                  f"{i['label']} 의 값이 숫자가 아니다: {i['value']!r}")
            self.assertIsInstance(i["base"], (int, float))
            # 컬럼명은 버리지 않고 따로 들고 간다 (화면에 작게 같이 보여준다)
            self.assertTrue(str(i.get("col") or "").strip(), "원본 컬럼명이 없다")
        t = self.ev()["evidence_text"]
        self.assertNotIn("AVGTOTALTIME1MIN", t, "근거글에 컬럼명이 값 자리에 들어갔다")

    def test_점수도_추이를_준다(self):
        """★ML 쪽만 추이를 주고 룰 쪽은 한 점만 주면, '누가 먼저 말했나'
        를 화면이 주장만 하고 보여 주지는 못한다."""
        rule = self.ev()["rule"]
        self.assertTrue(rule["trend"], "점수 추이가 비었다")
        self.assertIn("score", rule["trend"][0])
        self.assertIsNotNone(rule["d_score"])
        self.assertGreater(rule["d_score"], 0, "올라오는 중인데 변화량이 0 이하다")

    def test_점수가_언제_넘었는지_짚는다(self):
        """경보 기준을 넘은 시각 — 이게 있어야 ML 과 몇 분 차이인지 센다."""
        self.assertEqual(self.ev()["rule"]["onset"], "03:05")

    def test_누가_먼저_말했는지_센다(self):
        """★ML 선제경보 03:10 vs 룰 60점 03:05 — 룰이 5분 먼저다.
        '독립 두 시스템 비교' 는 이 숫자가 없으면 말뿐이다."""
        ag = self.ev()["agree"]
        self.assertEqual(ag["ml_at"], "03:10")
        self.assertEqual(ag["rule_at"], "03:05")
        self.assertEqual(ag["lead_min"], -5)
        self.assertIn("룰베이스가 5분 먼저", ag["verdict"])

    def test_경보끼리_견준다(self):
        """★관찰(단계1)과 경보(60점)를 견주면 ML 이 늘 먼저인 것처럼 보인다.
        ML 은 03:08 에 관찰로 올랐지만 경보는 03:10 이다."""
        ml = self.ev()["ml"]
        self.assertEqual(ml["onset"]["at"], "03:10")     # 지금 단계가 언제부터
        self.assertEqual(ml["alarm_at"], "03:10")        # 경보를 언제 넘었나
        self.assertNotEqual(ml["alarm_at"], "03:08")

    def test_관찰_단계에서는_경보시각이_없다(self):
        """★03:09 는 ML 이 '관찰'(단계1)로만 올라간 상태다. 이걸 룰의 경보
        시각과 견주면 'ML 이 먼저 말했다' 는 없는 사실이 만들어진다."""
        ev = ml_why.explain(datetime(2026, 8, 19, 3, 9), self.cfg, use_llm=False)
        ml = ev["ml"]
        self.assertEqual(ml["stage"], "1")
        self.assertEqual(ml["onset"]["at"], "03:08")   # 관찰로 올라간 시각
        self.assertIsNone(ml["alarm_at"], "경보를 넘지도 않았는데 시각이 있다")
        ag = ev["agree"]
        self.assertFalse(ag["ml_fired"])
        self.assertIsNone(ag["lead_min"], "관찰을 경보와 견주어 선후를 셌다")

    def test_평온하면_넘은_시각이_없다(self):
        ev = ml_why.explain(datetime(2026, 8, 19, 2, 50), self.cfg, use_llm=False)
        self.assertIsNone(ev["rule"]["onset"])

    def test_근거글에_점수_추이도_넣는다(self):
        """LLM 이 못 본 숫자는 쓸 수 없다."""
        t = self.ev()["evidence_text"]
        self.assertIn("점수 변화", t)
        self.assertIn("넘은 건 03:05", t)

    def test_두_시스템_비교를_말해_준다(self):
        """★'누가 맞다' 가 아니라 '같은 말을 했나' 를 본다."""
        ag = self.ev()["agree"]
        self.assertTrue(ag["ml_fired"])
        self.assertIn("verdict", ag)
        self.assertTrue(ag["verdict"].strip())

    def test_근거글에_숫자가_들어간다(self):
        """LLM 이 읽을 글이다 — 여기 없는 숫자는 LLM 도 알 수 없다."""
        t = self.ev()["evidence_text"]
        for w in ("10분 내 임계 초과 확률", "14.765", "실시간 관제", "두 시스템 비교"):
            self.assertIn(w, t)

    def test_평온한_시각도_설명한다(self):
        """경보 때만 되는 게 아니다 — 아무 줄이나 눌러도 답이 있어야 한다."""
        ev = ml_why.explain(datetime(2026, 8, 19, 2, 50), self.cfg, use_llm=False)
        self.assertTrue(ev["ml"]["ok"])
        self.assertFalse(ev["agree"]["ml_fired"])
        self.assertIn("평온", ev["agree"]["verdict"])

    def test_데이터가_없는_시각은_사유를_준다(self):
        """빈손으로 돌려보내지 않는다 — 왜 없는지는 말해 준다."""
        ev = ml_why.explain(datetime(2026, 8, 19, 20, 0), self.cfg, use_llm=False)
        self.assertFalse(ev["ml"]["ok"])
        self.assertTrue(ev["ml"]["error"])

    def test_실시간_데이터가_없어도_ML_근거는_나온다(self):
        """★한쪽이 없다고 화면이 통째로 비면 안 된다.

        ML 파일과 실시간 파일은 같은 폴더에 산다(둘 다 store_csv.data_dir).
        그래서 'ML 만 있는 폴더' 를 따로 만들어 확인한다."""
        import copy
        import ml_feed
        only = os.path.join(self.tmp, "ml만")
        os.makedirs(only, exist_ok=True)
        cfg = copy.deepcopy(self.cfg)
        cfg["storage"]["daily_csv_dir"] = only
        ml_feed._write(DAY, _ml_rows(), cfg)
        ev = ml_why.explain(AT, cfg, use_llm=False)
        self.assertTrue(ev["ml"]["ok"])
        self.assertFalse(ev["rule"]["ok"])
        self.assertIn("근거 없음", ev["evidence_text"])

    def test_시각을_못_읽으면_거절한다(self):
        self.assertFalse(ml_why.explain("어제쯤", self.cfg, use_llm=False)["ok"])


class LLM설명(unittest.TestCase):
    """LLM 은 근거를 '읽고 옮기는' 역할이다."""

    @classmethod
    def setUpClass(cls):
        근거.setUpClass()
        cls.cfg, cls.tmp = 근거.cfg, 근거.tmp

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _with_llm(self, fake_chat):
        import llm_client
        rc, rp = llm_client.chat, llm_client.build_system_prompt
        llm_client.chat = fake_chat
        llm_client.build_system_prompt = lambda cfg=None: "(페르소나)"
        try:
            return ml_why.explain(AT, self.cfg, use_llm=True)
        finally:
            llm_client.chat, llm_client.build_system_prompt = rc, rp

    def test_근거만_읽힌다(self):
        """★원본 CSV 를 던지면 숫자를 지어낸다. 계산된 것만 준다."""
        seen = {}

        def fake(messages, cfg=None, **kw):
            seen["sys"] = messages[0]["content"]
            seen["user"] = messages[1]["content"]
            return "**무슨 일인가** — 반송시간이 임계에 접근했습니다.", None

        ev = self._with_llm(fake)
        self.assertIn("why", ev)
        self.assertIn("[근거]", seen["user"])
        self.assertIn("14.765", seen["user"])
        # 원본 행을 통째로 넣지 않았다
        self.assertNotIn("prediction_for_10m", seen["user"])
        self.assertNotIn("backend", seen["user"])
        # 지어내지 말라는 지시가 들어간다
        self.assertIn("지어내지 마라", seen["sys"])
        self.assertIn("독립된 두 시스템", seen["sys"])

    # ★현장에서 실제로 이렇게 나왔다 — 영어 사고과정을 통째로 쏟고, 그러다
    #   max_tokens 에 걸려 답은 문장 중간에 잘렸다. 부탁으로는 안 막힌다.
    사고과정_영문 = """Thinking Process:

1. Analyze the Request:
* Role: SK Hynix M16 HUBROOM Transport Control Analysis Agent.
* Task: Explain why the ML early prediction made its judgment.
* Constraints: Use only the numbers in the [Evidence].

2. Analyze the Evidence:
* Time: 2026-08-19 16:27
* ML: 10min probability 0%, Stage 정상

3. Drafting the Content:
* Draft: ML 과 룰베이스 모두 정상 상태입니다. 반송 정체"""

    def test_영문_사고과정은_안_쓴다(self):
        """★이게 화면에 그대로 나왔다. 관제가 뭘 알겠나."""
        ev = self._with_llm(lambda *a, **k: (self.사고과정_영문, None))
        self.assertEqual(ev["used"], "규칙")
        self.assertNotIn("Thinking Process", ev["why"])
        self.assertNotIn("Analyze the Request", ev["why"])
        self.assertTrue(ev["llm_error"])

    def test_한국어_서론도_잘라_낸다(self):
        """★사고과정이 한국어로 올 때도 있다. 그건 언어 검사로 못 거른다 —
        소제목 앞을 통째로 잘라야 한다."""
        ev = self._with_llm(lambda *a, **k: (
            "먼저 요청을 분석하겠습니다. 역할은 관제 분석 에이전트이고, "
            "근거의 숫자만 써야 합니다. 이제 초안을 작성합니다.\n\n"
            "**무슨 일인가** — 10분 평균이 임계의 91%입니다.\n"
            "**왜 이렇게 나왔나** — 최근 20분 동안 2.1분 올랐습니다.\n"
            "**무엇을 보면 되나** — 추이가 이어지는지 보세요.", None))
        self.assertEqual(ev["used"], "llm")
        self.assertNotIn("요청을 분석", ev["why"], "서론이 그대로 남았다")
        self.assertNotIn("초안을 작성", ev["why"])
        self.assertTrue(ev["why"].lstrip().startswith("**무슨 일인가"))

    def test_영어로_답하면_거른다(self):
        eng = ("**무슨 일인가** — The transport time is rising.\n"
               "**왜 이렇게 나왔나** — The average exceeded the threshold.\n"
               "**무엇을 보면 되나** — Watch the lifter queue.")
        ev = self._with_llm(lambda *a, **k: (eng, None))
        self.assertEqual(ev["used"], "규칙")
        self.assertIn("한국어", ev["llm_error"])

    def test_중간에_잘리면_거른다(self):
        """★잘린 답을 보여 주면 사람이 그게 전부인 줄 안다."""
        cut = ("**무슨 일인가** — 반송시간이 임계에 접근했습니다.\n"
               "**왜 이렇게 나왔나** — 최근 20분 동안 10분 평균이 올라\n"
               "**무엇을 보면 되나** — 리프터 대기가 계속 늘어나는지 보고 있으면")
        ev = self._with_llm(lambda *a, **k: (cut, None))
        self.assertEqual(ev["used"], "규칙")
        self.assertIn("잘림", ev["llm_error"])

    def test_형식을_지키면_그대로_쓴다(self):
        good = ("**무슨 일인가** — 10분 평균이 임계의 91%까지 올라왔습니다.\n"
                "**왜 이렇게 나왔나** — 최근 20분 동안 2.1분 올랐고 "
                "룰베이스도 74점으로 경보 기준을 넘었습니다.\n"
                "**무엇을 보면 되나** — 반송시간이 계속 오르는지 보세요.")
        ev = self._with_llm(lambda *a, **k: (good, None))
        self.assertEqual(ev["used"], "llm")
        self.assertIn("91%", ev["why"])

    def test_사고블록도_떼어_낸다(self):
        ev = self._with_llm(lambda *a, **k: (
            "<think>사용자는 관제 담당자다…</think>\n"
            "**무슨 일인가** — 정상입니다.\n"
            "**왜 이렇게 나왔나** — 확률이 0% 입니다.\n"
            "**무엇을 보면 되나** — 추이가 뒤집히는지 보세요.", None))
        self.assertEqual(ev["used"], "llm")
        self.assertNotIn("think", ev["why"])

    def test_사고차단_옵션을_먼저_건다(self):
        """★'/no_think' 는 무시당한다 — 이 저장소가 JSON 경로에서 이미 배운
        것이다. 게이트웨이 옵션으로 강제하고, 400 이면 빼고 다시 부른다."""
        calls = []

        def fake(messages, cfg=None, **kw):
            calls.append(kw.get("extra"))
            if len(calls) == 1:
                return None, "API 400: unknown field chat_template_kwargs"
            return ("**무슨 일인가** — 정상입니다.\n"
                    "**왜 이렇게 나왔나** — 확률이 0% 입니다.\n"
                    "**무엇을 보면 되나** — 추이를 보세요.", None)

        ev = self._with_llm(fake)
        self.assertEqual(len(calls), 2, "400 을 받고 옵션을 빼고 다시 안 불렀다")
        self.assertEqual(calls[0], {"chat_template_kwargs": {"enable_thinking": False}})
        self.assertIsNone(calls[1])
        self.assertEqual(ev["used"], "llm")

    def test_규칙_요약도_한국어_세_줄이다(self):
        """★모델이 못 쓰면 우리가 쓴다. 숫자는 이미 다 계산해 뒀다."""
        ev = self._with_llm(lambda *a, **k: (None, "게이트웨이 죽음"))
        for h in ml_why.HEADS:
            self.assertIn(h, ev["why"], f"'{h}' 가 없다")
        self.assertIn("14.765", ev["why"] + ev["evidence_text"])
        import llm_client
        self.assertTrue(llm_client._is_korean(ev["why"], 0.25))

    def test_어떤_모델을_썼는지_알려_준다(self):
        """★모르면 답이 이상할 때 무엇을 바꿔야 할지 알 수 없다."""
        seen = {}

        def fake(messages, cfg=None, **kw):
            seen["model"] = (cfg or {}).get("llm", {}).get("model")
            return ("**무슨 일인가** — 정상입니다.\n"
                    "**왜 이렇게 나왔나** — 확률이 0% 입니다.\n"
                    "**무엇을 보면 되나** — 추이를 보세요.", None)

        import llm_client
        rc, rp = llm_client.chat, llm_client.build_system_prompt
        llm_client.chat = fake
        llm_client.build_system_prompt = lambda cfg=None: "(페르소나)"
        try:
            ev = ml_why.explain(AT, self.cfg, use_llm=True, model="gaia-GLM-5.2")
        finally:
            llm_client.chat, llm_client.build_system_prompt = rc, rp
        self.assertEqual(ev["model"], "gaia-GLM-5.2")
        self.assertEqual(seen["model"], "gaia-GLM-5.2", "고른 모델로 안 물었다")

    def test_고를_수_있는_모델을_준다(self):
        ms = ml_why.models(self.cfg)
        self.assertTrue(ms, "모델 목록이 비었다")
        self.assertTrue(all(m.get("id") for m in ms))
        self.assertEqual(len({m["id"] for m in ms}), len(ms), "중복이 있다")
        self.assertEqual(ml_why.default_model(self.cfg), ms[0]["id"])

    def test_LLM이_죽어도_근거는_남는다(self):
        """★설명이 없는 것과 아무것도 없는 것은 다르다.
        이제는 근거로 쓴 한국어 요약까지 낸다 — 대신 '규칙' 이라고 밝힌다."""
        ev = self._with_llm(lambda *a, **k: (None, "API 500"))
        self.assertEqual(ev["used"], "규칙")
        self.assertEqual(ev["llm_error"], "API 500")
        self.assertTrue(ev["ml"]["ok"])
        self.assertIn("14.765", ev["evidence_text"])

    def test_빈_응답도_실패로_본다(self):
        ev = self._with_llm(lambda *a, **k: ("   ", None))
        self.assertIn("llm_error", ev)

    def test_예외가_나도_안_죽는다(self):
        def boom(*a, **k):
            raise RuntimeError("게이트웨이 끊김")
        ev = self._with_llm(boom)
        self.assertIn("게이트웨이 끊김", ev["llm_error"])
        self.assertTrue(ev["ml"]["ok"])

    def test_금지어를_거른다(self):
        """★페르소나 §용어 표준 — LLM 이 어겨도 여기서 지운다."""
        ev = self._with_llm(lambda *a, **k: ("리프터 역방향 카운트가 늘었다", None))
        self.assertNotIn("역방향", ev["why"])


class 라우트(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import server
            cls.app = server.app.test_client()
        except Exception as e:
            raise unittest.SkipTest(f"서버를 못 띄운다: {e}")

    def test_시각이_없으면_400(self):
        self.assertEqual(self.app.get("/api/ml/why").status_code, 400)

    def test_llm_0_이면_계산만(self):
        r = self.app.get("/api/ml/why?at=2026-08-19 03:12&llm=0")
        self.assertEqual(r.status_code, 200, r.data[:200])
        d = r.get_json()
        self.assertIn("ml", d)
        self.assertIn("rule", d)
        self.assertIn("agree", d)
        self.assertNotIn("why", d)

    def test_데이터가_없어도_500이_아니다(self):
        """★관제 화면이다 — 없는 날짜를 눌렀다고 에러 화면을 띄우면 안 된다."""
        r = self.app.get("/api/ml/why?at=1999-01-01 00:00&llm=0")
        self.assertEqual(r.status_code, 200, r.data[:200])
        self.assertFalse(r.get_json()["ml"]["ok"])


if __name__ == "__main__":
    unittest.main()
