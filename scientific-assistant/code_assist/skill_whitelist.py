"""
code_assist_v1/skill_whitelist.py - 코딩 어시스턴트에 도움이 되는 스킬만 선별

scientific-skills/ 355개 중 코딩 어시스턴스에 직접 도움 되는 약 80~120개만 노출.
사용자가 UI에서 "전체 보기" 토글을 켜면 모든 스킬을 노출하는 옵션도 둠.
"""
from __future__ import annotations
import json
import os
import re
from typing import Iterable

# ── 1) 명시적 단일 스킬 (메타·개발도구·핵심 슈퍼파워) ──
CODING_EXACT: set[str] = {
    # 슈퍼파워 메타 스킬 (Claude Code 워크플로우)
    "skill-creator",
    "test-driven-development",
    "systematic-debugging",
    "verification-before-completion",
    "requesting-code-review",
    "brainstorming",
    "using-superpowers",
    "writing-skills",
    "writing-plans",
    "knowledge-search",  # 수동 토글용

    # 개발 도구
    "chrome-devtools",
    "git",
    "github",
    "github-cli",
    "github-actions",
    "vscode",
    "docker",
    "kubernetes",
    "terraform",
    "ansible",
    "bash",
    "powershell",
    "make",
    "cmake",
    "vim",
    "emacs",
    "tmux",

    # 빌드·번들링·패키징
    "webpack",
    "vite",
    "rollup",
    "esbuild",
    "npm",
    "yarn",
    "pnpm",
    "pip",
    "poetry",
    "uv",
    "cargo",
    "gradle",
    "maven",

    # 테스트·CI
    "pytest",
    "jest",
    "playwright",
    "cypress",
    "junit",
    "circleci",
    "jenkins",
    "githubworkflow",

    # DB·인프라
    "postgres",
    "mysql",
    "mongodb",
    "redis",
    "sqlite",
    "elasticsearch",
    "kafka",
    "rabbitmq",
}

# ── 2) 코딩 관련 prefix (이걸로 시작하는 폴더명은 통과) ──
CODING_PREFIXES: tuple[str, ...] = (
    "writing-",
    "code-",
    "developer-",
    "frontend-",
    "backend-",
    "fullstack-",
    "devops-",
    "infra-",
    "platform-",
    "test-",
    "debug-",
    "review-",
    "refactor-",
)

# ── 3) 코딩 관련 agent-* 키워드 (description 또는 폴더명에 포함) ──
CODING_AGENT_KEYWORDS: tuple[str, ...] = (
    "python", "javascript", "typescript", "java", "kotlin", "go", "rust", "ruby",
    "csharp", "cpp", "c-plus-plus", "swift", "scala", "haskell", "elixir",
    "react", "vue", "angular", "svelte", "next", "nuxt", "remix",
    "node", "deno", "bun", "express", "fastify", "nest",
    "fastapi", "django", "flask", "rails", "laravel", "spring",
    "frontend", "backend", "fullstack", "mobile", "android", "ios",
    "devops", "sre", "platform", "infra", "cloud",
    "aws", "azure", "gcp", "vercel", "netlify",
    "code-review", "code-reviewer", "debug", "refactor", "optimize",
    "architect", "api", "graphql", "rest", "websocket",
    "database", "sql", "nosql", "orm",
    "testing", "qa", "security",
    "performance", "profiling", "scalability",
    "data-engineer", "ml-engineer", "ai-engineer",  # 코딩 비중 큼
)

# ── 4) 비-코딩 도메인 차단 prefix (명시 차단) ──
NON_CODING_PREFIXES: tuple[str, ...] = (
    "adaptyv", "aeon", "biopython", "rdkit", "pymol", "openbabel",
    "astropy", "scanpy", "anndata", "scvi", "biolab", "biolab-",
    "cclib", "chemml", "deepchem", "openmm", "gromacs", "lammps",
    "qiskit", "cirq", "psi4", "vasp", "gpaw",
    "obspy", "metpy", "iris", "xarray-cf",
    "freecad", "openfoam", "fenics", "firedrake",
    "monai", "nibabel", "dicom",  # 의료영상
    "neurokit", "mne",  # 신경과학
)

# ── 5) 비-코딩 agent 키워드 (description에 있으면 차단) ──
NON_CODING_AGENT_KEYWORDS: tuple[str, ...] = (
    "protein", "chemistry", "chemist", "molecul",
    "medical", "clinical", "patient", "healthcare",
    "finance", "marketing", "sales", "legal", "lawyer",
    "biology", "biolog", "genom", "rna", "dna",
    "astronom", "physic-", "quantum-physics",
    "geosci", "weather", "climate-",
)


def _matches_any(name: str, patterns: Iterable[str]) -> bool:
    n = name.lower()
    return any(p.lower() in n for p in patterns)


def _starts_with_any(name: str, prefixes: Iterable[str]) -> bool:
    n = name.lower()
    return any(n.startswith(p.lower()) for p in prefixes)


def is_coding_skill(skill_name: str, description: str = "") -> bool:
    """이름·설명을 보고 코딩 어시스턴트에 노출할지 결정."""
    n = skill_name.lower()
    desc = (description or "").lower()

    # 명시적 차단 우선
    if _starts_with_any(n, NON_CODING_PREFIXES):
        return False
    if n.startswith("agent-") and _matches_any(desc + " " + n, NON_CODING_AGENT_KEYWORDS):
        return False

    # 명시적 허용
    if n in {x.lower() for x in CODING_EXACT}:
        return True
    if _starts_with_any(n, CODING_PREFIXES):
        return True
    if n.startswith("agent-") and _matches_any(desc + " " + n, CODING_AGENT_KEYWORDS):
        return True

    # 가이드/문서 종류 (skill_name 에 'guide', 'tutorial' 들어있는데 도메인이 코딩이면 위에서 잡힘)
    return False


def filter_coding_skills(all_skills: dict[str, dict]) -> list[str]:
    """{skill_id: {description, ...}} 에서 코딩 스킬만 선별.

    Args:
        all_skills: scan_skills() 결과 또는 ToolRegistry → dict 변환 결과

    Returns:
        코딩 스킬 ID 목록 (정렬됨)
    """
    out = []
    for sid, info in all_skills.items():
        desc = info.get("description", "") if isinstance(info, dict) else str(info)
        if is_coding_skill(sid, desc):
            out.append(sid)
    return sorted(out)


# ── 사용자 편집 가능 화이트리스트 (skill_whitelist.json) ──
def load_user_whitelist(path: str) -> dict | None:
    """사용자가 편집한 화이트리스트 로드. {include: [...], exclude: [...], show_all: bool}"""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_user_whitelist(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def apply_user_overrides(skill_ids: list[str], overrides: dict | None) -> list[str]:
    """자동 선별 결과에 사용자 override 적용."""
    if not overrides:
        return skill_ids
    out = set(skill_ids)
    for inc in overrides.get("include", []) or []:
        out.add(inc)
    for exc in overrides.get("exclude", []) or []:
        out.discard(exc)
    return sorted(out)
