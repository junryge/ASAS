"""
feedback.py - 피드백 루프 (Phase 7): 실행 결과 피드백 저장 및 활용

실행 결과에 대한 피드백(품질 점수, 반려 사유, 개선 제안)을 저장하고,
다음 실행 시 이전 피드백을 참조하여 시스템 프롬프트에 반영.
반복 사용할수록 품질이 개선됨.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class FeedbackEntry:
    """단일 피드백 항목"""
    timestamp: float
    skill_id: str
    agent: str
    quality_score: int  # 0~100
    approved: bool
    rejection_reason: str | None = None
    improvement_notes: str | None = None
    query_context: str | None = None  # 어떤 질문에서 발생했는지


class FeedbackStore:
    """피드백 저장소 - 스킬별 피드백 관리"""

    def __init__(self, store_dir: str | Path):
        self._dir = Path(store_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, skill_id: str) -> Path:
        safe_name = skill_id.replace("/", "_").replace("\\", "_")
        return self._dir / f"feedback_{safe_name}.json"

    def add(self, entry: FeedbackEntry) -> None:
        """피드백 추가"""
        path = self._path(entry.skill_id)
        entries = self._load_raw(path)
        entries.append(asdict(entry))

        # 최대 50개 유지 (오래된 것 삭제)
        if len(entries) > 50:
            entries = entries[-50:]

        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)

    def get(self, skill_id: str, limit: int = 10) -> list[FeedbackEntry]:
        """특정 스킬의 피드백 조회"""
        path = self._path(skill_id)
        raw = self._load_raw(path)
        entries = []
        for item in raw[-limit:]:
            try:
                entries.append(FeedbackEntry(**item))
            except (TypeError, KeyError):
                continue
        return entries

    def get_summary(self, skill_id: str) -> dict:
        """특정 스킬의 피드백 요약 통계"""
        entries = self.get(skill_id, limit=50)
        if not entries:
            return {"total": 0, "avg_score": 0, "approval_rate": 0, "common_issues": []}

        total = len(entries)
        avg_score = sum(e.quality_score for e in entries) / total
        approved = sum(1 for e in entries if e.approved)
        approval_rate = approved / total * 100

        # 반려 사유 빈도
        reasons: dict[str, int] = {}
        for e in entries:
            if e.rejection_reason:
                reasons[e.rejection_reason] = reasons.get(e.rejection_reason, 0) + 1
        common_issues = sorted(reasons.items(), key=lambda x: -x[1])[:5]

        return {
            "total": total,
            "avg_score": round(avg_score, 1),
            "approval_rate": round(approval_rate, 1),
            "common_issues": [{"reason": r, "count": c} for r, c in common_issues],
        }

    def build_prompt_hint(self, skill_ids: list[str]) -> str:
        """이전 피드백을 기반으로 시스템 프롬프트에 추가할 힌트 생성.

        반복 사용 시 이전 실패 사유를 참조하여 같은 실수를 방지.
        """
        hints = []
        for sid in skill_ids:
            summary = self.get_summary(sid)
            if summary["total"] == 0:
                continue
            if summary["approval_rate"] < 80 and summary["common_issues"]:
                issues_text = ", ".join(i["reason"] for i in summary["common_issues"][:3])
                hints.append(
                    f"[{sid}] 이전 피드백: 승인율 {summary['approval_rate']}%, "
                    f"주요 문제: {issues_text}. 이 점을 개선해주세요."
                )
        if not hints:
            return ""
        return "\n=== 이전 피드백 기반 주의사항 ===\n" + "\n".join(hints) + "\n\n"

    def _load_raw(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError):
            return []
