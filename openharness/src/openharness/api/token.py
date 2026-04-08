"""TOKEN.TXT based API key loading and validation.

Reference: SKILL/scientific-assistant/app.py lines 528-548
"""

from __future__ import annotations

import os
from pathlib import Path

# Token search order
TOKEN_SEARCH_PATHS = [
    Path("D:/openharness/TOKEN.TXT"),               # D:\openharness (primary)
    Path.home() / ".openharness" / "TOKEN.TXT",     # User home
    Path.cwd() / "TOKEN.TXT",                       # Current working directory
    Path(__file__).parent.parent.parent.parent / "TOKEN.TXT",  # Package root
]


def find_token_file() -> Path | None:
    """Find TOKEN.TXT in search paths."""
    for path in TOKEN_SEARCH_PATHS:
        if path.is_file():
            return path
    return None


def load_token(token_file: str | Path | None = None) -> str:
    """Load API key from TOKEN.TXT file.

    Validates that the token contains only ASCII characters.
    Returns empty string if file missing, empty, or contains non-ASCII.
    """
    if token_file is None:
        found = find_token_file()
        if found is None:
            return ""
        token_file = found

    token_path = Path(token_file)
    if not token_path.is_file():
        return ""

    try:
        with open(token_path, "r", encoding="utf-8-sig") as f:
            token = f.read().strip()
    except OSError:
        return ""

    if not token:
        return ""

    # ASCII only validation (reject Korean placeholders, etc.)
    try:
        token.encode("ascii")
    except UnicodeEncodeError:
        return ""

    return token


def validate_token(token: str) -> tuple[bool, str]:
    """Validate token and return (is_valid, message)."""
    if not token:
        return False, "TOKEN.TXT is empty or not found"

    try:
        token.encode("ascii")
    except UnicodeEncodeError:
        return False, "TOKEN.TXT contains non-ASCII characters"

    if len(token) < 8:
        return False, "Token too short (min 8 characters)"

    return True, f"Token loaded ({len(token)} chars)"


def print_token_status(token: str, token_path: Path | None = None) -> None:
    """Print token status at startup."""
    if token:
        print(f"  🔑 TOKEN.TXT: loaded ({len(token)} chars)")
    else:
        path_hint = token_path or TOKEN_SEARCH_PATHS[0]
        print(f"  ⚠️  TOKEN.TXT: missing or empty")
        print(f"     → Place your API key in: {path_hint}")
