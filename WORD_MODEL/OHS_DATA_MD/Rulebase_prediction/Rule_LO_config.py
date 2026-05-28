# -*- coding: utf-8 -*-
"""
Rule_LO_config.py — Logpresso 업로더 설정
=========================================
hubroom_predictor v4.1 발동이벤트 → Logpresso 테이블 적재 설정.
변경할 때 이 파일만 수정. Rule_LO.py 는 건드릴 필요 없음.
"""

# ============================================================
# Logpresso 연결 정보
# ============================================================
LOGPRESSO_HOST     = "logpresso.example.com"   # ← 실제 호스트로 변경
LOGPRESSO_PORT     = 8888                       # 클라이언트(8888) / HTTP(80,443)
LOGPRESSO_LOGIN    = "admin"                    # 계정
LOGPRESSO_PASSWORD = "admin"                    # 비밀번호
LOGPRESSO_USE_SSL  = False                      # TLS 사용 여부

# ============================================================
# HTTP REST API (클라이언트 실패 시 폴백)
# ============================================================
LOGPRESSO_HTTP_URL = "http://logpresso.example.com/api/v1/storage/insert"
LOGPRESSO_HTTP_TIMEOUT = 5   # 초

# ============================================================
# 적재 테이블 / 하드코딩 필드
# ============================================================
LOGPRESSO_TABLE = "test_table3"   # 저장 테이블명
FILE_LABEL      = "Rule_system"   # 'file' 컬럼 하드코딩 값

# ============================================================
# 동작 옵션
# ============================================================
ENABLED          = True    # False 면 로그프레소 적재 안 함 (CSV만)
ASYNC_UPLOAD     = True    # True: 백그라운드 큐로 비동기 (predictor 지연 방지)
QUEUE_MAX_SIZE   = 10000   # 비동기 큐 최대 크기 (초과 시 오래된 것 폐기)
RETRY_ON_FAIL    = 3       # 실패 시 재시도 횟수
RETRY_BACKOFF    = 1.0     # 재시도 간격 (초, 지수증가)
LOG_EVERY_N      = 60      # N행마다 로그 출력 (0=항상)
FAIL_SILENT      = True    # 적재 실패해도 예외 던지지 않음 (predictor 보호)

# ============================================================
# 연결 우선순위
# ============================================================
# True : Logpresso Python 클라이언트 먼저 시도, 실패 시 HTTP
# False: HTTP 만 사용
PREFER_CLIENT = True
