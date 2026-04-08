"""Skill loader - scans directories for SKILL.md files and registers them.

Compatible with anthropics/skills SKILL.md format:
---
name: skill-name
description: what the skill does
---
# Instructions for Claude
...
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..engine.models import Tool
from ..engine.registry import ToolRegistry

# Search paths for skills (in priority order)
SKILL_SEARCH_PATHS = [
    Path.home() / ".openharness" / "skills",   # User custom skills
]

SKILL_FILENAME = "SKILL.md"


@dataclass
class SkillMeta:
    """Parsed skill metadata from SKILL.md frontmatter."""
    name: str
    description: str
    content: str  # Full instruction body
    path: Path
    extra: dict[str, Any]


def load_skill_md(path: Path) -> SkillMeta | None:
    """Parse a SKILL.md file into metadata.

    Format:
    ---
    name: my-skill
    description: What it does
    ---
    # Body content
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    # Parse YAML frontmatter
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if fm_match:
        frontmatter = fm_match.group(1)
        body = text[fm_match.end():]
    else:
        # No frontmatter - use directory name as skill name
        body = text
        frontmatter = ""

    # Simple YAML key-value parser (no dependency on pyyaml)
    meta: dict[str, str] = {}
    for line in frontmatter.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip('"').strip("'")

    name = meta.pop("name", path.parent.name)
    description = meta.pop("description", f"Skill: {name}")

    return SkillMeta(
        name=name,
        description=description,
        content=body.strip(),
        path=path,
        extra=meta,
    )


class SkillLoader:
    """Scans directories for SKILL.md files and registers them as tools."""

    def __init__(
        self,
        search_paths: list[Path] | None = None,
        bundled_path: Path | None = None,
    ) -> None:
        self.search_paths = list(search_paths or SKILL_SEARCH_PATHS)
        # Bundled skills from the package
        if bundled_path:
            self.search_paths.insert(0, bundled_path)
        self._skills: dict[str, SkillMeta] = {}

    def scan(self) -> list[SkillMeta]:
        """Scan all search paths for SKILL.md files."""
        self._skills.clear()
        for base_path in self.search_paths:
            if not base_path.is_dir():
                continue
            # Look for pattern: base_path/skill-name/SKILL.md
            for skill_dir in sorted(base_path.iterdir()):
                if not skill_dir.is_dir():
                    continue
                skill_file = skill_dir / SKILL_FILENAME
                if not skill_file.is_file():
                    # Also check nested: base_path/category/skill-name/SKILL.md
                    for sub_dir in sorted(skill_dir.iterdir()):
                        if sub_dir.is_dir():
                            nested_file = sub_dir / SKILL_FILENAME
                            if nested_file.is_file():
                                meta = load_skill_md(nested_file)
                                if meta and meta.name not in self._skills:
                                    self._skills[meta.name] = meta
                    continue

                meta = load_skill_md(skill_file)
                if meta and meta.name not in self._skills:
                    self._skills[meta.name] = meta

        return list(self._skills.values())

    def register_all(self, registry: ToolRegistry) -> int:
        """Scan and register all found skills into the tool registry."""
        skills = self.scan()
        count = 0
        for skill in skills:
            # Create a handler that returns the skill content (instructions)
            content = skill.content

            def make_handler(c: str):
                def handler(payload: str) -> str:
                    return c[:2000]
                return handler

            tool = Tool(
                name=skill.name,
                description=skill.description,
                handler=make_handler(content),
                category="skill",
            )
            registry.register(tool)
            count += 1
        return count

    def get_skill(self, name: str) -> SkillMeta | None:
        return self._skills.get(name)

    def list_skills(self) -> list[str]:
        return sorted(self._skills.keys())

    @property
    def count(self) -> int:
        return len(self._skills)
