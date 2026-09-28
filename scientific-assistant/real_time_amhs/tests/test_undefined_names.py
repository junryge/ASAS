# -*- coding: utf-8 -*-
"""함수 안에서 **정의 안 된 이름**을 쓰는 줄이 없나 — 파일을 읽어서만 본다.

★계기: /api/window 가 STATE["settings_changed_at"] 을 썼는데 STATE 는 server.py 에
  없는 이름이었다(accuracy.py 에만 있다). 값은 바뀌는데 응답이 500 으로 끝나서,
  실시간 관제의 '수집 주기' 를 바꾸면 늘 실패로 떴다. 그 줄은 부를 때만 터지므로
  서버를 띄워 두기만 해서는 아무도 모른다 — 매뉴얼 스크린샷을 찍다가 잡혔다.
★flask 없이 돈다 (ast 로 읽기만 한다). 모듈 맨 위의 이름 · 함수 안에서 만든 이름 ·
  내장 이름이 아닌 것을 읽으면 걸린다.
"""
import ast
import builtins
import io
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
FILES = ["server.py", "sentinel.py", "graphs.py", "fab_score.py", "jupyter_csv.py", "store_csv.py",
         "world_link.py", "lp_client.py", "accuracy.py", "alarm_count.py", "http_cache.py",
         "contrib.py", "score_tune.py", "llm_client.py", "report.py"]


def _module_names(tree):
    names = set(dir(builtins)) | {"__file__", "__name__", "__doc__"}
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name)
            continue
        for t in ast.walk(n):
            if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store):
                names.add(t.id)
            elif isinstance(t, (ast.Import, ast.ImportFrom)):
                names.update((a.asname or a.name).split(".")[0] for a in t.names)
            elif isinstance(t, (ast.FunctionDef, ast.ClassDef)):
                names.add(t.name)
    return names


def undefined(src):
    tree = ast.parse(src)
    mod = _module_names(tree)
    out = []
    for fn in tree.body:
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        local = set()
        for t in ast.walk(fn):
            if isinstance(t, ast.Name) and isinstance(t.ctx, (ast.Store, ast.Del)):
                local.add(t.id)
            elif isinstance(t, ast.arg):
                local.add(t.arg)
            elif isinstance(t, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and t is not fn:
                local.add(t.name)
            elif isinstance(t, (ast.Import, ast.ImportFrom)):
                local.update((a.asname or a.name).split(".")[0] for a in t.names)
            elif isinstance(t, ast.ExceptHandler) and t.name:
                local.add(t.name)
            elif isinstance(t, (ast.Global, ast.Nonlocal)):
                local.update(t.names)
        for t in ast.walk(fn):
            if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Load) and t.id not in local and t.id not in mod:
                out.append(f"{fn.name}() {t.lineno}행 — {t.id}")
    return out


class 정의_안_된_이름이_없다(unittest.TestCase):

    def test_관제_모듈들(self):
        for f in FILES:
            with io.open(os.path.join(APP, f), encoding="utf-8") as fh:
                bad = undefined(fh.read())
            self.assertEqual(bad, [], f + " — " + ", ".join(bad))

    def test_검사기가_진짜로_잡는다(self):
        """★그때 그 줄 모양 그대로 — 이게 안 잡히면 위 시험은 빈말이다."""
        src = ("import datetime\n"
               "def api_window():\n"
               "    q = {}\n"
               "    STATE['settings_changed_at'] = datetime.datetime.now()\n"
               "    return q\n")
        self.assertEqual(undefined(src), ["api_window() 4행 — STATE"])

    def test_수집_주기_저장은_끝까지_간다(self):
        with io.open(os.path.join(APP, "server.py"), encoding="utf-8") as fh:
            s = fh.read()
        i = s.index("def api_window():")
        blk = s[i:s.index("\n@app.route(", i)]
        self.assertNotIn('STATE["settings_changed_at"]', blk)
        self.assertIn('q["poll_interval_s"] = p', blk)


if __name__ == "__main__":
    unittest.main()
