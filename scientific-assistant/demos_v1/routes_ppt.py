"""
demos_v1/routes_ppt.py - PPT 설계 모드 API

엔드포인트 4개:
- POST /api/ppt/from-md          : MD 텍스트 → .pptx 생성 → id 반환
- POST /api/ppt/from-md-file     : .md 파일 업로드 → .pptx 생성 → id 반환
- POST /api/ppt/from-blocks      : 채팅 빌더 JSON → .pptx 생성 → id 반환 (Phase 3)
- GET  /api/ppt/download/<id>    : .pptx 파일 다운로드
"""
import os
from flask import request, jsonify, send_file

from demos_v1.ppt_builder import (
    md_to_pptx_file, render_outline_to_pptx, save_pptx, get_pptx_path,
    parse_md_to_outline,
)


def register_ppt_routes(app):
    """Flask 앱에 PPT 설계 모드 라우트 등록."""

    @app.route("/api/ppt/from-md", methods=["POST"])
    def api_ppt_from_md():
        """MD 텍스트 → .pptx 자동 생성."""
        data = request.json or {}
        md_text = (data.get("md") or data.get("markdown") or "").strip()
        title_hint = (data.get("title") or "").strip()
        if not md_text:
            return jsonify({"error": "MD 텍스트가 비어있습니다."}), 400
        try:
            info = md_to_pptx_file(md_text, title_hint=title_hint)
            return jsonify({
                "ok": True,
                "id": info["id"],
                "filename": info["filename"],
                "size": info["size"],
                "slide_count": info["slide_count"],
                "download_url": f"/api/ppt/download/{info['id']}",
                "slides_summary": [
                    {"type": s.get("type"), "title": s.get("title", "")}
                    for s in info.get("outline", {}).get("slides", [])
                ],
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"변환 실패: {e}"}), 500

    @app.route("/api/ppt/from-md-file", methods=["POST"])
    def api_ppt_from_md_file():
        """.md 파일 업로드 → .pptx 자동 생성."""
        if "file" not in request.files:
            return jsonify({"error": "파일이 첨부되지 않았습니다."}), 400
        f = request.files["file"]
        if not f or not f.filename:
            return jsonify({"error": "빈 파일입니다."}), 400
        if not f.filename.lower().endswith((".md", ".markdown", ".txt")):
            return jsonify({"error": ".md / .markdown / .txt 파일만 허용됩니다."}), 400
        raw = f.read()
        # 인코딩 자동 감지 (utf-8 → utf-8-sig → cp949 → euc-kr)
        md_text = None
        for enc in ("utf-8", "utf-8-sig", "cp949", "euc-kr"):
            try:
                md_text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if md_text is None:
            return jsonify({"error": "파일 인코딩을 해석할 수 없습니다."}), 400
        title_hint = os.path.splitext(f.filename)[0]
        try:
            info = md_to_pptx_file(md_text, title_hint=title_hint)
            return jsonify({
                "ok": True,
                "id": info["id"],
                "filename": info["filename"],
                "size": info["size"],
                "slide_count": info["slide_count"],
                "download_url": f"/api/ppt/download/{info['id']}",
                "source_filename": f.filename,
                "slides_summary": [
                    {"type": s.get("type"), "title": s.get("title", "")}
                    for s in info.get("outline", {}).get("slides", [])
                ],
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"변환 실패: {e}"}), 500

    @app.route("/api/ppt/from-blocks", methods=["POST"])
    def api_ppt_from_blocks():
        """채팅 빌더 JSON (outline 형식) → .pptx 생성. Phase 3 UI 용."""
        data = request.json or {}
        outline = data.get("outline")
        if not outline or not isinstance(outline, dict):
            return jsonify({"error": "outline JSON 이 필요합니다."}), 400
        slides = outline.get("slides", [])
        if not slides:
            return jsonify({"error": "슬라이드가 비어있습니다."}), 400
        try:
            pptx_bytes = render_outline_to_pptx(outline)
            title = outline.get("meta", {}).get("title", "presentation")
            info = save_pptx(pptx_bytes, hint=title)
            return jsonify({
                "ok": True,
                "id": info["id"],
                "filename": info["filename"],
                "size": info["size"],
                "slide_count": len(slides),
                "download_url": f"/api/ppt/download/{info['id']}",
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"변환 실패: {e}"}), 500

    @app.route("/api/ppt/preview-outline", methods=["POST"])
    def api_ppt_preview_outline():
        """MD 파싱만 해서 outline 구조 미리보기 (실제 .pptx 안 만듦)."""
        data = request.json or {}
        md_text = (data.get("md") or "").strip()
        if not md_text:
            return jsonify({"error": "MD 텍스트가 비어있습니다."}), 400
        try:
            outline = parse_md_to_outline(md_text)
            return jsonify({"ok": True, "outline": outline,
                           "slide_count": len(outline.get("slides", []))})
        except Exception as e:
            return jsonify({"error": f"파싱 실패: {e}"}), 500

    @app.route("/api/ppt/download/<ppt_id>", methods=["GET"])
    def api_ppt_download(ppt_id):
        """저장된 .pptx 다운로드."""
        path = get_pptx_path(ppt_id)
        if not path or not os.path.exists(path):
            return jsonify({"error": "파일을 찾을 수 없습니다."}), 404
        return send_file(
            path,
            mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            as_attachment=True,
            download_name=os.path.basename(path),
        )

    print("[ppt] 라우트 등록 완료 (from-md, from-md-file, from-blocks, preview-outline, download)")
