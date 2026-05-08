"""
code_assist_v1 - 코딩 어시스턴트 (demos_v1 통합 모듈)

이 패키지는 메인 demos_v1 Flask 앱에 Blueprint로 마운트되어 동작합니다.
- 진입점: code_assist_v1.blueprint.register_code_blueprint(app)
- 마운트 URL prefix: /code/*
- 단독 실행 (app_code.py)은 더 이상 지원하지 않음 (DEPRECATED)

리소스 공유:
- TOKEN.TXT, api_config.json, *.gguf, knowledge/  → 루트와 공유
- skills/, sessions/, workspace/                   → code_assist_v1 자체 폴더 유지
"""
