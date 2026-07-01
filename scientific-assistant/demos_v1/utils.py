"""
demos_v1/utils.py - Shared state, global variables, and upload utilities
"""
import os
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(BASE_DIR, "scientific-skills")
TOKEN_FILE = os.path.join(BASE_DIR, "TOKEN.TXT")
PROMPTS_DIR = os.path.join(BASE_DIR, "saved-prompts")
os.makedirs(PROMPTS_DIR, exist_ok=True)

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# GGUF 모델 (llama-cpp-python)
gguf_model = None  # Llama 인스턴스 (하위호환: 단일스킬 경로)
gguf_loaded_path = None  # 현재 로드된 모델 파일 경로

# 업로드된 CSV 데이터
# ⚠️ 과거엔 서버 전역 1칸이라 다중 사용자(회사)에서 서로 첨부를 덮어쓰는 사고.
#   이제 user_id 별 슬롯(csv_slot)으로 분리. 비로그인/레거시는 기존 전역을 그대로 사용(하위호환).
uploaded_csv_data = {
    "filename": "",
    "headers": [],
    "rows": [],
    "summary": "",
    "raw_preview": "",
}
uploaded_csv_by_user = {}  # user_id -> {filename, headers, rows, summary, raw_preview}


def csv_slot(user_id=None):
    """user_id 별 첨부 CSV 슬롯. 빈 ID(비로그인)는 기존 전역(uploaded_csv_data) — 집 단독사용 호환."""
    uid = str(user_id or "").strip()
    if not uid:
        return uploaded_csv_data
    return uploaded_csv_by_user.setdefault(uid, {
        "filename": "", "headers": [], "rows": [], "summary": "", "raw_preview": "",
    })

# 업로드된 파일 (CSV 외 범용)
# ⚠️ 과거엔 전역 1칸이라 모든 사용자·앱(데모스/개인에이전트)이 서로 파일을 공유.
#   이제 scope 별 슬롯(files_slot)으로 분리. 빈 scope(레거시)는 기존 전역을 그대로 사용.
uploaded_files = []  # [{filename, type, size, summary, content_preview}]  (레거시/빈 scope)
uploaded_files_by_scope = {}  # scope -> [ ... ]


def files_slot(scope=None):
    """scope 별 업로드 파일 목록. 빈 scope(비로그인/레거시)는 기존 전역(uploaded_files)."""
    key = str(scope or "").strip()
    if not key:
        return uploaded_files
    return uploaded_files_by_scope.setdefault(key, [])

# 응답 중지 플래그
chat_stop_flag = {"stop": False}

# 하네스 브릿지 연결 (스킬 레지스트리, 세션 저장, 라우팅 강화)
try:
    from harness_bridge import init_harness, register_harness_routes, log_event, save_chat_session
    HARNESS_AVAILABLE = True
except ImportError:
    HARNESS_AVAILABLE = False
