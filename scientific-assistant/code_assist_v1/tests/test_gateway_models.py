"""API 모델은 게이트웨이 /v1/models 가 주는 것만 쓴다 (demos_v1/models.py).

예전엔 api_config.json 의 "models" 에 모델을 하나씩 등록했다. 게이트웨이 모델이 바뀌면 손으로
고쳐야 했고, 없어진 모델이 목록에 남아 고르면 실패했다. 이제 데모스가 켜질 때(그리고 목록을
달라는 요청이 5분 뒤에 오면) 게이트웨이에서 읽은 것만 등록한다. 데모스 본창 · 개인 에이전트 창 ·
코딩 어시스턴트 · UIO 가 모두 이 목록을 쓴다. GGUF(로컬) 는 그대로다.

여기서 지키는 것
  · 게이트웨이 목록 → 등록: 순서 · 크기(대/중/소) · 이미지 모델 · 대화용 아닌 모델 빼기
  · 다시 읽을 때 같은 dict 를 고친다(다른 모듈이 들고 있다) · gguf-N 은 그대로 · API 가 앞
  · 게이트웨이에 못 닿으면 마지막 목록을 그대로 쓴다
  · 자동 선택(pick_env) — 큰 · 빠른 · 이미지 모델, 없으면 가까운 것
  · 코딩 어시스턴트가 같은 목록 객체를 쓴다
  · api_config.json 에 예전 등록이 남아 있지 않다
"""
from __future__ import annotations

import json
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.environ.setdefault("LLM_GATEWAY_OFF", "1")        # 시험에서 진짜 게이트웨이를 부르지 않는다

import demos_v1.models as M  # noqa: E402

GATEWAY = [  # 게이트웨이가 돌려주는 모양 (vLLM /v1/models)
    {"id": "gaia-Qwen3.5-397B-A17B", "object": "model", "max_model_len": 131072},
    {"id": "Qwen3.6-35B-A3B", "object": "model"},
    {"id": "gemma-4-31B-it", "object": "model"},
    {"id": "gpt-oss-20b", "object": "model"},
    {"id": "Qwen2.5-VL-72B-Instruct", "object": "model"},
    {"id": "GLM-5.1", "object": "model"},
    {"id": "bge-m3", "object": "model"},
    {"id": "bge-reranker-v2-m3", "object": "model"},
]


class _State(unittest.TestCase):
    """시험 동안 목록을 바꾸고, 끝나면 되돌린다."""

    def setUp(self):
        self._saved = (dict(M.MODEL_REGISTRY), dict(M.ENV_CONFIG), dict(M.GATEWAY_STATUS), M._fetch)
        self._fake = GATEWAY
        M._fetch = lambda: self._fake
        M.GATEWAY_STATUS.update(count=0, error="", fetched_at=0.0, tried_at=0.0)

    def tearDown(self):
        reg, env, st, fetch = self._saved
        M._fetch = fetch
        M.MODEL_REGISTRY.clear()
        M.MODEL_REGISTRY.update(reg)
        M.ENV_CONFIG.clear()
        M.ENV_CONFIG.update(env)
        M.GATEWAY_STATUS.clear()
        M.GATEWAY_STATUS.update(st)


class 목록_만들기(unittest.TestCase):
    def test_게이트웨이_순서대로_대화용만(self):
        reg, skipped = M.build_registry(GATEWAY, base="http://gw")
        self.assertEqual([v["model"] for v in reg.values()],
                         ["gaia-Qwen3.5-397B-A17B", "Qwen3.6-35B-A3B", "gemma-4-31B-it", "gpt-oss-20b",
                          "Qwen2.5-VL-72B-Instruct", "GLM-5.1"])
        self.assertEqual(skipped, ["bge-m3", "bge-reranker-v2-m3"])          # 임베딩 · 재정렬은 뺀다
        for v in reg.values():
            self.assertEqual(v["url"], "http://gw/v1/chat/completions")

    def test_크기와_이미지(self):
        reg, _ = M.build_registry(GATEWAY, base="http://gw")
        by = {v["model"]: v for v in reg.values()}
        self.assertEqual(by["gaia-Qwen3.5-397B-A17B"]["tier"], "large")      # A17B(활성)가 아니라 397B
        self.assertEqual(by["Qwen3.6-35B-A3B"]["tier"], "large")
        self.assertEqual(by["gemma-4-31B-it"]["tier"], "medium")
        self.assertEqual(by["gpt-oss-20b"]["tier"], "small")
        self.assertEqual(by["GLM-5.1"]["tier"], "medium")                    # 크기를 모르면 중간
        self.assertIn("vision", by["Qwen2.5-VL-72B-Instruct"]["capabilities"])
        self.assertNotIn("vision", by["gpt-oss-20b"]["capabilities"])
        self.assertEqual(by["gaia-Qwen3.5-397B-A17B"]["context_window"], 131072)   # max_model_len
        self.assertEqual(by["gemma-4-31B-it"]["context_window"], 128000)

    def test_글자만_오는_목록과_이름_겹침(self):
        reg, _ = M.build_registry(["a-1", "A.1", "a-1"], base="http://gw")      # 같은 slug · 같은 id
        self.assertEqual(sorted(reg), ["a-1", "a-1-2"])

    def test_env_id_는_로컬_머리글자와_안_겹친다(self):
        reg, _ = M.build_registry(["gguf-model-7b"], base="http://gw")
        self.assertFalse(next(iter(reg)).startswith("gguf-"))


class 다시_읽기(_State):
    def test_같은_객체를_고치고_gguf_는_그대로(self):
        env_obj, reg_obj = M.ENV_CONFIG, M.MODEL_REGISTRY
        M.ENV_CONFIG.clear()
        M.ENV_CONFIG["gguf-0"] = {"url": "", "model": "local.gguf", "name": "로컬"}
        st = M.refresh_models(force=True)
        self.assertEqual(st["count"], 6)
        self.assertIs(M.ENV_CONFIG, env_obj)
        self.assertIs(M.MODEL_REGISTRY, reg_obj)
        keys = list(M.ENV_CONFIG)
        self.assertEqual(keys[-1], "gguf-0")                                  # API 가 앞, 로컬은 그대로
        self.assertEqual(len(keys), 7)

    def test_못_닿으면_마지막_목록(self):
        M.refresh_models(force=True)
        before = dict(M.MODEL_REGISTRY)

        def down():
            raise ConnectionError("gateway down")
        M._fetch = down
        st = M.refresh_models(force=True)
        self.assertIn("gateway down", st["error"])
        self.assertEqual(M.MODEL_REGISTRY, before)

    def test_5분_안에는_다시_안_읽는다(self):
        calls = []
        M._fetch = lambda: calls.append(1) or GATEWAY
        M.refresh_models(force=True)
        M.refresh_models()
        M.refresh_models()
        self.assertEqual(len(calls), 1)

    def test_목록이_있으면_화면은_기다리지_않는다(self):
        import time
        M.refresh_models(force=True)
        M.GATEWAY_STATUS["fetched_at"] -= M.GATEWAY_REFRESH_S + 1          # 5분이 지났다
        self._fake = [{"id": "gpt-oss-20b"}]
        t0 = time.time()
        M.refresh_models(wait=False)                                        # 지금 목록으로 바로 답
        self.assertLess(time.time() - t0, 0.5)
        for _ in range(100):                                                # 뒤에서 새로 읽는다
            if M.GATEWAY_STATUS["count"] == 1 and not M._BG["on"]:
                break
            time.sleep(0.02)
        self.assertEqual(list(M.ENV_CONFIG), ["gpt-oss-20b"])

    def test_게이트웨이에서_빠진_모델은_목록에서도_빠진다(self):
        M.refresh_models(force=True)
        self._fake = [g for g in GATEWAY if g["id"] != "gemma-4-31B-it"]
        M.refresh_models(force=True)
        self.assertNotIn("gemma-4-31b-it", M.ENV_CONFIG)
        self.assertEqual(M.GATEWAY_STATUS["count"], 5)


class 자동_선택(_State):
    def test_종류별로_고른다(self):
        M.refresh_models(force=True)
        self.assertEqual(M.pick_env("large"), "gaia-qwen3-5-397b-a17b")
        self.assertEqual(M.pick_env("small"), "gpt-oss-20b")
        self.assertEqual(M.pick_env("vision"), "qwen2-5-vl-72b-instruct")
        self.assertEqual(M.pick_env("default"), "gaia-qwen3-5-397b-a17b")    # 글 모델 중 게이트웨이 첫째

    def test_없으면_가까운_것(self):
        self._fake = [{"id": "gemma-4-31B-it"}]
        M.refresh_models(force=True)
        for kind in ("large", "small", "vision", "default"):
            self.assertEqual(M.pick_env(kind), "gemma-4-31b-it")
        self._fake = []
        M.refresh_models(force=True)
        self.assertEqual(M.pick_env("default"), "")

    def test_라우터가_목록에서_고른다(self):
        M.refresh_models(force=True)
        import demos_v1.router as R
        keep = R.API_TOKEN
        R.API_TOKEN = "x"
        try:
            env, why = R.classify_and_route("안녕", [], [])
            self.assertEqual(env, "gpt-oss-20b")
            self.assertIn("gpt-oss-20b", why)
            env, _ = R.classify_and_route("이 사진 뭐야", [], [{"type": "image"}])
            self.assertEqual(env, "qwen2-5-vl-72b-instruct")
        finally:
            R.API_TOKEN = keep


class 설정_파일(unittest.TestCase):
    def test_예전_등록이_남아_있지_않다(self):
        with open(os.path.join(_ROOT, "api_config.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        for k in ("models", "api_model_tiers", "fallback_chains", "default_model_priority"):
            self.assertNotIn(k, cfg)
        self.assertTrue(cfg["llm_gateway"]["base_url"].startswith("http"))

    def test_코딩_어시스턴트는_같은_목록(self):
        import code_assist_v1.models as CM
        self.assertIs(CM.MODEL_REGISTRY, M.MODEL_REGISTRY)
        self.assertIs(CM.ENV_CONFIG, M.ENV_CONFIG)
        self.assertIs(CM.DEFAULT_MODEL_PRIORITY, M.DEFAULT_MODEL_PRIORITY)


if __name__ == "__main__":
    unittest.main()
