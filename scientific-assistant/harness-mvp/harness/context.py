from __future__ import annotations

import os
from dataclasses import dataclass, field
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


# ── 프로젝트별 하네스 맵 관리 ──

HARNESS_MAPS_DIR = "harness_maps"  # BASE_DIR 기준 상대 경로


@dataclass
class ProjectMap:
    """프로젝트별 하네스 맵"""
    project_name: str
    content: str
    rules: list[str] = field(default_factory=list)
    forbidden: list[str] = field(default_factory=list)
    mistakes: list[str] = field(default_factory=list)


def _parse_harness_map(content: str) -> dict:
    """하네스 맵 .md 파일에서 섹션별 내용 추출"""
    sections = {}
    current_section = ""
    current_lines = []

    for line in content.split("\n"):
        if line.startswith("## "):
            if current_section:
                sections[current_section] = "\n".join(current_lines)
            current_section = line.strip("# ").strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_section:
        sections[current_section] = "\n".join(current_lines)

    return sections


def load_project_map(project_name: str, base_dir: str = "") -> ProjectMap | None:
    """프로젝트별 하네스 맵 로드

    harness_maps/{project_name}.md 파일에서 로드.
    없으면 None 반환.
    """
    maps_dir = os.path.join(base_dir, HARNESS_MAPS_DIR) if base_dir else HARNESS_MAPS_DIR
    map_path = os.path.join(maps_dir, f"{project_name}.md")

    if not os.path.isfile(map_path):
        return None

    try:
        with open(map_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None

    sections = _parse_harness_map(content)

    # 금지 사항 추출
    forbidden = []
    for key in sections:
        if "금지" in key or "Strict" in key or "Boundaries" in key:
            for line in sections[key].split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    forbidden.append(line.lstrip("- ").strip())

    # 오답 노트 추출
    mistakes = []
    for key in sections:
        if "오답" in key or "Mistakes" in key or "Lessons" in key:
            for line in sections[key].split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("["):
                    mistakes.append(line.lstrip("- ").strip())

    # 규칙 추출
    rules = []
    for key in sections:
        if "워크플로" in key or "Workflow" in key or "규칙" in key:
            for line in sections[key].split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    rules.append(line.lstrip("- ").strip())

    return ProjectMap(
        project_name=project_name,
        content=content,
        rules=rules,
        forbidden=forbidden,
        mistakes=mistakes,
    )


def list_project_maps(base_dir: str = "") -> list[str]:
    """사용 가능한 프로젝트 맵 목록 반환"""
    maps_dir = os.path.join(base_dir, HARNESS_MAPS_DIR) if base_dir else HARNESS_MAPS_DIR
    if not os.path.isdir(maps_dir):
        return []
    return [
        f.replace(".md", "")
        for f in os.listdir(maps_dir)
        if f.endswith(".md")
    ]


def build_project_prompt(project_map: ProjectMap) -> str:
    """프로젝트 맵을 시스템 프롬프트에 주입할 텍스트로 변환"""
    parts = [f"\n=== 프로젝트 하네스: {project_map.project_name} ==="]

    if project_map.forbidden:
        parts.append("\n🚫 절대 금지 사항:")
        for rule in project_map.forbidden:
            parts.append(f"  - {rule}")

    if project_map.rules:
        parts.append("\n⚙️ 작업 규칙:")
        for rule in project_map.rules:
            parts.append(f"  - {rule}")

    if project_map.mistakes:
        parts.append("\n📝 오답 노트 (반복 금지):")
        for m in project_map.mistakes:
            parts.append(f"  - {m}")

    parts.append("")
    return "\n".join(parts)
