"""
cli.py — 명령행 진입점

사용 예:
  python -m loop_engine.cli init                          # 작업공간 생성
  python -m loop_engine.cli skills                        # 등록된 스킬 목록
  python -m loop_engine.cli runs                          # 실행 이력
  python -m loop_engine.cli worklog -n 20                 # 작업로그 tail
  python -m loop_engine.cli signals                       # open 시그널
  python -m loop_engine.cli demo                          # 목 LLM 으로 루프 1회 시연

실제 루프는 보통 코드(examples/*.py)에서 LoopSystem 으로 등록해 돌린다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import LLMConfig, LoopConfig
from .orchestrator import LoopSystem


def _mk_system(workspace: str) -> LoopSystem:
    cfg = LoopConfig(base_dir=Path(workspace), llm=LLMConfig(endpoint="LOCAL"))
    return LoopSystem(cfg)


def cmd_init(args):
    sysm = _mk_system(args.workspace)
    print(f"[OK] 작업공간 생성: {sysm.cfg.base_dir}")
    for d in (sysm.cfg.runs_dir, sysm.cfg.artifacts_dir,
              sysm.cfg.skills_dir, sysm.cfg.contracts_dir):
        print(f"     - {d}")


def cmd_skills(args):
    sysm = _mk_system(args.workspace)
    names = sysm.skills.names()
    if not names:
        print("(스킬 없음 — skills/ 아래에 SKILL.md 를 두세요)")
        return
    for n in names:
        s = sysm.skills.get(n)
        print(f"- {n}: {s.description[:80] if s else ''}")


def cmd_runs(args):
    sysm = _mk_system(args.workspace)
    runs = sorted(sysm.cfg.runs_dir.glob("*/_run.json"))
    if not runs:
        print("(실행 이력 없음)")
        return
    import json
    for p in runs[-args.n:]:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            print(f"- {d.get('run_id')}: {d.get('status')} "
                  f"(created {d.get('created')})")
        except Exception:
            continue


def cmd_worklog(args):
    sysm = _mk_system(args.workspace)
    print(sysm.worklog.tail_text(args.n) or "(로그 없음)")


def cmd_signals(args):
    sysm = _mk_system(args.workspace)
    sigs = sysm.open_signals()
    if not sigs:
        print("(open 시그널 없음)")
        return
    for s in sigs:
        print(f"- [{s.kind}] {s.summary}  (sources={len(s.sources)})")


def cmd_demo(args):
    """엔드포인트 없이 목 LLM 으로 closed loop 1회 시연."""
    from .llm import LLMClient, make_mock_transport
    from .agents import Generator, VerifierAgent
    from .verifier import CheckSuite, check_min_length, check_contains
    from .loop import Loop, LoopSpec, LoopMode

    # 라운드가 진행될수록 좋아지는 목 응답
    state = {"n": 0}

    def responder(messages, model):
        # verifier 호출이면 JSON 점수 반환
        sys_txt = messages[0]["content"] if messages else ""
        if "평가자" in sys_txt or "evaluat" in sys_txt.lower():
            state["n"] += 1
            score = min(9.0, 6.0 + state["n"])
            return '{"score": %.1f, "reasons": "목 평가"}' % score
        # generator
        return ("# 제목\n폐쇄망 루프 엔지니어링 데모 산출물입니다. "
                "필수 키워드 '루프' 포함. " * 3)

    client = LLMClient(LLMConfig(endpoint="LOCAL"),
                       transport=make_mock_transport(responder))
    gen = Generator(client, model="qwen-demo")
    suite = CheckSuite([check_min_length(50), check_contains("루프")])
    from .verifier import Rubric
    ver = VerifierAgent(client, check_suite=suite,
                        rubric=Rubric("명료성/완결성", pass_score=8.0),
                        verifier_model="glm-demo", generator_model="qwen-demo")
    spec = LoopSpec(name="demo", goal="루프 데모 글 작성",
                    generator=gen, verifier=ver,
                    mode=LoopMode.CLOSED, max_rounds=5)
    result = Loop(spec).run()
    print(result.report())
    print("\n--- 최종 산출물(앞부분) ---")
    print(result.final_artifact[:200])


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="loop_engine",
                                description="폐쇄망 루프 엔지니어링 CLI")
    p.add_argument("-w", "--workspace", default="loop_workspace",
                   help="작업공간 경로 (기본: ./loop_workspace)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="작업공간 생성").set_defaults(func=cmd_init)
    sub.add_parser("skills", help="스킬 목록").set_defaults(func=cmd_skills)

    pr = sub.add_parser("runs", help="실행 이력")
    pr.add_argument("-n", type=int, default=20)
    pr.set_defaults(func=cmd_runs)

    pw = sub.add_parser("worklog", help="작업로그 tail")
    pw.add_argument("-n", type=int, default=10)
    pw.set_defaults(func=cmd_worklog)

    sub.add_parser("signals", help="open 시그널").set_defaults(func=cmd_signals)
    sub.add_parser("demo", help="목 LLM 루프 시연").set_defaults(func=cmd_demo)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
