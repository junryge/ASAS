"""code_assist_v1/ctxbudget.py — 컨텍스트 예산을 한 곳에서 나눈다.

무엇이 이상했나
    ① 스킬 예산이 DEFAULT_N_CTX 로 계산되는데 그 값이 **4096** 이었다.
       128,000 토큰짜리 모델을 골라도 스킬은 늘 2,000자만 들어갔다.
       고른 모델이 뭐든 상관이 없었다.
    ② **아무도 합계를 안 봤다.** 스킬·지식·워크스페이스가 각자 제 상한만
       지켰다. 작은 모델에서는 이미 넘치고 있었다:

         spark-gemma4-12b (16k):  입력 12,858 + 답변 16,384 = 29,242 ❌
         spark-qwen36-35b (32k):  입력 21,050 + 답변 16,384 = 37,434 ❌

       넘치면 업스트림이 거절하거나 조용히 잘라 버린다. 어느 쪽이든
       사용자는 왜 답이 이상한지 알 수 없다.
    ③ 대화 이력을 '턴 수'(12턴)로 잘랐다. 코드가 붙은 12턴과 인사말 12턴은
       크기가 백 배 다르다. 토큰으로 세야 한다.

어떻게 바꿨나
    쓸 수 있는 자리를 먼저 계산하고(모델 한도 − 답변 − 안전여유),
    우선순위대로 나눠 준다. 모자라면 **뒤쪽부터** 줄인다.

      시스템 프롬프트 > 지금 질문 > 첨부 파일 > 스킬 > 도메인 지식 > 이력

    첨부 파일을 스킬·지식보다 위에 둔 건, 코딩 에이전트에서 "지금 보고 있는
    코드" 가 제일 중요하기 때문이다. 그게 없으면 나머지가 다 있어도 못 고친다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict

_HANGUL = re.compile(r"[가-힣]")

# 글자 → 토큰 어림. 한글은 한 글자가 거의 한 토큰이고, 영문 코드는 3~4자에
# 하나다. 뭉뚱그려 하나로 잡으면 한쪽이 크게 틀리므로 나눠서 센다.
# ★넘치는 쪽이 훨씬 나쁘므로(업스트림 거절/무단 절단) 넉넉히 잡는다.
CHARS_PER_TOKEN_KO = 1.5
CHARS_PER_TOKEN_EN = 3.2


def est_tokens(text: str) -> int:
    """글자 수로 토큰을 어림한다 (토크나이저 없이, 보수적으로)."""
    if not text:
        return 0
    ko = len(_HANGUL.findall(text))
    other = len(text) - ko
    return int(ko / CHARS_PER_TOKEN_KO + other / CHARS_PER_TOKEN_EN) + 1


def est_chars(tokens: int) -> int:
    """토큰 예산 → 글자 예산 (한글이 섞여 있다고 보고 보수적으로)."""
    return max(0, int(tokens * 2.2))


@dataclass
class Budget:
    n_ctx: int
    reply: int              # 답변에 남겨 둘 토큰
    safety: int             # 채팅 템플릿·오차 여유
    system: int             # 페르소나+수정계약 (실측치)
    skills: int
    knowledge: int
    workspace: int
    history: int
    # 시스템 프롬프트만으로 이미 한도를 넘는 상태. 예산으로는 못 고친다 —
    # 부르는 쪽이 프롬프트를 줄이거나 더 큰 모델로 바꿔야 한다.
    # ★조용히 넘기면 API 400 / GGUF 크래시로 튄다. 반드시 말해 준다.
    system_overflow: bool = False

    @property
    def input_total(self) -> int:
        return self.system + self.skills + self.knowledge + self.workspace + self.history

    def fits(self) -> bool:
        return self.input_total + self.reply + self.safety <= self.n_ctx

    def to_json(self) -> dict:
        d = asdict(self)
        d["input_total"] = self.input_total
        d["fits"] = self.fits()
        return d


# 남는 자리를 어떤 비율로 나눌지. 합이 1 을 넘어도 된다 — 아래에서 우선순위
# 대로 깎으며 맞춘다. 첨부 파일에 제일 크게 준다(코딩 에이전트니까).
SHARE = {"workspace": 0.50, "history": 0.22, "skills": 0.16, "knowledge": 0.12}

# 아무리 좁아도 이만큼은 준다 (0 이 되면 기능이 통째로 죽는다)
FLOOR = {"workspace": 1500, "history": 600, "skills": 400, "knowledge": 400}

# 우선순위 낮은 것부터 깎는다
_SHRINK_ORDER = ["knowledge", "skills", "history", "workspace"]


def plan(
    n_ctx: int | None,
    reply_cap: int,
    system_tokens: int,
    *,
    want_skills: bool = True,
    want_knowledge: bool = True,
    want_workspace: bool = True,
    safety: int = 768,
) -> Budget:
    """모델 한도 안에 반드시 들어가는 예산표를 만든다.

    system_tokens 는 이미 만들어진 시스템 프롬프트의 실측 토큰이다 —
    이건 못 줄이므로 먼저 빼고 시작한다.
    """
    n_ctx = int(n_ctx or 32768)
    # ★답변 자리를 먼저 확보한다. 예전엔 max_tokens 를 16384 로 잡아 놓고
    #   입력을 가득 채워, 모델이 답을 쓸 자리가 없었다.
    reply = max(512, min(int(reply_cap or 4096), int(n_ctx * 0.4)))
    free = n_ctx - reply - safety - system_tokens

    overflow = False
    if free <= 0:
        # 시스템 프롬프트만으로 꽉 찼다 — 답변 자리를 줄여서라도 최소한 굴린다
        reply = max(256, n_ctx - system_tokens - safety - 256)
        free = max(0, n_ctx - reply - safety - system_tokens)
        # 그래도 안 들어가면 예산으로는 못 고친다. 숨기지 말고 표시한다.
        overflow = system_tokens + reply + safety > n_ctx

    want = {"workspace": want_workspace, "skills": want_skills,
            "knowledge": want_knowledge, "history": True}
    alloc = {k: (int(free * SHARE[k]) if want[k] else 0) for k in SHARE}

    # 안 쓰는 칸의 몫은 쓰는 칸에 돌려 준다
    unused = sum(int(free * SHARE[k]) for k in SHARE if not want[k])
    live = [k for k in SHARE if want[k]]
    if unused and live:
        each = unused // len(live)
        for k in live:
            alloc[k] += each

    # 바닥값 보장 → 그 때문에 넘치면 우선순위 낮은 것부터 깎는다
    for k in live:
        alloc[k] = max(alloc[k], min(FLOOR[k], free))
    over = sum(alloc.values()) - free
    for k in _SHRINK_ORDER:
        if over <= 0:
            break
        if not want[k]:
            continue
        cut = min(over, max(0, alloc[k] - 1))
        alloc[k] -= cut
        over -= cut

    return Budget(
        n_ctx=n_ctx, reply=reply, safety=safety, system=system_tokens,
        skills=alloc["skills"], knowledge=alloc["knowledge"],
        workspace=alloc["workspace"], history=alloc["history"],
        system_overflow=overflow,
    )


def resolve_n_ctx(cfg: dict, kind: str) -> int:
    """이 요청에 실제로 쓸 컨텍스트 크기.

    ★회사는 API(대부분 128k), 집은 GGUF 다. 둘을 같은 값으로 보면 안 된다.
      GGUF 는 **넘기면 크래시** 하므로, 설정값이 아니라 지금 메모리에 올라가
      있는 모델의 n_ctx 를 봐야 한다 (더 작게 로드됐을 수 있다).
    """
    if kind == "gguf":
        try:
            import importlib
            # ★'import demos_v1.utils as _u' 는 부모 패키지의 속성을 집는다.
            #   sys.modules 를 갈아 끼워도 그쪽이 우선이라 실제 로드된 모델을
            #   못 본다(시험에서 걸렸다). importlib 로 곧장 가져온다.
            _u = importlib.import_module("demos_v1.utils")
            m = getattr(_u, "gguf_model", None)
            if m is not None:
                attr = getattr(m, "n_ctx", None)
                v = attr() if callable(attr) else attr
                if v:
                    return int(v)
        except Exception:
            pass
        return int(cfg.get("n_ctx") or 4096)      # 모르면 좁게 — 크래시보다 낫다
    return int(cfg.get("n_ctx") or cfg.get("context")
               or cfg.get("context_window") or 32768)


def trim_history(messages: list[dict], budget_tokens: int) -> tuple[list[dict], int]:
    """대화 이력을 **토큰 기준으로** 자른다. 되돌려 주는 값: (남은 것, 버린 개수).

    ★예전엔 '최근 12턴' 이었다. 코드가 붙은 12턴과 인사말 12턴은 크기가
      백 배 다른데 똑같이 12턴을 남겼다.
    ★마지막 사용자 메시지는 무슨 일이 있어도 남긴다 — 그게 질문이다.
    """
    if not messages:
        return [], 0
    keep: list[dict] = []
    used = 0
    # 뒤에서부터 담는다 (최근 것이 중요하다)
    for m in reversed(messages):
        t = est_tokens(str(m.get("content") or "")) + 8
        if keep and used + t > budget_tokens:
            break
        keep.append(m)
        used += t
    keep.reverse()
    return keep, len(messages) - len(keep)
