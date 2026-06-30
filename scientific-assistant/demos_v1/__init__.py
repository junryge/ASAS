"""
demos_v1/__init__.py - Package initialization, Flask app creation, route registration
"""
import os
import sys
import warnings
from flask import Flask

# Create Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB 제한


_routes_registered = False

def create_app():
    """Create and configure the Flask app with all routes registered."""
    global _routes_registered
    if _routes_registered:
        return app

    from demos_v1.routes_api import register_api_routes
    from demos_v1.routes_chat import register_chat_routes
    from demos_v1.logpresso import register_logpresso_routes
    from demos_v1.knowledge import register_knowledge_routes
    from demos_v1.routes_ppt import register_ppt_routes
    from demos_v1.routes_agents import register_agent_routes

    register_api_routes(app)
    register_chat_routes(app)
    register_logpresso_routes(app)
    register_knowledge_routes(app)
    register_ppt_routes(app)
    register_agent_routes(app)

    # 루프 엔지니어링(loop_engine) 라우트 — 실패해도 본체 정상 동작
    try:
        from demos_v1.routes_loop import register_loop_routes
        register_loop_routes(app)
        print("  🔁 루프엔진 라우트 등록 완료 (/api/loop/run)")
    except Exception as _le:
        print(f"  ⚠️  루프엔진 라우트 스킵: {_le}")

    # 헤르메스(재해석) 엔진 라우트 — 실패해도 데모스 본체는 정상 동작
    try:
        from demos_v1.hermes.routes import register_hermes_routes
        register_hermes_routes(app)
        print("  🔮 헤르메스 라우트 등록 완료 (/api/hermes/*)")
    except Exception as _he:
        print(f"  ⚠️  헤르메스 라우트 등록 실패(무시): {_he}")

    # code_assist_v1 통합 (Blueprint, url_prefix="/code", demos_v1 리소스 공유)
    try:
        from code_assist_v1.blueprint import register_code_blueprint
        register_code_blueprint(app)
        print("  🖥️  code_assist_v1 Blueprint 등록 완료 (/code/*)")
    except Exception as _e:
        print(f"  ⚠️  code_assist_v1 Blueprint 등록 실패: {_e}")

    # 하네스(harness) 스킬 라우터 — init_harness() 를 호출하지 않으면 레지스트리가
    # 빈 채로 남아 라우터/Expert Pool/조합추천이 전부 빈 결과(자동 비활성)가 된다.
    # 여기서 명시적으로 초기화 + /api/harness/* 라우트 등록. 실패해도 본체는 정상 동작.
    try:
        from harness_bridge import init_harness, register_harness_routes
        from demos_v1.utils import SKILLS_DIR as _HSD
        try:
            from demos_v1.skills import SKILL_KEYWORDS as _HKW
        except Exception:
            _HKW = None
        _hreg = init_harness(skills_dir=_HSD, skill_keywords=_HKW)
        register_harness_routes(app)
        print(f"  🧰 하네스 등록 완료 ({len(_hreg.list_all())}개 스킬, 라우터/Expert Pool 활성, /api/harness/*)")
    except Exception as _hb:
        print(f"  ⚠️  하네스 등록 실패(무시): {_hb}")

    _routes_registered = True
    return app
