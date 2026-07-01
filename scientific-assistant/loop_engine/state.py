"""
state.py — 부품 ⑥ 상태/기억 + 부품 ② 워크트리 대체(runs/ 격리)

핵심 명제: "에이전트는 잊어도, 저장소는 안 잊는다."
  - RunContext : 실행마다 runs/<run-id>/ 격리 폴더 (git worktree 없이 충돌 방지)
  - Artifact   : 수정금지 산출물 체인 (spec.json -> evidence.json -> draft.md -> qa_report.json -> final)
  - Signal     : 루프를 '복리'로 만드는 단위 (아이디어/마찰/기회 + 출처)
  - WorkLog    : 전역 append-only 로그. 큰 작업 전 최근 N개 읽고, 끝나면 추가
  - Contract   : 루프당 계약(README) — 목표/워크플로/경계/백로그/타임라인
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ts_compact() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def new_run_id(prefix: str = "run") -> str:
    return f"{prefix}_{_ts_compact()}_{uuid.uuid4().hex[:6]}"


# ---------------------------------------------------------------------------
# RunContext — 실행 격리 (워크트리 대체)
# ---------------------------------------------------------------------------
class RunContext:
    """runs/<run-id>/ 한 폴더 = 한 실행. 동시에 여러 개 돌려도 서로 안 닿는다.

    git worktree 를 쓰지 않는 이유(폐쇄망 + 모놀리식/콘텐츠 특성):
    각 실행을 디렉토리로 분리하면 충돌은 이미 막힌다. 워크트리는 과함.
    """

    def __init__(self, runs_dir: Path, run_id: Optional[str] = None,
                 prefix: str = "run"):
        self.runs_dir = Path(runs_dir)
        self.run_id = run_id or new_run_id(prefix)
        self.dir = self.runs_dir / self.run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self._meta = {
            "run_id": self.run_id,
            "created": _now_iso(),
            "status": "running",
        }
        self._save_meta()

    def _save_meta(self):
        (self.dir / "_run.json").write_text(
            json.dumps(self._meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def path(self, name: str) -> Path:
        return self.dir / name

    def set_status(self, status: str, **extra):
        self._meta["status"] = status
        self._meta["updated"] = _now_iso()
        self._meta.update(extra)
        self._save_meta()

    # 산출물 체인 헬퍼
    def write_json(self, name: str, data: Any) -> Path:
        p = self.path(name)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return p

    def read_json(self, name: str, default=None) -> Any:
        p = self.path(name)
        if not p.exists():
            return default
        return json.loads(p.read_text(encoding="utf-8"))

    def write_text(self, name: str, text: str) -> Path:
        p = self.path(name)
        p.write_text(text, encoding="utf-8")
        return p

    def read_text(self, name: str, default: str = "") -> str:
        p = self.path(name)
        return p.read_text(encoding="utf-8") if p.exists() else default


# ---------------------------------------------------------------------------
# Artifact — 프론트매터 + 본문 + 변경 타임라인
# ---------------------------------------------------------------------------
@dataclass
class Artifact:
    """공유 지식층의 한 항목. 메타/본문/타임라인을 갖는다."""
    kind: str                                   # docs / signals / tasks / tickets ...
    id: str
    title: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)
    body: str = ""
    timeline: List[Dict[str, str]] = field(default_factory=list)
    created: str = field(default_factory=_now_iso)

    def log(self, event: str):
        self.timeline.append({"ts": _now_iso(), "event": event})

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Artifact":
        return cls(**d)


@dataclass
class Signal:
    """루프를 복리로 만드는 단위.
    제품 아이디어/마찰/놓친 기회를 잡아, 원천(티켓·고객발언)에 링크한다.
    어떤 루프든 읽고 쓸 수 있다.
    """
    id: str
    summary: str
    kind: str = "friction"                      # friction / idea / opportunity / bug
    sources: List[str] = field(default_factory=list)
    status: str = "open"                        # open / picked / done
    created_by: str = ""
    created: str = field(default_factory=_now_iso)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class ArtifactStore:
    """artifacts/<kind>/<id>.json 으로 영속. 공유 두뇌."""

    def __init__(self, artifacts_dir: Path):
        self.root = Path(artifacts_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def _kind_dir(self, kind: str) -> Path:
        d = self.root / kind
        d.mkdir(parents=True, exist_ok=True)
        return d

    def put(self, art: Artifact) -> Path:
        p = self._kind_dir(art.kind) / f"{art.id}.json"
        p.write_text(json.dumps(art.to_dict(), ensure_ascii=False, indent=2),
                     encoding="utf-8")
        return p

    def get(self, kind: str, id: str) -> Optional[Artifact]:
        p = self._kind_dir(kind) / f"{id}.json"
        if not p.exists():
            return None
        return Artifact.from_dict(json.loads(p.read_text(encoding="utf-8")))

    def list(self, kind: str) -> List[Artifact]:
        out = []
        for p in sorted(self._kind_dir(kind).glob("*.json")):
            try:
                out.append(Artifact.from_dict(json.loads(p.read_text(encoding="utf-8"))))
            except Exception:
                continue
        return out

    # --- signals 전용 (복리의 핵심) ---
    def emit_signal(self, sig: Signal) -> Path:
        d = self._kind_dir("signals")
        p = d / f"{sig.id}.json"
        p.write_text(json.dumps(sig.to_dict(), ensure_ascii=False, indent=2),
                     encoding="utf-8")
        return p

    def read_signals(self, status: Optional[str] = None) -> List[Signal]:
        out = []
        for p in sorted(self._kind_dir("signals").glob("*.json")):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                sig = Signal(**d)
                if status is None or sig.status == status:
                    out.append(sig)
            except Exception:
                continue
        return out

    def update_signal_status(self, sig_id: str, status: str) -> bool:
        p = self._kind_dir("signals") / f"{sig_id}.json"
        if not p.exists():
            return False
        d = json.loads(p.read_text(encoding="utf-8"))
        d["status"] = status
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        return True


# ---------------------------------------------------------------------------
# WorkLog — 전역 append-only 작업로그
# ---------------------------------------------------------------------------
class WorkLog:
    """세션 간 컨텍스트 생존용 단일 글로벌 로그.
    큰 작업 전: 최근 5~10개 읽기 / 끝나면: append.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("# WORKLOG\n\n", encoding="utf-8")

    def append(self, who: str, action: str, detail: str = ""):
        entry = f"- [{_now_iso()}] **{who}** — {action}"
        if detail:
            entry += f"  \n  {detail}"
        with self.path.open("a", encoding="utf-8") as f:
            f.write(entry + "\n")

    def tail(self, n: int = 10) -> List[str]:
        lines = [ln for ln in self.path.read_text(encoding="utf-8").splitlines()
                 if ln.strip().startswith("- [")]
        return lines[-n:]

    def tail_text(self, n: int = 10) -> str:
        return "\n".join(self.tail(n))


# ---------------------------------------------------------------------------
# Contract — 루프당 계약 (목표/워크플로/경계/백로그/타임라인)
# ---------------------------------------------------------------------------
@dataclass
class Contract:
    """루프가 매 실행 전에 먼저 읽는 계약서."""
    loop_name: str
    goal: str
    workflow: str = ""
    boundaries: str = ""
    backlog: List[str] = field(default_factory=list)
    timeline: List[Dict[str, str]] = field(default_factory=list)

    def log(self, event: str):
        self.timeline.append({"ts": _now_iso(), "event": event})

    def to_markdown(self) -> str:
        bl = "\n".join(f"- {b}" for b in self.backlog) or "- (없음)"
        tl = "\n".join(f"- [{t['ts']}] {t['event']}" for t in self.timeline) or "- (없음)"
        return (
            f"# CONTRACT: {self.loop_name}\n\n"
            f"## Goal\n{self.goal}\n\n"
            f"## Workflow\n{self.workflow or '(미정)'}\n\n"
            f"## Boundaries\n{self.boundaries or '(없음)'}\n\n"
            f"## Backlog\n{bl}\n\n"
            f"## Timeline\n{tl}\n"
        )

    def save(self, contracts_dir: Path) -> Path:
        Path(contracts_dir).mkdir(parents=True, exist_ok=True)
        p = Path(contracts_dir) / f"{self.loop_name}.json"
        p.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2),
                     encoding="utf-8")
        (Path(contracts_dir) / f"{self.loop_name}.md").write_text(
            self.to_markdown(), encoding="utf-8")
        return p

    @classmethod
    def load(cls, contracts_dir: Path, loop_name: str) -> Optional["Contract"]:
        p = Path(contracts_dir) / f"{loop_name}.json"
        if not p.exists():
            return None
        return cls(**json.loads(p.read_text(encoding="utf-8")))
