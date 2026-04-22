"""
demos_v1/hcpp_token.py — HCPP-PRD JWT 토큰 로드/저장 (수동 교체)

사용자가 UI 에 JWT 붙여넣으면 HCPP_TOKEN.TXT 에 저장되고,
routes_chat.py 가 HCPP-PRD 모델 요청 시 매번 이 파일에서 최신 토큰 읽음.
앱 재시작 없이 토큰 교체 반영.
"""
import os
import base64
import json
import time

from demos_v1.models import BASE_DIR

HCPP_TOKEN_FILE = os.path.join(os.path.dirname(BASE_DIR), "HCPP_TOKEN.TXT")


def load_hcpp_token() -> str:
    """HCPP_TOKEN.TXT 에서 현재 토큰 읽음. 없으면 빈 문자열."""
    try:
        if os.path.isfile(HCPP_TOKEN_FILE):
            with open(HCPP_TOKEN_FILE, "r", encoding="utf-8") as f:
                tok = f.read().strip()
                # "Bearer " prefix 제거 (사용자가 헤더 통째 복붙 가능성)
                if tok.lower().startswith("bearer "):
                    tok = tok[7:].strip()
                return tok
    except Exception as e:
        print(f"[HCPP] 토큰 로드 실패: {e}")
    return ""


def save_hcpp_token(token: str) -> dict:
    """사용자가 붙여넣은 JWT 를 파일에 저장. exp 정보 반환."""
    if not token:
        return {"saved": False, "error": "empty token"}
    token = token.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    try:
        with open(HCPP_TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(token)
        info = parse_jwt_exp(token)
        return {"saved": True, "path": HCPP_TOKEN_FILE, **info}
    except Exception as e:
        return {"saved": False, "error": str(e)}


def parse_jwt_exp(token: str) -> dict:
    """JWT 페이로드에서 exp 파싱. 실패하면 exp 없이 반환."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {"valid_jwt": False}
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = payload.get("exp", 0)
        now = int(time.time())
        remaining = exp - now
        return {
            "valid_jwt": True,
            "exp": exp,
            "remaining_seconds": remaining,
            "remaining_minutes": max(0, remaining // 60),
            "expired": remaining <= 0,
        }
    except Exception as e:
        return {"valid_jwt": False, "parse_error": str(e)}


def get_hcpp_status() -> dict:
    """현재 저장된 토큰의 상태 조회. UI 표시용."""
    tok = load_hcpp_token()
    if not tok:
        return {"has_token": False}
    info = parse_jwt_exp(tok)
    return {"has_token": True, **info}
