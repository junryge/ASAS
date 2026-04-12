from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspaceContext:
    root: Path
    python_file_count: int
    test_file_count: int


def scan_workspace(root: Path | None = None) -> WorkspaceContext:
    base = root or Path.cwd()
    src_root = base / 'harness' if (base / 'harness').exists() else base
    tests_root = base / 'tests'
    return WorkspaceContext(
        root=base,
        python_file_count=sum(1 for p in src_root.rglob('*.py') if p.is_file()),
        test_file_count=sum(1 for p in tests_root.rglob('*.py') if p.is_file()) if tests_root.exists() else 0,
    )


def render_context(ctx: WorkspaceContext) -> str:
    return '\n'.join([
        f'Workspace root: {ctx.root}',
        f'Python files: {ctx.python_file_count}',
        f'Test files: {ctx.test_file_count}',
    ])
