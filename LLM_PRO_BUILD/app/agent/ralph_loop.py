#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ralph 스타일 자율 에이전트 루프
- snarktank/ralph에서 영감을 받은 반복 실행 구조
- 각 반복마다 진행 상황을 확인하고 다음 단계를 결정
- 모든 작업이 완료되면 자동 종료
"""

import re
import json
import time
import logging
from pathlib import Path
from typing import Callable, Optional

from app.aider.project_manager import get_project, get_project_files, read_file, save_file
from app.aider.bridge import AiderBridge

logger = logging.getLogger(__name__)


class RalphLoop:
    """Ralph 스타일 자율 반복 에이전트 (마기 협동 모드)

    작업 흐름:
    1. Ralph가 사용자 요청을 하위 작업(스토리)으로 분해 (기획자)
    2. 각 반복마다:
       a. Ralph가 현재 진행 상황 확인
       b. 미완료 작업 선택
       c. 마기(Nanobot)가 도구로 코드 수정 실행 (실행자)
       d. Ralph가 결과 검증
    3. 모든 작업 완료 시 종료

    마기가 없으면 bridge 폴백으로 실행
    """

    PLAN_SYSTEM_PROMPT = """당신은 소프트웨어 개발 프로젝트 매니저입니다.
사용자의 요청을 구체적이고 작은 하위 작업(스토리)으로 분해해주세요.

출력 형식 (JSON):
{
    "stories": [
        {"id": 1, "title": "작업 제목", "description": "구체적 설명", "status": "pending"},
        ...
    ]
}

규칙:
- 각 스토리는 하나의 코드 수정으로 완료할 수 있는 크기로
- 최대 10개 스토리
- description에 수정할 파일이나 기능을 구체적으로 명시
- status는 항상 "pending"으로 시작"""

    CHECK_SYSTEM_PROMPT = """당신은 코드 품질 검토자입니다.
코드 수정 결과를 검토하고 작업 완료 여부를 판단해주세요.

출력 형식 (JSON):
{
    "story_id": 1,
    "passed": true/false,
    "reason": "판단 이유",
    "next_action": "완료 시 비움, 미완료 시 추가 조치 설명"
}

규칙:
- 코드가 정상적으로 수정되었으면 passed: true
- 수정이 불완전하거나 오류가 있으면 passed: false
- next_action에 구체적인 추가 작업 설명"""

    def __init__(self, config, llm_provider, aider_bridge: AiderBridge, nanobot_manager=None):
        self.config = config
        self.llm_provider = llm_provider
        self.bridge = aider_bridge
        self.nanobot_manager = nanobot_manager  # 마기 실행자 (없으면 bridge 폴백)

    def run(self, project_id: str, task: str, max_iterations: int = 5,
            progress_callback: Optional[Callable] = None,
            cancel_check: Optional[Callable] = None) -> dict:
        """자율 루프 실행"""
        t0 = time.time()
        iterations = 0
        all_results = []

        project = get_project(project_id)
        if not project:
            return {"success": False, "error": "프로젝트를 찾을 수 없습니다", "iterations": 0}

        # 1단계: 작업 분해
        if progress_callback:
            progress_callback(0, "작업 분석 및 계획 수립 중...")

        stories = self._plan_stories(project_id, task)
        if not stories:
            return {
                "success": False,
                "error": "작업 계획을 생성할 수 없습니다",
                "iterations": 0
            }

        if progress_callback:
            progress_callback(0, f"{len(stories)}개 하위 작업 생성 완료")

        # 2단계: 반복 실행
        for iteration in range(1, max_iterations + 1):
            if cancel_check and cancel_check():
                break

            iterations = iteration
            pending = [s for s in stories if s["status"] == "pending"]
            if not pending:
                if progress_callback:
                    progress_callback(iteration, "모든 작업 완료!")
                break

            current_story = pending[0]
            story_id = current_story["id"]

            if progress_callback:
                progress_callback(
                    iteration,
                    f"[{iteration}/{max_iterations}] 작업 {story_id}: {current_story['title']}"
                )

            # 코드 수정 실행 — 마기 우선, 없으면 bridge 폴백
            files = self._get_relevant_files(project_id)
            edit_message = self._build_story_message(project_id, current_story, files)

            result = self._execute_story(project_id, edit_message, files)
            all_results.append({
                "iteration": iteration,
                "story_id": story_id,
                "executor": "nanobot" if self._use_nanobot() else "bridge",
                "result": result
            })

            if self._use_nanobot():
                # 마기 실행 결과 처리
                if result.get("success"):
                    passed = self._verify_story(project_id, current_story, result)
                    if passed:
                        current_story["status"] = "done"
                        if progress_callback:
                            progress_callback(iteration, f"작업 {story_id} 완료 ✓ (마기 실행)")
                    else:
                        if progress_callback:
                            progress_callback(iteration, f"작업 {story_id} 검증 실패, 재시도 예정")
                else:
                    error = result.get("response", result.get("error", "마기 오류"))
                    if progress_callback:
                        progress_callback(iteration, f"작업 {story_id} 실패: {error}")
            else:
                # bridge 폴백 결과 처리
                if result.get("success") and result.get("needs_approval"):
                    proposal_id = result.get("proposal_id")
                    if proposal_id:
                        approve_result = self.bridge.approve_proposal(proposal_id)
                        if approve_result.get("success"):
                            passed = self._verify_story(project_id, current_story, result)
                            if passed:
                                current_story["status"] = "done"
                                if progress_callback:
                                    progress_callback(iteration, f"작업 {story_id} 완료 ✓ (bridge)")
                            else:
                                if progress_callback:
                                    progress_callback(iteration, f"작업 {story_id} 검증 실패, 재시도 예정")
                        else:
                            if progress_callback:
                                progress_callback(iteration, f"작업 {story_id} 적용 실패")
                elif result.get("success") and not result.get("needs_approval"):
                    current_story["status"] = "done"
                    if progress_callback:
                        progress_callback(iteration, f"작업 {story_id} 완료 (변경 없음)")
                else:
                    error = result.get("error", "알 수 없는 오류")
                    if progress_callback:
                        progress_callback(iteration, f"작업 {story_id} 실패: {error}")

        # 결과 요약
        done_count = sum(1 for s in stories if s["status"] == "done")
        total_count = len(stories)
        elapsed = round(time.time() - t0, 1)

        return {
            "success": done_count > 0,
            "iterations": iterations,
            "stories": stories,
            "done_count": done_count,
            "total_count": total_count,
            "results": all_results,
            "elapsed": elapsed,
            "summary": f"{done_count}/{total_count} 작업 완료 ({iterations}회 반복, {elapsed}초)"
        }

    def _use_nanobot(self) -> bool:
        """마기 사용 가능 여부"""
        return (self.nanobot_manager is not None
                and hasattr(self.nanobot_manager, 'available')
                and self.nanobot_manager.available)

    def _build_story_message(self, project_id: str, story: dict, files: list) -> str:
        """스토리 실행 메시지 생성 (파일 내용 포함)"""
        # 파일 내용 수집
        files_text = ""
        for fpath in files[:5]:  # 최대 5개 파일
            content = read_file(project_id, fpath)
            if content:
                ext = fpath.split(".")[-1] if "." in fpath else ""
                files_text += f"\n### 파일: {fpath}\n```{ext}\n{content}\n```\n"

        message = f"""다음 작업을 수행해주세요:

## 작업: {story['title']}
## 설명: {story['description']}
## 주의: 이 작업만 수행하고, 다른 부분은 변경하지 마세요.
"""
        if files_text:
            message = f"""다음은 프로젝트의 관련 파일입니다:
{files_text}

{message}"""

        return message

    def _execute_story(self, project_id: str, message: str, files: list) -> dict:
        """스토리 실행 - 마기 우선, bridge 폴백"""
        if self._use_nanobot():
            # 마기로 실행 (async → sync 브릿지)
            import asyncio
            session_id = f"ralph:{project_id}"
            try:
                # QThread 전용 이벤트 루프 (set_event_loop 제거 → 메인 스레드 충돌 방지)
                loop = asyncio.new_event_loop()
                try:
                    result = loop.run_until_complete(
                        self.nanobot_manager.process(message, session_id)
                    )
                    return result
                finally:
                    # 미완료 태스크 정리 후 루프 종료
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                    loop.close()
            except Exception as e:
                logger.error(f"마기 실행 실패, bridge 폴백: {e}")
                # 마기 실패 시 bridge 폴백
                return self.bridge.chat(project_id, message, files)
        else:
            # bridge로 실행
            return self.bridge.chat(project_id, message, files)

    def _plan_stories(self, project_id: str, task: str) -> list:
        """작업을 하위 스토리로 분해"""
        # 프로젝트 파일 구조 확인
        files = get_project_files(project_id)
        file_list = "\n".join([f"- {f['path']} ({f['size']}B)" for f in files[:20]])

        prompt = f"""프로젝트 파일 구조:
{file_list}

사용자 요청:
{task}

위 요청을 구체적인 하위 작업(스토리)으로 분해해주세요."""

        result = self.llm_provider.call(prompt, self.PLAN_SYSTEM_PROMPT)
        if not result.get("success"):
            logger.error(f"작업 분해 실패: {result.get('error')}")
            return []

        content = result["content"]
        # <think> 제거
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

        # JSON 추출
        try:
            json_match = re.search(r'\{[\s\S]*"stories"[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                stories = data.get("stories", [])
                # status 초기화
                for s in stories:
                    s["status"] = "pending"
                return stories
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"스토리 파싱 실패: {e}")

        # JSON 파싱 실패 시 단일 스토리로 처리
        return [{"id": 1, "title": task, "description": task, "status": "pending"}]

    def _verify_story(self, project_id: str, story: dict, result: dict) -> bool:
        """작업 완료 여부 검증 (마기/bridge 모두 대응)"""
        diff = result.get("diff", "")
        response = result.get("response", "")
        steps = result.get("steps", [])

        if not diff and not response:
            return False

        # 오류 메시지 감지
        error_indicators = ["error", "오류", "실패", "에러", "SyntaxError", "TypeError"]
        for indicator in error_indicators:
            if indicator.lower() in response.lower():
                return False

        # 마기 실행: steps가 있으면 도구를 사용한 것 → 성공으로 판단
        if steps:
            return True

        # bridge 실행: diff가 있으면 성공
        return bool(diff) or bool(response)

    def _get_relevant_files(self, project_id: str) -> list:
        """프로젝트의 주요 파일 목록 (최대 10개)"""
        files = get_project_files(project_id)
        # 코드 파일만 필터링, 크기 순으로 정렬
        code_exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".go", ".rs"}
        code_files = [f for f in files if f["ext"] in code_exts]
        if not code_files:
            code_files = files

        # 최대 10개
        return [f["path"] for f in code_files[:10]]
