"""허브룸 도메인 스킬 — 정작 우리 일이 라우팅에서 빠져 있었다.

    'M16 허브룸 반송 정체'  → []            (아무것도 안 나옴)
    '반송 정체 분석'        → gtars, cmd-cr  (엉뚱한 것)

원인
    도메인 문서 넷은 이미 스킬 형식(YAML 앞머리)으로 쓰여 있었는데
    m16_hub_skills/ 에 평범한 .md 로 놓여 있었다. 데모스는 스킬을
    scientific-skills/<id>/SKILL.md 에서만 찾는다(routes_api 의
    _skill_exists) — 그래서 등록 자체가 안 됐다.

    tools/sync_m16_skills.py 가 그 자리로 옮겨 심는다. 사본이 생기므로
    한쪽만 고치면 어긋난다. 이 파일이 그걸 잡는다.
"""
from __future__ import annotations

import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (_ROOT, os.path.join(_ROOT, "harness-mvp")):
    if p not in sys.path:
        sys.path.insert(0, p)

SKILLS_DIR = os.path.join(_ROOT, "scientific-skills")
SRC_DIR = os.path.join(_ROOT, "m16_hub_skills")

# 질의 → 나와야 하는 스킬 후보
DOMAIN_CASES = [
    ("M16 허브룸 반송 정체", ("m16-hub-overview", "m16-hub-interpret")),
    ("반송 정체 분석", ("m16-hub-overview", "m16-hub-interpret")),
    ("임계값 조정하고 싶어", ("m16-hub-thresholds",)),
    ("발동이벤트 결과 해석", ("m16-hub-interpret",)),
    ("hubroom_predictor 백테스트 돌리는 법", ("m16-hub-usage",)),
    ("초위험 등급이 뭐야", ("m16-hub-interpret", "m16-hub-overview")),
    ("8영역 9룰 구조 설명", ("m16-hub-overview",)),
]


@unittest.skipUnless(os.path.isdir(SRC_DIR), "m16_hub_skills 없음")
class M16SkillSync(unittest.TestCase):
    def test_원본과_어긋나지_않는다(self):
        """문서를 고쳐 놓고 sync 를 안 돌리면 스킬은 옛날 내용을 준다."""
        sys.path.insert(0, os.path.join(_ROOT, "tools"))
        import sync_m16_skills as sync
        res = sync.sync(write=False)
        stale = [n for n, same in res if not same]
        self.assertEqual(
            stale, [],
            f"원본과 어긋난 스킬: {stale} — python tools/sync_m16_skills.py 를 돌려라")

    def test_데모스가_찾는_자리에_있다(self):
        """routes_api 는 scientific-skills/<id>/SKILL.md 만 본다."""
        sys.path.insert(0, os.path.join(_ROOT, "tools"))
        import sync_m16_skills as sync
        for skill_id in sync.MAP.values():
            path = os.path.join(SKILLS_DIR, skill_id, "SKILL.md")
            self.assertTrue(os.path.isfile(path), f"없다: {path}")

    def test_앞머리에_설명이_있다(self):
        """description 이 없으면 라우팅이 이름만 보고 한다."""
        import harness_bridge as hb
        sys.path.insert(0, os.path.join(_ROOT, "tools"))
        import sync_m16_skills as sync
        for skill_id in sync.MAP.values():
            front = hb._read_frontmatter(
                os.path.join(SKILLS_DIR, skill_id, "SKILL.md"))
            self.assertTrue(front.get("description"), f"{skill_id}: 설명 없음")


@unittest.skipUnless(os.path.isdir(SKILLS_DIR), "scientific-skills 없음")
class M16Routing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from demos_v1.skills import SKILL_KEYWORDS
            import harness_bridge as hb
            hb.init_harness(skills_dir=SKILLS_DIR, skill_keywords=SKILL_KEYWORDS)
            cls.route = staticmethod(hb.harness_route)
        except Exception as e:
            raise unittest.SkipTest(f"하네스 초기화 불가: {e}")

    def test_도메인_질의가_도메인_스킬로_간다(self):
        bad = []
        for q, want in DOMAIN_CASES:
            got = [m["name"] for m in self.route(q, limit=2)]
            if not got or got[0] not in want:
                bad.append(f"{q} → {got} (기대 {want})")
        self.assertEqual(bad, [], "\n  " + "\n  ".join(bad))

    def test_도메인_스킬이_남의_자리를_뺏지_않는다(self):
        """'정체'·'등급' 같은 말이 흔해서, 상관없는 질의까지 끌어오면 안 된다."""
        for q in ("엑셀 피벗테이블", "단일세포 분석", "논문 검색"):
            got = [m["name"] for m in self.route(q, limit=3)]
            self.assertFalse(
                any(n.startswith("m16-hub") for n in got),
                f"{q} → {got} 에 허브룸 스킬이 끼어들었다")


if __name__ == "__main__":
    unittest.main()
