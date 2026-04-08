"""Tests for skill loading."""

import tempfile
import os
from pathlib import Path

from openharness.skills.loader import load_skill_md, SkillLoader
from openharness.engine.registry import ToolRegistry


def test_load_skill_md_with_frontmatter():
    with tempfile.TemporaryDirectory() as d:
        skill_dir = Path(d) / "test-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n"
            "# Test Skill\nDo the thing.\n"
        )
        meta = load_skill_md(skill_file)
        assert meta is not None
        assert meta.name == "test-skill"
        assert meta.description == "A test skill"
        assert "Do the thing" in meta.content


def test_load_skill_md_no_frontmatter():
    with tempfile.TemporaryDirectory() as d:
        skill_dir = Path(d) / "my-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("# Instructions\nJust do it.\n")
        meta = load_skill_md(skill_file)
        assert meta is not None
        assert meta.name == "my-skill"  # Falls back to directory name
        assert "Just do it" in meta.content


def test_skill_loader_scan():
    with tempfile.TemporaryDirectory() as d:
        # Create 2 skills
        for name in ["skill-a", "skill-b"]:
            skill_dir = Path(d) / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: Test {name}\n---\n# {name}\n"
            )

        loader = SkillLoader(search_paths=[Path(d)])
        skills = loader.scan()
        assert len(skills) == 2
        assert loader.count == 2
        assert "skill-a" in loader.list_skills()
        assert "skill-b" in loader.list_skills()


def test_skill_loader_register_all():
    with tempfile.TemporaryDirectory() as d:
        skill_dir = Path(d) / "echo-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: echo-skill\ndescription: Echo test\n---\nEcho the input.\n"
        )

        loader = SkillLoader(search_paths=[Path(d)])
        registry = ToolRegistry()
        count = loader.register_all(registry)
        assert count == 1
        assert registry.get("echo-skill") is not None
