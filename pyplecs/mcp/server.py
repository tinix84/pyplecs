"""Stdio MCP server exposing the plecs-expert tools."""
from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    TextContent,
    Tool,
)

from .plecs_tools import TOOL_CATALOGUE, ToolCatalogue


def _to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, indent=2, default=str)


def build_server(catalogue: ToolCatalogue = TOOL_CATALOGUE) -> Server:
    async def list_tools(_context: Any, _params: Any) -> ListToolsResult:
        return ListToolsResult(
            tools=[
                Tool(
                    name=definition.name,
                    description=definition.description,
                    input_schema=definition.input_schema,
                )
                for definition in catalogue.definitions
            ]
        )

    async def call_tool(
        _context: Any, params: CallToolRequestParams
    ) -> CallToolResult:
        outcome = catalogue.dispatch(params.name, params.arguments)
        text = outcome.error if not outcome.success else _to_text(outcome.value)
        return CallToolResult(
            content=[TextContent(type="text", text=text)],
            is_error=not outcome.success,
        )

    return Server(
        "pyplecs-mcp",
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )


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
