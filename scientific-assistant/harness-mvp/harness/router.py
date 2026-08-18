from __future__ import annotations

import math
import re

from .models import RoutedMatch
from .registry import ToolRegistry

# 한국어 조사·어미 — '분석해줘'·'파일을' 이 '분석'·'파일' 과 같은 말임을 알아야
# 한다. 형태소 분석기 없이(설치 부담 없이) 뒤에서 잘라 보는 정도로 충분하다.
_JOSA = ("으로", "에서", "에게", "부터", "까지", "이나", "라도", "해줘", "해줄",
         "하라", "하기", "해서", "한다", "합니다", "했다", "인가", "인지",
         "은", "는", "이", "가", "을", "를", "의", "에", "도", "만", "과",
         "와", "로", "랑", "님", "요")
_HANGUL = re.compile(r"[가-힣]")


def _variants(token: str) -> set[str]:
    """토큰 하나 → 비교해 볼 형태들 (원형 + 조사 뗀 것)."""
    out = {token}
    if _HANGUL.search(token):
        for j in _JOSA:
            if token.endswith(j) and len(token) > len(j) + 1:
                out.add(token[: -len(j)])
    return out


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+|[가-힣]+", text))


def _exact_in(field: str, token: str) -> bool:
    """쉼표로 나뉜 키워드 목록에 그 말이 **통째로** 들어 있나."""
    return any(token == part.strip() for part in field.split(','))


class ToolRouter:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry
        self._idf: dict[str, float] = {}
        self._n_docs = 0

    # ── 문서 빈도(IDF) ──
    # ★흔한 말과 희귀한 말을 같은 1점으로 세면 안 된다. '분석' 은 32개 스킬에,
    #   '엑셀' 은 1개에만 있는데 똑같이 1점이라, "엑셀 파일 정리해줘" 가
    #   xlsx 를 놓치고 agent-build-engineer 를 물어 왔다. 희귀할수록 높게 준다.
    def _build_idf(self, docs: list[str]) -> None:
        self._n_docs = max(1, len(docs))
        df: dict[str, int] = {}
        for d in docs:
            for w in set(re.findall(r"[a-z0-9]+|[가-힣]+", d.lower())):
                df[w] = df.get(w, 0) + 1
        self._idf = {w: math.log(1 + self._n_docs / (1 + c)) for w, c in df.items()}

    def _idf_of(self, token: str) -> float:
        """모르는 말은 '아주 희귀하다' 로 본다 (오탐보다 미탐이 나쁘다)."""
        if not self._idf:
            return 1.0
        best = self._idf.get(token)
        if best is not None:
            return best
        # 부분 일치(엑셀 → 엑셀파일)는 조금 깎아서 인정
        for w, v in self._idf.items():
            if len(token) >= 2 and (token in w or w in token):
                best = max(best or 0.0, v * 0.7)
        return best if best is not None else math.log(1 + self._n_docs)

    def route(self, prompt: str, limit: int = 5) -> list[RoutedMatch]:
        raw = [t for t in re.split(r"[\s/\-_,.]+", prompt.lower()) if t]
        tokens: set[str] = set()
        for t in raw:
            tokens |= _variants(t)
        if not tokens:
            return []

        tools = self._registry.list_all()
        if len(self._idf) == 0 or self._n_docs != len(tools):
            self._build_idf([f"{t.name} {t.description}" for t in tools])

        scored: list[RoutedMatch] = []
        for tool in tools:
            score, solid = self._score_parts(tokens, tool.name, tool.description)
            # ★확실한 근거(이름/키워드/설명 본문에 그 말이 실제로 있음)가
            #   하나도 없으면 아예 내보내지 않는다 — '모르겠다' 가 정답인
            #   질의에 억지로 상위 5개를 채워 주면, 에이전트는 엉뚱한 스킬을
            #   읽어 들이고 사용자는 그게 근거 있는 추천인 줄 안다.
            if score > 0 and solid:
                scored.append(RoutedMatch(name=tool.name,
                                          score=round(score, 3),
                                          description=tool.description))
        # 점수 같으면 짧은 이름 우선 — 'xlsx' 가 'agent-…' 보다 구체적이다
        scored.sort(key=lambda m: (-m.score, len(m.name), m.name))
        return scored[:limit]

    def _score(self, tokens: set[str], name: str, description: str = '') -> float:
        # ★self 없이 클래스에서 바로 부르는 호출도 지원한다 (기존 공개 사용법).
        if isinstance(self, (set, frozenset)):
            self, tokens, name, description = (
                ToolRouter.__new__(ToolRouter), self, tokens, name)
            self._idf, self._n_docs = {}, 0
        return self._score_parts(tokens, name, description)[0]

    def _score_parts(self, tokens: set[str], name: str,
                     description: str = '') -> tuple[float, bool]:
        """이름 > 등록 키워드 > 본문 설명 순으로 무겁게 센다.

        되돌려 주는 값은 (점수, 확실한_근거가_있나).

        ★키워드(스킬마다 사람이 붙여 둔 '이 말이 나오면 이 스킬')는 본문
          설명보다 훨씬 강한 신호다. 예전엔 셋을 같은 무게로 봐서, 설명이
          긴 스킬이 우연히 여러 단어에 걸리며 정답을 밀어냈다
          ('엑셀 파일 정리해줘' → file-organizer 가 xlsx 를 이겼다).
        """
        nm = name.lower()
        ds = description.lower()
        # description 은 "이름: 키워드 — 본문설명" 형태로 만들어 두지만,
        # 그냥 한 줄짜리 설명인 도구도 있다. 구분자가 없으면 전부 본문으로
        # 본다 — 예전엔 이 경우 body 가 빈 문자열이 되어, 멀쩡한 설명 일치가
        # 전부 흐릿한 유사 일치로 떨어졌다.
        if ' — ' in ds:
            head, _, body = ds.partition(' — ')
            kw = head.partition(':')[2]       # 키워드 구간만
        else:
            kw, body = '', ds

        total = 0.0
        solid = False
        for token in tokens:
            if len(token) < 2 and not _HANGUL.search(token):
                continue                      # 'a','를' 같은 한 글자는 버린다
            w = self._idf_of(token)
            if token == nm:
                total += w * 6.0              # 이름과 정확히 같다
                solid = True
            elif _exact_in(kw, token):
                total += w * 4.0              # 등록 키워드와 정확히 같다
                solid = True
            elif token in nm:
                total += w * 2.0              # 이름에 들어 있다
                solid = True
            elif token in kw:
                total += w * 1.5              # 키워드에 부분적으로
                solid = True
            elif token in body:
                total += w                    # 본문 설명에만
                solid = True
            elif len(token) >= 4:
                # 어미만 다른 경우(uppercase/upper). 짧은 말끼리 걸치면
                # 아무 뜻 없는 우연이라, 양쪽 다 4글자 이상일 때만 센다.
                if any(len(wd) >= 4 and (token in wd or wd in token)
                       for wd in _words(ds)):
                    total += w * 0.6
        return total, solid
