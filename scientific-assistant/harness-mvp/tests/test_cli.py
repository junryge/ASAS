from __future__ import annotations

import subprocess
import sys
import unittest


HARNESS_DIR = str(__import__('pathlib').Path(__file__).resolve().parent.parent)


class TestCLI(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, '-m', 'harness', *args],
            capture_output=True, text=True, cwd=HARNESS_DIR,
        )

    def test_list(self) -> None:
        result = self._run('list')
        self.assertEqual(result.returncode, 0)
        self.assertIn('Tool entries:', result.stdout)
        self.assertIn('echo', result.stdout)

    def test_tasks(self) -> None:
        result = self._run('tasks')
        self.assertEqual(result.returncode, 0)
        self.assertIn('tool-registry-check', result.stdout)

    def test_context(self) -> None:
        result = self._run('context')
        self.assertEqual(result.returncode, 0)
        self.assertIn('Python files:', result.stdout)

    def test_find(self) -> None:
        result = self._run('find', 'echo')
        self.assertEqual(result.returncode, 0)
        self.assertIn('echo', result.stdout)

    def test_route(self) -> None:
        result = self._run('route', 'echo hello')
        self.assertEqual(result.returncode, 0)
        self.assertIn('echo', result.stdout)

    def test_route_no_match(self) -> None:
        result = self._run('route', 'xyznonexistent')
        self.assertEqual(result.returncode, 0)
        self.assertIn('No tool matches', result.stdout)

    def test_run(self) -> None:
        result = self._run('run', 'echo hello')
        self.assertEqual(result.returncode, 0)
        self.assertIn('## Turn 1', result.stdout)
        self.assertIn('stop_reason=', result.stdout)
        self.assertIn('Session persisted:', result.stdout)

    def test_run_structured_output(self) -> None:
        result = self._run('run', 'echo hello', '--structured-output')
        self.assertEqual(result.returncode, 0)
        self.assertIn('"results"', result.stdout)

    def test_run_with_deny(self) -> None:
        result = self._run('run', 'echo hello', '--deny-tool', 'echo')
        self.assertEqual(result.returncode, 0)

    def test_exec_tool(self) -> None:
        result = self._run('exec-tool', 'upper', 'hello world')
        self.assertEqual(result.returncode, 0)
        self.assertIn('HELLO WORLD', result.stdout)

    def test_exec_tool_unknown(self) -> None:
        result = self._run('exec-tool', 'ghost', 'test')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Unknown tool', result.stdout)

    def test_summary(self) -> None:
        result = self._run('summary')
        self.assertEqual(result.returncode, 0)
        self.assertIn('Harness Session Report', result.stdout)

    def test_session_list(self) -> None:
        result = self._run('session-list')
        self.assertEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
