"""MCP server for PyPLECS.

Exposes the plecs-expert skill content and pyplecs introspection over stdio
(Documentation MCP Server), and the Simulation Task lifecycle over stdio
(Simulation MCP Server, `pyplecs-mcp-sim`).

The `mcp` SDK is an OPTIONAL dependency. Importing this module raises
ImportError when `mcp` isn't installed, which lets the top-level
`pyplecs/__init__.py` degrade `create_mcp_server` to None on a clean
`pip install pyplecs` (without the `[mcp]` extra). Install with
`pip install pyplecs[mcp]`.
"""
from __future__ import annotations

from .server import build_server
from .server import main as _main
from .simulation_server import build_simulation_server


def create_mcp_server():
    """Create and return the MCP server instance (for embedding/testing)."""
    return build_server()


def create_simulation_mcp_server(orchestrator):
    """Create the Simulation MCP Server over one orchestrator (ADR-0011)."""
    return build_simulation_server(orchestrator)


def main() -> int:
    """Entry point for the `pyplecs-mcp` console script."""
    return _main()


__all__ = ["create_mcp_server", "create_simulation_mcp_server", "main"]
