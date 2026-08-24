# -*- coding: utf-8 -*-
"""룰 코드 → 관제가 쓰는 한글 이름.

왜 한 모듈로 뺐나
  'R-A' 는 스코어 설계 문서의 내부 표기다. 관제 담당자는 그 코드를 모른다.
  그런데 코드가 **어디 한 군데라도** 프롬프트에 실리면 모델은 그걸 베낀다.
  실제로 근거에서 코드를 없앴는데도 "R-D 룰 활성화" 라고 답했다 — 범인은
  스킬 문서(SKILL.md)의 배점표였다.

  그래서 막는 자리를 셋으로 늘렸다.
    ① 근거(sentinel)      — 우리가 만드는 재료
    ② 스킬·자료(llm)      — 사람이 넣어 둔 재료 (문서에는 코드가 있다)
    ③ 대답(server)        — 그래도 새면 나가기 직전에 바꾼다
  ①②만 하고 ③을 빼면, 모델이 예전 대화를 참고해 코드를 다시 꺼낸다.
"""
import re

# ★이름을 지어내지 않는다. 현장 스킬(m16_hub_skills)에 이미 공식 한글명이
#   있다 — m16_hub_카파시 §4 '9개 룰' 표의 한글명, 그리고 그 출력 표기는
#   m16_hub_결과해석 §용어 표준(필수) 을 따른다.
#     · 카파시 표     : R-C = '리프터 막힘', R-D = '저장공간 포화'
#     · 용어 표준(필수): '리프터 막힘' → '리프터 정체',
#                        '저장공간 포화' → 'Storage FULL', '큐' → 'Queue'
#   사람이 읽는 문장에 나가는 것이므로 용어 표준 쪽을 최종형으로 쓴다.
KO = {
    "RA": "반송지연",
    "RA_sus": "반송지연 지속",
    "RB": "Queue 누적",
    "RB_fast": "Queue 급증",
    "RC": "리프터 정체",
    "RD": "Storage FULL",
    "SLA": "4분초과",
    "SORT": "분류기 대기",
    "MAXCAPA": "운영자 용량변경",
    "FLOW": "흐름 비율 정체",
    "FUSE": "융합 집계",
    "SCORE": "판정 결과",
}

# 용어 표준 — m16_hub_결과해석 §용어 표준 중 **금지어**만 자동으로 바로잡는다.
# ★전부 자동 치환하지 않는다. 표에는 '급증 → 상승' 도 있는데 공식 룰명이
#   'Queue 급증' 이라 서로 부딪힌다. 기계로 고칠 것은 '쓰면 안 된다' 고
#   못박은 것들만 두고, 나머지 말투는 스킬 본문을 프롬프트에 실어 맡긴다.
_STD = [
    (r"역증가|역류|역방향", "정체"),          # ★스킬에 '금지' 로 명시된 단어
    (r"막힌 리프터", "정체 리프터"),
    (r"리프터가 막혀|리프터 막힘", "리프터 정체"),
    (r"저장공간\s*포화|저장\s*포화", "Storage FULL"),
    (r"감독관\s*의견", "에이전트 의견"),
    (r"감독관\s*제언", "에이전트 제언"),
    (r"반송카", "OHT"),
    (r"적체", "정체"),
    (r"M16\s*허브룸", "M16 HUBROOM"),
    (r"허브룸", "HUBROOM"),
]
_STD_RE = [(re.compile(p), r) for p, r in _STD]


def house_style(s):
    """현장 용어 표준으로 바로잡는다 (금지어만)."""
    out = str(s or "")
    for rx, rep in _STD_RE:
        out = rx.sub(rep, out)
    return out


def clean(s):
    """밖으로 나가는 문장에 쓰는 것 — 룰 코드 제거 + 용어 표준."""
    return house_style(no_code(s))


# R-A · R‑A(비분리 하이픈) · RA · R-A′ · R-A' · RA_sus · R-B fast …
# ★뒤를 \b 로 막으면 안 된다 — "R-A′" 의 ′ 는 단어문자가 아니라 \b 가 깨져
#   프라임만 남는다. (?![\w]) 로 '뒤에 글자가 이어지지 않을 것' 만 본다.
#   그래야 RATIO·RACK 같은 진짜 낱말은 안 건드린다.
CODE_RE = re.compile(
    r"\bR[-‑]?(?:A_sus|B_fast|A[′']|[ABCD])(?![\w])"
    r"|\b(?:RA_sus|RB_fast|RA|RB|RC|RD)(?![\w])")


def no_code(s):
    """문장·문서에서 룰 코드를 한글 이름으로 바꾼다."""
    def rep(m):
        raw = (m.group(0) or "").replace("-", "").replace("‑", "") \
            .replace("′", "_sus").replace("'", "_sus").upper()
        key = raw.replace("_SUS", "_sus").replace("_FAST", "_fast")
        return KO.get(key, "해당 룰")
    return CODE_RE.sub(rep, str(s or ""))


def has_code(s):
    """코드가 남아 있나 — 스킬 재시딩·테스트 판정용."""
    return bool(CODE_RE.search(str(s or "")))
