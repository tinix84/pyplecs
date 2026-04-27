"""MCP server for PyPLECS.

Exposes the plecs-expert skill content and pyplecs introspection over stdio.
"""
from __future__ import annotations


def create_mcp_server():
    """Create and return the MCP server instance (for embedding/testing)."""
    from .server import build_server
    return build_server()


def main() -> int:
    """Entry point for the `pyplecs-mcp` console script."""
    from .server import main as _main
    return _main()


__all__ = ["create_mcp_server", "main"]
