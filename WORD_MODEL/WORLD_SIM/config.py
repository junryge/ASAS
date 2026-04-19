#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config.py - OHT 월드모델 시뮬레이션 설정
"""

import os
import pathlib

# ============================================================
# 경로 설정
# ============================================================
_SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
_PROJECT_DIR = _SCRIPT_DIR.parent  # OHT_WORDMODEL

# 데이터 폴더
DATA_DIR = _PROJECT_DIR / "OHS_DATA_MD"
MAP_DIR = _PROJECT_DIR / "OHT_MAP"

# 레이아웃/설정 파일
LAYOUT_CACHE_JSON = MAP_DIR / "layout_cache.json"
FAB_CONFIG_JSON = MAP_DIR / "fab_config.json"
HID_ZONE_MASTER_CSV = MAP_DIR / "MAP" / "M14A" / "HID_Zone_Master_M14A_A.csv"

# 날짜별 데이터 폴더 — 자동 스캔
def _scan_data_dates():
    """DATA_DIR 하위 폴더를 자동 스캔하여 날짜별 데이터 설정 생성"""
    import os, glob, re

    dates = {}
    if not DATA_DIR.exists():
        return dates

    for folder in sorted(DATA_DIR.iterdir()):
        if not folder.is_dir():
            continue
        # 폴더명이 날짜 형식인지 (숫자 8자리)
        name = folder.name
        if not re.match(r'^\d{6,8}$', name):
            continue

        files = os.listdir(str(folder))
        if not files:
            continue

        def _find(pattern):
            """패턴에 맞는 첫 번째 파일명 반환"""
            for f in files:
                if pattern.lower() in f.lower():
                    return f
            return None

        # 파일 자동 매칭
        oht_raw = _find('OHT_DATA') or _find('OHT_' + name) or _find('oht_raw')
        hid_inout = _find('HID_INOUT')
        rail_cut = _find('RAIL_CUT')
        star = _find('STAR_OHT') or _find('컬럼수집')
        ts_resource = _find('ts_resource')
        oht_data_m14a = _find('oht_data_m14a')
        oht_time_avg = _find('oht_time_avg')

        # OHT raw가 없으면 스킵
        if not oht_raw:
            continue

        # CSV 파일 수 카운트
        csv_count = sum(1 for f in files if f.lower().endswith('.csv'))

        dates[name] = {
            "dir": folder,
            "oht_raw": oht_raw,
            "hid_inout": hid_inout,
            "rail_cut": rail_cut,
            "star": star,
            "ts_resource": ts_resource,
            "oht_data_m14a": oht_data_m14a,
            "oht_time_avg": oht_time_avg,
            "time_range": ("00:00:00", "23:59:59"),
            "description": f"{name[:4]}-{name[4:6]}-{name[6:8]} ({csv_count}개 CSV)",
        }

    return dates

DATA_DATES = _scan_data_dates()

# ============================================================
# OHT 시스템 상수 (MD 문서 기반 검증된 값)
# ============================================================

# 차량
VEHICLE_COUNT_M14A = 450
VEHICLE_COUNT_TOTAL = 1033  # V-Vehicle (R-Vehicle 29대 별도)

# TAT (Turn Around Time) - ts_resource 분석 결과
TAT_AVERAGE_MIN = 2.88      # 평균 2.88분
TAT_MEDIAN_MIN = 2.57       # 중앙값 2.57분
TAT_UNDER_3MIN_PCT = 61.5   # 3분 이내 완료 비율
TAT_UNDER_5MIN_PCT = 91.7   # 5분 이내 완료 비율

# 물동량
THROUGHPUT_PER_HOUR = 20000  # 시간당 ~20,000건 (주야간 동일)

# 큐
QUEUE_NORMAL_RANGE = (1200, 1400)  # 정상 큐 범위
QUEUE_AVG = 1249

# OBS (장애물 정지)
OBS_NORMAL_RANGE = (120, 160)   # 정상 OBS 범위
OBS_WARNING_THRESHOLD = 180      # 주의 기준
OBS_DANGER_THRESHOLD = 200       # 위험 기준
OBS_DEADLOCK_THRESHOLD = 300     # 데드락 기준

# 가동률/적재율
UTILIZATION_PCT = 82.3
LOADED_PCT = 62.1
OBS_BZ_STOP_PCT = 14.3

# LineCost 가중치 (Dijkstra 아키텍처)
LINECOST_IDLE_VHL_PENALTY = 3000    # 놀고 있는 차량 1대당 +3,000ms
LINECOST_WORK_VHL_PENALTY = 5000    # 일하는 차량 1대당 +5,000ms
LINECOST_WORK_DEST_PENALTY = 5000   # 대기 작업 1건당 +5,000ms

# EMA 속도 갱신
EMA_OLD_WEIGHT = 0.6
EMA_NEW_WEIGHT = 0.4

# HID Zone
HID_ZONE_COUNT = 182
HID_VEHICLE_MAX = 37
HID_VEHICLE_PRECAUTION = 35
HID_CONGESTION_THRESHOLD_PCT = 70  # 70% 이상이면 혼잡

# 시뮬레이션
SIM_STEP_SEC = 5.0          # 시뮬레이션 스텝 (초)
DEFAULT_VELOCITY = 180.0     # 기본 차량 속도 (m/min)
PREDICTION_HORIZONS = [600, 1200]  # 예측 시간 (초): 10분, 20분

# OHT 메시지 상태 코드
STATE_NAMES = {
    1: "RUN",
    2: "STOP",
    3: "ACCEL",
    4: "DECEL",
    5: "CURVE",
    6: "OBS_BZ_STOP",
    7: "JAM",
    8: "HT_STOP",
    9: "E84_TIMEOUT",
}

# 서버 설정
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 10005
WS_INTERVAL = 0.5  # WebSocket 전송 간격 (초)
