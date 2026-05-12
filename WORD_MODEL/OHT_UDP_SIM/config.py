# -*- coding: utf-8 -*-
"""OHT_UDP_SIM 설정"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# ── UDP 포트 ────────────────────────────────────────
UDP_PORT_M14A    = 3710
UDP_PORT_M16A_BR = 3750
UDP_HOST         = "127.0.0.1"     # 송수신 동일 호스트 (개발용)
UDP_BUFFER_SIZE  = 65535

# ── HTTP 포트 ───────────────────────────────────────
HTTP_PORT_MAIN          = 11000    # main 수신 UI
HTTP_PORT_SENDER_M14A   = 11010    # M14A 송신 제어 UI
HTTP_PORT_SENDER_M16A_BR= 11020    # M16A_BR 송신 제어 UI

# ── 데이터 파일 (프로젝트 폴더 내부 우선, 없으면 상위 탐색) ───
def _find_csv(fab_folder: str, filename: str) -> str:
    candidates = [
        PROJECT_ROOT / fab_folder / filename,
        PROJECT_ROOT.parent / fab_folder / filename,                       # WORD_MODEL/M14A_DATA/...
        PROJECT_ROOT.parent.parent / fab_folder / filename,                # ASAS/M14A_DATA/...
        PROJECT_ROOT.parent / "OHS_DATA_MD" / fab_folder / filename,       # WORD_MODEL/OHS_DATA_MD/M14A_DATA/...
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    # 없을 때는 첫번째 후보 (자연스러운 기본 위치) 반환
    return str(candidates[0])

CSV_FILE_M14A    = _find_csv("M14A_DATA",    "LOGPRESSO_OHT_DATA_20260429.CSV")
CSV_FILE_M16A_BR = _find_csv("M16A_BR_DATA", "LOGPRESSO_OHT_DATA_20260429.CSV")

# ── 재생 시간창 (KST) ─────────────────────────────────
# 빈 문자열 = 필터 안 함 (CSV 전체 송신)
# 필요 시 환경변수 REPLAY_START / REPLAY_END 또는 직접 지정.
REPLAY_START = os.environ.get("REPLAY_START", "")
REPLAY_END   = os.environ.get("REPLAY_END",   "")

# ── 재생 속도 ────────────────────────────────────────
# 1.0  = 실시간   |   60.0 = 1분에 1시간 압축
DEFAULT_SPEED   = 1.0
TICK_INTERVAL_S = 1.0      # 송신 tick 간격 (초)

# ── 송신 패킷 포맷 ──────────────────────────────────
# 'raw_line' = LOGPRESSO line 컬럼만 (newline 구분) — 운영 포맷 호환 (기본)
# 'json'     = {fab, ts, count, rows[]} (디버깅용, 메타 포함)
# 'csv'      = CSV 형태 (헤더 포함)
PACKET_FORMAT = os.environ.get("PACKET_FORMAT", "raw_line")
# 한 UDP 패킷에 담을 row 수 (1 그룹 = 같은 _time row 묶음).
# 200 = 같은 1초 row 들을 한 패킷에 합쳐 송신 (기본, _time 단위 송신)
MAX_ROWS_PER_PACKET = int(os.environ.get("MAX_ROWS_PER_PACKET", 200))

# ── 환경변수 override ───────────────────────────────
UDP_PORT_M14A    = int(os.environ.get("UDP_PORT_M14A",    UDP_PORT_M14A))
UDP_PORT_M16A_BR = int(os.environ.get("UDP_PORT_M16A_BR", UDP_PORT_M16A_BR))
DEFAULT_SPEED    = float(os.environ.get("REPLAY_SPEED",   DEFAULT_SPEED))
