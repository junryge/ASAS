from __future__ import annotations

import re
from dataclasses import dataclass, field


# ── 기본 금지 코드 패턴 (위험한 SQL/Shell 명령) ──
DEFAULT_FORBIDDEN_PATTERNS = [
    # SQL 위험 명령
    (r'\bDROP\s+(TABLE|DATABASE|INDEX|VIEW)\b', "DROP 명령 금지"),
    (r'\bDELETE\s+FROM\b', "DELETE FROM 금지"),
    (r'\bTRUNCATE\s+TABLE\b', "TRUNCATE TABLE 금지"),
    (r'\bALTER\s+TABLE\s+\w+\s+DROP\b', "ALTER TABLE DROP 금지"),
    # Shell 위험 명령
    (r'\brm\s+-rf\b', "rm -rf 금지"),
    (r'\brm\s+-r\b', "rm -r 금지"),
    (r'\brmdir\s+/\b', "rmdir / 금지"),
    (r'\bmkfs\b', "mkfs 금지"),
    (r'\bdd\s+if=', "dd 명령 금지"),
    # 환경 변수 하드코딩
    (r'(api_key|secret|password|token)\s*=\s*["\'][^"\']{8,}', "민감정보 하드코딩 금지"),
    # .env 파일 직접 수정
    (r'open\(["\']\.env', ".env 파일 직접 수정 금지"),
]


@dataclass(frozen=True)
class ToolPermissionContext:
    deny_names: frozenset[str] = field(default_factory=frozenset)
    deny_prefixes: tuple[str, ...] = ()

    @classmethod
    def from_iterables(
        cls,
        deny_names: list[str] | None = None,
        deny_prefixes: list[str] | None = None,
    ) -> ToolPermissionContext:
        return cls(
            deny_names=frozenset(name.lower() for name in (deny_names or [])),
            deny_prefixes=tuple(prefix.lower() for prefix in (deny_prefixes or [])),
        )

    def blocks(self, tool_name: str) -> bool:
        lowered = tool_name.lower()
        return lowered in self.deny_names or any(
            lowered.startswith(prefix) for prefix in self.deny_prefixes
        )


class CodeGuard:
    """LLM 응답 코드에서 금지 패턴을 검사하고 차단"""

    def __init__(self, extra_patterns: list[tuple[str, str]] | None = None):
        self._patterns = list(DEFAULT_FORBIDDEN_PATTERNS)
        if extra_patterns:
            self._patterns.extend(extra_patterns)

    def add_pattern(self, regex: str, reason: str) -> None:
        """금지 패턴 추가"""
        self._patterns.append((regex, reason))

    def load_from_harness_map(self, map_content: str) -> None:
        """하네스 맵의 금지 사항 섹션에서 패턴 자동 추출"""
        in_forbidden = False
        for line in map_content.split("\n"):
            stripped = line.strip()
            if "금지" in stripped and ("##" in line or "**" in stripped):
                in_forbidden = True
                continue
            if in_forbidden and stripped.startswith("##"):
                in_forbidden = False
                continue
            if in_forbidden and stripped.startswith("-"):
                rule = stripped.lstrip("- ").strip()
                if rule:
                    # 규칙 텍스트에서 키워드 추출하여 패턴 생성
                    keywords = re.findall(r'`([^`]+)`', rule)
                    for kw in keywords:
                        escaped = re.escape(kw)
                        self._patterns.append((escaped, rule))

    def check(self, code: str) -> list[dict]:
        """코드에서 금지 패턴 검사. 위반 목록 반환."""
        violations = []
        for pattern, reason in self._patterns:
            try:
                matches = re.findall(pattern, code, re.IGNORECASE)
                if matches:
                    violations.append({
                        "pattern": pattern,
                        "reason": reason,
                        "matches": [str(m)[:100] for m in matches[:3]],
                    })
            except re.error:
                continue
        return violations

    def is_safe(self, code: str) -> tuple[bool, str]:
        """코드가 안전한지 검사. (안전여부, 사유) 반환."""
        violations = self.check(code)
        if not violations:
            return True, ""
        reasons = [v["reason"] for v in violations[:3]]
        return False, f"금지된 패턴 감지: {', '.join(reasons)}"
