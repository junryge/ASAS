"""Event history logging."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class HistoryEvent:
    title: str
    detail: str


@dataclass
class HistoryLog:
    """Chronological event log."""

    events: list[HistoryEvent] = field(default_factory=list)

    def add(self, title: str, detail: str) -> None:
        self.events.append(HistoryEvent(title=title, detail=detail))

    def as_markdown(self) -> str:
        if not self.events:
            return "# Session History\n(empty)"
        lines = ["# Session History"]
        for e in self.events:
            lines.append(f"- **{e.title}**: {e.detail}")
        return "\n".join(lines)

    def clear(self) -> None:
        self.events.clear()
