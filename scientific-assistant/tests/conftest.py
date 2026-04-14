"""
pytest 공통 fixture - Flask test client 생성
외부 서비스(Logpresso, GGUF) 없이 테스트 가능하도록 mock 처리
"""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session")
def app():
    """Flask 앱 인스턴스 생성 (세션 전체에서 1회)"""
    # Logpresso 네트워크 호출 mock
    with patch("demos_v1.logpresso._refresh_logpresso_tables", return_value=None), \
         patch("demos_v1.logpresso.query_logpresso", return_value={"result": []}):
        from demos_v1 import create_app
        flask_app = create_app()
        flask_app.config["TESTING"] = True
        yield flask_app


@pytest.fixture
def client(app):
    """Flask test client - 각 테스트마다 새로 생성"""
    with app.test_client() as c:
        yield c


@pytest.fixture
def uploads_dir():
    """테스트용 uploads 디렉토리 경로"""
    from demos_v1.utils import BASE_DIR
    d = os.path.join(BASE_DIR, "uploads")
    os.makedirs(d, exist_ok=True)
    return d
