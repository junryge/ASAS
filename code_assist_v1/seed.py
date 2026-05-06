"""
code_assist_v1/seed.py - 첫 기동 시 scientific-skills 의 코딩 스킬을 skills/ 로 복사.

- skills/ 가 비어있을 때만 동작 (멱등).
- scientific-skills/ 가 없으면 조용히 패스.
- 도메인 지식은 가져오지 않음 (사용자가 새로 등록).
"""
from __future__ import annotations
import os
import shutil

from code_assist_v1.config import SKILLS_DIR, ROOT_DIR
from code_assist_v1.skill_whitelist import is_coding_skill


def _read_description(skill_md: str) -> str:
    try:
        with open(skill_md, "r", encoding="utf-8") as f:
            head = f.read(2000)
    except Exception:
        return ""
    for line in head.splitlines():
        if line.lower().startswith("description:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return ""


def seed_skills_if_empty() -> int:
    """skills/ 가 비어있으면 scientific-skills/ 에서 코딩 스킬을 복사한다.

    Returns:
        복사한 스킬 개수 (이미 있으면 0).
    """
    if not os.path.isdir(SKILLS_DIR):
        os.makedirs(SKILLS_DIR, exist_ok=True)

    if any(os.scandir(SKILLS_DIR)):
        return 0  # 이미 채워져 있음

    src_root = os.path.join(ROOT_DIR, "scientific-skills")
    if not os.path.isdir(src_root):
        print(f"  ℹ️  scientific-skills/ 없음 → 스킬 시드 건너뜀")
        return 0

    print(f"  📦 scientific-skills/ → skills/ 코딩 스킬 시드 중...")
    copied = 0
    skipped = 0
    for name in sorted(os.listdir(src_root)):
        src_dir = os.path.join(src_root, name)
        skill_md = os.path.join(src_dir, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue
        desc = _read_description(skill_md)
        if not is_coding_skill(name, desc):
            skipped += 1
            continue
        dst_dir = os.path.join(SKILLS_DIR, name)
        try:
            shutil.copytree(src_dir, dst_dir)
            copied += 1
        except Exception as e:
            print(f"     ⚠️  복사 실패 ({name}): {e}")

    print(f"     ✅ 코딩 스킬 {copied}개 가져옴 (비-코딩 {skipped}개 제외)")
    return copied
