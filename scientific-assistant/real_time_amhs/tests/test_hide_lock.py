#!/usr/bin/env python3
"""숨김 모드 — 2026-09-22 고객 요청.

  "실시간 관제, 과거 데이터 조회 ALL 숨기자 … 오프닝 화면에서도 ALL 화면 숨겨
   각 FAB 만 보이면 되"
  "실시간관제, 과거데이터 이력조회, 정책, UI대쉬보드 외 나머지 숨김처리 —
   LLM 모델 분석, 리포트 피드백 숨김처리"
  "숨김처리 활성화 버튼 비밀번호 … 지금 숨김처리하되 숨김처리 활성화·비활성화
   버튼 만들어줘 … ALL 쪽도 활성·비활성화 들어가겠지"

브라우저를 띄우지 않고 글자로 본다(test_dashboard_open 과 같은 방식).
해시 함수만 node 로 실제로 돌려 파이썬 hashlib 과 맞춰 본다 (node 없으면 건너뜀).
★비밀번호 글자는 이 파일에도 두지 않는다 — 저장소에 비밀이 생긴다(test_secrets).
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import unittest

from . import util


def _html():
    with open(os.path.join(util.BASE, "static", "dashboard.html"), encoding="utf-8") as f:
        return f.read()


def _fn(js, name):
    """function name(…){ … } 한 덩어리 — 줄 맨 앞의 '}' 까지."""
    i = js.index(f"function {name}(")
    j = js.index("\n}", i)
    return js[i:j + 2]


class 가리는_것(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = _html()

    def test_숨기는_탭은_셋(self):
        m = re.search(r"const HIDE_TABS = \[([^\]]*)\];", self.h)
        self.assertTrue(m)
        tabs = re.findall(r"'([a-z]+)'", m.group(1))
        self.assertEqual(tabs, ["ml", "analysis", "report"])

    def test_남는_탭은_넷(self):
        """실시간 관제 · 과거 데이터 조회 · 정책 · UI대쉬보드."""
        box = self.h[self.h.index('<div class="tabs">'):]
        box = box[:box.index("</div>")]
        tabs = dict(re.findall(r'data-tab="([a-z]+)"[^>]*>([^<]+)<', box))
        hide = {"ml", "analysis", "report"}
        self.assertEqual({t for t in tabs if t not in hide},
                         {"live", "past", "policy", "ui"})
        self.assertEqual(tabs["analysis"], "LLM 모델 분석")
        self.assertEqual(tabs["report"], "리포트·피드백")

    def test_기본은_켜짐(self):
        """저장값이 없거나 저장소가 막혀 있으면 가린다 — 풀린 채로 시작하지 않는다."""
        self.assertIn("let HIDE_ON = true;", self.h)
        self.assertIn("HIDE_ON = sessionStorage.getItem(HIDE_KEY) !== 'off';", self.h)
        self.assertIn("catch(e){ HIDE_ON = true; }", self.h)

    def test_풀린_상태는_이_창에만(self):
        """관제실 PC 에 풀린 채로 남지 않게 — localStorage 가 아니라 sessionStorage."""
        body = _fn(self.h, "hideSet")
        self.assertIn("sessionStorage.setItem(HIDE_KEY", body)
        self.assertNotIn("localStorage", body)

    def test_탭은_클래스로_가린다(self):
        """ML 탭은 syncMlTab 이 style.display 를 만진다 — 인라인과 안 싸우게."""
        body = _fn(self.h, "hideApply")
        self.assertIn("b.classList.toggle('hidden', HIDE_ON)", body)
        self.assertIn(".hidden{display:none!important}", self.h)

    def test_보던_탭을_가리면_실시간_관제로(self):
        body = _fn(self.h, "hideApply")
        self.assertIn("b.classList.contains('on')", body)
        self.assertIn('data-tab="live"', body)


class ALL_도_같은_단추로(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = _html()

    def test_고를_수_있는_목록(self):
        self.assertIn("function sysShown(){ return HIDE_ON ? "
                      "SYSTEMS.filter(s => s.code !== 'ALL') : SYSTEMS; }", self.h)

    def test_SYSTEMS_는_그대로_여섯(self):
        """서버 systems() 와 같아야 test_fabs 가 통과한다 — 목록에서 지우지 않는다."""
        blk = self.h[self.h.index("const SYSTEMS = ["):]
        blk = blk[:blk.index("];")]
        self.assertEqual(re.findall(r"code:'([A-Z0-9]+)'", blk),
                         ["ALL", "M14", "M14B", "M16A", "M16B", "M16HUB"])

    def test_고르는_자리와_들어가는_길이_전부_sysShown(self):
        for fn in ("renderOpen", "sysDdRender", "pickSystem"):
            body = _fn(self.h, fn)
            self.assertIn("sysShown()", body, fn)
            self.assertNotIn("SYSTEMS.find", body, fn)
            self.assertNotIn("SYSTEMS.map", body, fn)
        boot = self.h[self.h.index("(function boot(){"):]
        boot = boot[:boot.index("})();")]
        self.assertIn("hideApply();", boot)
        self.assertIn("sysShown().find(s => s.code === q && s.ready)", boot)

    def test_ALL_카드는_보일_때만(self):
        body = _fn(self.h, "renderOpen")
        self.assertIn("const all = shown.find(s => s.code === 'ALL');", body)
        self.assertIn("const lead = all ? `", body)
        self.assertIn("$('#sysgrid').innerHTML = `${lead}", body)

    def test_ALL_을_보다가_가리면_오프닝으로(self):
        body = _fn(self.h, "hideSet")
        self.assertIn("if(HIDE_ON && SYS === 'ALL')", body)
        self.assertIn("location.href = location.pathname;", body)

    def test_오프닝_지표도_보이는_것만_센다(self):
        body = self.h[self.h.index("async function openStats()"):]
        body = body[:body.index("\n}")]
        self.assertIn("const shown = sysShown();", body)


class 단추와_비밀번호(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = _html()

    def test_단추가_두_자리(self):
        """상단 바와 오프닝 — 같은 길(data-hidebtn)로 묶는다(테마 단추와 같은 이유)."""
        self.assertEqual(self.h.count('data-hidebtn="1"'), 2)
        self.assertIn('id="hideseg"', self.h)
        self.assertIn("document.querySelectorAll('[data-hidebtn]').forEach(b => "
                      "b.onclick = hideToggle);", self.h)

    def test_끌_때만_비밀번호(self):
        body = _fn(self.h, "hideToggle")
        self.assertIn("if(!HIDE_ON){ hideSet(true); return; }", body)
        self.assertIn("pwOpen();", body)

    def test_글자가_아니라_해시로_비교(self):
        m = re.search(r"const HIDE_PW_SHA = '([0-9a-f]+)';", self.h)
        self.assertTrue(m, "HIDE_PW_SHA 가 없다")
        self.assertEqual(len(m.group(1)), 64)
        self.assertIn("if(sha256hex($('#pwin').value) === HIDE_PW_SHA)", self.h)
        # 입력값을 다른 데서 글자 그대로 비교하지 않는다
        self.assertEqual(len(re.findall(r"\$\('#pwin'\)\.value\s*===", self.h)), 0)

    def test_crypto_subtle_에_기대지_않는다(self):
        """공장 서버는 http 라 crypto.subtle 이 아예 없다."""
        self.assertNotIn("crypto.subtle.digest", self.h)     # 주석의 설명은 괜찮다

    def test_입력칸은_가려진다(self):
        self.assertIn('<input type="password" id="pwin"', self.h)

    def test_오프닝_위에_뜬다(self):
        """오프닝이 z-index 100 — 그 위에서 눌러도 창이 가려지면 안 된다."""
        m = re.search(r'<div id="pwmask" class="gmask hidden" style="z-index:(\d+)">', self.h)
        self.assertTrue(m)
        self.assertGreater(int(m.group(1)), 100)
        self.assertIn(".open{position:fixed;inset:0;z-index:100;", self.h)

    def test_Esc_는_이_창만_닫는다(self):
        i = self.h.index("$('#pwmask').addEventListener('keydown'")
        body = self.h[i:i + 200]
        self.assertIn("e.stopPropagation();", body)
        self.assertIn("pwClose();", body)


class 해시가_표준과_같다(unittest.TestCase):
    """dashboard.html 의 sha256hex 를 잘라 node 로 돌려 hashlib 과 맞춘다."""

    VECS = ["", "abc", "a" * 55, "b" * 56, "c" * 63, "d" * 64, "e" * 119, "f" * 120,
            "관제 숨김 해제", "q" * 1000, "!@#$%^&*()_+-=~`[]{};':\",./<>?"]

    def test_hashlib_과_같다(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node 가 없다")
        fn = _fn(_html(), "sha256hex")
        js = fn + "\nconst v = JSON.parse(process.argv[1]);\n" \
                  "console.log(JSON.stringify(v.map(sha256hex)));\n"
        r = subprocess.run([node, "-e", js, json.dumps(self.VECS)],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout)
        want = [hashlib.sha256(v.encode("utf-8")).hexdigest() for v in self.VECS]
        self.assertEqual(got, want)


if __name__ == "__main__":
    unittest.main()
