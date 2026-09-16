# -*- coding: utf-8 -*-
"""월드모델파생 — HMI 맵 (파서 + 그리기) 시험을 본 묶음에서 같이 돌린다.

월드모델은 별도 프로세스(FastAPI)라 코드가 월드모델/월드모델파생/ 아래 따로
산다. 시험도 거기 두되, 여기서 불러 돌려야 `unittest discover` 한 번에
걸린다 — 따로 두면 아무도 안 돌린다.
"""
import os
import subprocess
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WM = os.path.join(_BASE, "월드모델", "월드모델파생")


class 월드모델_HMI_맵(unittest.TestCase):
    def test_레이아웃_파서(self):
        r = subprocess.run([sys.executable, "-m", "unittest", "tests.test_layout_parse", "-q"],
                           cwd=_WM, capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])

    def test_맵_기하_JS(self):
        """캔버스 호출을 기록해 둥근 모서리·포트 자리·번호 방향·차량 방향을 본다."""
        node = "/opt/node22/bin/node" if os.path.exists("/opt/node22/bin/node") else "node"
        try:
            r = subprocess.run([node, os.path.join(_WM, "tests", "hmi_map.js")],
                               capture_output=True, text=True, timeout=60)
        except FileNotFoundError:
            self.skipTest("node 없음")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_API_가_새_재료를_준다(self):
        src = open(os.path.join(_WM, "main.py"), encoding="utf-8").read()
        for k in ('"stations"', '"labels"', '"meta"', '"schema"'):
            self.assertIn(k, src, k)

    def test_화면_테마가_맵_테마를_따라간다(self):
        """맵만 밝게 바꾸고 상단·패널·설정창은 어두운 채로 두면 따로 논다
        (고객 지적). body[data-theme] 하나로 전부 바뀌어야 한다."""
        src = open(os.path.join(_WM, "dashboard.html"), encoding="utf-8").read()
        self.assertIn("function applyPageTheme()", src)
        self.assertIn("loadMapSettings();\napplyPageTheme();", src)          # 첫 화면부터
        for fn in ("function applyMapSettings", "function resetMapSettings"):
            body = src.split(fn, 1)[1].split("\n}\n", 1)[0]
            self.assertIn("applyPageTheme();", body, fn)
        self.assertIn('body[data-theme="hmi"] {', src)
        # 옛 모달의 인라인 어두운 색을 밝은 테마가 눌러 준다
        self.assertIn('body[data-theme="hmi"] [style*="background:#222"]', src)

    def test_상단은_두_줄이고_단추_id_와_속도_글자는_그대로(self):
        """setSpeed 는 단추 **글자**(x1·MAX)로 선택 표시를 맞춘다 — 글자가
        바뀌면 표시가 안 된다. toggleLayer 는 id 로 찾는다."""
        import re
        src = open(os.path.join(_WM, "dashboard.html"), encoding="utf-8").read()
        top = src.split('<div id="topbar">', 1)[1].split("<!-- 데드락 알람 배너 -->", 1)[0]
        self.assertEqual(top.count('class="tb-row"'), 2)
        self.assertEqual(re.findall(r'class="speed-btn"[^>]*>([^<]+)<', top),
                         ["x1", "x2", "x5", "x10", "MAX"])
        for i in ("btn-zone", "btn-railcut", "btn-id", "btn-name", "btn-station",
                  "btn-label", "btn-junction", "btn-sensor", "btn-hotspot",
                  "fab-select", "layout-select", "lp-from", "lp-to", "lp-table",
                  "lp-btn", "lp-status", "time-display", "frame-display",
                  "time-slider", "status-badge", "loading-msg"):
            self.assertIn(f'id="{i}"', top, i)
        # 손잡이가 툴바 위에 얹히지 않게 맵 줄 기준으로 잡는다
        self.assertIn("#rsidebar-toggle, #sidebar-toggle { top:10px; }", src)

    def test_설정창_입력_id_는_전부_그대로(self):
        """openMapSettings/applyMapSettings 가 'ms-'+키 로 찾는다 — 하나라도
        빠지면 그 설정은 저장이 안 된다."""
        import re
        src = open(os.path.join(_WM, "dashboard.html"), encoding="utf-8").read()
        keys = re.findall(r"^\s+(\w+):\s", src.split("const DEFAULT_MAP_SETTINGS = {", 1)[1].split("\n};", 1)[0], re.M)
        self.assertGreater(len(keys), 15)
        for k in keys:
            self.assertIn(f'id="ms-{k}"', src, k)

    def test_투영은_한_벌이다(self):
        """등각(◈) 토글이 들어오면서 투영을 한 함수로 모았다. 예전엔 같은 공식이
        그리기·클릭·차량 이동·존 이동·핫스팟 다섯 곳에 복사돼 있어서, 투영을
        바꾸면 클릭이 엉뚱한 차량을 집었다. 옛 공식이 한 줄이라도 남으면 걸린다."""
        src = open(os.path.join(_WM, "dashboard.html"), encoding="utf-8").read()
        for old in ("(cw-20-dataW*sc)/2", "(w-20-dataW*sc)/2", "ox+(x-b.min_x)*sc",
                    "ox + (v.dx - b.min_x) * sc"):
            self.assertNotIn(old, src, old)
        self.assertEqual(src.count("mapCenterOn("), 4)          # 정의 1 + 차량·존·핫스팟 3
        self.assertGreaterEqual(src.count("mapProj(b, w, h)"), 2)  # drawMap + 클릭
        self.assertIn('id="btn-iso"', src)
        self.assertIn("if (layer==='iso')", src)
        # 등각은 기본 **끔** — 지금보다 못하면 하지 말라는 것이 결정이었다
        self.assertIn("let showIso = false;", src)

    def test_옛_노드번호_블록이_안_남아_있다(self):
        """캐시 밖에서 매 프레임 9,403개를 다시 훑던 자리 — 레이어로 옮겼다."""
        src = open(os.path.join(_WM, "dashboard.html"), encoding="utf-8").read()
        self.assertNotIn("// 2.7. 레일 노드 주소(addr) 표시", src)
        self.assertEqual(src.count("drawRailLayer("), 2)      # 정의 1 + 호출 1


if __name__ == "__main__":
    unittest.main()
