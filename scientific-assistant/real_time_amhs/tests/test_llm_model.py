# -*- coding: utf-8 -*-
"""LLM 판단 모델을 화면에서 고르고 저장하나.

2026-09-18 현장 로그 (매분, 여섯 시스템 전부):
    [LLM/1분:M14] ⚠️ HTTP 400: {"error":{"message":"/chat/completions:
      Invalid model name passed in model=gaia-Qwen3.5-397B-A17B.
      Call `/v1/models` to view available models for your key."}}
config 의 모델 이름이 게이트웨이에서 내려간 것이다. 하루 종일 'LLM 판단 일치'
가 통째로 비었는데, 화면에서는 무슨 이름을 써야 하는지도 어디를 고쳐야 하는지도
알 수 없었다 — config.json 을 직접 고치고 재시작해야 했다.

지키는 것
  · 게이트웨이가 알려 주는 목록(/v1/models)을 그대로 보여 준다
  · 고른 값은 **한 번 불러 보고** 되는 것만 저장한다 (틀린 이름을 남기면 또 하루)
  · 저장은 config.json — 재시작해도 남는다
  · 목록을 못 받아도 화면은 뜬다 (직접 입력)
"""
import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)


def _read(*p):
    with open(os.path.join(APP, *p), encoding="utf-8") as fh:
        return fh.read()


class 목록_물어보기(unittest.TestCase):
    def test_주소를_chat_에서_뽑는다(self):
        import llm_client
        f = llm_client.models_url
        self.assertEqual(f({"llm": {"url": "http://x/v1/chat/completions"}}),
                         "http://x/v1/models")
        self.assertEqual(f({"llm": {"url": "http://x/v1/chat/completions/"}}),
                         "http://x/v1/models")
        self.assertEqual(f({"llm": {"url": "https://h:8443/v1/chat/completions"}}),
                         "https://h:8443/v1/models")
        self.assertEqual(f({"llm": {}}), "", "주소가 없으면 빈 글자")

    def test_못_물어봐도_안_터진다(self):
        """폐쇄망·게이트웨이 점검 중 — 목록은 비고 이유만 온다."""
        import llm_client
        items, err = llm_client.list_models(
            {"llm": {"url": "http://주소없음.invalid/v1/chat/completions"}}, force=True)
        self.assertEqual(items, [])
        self.assertTrue(err)

    def test_주소가_비면_그렇게_말한다(self):
        import llm_client
        items, err = llm_client.list_models({"llm": {}}, force=True)
        self.assertEqual(items, [])
        self.assertIn("config.llm.url", err)

    def test_키를_통째로_안_찍는다(self):
        s = _read("llm_client.py")
        i = s.index("def list_models(")
        body = s[i:s.index("\ndef ", i + 10) if "\ndef " in s[i + 10:] else len(s)]
        self.assertNotIn("print(key", body)
        self.assertNotIn("print(f\"{key", body)


class API(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = _read("server.py")

    def test_길이_하나_있다(self):
        self.assertIn('@app.route("/api/llm/model", methods=["GET", "POST"])', self.s)

    def test_GET_은_지금값과_목록을_같이_준다(self):
        i = self.s.index("def api_llm_model(")
        body = self.s[i:i + 2600]
        for k in ('"model"', '"items"', '"error"', '"ok_now"', '"models_url"'):
            self.assertIn(k, body, k + " 가 응답에 없다")
        self.assertIn("llm_client.list_models(CFG", body)

    def test_시험해_보고_안_되면_되돌린다(self):
        """★틀린 이름을 저장하면 또 하루를 날린다."""
        i = self.s.index("def api_llm_model(")
        body = self.s[i:i + 3200]
        self.assertIn('if b.get("test"):', body)
        self.assertIn("lc[\"model\"] = prev", body, "실패하면 옛 값으로 되돌려야 한다")
        self.assertIn('"applied": False', body)

    def test_저장은_config_json_에(self):
        self.assertIn("def _persist_llm_model(", self.s)
        i = self.s.index("def _persist_llm_model(")
        body = self.s[i:i + 900]
        self.assertIn('disk.setdefault("llm", {})["model"] = model', body)
        # ★임시 파일에 쓰고 바꿔치기 — 쓰다 죽어도 config.json 이 깨지지 않는다
        self.assertIn("os.replace(tmp, CONFIG_PATH)", body)

    def test_빈_이름은_막는다(self):
        i = self.s.index("def api_llm_model(")
        body = self.s[i:i + 3200]
        self.assertIn('if not model:', body)
        self.assertIn("len(model) > 200", body)

    def test_메모리에_바로_적용한다(self):
        """재시작해야 반영되면 현장에서 못 쓴다."""
        i = self.s.index("def api_llm_model(")
        self.assertIn('lc = CFG.setdefault("llm", {})', self.s[i:i + 900])


class 화면(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = _read("static", "dashboard.html")

    def test_정책_탭에_카드가_있다(self):
        self.assertIn("<h2>LLM 판단 모델", self.h)
        for i in ("lm-sel", "lm-txt", "lm-reload", "lm-save", "lm-warn", "lm-cur"):
            self.assertIn('id="%s"' % i, self.h, i + " 가 없다")

    def test_정책_탭을_열_때_부른다(self):
        i = self.h.index("}else if(b.dataset.tab==='policy'){")
        self.assertIn("initLlmModel();", self.h[i:i + 220])

    def test_시험_후_저장을_보낸다(self):
        self.assertIn("post('/api/llm/model', {model: m, save: true, test: true})", self.h)

    def test_목록을_못_받아도_직접_넣을_수_있다(self):
        self.assertIn("const LM_CUSTOM = '__직접__';", self.h)
        self.assertIn("직접 입력", self.h)

    def test_지금_값이_목록에_없으면_경고한다(self):
        """이게 바로 이번 사고다 — 조용히 넘어가면 또 못 알아챈다."""
        self.assertIn("d.ok_now === false", self.h)
        self.assertIn("매분 HTTP 400", self.h)

    def test_지금_값이_목록에_없어도_골라_둔다(self):
        self.assertIn("if(LM_CUR && !opts.includes(LM_CUR)) opts.unshift(LM_CUR);", self.h)

    def test_이름을_그대로_넣지_않는다(self):
        """모델 이름은 게이트웨이가 준 글자다 — esc 를 거쳐야 한다."""
        i = self.h.index("function lmFill(d)")
        body = self.h[i:i + 1500]
        self.assertIn("esc(n)", body)
        self.assertNotIn("${n}</option>", body)


class 나머지는_그대로(unittest.TestCase):
    def test_config_의_모델은_손대지_않았다(self):
        c = json.load(open(os.path.join(APP, "config.json"), encoding="utf-8"))
        self.assertTrue((c.get("llm") or {}).get("model"),
                        "config 의 모델 이름을 마음대로 바꾸면 안 된다 — 화면에서 고를 일이다")

    def test_판정_계산은_안_건드린다(self):
        for f in ("fab_score.py", "sentinel.py", "accuracy.py"):
            self.assertNotIn("list_models", _read(f), f + " 는 무관해야 한다")


if __name__ == "__main__":
    unittest.main()
