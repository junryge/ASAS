"""
skills.py — 부품 ③ 스킬 (SKILL.md '인수인계 노트')

세션 바뀌면 맥락이 백지가 되고, AI 는 비어있는 정보를 자신있게 추측으로 메운다.
스킬은 프로젝트 지식을 파일에 박아두고, 루프가 매 작업마다 다시 읽게 한다.

stdlib 만으로 YAML 비슷한 프론트매터(---) 를 파싱한다(간이 파서).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def _parse_frontmatter(text: str):
    """'---\\nkey: value\\n---\\n본문' 형식을 (meta, body) 로 분리.
    중첩/리스트는 지원 안 함(간이). 필요한 키-값/콤마리스트만.
    """
    meta: Dict[str, Any] = {}
    body = text
    if text.lstrip().startswith("---"):
        t = text.lstrip()
        end = t.find("\n---", 3)
        if end != -1:
            fm = t[3:end].strip()
            body = t[end + 4:].lstrip("\n")
            for line in fm.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                k, v = line.split(":", 1)
                k, v = k.strip(), v.strip()
                # 콤마 리스트 자동 인식
                if "," in v:
                    meta[k] = [x.strip() for x in v.split(",") if x.strip()]
                else:
                    meta[k] = v
    return meta, body


@dataclass
class Skill:
    """하나의 SKILL.md = 이름 + 메타 + 본문(지침)."""
    name: str
    body: str
    meta: Dict[str, Any] = field(default_factory=dict)
    path: Optional[Path] = None

    @property
    def description(self) -> str:
        return str(self.meta.get("description", "")).strip()

    def as_prompt_block(self) -> str:
        """프롬프트에 끼워넣을 형태로."""
        head = f"[SKILL: {self.name}]"
        if self.description:
            head += f" {self.description}"
        return f"{head}\n{self.body}".strip()

    @classmethod
    def from_file(cls, path: Path) -> "Skill":
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        # 이름: 메타 name > 부모폴더명 > 파일stem
        name = (meta.get("name")
                or (path.parent.name if path.name.upper() == "SKILL.MD" else path.stem))
        return cls(name=str(name), body=body, meta=meta, path=path)

    @classmethod
    def from_text(cls, name: str, text: str) -> "Skill":
        meta, body = _parse_frontmatter(text)
        return cls(name=name, body=body, meta=meta)


class SkillRegistry:
    """skills_dir 아래의 SKILL.md / *.md 를 로드해 이름으로 조회."""

    def __init__(self, skills_dir: Optional[Path] = None):
        self._skills: Dict[str, Skill] = {}
        if skills_dir:
            self.discover(skills_dir)

    def add(self, skill: Skill):
        self._skills[skill.name] = skill

    def discover(self, skills_dir: Path) -> "SkillRegistry":
        root = Path(skills_dir)
        if not root.exists():
            return self
        # 1) <dir>/<name>/SKILL.md 패턴
        for p in root.glob("*/SKILL.md"):
            try:
                self.add(Skill.from_file(p))
            except Exception:
                continue
        # 2) <dir>/*.md 패턴 (SKILL.md 단독 포함)
        for p in root.glob("*.md"):
            try:
                self.add(Skill.from_file(p))
            except Exception:
                continue
        return self

    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def names(self) -> List[str]:
        return sorted(self._skills)

    def all(self) -> List[Skill]:
        return [self._skills[n] for n in self.names()]

    def bundle(self, names: List[str]) -> str:
        """여러 스킬을 하나의 프롬프트 블록으로 합친다."""
        blocks = []
        for n in names:
            s = self.get(n)
            if s:
                blocks.append(s.as_prompt_block())
        return "\n\n".join(blocks)
