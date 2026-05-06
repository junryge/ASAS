# -*- coding: utf-8 -*-
"""UDP_SIM 설정 — 실시간 UDP 수신 + 차량 위치 지도 표시"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# ── UDP 수신 포트 (OHT_UDP_SIM/sender.py 와 일치) ──
UDP_HOST         = os.environ.get("UDP_HOST", "0.0.0.0")
UDP_PORT_M14A    = int(os.environ.get("UDP_PORT_M14A",    3710))
UDP_PORT_M16A_BR = int(os.environ.get("UDP_PORT_M16A_BR", 3750))
UDP_BUFFER_SIZE  = 65535

# ── HTTP/WS 서버 ──
HTTP_HOST = os.environ.get("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.environ.get("HTTP_PORT", 12000))

# ── 레이아웃 캐시 ──
# 우선순위: ① UDP_SIM/cache/ (zip 내장)  ② WORD_MODEL/OHT_MAP/cache/  ③ ENV override
def _resolve_layout(name: str) -> Path:
    candidates = [
        PROJECT_ROOT / "cache" / name,                                 # zip 내장 (Windows 친화)
        PROJECT_ROOT.parent / "OHT_MAP" / "cache" / name,              # 원본 위치
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]   # 첫번째 후보 (없어도)

LAYOUT_FILE_M14A    = Path(os.environ.get("LAYOUT_M14A",    str(_resolve_layout("M14A_A_layout_cache.json"))))
LAYOUT_FILE_M16A_BR = Path(os.environ.get("LAYOUT_M16A_BR", str(_resolve_layout("M16A_BR_layout_cache.json"))))

# ── 송신 주기 (브라우저로 차량 push) ──
WS_PUSH_INTERVAL_S = 0.25      # 4 Hz

# ── 차량 stale 판정 (마지막 갱신 후) ──
VEHICLE_STALE_SEC = 10.0
