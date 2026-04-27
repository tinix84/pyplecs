"""Stdio MCP server exposing the plecs-expert tools."""
from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .plecs_tools import TOOL_REGISTRY


def _to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, indent=2, default=str)


def build_server() -> Server:
    server: Server = Server("pyplecs-mcp")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=name,
                description=(fn.__doc__ or name).strip().splitlines()[0],
                inputSchema={
                    "type": "object",
                    "properties": {"argument": {"type": "string"}},
                    "required": [],
                },
            )
            for name, fn in TOOL_REGISTRY.items()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        fn = TOOL_REGISTRY.get(name)
        if fn is None:
            return [TextContent(type="text", text=f"unknown tool: {name}")]
        arg = arguments.get("argument", "")
        try:
            result = fn(arg) if arg else fn()
        except TypeError:
            result = fn()
        return [TextContent(type="text", text=_to_text(result))]

    return server


async def _serve() -> None:
    server = build_server()
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> int:
    try:
        asyncio.run(_serve())
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"pyplecs-mcp error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
