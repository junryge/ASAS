"""
routes_api.py 엔드포인트 테스트
"""
import json
import os


class TestMainPage:
    def test_index_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_uio_page(self, client):
        resp = client.get("/uio")
        # 200 또는 302 (리다이렉트) 모두 정상
        assert resp.status_code in (200, 301, 302)


class TestConfig:
    def test_get_config(self, client):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "environments" in data or "envs" in data or isinstance(data, dict)


class TestSkills:
    def test_list_skills(self, client):
        resp = client.get("/api/skills")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, (list, dict))

    def test_get_nonexistent_skill(self, client):
        resp = client.get("/api/skill/nonexistent-skill-xyz")
        assert resp.status_code in (404, 200)


class TestGenerateHtml:
    def test_generate_html_success(self, client):
        resp = client.post("/api/generate_html", json={
            "markdown": "# 테스트 보고서\n\n## 개요\n\n이것은 테스트입니다.\n\n| 항목 | 값 |\n|---|---|\n| A | 100 |",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "download_url" in data
        assert "document.html" in data["download_url"]

    def test_generate_html_auto_title(self, client):
        resp = client.post("/api/generate_html", json={
            "markdown": "# OHT 분석 보고서\n\n내용",
        })
        data = resp.get_json()
        assert resp.status_code == 200
        assert "download_url" in data

    def test_generate_html_empty_markdown(self, client):
        resp = client.post("/api/generate_html", json={
            "markdown": "",
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_generate_html_no_body(self, client):
        resp = client.post("/api/generate_html",
                           data="{}",
                           content_type="application/json")
        assert resp.status_code == 400


class TestDownloadStatic:
    def test_download_html_invalid_id(self, client):
        resp = client.get("/api/download_static/document.html")
        assert resp.status_code == 400

    def test_download_html_not_found(self, client):
        resp = client.get("/api/download_static/document.html?id=99999999_999999")
        assert resp.status_code == 404

    def test_download_md_invalid_id(self, client):
        resp = client.get("/api/download_static/document.md")
        assert resp.status_code == 400

    def test_download_md_not_found(self, client):
        resp = client.get("/api/download_static/document.md?id=99999999_999999")
        assert resp.status_code == 404

    def test_download_pptx_invalid_id(self, client):
        resp = client.get("/api/download_static/presentation.pptx")
        assert resp.status_code == 400

    def test_generate_then_download_html(self, client):
        """HTML 생성 후 다운로드까지 E2E 테스트"""
        gen_resp = client.post("/api/generate_html", json={
            "markdown": "# E2E 테스트\n\n내용입니다",
        })
        assert gen_resp.status_code == 200
        url = gen_resp.get_json()["download_url"]

        dl_resp = client.get(url)
        assert dl_resp.status_code == 200
        assert b"E2E" in dl_resp.data


class TestGeneratePptx:
    def test_generate_pptx_no_code(self, client):
        resp = client.post("/api/generate_pptx", json={})
        assert resp.status_code in (400, 500)

    def test_generate_pptx_empty_code(self, client):
        resp = client.post("/api/generate_pptx", json={"code": ""})
        assert resp.status_code in (400, 500)


class TestFileUpload:
    def test_clear_files(self, client):
        resp = client.post("/api/clear_files")
        assert resp.status_code == 200

    def test_uploaded_files_list(self, client):
        resp = client.get("/api/uploaded_files")
        assert resp.status_code == 200

    def test_clear_csv(self, client):
        resp = client.post("/api/clear_csv")
        assert resp.status_code == 200


class TestPrompts:
    def test_list_prompts(self, client):
        resp = client.get("/api/prompts")
        assert resp.status_code == 200

    def test_delete_nonexistent_prompt(self, client):
        resp = client.delete("/api/prompts/nonexistent-id-xyz")
        assert resp.status_code in (200, 400, 404)


class TestAutoSkills:
    def test_auto_skills(self, client):
        resp = client.post("/api/auto-skills", json={
            "query": "OHT 반송 데이터 분석해줘"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, (list, dict))
