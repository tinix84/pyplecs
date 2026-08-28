"""Stdio Simulation MCP Server: the executable counterpart of ``pyplecs-mcp``.

Kept as a separate console command on purpose (ADR-0011): the Documentation
MCP Server is safe to hand to anyone, a server that can start PLECS is not.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server

from ..config import ConfigManager, get_config
from ..orchestration import SimulationOrchestrator
from ..orchestration.live import LivePlecsAdapter
from .server import build_server
from .simulation_tools import build_simulation_catalogue

SERVER_NAME = "pyplecs-mcp-sim"


def build_simulation_server(orchestrator: SimulationOrchestrator) -> Server:
    """Wrap one orchestrator in a stdio MCP server (for embedding and tests)."""
    return build_server(build_simulation_catalogue(orchestrator), name=SERVER_NAME)


def build_orchestrator(config: Optional[ConfigManager] = None) -> SimulationOrchestrator:
    """The production orchestrator behind the console command."""
    resolved = config or get_config()
    return SimulationOrchestrator(LivePlecsAdapter(resolved), config=resolved)


async def _serve(config: Optional[ConfigManager] = None) -> None:
    orchestrator = build_orchestrator(config)
    await orchestrator.start()
    try:
        server = build_simulation_server(orchestrator)
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())
    finally:
        await orchestrator.stop()


def main() -> int:
    """Entry point for the ``pyplecs-mcp-sim`` console script."""
    try:
        asyncio.run(_serve())
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"{SERVER_NAME} error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
