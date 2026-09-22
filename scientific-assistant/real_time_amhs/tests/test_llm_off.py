# -*- coding: utf-8 -*-
"""LLM 판단 모델 '사용 안 함' — 정책 탭에서 끌 수 있나.

고객: "정책에서 llm판단 모델 사용안함 이라고 선택할수 있게해줘.
      1차,2차,3차,최종도 마찬가지야".

끄는 길이 둘이다.
  · 판단 모델 자체   llm.enabled=false   — 분당 판단·리포트·4단계가 한꺼번에 멎는다
                                          (llm_client.chat 이 원래 보던 스위치다)
  · 단계 하나만      llm.analysis.roles.{id}.enabled=false
끈 단계는 **그 단계의 대체 경로**(_fill_p1·_fill_p2·_fill_p3·_fallback_final)로
간다 — 원래 실패했을 때 쓰라고 있던 길이라 새로 만든 것이 없다.

★flask 없이 돌아야 한다 (폐쇄망·이 시험 환경 둘 다). analysis 는 그냥 import 하고,
  server.py·dashboard.html 은 글로 읽어 확인한다.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)


def _read(*p):
    with open(os.path.join(APP, *p), encoding="utf-8") as fh:
        return fh.read()


class 단계_켜짐_끄기(unittest.TestCase):
    def setUp(self):
        import analysis
        self.a = analysis

    def test_기본은_다_켜짐(self):
        for sid in ("p1", "p2", "p3", "final"):
            self.assertTrue(self.a._stage_on({}, sid), sid)

    def test_단계_하나만_끈다(self):
        cfg = {"llm": {"analysis": {"roles": {"p2": {"enabled": False}}}}}
        self.assertFalse(self.a._stage_on(cfg, "p2"))
        for sid in ("p1", "p3", "final"):
            self.assertTrue(self.a._stage_on(cfg, sid), sid + " 까지 꺼졌다")

    def test_전체를_끄면_네_단계_다_꺼진다(self):
        """★llm.enabled 는 전체 스위치다 — 단계별 설정보다 위다."""
        cfg = {"llm": {"enabled": False,
                       "analysis": {"roles": {"p1": {"enabled": True}}}}}
        for sid in ("p1", "p2", "p3", "final"):
            self.assertFalse(self.a._stage_on(cfg, sid), sid)

    def test_끈다고_모델_이름을_지우지_않는다(self):
        """★다시 켤 때 쓰던 것이 그대로 돌아와야 한다."""
        cfg = {"llm": {"analysis": {"roles": {"p2": {"enabled": False,
                                                    "model": "쓰던-모델"}}}}}
        self.assertEqual(self.a._stage_model(cfg, "p2"), "쓰던-모델")

    def test_사용안함_이름이_한_곳에만_있다(self):
        """★서버와 화면이 같은 말을 써야 한다 — 화면은 off_value 로 받아 간다."""
        self.assertEqual(self.a.OFF, "(사용안함)")
        self.assertIn('"off_value": analysis.OFF', _read("server.py"))


class 끈_단계는_대체_경로로(unittest.TestCase):
    """★건너뛰기만 하고 결과가 안 나오면 분석이 통째로 빈다. 원래 있던
    대체 경로로 이어져야 한다."""

    @classmethod
    def setUpClass(cls):
        cls.s = _read("analysis.py")

    def test_네_단계_모두_끌_수_있다(self):
        for v in ("p1_on = _stage_on(cfg, \"p1\")", "p2_on = _stage_on(cfg, \"p2\")",
                  "p3_on = _stage_on(cfg, \"p3\")", "fin_on = _stage_on(cfg, \"final\")"):
            self.assertIn(v, self.s, v)

    def test_끄면_모델을_아예_안_부른다(self):
        """★끄고도 호출하면 끈 뜻이 없다 (요금도 그대로 나간다)."""
        for call, on in (("_stage1(chunks, cfg, prog, cancel)", "p1_on"),
                         ("_stage2(overview, obs, cfg, cancel)", "p2_on"),
                         ("_stage3(overview, obs, p2, chunks, cfg, cancel)", "p3_on"),
                         ("_stage_final(overview, obs, p2, p3, cfg, cancel)", "fin_on")):
            i = self.s.index(call)
            앞 = self.s[max(0, i - 200):i]
            self.assertIn("if " + on + ":", 앞, call + " 가 조건 없이 불린다")

    def test_대체_경로가_그대로_이어진다(self):
        for f in ("_fill_p1(chunks, seq, cfg)", "_fill_p2(meta, obs, cfg)",
                  "_fill_p3(meta, cfg)", "_fallback_final(meta, obs, p2, p3)"):
            self.assertIn(f, self.s, f)

    def test_끈_단계는_실패가_아니다(self):
        """★'실패' 로 적으면 화면이 빨갛게 뜨고 사람이 원인을 찾으러 간다."""
        for sid in ("p1", "p2", "p3", "final"):
            m = re.search(r'prog\["roles"\]\["%s"\]\.update\(status=\("사용안함"' % sid, self.s)
            self.assertTrue(m, sid + " 를 끄면 뭐라고 적는지가 없다")
        self.assertIn('_fin_ok = bool(body) and (not fin_on or "실패" not in str(ef or ""))', self.s)

    def test_끈_단계의_모델_이름은_사용안함(self):
        for v in ('(OFF if not p1_on else', '(OFF if not p2_on else',
                  '(OFF if not p3_on else', '(OFF if not fin_on else'):
            self.assertIn(v, self.s, v)


class 서버가_받아_준다(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = _read("server.py")

    def test_판단_모델을_끄면_llm_enabled_false(self):
        self.assertIn('if model == __import__("analysis").OFF:', self.s)
        self.assertIn('lc["enabled"] = False', self.s)
        self.assertIn("serr = _persist_llm_model(enabled=False)", self.s)

    def test_이름을_다시_고르면_켜진다(self):
        """★끄고 나서 모델을 고르면 다시 켜져야 한다 — 안 그러면 영영 꺼진 채다."""
        self.assertIn("# 이름을 골랐다 = 다시 켠다\n    lc[\"enabled\"] = True", self.s)
        self.assertIn("_persist_llm_model(model=model, enabled=True)", self.s)

    def test_단계를_끄면_roles_on_에_false(self):
        self.assertIn("if m == analysis.OFF:\n                roles_on[sid] = False", self.s)
        self.assertIn("_apply_roles_on(roles_on)", self.s)
        self.assertIn("_persist_llm_model(roles=roles, roles_on=roles_on)", self.s)

    def test_끈_단계는_불러_보지_않는다(self):
        """★test:true 일 때 끈 단계까지 호출하면 끈 뜻이 없다.
           roles 에는 **켠 것만** 담기므로, 그걸 도는 시험 고리는 끈 단계를 지나친다."""
        i = self.s.index("roles_on[sid] = False")          # 끈 단계는 여기서 continue
        j = self.s.index("roles[sid] = m", i)              # 켠 단계만 roles 에
        k = self.s.index('if b.get("test"):', j)           # 그 뒤에 시험 고리
        고리 = self.s[k:k + 700]
        self.assertTrue("for sid, m in roles.items():" in 고리,
                        "시험 고리가 roles(켠 것)를 돌지 않는다")
        self.assertTrue("continue" in self.s[i:i + 120], "끈 단계를 건너뛰지 않는다")

    def test_config_에_남는다(self):
        self.assertIn('lc["enabled"] = bool(enabled)', self.s)
        self.assertIn('rr.setdefault(sid, {})["enabled"] = bool(on)', self.s)

    def test_GET_이_단계별_켜짐을_알려_준다(self):
        self.assertIn('"enabled": on,', self.s)
        self.assertIn('"ok": None if not on else', self.s)


class 화면에서_고를_수_있다(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = _read("static", "dashboard.html")

    def test_판단_모델_칸에_사용_안_함(self):
        self.assertIn("⛔ 사용 안 함 (LLM 판단 끔)", self.h)

    def test_네_단계_칸에도(self):
        self.assertIn("⛔ 사용 안 함 (이 단계만)", self.h)

    def test_값은_서버에서_받아_쓴다(self):
        """★한쪽에만 적어 두면 언젠가 어긋난다."""
        self.assertIn("LM_OFF = d.off_value || '(사용안함)';", self.h)

    def test_꺼_두면_그렇게_말한다(self):
        self.assertIn("LLM 판단을 쓰지 않습니다.", self.h)
        self.assertIn("이 단계는 LLM 없이 통계로 채웁니다", self.h)

    def test_꺼_둔_것을_사고로_안_본다(self):
        """★안 쓰는데 '목록에 없다' 고 빨갛게 띄우면 사람이 원인을 찾으러 간다."""
        self.assertIn("const bad = !off && r.ok === false;", self.h)
        self.assertIn("r.enabled !== false && r.ok === false", self.h)


if __name__ == "__main__":
    unittest.main()
