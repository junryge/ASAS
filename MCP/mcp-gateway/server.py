# -*- coding: utf-8 -*-
"""AMHS MCP Gateway — 폐쇄망 MCP 서버 본체.

실행:  python server.py
접속:  http://<서버IP>:8010/mcp  (Streamable HTTP)
콘솔:  http://<서버IP>:8010/console  (관리 화면, 저장은 servers.yaml)
"""
import logging
import sys
from pathlib import Path

import yaml
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import (
    FileResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from connectors import rest, db, files, mcp_relay  # noqa: E402


def load_config() -> dict:
    with open(BASE / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_servers() -> list:
    """콘솔에서 등록한 MCP 서버 목록 (servers.yaml)."""
    p = BASE / "servers.yaml"
    if p.is_file():
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or []
        return data if isinstance(data, list) else []
    return []


def save_servers(items: list) -> None:
    (BASE / "servers.yaml").write_text(
        yaml.safe_dump(items, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def setup_logging(cfg: dict) -> None:
    lc = cfg.get("logging", {}) or {}
    logging.basicConfig(
        level=getattr(logging, str(lc.get("level", "INFO")).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(BASE / lc.get("file", "gateway.log"), encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def build_server() -> FastMCP:
    cfg = load_config()
    setup_logging(cfg)
    sc = cfg.get("server", {}) or {}
    mcp = FastMCP(
        sc.get("name", "amhs-mcp-gateway"),
        host=sc.get("host", "0.0.0.0"),
        port=int(sc.get("port", 8010)),
    )
    # 커넥터별 tool 등록
    rest.register(mcp, cfg)
    db.register(mcp, cfg)
    files.register(mcp, cfg)
    mcp_relay.register(mcp, cfg)

    @mcp.tool()
    def gateway_info() -> dict:
        """게이트웨이 상태·설정 요약을 반환한다 (연결 확인용)."""
        return {
            "name": sc.get("name", "amhs-mcp-gateway"),
            "port": sc.get("port", 8010),
            "rest_endpoints": list((cfg.get("rest", {}).get("endpoints") or {}).keys()),
            "db_connections": list((cfg.get("db", {}).get("connections") or {}).keys()),
            "file_roots": list((cfg.get("files", {}).get("roots") or {}).keys()),
            "relay_servers": list((cfg.get("relay", {}).get("servers") or {}).keys()),
            "registered_servers": [s.get("name") for s in load_servers()],
        }

    # ---- 관리 API (콘솔 HTML ↔ YAML 저장) ----
    CORS = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

    @mcp.custom_route("/", methods=["GET"])
    async def root(request: Request):
        """루트 → 오프닝 페이지 (AMHS_MCP_OP.html). 없으면 콘솔로."""
        rel = sc.get("opening_html", "../INDEX/AMHS_MCP_OP.html")
        p = (BASE / rel).resolve()
        if p.is_file():
            return FileResponse(p, media_type="text/html")
        return RedirectResponse(url="/console")

    @mcp.custom_route("/console", methods=["GET"])
    async def console(request: Request):
        """관리 콘솔 HTML 서빙 — http://<서버IP>:8010/console"""
        rel = sc.get("console_html", "../INDEX/MCP_Console.html")
        p = (BASE / rel).resolve()
        if p.is_file():
            return FileResponse(p, media_type="text/html")
        return PlainTextResponse(f"console HTML 없음: {p}", status_code=404)

    @mcp.custom_route("/admin/tools", methods=["GET"])
    async def admin_tools(request: Request):
        """게이트웨이에 등록된 tool 목록 — 콘솔 '도구' 탭에서 사용."""
        tools = await mcp.list_tools()
        return JSONResponse(
            [{"name": t.name, "description": (t.description or "").strip().split("\n")[0]} for t in tools],
            headers=CORS,
        )

    @mcp.custom_route("/admin/servers", methods=["GET", "POST", "OPTIONS"])
    async def admin_servers(request: Request):
        """콘솔의 서버 등록 목록 조회(GET)/저장(POST) → servers.yaml"""
        if request.method == "OPTIONS":
            return Response(status_code=204, headers=CORS)
        if request.method == "GET":
            return JSONResponse(load_servers(), headers=CORS)
        try:
            items = await request.json()
        except Exception:
            return JSONResponse({"error": "JSON 파싱 실패"}, status_code=400, headers=CORS)
        if not isinstance(items, list):
            return JSONResponse({"error": "list 형식이어야 한다"}, status_code=400, headers=CORS)
        save_servers(items)
        logging.getLogger("gateway.admin").info("servers.yaml 저장 — %d건", len(items))
        return JSONResponse({"ok": True, "count": len(items)}, headers=CORS)

    return mcp


if __name__ == "__main__":
    server = build_server()
    logging.getLogger("gateway").info("AMHS MCP Gateway 시작 — Streamable HTTP")
    server.run(transport="streamable-http")
