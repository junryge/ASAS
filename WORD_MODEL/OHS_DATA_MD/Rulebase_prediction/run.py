# -*- coding: utf-8 -*-
"""
M16A HUBROOM 수집 + 예측 동시 실행
- 수집기 스레드 시작 (백그라운드 데몬)
- 0.5초 뒤 예측기 watch 시작 (메인)
- Ctrl+C 한 번으로 같이 종료
"""

import importlib.util
import threading
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def load_module(name: str, filename: str):
    """한글 파일명도 import 가능하게 importlib로 로드."""
    path = BASE_DIR / filename
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# 두 모듈 로드 (파일명은 실제 파일명에 맞게)
collector = load_module("collector", "aws_idc_realtime_collector.py")
predictor = load_module("predictor", "3단계_룰베이스_사건단위.py")


# 수집기 (백그라운드 데몬 — 메인 종료 시 같이 죽음)
threading.Thread(target=collector.main, daemon=True).start()

# 0.5초 후 예측기 watch (메인 스레드)
time.sleep(0.5)

# 예측기 watch — 기본 경로/로거 자동 사용
out_dir = predictor.DEFAULT_OUTPUT_DIR
out_dir.mkdir(parents=True, exist_ok=True)
logger = predictor.setup_logger(out_dir)
predictor.run_watch(predictor.DEFAULT_INPUT_CSV, out_dir, logger)
