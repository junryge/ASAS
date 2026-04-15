"""
헬퍼 함수 단위 테스트
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestMaybeGenerateMdHtml:
    def test_skip_when_no_skill(self):
        """md-to-html 스킬이 없으면 건너뜀"""
        from demos_v1.routes_chat import _maybe_generate_md_html
        resp = {"content": "테스트"}
        result = _maybe_generate_md_html("테스트", ["pptx"], resp)
        assert "md_download_url" not in result
        assert "html_download_url" not in result

    def test_generates_files_when_skill_loaded(self):
        """md-to-html 스킬이 있으면 MD/HTML 파일 생성"""
        from demos_v1.routes_chat import _maybe_generate_md_html
        from demos_v1.utils import BASE_DIR

        answer = "# 테스트 보고서\n\n## 개요\n\n내용입니다.\n\n| 항목 | 값 |\n|---|---|\n| A | 100 |"
        resp = {"content": answer}
        result = _maybe_generate_md_html(answer, ["md-to-html"], resp)

        assert "md_download_url" in result
        assert "html_download_url" in result
        assert "doc_download_id" in result

        # 실제 파일 생성 확인
        timestamp = result["doc_download_id"]
        uploads = os.path.join(BASE_DIR, "uploads")
        md_path = os.path.join(uploads, f"document_{timestamp}.md")
        html_path = os.path.join(uploads, f"document_{timestamp}.html")

        assert os.path.exists(md_path)
        assert os.path.exists(html_path)

        # MD 파일 내용 확인
        with open(md_path, encoding="utf-8") as f:
            assert "테스트 보고서" in f.read()

        # HTML 파일 제목 확인
        with open(html_path, encoding="utf-8") as f:
            html_content = f.read()
            assert "<title>테스트 보고서</title>" in html_content
            assert "<table>" in html_content

        # 정리
        os.remove(md_path)
        os.remove(html_path)

    def test_title_extraction(self):
        """첫 번째 # 제목 자동 추출"""
        from demos_v1.routes_chat import _maybe_generate_md_html
        from demos_v1.utils import BASE_DIR

        answer = "## 서론\n\n이건 h2\n\n# OHT 분석\n\n본문"
        resp = {"content": answer}
        result = _maybe_generate_md_html(answer, ["md-to-html"], resp)

        timestamp = result["doc_download_id"]
        html_path = os.path.join(BASE_DIR, "uploads", f"document_{timestamp}.html")

        with open(html_path, encoding="utf-8") as f:
            assert "<title>OHT 분석</title>" in f.read()

        # 정리
        os.remove(os.path.join(BASE_DIR, "uploads", f"document_{timestamp}.md"))
        os.remove(html_path)

    def test_no_h1_uses_default_title(self):
        """# 제목이 없으면 '문서' 사용"""
        from demos_v1.routes_chat import _maybe_generate_md_html
        from demos_v1.utils import BASE_DIR

        answer = "## 소제목만 있음\n\n내용"
        resp = {"content": answer}
        result = _maybe_generate_md_html(answer, ["md-to-html"], resp)

        timestamp = result["doc_download_id"]
        html_path = os.path.join(BASE_DIR, "uploads", f"document_{timestamp}.html")

        with open(html_path, encoding="utf-8") as f:
            assert "<title>문서</title>" in f.read()

        # 정리
        os.remove(os.path.join(BASE_DIR, "uploads", f"document_{timestamp}.md"))
        os.remove(html_path)


class TestSkillScan:
    def test_skills_directory_exists(self):
        """scientific-skills 디렉토리 존재 확인"""
        from demos_v1.utils import SKILLS_DIR
        assert os.path.isdir(SKILLS_DIR)

    def test_md_to_html_skill_exists(self):
        """md-to-html 스킬 파일 존재 확인"""
        from demos_v1.utils import SKILLS_DIR
        skill_path = os.path.join(SKILLS_DIR, "md-to-html", "SKILL.md")
        assert os.path.exists(skill_path)

    def test_domain_skills_has_md_to_html(self):
        """DOMAIN_SKILLS에 md-to-html 등록 확인"""
        from demos_v1.skills import DOMAIN_SKILLS
        utilities = DOMAIN_SKILLS.get("utilities", {}).get("skills", [])
        writing = DOMAIN_SKILLS.get("writing-comm", {}).get("skills", [])
        assert "md-to-html" in utilities
        assert "md-to-html" in writing
