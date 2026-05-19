"""
harness_bridge.py - app.py와 harness-mvp를 연결하는 브릿지 모듈

기능:
1. 355개 스킬을 ToolRegistry에 자동 등록
2. 세션 저장/로드 (서버 재시작 후 복원 가능)
3. 스킬 라우팅 강화 (ToolRouter + 기존 키워드 병합)
4. 권한 차단 (PermissionContext)
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

# harness-mvp 패키지 경로 추가
_HARNESS_MVP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'harness-mvp')
if _HARNESS_MVP_DIR not in sys.path:
    sys.path.insert(0, _HARNESS_MVP_DIR)

from harness import (
    Tool, ToolRegistry, ToolRouter, HarnessEngine, EngineConfig,
    ToolPermissionContext, StoredSession, HistoryLog, HistoryEvent,
    save_session, load_session, list_sessions,
    AgentAssignment, select_experts,
    FeedbackEntry, FeedbackStore,
)

# ─── 세션 저장 디렉토리 ───
SESSION_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / '.harness_sessions'

# ─── 전역 레지스트리 (서버 시작 시 1회 초기화) ───
_registry: ToolRegistry | None = None
_router: ToolRouter | None = None
_history: HistoryLog = HistoryLog()
_feedback_store: FeedbackStore | None = None


# ============================================================
# 1. 스킬 → ToolRegistry 자동 등록
# ============================================================

def build_skill_registry(
    skills_dir: str | None = None,
    skill_keywords: dict | None = None,
) -> ToolRegistry:
    """scientific-skills 폴더를 스캔하여 ToolRegistry에 등록.

    Args:
        skills_dir: scientific-skills 폴더 경로 (기본: app.py 옆 scientific-skills/)
        skill_keywords: SKILL_KEYWORDS dict (키워드를 description에 포함)

    Returns:
        355+ 스킬이 등록된 ToolRegistry
    """
    registry = ToolRegistry()

    base_dir = skills_dir or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'scientific-skills'
    )

    if not os.path.isdir(base_dir):
        return registry

    keywords = skill_keywords or {}

    for folder_name in sorted(os.listdir(base_dir)):
        skill_dir = os.path.join(base_dir, folder_name)
        skill_md = os.path.join(skill_dir, 'SKILL.md')
        if not os.path.isfile(skill_md):
            continue

        # description 구성: 키워드 + 스킬명
        kw_list = keywords.get(folder_name, [])
        kw_text = ', '.join(kw_list[:10]) if kw_list else folder_name
        description = f'{folder_name}: {kw_text}'

        # handler: SKILL.md 내용 읽기 (lazy)
        def make_handler(path: str):
            def handler(payload: str) -> str:
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return content[:2000] if len(content) > 2000 else content
                except Exception as e:
                    return f'Error reading {path}: {e}'
            return handler

        registry.register(Tool(
            name=folder_name,
            description=description,
            handler=make_handler(skill_md),
        ))

    return registry


# Lazy init 용 — init_harness 호출 시 받은 인자를 저장해뒀다가
# get_registry()/get_router() 가 처음 호출될 때 자동으로 빌드.
_lazy_skills_dir: str | None = None
_lazy_skill_keywords: dict | None = None


def configure_lazy_init(skills_dir: str | None = None, skill_keywords: dict | None = None):
    """시작 시 init_harness 를 호출하지 않을 때, 어떤 dir/keywords 로 lazy 빌드할지 등록만 함."""
    global _lazy_skills_dir, _lazy_skill_keywords
    _lazy_skills_dir = skills_dir
    _lazy_skill_keywords = skill_keywords


def init_harness(skills_dir: str | None = None, skill_keywords: dict | None = None):
    """전역 레지스트리 + 라우터 초기화. 시작 시 호출하면 즉시 빌드,
    아니면 get_registry/get_router 첫 호출 시점에 자동 빌드됨."""
    global _registry, _router, _history, _feedback_store
    _registry = build_skill_registry(skills_dir, skill_keywords)
    _router = ToolRouter(_registry)
    _history = HistoryLog()
    _feedback_store = FeedbackStore(SESSION_DIR / 'feedback')
    _history.add('init', f'Registry loaded: {len(_registry.list_all())} tools')
    return _registry


def _ensure_initialized():
    """이전에는 비어 있으면 자동으로 390 스킬을 모두 등록했지만,
    "사용된 스킬만 로드" 정책에 따라 더 이상 자동 빌드하지 않음.
    필요하면 외부에서 init_harness(...) 를 명시적으로 호출."""
    return


def get_registry() -> ToolRegistry:
    """현재 레지스트리 반환. 초기화 전이면 빈 레지스트리 (자동 빌드 안 함)."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def get_router() -> ToolRouter:
    """현재 라우터 반환. 초기화 전이면 빈 라우터 (자동 빌드 안 함)."""
    global _router, _registry
    if _router is None:
        _router = ToolRouter(get_registry())
    return _router


# ============================================================
# 2. 스킬 라우팅 강화
# ============================================================

def harness_route(query: str, limit: int = 5) -> list[dict]:
    """하네스 라우터로 프롬프트에 매칭되는 스킬 반환.

    Returns:
        [{"name": "biopython", "score": 3, "description": "..."}, ...]
    """
    router = get_router()
    matches = router.route(query, limit=limit)
    return [{'name': m.name, 'score': m.score, 'description': m.description} for m in matches]


def harness_search(query: str, limit: int = 20) -> list[dict]:
    """스킬 이름/설명 텍스트 검색."""
    registry = get_registry()
    results = registry.find(query, limit=limit)
    return [{'name': t.name, 'description': t.description} for t in results]


def harness_filter(deny_names: list[str] | None = None, deny_prefixes: list[str] | None = None) -> list[dict]:
    """권한 차단 필터 적용 후 스킬 목록."""
    registry = get_registry()
    ctx = ToolPermissionContext.from_iterables(deny_names, deny_prefixes)
    tools = registry.filter(ctx)
    return [{'name': t.name, 'description': t.description} for t in tools]


# ============================================================
# 3. 세션 저장/로드
# ============================================================

def save_chat_session(
    session_id: str | None = None,
    messages: list[dict] | None = None,
    uploaded_files: list[dict] | None = None,
    skills_used: list[str] | None = None,
    metadata: dict | None = None,
) -> str:
    """대화 세션을 JSON으로 저장.

    Returns:
        저장된 세션 ID
    """
    sid = session_id or uuid4().hex
    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    msgs = messages or []
    first_msg = ''
    for m in msgs:
        if m.get('role') == 'user' and m.get('content', '').strip():
            first_msg = m['content'].strip()[:50]
            break

    session_data = {
        'session_id': sid,
        'timestamp': time.time(),
        'first_message': first_msg,
        'messages': msgs,
        'uploaded_files': [
            {k: v for k, v in f.items() if k != 'content_full'}
            for f in (uploaded_files or [])
        ],
        'skills_used': skills_used or [],
        'metadata': metadata or {},
    }

    path = SESSION_DIR / f'{sid}.json'
    path.write_text(json.dumps(session_data, ensure_ascii=False, indent=2), encoding='utf-8')

    _history.add('session_save', f'{sid} ({len(session_data["messages"])} messages)')
    return sid


def load_chat_session(session_id: str) -> dict | None:
    """저장된 세션 로드."""
    path = SESSION_DIR / f'{session_id}.json'
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        _history.add('session_load', session_id)
        return data
    except Exception:
        return None


def list_chat_sessions() -> list[dict]:
    """저장된 세션 목록 반환 (최신순)."""
    if not SESSION_DIR.exists():
        return []

    sessions = []
    for p in SESSION_DIR.glob('*.json'):
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
            sessions.append({
                'session_id': data.get('session_id', p.stem),
                'timestamp': data.get('timestamp', 0),
                'message_count': len(data.get('messages', [])),
                'skills_used': data.get('skills_used', []),
                'first_message': data.get('first_message', ''),
            })
        except Exception:
            continue

    sessions.sort(key=lambda s: s['timestamp'], reverse=True)
    return sessions


def delete_chat_session(session_id: str) -> bool:
    """세션 삭제."""
    path = SESSION_DIR / f'{session_id}.json'
    if path.exists():
        path.unlink()
        return True
    return False


# ============================================================
# 4. 히스토리 로깅
# ============================================================

def log_event(title: str, detail: str):
    """이벤트 기록."""
    _history.add(title, detail)


def get_history_markdown() -> str:
    """히스토리를 마크다운으로 반환."""
    return _history.as_markdown()


def get_history_events() -> list[dict]:
    """히스토리 이벤트 목록."""
    return [{'title': e.title, 'detail': e.detail} for e in _history.events]


# ============================================================
# 5. 스킬 조합 보조 (기존 group_skills_for_parallel 강화)
# ============================================================

_META_SKILLS = {
    "using-superpowers", "brainstorming", "writing-plans",
    "test-driven-development", "systematic-debugging",
    "verification-before-completion", "writing-skills",
    "requesting-code-review",
}


def _pick_meta_for_query(query: str) -> str:
    """쿼리 의도로 도메인 스킬에 짝지을 슈퍼파워 메타 스킬 1개 선정.

    더 구체적인 패턴(예: '스킬 만들')을 일반 패턴('만들자')보다 먼저 검사한다.
    """
    q = query.lower()
    if any(kw in q for kw in ["스킬 만들", "skill.md", "스킬 작성", "새 스킬"]):
        return "writing-skills"
    if any(kw in q for kw in ["버그", "에러", "왜 안 되", "디버깅", "이상해", "traceback"]):
        return "systematic-debugging"
    if any(kw in q for kw in ["tdd", "테스트 먼저", "레드그린"]):
        return "test-driven-development"
    if any(kw in q for kw in ["끝났어", "배포", "완료 선언", "검증"]):
        return "verification-before-completion"
    if any(kw in q for kw in ["리뷰", "pr", "코드리뷰", "코드 검토"]):
        return "requesting-code-review"
    if any(kw in q for kw in ["설계", "만들자", "새 기능", "아이디어", "브레인스토밍"]):
        return "brainstorming"
    if any(kw in q for kw in ["계획", "태스크", "분해", "쪼개"]):
        return "writing-plans"
    return "using-superpowers"


def suggest_skill_combinations(query: str, selected_skills: list[str], limit: int = 3) -> list[str]:
    """선택된 스킬과 함께 쓰면 좋을 보조 스킬을 하네스 라우터로 추천.

    1) 하네스 라우터 매칭 결과를 기본으로 사용한다.
    2) selected_skills 에 도메인 스킬이 있으면 의도 기반 메타 스킬 1개를 앞쪽에 prepend.
    """
    router = get_router()
    matches = router.route(query, limit=limit + len(selected_skills))
    existing = set(s.lower() for s in selected_skills)
    suggestions: list[str] = []
    for m in matches:
        if m.name.lower() not in existing:
            suggestions.append(m.name)
        if len(suggestions) >= limit:
            break

    # 도메인↔메타 페어링: 선택에 도메인 스킬이 있으면 메타 1개 앞에 붙임
    has_domain = any(s.lower() not in _META_SKILLS for s in selected_skills)
    if has_domain:
        meta = _pick_meta_for_query(query)
        if meta not in existing and meta not in {s.lower() for s in suggestions}:
            suggestions.insert(0, meta)
            if len(suggestions) > limit:
                suggestions = suggestions[:limit]
    return suggestions


def validate_skill_combination(skill_ids: list[str]) -> dict:
    """스킬 조합의 유효성 검사.

    Returns:
        {
            "valid": list[str],       # 레지스트리에 있는 스킬
            "invalid": list[str],     # 레지스트리에 없는 스킬
            "blocked": list[str],     # 차단된 스킬
            "total": int,
        }
    """
    registry = get_registry()
    valid = []
    invalid = []
    for sid in skill_ids:
        if registry.get(sid):
            valid.append(sid)
        else:
            invalid.append(sid)
    return {
        'valid': valid,
        'invalid': invalid,
        'blocked': [],
        'total': len(skill_ids),
    }


def optimize_skill_groups(skill_ids: list[str], max_groups: int = 4) -> list[list[str]]:
    """하네스 라우터 스코어 기반으로 스킬을 그룹핑.

    높은 스코어끼리 같은 그룹 → 관련 스킬이 같은 에이전트에서 실행.
    기존 SKILL_GROUPS가 없는 스킬도 처리 가능.
    """
    registry = get_registry()
    router = get_router()

    # 각 스킬의 description으로 서로 유사도 판단
    scored_pairs: dict[str, list[str]] = {}
    for sid in skill_ids:
        tool = registry.get(sid)
        if not tool:
            continue
        # 이 스킬의 description 키워드로 다른 스킬 매칭
        matches = router.route(tool.description, limit=len(skill_ids))
        related = [m.name for m in matches if m.name in skill_ids and m.name != sid]
        scored_pairs[sid] = related

    # 관련 스킬끼리 그룹핑 (간단한 클러스터링)
    assigned = set()
    groups: list[list[str]] = []
    for sid in skill_ids:
        if sid in assigned:
            continue
        group = [sid]
        assigned.add(sid)
        for related in scored_pairs.get(sid, []):
            if related not in assigned and len(group) < 5:
                group.append(related)
                assigned.add(related)
        groups.append(group)

    # max_groups 초과 시 작은 그룹 병합
    while len(groups) > max_groups:
        groups.sort(key=len)
        smallest = groups.pop(0)
        groups[0].extend(smallest)

    return groups


# ============================================================
# 6. Flask 라우트 등록 (app.py에서 호출)
# ============================================================

def register_harness_routes(app):
    """Flask 앱에 하네스 API 엔드포인트를 등록."""
    from flask import request as flask_request, jsonify as flask_jsonify

    @app.route('/api/harness/skills')
    def api_harness_skills():
        query = flask_request.args.get('q', '')
        limit = int(flask_request.args.get('limit', '50'))
        registry = get_registry()
        if query:
            tools = registry.find(query, limit=limit)
        else:
            tools = registry.list_all()[:limit]
        return flask_jsonify({
            'total': len(registry.list_all()),
            'showing': len(tools),
            'skills': [{'name': t.name, 'description': t.description} for t in tools],
        })

    @app.route('/api/harness/route', methods=['POST'])
    def api_harness_route():
        data = flask_request.get_json(force=True)
        query = data.get('query', '')
        limit = data.get('limit', 5)
        matches = harness_route(query, limit=limit)
        return flask_jsonify({'query': query, 'matches': matches})

    @app.route('/api/harness/reload', methods=['POST'])
    def api_harness_reload():
        """스킬 레지스트리 새로고침 (서버 재시작 없이)."""
        try:
            # app.py의 SKILL_KEYWORDS를 가져오려면 globals에서 참조
            import app as app_module
            skill_keywords = getattr(app_module, 'SKILL_KEYWORDS', {})
            skills_dir = getattr(app_module, 'SKILLS_DIR', None)
            registry = init_harness(skills_dir, skill_keywords)
            return flask_jsonify({
                'status': 'ok',
                'tools_count': len(registry.list_all()),
            })
        except Exception as e:
            return flask_jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/api/harness/session/save', methods=['POST'])
    def api_harness_session_save():
        data = flask_request.get_json(force=True)
        sid = save_chat_session(
            session_id=data.get('session_id'),
            messages=data.get('messages', []),
            uploaded_files=data.get('uploaded_files', []),
            skills_used=data.get('skills_used', []),
            metadata=data.get('metadata', {}),
        )
        return flask_jsonify({'session_id': sid, 'status': 'saved'})

    @app.route('/api/harness/session/load/<session_id>')
    def api_harness_session_load(session_id):
        session = load_chat_session(session_id)
        if session is None:
            return flask_jsonify({'error': 'Session not found'}), 404
        return flask_jsonify(session)

    @app.route('/api/harness/session/list')
    def api_harness_session_list():
        return flask_jsonify({'sessions': list_chat_sessions()})

    @app.route('/api/harness/session/delete/<session_id>', methods=['DELETE'])
    def api_harness_session_delete(session_id):
        ok = delete_chat_session(session_id)
        return flask_jsonify({'deleted': ok})

    @app.route('/api/harness/history')
    def api_harness_history():
        return flask_jsonify({'events': get_history_events()})

    @app.route('/api/harness/suggest-combo', methods=['POST'])
    def api_harness_suggest_combo():
        """선택된 스킬과 함께 쓰면 좋을 보조 스킬 추천."""
        data = flask_request.get_json(force=True)
        query = data.get('query', '')
        selected = data.get('selected_skills', [])
        limit = data.get('limit', 3)
        combos = suggest_skill_combinations(query, selected, limit=limit)
        return flask_jsonify({'query': query, 'suggestions': combos})

    @app.route('/api/harness/validate-combo', methods=['POST'])
    def api_harness_validate_combo():
        """스킬 조합 유효성 검사."""
        data = flask_request.get_json(force=True)
        skill_ids = data.get('skill_ids', [])
        result = validate_skill_combination(skill_ids)
        return flask_jsonify(result)

    @app.route('/api/harness/optimize-groups', methods=['POST'])
    def api_harness_optimize_groups():
        """스킬 그룹 최적화 (병렬 실행용)."""
        data = flask_request.get_json(force=True)
        skill_ids = data.get('skill_ids', [])
        max_groups = data.get('max_groups', 4)
        groups = optimize_skill_groups(skill_ids, max_groups)
        return flask_jsonify({'groups': groups, 'group_count': len(groups)})

    @app.route('/api/harness/status')
    def api_harness_status():
        registry = get_registry()
        return flask_jsonify({
            'tools_count': len(registry.list_all()),
            'sessions_count': len(list_chat_sessions()),
            'history_events': len(_history.events),
        })

    # ─── Expert Pool: 동적 에이전트 선택 ───
    @app.route('/api/harness/expert-pool', methods=['POST'])
    def api_harness_expert_pool():
        """질문에 맞는 에이전트+스킬 조합을 동적으로 선택."""
        data = flask_request.get_json(force=True)
        query = data.get('query', '')
        min_agents = data.get('min_agents', 2)
        max_agents = data.get('max_agents', 4)
        if not query:
            return flask_jsonify({'error': 'query 필요'}), 400
        router = get_router()
        assignments = select_experts(query, router, min_agents, max_agents)
        return flask_jsonify({
            'query': query,
            'agents': [
                {
                    'agent': a.agent,
                    'role': a.role,
                    'skills': a.skills,
                    'relevance_score': a.relevance_score,
                }
                for a in assignments
            ],
            'total': len(assignments),
        })

    # ─── 피드백 루프 ───
    @app.route('/api/harness/feedback', methods=['POST'])
    def api_harness_feedback_save():
        """실행 결과 피드백 저장."""
        global _feedback_store
        if _feedback_store is None:
            _feedback_store = FeedbackStore(SESSION_DIR / 'feedback')
        data = flask_request.get_json(force=True)
        entry = FeedbackEntry(
            timestamp=time.time(),
            skill_id=data.get('skill_id', ''),
            agent=data.get('agent', ''),
            quality_score=data.get('quality_score', 0),
            approved=data.get('approved', False),
            rejection_reason=data.get('rejection_reason'),
            improvement_notes=data.get('improvement_notes'),
            query_context=data.get('query_context'),
        )
        _feedback_store.add(entry)
        log_event('feedback', f'{entry.skill_id} agent={entry.agent} score={entry.quality_score} approved={entry.approved}')
        return flask_jsonify({'status': 'saved', 'skill_id': entry.skill_id})

    @app.route('/api/harness/feedback/<skill_id>')
    def api_harness_feedback_get(skill_id):
        """특정 스킬의 피드백 조회."""
        global _feedback_store
        if _feedback_store is None:
            _feedback_store = FeedbackStore(SESSION_DIR / 'feedback')
        summary = _feedback_store.get_summary(skill_id)
        entries = _feedback_store.get(skill_id, limit=10)
        return flask_jsonify({
            'skill_id': skill_id,
            'summary': summary,
            'recent': [
                {
                    'timestamp': e.timestamp,
                    'agent': e.agent,
                    'quality_score': e.quality_score,
                    'approved': e.approved,
                    'rejection_reason': e.rejection_reason,
                }
                for e in entries
            ],
        })

    @app.route('/api/harness/feedback/prompt-hint', methods=['POST'])
    def api_harness_feedback_prompt_hint():
        """이전 피드백 기반 프롬프트 힌트 생성."""
        global _feedback_store
        if _feedback_store is None:
            _feedback_store = FeedbackStore(SESSION_DIR / 'feedback')
        data = flask_request.get_json(force=True)
        skill_ids = data.get('skill_ids', [])
        hint = _feedback_store.build_prompt_hint(skill_ids)
        return flask_jsonify({'hint': hint})
