"""
backend/ralph_orchestrator.py - 랄프 위검 루프 오케스트레이터.

활성 역할: 헤르메스→하네스 사이클을 반복하면서 매 사이클 5개 종료조건 평가.
mode("api" | "gguf") 분기는 호출자가 헤르메스/하네스 인스턴스를 주입해서 처리.
"""
import time


# 5개 종료조건 식별자
TERM_GOAL_MET = "goal_met"
TERM_MAX_ITER = "max_iter_reached"
TERM_REPEATED = "repeated_failure"
TERM_LOW_CONF = "low_classifier_confidence"
TERM_ABORT = "human_abort"


def _l2_severity_rank(sev):
    return {"NONE": 0, "LOW": 1, "MED": 2, "HIGH": 3}.get(sev or "NONE", 0)


def _score(l1, l2):
    """가중합 점수 — 높을수록 좋음."""
    if not l1 or not l1.get("ok"):
        return -10
    if not l2:
        return 0
    sev_penalty = _l2_severity_rank(l2.get("severity"))
    conf = float(l2.get("confidence", 0.0) or 0.0)
    return 10 - 2 * sev_penalty + conf  # NONE/0.9 → 10.9, HIGH/0.3 → 4.3


def evaluate_terminations(state):
    """현재 state 기반 종료조건 평가.

    state = {
        "iter": int, "max_iter": int, "aborted": bool,
        "history": [{"layer1":..., "layer2":...}, ...],  # 사이클별 결과
    }
    Returns: (should_stop: bool, reason: str|None, triggered: [str])
    """
    triggered = []
    history = state.get("history") or []

    if state.get("aborted"):
        triggered.append(TERM_ABORT)

    if state.get("iter", 0) >= state.get("max_iter", 20):
        triggered.append(TERM_MAX_ITER)

    if history:
        last = history[-1]
        l1, l2 = last.get("layer1"), last.get("layer2")
        if l1 and l1.get("ok") and l2 and l2.get("severity") == "NONE":
            triggered.append(TERM_GOAL_MET)

    # 직전 3 사이클 동일 카테고리
    if len(history) >= 3:
        cats = [(h.get("layer2") or {}).get("category") for h in history[-3:]]
        if cats[0] and all(c == cats[0] and c not in (None, "none") for c in cats):
            triggered.append(TERM_REPEATED)

    # 최근 5 사이클 평균 confidence < 0.6
    if len(history) >= 5:
        confs = [float((h.get("layer2") or {}).get("confidence", 0.0) or 0.0) for h in history[-5:]]
        if sum(confs) / 5 < 0.6:
            triggered.append(TERM_LOW_CONF)

    if not triggered:
        return False, None, []
    # 우선순위: abort > goal > max > repeat > low_conf
    order = [TERM_ABORT, TERM_GOAL_MET, TERM_MAX_ITER, TERM_REPEATED, TERM_LOW_CONF]
    for r in order:
        if r in triggered:
            return True, r, triggered
    return True, triggered[0], triggered


def run_loop(hermes, harness, md_spec, lang="Python", fw="", max_iter=20, abort_flag=None):
    """헤르메스→하네스 루프 generator. 매 사이클 dict yield.

    hermes/harness 는 elements_api 또는 elements_gguf 의 클래스 인스턴스 (duck typing).
    abort_flag: {"stop": bool} 같은 dict — 외부에서 stop=True 로 중단.

    Yields:
        {"event": "cycle", "iter": int, "code": str, "harness": {...}, "score": float}
        {"event": "done", "reason": str, "iter": int, "best": {...}}
    """
    state = {"iter": 0, "max_iter": max_iter, "aborted": False, "history": []}
    best = None
    t0 = time.time()

    while True:
        state["aborted"] = bool(abort_flag and abort_flag.get("stop"))

        # 헤르메스 생성
        try:
            gen = hermes.generate(md_spec, lang=lang, fw=fw)
        except Exception as e:
            yield {"event": "error", "iter": state["iter"], "phase": "hermes", "error": str(e)}
            return

        code = gen.get("code", "")

        # 하네스 검증
        try:
            verdict = harness.validate(code, run_l2=True)
        except Exception as e:
            yield {"event": "error", "iter": state["iter"], "phase": "harness", "error": str(e)}
            return

        state["history"].append({
            "layer1": verdict.get("layer1"),
            "layer2": verdict.get("layer2"),
        })
        sc = _score(verdict.get("layer1"), verdict.get("layer2"))
        if best is None or sc > best["score"]:
            best = {"iter": state["iter"], "code": code, "verdict": verdict, "score": sc}

        yield {
            "event": "cycle",
            "iter": state["iter"],
            "code": code,
            "harness": verdict,
            "score": sc,
            "elapsed": time.time() - t0,
        }

        state["iter"] += 1
        should_stop, reason, triggered = evaluate_terminations(state)
        if should_stop:
            yield {
                "event": "done",
                "reason": reason,
                "triggered": triggered,
                "iter": state["iter"],
                "best": best,
                "elapsed": time.time() - t0,
            }
            return
