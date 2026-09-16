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

    def test_옛_노드번호_블록이_안_남아_있다(self):
        """캐시 밖에서 매 프레임 9,403개를 다시 훑던 자리 — 레이어로 옮겼다."""
        src = open(os.path.join(_WM, "dashboard.html"), encoding="utf-8").read()
        self.assertNotIn("// 2.7. 레일 노드 주소(addr) 표시", src)
        self.assertEqual(src.count("drawRailLayer("), 2)      # 정의 1 + 호출 1


if __name__ == "__main__":
    unittest.main()
