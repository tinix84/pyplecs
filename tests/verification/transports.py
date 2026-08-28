"""Drive the canonical Operating Point through each transport and reduce every answer to ``time`` + ``signals``."""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any, AsyncIterator

import httpx
from mcp.client.session import ClientSession
from mcp.shared.memory import create_client_server_memory_streams

from pyplecs.api import _get_app, _register_routes, get_orchestrator
from pyplecs.core.models import SimulationRequest
from pyplecs.mcp.simulation_server import build_simulation_server
from pyplecs.orchestration import SimulationOrchestrator

from .manifest import Manifest
from .oracle import result_payload


def canonical_request(manifest: Manifest) -> SimulationRequest:
    return SimulationRequest(
        model_file=str(manifest.model_file),
        parameters=manifest.parameters,
        output_variables=manifest.signals,
    )


async def through_python(orchestrator: SimulationOrchestrator, manifest: Manifest, *, use_cache: bool = False) -> dict[str, Any]:
    task_id = await orchestrator.submit_simulation(canonical_request(manifest), use_cache=use_cache)
    snapshot = await orchestrator.wait_for_completion(task_id, timeout=120)
    assert snapshot is not None and snapshot.status.value == "completed", snapshot
    return {**result_payload(snapshot.result), "cached": snapshot.result.cached, "task_id": task_id}


def rest_app(orchestrator: SimulationOrchestrator, config):
    app = _get_app(config)
    _register_routes(app, config, orchestrator_instance=orchestrator)
    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    return app


async def through_rest_async(app, manifest: Manifest, *, use_cache: bool = False, timeout: float = 120) -> dict[str, Any]:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", timeout=timeout) as client:
        submitted = await client.post(
            "/simulations",
            json={
                "model_file": str(manifest.model_file),
                "parameters": manifest.parameters,
                "output_variables": manifest.signals,
                "use_cache": use_cache,
            },
        )
        assert submitted.status_code == 200, submitted.text
        task_id = submitted.json()["task_id"]
        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            status = (await client.get(f"/simulations/{task_id}")).json()
            if status["status"] in {"completed", "failed", "cancelled"}:
                break
            assert asyncio.get_running_loop().time() < deadline, "REST Simulation Task did not become terminal"
            await asyncio.sleep(0.02)
        assert status["status"] == "completed", status
        result = (await client.get(f"/simulations/{task_id}/result")).json()
    return {"time": result["time"], "signals": result["signals"], "cached": result["cached"], "task_id": task_id}


async def through_rest_sync(app, manifest: Manifest, prefix: str, *, timeout: float = 120) -> dict[str, Any]:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", timeout=timeout) as client:
        response = await client.post(
            f"{prefix}/simulations/sync",
            json={
                "model_file": str(manifest.model_file),
                "parameters": manifest.parameters,
                "signal_map": {str(index): name for index, name in enumerate(manifest.signals)},
            },
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"], body
    return {"time": body["time"], "signals": body["signals"]}


@contextlib.asynccontextmanager
async def mcp_client(orchestrator: SimulationOrchestrator) -> AsyncIterator[ClientSession]:
    """A real MCP client session speaking JSON-RPC to the Simulation MCP Server over memory streams."""
    server = build_simulation_server(orchestrator)
    async with create_client_server_memory_streams() as (client_streams, server_streams):
        server_task = asyncio.create_task(
            server.run(server_streams[0], server_streams[1], server.create_initialization_options(), raise_exceptions=True)
        )
        try:
            async with ClientSession(*client_streams) as session:
                await session.initialize()
                yield session
        finally:
            server_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await server_task


async def call(session: ClientSession, name: str, **arguments: Any) -> Any:
    outcome = await session.call_tool(name, arguments)
    text = "".join(getattr(item, "text", "") for item in outcome.content)
    assert not outcome.is_error, f"{name} failed: {text}"
    return json.loads(text)


async def through_mcp(session: ClientSession, manifest: Manifest, *, use_cache: bool = False) -> dict[str, Any]:
    submitted = await call(
        session,
        "simulation_submit",
        model_file=str(manifest.model_file),
        parameters=manifest.parameters,
        output_variables=manifest.signals,
        use_cache=use_cache,
    )
    waited = await call(session, "simulation_wait", task_id=submitted["task_id"], timeout_s=120)
    assert waited["terminal"] and waited["status"] == "completed", waited
    result = await call(session, "simulation_result", task_id=submitted["task_id"])
    return {"time": result["time"], "signals": result["signals"], "cached": result["cached"], "task_id": submitted["task_id"]}
