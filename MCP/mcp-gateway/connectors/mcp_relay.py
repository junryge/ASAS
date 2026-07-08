# -*- coding: utf-8 -*-
"""MCP 중계 커넥터 — 내부의 다른 MCP 서버들을 이 게이트웨이 하나로 묶는다.

게이트웨이가 다른 MCP 서버의 '클라이언트'가 되어 tool 목록 조회·호출을 대신 해준다.
"""
import logging

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

log = logging.getLogger("gateway.relay")


async def _open(url: str, fn):
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await fn(session)


def register(mcp, cfg: dict) -> None:
    rc = cfg.get("relay", {}) or {}
    servers: dict = rc.get("servers") or {}

    @mcp.tool()
    def relay_servers() -> dict:
        """중계 가능한 내부 MCP 서버 목록(이름: URL)을 반환한다."""
        return servers

    @mcp.tool()
    async def relay_list_tools(server: str) -> dict:
        """내부 MCP 서버의 tool 목록을 가져온다. server는 relay_servers에 등록된 이름."""
        if server not in servers:
            return {"error": f"등록되지 않은 서버: {server}", "allowed": list(servers)}
        try:
            async def fn(s: ClientSession):
                res = await s.list_tools()
                return {
                    "server": server,
                    "tools": [
                        {"name": t.name, "description": t.description} for t in res.tools
                    ],
                }
            return await _open(servers[server], fn)
        except Exception as e:
            log.warning("relay_list_tools 실패 %s: %s", server, e)
            return {"error": str(e), "url": servers[server]}

    @mcp.tool()
    async def relay_call(server: str, tool: str, arguments: dict | None = None) -> dict:
        """내부 MCP 서버의 tool을 대신 호출하고 결과를 반환한다."""
        if server not in servers:
            return {"error": f"등록되지 않은 서버: {server}", "allowed": list(servers)}
        log.info("relay_call %s.%s args=%s", server, tool, arguments)
        try:
            async def fn(s: ClientSession):
                res = await s.call_tool(tool, arguments or {})
                out = []
                for c in res.content:
                    out.append(c.text if getattr(c, "type", "") == "text" else str(c))
                return {"server": server, "tool": tool, "isError": res.isError, "content": out}
            return await _open(servers[server], fn)
        except Exception as e:
            log.warning("relay_call 실패 %s.%s: %s", server, tool, e)
            return {"error": str(e), "url": servers[server]}
