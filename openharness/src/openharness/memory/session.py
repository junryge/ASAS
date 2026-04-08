"""Session persistence - JSON save/load."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

SESSIONS_DIR_NAME = ".harness_sessions"


@dataclass(frozen=True)
class StoredSession:
    """Immutable session snapshot."""
    session_id: str
    messages: tuple[str, ...]
    input_tokens: int = 0
    output_tokens: int = 0
    timestamp: float = 0.0


def _sessions_dir(directory: str | None = None) -> Path:
    root = Path(directory) if directory else Path.home() / ".openharness"
    d = root / SESSIONS_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_session(session: StoredSession, directory: str | None = None) -> Path:
    """Save session to JSON file."""
    d = _sessions_dir(directory)
    path = d / f"{session.session_id}.json"
    data = {
        "session_id": session.session_id,
        "messages": list(session.messages),
        "input_tokens": session.input_tokens,
        "output_tokens": session.output_tokens,
        "timestamp": session.timestamp or time.time(),
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_session(session_id: str, directory: str | None = None) -> StoredSession:
    """Load session from JSON file."""
    d = _sessions_dir(directory)
    path = d / f"{session_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return StoredSession(
        session_id=data["session_id"],
        messages=tuple(data.get("messages", [])),
        input_tokens=data.get("input_tokens", 0),
        output_tokens=data.get("output_tokens", 0),
        timestamp=data.get("timestamp", 0.0),
    )


def list_sessions(directory: str | None = None) -> list[str]:
    """List all session IDs, sorted by name."""
    d = _sessions_dir(directory)
    return sorted(p.stem for p in d.glob("*.json"))


def delete_session(session_id: str, directory: str | None = None) -> bool:
    """Delete a session file. Returns True if deleted."""
    d = _sessions_dir(directory)
    path = d / f"{session_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False
