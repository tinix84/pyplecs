"""Web GUI for PyPLECS simulation monitoring and control."""

import json
import logging
import os
from pathlib import Path
from typing import List

import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..cache import SimulationCache
from ..config import ConfigManager, get_config

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            f"WebSocket connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(
            f"WebSocket disconnected. Total connections: {len(self.active_connections)}"
        )

    async def broadcast_json(self, data: dict):
        """Broadcast JSON data to all connected clients."""
        message = json.dumps(data)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)

        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)


def create_web_app(
    config: ConfigManager | None = None, cache: SimulationCache | None = None
):
    """Create and configure the web application."""
    resolved_config = config or get_config()
    simulation_cache = cache or SimulationCache(resolved_config.cache)
    app = FastAPI(
        title="PyPLECS Web GUI",
        description="Web interface for PLECS simulation monitoring and control",
        version="1.0.0",
    )

    # Use package-relative paths for static files and templates
    package_dir = Path(__file__).parent
    static_dir = package_dir / "static"
    templates_dir = package_dir / "templates"

    # Mount static files
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Setup templates
    templates = Jinja2Templates(directory=str(templates_dir))

    # Initialize WebSocket manager
    websocket_manager = WebSocketManager()

    # Page routes
    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        """Main dashboard page."""
        return templates.TemplateResponse("dashboard.html", {"request": request})

    @app.get("/simulations")
    async def simulations_page(request: Request):
        """Simulation management page"""
        return templates.TemplateResponse("simulations.html", {"request": request})

    @app.get("/cache")
    async def cache_page(request: Request):
        """Cache management page"""
        return templates.TemplateResponse("cache.html", {"request": request})

    @app.get("/settings")
    async def settings_page(request: Request):
        """Settings page"""
        return templates.TemplateResponse("settings.html", {"request": request})

    # API routes
    @app.get("/api/status")
    async def get_status():
        """Get system status and statistics."""
        return {
            "status": "running",
            "version": "1.0.0",
            "stats": {"total_tasks": 0, "completed_tasks": 0},
            "workers": [],
        }

    @app.get("/api/simulations")
    async def get_simulations(limit: int = 50, offset: int = 0):
        """Get list of simulations with pagination."""
        return {"tasks": [], "total": 0, "limit": limit, "offset": offset}

    @app.get("/api/cache/stats")
    async def get_cache_stats():
        """Get cache statistics."""
        try:
            return simulation_cache.get_cache_stats()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/api/cache/clear")
    async def clear_cache():
        """Clear cache."""
        simulation_cache.clear_cache()
        return {"message": "Cache cleared successfully"}

    # WebSocket endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time updates."""
        await websocket_manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            websocket_manager.disconnect(websocket)

    return app, templates


def run_app(
    host: str | None = None,
    port: int | None = None,
    config: ConfigManager | None = None,
):
    """Run the web application."""
    resolved_config = config or get_config()
    resolved_host = host or resolved_config.webgui.host
    resolved_port = port or resolved_config.webgui.port
    app, _ = create_web_app(resolved_config)
    logger.info(f"Starting PyPLECS Web GUI on http://{resolved_host}:{resolved_port}")
    uvicorn.run(app, host=resolved_host, port=resolved_port)


def main():
    """Entry point for pyplecs-gui command.

    PYPLECS_HOST / PYPLECS_PORT override the defaults; they were the only
    capability the deleted tools/start_webgui.py had over this entry point.
    """
    config = get_config()
    run_app(
        host=os.environ.get("PYPLECS_HOST", config.webgui.host),
        port=int(os.environ.get("PYPLECS_PORT", str(config.webgui.port))),
        config=config,
    )
