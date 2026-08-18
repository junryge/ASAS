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


def _compound_in(field: str, token: str) -> bool:
    """한글 복합어 **안쪽까지** 본다 — '논문' 이 '논문검색' 에 들어 있나.

    ★한국어는 낱말을 붙여 쓴다. 스킬엔 '논문검색' 이라 적혀 있는데 사람은
      '논문 검색' 이라 친다. 이걸 '부분 일치' 로 약하게 세면, 흔해 빠진
      '검색' 을 통째로 가진 범용 스킬한테 진다. 복합어를 이루는 조각은
      약한 근거가 아니라 제대로 된 근거다.
    """
    if not _HANGUL.search(token) or len(token) < 2:
        return False
    return any(token in part.strip() for part in field.split(',')
               if _HANGUL.search(part))


class ToolRouter:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry
        self._idf: dict[str, float] = {}
        self._n_docs = 0

    # ── 문서 빈도(IDF) ──
    # ★흔한 말과 희귀한 말을 같은 1점으로 세면 안 된다. '분석' 은 32개 스킬에,
    #   '엑셀' 은 1개에만 있는데 똑같이 1점이라, "엑셀 파일 정리해줘" 가
    #   xlsx 를 놓치고 agent-build-engineer 를 물어 왔다. 희귀할수록 높게 준다.
    #
    # ★★한국어는 띄어쓰기로 낱말이 안 갈라진다. 스킬 설명엔 '논문검색' 이라고
    #   붙여 써 있는데 사람은 '논문 검색' 이라고 친다. 낱말 단위로 세면
    #   '논문' 의 문서빈도가 0 이 되어 IDF 가 통째로 헛돈다. 실제로
    #   '논문 검색' 이 pubmed 를 놓치고, 흔한 '검색' 만 가진 범용
    #   agent-search-specialist 를 물어 왔다.
    #   그래서 '점수를 매길 때 쓰는 일치 기준' 과 똑같은 기준으로 센다 —
    #   한글은 부분 포함, 영문은 낱말 단위. 질의어마다 한 번만 세면 되니
    #   (389개 문서 × 질의어 몇 개) 값도 싸다.
    def _build_idf(self, docs: list[str]) -> None:
        self._n_docs = max(1, len(docs))
        self._docs = [d.lower() for d in docs]
        self._doc_words = [set(re.findall(r"[a-z0-9]+|[가-힣]+", d)) for d in self._docs]
        self._idf = {}

    def _idf_of(self, token: str) -> float:
        """모르는 말은 '아주 희귀하다' 로 본다 (오탐보다 미탐이 나쁘다)."""
        if not getattr(self, "_docs", None):
            return 1.0
        hit = self._idf.get(token)
        if hit is not None:
            return hit
        if _HANGUL.search(token):
            df = sum(1 for d in self._docs if token in d)      # 복합어 안쪽까지
        else:
            df = sum(1 for ws in self._doc_words if token in ws)
            if df == 0 and len(token) >= 4:
                df = sum(1 for d in self._docs if token in d)
        val = math.log(1 + self._n_docs / (1 + df))
        self._idf[token] = val
        return val

    def route(self, prompt: str, limit: int = 5) -> list[RoutedMatch]:
        raw = [t for t in re.split(r"[\s/\-_,.]+", prompt.lower()) if t]
        # ★한 낱말은 한 번만 센다. '정리해줘' 를 조사 떼고 '정리' 로도 보는데,
        #   둘 다 점수를 주면 같은 말을 두 번 센 셈이라 어미가 붙은 질의일수록
        #   엉뚱한 스킬이 부풀어 오른다. 변형끼리는 '가장 잘 맞는 하나' 만.
        groups = [_variants(t) for t in raw]
        if not any(groups):
            return []

        tools = self._registry.list_all()
        if not getattr(self, "_docs", None) or self._n_docs != len(tools):
            self._build_idf([f"{t.name} {t.description}" for t in tools])

        scored: list[RoutedMatch] = []
        for tool in tools:
            score, solid = self._score_parts(groups, tool.name, tool.description)
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

    def _score_parts(self, tokens, name: str,
                     description: str = '') -> tuple[float, bool]:
        """이름 > 등록 키워드 > 본문 설명 순으로 무겁게 센다.

        tokens 는 낱말 묶음들의 목록이다 — 한 묶음은 같은 낱말의 변형들
        ('정리해줘', '정리')이고, 묶음마다 가장 높은 점수 하나만 센다.
        낱낱의 집합을 주면 각각을 홀로 선 묶음으로 본다.

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

        groups = [{t} for t in tokens] if isinstance(tokens, (set, frozenset)) \
            else list(tokens)
        dwords = _words(ds)

        total = 0.0
        solid = False
        for group in groups:
            best, best_solid = 0.0, False
            for token in group:
                if len(token) < 2 and not _HANGUL.search(token):
                    continue                  # 'a','를' 같은 한 글자는 버린다
                w = self._idf_of(token)
                hit, is_solid = 0.0, True
                if token == nm:
                    hit = w * 6.0             # 이름과 정확히 같다
                elif _exact_in(kw, token):
                    hit = w * 4.0             # 등록 키워드와 정확히 같다
                elif _compound_in(kw, token):
                    hit = w * 3.5             # 키워드 복합어의 한 조각 ('논문'⊂'논문검색')
                elif token in nm:
                    hit = w * 2.0             # 이름에 들어 있다
                elif token in kw:
                    hit = w * 1.5             # 키워드에 부분적으로
                elif token in body:
                    hit = w                   # 본문 설명에만
                elif len(token) >= 4 and any(
                        len(wd) >= 4 and (token in wd or wd in token)
                        for wd in dwords):
                    # 어미만 다른 경우(uppercase/upper). 짧은 말끼리 걸치면
                    # 아무 뜻 없는 우연이라, 양쪽 다 4글자 이상일 때만 센다.
                    hit, is_solid = w * 0.6, False
                else:
                    continue
                if hit > best:
                    best, best_solid = hit, is_solid
            total += best
            solid = solid or best_solid
        return total, solid
