"""알아서 만들기 — 내용만 적으면 발표자료가 나온다.

왜 이게 있나
    "MD 문법을 알아야 하고, 탭을 고르고, 모델을 고르고" 는 도구가 사람한테
    일을 시키는 것이다. 회의록이든 메모든 붙여 넣으면 나와야 한다.

두 갈래를 다 확인한다
    1) LLM 이 붙었을 때 — 모델이 **무슨 내용인지만** 낸다(좌표 X).
    2) LLM 이 없거나 헛소리를 냈을 때 — 규칙으로라도 나온다.
       ★"모델이 안 붙어서 못 만들었습니다" 는 답이 아니다.
"""
from __future__ import annotations

import json
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from demos_v1 import auto_deck as ad          # noqa: E402
from demos_v1 import bento_builder as bb      # noqa: E402

# 사람이 실제로 붙여 넣을 법한 글 — MD 문법이 아니다
회의록 = """반송 정체 점검 회의
2026-08-19 오전

현황:
- 리프터 대기시간이 3.2분에서 7.8분으로 늘었다
  - 새벽 2시 이후 특히 심함
- ML 조기예측은 10분 앞을 가리키고 있다

원인으로 보이는 것
HID 편중이 심해졌다. 상위 3개 HID 가 전체의 절반을 먹고 있다.
반송 지연도 같이 올라간다.

조치:
1) 임계값을 0.30 에서 0.25 로 내린다
2) 야간 순찰 경로를 바꾼다
"""


class 규칙(unittest.TestCase):
    """LLM 없이도 뭐라도 나와야 한다."""

    def out(self, t=회의록, **kw):
        return ad.plain_to_outline(t, **kw)

    def test_MD_문법을_몰라도_된다(self):
        o = self.out()
        self.assertGreaterEqual(len(o["slides"]), 3)
        self.assertEqual(o["slides"][0]["type"], "title")
        self.assertEqual(o["slides"][0]["title"], "반송 정체 점검 회의")
        self.assertEqual(o["slides"][0]["subtitle"], "2026-08-19 오전")

    def test_콜론_제목을_장으로_끊는다(self):
        titles = [s.get("title") for s in self.out()["slides"]]
        self.assertIn("현황", titles)
        self.assertIn("조치", titles)

    def test_내용이_사라지지_않는다(self):
        """★제일 나쁜 건 조용히 빠지는 것이다."""
        body = json.dumps(self.out(), ensure_ascii=False)
        for w in ("리프터 대기시간", "새벽 2시", "ML 조기예측",
                  "HID 편중", "임계값", "야간 순찰"):
            self.assertIn(w, body, f"'{w}' 가 사라졌다")

    def test_들여쓴_줄은_하위_항목이_된다(self):
        for s in self.out()["slides"]:
            for b in s.get("bullets", []):
                if "새벽 2시" in b["text"]:
                    self.assertEqual(b["level"], 1)
                    return
        self.fail("하위 항목을 못 찾았다")

    def test_홀로_선_짧은_줄은_제목이다(self):
        """★사람은 콜론을 항상 찍지 않는다. '원인으로 보이는 것' 이 글머리로
        들어가면 제목이 본문 한가운데 섞여 버린다."""
        titles = [s.get("title") for s in self.out()["slides"]]
        self.assertIn("원인으로 보이는 것", titles)
        for s in self.out()["slides"]:
            for b in s.get("bullets", []):
                self.assertNotEqual(b["text"], "원인으로 보이는 것")

    def test_마침표가_들쭉날쭉하지_않다(self):
        """★한 장 안에서 어떤 줄엔 붙고 어떤 줄엔 없으면 지저분하다."""
        for s in self.out()["slides"]:
            for b in s.get("bullets", []):
                self.assertFalse(b["text"].endswith("."), b["text"])

    def test_숫자_뒤_점은_안_건드린다(self):
        o = ad.plain_to_outline("제목\n\n항목:\n- 버전 1.0.")
        self.assertIn("버전 1.0.", json.dumps(o, ensure_ascii=False))

    def test_승격시켜도_제목을_안_잃는다(self):
        """★clear() 뒤에 title 을 읽어서 제목이 사라졌었다."""
        o = ad.plain_to_outline("보고\n\n대기시간:\n- 7.8분")
        big = next(s for s in o["slides"] if s["type"] == "bignumber")
        self.assertEqual(big["title"], "대기시간")

    def test_긴_단락은_문장으로_쪼갠다(self):
        o = ad.plain_to_outline("메모\n\n첫 문장이다. 두 번째 문장이다. 세 번째다.")
        bl = [b["text"] for s in o["slides"] for b in s.get("bullets", [])]
        self.assertGreaterEqual(len(bl), 3, "한 덩어리로 박아 넣었다")

    def test_한_장에_너무_많으면_나눈다(self):
        """★넘치면 글씨만 작아진다. 장을 나누는 게 낫다."""
        t = "제목\n\n항목:\n" + "".join(f"- 항목 {i}\n" for i in range(14))
        o = ad.plain_to_outline(t)
        for s in o["slides"]:
            tops = [b for b in s.get("bullets", []) if b["level"] == 0]
            self.assertLessEqual(len(tops), ad.MAX_BULLETS)

    def test_표와_코드도_알아본다(self):
        t = ("보고서\n\n| 시각 | 점수 |\n|---|---|\n| 01:00 | 42 |\n\n"
             "```python\nx = 1\n```\n")
        kinds = [s["type"] for s in ad.plain_to_outline(t)["slides"]]
        self.assertIn("table", kinds)
        self.assertIn("code", kinds)

    def test_표의_구분줄은_행이_아니다(self):
        t = "제목\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"
        tbl = next(s for s in ad.plain_to_outline(t)["slides"]
                   if s["type"] == "table")
        self.assertEqual(tbl["headers"], ["a", "b"])
        self.assertEqual(tbl["rows"], [["1", "2"]])

    def test_마크다운_장식을_걷어낸다(self):
        o = ad.plain_to_outline("제목\n\n- **굵게** 와 `코드` 와 [링크](http://x)")
        txt = json.dumps(o, ensure_ascii=False)
        for ch in ("**", "`", "](http"):
            self.assertNotIn(ch, txt)

    def test_숫자_한_줄은_크게(self):
        o = ad.plain_to_outline("제목\n\n대기시간:\n- 7.8분")
        self.assertIn("bignumber", [s["type"] for s in o["slides"]])

    def test_너무_길면_줄이고_밝힌다(self):
        """★잘라 놓고 말을 안 하면 전부인 줄 안다."""
        t = "제목\n\n" + "".join(f"{i}번 항목:\n- 내용 {i}\n\n" for i in range(40))
        o = ad.plain_to_outline(t)
        self.assertLessEqual(len(o["slides"]), ad.MAX_SLIDES + 1)
        self.assertIn("생략", json.dumps(o, ensure_ascii=False))

    def test_빈_입력도_열리는_파일을_준다(self):
        o = ad.plain_to_outline("   \n\n  ")
        self.assertEqual(len(o["slides"]), 1)
        self.assertEqual(o["slides"][0]["type"], "title")

    def test_바로_그려진다(self):
        doc = bb.build_doc(self.out()["slides"])
        body = " ".join(e.get("html", "") for s in doc["slides"]
                        for e in s["elements"] if e["type"] == "text")
        self.assertIn("리프터 대기시간", body)


class 모델출력정리(unittest.TestCase):
    """★모델 출력은 못 믿는다. 살릴 건 살리고 나머지는 버린다."""

    GOOD = {"meta": {"title": "반송 정체", "subtitle": "2026-08-19"},
            "slides": [
                {"type": "compare2", "title": "전후", "left_title": "이전",
                 "left_items": ["3.2분"], "right_title": "지금",
                 "right_items": ["7.8분"]},
                {"type": "bignumber", "title": "핵심", "number": "2.4배",
                 "label": "증가"}]}

    def test_정상_출력을_받는다(self):
        o = ad.normalize_outline(self.GOOD)
        self.assertEqual(o["slides"][0]["type"], "title")   # 표지는 우리가 붙인다
        self.assertEqual(o["meta"]["title"], "반송 정체")
        self.assertEqual(len(o["slides"]), 3)

    def test_문자열로_와도_읽는다(self):
        self.assertIsNotNone(
            ad.normalize_outline(json.dumps(self.GOOD, ensure_ascii=False)))

    def test_모르는_종류는_content로_떨군다(self):
        o = ad.normalize_outline({"slides": [
            {"type": "3d홀로그램", "title": "t",
             "bullets": [{"text": "살아남아야 한다"}]}]})
        self.assertEqual(o["slides"][1]["type"], "content")
        self.assertEqual(o["slides"][1]["bullets"][0]["text"], "살아남아야 한다")

    def test_글머리가_그냥_문자열이어도_받는다(self):
        o = ad.normalize_outline({"slides": [
            {"type": "content", "title": "t", "bullets": ["가", "나"]}]})
        self.assertEqual(o["slides"][1]["bullets"][0],
                         {"text": "가", "level": 0})

    def test_알맹이_없는_장은_버린다(self):
        """★빈 장을 그리면 '만들다 만 것' 처럼 보인다."""
        o = ad.normalize_outline({"slides": [
            {"type": "content", "title": "빈 장", "bullets": []},
            {"type": "statement", "title": "빈 선언"},
            {"type": "grid", "title": "빈 격자", "cards": []},
            {"type": "statement", "title": "쓸 것", "statement": "결론"}]})
        self.assertEqual(len(o["slides"]), 2)               # 표지 + 결론
        self.assertEqual(o["slides"][1]["statement"], "결론")

    def test_망가진_출력은_None(self):
        for bad in (None, "그냥 잡담", {"slides": "문자열"}, {}, [1, 2],
                    {"slides": [{"type": "content", "bullets": []}]}):
            self.assertIsNone(ad.normalize_outline(bad), repr(bad))

    def test_단계값이_이상해도_안_죽는다(self):
        o = ad.normalize_outline({"slides": [{"type": "content", "title": "t",
            "bullets": [{"text": "가", "level": "깊게"},
                        {"text": "나", "level": 99}]}]})
        lv = [b["level"] for b in o["slides"][1]["bullets"]]
        self.assertEqual(lv, [0, 2])

    def test_정리된_결과가_바로_그려진다(self):
        o = ad.normalize_outline(self.GOOD)
        doc = bb.build_doc(o["slides"])
        body = " ".join(e.get("html", "") for s in doc["slides"]
                        for e in s["elements"] if e["type"] == "text")
        for w in ("이전", "지금", "2.4배"):
            self.assertIn(w, body)


class 라우트(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import demos_v1
            cls.client = demos_v1.create_app().test_client()
        except Exception as e:
            raise unittest.SkipTest(f"앱을 못 띄운다: {e}")

    def test_모델_없이도_만들어_준다(self):
        """★이 환경엔 사내 토큰이 없다 — 그래도 결과가 나와야 한다."""
        r = self.client.post("/api/ppt/auto", json={"text": 회의록,
                                                     "theme": "hynix"})
        self.assertEqual(r.status_code, 200, r.data[:300])
        d = r.get_json()
        self.assertGreater(d["slide_count"], 2)
        self.assertTrue(d["filename"].endswith(".bento.html"))
        self.assertIn(d["used"], ("규칙", "llm"))

    def test_무엇으로_만들었는지_알려_준다(self):
        """★규칙으로 만들어 놓고 'AI가 만들었습니다' 하면 거짓말이다."""
        d = self.client.post("/api/ppt/auto", json={"text": 회의록}).get_json()
        self.assertIn("used", d)

    def test_내려받아진다(self):
        d = self.client.post("/api/ppt/auto", json={"text": 회의록}).get_json()
        r = self.client.get(d["download_url"])
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data.startswith(b"<!DOCTYPE html"))

    def test_빈_내용은_400(self):
        r = self.client.post("/api/ppt/auto", json={"text": "  "})
        self.assertEqual(r.status_code, 400)

    def test_pptx로도_받을_수_있다(self):
        d = self.client.post("/api/ppt/auto",
                             json={"text": 회의록, "format": "pptx"}).get_json()
        self.assertTrue(d["filename"].endswith(".pptx"), d)

    def test_모델이_있으면_모델을_쓴다(self):
        """모델 호출 자리만 가짜로 바꿔 경로를 확인한다 (실제 호출 X)."""
        from demos_v1 import routes_ppt as rp
        called = {}

        def fake(model_id, system, user, max_tokens=4096):
            called["sys"] = system
            called["user"] = user
            return json.dumps(모델출력정리.GOOD, ensure_ascii=False), ""

        rm, rt = rp._llm_text, rp._auto_model
        rp._llm_text, rp._auto_model = fake, (lambda: "가짜모델")
        try:
            d = self.client.post("/api/ppt/auto",
                                 json={"text": 회의록}).get_json()
        finally:
            rp._llm_text, rp._auto_model = rm, rt
        self.assertEqual(d["used"], "llm")
        self.assertEqual(d["model"], "가짜모델")
        self.assertEqual(d["slide_count"], 3)
        # ★모델한테 좌표를 시키지 않는다 — 그건 우리가 한다
        self.assertNotIn("inch", called["sys"])
        self.assertIn("배치·좌표", called["sys"])
        self.assertIn("리프터", called["user"])

    def test_모델이_헛소리하면_규칙으로_내려간다(self):
        """★모델이 깨진 걸 냈다고 사용자가 빈손으로 돌아가면 안 된다."""
        from demos_v1 import routes_ppt as rp
        rm, rt = rp._llm_text, rp._auto_model
        rp._llm_text = lambda *a, **k: ("이건 JSON 이 아니고 그냥 잡담", "")
        rp._auto_model = lambda: "가짜모델"
        try:
            d = self.client.post("/api/ppt/auto",
                                 json={"text": 회의록}).get_json()
        finally:
            rp._llm_text, rp._auto_model = rm, rt
        self.assertEqual(d["used"], "규칙")
        self.assertGreater(d["slide_count"], 2)
        self.assertTrue(d["note"], "왜 규칙으로 갔는지 말을 안 한다")

    def test_모델_고장도_규칙으로_내려간다(self):
        from demos_v1 import routes_ppt as rp
        rm, rt = rp._llm_text, rp._auto_model
        rp._llm_text = lambda *a, **k: ("", "API 500: 서버 죽음")
        rp._auto_model = lambda: "가짜모델"
        try:
            d = self.client.post("/api/ppt/auto",
                                 json={"text": 회의록}).get_json()
        finally:
            rp._llm_text, rp._auto_model = rm, rt
        self.assertEqual(d["used"], "규칙")
        self.assertIn("500", d["note"])


class 모델자동선택(unittest.TestCase):
    def test_쓸_수_있는_걸_고른다(self):
        """★'모델을 선택하세요' 는 사용자가 답을 아는 질문이 아니다."""
        from demos_v1 import routes_ppt as rp
        real_cfg, real_tok = rp.ENV_CONFIG, rp.API_TOKEN
        try:
            rp.ENV_CONFIG = {"api1": {"url": "http://x"},
                             "g1": {"url": "python://gguf", "_gguf_path": "/a"}}
            rp.API_TOKEN = "토큰있음"
            self.assertEqual(rp._auto_model(), "api1")
            rp.API_TOKEN = ""                     # 집 — 토큰이 없다
            self.assertEqual(rp._auto_model(), "g1")
            rp.ENV_CONFIG = {}
            self.assertEqual(rp._auto_model(), "")
        finally:
            rp.ENV_CONFIG, rp.API_TOKEN = real_cfg, real_tok


if __name__ == "__main__":
    unittest.main()
