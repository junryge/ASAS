# -*- coding: utf-8 -*-
"""집에서 로컬 GGUF 로 붙는 길.

집은 GPU 한 장이다. 앱마다 llama-cpp 로 모델을 올리면 같은 모델이 VRAM 에
두 벌 세 벌 올라가서 결국 아무것도 안 뜬다. 그래서 **모델은 한 곳만 올린다** —
demos_v1(app.py)이 부팅할 때 올려 두고, 그걸 OpenAI 호환으로 내보낸다
(demos_v1/routes_openai.py). 아바타는 원래 OpenAI 호환 게이트웨이만 말할 줄
아니까 주소만 그쪽으로 돌리면 코드를 안 고치고 그대로 붙는다.

여기서 지키는 것
  · 토큰이 없어도 뜬다 (로컬 GGUF 는 토큰이 없다)
  · 토큰이 없으면 Authorization 을 **아예 안 보낸다** (빈 Bearer 는 401 이 난다)
  · 사내 주소에서는 토큰을 여전히 요구한다
"""
import os
import re
import unittest

from . import util

RUN = os.path.join(util.BASE, "avatar_2d", "run.py")
LLM = os.path.join(util.BASE, "avatar_2d", "avatar", "llm.py")
CFG = os.path.join(util.BASE, "avatar_2d", "avatar", "config.py")


def _read(p):
    if not os.path.isfile(p):
        raise unittest.SkipTest("{} 가 없다".format(p))
    with open(p, encoding="utf-8") as f:
        return f.read()


class 로컬_GGUF_로_붙는다(unittest.TestCase):

    def setUp(self):
        self.run = _read(RUN)
        self.llm = _read(LLM)
        self.cfg = _read(CFG)

    def test_gguf_옵션이_있다(self):
        self.assertIn('"--gguf"', self.run)
        self.assertIn("GGUF_LOCAL", self.cfg)

    def test_기본_주소가_app_py_다(self):
        """★demos_v1(app.py)은 10009 에 뜬다. 여기가 모델을 들고 있는 쪽이다."""
        m = re.search(r'GGUF_LOCAL\s*=\s*"([^"]+)"', self.cfg)
        self.assertIsNotNone(m)
        self.assertIn("10009", m.group(1))
        self.assertIn("127.0.0.1", m.group(1))

    def test_고르는_목록_맨_앞에_있다(self):
        """★집에서 제일 자주 고르는 것이 맨 앞이어야 한다."""
        i = self.cfg.index("ENDPOINTS = [")
        first = self.cfg[i:i + 200].splitlines()[1]
        self.assertIn("GGUF_LOCAL", first)

    def test_토큰이_없어도_뜬다(self):
        """★예전엔 토큰이 없으면 sys.exit(1) 이었다. 집에서는 아예 못 띄운다."""
        i = self.run.index("token, src = read_token(")
        blk = self.run[i:i + 900]
        self.assertIn("if not token and not local:", blk,
                      "토큰이 없으면 무조건 죽는다")
        self.assertIn("_is_local(", blk)

    def test_사내_주소는_토큰을_그대로_요구한다(self):
        """★로컬만 봐 준다. 사내 게이트웨이는 토큰 없이 붙어 봐야 401 이다 —
        거기서 통과시키면 원인을 늦게 안다."""
        i = self.run.index("def _is_local(")
        blk = self.run[i:i + 600]
        for h in ("127.0.0.1", "localhost"):
            self.assertIn(h, blk)
        self.assertNotIn("skhynix", blk)

    def test_빈_토큰이면_헤더를_안_보낸다(self):
        """★빈 Bearer 를 보내면 서버에 따라 401 로 잘라 버린다 —
        붙을 수 있는 것을 못 붙는다. 아예 안 보낸다."""
        for src, where in ((self.llm, "llm.py Gateway"), (self.run, "run.py fetch_models")):
            self.assertIn("if self.token:", src) if where.startswith("llm") \
                else self.assertIn("if token:", src)
            self.assertNotIn('"Authorization": "Bearer " + self.token', src, where)
        self.assertNotIn('headers={"Authorization": "Bearer " + token,', self.run)

    def test_gguf_는_upstream_보다_약하다(self):
        """★둘 다 주면 사람이 주소를 직접 적은 쪽이 이긴다 — 더 구체적인 뜻이다."""
        i = self.run.index("gguf_mode = ")
        self.assertIn("not args.upstream", self.run[i:i + 120])


class 관제_없이도_돈다(unittest.TestCase):
    """집에는 관제(real_time_amhs)가 없다.

    ★끄지 않으면 10초마다 두드리면서 화면에 "관제 연결 끊김 —
      real_time_amhs 폴더에서 python server.py 를 띄우세요" 가 영영 떠 있는다.
      집에서는 띄울 게 없는데 고치라고 하는 셈이다.
    """

    def setUp(self):
        self.run = _read(RUN)
        self.sen = _read(os.path.join(util.BASE, "avatar_2d", "avatar",
                                      "sentinel.py"))

    def test_끄는_길이_있다(self):
        i = self.run.index('ap.add_argument("--sentinel"')
        self.assertIn("off", self.run[i:i + 300])

    def test_끄면_상시감시도_멈춘다(self):
        """★주소만 off 로 두고 감시를 켜 두면 10초마다 헛되이 두드린다."""
        i = self.run.index("if args.sentinel:")
        blk = self.run[i:i + 700]
        self.assertIn('_cfg.SENTINEL["watch_sec"] = 0', blk)
        self.assertIn('_cfg.SENTINEL["url"] = "off"', blk)

    def test_끊긴_것과_안_보는_것을_구분한다(self):
        """★같은 글로 말하면, 집에서는 고칠 수 없는 것을 고치라고 하게 된다."""
        self.assertIn("def sentinel_off(", self.sen)
        i = self.sen.index("def watch()")
        blk = self.sen[i:i + 900]
        self.assertIn("if sentinel_off():", blk)
        self.assertIn('"why": "off"', blk)
        self.assertNotIn("server.py 를 띄우세요", blk)

    def test_그_판정을_한_곳에서_한다(self):
        """★off 인지를 여러 곳에서 각자 재면 한쪽만 고쳐서 어긋난다."""
        self.assertEqual(self.sen.count('in ("off", "none", "no", "0")'), 1)


class 서버쪽_문이_있다(unittest.TestCase):
    """demos_v1 쪽(집 PC)에 OpenAI 호환 문이 있어야 아바타가 붙는다.

    ★이 저장소에 demos_v1 이 같이 있을 때만 본다 (회사 배포본에는 없다).
    """

    def setUp(self):
        self.p = os.path.join(os.path.dirname(util.BASE), "demos_v1",
                              "routes_openai.py")
        if not os.path.isfile(self.p):
            raise unittest.SkipTest("demos_v1 이 없다 (회사 배포본)")
        with open(self.p, encoding="utf-8") as f:
            self.src = f.read()

    def test_두_길이_다_있다(self):
        self.assertIn('"/v1/models"', self.src)
        self.assertIn('"/v1/chat/completions"', self.src)

    def test_한_번에_하나만_생성한다(self):
        """★llama.cpp 모델 객체는 스레드 안전하지 않다. 두 요청이 겹치면
        토큰이 섞이거나 프로세스가 죽는다."""
        self.assertIn("_GEN_LOCK", self.src)
        i = self.src.index("def gen():")
        self.assertIn("with _GEN_LOCK:", self.src[i:i + 300],
                      "스트리밍은 제너레이터 **안에서** 락을 잡아야 한다")

    def test_response_format_을_한_계단씩_낮춘다(self):
        """★아바타는 json_schema 로 보낸다. llama-cpp 빌드마다 아는 모양이
        달라서, 바로 버리면 JSON 보장이 통째로 날아간다."""
        self.assertIn("def _rf_ladder(", self.src)
        i = self.src.index("def _rf_ladder(")
        blk = self.src[i:i + 900]
        self.assertIn("json_schema", blk)
        self.assertIn('"type": "json_object", "schema"', blk)

    def test_모델_이름을_세_가지로_받는다(self):
        """★부르는 쪽마다 아는 이름이 다르다 — env_id · 모델명 · 파일명."""
        i = self.src.index("def _resolve(")
        blk = self.src[i:i + 1200]
        self.assertIn("os.path.basename", blk)
        self.assertIn(".gguf", blk)


if __name__ == "__main__":
    unittest.main()
