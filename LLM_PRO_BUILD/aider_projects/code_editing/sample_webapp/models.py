"""데이터 모델 정의"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Todo:
    """할일 항목"""
    id: int
    title: str
    done: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    priority: int = 0  # 0=보통, 1=중요, 2=긴급

    def __post_init__(self):
        """타이틀 유효성 검증"""
        if not self.title:
            raise ValueError("할일 제목은 비어 있을 수 없습니다")
        if not (0 <= self.priority <= 2):
            raise ValueError("우선순위는 0, 1, 2 중 하나여야 합니다")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "done": self.done,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "priority": self.priority,
        }

    def mark_done(self):
        self.done = True
        self.updated_at = datetime.now()

    def mark_undone(self):
        self.done = False
        self.updated_at = datetime.now()


@dataclass
class User:
    """사용자"""
    id: int
    username: str
    email: str
    created_at: datetime = field(default_factory=datetime.now)
