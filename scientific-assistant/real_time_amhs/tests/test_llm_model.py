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
        i = self.s.index("    model = str(b.get(\"model\") or \"\").strip()")
        body = self.s[i:i + 2000]
        self.assertIn('if b.get("test"):', body)
        self.assertIn("lc[\"model\"] = prev", body, "실패하면 옛 값으로 되돌려야 한다")
        self.assertIn('"applied": False', body)

    def test_저장은_config_json_에(self):
        self.assertIn("def _persist_llm_model(", self.s)
        i = self.s.index("def _persist_llm_model(")
        body = self.s[i:i + 1600]
        self.assertIn('lc["model"] = model', body)
        # ★임시 파일에 쓰고 바꿔치기 — 쓰다 죽어도 config.json 이 깨지지 않는다
        self.assertIn("os.replace(tmp, CONFIG_PATH)", body)

    def test_빈_이름은_막는다(self):
        i = self.s.index("    model = str(b.get(\"model\") or \"\").strip()")
        body = self.s[i:i + 2200]          # '(사용안함)' 갈래가 앞에 붙어 자리가 밀렸다
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


class 파이프라인_네_단계(unittest.TestCase):
    """고객: "4-LLM 파이프라인 분석 모델 저장 되게 해줘 · 다른 모델을 저장 할 수
    있고 모델 재로드를 하게 해서 선택해서 저장 할 수도 있잖아 · 일부 모델이
    없어지는 경우가 있어".

    단계마다 다른 모델을 쓴다(analysis.STAGES). 그중 하나가 게이트웨이에서
    없어지면 **그 단계만** 매번 실패하는데, 화면에서는 알 길이 없었다.
    """

    @classmethod
    def setUpClass(cls):
        cls.s = _read("server.py")
        cls.h = _read("static", "dashboard.html")

    def test_단계가_넷이다(self):
        import analysis
        self.assertEqual(list(analysis.STAGES), ["p1", "p2", "p3", "final"])

    def test_GET_이_단계별_모델을_같이_준다(self):
        i = self.s.index("def api_llm_model(")
        body = self.s[i:i + 3000]
        self.assertIn("for sid, st in analysis.STAGES.items():", body)
        self.assertIn('"model": m,', body)
        # ★안 쓰는 단계(enabled=false)는 따지지 않는다 — 없는 이름이어도 상관없다
        self.assertIn('"ok": None if not on else ((m in names) if names else None)', body,
                      "그 모델이 지금 있는지도 알려야 한다")
        self.assertIn('"enabled": on,', body, "그 단계를 쓰는지도 알려야 한다")
        self.assertIn('"roles": roles,', body)

    def test_POST_이_단계별로_저장한다(self):
        i = self.s.index("def api_llm_model(")
        body = self.s[i:i + 5000]
        self.assertIn('if b.get("roles") is not None:', body)
        self.assertIn("if sid not in analysis.STAGES:", body, "모르는 단계는 막는다")
        # 모델과 '사용 안 함' 을 **한 번에** 적는다 (따로 쓰면 뒤엣것이 앞엣것을 덮는다)
        self.assertIn("_persist_llm_model(roles=roles, roles_on=roles_on)", body)

    def test_네_단계를_각각_불러_본다(self):
        """★하나만 확인하면 나머지가 없어진 이름이어도 저장된다."""
        i = self.s.index('if b.get("roles") is not None:')
        body = self.s[i:i + 3000]
        self.assertIn("for sid, m in roles.items():", body)
        self.assertIn("_apply_roles(prev)", body, "하나라도 안 되면 전부 되돌린다")
        self.assertIn('"applied": False', body)

    def test_설명은_안_지운다(self):
        """roles 를 통째로 갈아끼우면 각 단계의 _doc 이 날아간다."""
        i = self.s.index("def _persist_llm_model(")
        body = self.s[i:i + 1600]
        self.assertIn('rr.setdefault(sid, {})["model"] = m', body)

    def test_한_번에_읽고_한_번에_쓴다(self):
        """model 과 roles 를 따로 쓰면 뒤에 쓴 쪽이 앞의 것을 덮는다."""
        i = self.s.index("def _persist_llm_model(")
        body = self.s[i:i + 1600]
        self.assertEqual(body.count("json.load(f)"), 1)
        self.assertEqual(body.count("os.replace(tmp, CONFIG_PATH)"), 1)

    def test_화면에_표가_있다(self):
        for i in ("lr-rows", "lr-save", "lr-note", "lr-msg"):
            self.assertIn('id="%s"' % i, self.h, i + " 가 없다")
        self.assertIn("4-LLM 파이프라인", self.h)

    def test_같은_목록을_같이_쓴다(self):
        """모델 목록을 두 번 받아 오면 '↻ 목록' 을 눌러도 한쪽만 새로 된다."""
        self.assertIn("lrFill(d);", self.h)
        i = self.h.index("async function loadLlmModel(force)")
        self.assertIn("lmFill(d);", self.h[i:i + 400])

    def test_없어진_모델을_빨갛게_알린다(self):
        # ★꺼 둔 단계는 빼고 본다 — 안 쓰는데 빨갛게 띄우면 사람이 원인을 찾으러 간다
        self.assertIn("const bad = !off && r.ok === false;", self.h)
        self.assertIn("목록에 없음 — 이 단계는 실패합니다", self.h)
        self.assertIn("개 단계가 목록에 없습니다", self.h)

    def test_지금_값이_목록에_없어도_골라_둔다(self):
        self.assertIn("if(r.model && !opts.includes(r.model)) opts.unshift(r.model);", self.h)

    def test_직접_입력도_된다(self):
        self.assertIn("data-lrtxt=", self.h)
        i = self.h.index("function lrPicked()")
        self.assertIn("sel.value === LM_CUSTOM", self.h[i:i + 500])

    def test_시험_후_저장을_보낸다(self):
        self.assertIn("post('/api/llm/model', {roles, save: true, test: true})", self.h)

    def test_이름을_그대로_넣지_않는다(self):
        i = self.h.index("function lrFill(d)")
        body = self.h[i:i + 2200]
        self.assertIn("esc(n)", body)
        self.assertIn("esc(r.name || r.id)", body)




if __name__ == "__main__":
    unittest.main()
