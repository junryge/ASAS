"""
code_assist_v1/engine.py - 코딩 어시스턴트용 시스템 프롬프트·컨텍스트 빌더
"""
from __future__ import annotations
import os
from typing import Optional

from code_assist_v1.config import (
    MAX_WORKSPACE_FILE_CHARS,
    MAX_WORKSPACE_TOTAL_CHARS,
    MAX_KNOWLEDGE_INJECT_CHARS,
)
from code_assist_v1.prompts import (
    CODING_SYSTEM_PROMPT,
    ANTI_HALLUCINATION,
    KNOWLEDGE_INJECT_HEADER,
    WORKSPACE_INJECT_HEADER,
    SKILL_INJECT_HEADER,
)
from code_assist_v1.skill_filter import load_skill_content


def build_coding_system_prompt(
    skill_ids: list[str] | None = None,
    user_extra: str = "",
    n_ctx: int = 32768,
) -> str:
    """코딩 어시스턴트 시스템 프롬프트 (스킬 본문 포함).

    knowledge / workspace 는 별도 system 메시지로 주입한다 (build_knowledge_block / build_workspace_block).
    """
    parts: list[str] = [CODING_SYSTEM_PROMPT.strip(), ANTI_HALLUCINATION.strip()]

    skill_ids = skill_ids or []
    if skill_ids:
        parts.append(SKILL_INJECT_HEADER.strip())
        # 컨텍스트 예산: 시스템 프롬프트 1500 + ctx 의 50% 까지 스킬에 할당
        budget = max(2000, int(n_ctx * 0.4) - 1500)
        used = 0
        for sid in skill_ids:
            content = load_skill_content(sid, max_chars=4000)
            if not content:
                continue
            head = f"\n--- 스킬: {sid} ---\n"
            chunk = head + content
            if used + len(chunk) > budget:
                # 잘라서라도 일부 포함
                remain = budget - used
                if remain > 200:
                    parts.append(chunk[:remain] + "\n... (잘림)")
                break
            parts.append(chunk)
            used += len(chunk)

    if user_extra and user_extra.strip():
        parts.append("\n=== 사용자 추가 지시 ===\n" + user_extra.strip())

    return "\n\n".join(parts)


def build_knowledge_block(
    query: str,
    knowledge_results: list[dict],
    intent_search_only: bool = False,
) -> Optional[dict]:
    """BM25 검색 결과 → system 메시지 dict 또는 None."""
    if not knowledge_results:
        return None

    body_parts = [KNOWLEDGE_INJECT_HEADER.strip(), f"검색어: {query}", ""]
    total = 0
    for r in knowledge_results:
        chunk = (r.get("content") or "")[:4000]
        if total + len(chunk) > MAX_KNOWLEDGE_INJECT_CHARS:
            chunk = chunk[: max(0, MAX_KNOWLEDGE_INJECT_CHARS - total)]
            if not chunk:
                break
        body_parts.append(f"--- 📄 {r.get('filename', '?')} (관련도 {r.get('score', 0):.1f}) ---")
        body_parts.append(chunk)
        body_parts.append("")
        total += len(chunk)

    if intent_search_only:
        body_parts.append(
            "사용자가 '검색'을 요청했습니다. 파일명 목록과 관련도만 간단히 보여주고, "
            "본문 분석/요약은 하지 마세요."
        )
    else:
        body_parts.append(
            "위 발췌만 근거로 사용하세요. 발췌 외 사실을 단정하지 마세요. "
            "어느 문서에서 가져왔는지 출처를 본문에 표기하세요."
        )

    return {"role": "system", "content": "\n".join(body_parts)}


def build_workspace_block(workspace_files: list[dict]) -> Optional[dict]:
    """첨부된 파일들을 system 메시지로 묶음.

    workspace_files: [{filename, content, lang?}]
    """
    if not workspace_files:
        return None

    parts = [WORKSPACE_INJECT_HEADER.strip()]
    total = 0
    for f in workspace_files:
        fname = f.get("filename", "untitled")
        lang = f.get("lang", "")
        content = (f.get("content") or "")
        if len(content) > MAX_WORKSPACE_FILE_CHARS:
            content = content[:MAX_WORKSPACE_FILE_CHARS] + "\n... (파일 잘림)"
        if total + len(content) > MAX_WORKSPACE_TOTAL_CHARS:
            remain = MAX_WORKSPACE_TOTAL_CHARS - total
            if remain < 300:
                parts.append(f"\n--- {fname} (생략됨, 컨텍스트 예산 초과) ---")
                continue
            content = content[:remain] + "\n... (예산 초과로 잘림)"
        fence_lang = lang or _guess_lang(fname)
        parts.append(f"\n--- 📁 {fname} ---\n```{fence_lang}\n{content}\n```")
        total += len(content)

    return {"role": "system", "content": "\n".join(parts)}


def _guess_lang(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return {
        ".py": "python", ".pyi": "python",
        ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
        ".ts": "typescript", ".tsx": "tsx",
        ".jsx": "jsx",
        ".html": "html", ".htm": "html",
        ".css": "css", ".scss": "scss", ".sass": "sass",
        ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
        ".md": "markdown", ".sh": "bash", ".bash": "bash", ".zsh": "bash",
        ".ps1": "powershell", ".bat": "batch",
        ".java": "java", ".kt": "kotlin",
        ".c": "c", ".cpp": "cpp", ".cc": "cpp", ".h": "c", ".hpp": "cpp",
        ".cs": "csharp", ".go": "go", ".rs": "rust",
        ".rb": "ruby", ".php": "php", ".sql": "sql",
        ".vue": "vue", ".svelte": "svelte",
        ".xml": "xml",
    }.get(ext, "")


def trim_message_history(messages: list[dict], max_turns: int = 12) -> list[dict]:
    """대화 히스토리를 최근 N턴으로 트림 (system 메시지는 첫 2개까지 유지)."""
    if len(messages) <= max_turns:
        return messages
    sys_head = [m for m in messages[:2] if m.get("role") == "system"]
    recent = messages[-max_turns:]
    return sys_head + recent
