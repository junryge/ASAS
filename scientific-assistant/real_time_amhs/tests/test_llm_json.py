"""LLM 응답 처리 — 오늘 하루 종일 잡았던 실패들을 케이스로 박아둔다.

전부 실제로 겪은 것들이다 (게이트웨이 로그·화면 붙여넣기에서 나옴):
  · 2·3차가 JSON 대신 추론문을 쓰다 max_tokens 에 걸려 잘림
  · 게이트웨이가 response_format 을 몰라 400 → 옵션 빼고 재시도해야 함
  · 'Invalid model name' 400 을 옵션 탓으로 오해하면 안 됨
  · 503(nginx HTML 통째)이 화면을 덮음 + 재시도 없이 즉시 포기
  · 산문을 JSON 으로 잘못 받아들여 '{"원인": "…산문…"}' 이 통과
"""
import unittest

from . import util  # noqa: F401
import analysis as A
import llm_client as L


class ParseJson(unittest.TestCase):
    REQ = ("원인", "핫구역", "전파경로", "요약")
    OK = ('{"원인":"STB 포화","핫구역":["M16HUB"],'
          '"전파경로":"단일 구역","요약":"허브 포화."}')

    def test_그냥_JSON(self):
        self.assertIsNotNone(A._parse_or_none(self.OK, self.REQ))

    def test_코드펜스_감싼_JSON(self):
        self.assertIsNotNone(A._parse_or_none("```json\n" + self.OK + "\n```", self.REQ))

    def test_영어_추론_뒤에_JSON(self):
        """gpt-oss 가 'We need to produce JSON…' 을 먼저 쓰던 경우."""
        t = "We need to produce JSON with fields 원인, 핫구역. Let me check.\n" + self.OK
        self.assertIsNotNone(A._parse_or_none(t, self.REQ))

    def test_한국어_추론_뒤에_JSON(self):
        t = "사용자의 요청은 2차 분석가 역할로… 페르소나 확인: 한국어.\n" + self.OK
        self.assertIsNotNone(A._parse_or_none(t, self.REQ))

    def test_잘린_JSON_은_복구한다(self):
        t = '{"원인":"STB 포화","핫구역":["M16HUB"],"전파경로":"단일 구역","요약":"허브'
        self.assertIsNotNone(A._parse_or_none(t, self.REQ))

    def test_산문은_JSON_으로_받지_않는다(self):
        """★복구 로직이 산문을 {"원인": "…"} 로 만들어 통과시키던 버그."""
        self.assertIsNone(A._parse_or_none("허브 저장율이 포화되어 반송이 지연됐습니다.", self.REQ))

    def test_키가_모자라면_거절(self):
        self.assertIsNone(A._parse_or_none('{"원인":"포화"}', self.REQ))

    def test_프리필이_앞에_겹친_깨진_형태(self):
        """'{"구간": "```json {"구간":"…' 처럼 프리필이 두 번 붙던 경우."""
        t = '{"원인": "```json ' + self.OK
        self.assertIsNotNone(A._parse_or_none(t, self.REQ))


class GatewayOptions(unittest.TestCase):
    """response_format / chat_template_kwargs 를 400 으로 거부당했을 때."""

    def test_티어는_전체_response_format만_없음_순서(self):
        t = A._opt_tiers({"json_mode": True, "disable_thinking": True},
                         "gaia-Qwen3.6-35B-A3B", want_json=True)
        self.assertEqual(len(t), 3)
        self.assertIn("response_format", t[0])
        self.assertIn("chat_template_kwargs", t[0])
        self.assertEqual(list(t[1]), ["response_format"])
        self.assertIsNone(t[2])

    def test_gpt_oss_에는_reasoning_effort(self):
        t = A._opt_tiers({"json_mode": True, "disable_thinking": True},
                         "gaia-lst-gpt-oss-120b", want_json=True)
        self.assertEqual(t[0].get("reasoning_effort"), "low")

    def test_마크다운_단계는_옵션_없음(self):
        """최종 리포트는 JSON 이 아니다 — response_format 을 붙이면 안 된다."""
        self.assertEqual(A._opt_tiers({}, "gaia-GLM-5.2", want_json=False), [None])

    def test_400은_옵션_거부로_본다(self):
        self.assertTrue(A._opt_rejected("HTTP 400: Unrecognized request argument"))
        self.assertTrue(A._opt_rejected("HTTP 422: unprocessable"))

    def test_모델_문제_400은_옵션_탓이_아니다(self):
        """★옵션을 빼봐야 소용없다 — 바로 대체 모델로 가야 한다."""
        self.assertFalse(A._opt_rejected('HTTP 400: {"error":"Invalid model name"}'))
        self.assertFalse(A._opt_rejected("HTTP 403: team not allowed"))

    def test_5xx는_옵션_거부가_아니다(self):
        self.assertFalse(A._opt_rejected("HTTP 503: Service Unavailable"))


class Transient(unittest.TestCase):
    """게이트웨이 일시 장애 — 모델·프롬프트 잘못이 아니다."""

    NGINX = ('HTTP 503: {"error":{"message":"litellm.ServiceUnavailableError: '
             'Hosted_vllmException - <html><head><title>503 Service Temporarily '
             'Unavailable</title></head><body><center><h1>503 Service Temporarily '
             'Unavailable</h1></center><hr><center>nginx</center></body></html>"}}')

    def test_503_은_일시장애(self):
        self.assertTrue(A._is_transient(self.NGINX))
        for e in ("HTTP 429", "HTTP 500", "HTTP 502", "HTTP 504",
                  "Connection reset by peer"):
            self.assertTrue(A._is_transient(e), e)

    def test_JSON_형식_오류는_일시장애가_아니다(self):
        self.assertFalse(A._is_transient("JSON 형식 아님 (필수 키 없음)"))
        self.assertFalse(A._is_transient("HTTP 400: Invalid model name"))

    def test_nginx_HTML_은_한_줄로_줄인다(self):
        s = A._short_err(self.NGINX)
        self.assertLess(len(s), 60, s)
        self.assertIn("503", s)
        self.assertNotIn("<html>", s)
        self.assertNotIn("nginx", s)

    def test_줄인_문구를_또_넣어도_그대로(self):
        """_fail_kind 가 이미 줄인 문구를 다시 보고 판정한다 — 멱등이어야 함."""
        once = A._short_err(self.NGINX)
        self.assertEqual(A._short_err(once), once)
        self.assertTrue(A._is_transient(once))
        self.assertEqual(A._fail_kind([once]), "gateway")

    def test_LLM_실패는_gateway_가_아니다(self):
        self.assertEqual(A._fail_kind("JSON 형식 아님"), "llm")
        self.assertIn("LLM 실패", A._fill_status("JSON 형식 아님"))
        self.assertIn("게이트웨이", A._fill_status([A._short_err(self.NGINX)]))


class ReasoningLeak(unittest.TestCase):
    def test_추론문을_알아본다(self):
        self.assertTrue(A._looks_like_reasoning(
            "We need to produce JSON with fields: 검증, 확인된사실…"))
        self.assertTrue(A._looks_like_reasoning(
            "사용자의 요청은 반송 데이터 2차 분석가 역할로, 제공된 통계를…"))

    def test_JSON_은_추론문이_아니다(self):
        self.assertFalse(A._looks_like_reasoning('{"원인":"포화"}'))

    def test_사고모델_판별(self):
        for m in ("gaia-GLM-5.2", "gaia-Qwen3.6-35B-A3B", "gaia-lst-gpt-oss-120b",
                  "gaia-Qwen3.5-397B-A17B"):
            self.assertTrue(L._is_reasoning_model(m), m)

    def test_think_블록_제거(self):
        self.assertEqual(L._strip_think("<think>고민중</think>답"), "답")
        self.assertEqual(L._strip_think("<think>닫히지 않고 잘림"), "")

    def test_금지어는_결정적으로_치환(self):
        out = L.scrub("리프터 역방향 카운트 4개, 역증가 발생")
        for w in ("역방향", "역증가", "카운트"):
            self.assertNotIn(w, out)


if __name__ == "__main__":
    unittest.main()


class AnalysisThreshold(unittest.TestCase):
    """LLM 모델 분석(4단계) 프롬프트의 임계·등급 — 시스템별 컷을 따라가야 한다.

    ★'[사건 목록] (점수 50+ …)' 이 문자열로 박혀 있었다. 경계 하한을 60 으로
      올린 뒤에도 LLM 에게 "50점 이상이 사건" 이라고 알려주고 있었고,
      daily.MIN_SCORE 도 50 이라 이벤트 목록·일일통계가 50 기준으로 세어졌다.
    """

    @staticmethod
    def _seq(scores):
        from datetime import datetime
        out = []
        for i, s in enumerate(scores):
            r = {"datetime": f"2026-08-18 00:{i:02d}", "unified_risk_score": s,
                 "hot_area": "M16HUB", "reason": "발동: M16HUB[R-C]"}
            out.append((datetime.strptime(r["datetime"], "%Y-%m-%d %H:%M"),
                        float(s), r))
        return out

    def setUp(self):
        import copy
        from lp_client import load_config
        self.cfg = copy.deepcopy(load_config())
        self.cfg.setdefault("grade", {})["by_sys"] = {
            "M16B": {"warn": 70, "danger": 80, "critical": 90}}

    def test_프롬프트에_50이_박혀있지_않다(self):
        from analysis import _overview
        txt, meta = _overview(self._seq((5, 55, 65, 72, 88, 40)), self.cfg, "00:00~00:05")
        self.assertIn("점수 60+", txt)
        self.assertNotIn("점수 50+", txt)
        self.assertIn("60~70 경계", txt)
        self.assertEqual(meta["floor"], 60)

    def test_FAB_은_자기_컷을_설명한다(self):
        from analysis import _overview
        from lp_client import sys_cfg
        txt, meta = _overview(self._seq((5, 55, 65, 72, 88, 40)),
                              sys_cfg(self.cfg, "M16B"), "00:00~00:05")
        self.assertEqual(meta["floor"], 70)
        self.assertIn("점수 70+", txt)
        self.assertIn("70~79 경계", txt)
        self.assertIn("90~100 초위험", txt)

    def test_이벤트_목록도_시스템_임계로_잡힌다(self):
        """M16B(임계 70)에서는 65점이 이벤트 시작이 아니어야 한다."""
        from analysis import _overview
        from lp_client import sys_cfg
        _, m_all = _overview(self._seq((5, 65, 66, 40)), self.cfg, "x")
        _, m_fab = _overview(self._seq((5, 65, 66, 40)), sys_cfg(self.cfg, "M16B"), "x")
        self.assertEqual(m_all["incidents"], 1, "ALL(60) 에서는 65점이 이벤트")
        self.assertEqual(m_fab["incidents"], 0, "M16B(70) 에서는 이벤트 아님")
