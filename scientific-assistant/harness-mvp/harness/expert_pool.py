"""
expert_pool.py - Expert Pool: 질문에 맞는 에이전트만 동적 선택

질문을 분석하여 필요한 에이전트+스킬 조합만 투입.
전체 에이전트 중 관련도 높은 2~4명만 선택하여 효율성 극대화.
"""
from __future__ import annotations

from dataclasses import dataclass
from .router import ToolRouter
from .registry import ToolRegistry


@dataclass(frozen=True)
class AgentAssignment:
    """에이전트에 배정된 스킬 조합"""
    agent: str
    role: str
    skills: list[str]
    relevance_score: int  # 질문과의 관련도 (높을수록 적합)


# 에이전트별 전문 분야 정의
AGENT_PROFILES = {
    "seo": {
        "name": "SEO",
        "specialties": ["data", "analysis", "statistics", "csv", "excel", "visualization", "chart", "graph",
                        "데이터", "분석", "통계", "시각화", "차트", "그래프", "탐색", "EDA"],
        "default_role": "데이터 분석",
    },
    "yoon": {
        "name": "YOON",
        "specialties": ["ppt", "presentation", "slide", "report", "document", "word", "pdf",
                        "보고서", "문서", "발표", "슬라이드", "프레젠테이션", "PPT"],
        "default_role": "보고서/문서 작성",
    },
    "lee": {
        "name": "LEE",
        "specialties": ["diagram", "flowchart", "architecture", "drawio", "visualization", "infographic",
                        "다이어그램", "플로우차트", "아키텍처", "구조도", "시각화", "인포그래픽"],
        "default_role": "시각화/다이어그램",
    },
    "park": {
        "name": "PARK",
        "specialties": ["code", "programming", "python", "javascript", "development", "debug", "review",
                        "코드", "프로그래밍", "개발", "디버깅", "리뷰", "구현", "함수"],
        "default_role": "코딩/개발",
    },
    "kim": {
        "name": "KIM",
        "specialties": ["semiconductor", "fab", "oht", "process", "yield", "defect", "wafer", "equipment",
                        "반도체", "공정", "수율", "불량", "웨이퍼", "장비", "FAB"],
        "default_role": "반도체/FAB 분석",
    },
    "choi": {
        "name": "CHOI",
        "specialties": ["log", "query", "lpql", "logpresso", "search", "database", "table",
                        "로그", "쿼리", "검색", "데이터베이스", "테이블", "조회"],
        "default_role": "로그/데이터 조회",
    },
}


def select_experts(
    query: str,
    router: ToolRouter,
    min_agents: int = 2,
    max_agents: int = 4,
) -> list[AgentAssignment]:
    """질문에 맞는 에이전트를 동적으로 선택하고 스킬을 배정.

    Args:
        query: 사용자 질문
        router: ToolRouter 인스턴스 (스킬 매칭용)
        min_agents: 최소 투입 에이전트 수
        max_agents: 최대 투입 에이전트 수

    Returns:
        관련도 순으로 정렬된 AgentAssignment 리스트
    """
    query_lower = query.lower()
    query_tokens = set(query_lower.replace("/", " ").replace("-", " ").split())

    # 1) 각 에이전트의 관련도 점수 계산
    agent_scores: list[tuple[str, int]] = []
    for agent_id, profile in AGENT_PROFILES.items():
        score = 0
        for specialty in profile["specialties"]:
            if specialty.lower() in query_lower:
                score += 2  # 전체 매칭
            elif specialty.lower() in query_tokens:
                score += 1  # 토큰 매칭
        agent_scores.append((agent_id, score))

    # 2) 점수 내림차순 정렬
    agent_scores.sort(key=lambda x: -x[1])

    # 3) 최소 min_agents명, 최대 max_agents명 선택
    # 점수 > 0인 에이전트 우선, 부족하면 기본 에이전트 추가
    selected = []
    for agent_id, score in agent_scores:
        if score > 0 and len(selected) < max_agents:
            selected.append((agent_id, score))

    # 최소 인원 미달 시 점수 0이어도 추가
    if len(selected) < min_agents:
        for agent_id, score in agent_scores:
            if agent_id not in [s[0] for s in selected]:
                selected.append((agent_id, score))
                if len(selected) >= min_agents:
                    break

    # 4) 각 에이전트에 스킬 배정 (ToolRouter로 관련 스킬 매칭)
    # 에이전트 전문분야 키워드를 스킬 라우팅에 활용
    assignments = []
    matched_skills = router.route(query, limit=30)
    all_skill_names = [m.name for m in matched_skills]

    skills_per_agent = max(3, len(all_skill_names) // max(len(selected), 1))

    used_skills: set[str] = set()
    for agent_id, score in selected:
        profile = AGENT_PROFILES[agent_id]

        # 에이전트 전문분야와 관련된 스킬 우선 배정
        agent_skills = []
        for skill_match in matched_skills:
            if skill_match.name in used_skills:
                continue
            skill_lower = skill_match.name.lower() + " " + skill_match.description.lower()
            relevance = sum(1 for sp in profile["specialties"] if sp.lower() in skill_lower)
            if relevance > 0:
                agent_skills.append(skill_match.name)
                used_skills.add(skill_match.name)
                if len(agent_skills) >= skills_per_agent:
                    break

        # 전문분야 매칭 스킬이 부족하면 나머지에서 채움
        if len(agent_skills) < 2:
            for skill_match in matched_skills:
                if skill_match.name not in used_skills:
                    agent_skills.append(skill_match.name)
                    used_skills.add(skill_match.name)
                    if len(agent_skills) >= skills_per_agent:
                        break

        assignments.append(AgentAssignment(
            agent=agent_id,
            role=profile["default_role"],
            skills=agent_skills,
            relevance_score=score,
        ))

    return assignments
