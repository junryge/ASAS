"""Transcript management - message compaction and replay."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TranscriptStore:
    """Stores conversation transcript entries with compaction support."""

    entries: list[str] = field(default_factory=list)
    flushed: bool = False

    def append(self, entry: str) -> None:
        self.entries.append(entry)
        self.flushed = False

    def compact(self, keep_last: int = 10) -> None:
        """Trim old entries, keeping only the last N."""
        if len(self.entries) > keep_last:
            self.entries = self.entries[-keep_last:]

    def replay(self) -> tuple[str, ...]:
        return tuple(self.entries)

    def flush(self) -> None:
        self.flushed = True

    @property
    def count(self) -> int:
        return len(self.entries)
