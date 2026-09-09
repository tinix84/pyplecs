"""One normalized Simulation Result payload across REST and the Simulation MCP Server; the API boots live."""

import httpx
import pytest

import pyplecs.api as api
from pyplecs.api import _get_app, _register_routes, get_orchestrator
from pyplecs.config import ConfigManager
from pyplecs.core.models import SimulationRequest
from pyplecs.mcp.simulation_tools import build_simulation_catalogue
from pyplecs.orchestration import SimulationOrchestrator
from pyplecs.orchestration.live import LivePlecsAdapter


class Adapter:
    def is_available(self):
        return True

    def simulate_batch(self, parameter_list):
        return [{"Time": [0.0, 0.5, 1.0], "Values": [[24.0, 24.0, 24.0], [1.0, 2.0, 3.0]]} for _ in parameter_list]


def _config(tmp_path, **updates):
    config = ConfigManager(search_paths=[])
    config.update("cache.directory", str(tmp_path / "cache"))
    config.update("plecs.version", "test")
    config.update("orchestration.retry_attempts", 1)
    config.update("orchestration.retry_delay", 0)
    for key, value in updates.items():
        config.update(key, value)
    return config


async def _get(app, path):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(path)


async def _post(app, path, body):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(path, json=body)


@pytest.mark.asyncio
async def test_rest_result_route_returns_the_payload_the_mcp_result_tool_returns(tmp_path):
    config = _config(tmp_path)
    orchestrator = SimulationOrchestrator(Adapter(), config=config)
    app = _get_app(config)
    _register_routes(app, config, orchestrator_instance=orchestrator)
    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    catalogue = build_simulation_catalogue(orchestrator)
    model = tmp_path / "buck.plecs"
    model.touch()
    try:
        task_id = await orchestrator.submit_simulation(
            SimulationRequest(model_file=str(model), parameters={"Vi": 24.0}, output_variables=["v_in", "i_L"])
        )
        assert (await orchestrator.wait_for_completion(task_id, timeout=5)).status.value == "completed"

        rest = (await _get(app, f"/simulations/{task_id}/result")).json()
        mcp = await catalogue.dispatch_async("simulation_result", {"task_id": task_id})

        assert mcp.success
        assert rest["time"] == mcp.value["time"] == [0.0, 0.5, 1.0]
        assert rest["signals"] == mcp.value["signals"] == {"v_in": [24.0, 24.0, 24.0], "i_L": [1.0, 2.0, 3.0]}
        assert rest["timeseries_data"]["Time"] == {"0": 0.0, "1": 0.5, "2": 1.0}  # v1.x field kept
    finally:
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_pyplecs_api_startup_wires_the_live_plecs_adapter_without_opening_plecs(tmp_path):
    config = _config(tmp_path, **{"plecs.auto_launch": False})
    app = _get_app(config)
    _register_routes(app, config)
    async with app.router.lifespan_context(app):
        assert isinstance(api.orchestrator._plecs, LivePlecsAdapter)
        assert api.orchestrator.config is config


@pytest.mark.asyncio
async def test_sync_route_uses_the_configured_endpoint_and_the_shared_payload(tmp_path, monkeypatch):
    seen = {}

    class FakePlecsServer:
        def __init__(self, model_file, **kwargs):
            seen.update(kwargs, model_file=model_file)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def simulate(self, parameters=None):
            return {"Time": [0.0, 0.5, 1.0], "Values": [[24.0, 24.0, 24.0], [1.0, 2.0, 3.0]]}

    monkeypatch.setattr("pyplecs.api.simulation_sync.PlecsServer", FakePlecsServer)
    config = _config(tmp_path, **{"plecs.xmlrpc.port": 1234, "plecs.auto_launch": False})
    app = _get_app(config)
    model = tmp_path / "buck.plecs"
    model.touch()

    response = await _post(app, "/api/v1/simulations/sync", {"model_file": str(model), "signal_map": {"0": "v_in", "1": "i_L"}})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["time"] == [0.0, 0.5, 1.0] and body["signals"] == {"v_in": [24.0, 24.0, 24.0], "i_L": [1.0, 2.0, 3.0]}
    assert seen["port"] == "1234" and seen["auto_launch"] is False
