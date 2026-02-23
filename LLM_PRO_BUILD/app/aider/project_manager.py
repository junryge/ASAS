#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프로젝트 관리 - CRUD, 레지스트리
"""

import os
import re
import sys
import json
import uuid
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# 프로젝트 루트 경로 (PyInstaller EXE 환경 지원)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(os.path.dirname(sys.executable))
else:
    BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PROJECTS_ROOT = BASE_DIR / "aider_projects"
PROJECTS_FILE = PROJECTS_ROOT / "projects.json"

# 파일 트리에서 제외할 패턴
IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", ".tox", ".eggs",
    ".aider.tags.cache.v4", ".aider.tags.cache",
}

IGNORE_PREFIXES = (".aider",)

IGNORE_FILES = {
    ".DS_Store", "Thumbs.db", ".gitkeep",
}


def _should_ignore(rel_path: Path) -> bool:
    """파일/폴더를 무시해야 하는지 확인"""
    parts = rel_path.parts
    name = rel_path.name

    for part in parts:
        if part in IGNORE_DIRS:
            return True
        for prefix in IGNORE_PREFIXES:
            if part.startswith(prefix):
                return True

    if name in IGNORE_FILES:
        return True
    for prefix in IGNORE_PREFIXES:
        if name.startswith(prefix):
            return True

    return False


def _ensure_dirs():
    """프로젝트 디렉토리 구조 생성"""
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    (PROJECTS_ROOT / "code_editing").mkdir(exist_ok=True)
    (PROJECTS_ROOT / "data_analysis").mkdir(exist_ok=True)
    if not PROJECTS_FILE.exists():
        PROJECTS_FILE.write_text(
            json.dumps({"projects": []}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )


def _load_registry() -> dict:
    _ensure_dirs()
    try:
        return json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"레지스트리 로드 실패, 초기화: {e}")
        data = {"projects": []}
        _save_registry(data)
        return data


def _save_registry(data: dict):
    _ensure_dirs()
    PROJECTS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8"
    )


def _git_available() -> bool:
    """git 사용 가능 여부 확인"""
    try:
        result = subprocess.run(
            ["git", "--version"], capture_output=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def get_project(project_id: str) -> Optional[dict]:
    reg = _load_registry()
    for p in reg["projects"]:
        if p["id"] == project_id:
            # 경로 유효성 검사
            if not Path(p["path"]).exists():
                logger.warning(f"프로젝트 경로 없음: {p['path']}")
            return p
    return None


def scan_folder(path: str) -> dict:
    """폴더 경로 검증 + 내부 파일 미리보기"""
    p = Path(path)
    if not p.exists():
        return {"success": False, "error": f"경로가 존재하지 않습니다: {path}"}
    if not p.is_dir():
        return {"success": False, "error": "폴더가 아닙니다"}

    files = []
    for f in p.rglob("*"):
        if f.is_file():
            rel = f.relative_to(p)
            if not _should_ignore(rel):
                files.append(f)
    has_git = (p / ".git").exists()

    return {
        "success": True,
        "path": str(p),
        "file_count": len(files),
        "has_git": has_git,
        "sample_files": [str(f.relative_to(p)).replace("\\", "/") for f in files[:10]],
    }


def create_project(name: str, customer_type: str, description: str = "",
                   path: Optional[str] = None) -> dict:
    """프로젝트 생성"""
    reg = _load_registry()
    project_id = f"proj_{uuid.uuid4().hex[:8]}"

    is_existing_folder = False

    if path:
        project_path = Path(path)
        if project_path.exists() and project_path.is_dir():
            is_existing_folder = True
        elif not project_path.exists():
            project_path.mkdir(parents=True, exist_ok=True)
    else:
        safe_name = re.sub(r'[^\w\-]', '_', name.lower())
        project_path = PROJECTS_ROOT / customer_type / safe_name
        project_path.mkdir(parents=True, exist_ok=True)

    existing_files = []
    for f in project_path.rglob("*"):
        if f.is_file():
            rel = f.relative_to(project_path)
            if not _should_ignore(rel):
                existing_files.append(f)

    # git init (git 사용 가능한 경우만)
    git_dir = project_path / ".git"
    if not git_dir.exists() and _git_available():
        try:
            subprocess.run(["git", "init", str(project_path)], capture_output=True, check=True)
            # git user 설정 (로컬)
            subprocess.run(
                ["git", "-C", str(project_path), "config", "user.email", "nomos@local"],
                capture_output=True
            )
            subprocess.run(
                ["git", "-C", str(project_path), "config", "user.name", "Nomos"],
                capture_output=True
            )
            readme = project_path / "README.md"
            if not readme.exists():
                readme.write_text(f"# {name}\n{description}\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(project_path), "add", "."], capture_output=True)
            subprocess.run(
                ["git", "-C", str(project_path), "commit", "-m",
                 f"Initial commit ({len(existing_files)} files)"],
                capture_output=True
            )
            logger.info(f"git 초기화: {project_path} ({len(existing_files)}개 파일)")
        except Exception as e:
            logger.warning(f"git init 실패 (계속 진행): {e}")

    project = {
        "id": project_id,
        "name": name,
        "customer_type": customer_type,
        "description": description,
        "path": str(project_path),
        "created": datetime.now().isoformat(),
        "last_active": datetime.now().isoformat(),
        "file_count": len(existing_files),
        "is_existing_folder": is_existing_folder,
    }

    reg["projects"].append(project)
    _save_registry(reg)
    return project


def list_projects() -> list:
    return _load_registry()["projects"]


def delete_project(project_id: str) -> bool:
    reg = _load_registry()
    project = None
    for p in reg["projects"]:
        if p["id"] == project_id:
            project = p
            break

    if not project:
        return False

    ppath = Path(project["path"])
    if str(PROJECTS_ROOT) in str(ppath):
        shutil.rmtree(ppath, ignore_errors=True)

    reg["projects"] = [p for p in reg["projects"] if p["id"] != project_id]
    _save_registry(reg)
    return True


def get_project_files(project_id: str) -> list:
    """프로젝트 파일 목록 (노이즈 필터링 포함)"""
    project = get_project(project_id)
    if not project:
        return []

    ppath = Path(project["path"])
    if not ppath.exists():
        logger.warning(f"프로젝트 경로 없음: {ppath}")
        return []

    files = []
    for f in ppath.rglob("*"):
        if f.is_file():
            try:
                rel = f.relative_to(ppath)
            except ValueError:
                continue
            if not _should_ignore(rel):
                try:
                    size = f.stat().st_size
                except OSError:
                    size = 0
                files.append({
                    "path": str(rel).replace("\\", "/"),
                    "size": size,
                    "ext": f.suffix,
                })
    return sorted(files, key=lambda x: x["path"])


def read_file(project_id: str, file_path: str, smart_truncate: bool = True) -> Optional[str]:
    """파일 읽기 (CSV/대용량 파일 스마트 처리)

    smart_truncate=True: CSV는 헤더+샘플+통계, 대용량은 앞부분만
    smart_truncate=False: 전체 읽기 (UI 파일뷰어용)
    """
    project = get_project(project_id)
    if not project:
        return None

    fpath = Path(project["path"]) / file_path
    if not fpath.exists() or not fpath.is_file():
        return None

    try:
        content = fpath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            content = fpath.read_text(encoding="cp949")
        except Exception:
            return None
    except Exception:
        return None

    if not smart_truncate:
        return content

    ext = fpath.suffix.lower()
    lines = content.splitlines()
    total_lines = len(lines)

    # CSV/TSV 파일: 헤더 + 샘플 + 통계 요약
    if ext in (".csv", ".tsv"):
        return _smart_read_csv(content, lines, total_lines, ext)

    # 대용량 파일 (500줄 초과): 앞 200줄 + 뒷 50줄
    if total_lines > 500:
        return _smart_read_large(lines, total_lines)

    return content


def _smart_read_csv(content: str, lines: list, total_lines: int, ext: str) -> str:
    """CSV/TSV 스마트 읽기: 헤더 + 샘플 20줄 + 통계"""
    import csv
    from io import StringIO

    delimiter = "\t" if ext == ".tsv" else ","
    header = lines[0] if lines else ""

    # 컬럼 파악
    try:
        reader = csv.reader(StringIO(header), delimiter=delimiter)
        columns = next(reader, [])
    except Exception:
        columns = header.split(delimiter)

    num_cols = len(columns)

    # 샘플 행 (앞 10줄 + 뒤 10줄)
    sample_lines = []
    if total_lines <= 22:
        sample_lines = lines
    else:
        sample_lines = lines[:11]  # 헤더 + 앞 10줄
        sample_lines.append(f"... ({total_lines - 22}줄 생략) ...")
        sample_lines.extend(lines[-10:])  # 뒤 10줄

    # 파일 크기
    size_kb = len(content.encode("utf-8")) / 1024

    summary = f"""[CSV 요약] 총 {total_lines:,}줄 x {num_cols}컬럼 ({size_kb:.1f}KB)
컬럼: {', '.join(columns[:20])}{'...' if num_cols > 20 else ''}

--- 샘플 데이터 ---
{chr(10).join(sample_lines)}"""

    return summary


def _smart_read_large(lines: list, total_lines: int) -> str:
    """대용량 파일: 앞 200줄 + 뒤 50줄"""
    head = lines[:200]
    tail = lines[-50:]

    return f"""{chr(10).join(head)}

... (중간 {total_lines - 250}줄 생략, 총 {total_lines:,}줄) ...

{chr(10).join(tail)}"""


def save_file(project_id: str, file_path: str, content: str) -> dict:
    """파일 내용 저장 (직접 편집)"""
    project = get_project(project_id)
    if not project:
        return {"success": False, "error": "프로젝트를 찾을 수 없습니다"}

    fpath = Path(project["path"]) / file_path
    if not fpath.exists() or not fpath.is_file():
        return {"success": False, "error": "파일을 찾을 수 없습니다"}

    try:
        fpath.write_text(content, encoding="utf-8")
        if _git_available():
            subprocess.run(["git", "-C", project["path"], "add", str(fpath)], capture_output=True)
            subprocess.run(
                ["git", "-C", project["path"], "commit", "-m", f"Edit {file_path}"],
                capture_output=True, encoding="utf-8"
            )
        return {"success": True, "message": "저장 완료"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_new_file(project_id: str, file_path: str, content: str = "") -> dict:
    """새 파일 생성"""
    project = get_project(project_id)
    if not project:
        return {"success": False, "error": "프로젝트를 찾을 수 없습니다"}

    fpath = Path(project["path"]) / file_path
    if fpath.exists():
        return {"success": False, "error": "이미 존재하는 파일입니다"}

    try:
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content, encoding="utf-8")
        if _git_available():
            subprocess.run(["git", "-C", project["path"], "add", str(fpath)], capture_output=True)
            subprocess.run(
                ["git", "-C", project["path"], "commit", "-m", f"Create {file_path}"],
                capture_output=True, encoding="utf-8"
            )
        return {"success": True, "message": "파일 생성 완료"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_folder(project_id: str, folder_path: str) -> dict:
    """새 폴더 생성"""
    project = get_project(project_id)
    if not project:
        return {"success": False, "error": "프로젝트를 찾을 수 없습니다"}

    fpath = Path(project["path"]) / folder_path
    if fpath.exists():
        return {"success": False, "error": "이미 존재하는 폴더입니다"}

    try:
        fpath.mkdir(parents=True, exist_ok=True)
        (fpath / ".gitkeep").write_text("", encoding="utf-8")
        if _git_available():
            subprocess.run(["git", "-C", project["path"], "add", "-A"], capture_output=True)
            subprocess.run(
                ["git", "-C", project["path"], "commit", "-m", f"Create folder {folder_path}"],
                capture_output=True, encoding="utf-8"
            )
        return {"success": True, "message": "폴더 생성 완료"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def rename_file(project_id: str, old_path: str, new_name: str) -> dict:
    """파일/폴더 이름 변경"""
    project = get_project(project_id)
    if not project:
        return {"success": False, "error": "프로젝트를 찾을 수 없습니다"}

    old = Path(project["path"]) / old_path
    if not old.exists():
        return {"success": False, "error": "대상을 찾을 수 없습니다"}
    if not new_name.strip():
        return {"success": False, "error": "새 이름을 입력해주세요"}

    new = old.parent / new_name.strip()
    if new.exists():
        return {"success": False, "error": "같은 이름이 이미 존재합니다"}

    try:
        old.rename(new)
        if _git_available():
            subprocess.run(["git", "-C", project["path"], "add", "-A"], capture_output=True)
            subprocess.run(
                ["git", "-C", project["path"], "commit", "-m", f"Rename {old_path} -> {new_name}"],
                capture_output=True, encoding="utf-8"
            )
        return {"success": True, "message": "이름 변경 완료"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_file(project_id: str, file_path: str) -> dict:
    """파일/폴더 삭제"""
    project = get_project(project_id)
    if not project:
        return {"success": False, "error": "프로젝트를 찾을 수 없습니다"}

    target = Path(project["path"]) / file_path
    if not target.exists():
        return {"success": False, "error": "대상을 찾을 수 없습니다"}

    try:
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        if _git_available():
            subprocess.run(["git", "-C", project["path"], "add", "-A"], capture_output=True)
            subprocess.run(
                ["git", "-C", project["path"], "commit", "-m", f"Delete {file_path}"],
                capture_output=True, encoding="utf-8"
            )
        return {"success": True, "message": "삭제 완료"}
    except Exception as e:
        return {"success": False, "error": str(e)}
