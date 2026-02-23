#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AiderBridge - aider-chat 통합 핵심 클래스
API 모드: aider Python API 사용
GGUF 모드: 직접 LLM 호출로 코드 수정
"""

import os
import re
import uuid
import subprocess
import logging
import requests
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from .project_manager import get_project, _load_registry, _save_registry, _should_ignore

logger = logging.getLogger(__name__)

# 코드 파일 확장자
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h",
    ".cs", ".go", ".rs", ".sql", ".html", ".css", ".json", ".yaml", ".yml",
    ".md", ".txt", ".sh", ".bat", ".ps1", ".r", ".R", ".vue", ".svelte",
    ".php", ".rb", ".swift", ".kt", ".scala", ".xml", ".toml", ".cfg", ".ini",
}


class AiderBridge:
    """aider-chat Python API 래퍼"""

    def __init__(self, config, llm_provider):
        self.config = config
        self.llm_provider = llm_provider
        self._coders: Dict[str, object] = {}
        self._pending_proposals: Dict[str, dict] = {}

    def _get_llm_config(self) -> tuple:
        """현재 LLM 설정 반환: (model_name, api_base, api_key)"""
        # API 모드
        if self.config.api_token and self.config.llm_mode != "local":
            cfg = self.config.ENV_CONFIG.get(self.config.env_mode, {})
            url = cfg.get("url", "")
            api_base = url.rsplit("/chat/completions", 1)[0] if "/chat/completions" in url else url
            model_name = f"openai/{cfg.get('model', 'gpt-oss-20b')}"
            return model_name, api_base, self.config.api_token

        # GGUF 모드 → 로컬 서버
        model_name = f"openai/{self.config.current_gguf_model or 'local-gguf'}"
        api_base = "http://127.0.0.1:10002/v1"
        api_key = "sk-local-dummy"
        return model_name, api_base, api_key

    def _get_project_files(self, project_path: Path, files: Optional[List[str]] = None) -> List[str]:
        """프로젝트 파일 목록 반환 (노이즈 필터링 적용)"""
        if files:
            result = []
            for f in files:
                full_path = project_path / f
                if full_path.exists() and full_path.is_file():
                    result.append(str(full_path))
            return result

        result = []
        for f in project_path.rglob("*"):
            if f.is_file() and f.suffix in CODE_EXTENSIONS:
                try:
                    rel = f.relative_to(project_path)
                except ValueError:
                    continue
                if not _should_ignore(rel):
                    result.append(str(f))
        return result

    def _chat_with_aider(self, project_path: Path, model_name: str, api_base: str,
                         api_key: str, message: str, fnames: List[str]) -> dict:
        """aider를 통한 코드 수정 (stash 기반 승인 워크플로우)"""
        try:
            from aider.coders import Coder
            from aider.models import Model
            from aider.io import InputOutput
        except ImportError:
            return {"success": False, "error": "aider-chat 미설치. pip install aider-chat"}

        os.environ["OPENAI_API_BASE"] = api_base
        os.environ["OPENAI_API_KEY"] = api_key

        original_cwd = os.getcwd()
        os.chdir(str(project_path))
        try:
            from io import StringIO
            capture = StringIO()
            io = InputOutput(yes=True, output=capture)
            model = Model(model_name)
            coder = Coder.create(
                main_model=model, fnames=fnames, io=io,
                auto_commits=False, use_git=True
            )
            result = coder.run(message)

            captured_output = capture.getvalue()
            response_text = result if result else captured_output.strip()
            if not response_text:
                response_text = "변경 제안 없음"

            # diff 수집
            diff_text = self._collect_diff(project_path)

            # stash로 임시 보관
            proposal_id = f"prop_{uuid.uuid4().hex[:8]}"
            has_changes = bool(diff_text)

            if has_changes:
                self._update_gitignore(project_path)
                self._stash_changes(project_path, proposal_id)

            return {
                "success": True,
                "response": response_text,
                "diff": diff_text,
                "proposal_id": proposal_id if has_changes else None,
                "needs_approval": has_changes,
                "model": model_name,
                "mode": "preview"
            }
        except Exception as e:
            logger.error(f"aider 오류: {e}")
            try:
                subprocess.run(["git", "-C", str(project_path), "checkout", "."], capture_output=True)
            except Exception:
                pass
            return {"success": False, "error": str(e)}
        finally:
            os.chdir(original_cwd)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """토큰 수 추정 (한글 ~1.5토큰/글자, 영문/코드 ~0.25토큰/단어)"""
        # 한글 글자 수
        kr_chars = sum(1 for c in text if '\uac00' <= c <= '\ud7a3')
        # 영문/코드는 공백+특수문자 기준
        non_kr = len(text) - kr_chars
        return int(kr_chars * 1.5 + non_kr * 0.35)

    def _get_ctx_limit(self) -> int:
        """현재 모델의 컨텍스트 윈도우 크기"""
        if self.config.llm_mode == "local":
            gguf_cfg = self.config.get_gguf_config()
            return gguf_cfg.get("ctx", 8192)
        # API 모드는 넉넉하게
        return 32768

    def _split_files_by_token_limit(self, file_contents: dict, message: str,
                                     system_prompt: str) -> List[dict]:
        """파일을 토큰 한도에 맞게 그룹으로 분할"""
        ctx_limit = self._get_ctx_limit()
        max_tokens = self.config.get_max_tokens()
        # 입력에 쓸 수 있는 토큰 = 컨텍스트 - 출력 예약 - 시스템프롬프트 - 여유분
        system_tokens = self._estimate_tokens(system_prompt)
        message_tokens = self._estimate_tokens(message)
        overhead = system_tokens + message_tokens + 500  # 템플릿 오버헤드
        available = ctx_limit - max_tokens - overhead

        if available < 500:
            available = 500  # 최소 보장

        # 파일별 토큰 계산
        file_token_list = []
        for fname, content in file_contents.items():
            ext = Path(fname).suffix.lstrip(".")
            file_text = f"\n### 파일: {fname}\n```{ext}\n{content}\n```\n"
            tokens = self._estimate_tokens(file_text)
            file_token_list.append((fname, content, file_text, tokens))

        # 그룹 분할
        groups = []
        current_group = {}
        current_tokens = 0

        for fname, content, file_text, tokens in file_token_list:
            if tokens > available:
                # 단일 파일이 한도 초과 → 단독 그룹 (잘릴 수 있지만 시도)
                if current_group:
                    groups.append(current_group)
                    current_group = {}
                    current_tokens = 0
                groups.append({fname: content})
                logger.warning(f"파일 '{fname}'이 토큰 한도 초과 ({tokens} > {available})")
                continue

            if current_tokens + tokens > available:
                # 현재 그룹 마감, 새 그룹 시작
                if current_group:
                    groups.append(current_group)
                current_group = {fname: content}
                current_tokens = tokens
            else:
                current_group[fname] = content
                current_tokens += tokens

        if current_group:
            groups.append(current_group)

        return groups

    def _build_code_prompt(self, file_contents: dict, message: str, mode: str = "modify") -> tuple:
        """코드 프롬프트 생성 (mode: 'modify' 또는 'analyze')"""
        files_text = ""
        for fname, content in file_contents.items():
            ext = Path(fname).suffix.lstrip(".")
            files_text += f"\n### 파일: {fname}\n```{ext}\n{content}\n```\n"

        if mode == "analyze":
            system_prompt = """당신은 시니어 소프트웨어 엔지니어이며 코드 분석 전문가입니다.
사용자가 제공한 코드를 분석하고 질문에 답변해주세요.

규칙:
1. 코드의 구조, 로직, 패턴을 분석해주세요
2. 버그, 잠재적 문제, 개선 가능한 부분을 찾아주세요
3. 한국어로 상세히 설명해주세요
4. 코드를 수정하지 말고 분석 결과만 제공하세요
5. 요청에 따라 성능, 보안, 가독성 관점에서 리뷰하세요

출력 형식:
- 마크다운 형식으로 깔끔하게 정리
- 중요도 순서대로 설명
- 코드 참조 시 해당 부분을 인용"""

            user_prompt = f"""다음 코드를 분석해주세요.

## 분석 대상 코드
{files_text}

## 분석 요청
{message}

위 코드에 대해 상세히 분석해주세요."""
        else:
            system_prompt = """당신은 코드 수정 전문가입니다.
사용자가 요청한 변경사항을 기존 코드에 적용해주세요.

규칙:
1. 수정된 파일마다 반드시 "### 파일: 파일명" 헤더를 쓰고, 바로 아래 코드 블록으로 전체 수정 코드를 제공하세요
2. 수정한 부분에 주석으로 설명을 달아주세요
3. 어떤 부분을 왜 변경했는지 한국어로 설명해주세요
4. 기존 코드의 구조와 스타일을 유지하세요
5. 요청하지 않은 부분은 절대 변경하지 마세요
6. 변경이 필요 없는 파일은 포함하지 마세요

출력 형식 예시:
### 파일: src/main.py
```python
(수정된 전체 코드)
```
### 변경 설명
- 무엇을 왜 변경했는지"""

            user_prompt = f"""다음 파일을 수정해주세요.

## 현재 파일 내용
{files_text}

## 수정 요청
{message}

위 형식대로 수정된 파일 코드와 변경 설명을 제공해주세요."""

        return system_prompt, user_prompt

    def _call_llm(self, system_prompt: str, user_prompt: str) -> dict:
        """LLM 호출 (로컬/API 자동 선택)"""
        if self.config.llm_mode == "local" and self.llm_provider.local_llm is not None:
            max_tokens = self.config.get_max_tokens()
            logger.info(f"GGUF 직접 호출 모드 (max_tokens={max_tokens})")
            result = self.llm_provider.call(user_prompt, system_prompt, max_tokens=max_tokens)
            if not result.get("success"):
                return {"success": False, "error": result.get("error", "GGUF 추론 실패")}
            return {"success": True, "content": result["content"]}
        else:
            model_name, api_base, api_key = self._get_llm_config()
            resp = requests.post(
                f"{api_base}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model_name.replace("openai/", ""),
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": self.config.get_max_tokens(),
                    "temperature": 0.3,
                    "stream": False
                },
                timeout=300
            )
            if resp.status_code != 200:
                return {"success": False, "error": f"LLM 호출 실패: {resp.status_code}"}
            result_data = resp.json()
            return {"success": True, "content": result_data["choices"][0]["message"]["content"]}

    def _chat_direct_llm(self, project_path: Path, message: str, fnames: List[str],
                         mode: str = "modify") -> dict:
        """aider 대신 직접 LLM 호출로 코드 수정/분석 (GGUF 안정성 확보)"""
        # 선택된 파일 내용 읽기
        file_contents = {}
        for fpath in fnames:
            p = Path(fpath)
            if p.exists() and p.is_file():
                try:
                    content = p.read_text(encoding="utf-8")
                    rel = p.relative_to(project_path)
                    file_contents[str(rel).replace("\\", "/")] = content
                except Exception:
                    pass

        if not file_contents:
            return {"success": False, "error": "선택된 파일을 읽을 수 없습니다"}

        file_list = list(file_contents.keys())

        # 토큰 한도 체크 및 자동 분할
        system_prompt, _ = self._build_code_prompt(file_contents, message, mode)
        groups = self._split_files_by_token_limit(file_contents, message, system_prompt)

        logger.info(f"파일 {len(file_contents)}개 → {len(groups)}개 그룹으로 분할 (mode={mode})")

        try:
            all_responses = []
            all_applied = []

            for i, group in enumerate(groups):
                group_system, group_user = self._build_code_prompt(group, message, mode)

                if len(groups) > 1:
                    logger.info(f"그룹 {i+1}/{len(groups)} 처리 중 (파일 {len(group)}개)")

                result = self._call_llm(group_system, group_user)
                if not result.get("success"):
                    return result

                response_text = result["content"]
                response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL).strip()
                all_responses.append(response_text)

                # 분석 모드면 코드 적용 안함, 수정 모드만 적용
                if mode == "modify":
                    applied = self._apply_code_blocks(response_text, group, list(group.keys()), project_path)
                    all_applied.extend(applied)

            # 전체 응답 합치기
            response_text = "\n\n---\n\n".join(all_responses) if len(all_responses) > 1 else all_responses[0]
            applied_files = all_applied

            # diff 수집
            diff_text = self._collect_diff(project_path)

            # stash로 임시 보관
            proposal_id = f"prop_{uuid.uuid4().hex[:8]}"
            has_changes = bool(diff_text)

            if has_changes:
                self._update_gitignore(project_path)
                self._stash_changes(project_path, proposal_id)

            model_name = self.config.current_gguf_model if self.config.llm_mode == "local" else self.config.api_model
            return {
                "success": True,
                "response": response_text,
                "diff": diff_text,
                "proposal_id": proposal_id if has_changes else None,
                "needs_approval": has_changes,
                "applied_files": applied_files,
                "model": model_name,
                "mode": "preview"
            }
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "LLM 서버에 연결할 수 없습니다. 서버 상태를 확인해주세요."}
        except requests.exceptions.Timeout:
            return {"success": False, "error": "LLM 응답 시간 초과 (300초). 요청을 줄여서 다시 시도해주세요."}
        except Exception as e:
            try:
                subprocess.run(["git", "-C", str(project_path), "checkout", "."], capture_output=True)
            except Exception:
                pass
            logger.error(f"직접 LLM 수정 오류: {e}")
            return {"success": False, "error": str(e)}

    def _apply_code_blocks(self, response_text: str, file_contents: dict,
                           file_list: list, project_path: Path) -> list:
        """LLM 응답에서 파일별 코드 블록을 추출하여 적용"""
        applied_files = []

        # 방법 1: "### 파일: filename" 형식으로 파일명이 명시된 경우
        pattern = r'###\s*파일[:\s]*([^\n]+)\s*\n```\w*\s*\n(.*?)```'
        matches = re.findall(pattern, response_text, re.DOTALL)

        if matches:
            for fname_raw, code_block in matches:
                fname = fname_raw.strip().strip('`').strip()
                code = code_block.strip()
                if len(code) < 5:
                    continue

                # 파일명 매칭 (정확히 일치하거나 경로의 마지막 부분이 일치)
                matched_file = None
                for existing_fname in file_contents:
                    if fname == existing_fname or fname == Path(existing_fname).name:
                        matched_file = existing_fname
                        break

                if matched_file and code != file_contents[matched_file].strip():
                    target = project_path / matched_file
                    try:
                        target.write_text(code + "\n", encoding="utf-8")
                        applied_files.append(matched_file)
                        logger.info(f"코드 적용: {matched_file}")
                    except Exception as e:
                        logger.error(f"파일 쓰기 실패 ({matched_file}): {e}")
            return applied_files

        # 방법 2: 파일명 없이 코드 블록만 있는 경우 (파일 1개일 때만 적용)
        code_blocks = re.findall(r'```(?:\w+)?\s*\n(.*?)```', response_text, re.DOTALL)
        if code_blocks and len(file_list) == 1:
            fname = file_list[0]
            for block in code_blocks:
                block_stripped = block.strip()
                if (block_stripped != file_contents[fname].strip()
                        and len(block_stripped) > 10):
                    target = project_path / fname
                    try:
                        target.write_text(block_stripped + "\n", encoding="utf-8")
                        applied_files.append(fname)
                        logger.info(f"코드 적용 (단일 파일): {fname}")
                    except Exception as e:
                        logger.error(f"파일 쓰기 실패 ({fname}): {e}")
                    break
        elif code_blocks and len(file_list) > 1:
            # 여러 파일인데 파일명이 없으면 경고만 남기고 적용하지 않음
            logger.warning(
                f"파일명 없는 코드 블록 {len(code_blocks)}개 감지. "
                f"대상 파일이 {len(file_list)}개여서 자동 적용 불가."
            )

        return applied_files

    def chat(self, project_id: str, message: str, files: Optional[List[str]] = None,
             mode: str = "modify") -> dict:
        """코드 수정/분석 요청 - GGUF면 직접 LLM, API면 aider
        mode: 'modify' (코드 수정) 또는 'analyze' (코드 분석)
        """
        project = get_project(project_id)
        if not project:
            return {"success": False, "error": "프로젝트를 찾을 수 없습니다"}

        project_path = Path(project["path"])
        if not project_path.exists():
            return {"success": False, "error": f"프로젝트 경로가 존재하지 않습니다: {project_path}"}

        model_name, api_base, api_key = self._get_llm_config()
        fnames = self._get_project_files(project_path, files)

        if not fnames:
            action = "분석할" if mode == "analyze" else "수정할"
            return {"success": False, "error": f"{action} 파일이 없습니다. 파일을 선택하거나 프로젝트에 파일을 추가해주세요."}

        # 분석 모드는 항상 직접 LLM 호출 (aider는 수정 전용)
        if mode == "analyze" or "127.0.0.1:10002" in api_base:
            logger.info(f"직접 LLM 모드 ({mode}) - 파일 {len(fnames)}개")
            result = self._chat_direct_llm(project_path, message, fnames, mode=mode)
        else:
            logger.info(f"aider 모드 (API) - 파일 {len(fnames)}개")
            result = self._chat_with_aider(project_path, model_name, api_base, api_key, message, fnames)

        # last_active 업데이트
        if result.get("success"):
            try:
                reg = _load_registry()
                for p in reg["projects"]:
                    if p["id"] == project_id:
                        p["last_active"] = datetime.now().isoformat()
                _save_registry(reg)
            except Exception as e:
                logger.warning(f"last_active 업데이트 실패: {e}")

        return result

    def approve_proposal(self, proposal_id: str) -> dict:
        """승인: 올바른 stash를 찾아서 pop → 커밋"""
        proposal = self._pending_proposals.pop(proposal_id, None)
        if not proposal:
            return {"success": False, "error": "만료되었거나 존재하지 않는 제안입니다"}

        project_path = proposal["project_path"]
        stash_name = f"aider-proposal-{proposal_id}"

        try:
            # aider 캐시 정리
            import shutil
            aider_cache = Path(project_path) / ".aider.tags.cache.v4"
            if aider_cache.exists():
                shutil.rmtree(aider_cache, ignore_errors=True)

            # 올바른 stash를 찾아서 pop (여러 proposal이 있을 수 있음)
            stash_ref = self._find_stash_ref(project_path, stash_name)
            if stash_ref:
                result = subprocess.run(
                    ["git", "-C", project_path, "stash", "pop", stash_ref],
                    capture_output=True, text=True, encoding="utf-8"
                )
            else:
                # 못 찾으면 최신 stash pop 시도
                result = subprocess.run(
                    ["git", "-C", project_path, "stash", "pop"],
                    capture_output=True, text=True, encoding="utf-8"
                )

            if result.returncode != 0:
                return {"success": False, "error": f"stash pop 실패: {result.stderr}"}

            # diff 수집
            diff_text = ""
            try:
                diff_result = subprocess.run(
                    ["git", "-C", project_path, "diff"],
                    capture_output=True, text=True, encoding="utf-8"
                )
                diff_text = diff_result.stdout.strip()
            except Exception:
                pass

            # 커밋
            subprocess.run(["git", "-C", project_path, "add", "-A"], capture_output=True)
            subprocess.run(
                ["git", "-C", project_path, "commit", "-m",
                 f"aider: approved changes ({proposal_id})"],
                capture_output=True, encoding="utf-8"
            )

            logger.info(f"변경 승인 완료: {proposal_id}")
            return {"success": True, "response": "변경이 적용되었습니다!", "diff": diff_text, "mode": "applied"}
        except Exception as e:
            logger.error(f"승인 적용 오류: {e}")
            return {"success": False, "error": str(e)}

    def reject_proposal(self, proposal_id: str) -> dict:
        """거부: stash drop"""
        proposal = self._pending_proposals.pop(proposal_id, None)
        if not proposal:
            return {"success": False, "error": "제안을 찾을 수 없습니다"}

        project_path = proposal["project_path"]
        stash_name = f"aider-proposal-{proposal_id}"

        try:
            stash_ref = self._find_stash_ref(project_path, stash_name)
            if stash_ref:
                subprocess.run(
                    ["git", "-C", project_path, "stash", "drop", stash_ref],
                    capture_output=True, encoding="utf-8"
                )
            else:
                logger.warning(f"stash를 찾지 못함: {stash_name}")

            logger.info(f"변경 거부: {proposal_id}")
            return {"success": True, "message": "변경이 취소되었습니다. 기존 코드 유지."}
        except Exception as e:
            logger.error(f"거부 처리 오류: {e}")
            return {"success": False, "error": str(e)}

    # --- 유틸리티 ---

    def _find_stash_ref(self, project_path: str, stash_name: str) -> Optional[str]:
        """stash 목록에서 특정 proposal의 stash 참조를 찾기"""
        try:
            result = subprocess.run(
                ["git", "-C", project_path, "stash", "list"],
                capture_output=True, text=True, encoding="utf-8"
            )
            for line in result.stdout.strip().split("\n"):
                if stash_name in line:
                    return line.split(":")[0]  # e.g. "stash@{0}"
        except Exception:
            pass
        return None

    def _collect_diff(self, project_path: Path) -> str:
        """변경사항 diff 수집"""
        diff_text = ""
        try:
            diff_result = subprocess.run(
                ["git", "-C", str(project_path), "diff"],
                capture_output=True, text=True, encoding="utf-8"
            )
            diff_text = diff_result.stdout.strip()
        except Exception:
            pass

        if not diff_text:
            try:
                diff_result = subprocess.run(
                    ["git", "-C", str(project_path), "diff", "--cached"],
                    capture_output=True, text=True, encoding="utf-8"
                )
                diff_text = diff_result.stdout.strip()
            except Exception:
                pass

        return diff_text

    def _update_gitignore(self, project_path: Path):
        """aider 캐시 파일을 gitignore에 추가"""
        gitignore = project_path / ".gitignore"
        ignore_entries = [".aider*", ".aider.tags.cache*", "__pycache__/"]
        try:
            existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
            added = False
            for entry in ignore_entries:
                if entry not in existing:
                    existing += f"\n{entry}"
                    added = True
            if added:
                gitignore.write_text(existing.strip() + "\n", encoding="utf-8")
        except Exception:
            pass

        subprocess.run(
            ["git", "-C", str(project_path), "rm", "-r", "--cached",
             "--ignore-unmatch", ".aider.tags.cache.v4"],
            capture_output=True, encoding="utf-8"
        )

    def _stash_changes(self, project_path: Path, proposal_id: str):
        """변경사항을 stash에 보관"""
        subprocess.run(
            ["git", "-C", str(project_path), "add", "-A"],
            capture_output=True
        )
        result = subprocess.run(
            ["git", "-C", str(project_path), "stash", "push", "-m",
             f"aider-proposal-{proposal_id}"],
            capture_output=True, encoding="utf-8", text=True
        )
        if result.returncode != 0:
            logger.error(f"stash push 실패: {result.stderr}")
        else:
            logger.info(f"변경사항 stash 보관: {proposal_id}")
        self._pending_proposals[proposal_id] = {
            "project_path": str(project_path),
            "created": datetime.now().isoformat(),
        }
