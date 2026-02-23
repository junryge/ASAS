#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git 작업 - diff, stash, approve/reject, undo, history
"""

import subprocess
import logging
from .project_manager import get_project

logger = logging.getLogger(__name__)


def _git_run(project_path: str, args: list, **kwargs) -> subprocess.CompletedProcess:
    """git 명령 실행 헬퍼"""
    return subprocess.run(
        ["git", "-C", project_path] + args,
        capture_output=True, text=True, encoding="utf-8",
        **kwargs
    )


def undo(project_id: str) -> dict:
    """마지막 변경 취소 (git reset) - 안전한 버전"""
    project = get_project(project_id)
    if not project:
        return {"success": False, "error": "프로젝트를 찾을 수 없습니다"}

    project_path = project["path"]
    try:
        # 커밋 수 확인
        count_result = _git_run(project_path, ["rev-list", "--count", "HEAD"])
        if count_result.returncode != 0:
            return {"success": False, "error": "git 히스토리를 확인할 수 없습니다"}

        commit_count = int(count_result.stdout.strip())
        if commit_count <= 1:
            return {"success": False, "error": "초기 커밋이므로 되돌릴 수 없습니다"}

        # 마지막 커밋 메시지 확인
        last_result = _git_run(project_path, ["log", "--oneline", "-1"])
        last_commit = last_result.stdout.strip()

        # soft reset → unstage → checkout (안전한 3단계)
        reset_result = _git_run(project_path, ["reset", "--soft", "HEAD~1"])
        if reset_result.returncode != 0:
            return {"success": False, "error": f"reset 실패: {reset_result.stderr}"}

        _git_run(project_path, ["reset", "HEAD"])
        _git_run(project_path, ["checkout", "."])

        return {"success": True, "reverted": last_commit}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_diff(project_id: str) -> dict:
    """현재 변경사항 diff"""
    project = get_project(project_id)
    if not project:
        return {"success": False, "error": "프로젝트를 찾을 수 없습니다"}

    try:
        # 최근 커밋 diff
        result = _git_run(project["path"], ["diff", "HEAD~1", "HEAD"])
        diff_text = result.stdout

        if not diff_text:
            # 미커밋 변경사항
            result = _git_run(project["path"], ["diff"])
            diff_text = result.stdout

        if not diff_text:
            # staged 변경사항
            result = _git_run(project["path"], ["diff", "--cached"])
            diff_text = result.stdout

        return {"success": True, "diff": diff_text or "변경사항 없음"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_history(project_id: str, limit: int = 20) -> dict:
    """git 커밋 히스토리"""
    project = get_project(project_id)
    if not project:
        return {"success": False, "error": "프로젝트를 찾을 수 없습니다"}

    try:
        result = _git_run(
            project["path"],
            ["log", f"--max-count={limit}", "--format=%H|%h|%s|%ai|%an"]
        )

        if result.returncode != 0:
            return {"success": True, "commits": []}

        commits = []
        for line in result.stdout.strip().split("\n"):
            if "|" in line:
                parts = line.split("|", 4)
                commits.append({
                    "hash": parts[0],
                    "short_hash": parts[1],
                    "message": parts[2],
                    "date": parts[3],
                    "author": parts[4] if len(parts) > 4 else "",
                })

        return {"success": True, "commits": commits}
    except Exception as e:
        return {"success": False, "error": str(e)}
