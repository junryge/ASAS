# -*- coding: utf-8 -*-
"""MCP 중계 커넥터 — 내부의 다른 MCP 서버들을 이 게이트웨이 하나로 묶는다.

게이트웨이가 다른 MCP 서버의 '클라이언트'가 되어 tool 목록 조회·호출을 대신 해준다.

중계 대상은 두 곳을 병합한다:
  1) config.yaml 의 relay.servers  (정적·손으로 관리)
  2) servers.yaml               (관리 콘솔에서 등록, 호출마다 재로딩 → 즉시 반영)
이름이 겹치면 콘솔(servers.yaml) 쪽이 우선한다.
"""
import logging
from pathlib import Path

import yaml
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

log = logging.getLogger("gateway.relay")

# server.py 와 같은 폴더(mcp-gateway/)에 저장되는 콘솔 등록 파일
SERVERS_YAML = Path(__file__).resolve().parent.parent / "servers.yaml"


def _entry_url(entry: dict) -> str | None:
    """콘솔 서버 항목(dict) → Streamable HTTP URL 문자열.

    지원 포맷:
      - {"url": "http://10.0.0.41:8020/mcp"}   → 그대로 사용
      - {"host": "10.0.0.41", "port": 8020}    → http://host:port/mcp 로 조립
        (path/scheme 지정 시 반영, 기본 /mcp · http)
    """
    url = entry.get("url") or entry.get("address")
    if url:
        return str(url).strip()
    host = entry.get("host")
    if not host:
        return None
    scheme = "https" if str(entry.get("scheme", "http")).lower() == "https" else "http"
    port = entry.get("port")
    hostpart = f"{host}:{port}" if port else str(host)
    path = str(entry.get("path") or "/mcp")
    if not path.startswith("/"):
        path = "/" + path
    return f"{scheme}://{hostpart}{path}"


def _console_servers() -> dict:
    """servers.yaml(리스트) → {이름: URL}. 파싱 실패해도 게이트웨이는 안 죽는다."""
    if not SERVERS_YAML.is_file():
        return {}
    try:
        data = yaml.safe_load(SERVERS_YAML.read_text(encoding="utf-8")) or []
    except Exception as e:  # YAML 깨져도 정적 서버는 계속 동작
        log.warning("servers.yaml 읽기 실패 — 콘솔 서버 무시: %s", e)
        return {}
    out: dict = {}
    if isinstance(data, list):
        for entry in data:
            if not isinstance(entry, dict):
                continue
            if entry.get("enabled") is False:  # 명시적 비활성만 제외
                continue
            name = entry.get("name")
            url = _entry_url(entry)
            if name and url:
                out[str(name)] = url
    return out


async def _open(url: str, fn):
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await fn(session)


def register(mcp, cfg: dict) -> None:
    rc = cfg.get("relay", {}) or {}
    static: dict = dict(rc.get("servers") or {})

    def servers() -> dict:
        """정적(config) + 콘솔(servers.yaml) 병합. 이름 충돌 시 콘솔 우선."""
        merged = dict(static)
        merged.update(_console_servers())
        return merged

    @mcp.tool()
    def relay_servers() -> dict:
        """중계 가능한 내부 MCP 서버 목록(이름: URL)을 반환한다.

        config.yaml relay.servers 와 관리 콘솔 등록(servers.yaml)을 합친 결과다.
        """
        return servers()

    @mcp.tool()
    async def relay_list_tools(server: str) -> dict:
        """내부 MCP 서버의 tool 목록을 가져온다. server는 relay_servers에 등록된 이름."""
        current = servers()
        if server not in current:
            return {"error": f"등록되지 않은 서버: {server}", "allowed": list(current)}
        url = current[server]
        try:
            async def fn(s: ClientSession):
                res = await s.list_tools()
                return {
                    "server": server,
                    "tools": [
                        {"name": t.name, "description": t.description} for t in res.tools
                    ],
                }
            return await _open(url, fn)
        except Exception as e:
            log.warning("relay_list_tools 실패 %s: %s", server, e)
            return {"error": str(e), "url": url}

    @mcp.tool()
    async def relay_call(server: str, tool: str, arguments: dict | None = None) -> dict:
        """내부 MCP 서버의 tool을 대신 호출하고 결과를 반환한다."""
        current = servers()
        if server not in current:
            return {"error": f"등록되지 않은 서버: {server}", "allowed": list(current)}
        url = current[server]
        log.info("relay_call %s.%s args=%s", server, tool, arguments)
        try:
            async def fn(s: ClientSession):
                res = await s.call_tool(tool, arguments or {})
                out = []
                for c in res.content:
                    out.append(c.text if getattr(c, "type", "") == "text" else str(c))
                return {"server": server, "tool": tool, "isError": res.isError, "content": out}
            return await _open(url, fn)
        except Exception as e:
            log.warning("relay_call 실패 %s.%s: %s", server, tool, e)
            return {"error": str(e), "url": url}
