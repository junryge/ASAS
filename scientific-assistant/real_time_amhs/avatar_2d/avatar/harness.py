# -*- coding: utf-8 -*-
"""
harness.py — 서윤의 하네스 + 루프 (loop_engine 의 핵심을 네이티브 포팅)

왜 필요한가
    한 번 만들고 끝내면 "그럴듯한 것" 이 나온다. 스킬 초안은 절이 빠지고,
    분석 답은 한 순간만 집어 말한다 — 실제로 둘 다 겪었다.
    loop_engine 의 구조가 답이다:  execute → verify → (부족하면 그 이유를
    붙여) 다시 execute … 조건을 만족하거나 최대 라운드까지.

loop_engine 에서 가져온 것 / 버린 것
    가져옴: Check/CheckSuite(하드체크), Verdict, 라운드 루프, 최고점 보존,
            "critical 하나라도 실패면 불합격", 피드백을 다음 라운드에 주입
    버림  : 검사하는 **AI**(VerifierAgent), 루브릭 LLM 채점, discover/plan
            에이전트 — 아바타는 LLM 호출이 곧 비용·지연이라, 검사는
            **결정적 규칙**으로만 한다. 규칙으로 못 잡는 것만 사람이 본다.

원칙
    · 검사는 재료로 한다. "재료에 없는 숫자" 는 재료를 보면 알 수 있다.
    · 실패는 이유를 남긴다 — 다음 라운드에 그 이유를 그대로 붙여 준다.
    · 최대 라운드는 필수다. 안 되면 안 된 채로 내놓되 **무엇이 모자란지 밝힌다.**
"""
import re

MAX_ROUNDS = 3           # 무한루프 방지. 3라운드면 대개 붙거나 안 붙는다


class Check:
    """검사 하나. fn(artifact, material) -> (ok, 왜 실패했나)"""

    def __init__(self, name, fn, critical=True, why=""):
        self.name = name
        self.fn = fn
        self.critical = critical
        self.why = why

    def run(self, artifact, material=""):
        try:
            ok, detail = self.fn(artifact, material)
        except Exception as e:                       # noqa: BLE001
            return False, "검사 중 오류({}): {}".format(self.name, e)
        return bool(ok), ("" if ok else (detail or self.why or self.name))


class Verdict:
    """한 라운드의 판정."""

    def __init__(self, results):
        self.results = results                       # [(Check, ok, detail)]

    @property
    def failures(self):
        return [(c, d) for c, ok, d in self.results if not ok]

    @property
    def critical_failures(self):
        return [(c, d) for c, ok, d in self.results if not ok and c.critical]

    @property
    def passed(self):
        return not self.critical_failures

    @property
    def score(self):
        """통과한 검사 수 — 미달이어도 '가장 나은 라운드' 를 고르는 기준."""
        return sum(1 for _c, ok, _d in self.results if ok)

    def feedback(self):
        """다음 라운드에 그대로 붙일 지적."""
        if not self.failures:
            return ""
        L = ["다음을 고쳐서 다시 써 주세요:"]
        for c, d in self.failures:
            L.append("- {}{}".format(d, "" if c.critical else " (권고)"))
        return "\n".join(L)

    def gaps_text(self):
        """끝내 못 고친 것 — 사용자에게 정직하게 밝힐 문장."""
        left = [d for _c, d in self.failures]
        return " / ".join(left)


def run_loop(generate, checks, material="", max_rounds=MAX_ROUNDS, on_round=None):
    """execute → verify → 재시도. 반환 {ok, artifact, verdict, rounds}.

    generate(feedback) -> artifact(str). 첫 라운드는 feedback="".
    최고점 라운드를 보존한다 — 3라운드가 1라운드보다 나쁠 수도 있다.
    """
    best, best_v, rounds = None, None, 0
    feedback = ""
    for i in range(1, int(max_rounds) + 1):
        rounds = i
        art = generate(feedback)
        if not art:
            break
        v = Verdict([(c,) + c.run(art, material) for c in checks])
        if on_round:
            on_round(i, art, v)
        if best_v is None or v.score > best_v.score:
            best, best_v = art, v
        if v.passed:
            return {"ok": True, "artifact": art, "verdict": v, "rounds": i}
        feedback = v.feedback()
    return {"ok": False, "artifact": best, "verdict": best_v, "rounds": rounds}


# ────────────────────────── 자주 쓰는 검사 ──────────────────────────
def has_sections(sections):
    def fn(art, _m):
        miss = [s for s in sections if s not in art]
        return (not miss), "빠진 절: " + ", ".join(miss) if miss else ""
    return Check("절 존재", fn, True)


_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def numbers_from(text):
    out = set()
    for m in _NUM.findall(str(text or "")):
        try:
            out.add(round(float(m), 2))
        except ValueError:
            pass
    return out


def numbers_in_material(allow_extra=(), tol=1.0):
    """★재료에 없는 숫자를 쓰면 그 스킬은 다음 사람을 속인다.

    번호 매기기(1. 2. 3.)와 흔한 작은 수는 봐준다 — 그것까지 잡으면
    아무 문장도 못 쓴다.
    """
    def fn(art, material):
        have = numbers_from(material) | {round(float(x), 2) for x in allow_extra}
        bad = []
        for line in str(art or "").splitlines():
            body = re.sub(r"^\s*\d+[.)]\s", "", line)      # 목록 번호는 제외
            for n in numbers_from(body):
                if abs(n) <= 10 and float(n).is_integer():
                    continue                               # 작은 정수는 봐준다
                if any(abs(n - h) <= tol * 0.01 * max(1.0, abs(h)) for h in have):
                    continue
                bad.append(n)
        bad = sorted(set(bad))[:6]
        return (not bad), ("재료에 없는 숫자를 썼습니다: {} — 재료의 값만 쓰거나 "
                           "'확인 필요' 라고 적어 주세요.".format(bad) if bad else "")
    return Check("숫자 근거", fn, True)


def no_rule_codes():
    from . import terms

    def fn(art, _m):
        found = terms.CODE_RE.findall(str(art or ""))
        return (not found), ("룰 코드를 그대로 썼습니다 — 한글 이름으로 "
                             "바꿔 주세요." if found else "")
    return Check("룰 코드 금지", fn, True)


def min_length(n):
    def fn(art, _m):
        ln = len(str(art or "").strip())
        return ln >= n, "너무 짧습니다({}자) — {}자 이상 써 주세요.".format(ln, n)
    return Check("최소 분량", fn, True)


def no_placeholder(tokens=("TODO", "FIXME", "생략", "...", "<여기에")):
    def fn(art, _m):
        hit = [t for t in tokens if t in str(art or "")]
        return (not hit), ("채우다 만 자리가 있습니다: {}".format(hit) if hit else "")
    return Check("빈자리 없음", fn, True)


def mentions_any(words, name, why, critical=True):
    def fn(art, _m):
        ok = any(w in str(art or "") for w in words)
        return ok, why
    return Check(name, fn, critical)
