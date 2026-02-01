"""Web GUI for PyPLECS simulation monitoring and control."""

import json
import logging
from pathlib import Path
from typing import List

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn

from ..config import get_config


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


def create_web_app():
    """Create and configure the web application."""
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
            config = get_config()
            cache_dir = config.cache.directory

            import os

            total_entries = 0
            total_size = 0

            if os.path.exists(cache_dir):
                for root, _, files in os.walk(cache_dir):
                    total_entries += len(files)
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            total_size += os.path.getsize(file_path)
                        except OSError:
                            continue

            return {
                "total_entries": total_entries,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "cache_directory": cache_dir,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/api/cache/clear")
    async def clear_cache():
        """Clear cache."""
        return {"message": "Cache clear not implemented yet"}

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


def run_app(host: str = "127.0.0.1", port: int = 8001):
    """Run the web application."""
    app, _ = create_web_app()
    logger.info(f"Starting PyPLECS Web GUI on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


def main():
    """Entry point for pyplecs-gui command."""
    app, _ = create_web_app()
    uvicorn.run(app, host="127.0.0.1", port=8001)
