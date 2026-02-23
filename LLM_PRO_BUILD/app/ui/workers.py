#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QThread 워커 - LLM/Aider/Nanobot/Ralph 호출을 백그라운드에서 실행
"""

import asyncio
import logging
import requests
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


class LLMWorker(QThread):
    """LLM 호출 워커 (자기교정 옵션 + 취소 지원)"""
    finished = Signal(dict)
    progress = Signal(str)

    def __init__(self, llm_provider, prompt, system_prompt, use_sc=False, parent=None):
        super().__init__(parent)
        self.llm_provider = llm_provider
        self.prompt = prompt
        self.system_prompt = system_prompt
        self.use_sc = use_sc
        self._cancelled = False
        self._session = requests.Session()  # 취소 가능한 세션

    def run(self):
        try:
            if self._cancelled:
                self.finished.emit({"success": False, "answer": "취소됨"})
                return

            if self.use_sc:
                self.progress.emit("자기교정 모드 실행 중...")
                from app.core.self_correction import run_self_correction
                result = run_self_correction(self.llm_provider, self.prompt, self.system_prompt)

                if self._cancelled:
                    self.finished.emit({"success": False, "answer": "취소됨"})
                    return

                if result["success"]:
                    self.finished.emit({
                        "success": True,
                        "answer": result["answer"],
                        "use_sc": True,
                        "retry_count": result["retry_count"],
                        "is_valid": result["is_valid"],
                        "review": result.get("review", "")
                    })
                else:
                    self.finished.emit({"success": False, "answer": result.get("error", "오류 발생")})
            else:
                self.progress.emit("LLM 호출 중...")
                result = self.llm_provider.call(
                    self.prompt, self.system_prompt, session=self._session
                )

                if self._cancelled:
                    self.finished.emit({"success": False, "answer": "취소됨"})
                    return

                if result["success"]:
                    self.finished.emit({
                        "success": True,
                        "answer": result["content"],
                        "use_sc": False
                    })
                else:
                    self.finished.emit({"success": False, "answer": result.get("error", "오류 발생")})
        except Exception as e:
            if self._cancelled:
                self.finished.emit({"success": False, "answer": "취소됨"})
            else:
                self.finished.emit({"success": False, "answer": str(e)})

    def cancel(self):
        """작업 취소 요청 - 진행 중인 HTTP 연결도 즉시 종료"""
        self._cancelled = True
        try:
            self._session.close()  # 진행 중인 HTTP 요청 즉시 중단
        except Exception:
            pass
        logger.info("LLM 워커 취소 요청 (HTTP 세션 종료)")


class AiderWorker(QThread):
    """Aider 채팅 워커 (수정/분석 모드 지원)"""
    finished = Signal(dict)
    progress = Signal(str)

    def __init__(self, bridge, project_id, message, files=None, mode="modify", parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.project_id = project_id
        self.message = message
        self.files = files
        self.mode = mode  # "modify" 또는 "analyze"

    def run(self):
        try:
            action = "코드 분석 중..." if self.mode == "analyze" else "코드 수정 중..."
            self.progress.emit(action)
            result = self.bridge.chat(self.project_id, self.message, self.files, mode=self.mode)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({"success": False, "error": str(e)})


class NanobotWorker(QThread):
    """마기(MAGI) Nanobot 에이전트 워커"""
    finished = Signal(dict)
    progress = Signal(str)

    def __init__(self, nanobot_manager, message, session_id="desktop:default", parent=None):
        super().__init__(parent)
        self.nanobot_manager = nanobot_manager
        self.message = message
        self.session_id = session_id

    def run(self):
        try:
            self.progress.emit("마기 에이전트 처리 중...")
            # async 함수를 QThread 전용 이벤트 루프에서 실행
            # 주의: set_event_loop 제거 → 메인 스레드 이벤트 루프 충돌 방지
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    self.nanobot_manager.process(self.message, self.session_id)
                )
                self.finished.emit(result)
            finally:
                # 미완료 태스크 정리 후 루프 종료
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                loop.close()
        except Exception as e:
            logger.error(f"Nanobot 워커 오류: {e}")
            self.finished.emit({
                "success": False,
                "response": str(e),
                "steps": [],
                "session_id": self.session_id,
            })


class RalphWorker(QThread):
    """Ralph 스타일 자율 에이전트 루프 워커"""
    finished = Signal(dict)
    progress = Signal(str)
    iteration_done = Signal(int, str)  # (iteration_num, status_message)

    def __init__(self, ralph_loop, project_id, task_description, max_iterations=5, parent=None):
        super().__init__(parent)
        self.ralph_loop = ralph_loop
        self.project_id = project_id
        self.task_description = task_description
        self.max_iterations = max_iterations
        self._cancelled = False

    def run(self):
        try:
            self.progress.emit(f"Ralph 자율 루프 시작 (최대 {self.max_iterations}회)...")
            result = self.ralph_loop.run(
                project_id=self.project_id,
                task=self.task_description,
                max_iterations=self.max_iterations,
                progress_callback=self._on_progress,
                cancel_check=lambda: self._cancelled
            )
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Ralph 워커 오류: {e}")
            self.finished.emit({"success": False, "error": str(e), "iterations": 0})

    def _on_progress(self, iteration: int, message: str):
        self.iteration_done.emit(iteration, message)
        self.progress.emit(f"[반복 {iteration}] {message}")

    def cancel(self):
        self._cancelled = True
        self.progress.emit("취소 요청됨...")


class ModelLoadWorker(QThread):
    """GGUF 모델 로딩 워커"""
    finished = Signal(bool, str)
    progress = Signal(str)

    def __init__(self, llm_provider, model_key=None, parent=None):
        super().__init__(parent)
        self.llm_provider = llm_provider
        self.model_key = model_key

    def run(self):
        try:
            if self.model_key:
                self.progress.emit(f"모델 전환 중: {self.model_key}...")
                success = self.llm_provider.switch_model(self.model_key)
                msg = "모델 전환 완료" if success else "모델 전환 실패"
            else:
                self.progress.emit("로컬 모델 로딩 중...")
                success = self.llm_provider.load_local_model()
                msg = "모델 로드 완료" if success else "모델 로드 실패"
            self.finished.emit(success, msg)
        except Exception as e:
            self.finished.emit(False, str(e))
