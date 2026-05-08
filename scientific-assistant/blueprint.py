"""
code_assist_v1/blueprint.py - demos_v1 통합용 Blueprint

메인 demos_v1 Flask 앱에 url_prefix="/code"로 마운트되는 Blueprint.
단독 실행(app_code.py / __init__.py:create_app)은 별개로 그대로 유지.

원리:
- routes_*.py의 register_xxx_routes(app)는 @app.route 패턴이라
  Flask app과 Blueprint가 동일 시그니처를 가지므로 Blueprint를 그대로 넘기면
  routes 본문 변경 없이 url_prefix만 자동 부착됨.
- root 라우트("/")에서 index.html을 읽고 `<base href="/code/">`를 주입해서
  정적 자원 + fetch 상대경로가 /code/ 기준으로 해석되도록 함.
- 메인 app.py가 이미 init_harness/register_harness_routes를 호출하므로
  여기서는 setup_harness를 호출하지 않음 (충돌 방지).
"""
from __future__ import annotations
import os
from flask import Blueprint, Response

from code_assist_v1.config import STATIC_DIR


code_bp = Blueprint(
    "code_assist",
    __name__,
    url_prefix="/code",
    static_folder=STATIC_DIR,
    static_url_path="/static",
)

_routes_registered = False


def register_code_blueprint(app) -> bool:
    """메인 demos_v1 app에 code_assist Blueprint 등록.

    Returns: 등록 성공 여부.
    """
    global _routes_registered
    if _routes_registered:
        return True

    # routes_*.py의 register_xxx_routes(target)는 @target.route(...)를 사용
    # → Blueprint도 동일 시그니처. Blueprint를 그대로 넘기면 본문 변경 없음.
    from code_assist_v1.routes_models import register_model_routes
    from code_assist_v1.routes_skills import register_skill_routes
    from code_assist_v1.routes_knowledge import register_knowledge_routes
    from code_assist_v1.routes_workspace import register_workspace_routes
    from code_assist_v1.routes_chat_stream import register_chat_stream_routes
    from code_assist_v1.routes_sessions import register_session_routes

    register_model_routes(code_bp)
    register_skill_routes(code_bp)
    register_knowledge_routes(code_bp)
    register_workspace_routes(code_bp)
    register_chat_stream_routes(code_bp)
    register_session_routes(code_bp)

    # 모델 정보(API + GGUF)는 demos_v1.models에서 직접 가져온다 (routes_models.py가 처리).
    # → code_assist_v1 자체 MODEL_REGISTRY/ENV_CONFIG 빌드 안 함, demos_v1 것 그대로 공유.

    # 하네스: 메인 app.py가 이미 init_harness + register_harness_routes 호출함.
    # 여기서 setup_harness를 호출하면 ToolRegistry 재초기화/라우트 중복으로 충돌.
    # → 호출하지 않음.

    @code_bp.route("/")
    def code_index():
        """code_assist UI 메인 — index.html에 <base href> + 로그인 게이트 주입.

        - 모든 상대경로 (static/*, api/*) 가 /code/ 기준으로 해석되도록 base href 주입
        - sessionStorage('demos_user') 검증 — 미로그인 시 demos 메인으로 즉시 리다이렉트
          (앱 다른 화면이 그려지기 전에 차단)
        """
        index_path = os.path.join(STATIC_DIR, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
        # head 직후에 base href + 로그인 게이트 inline script 주입
        gate_html = (
            '<base href="/code/">\n'
            '<script>'
            '(function(){'
            'try{'
            'var u=JSON.parse(sessionStorage.getItem("demos_user")||"null");'
            'if(!u||!u.id){window.location.replace("/");}'
            '}catch(e){window.location.replace("/");}'
            '})();'
            '</script>'
        )
        html = html.replace("<head>", "<head>\n" + gate_html, 1)
        return Response(html, mimetype="text/html; charset=utf-8")

    @code_bp.route("/healthz")
    def code_healthz():
        return {"status": "ok", "service": "code_assist_v1", "mounted": "/code"}

    app.register_blueprint(code_bp)
    _routes_registered = True
    return True
