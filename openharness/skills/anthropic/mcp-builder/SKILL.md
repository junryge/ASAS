---
name: mcp-builder
description: Build Model Context Protocol (MCP) servers. TRIGGER when the user asks to create an MCP server, build MCP tools, or implement MCP protocol handlers.
---
# MCP Server Builder Skill

Guide for creating high-quality Model Context Protocol (MCP) servers.

## MCP Server Structure (Python)

```python
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("my-server")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="my_tool",
            description="What this tool does",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "Parameter description"}
                },
                "required": ["param1"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "my_tool":
        result = process(arguments["param1"])
        return [TextContent(type="text", text=result)]
```

## MCP Server Structure (TypeScript)

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

const server = new McpServer({ name: "my-server", version: "1.0.0" });

server.tool("my_tool", { param1: z.string() }, async ({ param1 }) => ({
    content: [{ type: "text", text: `Result: ${param1}` }]
}));
```

## Guidelines
- Provide clear tool descriptions
- Define proper input schemas with descriptions
- Handle errors gracefully
- Include proper logging
- Test with MCP Inspector
