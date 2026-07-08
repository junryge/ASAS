# -*- coding: utf-8 -*-
"""폐쇄망 MCP 클라이언트 앱 — 니 PC에서 실행.

흐름:  질문 → 내부 LLM(vLLM, tool calling) → 게이트웨이 MCP tool 실행 → 결과로 최종 답변

실행:
  python app.py                    # 대화 모드
  python app.py "OHT 상태 알려줘"   # 단발 질문
"""
import asyncio
import json
import sys
from pathlib import Path

import requests
import yaml
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

BASE = Path(__file__).resolve().parent

with open(BASE / "config.yaml", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

LLM = CFG["llm"]
GATEWAY_URL = CFG["gateway"]["url"]
MAX_ROUNDS = int(CFG.get("max_tool_rounds", 5))


def resolve_api_key() -> str:
    """API 키 탐색: 환경변수 LLM_API_KEY → api_key_file → config api_key."""
    import os
    key = os.environ.get("LLM_API_KEY", "").strip()
    if key:
        return key
    kf = LLM.get("api_key_file")
    if kf:
        p = Path(kf) if Path(kf).is_absolute() else BASE / kf
        if p.is_file():
            key = p.read_text(encoding="utf-8").strip()
            if key:
                return key
    return LLM.get("api_key", "EMPTY")


API_KEY = resolve_api_key()


def chat(messages: list, tools: list) -> dict:
    """내부 LLM(OpenAI 호환 /chat/completions) 호출."""
    r = requests.post(
        LLM["base_url"].rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": LLM["model"],
            "messages": messages,
            "tools": tools,
            "temperature": LLM.get("temperature", 0.2),
        },
        timeout=LLM.get("timeout", 120),
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]


def to_openai_tools(mcp_tools) -> list:
    """MCP tool 정의 → OpenAI tool calling 스키마 변환."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema or {"type": "object", "properties": {}},
            },
        }
        for t in mcp_tools
    ]


async def ask(session: ClientSession, oai_tools: list, messages: list, question: str) -> None:
    """질문 하나 처리: LLM ↔ tool 호출 루프."""
    messages.append({"role": "user", "content": question})
    for _ in range(MAX_ROUNDS):
        msg = chat(messages, oai_tools)
        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            answer = msg.get("content") or ""
            print(answer)
            messages.append({"role": "assistant", "content": answer})
            return
        messages.append(msg)
        for tc in tool_calls:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            print(f"  [tool] {name} {args}")
            try:
                res = await session.call_tool(name, args)
                text = "\n".join(
                    c.text for c in res.content if getattr(c, "type", "") == "text"
                )
            except Exception as e:
                text = json.dumps({"error": str(e)}, ensure_ascii=False)
            messages.append(
                {"role": "tool", "tool_call_id": tc["id"], "content": text[:8000]}
            )
    print("(tool 호출 한도 초과 — max_tool_rounds 확인)")


async def main() -> None:
    async with streamablehttp_client(GATEWAY_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = (await session.list_tools()).tools
            oai_tools = to_openai_tools(mcp_tools)
            print(f"게이트웨이 연결됨 ({GATEWAY_URL}) · tool {len(mcp_tools)}개")

            messages = [{"role": "system", "content": CFG.get("system_prompt", "")}]

            if len(sys.argv) > 1:  # 단발 질문 모드
                await ask(session, oai_tools, messages, " ".join(sys.argv[1:]))
                return

            while True:  # 대화 모드
                try:
                    q = input("\n질문> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not q or q.lower() in ("exit", "quit", "종료"):
                    break
                await ask(session, oai_tools, messages, q)


if __name__ == "__main__":
    asyncio.run(main())
