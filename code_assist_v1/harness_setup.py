"""
code_assist_v1/harness_setup.py - skills/ → ToolRegistry 동기화

scientific-skills 와 무관. code_assist_v1/skills/ 만 본다.
"""
from __future__ import annotations
import os
import sys

from code_assist_v1.config import SKILLS_DIR, ROOT_DIR

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

HARNESS_AVAILABLE = False
try:
    from harness_bridge import (
        init_harness,
        register_harness_routes,
        get_registry,
        get_router,
    )
    _HARNESS_MVP_DIR = os.path.join(ROOT_DIR, "harness-mvp")
    if _HARNESS_MVP_DIR not in sys.path:
        sys.path.insert(0, _HARNESS_MVP_DIR)
    from harness import Tool  # type: ignore
    HARNESS_AVAILABLE = True
except Exception as _e:
    print(f"[code_assist_v1] harness_bridge 미가용: {_e}")


def _read_skill_md_head(path: str, n: int = 4000) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read(n)
    except Exception:
        return ""


def _make_handler(path: str):
    def handler(payload: str = "") -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return content[:2000] if len(content) > 2000 else content
        except Exception as e:
            return f"Error reading {path}: {e}"
    return handler


_REGISTERED_NAMES: set[str] = set()


def sync_skills() -> int:
    """skills/ 폴더 → ToolRegistry 동기화 (추가/갱신/삭제)."""
    global _REGISTERED_NAMES
    if not HARNESS_AVAILABLE:
        return 0
    registry = get_registry()

    seen: set[str] = set()
    if os.path.isdir(SKILLS_DIR):
        for name in sorted(os.listdir(SKILLS_DIR)):
            sd = os.path.join(SKILLS_DIR, name)
            skill_md = os.path.join(sd, "SKILL.md")
            if not os.path.isfile(skill_md):
                continue
            seen.add(name.lower())
            head = _read_skill_md_head(skill_md, 2000)
            desc = name
            for line in head.splitlines():
                if line.lower().startswith("description:"):
                    desc = line.split(":", 1)[1].strip().strip("'\"")
                    break
            try:
                registry.register(Tool(
                    name=name,
                    description=desc,
                    handler=_make_handler(skill_md),
                ))
            except Exception:
                pass

    # 사라진 스킬 제거
    for stale in _REGISTERED_NAMES - seen:
        try:
            registry.unregister(stale)
        except Exception:
            pass
    _REGISTERED_NAMES = seen
    return len(seen)


def setup_harness(app) -> bool:
    """Flask 앱에 harness 등록 + skills/ 동기화 + 라우트 등록."""
    if not HARNESS_AVAILABLE:
        return False
    try:
        # 빈 레지스트리로 시작 (legacy 안 봄)
        init_harness(SKILLS_DIR)
        sync_skills()
        register_harness_routes(app)
        return True
    except Exception as e:
        print(f"[code_assist_v1] setup_harness 실패: {e}")
        return False
