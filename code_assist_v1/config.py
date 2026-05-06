"""
code_assist_v1/config.py - 코딩 어시스턴트 플랫폼 설정 (demos_v1 와 독립)

- TOKEN.TXT, api_config.json, MODEL_GGUF/ 모두 code_assist_v1/ 안에서 자체 처리
- skills/, knowledge/, workspace/ 모두 평면 구조 (user_id 폴더 없음)
"""
from __future__ import annotations
import os
import sys

# Windows 콘솔 cp949 → utf-8 강제
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    for _name in ("stdout", "stderr"):
        try:
            getattr(sys, _name).reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass

# ── 경로 ──
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(_THIS_DIR)  # 시드 시 scientific-skills 참조용

if os.path.dirname(_THIS_DIR) not in sys.path:
    sys.path.insert(0, os.path.dirname(_THIS_DIR))

PKG_DIR = _THIS_DIR
STATIC_DIR = os.path.join(PKG_DIR, "static")
SKILLS_DIR = os.path.join(PKG_DIR, "skills")
KNOWLEDGE_DIR = os.path.join(PKG_DIR, "knowledge")
SESSIONS_DIR = os.path.join(PKG_DIR, "sessions")
WORKSPACE_DIR = os.path.join(PKG_DIR, "workspace")
SKILL_WHITELIST_JSON = os.path.join(PKG_DIR, "skill_whitelist.json")
TOKEN_FILE = os.path.join(PKG_DIR, "TOKEN.TXT")
MODEL_GGUF_DIR = os.path.join(PKG_DIR, "MODEL_GGUF")

for _d in (SKILLS_DIR, KNOWLEDGE_DIR, SESSIONS_DIR, WORKSPACE_DIR, MODEL_GGUF_DIR):
    os.makedirs(_d, exist_ok=True)


# ── TOKEN 로드 ──
def load_token() -> str:
    if not os.path.isfile(TOKEN_FILE):
        return ""
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8-sig") as f:
            token = f.read().strip()
    except Exception as e:
        print(f"  ⚠️  TOKEN.TXT 읽기 실패: {e}")
        return ""
    if not token:
        return ""
    try:
        token.encode("ascii")
    except UnicodeEncodeError:
        print(f"  ⚠️  TOKEN.TXT 비-ASCII 문자")
        return ""
    return token


API_TOKEN = load_token()


# ── 모델 / GGUF 설정 ──
from code_assist_v1.models import (
    MODEL_REGISTRY,
    ENV_CONFIG,
    ENV_TO_REGISTRY,
    TOKEN_SETTINGS,
    DEFAULT_MODEL_PRIORITY,
    MAX_POOL_SIZE,
    VRAM_BUDGET_GB,
    GGUF_DEFAULT_N_CTX,
    GGUF_DEFAULT_N_GPU_LAYERS,
    GGUF_DEFAULT_N_BATCH,
)


# ── 동작 설정 ──
PORT = int(os.environ.get("CODE_ASSIST_PORT", "10010"))

DEFAULT_N_CTX = TOKEN_SETTINGS.get("default_n_ctx", 32768)
MAX_AGENT_TOKENS = TOKEN_SETTINGS.get("agent_max_tokens", 8192)
MAX_HISTORY_TURNS = 12
MAX_WORKSPACE_FILE_CHARS = 4000
MAX_WORKSPACE_TOTAL_CHARS = 16000
MAX_KNOWLEDGE_INJECT_CHARS = 12000

MAX_UPLOAD_MB = 50
ALLOWED_UPLOAD_EXT = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".vue", ".svelte",
    ".html", ".css", ".scss", ".sass", ".less",
    ".json", ".yaml", ".yml", ".toml", ".xml",
    ".md", ".txt", ".csv", ".tsv",
    ".java", ".kt", ".c", ".cpp", ".h", ".hpp", ".cs", ".go", ".rs", ".rb", ".php",
    ".sh", ".bash", ".zsh", ".ps1", ".bat",
    ".sql", ".dockerfile",
    ".pdf", ".docx", ".xlsx", ".pptx",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
    ".ipynb",
}


def get_default_model() -> str:
    for mid in DEFAULT_MODEL_PRIORITY:
        if mid in MODEL_REGISTRY:
            return mid
    if MODEL_REGISTRY:
        return next(iter(MODEL_REGISTRY.keys()))
    return ""
