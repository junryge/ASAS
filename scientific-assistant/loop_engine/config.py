"""
config.py — 루프 엔진 전역 설정 / 토큰 / 엔드포인트 레지스트리

폐쇄망 원칙:
  - 외부 의존성 0개 (stdlib only)
  - TOKEN.TXT 는 CWD 우선, 그 다음 환경변수
  - 내부 LLM 은 OpenAI 호환(/v1/chat/completions) 엔드포인트
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# 내부 LLM 엔드포인트 레지스트리 (DEV / COMMON / PROD ...)
#   필요시 환경에 맞게 이름/URL 수정. base_url 은 /v1 까지 포함하지 않아도 되며
#   LLMClient 가 알아서 /chat/completions 경로를 붙인다.
# ---------------------------------------------------------------------------
DEFAULT_ENDPOINTS: Dict[str, str] = {
    "DEV":     "https://dev.hcp.llm.skhynix.com/v1",
    "COMMON":  "https://common.llm.skhynix.com/v1",
    # 로컬 테스트용 (llama-cpp-python / FastAPI OpenAI 호환 서버)
    "LOCAL":   "http://127.0.0.1:10010/v1",
}


def load_token(explicit: Optional[str] = None,
               filename: str = "TOKEN.TXT",
               env_keys=("LLM_TOKEN", "OPENAI_API_KEY", "HCP_TOKEN")) -> str:
    """토큰 로딩 우선순위: 인자 > CWD/TOKEN.TXT > 환경변수 > 빈 문자열.

    빈 문자열을 허용하는 이유: 토큰 없는 로컬 서버(llama-cpp)에서도 동작해야 하기 때문.
    """
    if explicit:
        return explicit.strip()

    # 1) CWD 의 TOKEN.TXT 최우선
    p = Path.cwd() / filename
    if p.exists():
        try:
            return p.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    # 2) 환경변수
    for k in env_keys:
        v = os.environ.get(k)
        if v:
            return v.strip()

    return ""


@dataclass
class LLMConfig:
    """LLM 커넥터 설정."""
    endpoint: str = "LOCAL"                 # DEFAULT_ENDPOINTS 의 키
    base_url: Optional[str] = None          # 직접 지정시 endpoint 보다 우선
    token: Optional[str] = None             # None 이면 load_token() 사용
    generator_model: str = "gpt-oss-20b"    # '만드는 AI' 기본 모델
    verifier_model: str = "gpt-oss-20b"     # '검사하는 AI' 기본 모델 (가능하면 다른 모델로!)
    temperature: float = 0.7
    verifier_temperature: float = 0.0       # 검사는 결정적으로
    max_tokens: int = 2048
    timeout: int = 120
    verify_ssl: bool = False                # 사내 self-signed 대비 기본 False
    retries: int = 2

    def resolve_base_url(self) -> str:
        if self.base_url:
            return self.base_url.rstrip("/")
        url = DEFAULT_ENDPOINTS.get(self.endpoint)
        if not url:
            raise ValueError(
                f"알 수 없는 endpoint '{self.endpoint}'. "
                f"사용 가능: {list(DEFAULT_ENDPOINTS)} 또는 base_url 직접 지정."
            )
        return url.rstrip("/")

    def resolve_token(self) -> str:
        return load_token(self.token)


@dataclass
class LoopConfig:
    """루프 엔진 전역 설정. 모든 산출물/로그/계약이 base_dir 아래에 쌓인다."""
    base_dir: Path = field(default_factory=lambda: Path.cwd() / "loop_workspace")
    llm: LLMConfig = field(default_factory=LLMConfig)

    # 하위 디렉토리 이름 (워크트리 대체 = runs/ 격리, 공유 두뇌 = artifacts/)
    runs_dirname: str = "runs"
    artifacts_dirname: str = "artifacts"
    skills_dirname: str = "skills"
    contracts_dirname: str = "contracts"
    worklog_filename: str = "WORKLOG.md"

    def __post_init__(self):
        self.base_dir = Path(self.base_dir)

    # --- 경로 헬퍼 ---
    @property
    def runs_dir(self) -> Path:
        return self.base_dir / self.runs_dirname

    @property
    def artifacts_dir(self) -> Path:
        return self.base_dir / self.artifacts_dirname

    @property
    def skills_dir(self) -> Path:
        return self.base_dir / self.skills_dirname

    @property
    def contracts_dir(self) -> Path:
        return self.base_dir / self.contracts_dirname

    @property
    def worklog_path(self) -> Path:
        return self.base_dir / self.worklog_filename

    def ensure_dirs(self) -> "LoopConfig":
        for d in (self.base_dir, self.runs_dir, self.artifacts_dir,
                  self.skills_dir, self.contracts_dir):
            d.mkdir(parents=True, exist_ok=True)
        return self

    def to_dict(self) -> dict:
        d = asdict(self)
        d["base_dir"] = str(self.base_dir)
        return d
