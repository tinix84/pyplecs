"""Web GUI package for PyPLECS."""

from .webgui import create_web_app, run_app, WebSocketManager

__all__ = ['create_web_app', 'run_app', 'WebSocketManager']