"""
hermes/config.py — 저장 경로 설정 (포터블)

데이터 저장 위치:
  - 환경변수 HERMES_DATA_DIR 가 있으면 그것
  - 없으면 현재 작업 폴더의 ./hermes_data
구조: <HERMES_DATA_DIR>/agents/<user_id>/
"""
from __future__ import annotations
import os

HERMES_DATA_DIR = os.environ.get("HERMES_DATA_DIR") or os.path.join(os.getcwd(), "hermes_data")
AGENTS_ROOT = os.path.join(HERMES_DATA_DIR, "agents")

MAX_STORE_CHARS = 6000      # MEMORY/USER 저장소당 상한
ITEM_SEP = "§"              # 항목 구분자

# 백그라운드 리뷰 카운터 임계
TURN_THRESHOLD = 10
SKILL_THRESHOLD = 5
