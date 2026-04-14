from __future__ import annotations

import unittest
from pathlib import Path

from harness.context import WorkspaceContext, render_context, scan_workspace


class TestWorkspaceContext(unittest.TestCase):
    def test_scan_current_workspace(self) -> None:
        ctx = scan_workspace(Path(__file__).resolve().parent.parent)
        self.assertGreater(ctx.python_file_count, 0)
        self.assertGreater(ctx.test_file_count, 0)

    def test_render_context(self) -> None:
        ctx = WorkspaceContext(root=Path('/tmp/test'), python_file_count=5, test_file_count=2)
        output = render_context(ctx)
        self.assertIn('Python files: 5', output)
        self.assertIn('Test files: 2', output)

    def test_frozen(self) -> None:
        ctx = WorkspaceContext(root=Path('.'), python_file_count=0, test_file_count=0)
        with self.assertRaises(AttributeError):
            ctx.python_file_count = 10  # type: ignore[misc]


if __name__ == '__main__':
    unittest.main()
