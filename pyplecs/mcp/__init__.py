"""MCP server for PyPLECS.

Exposes the plecs-expert skill content and pyplecs introspection over stdio.

The `mcp` SDK is an OPTIONAL dependency. Importing this module raises
ImportError when `mcp` isn't installed, which lets the top-level
`pyplecs/__init__.py` degrade `create_mcp_server` to None on a clean
`pip install pyplecs` (without the `[mcp]` extra). Install with
`pip install pyplecs[mcp]`.
"""
from __future__ import annotations

from .server import build_server
from .server import main as _main


def create_mcp_server():
    """Create and return the MCP server instance (for embedding/testing)."""
    return build_server()


def main() -> int:
    """Entry point for the `pyplecs-mcp` console script."""
    return _main()


__all__ = ["create_mcp_server", "main"]
