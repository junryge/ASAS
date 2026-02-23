#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nomos LLM Desktop App - 진입점
코드 개발 / 수정 / 데이터 분석 데스크탑 애플리케이션
Nanobot 에이전트 + Ralph 자율 루프 통합
"""

import sys
import os
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# 앱 경로를 PYTHONPATH에 추가
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)


def main():
    """앱 메인 함수"""
    logger.info("=" * 50)
    logger.info("Nomos LLM Desktop v1.1 시작")
    logger.info(f"Python: {sys.executable} (v{sys.version.split()[0]})")
    logger.info("=" * 50)

    # 1. 설정 로드
    from app.core.config import AppConfig
    config = AppConfig()

    # 2. API 토큰 로드 시도
    if config.load_token():
        config.llm_mode = "api"
        logger.info(f"API 모드: {config.ENV_CONFIG[config.env_mode]['name']}")
    else:
        logger.warning("API 토큰 없음 - 로컬 GGUF 모드로 시작")
        config.llm_mode = "local"
        config.env_mode = "local"

    # 3. LLM Provider 초기화
    from app.core.llm_provider import LLMProvider
    provider = LLMProvider(config)

    # 4. Aider Bridge 초기화 (모델 로드 전에 가능)
    from app.aider.bridge import AiderBridge
    bridge = AiderBridge(config, provider)

    # 5. Nanobot (마기 에이전트) 초기화
    nanobot_manager = None
    try:
        from app.agent.nanobot_manager import NanobotManager
        nanobot_manager = NanobotManager(config, provider)
        logger.info(f"마기(MAGI) 에이전트 초기화 - nanobot 사용 가능: {nanobot_manager.available}")
    except Exception as e:
        logger.warning(f"마기 에이전트 초기화 실패 (계속 진행): {e}")

    # 6. Ralph 자율 루프 초기화
    ralph_loop = None
    try:
        from app.agent.ralph_loop import RalphLoop
        ralph_loop = RalphLoop(config, provider, bridge, nanobot_manager=nanobot_manager)
        logger.info(f"Ralph 자율 루프 초기화 완료 (마기 협동: {nanobot_manager is not None and nanobot_manager.available})")
    except Exception as e:
        logger.warning(f"Ralph 루프 초기화 실패 (계속 진행): {e}")

    # 7. Qt 앱 실행 — UI 먼저 표시
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon

    app = QApplication(sys.argv)
    app.setApplicationName("Nomos LLM")
    app.setApplicationVersion("1.1")

    # 아이콘 설정 (있으면)
    icon_path = os.path.join(APP_DIR, "magi.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 8. 메인 윈도우 — 모델 로드 전에 화면부터 띄움
    from app.main_window import MainWindow
    window = MainWindow(
        config, provider, bridge,
        nanobot_manager=nanobot_manager,
        ralph_loop=ralph_loop
    )
    window.show()

    logger.info("앱 UI 표시 완료!")
    logger.info(f"모드: {config.llm_mode} | 환경: {config.env_mode}")
    logger.info(f"에이전트: 마기={'OK' if nanobot_manager else '-'} | Ralph={'OK' if ralph_loop else '-'}")

    # 9. 로컬 모드면 모델을 백그라운드에서 로드
    if config.llm_mode == "local":
        logger.info("로컬 GGUF 모델 백그라운드 로딩 시작...")
        from app.ui.workers import ModelLoadWorker
        _model_worker = ModelLoadWorker(provider)

        def _on_bg_model_loaded(success, msg):
            if success:
                logger.info("백그라운드 모델 로드 성공!")
                window._update_status()
                # GGUF 서버 시작 (aider 연동용)
                try:
                    from app.core.gguf_server import GGUFServer
                    window._gguf_server = GGUFServer(provider, port=10002)
                    window._gguf_server.start()
                    logger.info("GGUF 호환 서버 시작 (port 10002)")
                except Exception as e:
                    logger.warning(f"GGUF 서버 시작 실패 (무시): {e}")
            else:
                logger.warning(f"백그라운드 모델 로드 실패: {msg}")
                window._update_status()

        _model_worker.finished.connect(_on_bg_model_loaded)
        _model_worker.progress.connect(lambda t: window.header.update_status(t))
        _model_worker.start()
        # 워커 참조 유지 (GC 방지)
        window._bg_model_worker = _model_worker

    # 10. 이벤트 루프
    exit_code = app.exec()

    # 11. 정리
    if hasattr(window, '_gguf_server') and window._gguf_server:
        window._gguf_server.stop()
    logger.info("앱 종료")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
