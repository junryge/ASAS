"""
demos_v1/hermes/store.py — 헤르메스 파일 저장 공통 (경로 / 원자쓰기 / 안전성)

- 사용자별 폴더: demos_data/agents/<user_id>/
- 모든 쓰기는 tempfile → os.replace 원자 교체
- 저장소 6,000자 상한, 인젝션 패턴 차단
"""
from __future__ import annotations
import os
import re
import json
import tempfile

# BASE_DIR = scientific-assistant/  (demos_v1/hermes/store.py 기준 3단계 상위)
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))          # demos_v1/hermes
_DEMOS_DIR = os.path.dirname(_PKG_DIR)                          # demos_v1
try:
    from demos_v1.utils import BASE_DIR as _BASE_DIR
    BASE_DIR = _BASE_DIR
except Exception:
    BASE_DIR = os.path.dirname(_DEMOS_DIR)                      # scientific-assistant

AGENTS_ROOT = os.path.join(BASE_DIR, "demos_data", "agents")

MAX_STORE_CHARS = 6000      # 저장소(MEMORY/USER)당 상한
ITEM_SEP = "§"              # 항목 구분자


def safe_id(val: str) -> str:
    """경로 조작 차단. 빈/위험 입력은 빈 문자열."""
    val = (val or "").strip()
    if not val or "/" in val or "\\" in val or ".." in val:
        return ""
    return val


def user_dir(user_id: str) -> str:
    uid = safe_id(user_id) or "_shared"
    d = os.path.join(AGENTS_ROOT, uid)
    os.makedirs(d, exist_ok=True)
    return d


def atomic_write(path: str, content: str) -> None:
    """tempfile 작성 후 os.replace 로 원자 교체."""
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def read_text(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def read_json(path: str, default):
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path: str, obj) -> None:
    atomic_write(path, json.dumps(obj, ensure_ascii=False, indent=2))


# ── 인젝션 방어 ──
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+|the\s+)?(previous|prior|above)",
    r"disregard\s+.{0,20}(instruction|prompt|rule)",
    r"system\s*prompt",
    r"you\s+are\s+now\b",
    r"new\s+instructions?\s*:",
    r"<\s*\|.*\|\s*>",          # 채팅 템플릿 토큰
    r"</?(system|assistant|user)>",
    r"\bBEGIN\s+SYSTEM\b",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def looks_injected(text: str) -> bool:
    return bool(_INJECTION_RE.search(text or ""))
