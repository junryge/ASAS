"""
hermes/builtin.py — 헤르메스 빌트인 스킬 팩 (Hermes 영감, 폐쇄망용 프롬프트 스킬)

개인 학습 스킬(skills.py)과 별개로, 공통 "작업 방식" 프롬프트 스킬.
질의 키워드에 맞으면 build_system_prompt 가 주입한다. (순수 프롬프트, 외부망/실행 불필요)
"""
from __future__ import annotations

BUILTIN_SKILLS = {
    "task-planning": {
        "desc": "복잡한 작업은 먼저 단계 계획을 세우고 실행",
        "keywords": ["만들", "구현", "설계", "프로그램", "코드", "연구", "분석", "계획",
                     "파이프라인", "단계", "아키텍처", "build", "design", "research"],
        "body": (
            "복잡·다단계 요청이면 바로 답하지 말고:\n"
            "1) 목표를 한 줄로 정의\n"
            "2) 3~6단계 실행 계획 제시(각 단계 산출물 명시)\n"
            "3) 계획대로 실행/작성\n"
            "4) 마지막에 빠진 단계가 없는지 자가점검"
        ),
    },
    "systematic-debugging": {
        "desc": "오류는 재현→가설→최소수정→검증 순서로",
        "keywords": ["오류", "에러", "버그", "디버", "안돼", "안 돼", "실패", "exception",
                     "traceback", "고장", "error", "bug", "fix"],
        "body": (
            "오류 해결 순서:\n"
            "1) 증상/재현 조건 명확화\n"
            "2) 원인 가설 2~3개\n"
            "3) 가능성 높은 것부터 최소 변경으로 검증\n"
            "4) 환경 의존(패키지/권한) vs 코드 문제 구분\n"
            "5) 수정 후 재현 절차로 검증"
        ),
    },
    "structured-data-analysis": {
        "desc": "데이터는 컬럼/단위 확인 후 가설→통계→시각화",
        "keywords": ["데이터", "분석", "통계", "반송", "fab", "로그", "수율", "oht", "ohs",
                     "csv", "엑셀", "컬럼", "추세", "이상", "data", "analysis"],
        "body": (
            "데이터 분석 절차:\n"
            "1) 컬럼명·단위·기간을 먼저 확인(추측 금지)\n"
            "2) 분석 질문을 가설로 정의\n"
            "3) 기술통계 → 이상치 → 상관/추세 순\n"
            "4) 실제 값/컬럼만 인용(없는 값 만들지 말 것)\n"
            "5) 결론 + 표/차트 시각화 권고"
        ),
    },
    "answer-verification": {
        "desc": "최종 답 전 자가검증(근거·누락 확인)",
        "keywords": ["보고서", "결론", "정확", "검증", "요약", "report", "verify"],
        "body": (
            "최종 답 직전 자가검증:\n"
            "1) 인용한 수치·컬럼·함수가 실제 컨텍스트에 있는가?\n"
            "2) 단정 대신 근거를 붙였는가?\n"
            "3) 요청을 빠짐없이 다뤘는가?\n"
            "불확실하면 추측임을 명시한다."
        ),
    },
}


def recall_builtin(query: str, top_k: int = 2) -> list[dict]:
    q = (query or "").lower()
    if not q:
        return []
    scored = []
    for name, s in BUILTIN_SKILLS.items():
        hits = sum(1 for kw in s["keywords"] if kw in q)
        if hits:
            scored.append((hits, name, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"name": n, "desc": s["desc"], "body": s["body"]} for _h, n, s in scored[:top_k]]


def index_text() -> str:
    return "\n".join(f"- {n}: {s['desc']}" for n, s in BUILTIN_SKILLS.items())
