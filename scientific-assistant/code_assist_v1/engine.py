"""
code_assist_v1/engine.py - 코딩 어시스턴트용 시스템 프롬프트·컨텍스트 빌더
"""
from __future__ import annotations
import os
import re
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
    EDIT_PROTOCOL,
)
from code_assist_v1.skill_filter import load_skill_content


def build_coding_system_prompt(
    skill_ids: list[str] | None = None,
    user_extra: str = "",
    n_ctx: int = 32768,
    can_edit: bool = False,
) -> str:
    """코딩 어시스턴트 시스템 프롬프트 (스킬 본문 포함).

    knowledge / workspace 는 별도 system 메시지로 주입한다 (build_knowledge_block / build_workspace_block).
    """
    parts: list[str] = [CODING_SYSTEM_PROMPT.strip(), ANTI_HALLUCINATION.strip()]

    # ★첨부된 파일이 있을 때만 수정 계약을 넣는다. 볼 파일도 없는데 "고쳐서
    #   내놔라" 고 시키면, 모델이 있지도 않은 파일에 edit 블록을 지어낸다.
    if can_edit:
        parts.append(EDIT_PROTOCOL.strip())

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


# ── 워크스페이스 예산 ──
# ★예산이 16,000자로 못박혀 있었다. 그런데 쓰는 모델은 대부분 128,000 토큰
#   짜리다 — 프로젝트를 통째로 붙여도 모델 능력의 4% 만 쓰고, 파일 네댓 개
#   들어가면 나머지는 통째로 잘려 나갔다. "모델도 큰 게 있는데 왜 안 되냐"
#   가 바로 이 얘기다. 예산을 모델 크기에 맞춰 잡는다.
#
# 코드 1토큰 ≈ 3자로 본다(한글 주석이 섞이면 더 짧아지므로 보수적으로).
CHARS_PER_TOKEN = 3
# 남은 자리는 대화 이력·시스템 프롬프트·답변에 쓴다. 절반까지만 첨부에 준다.
WORKSPACE_CTX_SHARE = 0.5


def workspace_budget(n_ctx: int | None) -> tuple[int, int]:
    """(전체 예산, 파일 하나 상한) — 글자 수 기준.

    모델을 모르면 예전 고정값으로 떨어진다(더 나빠지지는 않게).
    """
    if not n_ctx or n_ctx <= 0:
        return MAX_WORKSPACE_TOTAL_CHARS, MAX_WORKSPACE_FILE_CHARS
    total = int(n_ctx * WORKSPACE_CTX_SHARE * CHARS_PER_TOKEN)
    total = max(total, MAX_WORKSPACE_TOTAL_CHARS)     # 줄어들 일은 없게
    per_file = max(MAX_WORKSPACE_FILE_CHARS, total // 8)
    return total, per_file


def _rank_files(workspace_files: list[dict], query: str) -> list[dict]:
    """질문과 상관있는 파일을 앞으로.

    ★예산이 모자라면 뒤쪽 파일이 통째로 잘린다. 그때 잘려 나갈 것이
      '나중에 올린 파일' 이 아니라 '질문과 상관없는 파일' 이어야 한다.
      예산이 넉넉하면 순서는 아무 영향이 없으니 손해 볼 것도 없다.
    """
    if not query.strip():
        return list(workspace_files)
    words = {w for w in re.findall(r"[a-z0-9_]{2,}|[가-힣]{2,}", query.lower())}
    if not words:
        return list(workspace_files)

    def score(f: dict) -> float:
        name = str(f.get("filename", "")).lower()
        body = str(f.get("content") or "").lower()
        s = 0.0
        for w in words:
            if w in name:
                s += 5.0            # 파일 이름에 나오면 거의 확실하다
            elif w in body:
                s += 1.0
        return s

    # 점수 같으면 원래 순서 유지 (sorted 는 안정 정렬)
    return sorted(workspace_files, key=lambda f: -score(f))


def _cut(text: str, limit: int) -> str:
    """줄 경계에서 자른다 — 문장 한가운데서 끊으면 코드가 깨져 보인다."""
    if len(text) <= limit:
        return text
    head = text[:limit]
    nl = head.rfind("\n")
    if nl > limit * 0.6:            # 너무 많이 버리게 되면 그냥 자른다
        head = head[:nl]
    return head


def build_workspace_block(
    workspace_files: list[dict],
    n_ctx: int | None = None,
    query: str = "",
) -> Optional[dict]:
    """첨부된 파일들을 system 메시지로 묶음.

    workspace_files: [{filename, content, lang?}]
    n_ctx: 고른 모델의 컨텍스트 크기. 주면 예산을 거기 맞춘다.
    query: 지금 질문. 주면 상관있는 파일을 앞에 놓는다.
    """
    if not workspace_files:
        return None

    max_total, max_file = workspace_budget(n_ctx)
    ordered = _rank_files(workspace_files, query)

    parts = [WORKSPACE_INJECT_HEADER.strip()]
    total = 0
    omitted: list[str] = []
    for f in ordered:
        fname = f.get("filename", "untitled")
        lang = f.get("lang", "")
        content = (f.get("content") or "")
        if len(content) > max_file:
            content = _cut(content, max_file) + "\n... (파일 잘림)"
        if total + len(content) > max_total:
            remain = max_total - total
            if remain < 300:
                omitted.append(str(fname))
                continue
            content = _cut(content, remain) + "\n... (예산 초과로 잘림)"
        fence_lang = lang or _guess_lang(fname)
        parts.append(f"\n--- 📁 {fname} ---\n```{fence_lang}\n{content}\n```")
        total += len(content)

    # ★몇 개를 못 넣었는지 모델에게 알려 준다. 안 그러면 모델은 이게 프로젝트
    #   전부인 줄 알고 "그런 코드는 없다" 고 단언한다.
    if omitted:
        parts.append(
            f"\n--- ⚠️ 컨텍스트 예산 초과로 {len(omitted)}개 파일을 넣지 못했다 ---\n"
            + ", ".join(omitted[:40])
            + (" ..." if len(omitted) > 40 else "")
            + "\n이 목록의 파일 내용은 보이지 않는다. 필요하면 사용자에게 요청하라."
        )

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
