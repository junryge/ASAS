"""
demos_v1/hcpp_token.py — HCPP-PRD JWT 파싱 유틸 (파일 IO 없음)

토큰은 UI(브라우저 sessionStorage) 가 보관하고 매 요청마다 전송.
서버는 JWT 검증용 파싱 함수만 제공.
"""
import base64
import json
import time


def parse_jwt_exp(token: str) -> dict:
    """JWT 페이로드에서 exp 파싱. 실패하면 exp 없이 반환."""
    if not token:
        return {"valid_jwt": False, "has_token": False}
    token = token.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {"valid_jwt": False, "has_token": True}
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = payload.get("exp", 0)
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


def clean_token(token: str) -> str:
    """Bearer prefix 제거하고 토큰만 반환."""
    if not token:
        return ""
    token = token.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token
