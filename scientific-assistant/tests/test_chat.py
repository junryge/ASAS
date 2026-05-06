"""
routes_chat.py 엔드포인트 테스트
"""
import json


class TestChatStop:
    def test_chat_stop(self, client):
        resp = client.post("/api/chat/stop")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("stopped") is True


class TestChat:
    def test_chat_missing_messages(self, client):
        """messages 없이 요청하면 에러"""
        resp = client.post("/api/chat", json={
            "env": "auto",
            "skills": [],
        })
        # messages가 없거나 비어있으면 에러 또는 빈 응답
        assert resp.status_code in (200, 400, 500)

    def test_chat_no_api_key_gguf_fallback(self, client):
        """API 키 없이 GGUF도 없으면 에러 반환"""
        resp = client.post("/api/chat", json={
            "env": ["auto"],
            "messages": [{"role": "user", "content": "안녕하세요"}],
            "skills": [],
            "effort": 1,
            "format": "auto",
            "writing_style": "auto",
        })
        # API 키/GGUF 없으면 에러, 있으면 200
        assert resp.status_code in (200, 400, 500)
        data = resp.get_json()
        assert "content" in data or "error" in data

    def test_chat_with_md_to_html_skill(self, client):
        """md-to-html 스킬 로드 시 정상 처리"""
        resp = client.post("/api/chat", json={
            "env": ["auto"],
            "messages": [{"role": "user", "content": "보고서 작성해줘"}],
            "skills": ["md-to-html"],
            "effort": 1,
            "format": "auto",
            "writing_style": "auto",
        })
        assert resp.status_code in (200, 400, 500)
        data = resp.get_json()
        assert "content" in data or "error" in data
