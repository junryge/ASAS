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

# 업로드된 CSV 데이터 (세션별 - 단순 메모리 저장)
uploaded_csv_data = {
    "filename": "",
    "headers": [],
    "rows": [],
    "summary": "",
    "raw_preview": "",
}

# 업로드된 파일 (CSV 외 범용)
uploaded_files = []  # [{filename, type, size, summary, content_preview}]

# 응답 중지 플래그
chat_stop_flag = {"stop": False}

# 하네스 브릿지 연결 (스킬 레지스트리, 세션 저장, 라우팅 강화)
try:
    from harness_bridge import init_harness, register_harness_routes, log_event, save_chat_session
    HARNESS_AVAILABLE = True
except ImportError:
    HARNESS_AVAILABLE = False
