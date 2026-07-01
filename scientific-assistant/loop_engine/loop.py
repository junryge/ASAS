"""
loop.py — 루프 코어. discover -> plan -> execute -> verify -> (조건까지 반복)

루프 = generator(짓는 AI) + verifier(검사하는 AI) 를 엮어 '조건 만족까지' 자동 반복.
당신은 루프 안에서 매 스텝 엔터를 누르던 자리에서 빠져나와, 트랙을 설계한다.

  - Open loop  : 목표 + 느슨한 조건 → 넓게 탐색. 참신하지만 토큰 태우고 슬롭 위험.
  - Closed loop: 성공기준 미리 못박고 매 스텝 평가 + 명시적 stop. 예측가능/안전.
  실전 트릭: closed 하드체크를 '바닥'으로 깔고 그 위에 open 지시 하나 → 기준 밑으로 안 떨어지는 탐색.

stop: (모든 critical 체크 통과 AND 루브릭 통과) OR max_rounds 도달.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .agents import Agent, Generator, VerifierAgent
from .state import RunContext, WorkLog
from .verifier import Verdict


class LoopMode(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class LoopStatus(str, Enum):
    SHIPPED = "shipped"          # 조건 만족, 출시
    EXHAUSTED = "exhausted"      # max_rounds 소진(미달)
    ERROR = "error"


@dataclass
class Round:
    index: int
    artifact: str
    verdict: Verdict
    ts: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@dataclass
class LoopResult:
    status: LoopStatus
    rounds: List[Round] = field(default_factory=list)
    best: Optional[Round] = None
    run_dir: Optional[str] = None

    @property
    def final_artifact(self) -> str:
        return self.best.artifact if self.best else ""

    @property
    def n_rounds(self) -> int:
        return len(self.rounds)

    def report(self) -> str:
        lines = [f"STATUS: {self.status.value}  (rounds={self.n_rounds})"]
        if self.run_dir:
            lines.append(f"RUN_DIR: {self.run_dir}")
        for r in self.rounds:
            mark = "✅" if r.verdict.done else "🔁"
            score = ""
            if r.verdict.rubric:
                score = f" score={r.verdict.rubric.score}"
            fails = len(r.verdict.critical_failures)
            lines.append(f"  {mark} round {r.index}{score} critical_fail={fails}")
        return "\n".join(lines)


@dataclass
class LoopSpec:
    """루프 한 벌의 정의."""
    name: str
    goal: str                                       # done 의 정의는 '측정 가능'하게
    generator: Generator
    verifier: VerifierAgent
    mode: LoopMode = LoopMode.CLOSED
    max_rounds: int = 5                             # 무한루프 방지 (필수)
    context_provider: Optional[Callable[[], str]] = None   # discover: 매 라운드 맥락 주입
    open_instruction: str = ""                      # closed 바닥 위에 얹는 탐색 지시
    keep_best_by_rubric: bool = True                # 미달이라도 최고점 라운드 보존
    planner: Optional["Agent"] = None               # 선택: plan 단계 분리(없으면 generator 가 plan+execute)
    plan_once: bool = True                          # True=첫 라운드만 계획, False=매 라운드 재계획


class Loop:
    """LoopSpec 을 받아 실제로 돌린다."""

    def __init__(self, spec: LoopSpec,
                 worklog: Optional[WorkLog] = None,
                 on_round: Optional[Callable[[Round], None]] = None):
        self.spec = spec
        self.worklog = worklog
        self.on_round = on_round

    def run(self, run_ctx: Optional[RunContext] = None) -> LoopResult:
        spec = self.spec
        rounds: List[Round] = []
        best: Optional[Round] = None
        feedback = ""
        plan_text = ""

        if self.worklog:
            self.worklog.append(spec.name, "loop start", f"goal: {spec.goal[:80]}")

        try:
            for i in range(1, spec.max_rounds + 1):
                # --- discover: 맥락 주입 ---
                context = spec.context_provider() if spec.context_provider else ""
                if spec.mode == LoopMode.OPEN and spec.open_instruction:
                    context = (context + "\n\n[탐색 지시]\n" + spec.open_instruction).strip()

                # --- plan: 선택적 planner (없으면 generator 가 plan+execute 동시) ---
                if spec.planner is not None and (i == 1 or not spec.plan_once):
                    plan_prompt = (f"[목표]\n{spec.goal}\n"
                                   + (f"\n[맥락]\n{context}\n" if context else "")
                                   + (f"\n[직전 피드백]\n{feedback}\n" if feedback else "")
                                   + "\n위 목표를 달성할 단계별 계획을 간결히 작성하라.")
                    plan_text = spec.planner.run(plan_prompt)
                    if run_ctx and i == 1:
                        run_ctx.write_text("plan.md", plan_text)
                ctx_for_gen = context
                if plan_text:
                    ctx_for_gen = (context + "\n\n[계획]\n" + plan_text).strip()

                # --- execute: 짓는 AI ---
                artifact = spec.generator.generate(
                    goal=spec.goal, context=ctx_for_gen, prior_feedback=feedback)

                # --- verify: 검사하는 AI ---
                verdict = spec.verifier.verify(artifact, spec.goal)

                rnd = Round(index=i, artifact=artifact, verdict=verdict)
                rounds.append(rnd)

                # 산출물 디스크 보존 (에이전트는 잊어도 저장소는 안 잊는다)
                if run_ctx:
                    run_ctx.write_text(f"round_{i:02d}_artifact.txt", artifact)
                    run_ctx.write_text(f"round_{i:02d}_verdict.txt", verdict.summary())

                # best 갱신
                if best is None:
                    best = rnd
                elif spec.keep_best_by_rubric and verdict.rubric and best.verdict.rubric:
                    if verdict.rubric.score > best.verdict.rubric.score:
                        best = rnd
                elif verdict.done and not best.verdict.done:
                    best = rnd

                if self.on_round:
                    self.on_round(rnd)
                if self.worklog:
                    sc = verdict.rubric.score if verdict.rubric else "-"
                    self.worklog.append(spec.name, f"round {i}",
                                        f"done={verdict.done} score={sc}")

                # --- stop 판정 ---
                if verdict.done:
                    best = rnd
                    result = LoopResult(LoopStatus.SHIPPED, rounds, best,
                                        run_ctx.dir.as_posix() if run_ctx else None)
                    if run_ctx:
                        run_ctx.write_text("final_artifact.txt", best.artifact)
                        run_ctx.set_status("shipped", rounds=i)
                    if self.worklog:
                        self.worklog.append(spec.name, "SHIPPED", f"round {i}")
                    return result

                # 미달 → 피드백 만들어 다음 라운드로 되돌림
                feedback = verdict.feedback_for_retry()

            # max_rounds 소진
            result = LoopResult(LoopStatus.EXHAUSTED, rounds, best,
                                run_ctx.dir.as_posix() if run_ctx else None)
            if run_ctx:
                if best:
                    run_ctx.write_text("final_artifact.txt", best.artifact)
                run_ctx.set_status("exhausted", rounds=spec.max_rounds)
            if self.worklog:
                self.worklog.append(spec.name, "EXHAUSTED",
                                    f"{spec.max_rounds} rounds, 미달")
            return result

        except Exception as e:
            if run_ctx:
                run_ctx.set_status("error", error=str(e))
            if self.worklog:
                self.worklog.append(spec.name, "ERROR", str(e))
            return LoopResult(LoopStatus.ERROR, rounds, best,
                              run_ctx.dir.as_posix() if run_ctx else None)
