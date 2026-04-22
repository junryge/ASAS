"""
demos_v1/hcpp_token.py — HCPP-PRD JWT 토큰 서버 메모리 보관 (파일 IO 없음)

서버 프로세스 안의 모듈 변수로 보관.
UI 에서 JWT 붙여넣으면 POST /api/config/hcpp-token 으로 서버에 저장,
이후 routes_chat.py 가 HCPP_* 모델 요청 시 여기서 읽어 사용.

앱 재시작하면 토큰 소실 → 다시 붙여넣기 필요 (사용자 2시간 교체 패턴에 맞음).
"""
import base64
import json
import time
import threading


_LOCK = threading.Lock()
_CURRENT_TOKEN: str = ""   # 현재 메모리 보관 중인 JWT
_CURRENT_EXP: int = 0      # JWT exp (초 epoch). 0 이면 미파싱.


def clean_token(token: str) -> str:
    """Bearer 접두어 제거."""
    if not token:
        return ""
    token = token.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token


def parse_jwt_exp(token: str) -> dict:
    """JWT payload 에서 exp 파싱. 형식 문제 시 has_token 만 true."""
    if not token:
        return {"valid_jwt": False, "has_token": False}
    token = clean_token(token)
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {"valid_jwt": False, "has_token": True}
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = int(payload.get("exp", 0))
        now = int(time.time())
        remaining = exp - now
        return {
            "has_token": True,
            "valid_jwt": True,
            "exp": exp,
            "remaining_seconds": remaining,
            "remaining_minutes": max(0, remaining // 60),
            "expired": remaining <= 0,
        }
    except Exception as e:
        return {"valid_jwt": False, "has_token": True, "parse_error": str(e)}


def set_hcpp_token(token: str) -> dict:
    """사용자가 UI 에서 붙여넣은 JWT 를 서버 메모리에 저장."""
    global _CURRENT_TOKEN, _CURRENT_EXP
    token = clean_token(token)
    info = parse_jwt_exp(token)
    with _LOCK:
        _CURRENT_TOKEN = token
        _CURRENT_EXP = info.get("exp", 0) if info.get("valid_jwt") else 0
    info["stored"] = True
    return info


def get_hcpp_token() -> str:
    """routes_chat.py 에서 호출. 현재 보관 중인 JWT 반환."""
    with _LOCK:
        return _CURRENT_TOKEN


def get_hcpp_status() -> dict:
    """UI 가 주기적으로 호출해서 남은 시간 표시."""
    with _LOCK:
        tok = _CURRENT_TOKEN
        exp = _CURRENT_EXP
    if not tok:
        return {"has_token": False}
    if not exp:
        return {"has_token": True, "valid_jwt": False}
    now = int(time.time())
    remaining = exp - now
    return {
        "has_token": True,
        "valid_jwt": True,
        "exp": exp,
        "remaining_seconds": remaining,
        "remaining_minutes": max(0, remaining // 60),
        "expired": remaining <= 0,
    }


def clear_hcpp_token() -> dict:
    """토큰 지우기 (UI 로그아웃용)."""
    global _CURRENT_TOKEN, _CURRENT_EXP
    with _LOCK:
        _CURRENT_TOKEN = ""
        _CURRENT_EXP = 0
    return {"cleared": True}
