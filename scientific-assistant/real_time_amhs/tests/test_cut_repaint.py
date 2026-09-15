# -*- coding: utf-8 -*-
"""등급 컷을 바꾸면 **화면 글자색이 따라오는가**.

고객 지적: "실시간 관제에서 정책을 바꿔도 경계·위험·초위험 색이 안 바뀐다."
원인이 두 군데였고 둘 다 '다시 계산할 이유가 없다' 고 판단하는 자리였다.

  · 서버 — /api/feed 의 캐시 키(_sig)에 등급 컷이 없었다. 정책 탭에서 컷을
    바꾸면 메모리 CFG 는 바로 바뀌는데 원본 CSV 는 그대로라 키가 같고,
    그래서 **옛 컷으로 계산한 응답**이 캐시에서 그대로 나갔다.
    컷은 level·counts·fab_cuts 를 전부 바꾼다.
  · 화면 — feedSig() 에 컷이 없어서 표를 다시 안 그렸다. 특히 FAB 칸 색은
    FCUTS 로 칠하는데, FAB 컷이 바뀌어도 행 등급(counts)은 안 바뀌니
    counts 로도 안 걸렸다. 추이 막대(ssig)도 같았다.

두 자리 다 '원본이 안 바뀌었으니 넘어간다' 가 맞는 최적화였고, 컷이라는
입력이 하나 더 있다는 것만 빠져 있었다.

세 번째가 더 컸다 — FAB 칸은 **예측기가 CSV 에 적어 둔 등급**(fab_lv)을
정책 컷보다 먼저 썼다. 그 값은 정책을 바꿔도 안 변하니, 캐시를 고쳐도
그 칸만 옛 색 그대로다. 고객 지시대로 **정책이 이긴다** — 예측기가 다르게
적어 뒀다는 사실은 버리지 않고 툴팁에 남긴다.
"""
import os
import re
import shutil
import subprocess
import unittest

from . import util  # noqa: F401

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(_BASE, *parts), encoding="utf-8") as fh:
        return fh.read()


class 서버_캐시_키(unittest.TestCase):
    def setUp(self):
        self.src = _read("server.py")
        m = re.search(r"_sig = \(_st\.st_mtime_ns.*?files_sig\([^\n]*\)\)",
                      self.src, re.S)
        self.assertIsNotNone(m, "/api/feed 의 캐시 키를 못 찾았다")
        self.key = m.group(0)

    def test_등급_컷이_캐시_키에_있다(self):
        self.assertIn('C["cfg"].get("grade")', self.key,
                      "컷이 키에 없으면 정책을 바꿔도 옛 응답이 그대로 나간다")

    def test_컷을_정렬해서_넣는다(self):
        # dict 순서가 달라졌다고 캐시가 깨지면 매 폴링이 재계산이다
        self.assertIn("sort_keys=True", self.key)

    def test_파일_서명도_그대로_남아_있다(self):
        # 컷을 넣느라 원래 있던 조건을 잃으면 다른 사고가 난다
        for need in ("_st.st_mtime_ns", "_st.st_size", 'C["sys"]',
                     "shown_day", "files_sig"):
            self.assertIn(need, self.key, need + " 가 키에서 빠졌다")


class 정책이_색을_정한다(unittest.TestCase):
    """예측기가 적어 둔 등급이 아니라 정책 컷이 색을 정하는가."""

    def setUp(self):
        self.html = _read("static", "dashboard.html")

    def test_FAB_칸_등급은_정책_컷에서_나온다(self):
        # 세 곳(표·HI_FAB·툴팁) 다 fabLv(값, FCUTS[f]) 로만 등급을 정한다
        got = re.findall(r"fabLv\([^)]*\)", self.html)
        self.assertGreaterEqual(len(got), 3, "색을 정하는 자리가 셋이다")
        for g in got:
            self.assertIn("FCUTS", g, g + " 가 정책 컷을 안 쓴다")

    def test_예측기_등급이_색을_덮지_않는다(self):
        # `(r.fab_lv && r.fab_lv[f]) || fabLv(...)` 이 되살아나면 안 된다
        self.assertNotIn("r.fab_lv && r.fab_lv", self.html,
                         "예측기 등급이 정책 컷보다 앞서면 정책을 바꿔도 "
                         "색이 안 바뀐다 — 이게 고객이 본 증상이다")

    def test_예측기_등급을_버리지는_않는다(self):
        # 색에서 뺐다고 정보를 없애면 안 된다 — 툴팁에 남긴다
        self.assertIn("예측기 표기", self.html,
                      "정책과 예측기가 갈렸다는 사실은 남아 있어야 한다")
        self.assertIn("r.fab_lv || {}", self.html)

    def test_경계부터_칠한다(self):
        # 고객 요청 — 위험 이상만 칠하던 것을 경계까지 넓혔다
        m = re.search(r"const fabTx\s*=.*", self.html)
        self.assertIsNotNone(m, "색 규칙이 한 군데 모여 있어야 한다")
        self.assertIn("'정상'", m.group(0),
                      "정상만 빼고 칠한다 — 경계도 등급색")

    def test_굵게는_위험_이상만(self):
        # 색과 굵기가 같이 올라가면 경계가 위험처럼 읽힌다
        m = re.search(r"const fabBold\s*=.*", self.html)
        self.assertIsNotNone(m)
        self.assertIn("위험", m.group(0))
        self.assertNotIn("경계", m.group(0))


class 화면_다시_그리기(unittest.TestCase):
    def setUp(self):
        self.html = _read("static", "dashboard.html")

    def test_cutSig_가_있다(self):
        self.assertIn("function cutSig()", self.html)
        m = re.search(r"function cutSig\(\)\{(.*?)\n\}", self.html, re.S)
        body = m.group(1)
        self.assertIn("CUTS", body, "시스템 컷")
        self.assertIn("FCUTS", body, "FAB 별 컷 — 이쪽이 counts 로 안 걸린다")

    def test_표_서명에_컷이_들어간다(self):
        m = re.search(r"function feedSig\(.*?\n\}", self.html, re.S)
        self.assertIsNotNone(m)
        self.assertIn("cutSig()", m.group(0),
                      "컷이 빠지면 정책을 바꿔도 표를 다시 안 그린다")

    def test_추이_서명에도_컷이_들어간다(self):
        m = re.search(r"const ssig = \[.*?\]\.join\('\|'\);", self.html, re.S)
        self.assertIsNotNone(m)
        self.assertIn("cutSig()", m.group(0),
                      "막대 등급색·리미트 점선도 컷을 따라가야 한다")

    def test_cutSig_는_쓰이기_전에_선언된다(self):
        # 호이스팅되는 function 선언이지만 CUTS·FCUTS 는 let 이라 TDZ 가 있다
        for name in ("let CUTS", "let FABS = [], FCUTS"):
            self.assertLess(self.html.index(name), self.html.index("function cutSig()"),
                            name + " 가 cutSig 보다 뒤에 있다")


class 진짜로_칠해_본다(unittest.TestCase):
    """소스 글자가 아니라 **결과 색**을 본다.

    dashboard.html 에서 색 함수만 떼어 node 위에서 돌린다 — 컷을 60→36 으로
    바꿨을 때 같은 43점이 정말 다른 색으로 나오는지. 위 시험들이 전부 통과해도
    여기서 걸리는 경우가 있다 (글자는 맞는데 순서가 틀린 식).
    """

    def test_컷을_바꾸면_색이_바뀐다(self):
        node = shutil.which("node") or "/opt/node22/bin/node"
        if not os.path.exists(node):
            self.skipTest("node 가 없다")
        r = subprocess.run([node, os.path.join(_BASE, "tests", "cut_color.js")],
                           capture_output=True, text=True, timeout=60, cwd=_BASE)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK", r.stdout)


if __name__ == "__main__":
    unittest.main()
