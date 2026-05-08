"""
code_assist_v1/skill_filter.py - skills/ 단일 폴더 스캔

- code_assist_v1/skills/ 만 본다 (legacy 공유 없음).
- source 구분 없음 — 모두 동일하게 편집 가능.
"""
from __future__ import annotations
import os
import re
from typing import Optional

from code_assist_v1.config import SKILLS_DIR


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> dict:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    out: dict = {}
    for line in m.group(1).splitlines():
        line = line.rstrip()
        if not line or line.startswith(" "):
            continue
        kv = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", line)
        if kv:
            val = kv.group(2).strip()
            if val and (val.startswith('"') and val.endswith('"') or val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            out[kv.group(1)] = val if val else {}
    return out


def scan_all_skills() -> dict[str, dict]:
    """skills/ 의 모든 SKILL.md 보유 폴더 스캔."""
    result: dict[str, dict] = {}
    if not os.path.isdir(SKILLS_DIR):
        return result
    for name in sorted(os.listdir(SKILLS_DIR)):
        sd = os.path.join(SKILLS_DIR, name)
        skill_md = os.path.join(sd, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue
        try:
            with open(skill_md, "r", encoding="utf-8") as f:
                head = f.read(4000)
        except Exception:
            head = ""
        fm = _parse_frontmatter(head)
        result[name] = {
            "id": name,
            "description": str(fm.get("description") or "")[:400],
            "path": skill_md,
            "frontmatter": fm,
        }
    return result


def list_skills(query: str = "") -> list[dict]:
    all_skills = scan_all_skills()
    if query:
        ql = query.lower()
        keep = [
            sid for sid, info in all_skills.items()
            if ql in sid.lower() or ql in (info.get("description") or "").lower()
        ]
    else:
        keep = list(all_skills.keys())
    out = []
    for sid in sorted(keep):
        info = all_skills[sid]
        out.append({
            "id": sid,
            "description": info.get("description", ""),
        })
    return out


def get_skill_path(skill_id: str) -> Optional[str]:
    p = os.path.join(SKILLS_DIR, skill_id, "SKILL.md")
    return p if os.path.isfile(p) else None


def load_skill_content(skill_id: str, max_chars: int = 8000) -> Optional[str]:
    path = get_skill_path(skill_id)
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None
    if len(content) > max_chars:
        content = content[:max_chars] + "\n\n... (잘림)"
    return content


def get_skill_meta(skill_id: str) -> Optional[dict]:
    path = get_skill_path(skill_id)
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            head = f.read(4000)
    except Exception:
        head = ""
    fm = _parse_frontmatter(head)
    return {
        "id": skill_id,
        "name": fm.get("name", skill_id),
        "description": fm.get("description", ""),
        "path": path,
        "frontmatter": fm,
        "editable": True,  # 모두 편집 가능 (단일 폴더)
    }
