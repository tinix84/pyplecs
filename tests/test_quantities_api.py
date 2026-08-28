import threading

import httpx
import pytest

from pyplecs.api import _get_app, get_orchestrator
from pyplecs.config import ConfigManager
from pyplecs.core.models import SimulationRequest
from pyplecs.mcp.simulation_tools import build_simulation_catalogue
from pyplecs.orchestration import SimulationOrchestrator
from pyplecs.quantities import design_quantities_payload

SIGNAL_MAP = {
    "components": {"S1": {"voltage": "v_S", "current": "i_S"}},
    "ports": {"input": {"voltage": "v_S", "current": "i_S"}, "output": {"voltage": "v_S", "current": "i_S"}},
}


class Adapter:
    def is_available(self):
        return True

    def simulate_batch(self, parameter_list):
        return [
            {"Time": [0.0, 0.5, 1.0], "Values": [[10.0, 10.0, 10.0], [1.0, 2.0, 3.0]]}
            for _ in parameter_list
        ]


def _config(tmp_path):
    config = ConfigManager(search_paths=[])
    config.update("cache.directory", str(tmp_path / "cache"))
    config.update("plecs.version", "test")
    config.update("orchestration.retry_attempts", 1)
    config.update("orchestration.retry_delay", 0)
    return config


async def _completed_task(tmp_path, orchestrator, *, use_cache=True):
    model = tmp_path / "buck.plecs"
    model.touch()
    request = SimulationRequest(model_file=str(model), parameters={"Vi": 24.0}, output_variables=["v_S", "i_S"])
    task_id = await orchestrator.submit_simulation(request, use_cache=use_cache)
    snapshot = await orchestrator.wait_for_completion(task_id, timeout=5)
    assert snapshot.status.value == "completed"
    return task_id, snapshot


async def _post(app, path, body):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(path, json=body)


@pytest.mark.asyncio
async def test_rest_and_mcp_return_the_python_payload_and_leave_the_cache_untouched(tmp_path):
    config = _config(tmp_path)
    orchestrator = SimulationOrchestrator(Adapter(), config=config)
    app = _get_app(config)
    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    catalogue = build_simulation_catalogue(orchestrator)
    body = {"signal_map": SIGNAL_MAP, "window": {"switching_frequency": 2.0, "periods": 1}, "waveforms": ["i_S"]}
    try:
        task_id, snapshot = await _completed_task(tmp_path, orchestrator)
        cache_files = sorted(path.relative_to(tmp_path) for path in (tmp_path / "cache").rglob("*") if path.is_file())
        expected = design_quantities_payload(
            snapshot.result, signal_map=SIGNAL_MAP, window=body["window"], waveforms=["i_S"]
        )

        response = await _post(app, f"/api/v1/simulations/{task_id}/quantities", body)
        tool = await catalogue.dispatch_async("simulation_quantities", {"task_id": task_id, **body})

        assert response.status_code == 200 and response.json() == expected
        assert tool.success and tool.value == expected
        assert expected["stress"]["S1"]["current"]["mean"] == pytest.approx(2.5)
        assert expected["stress"]["S1"]["voltage"]["rms"] == pytest.approx(10.0)
        assert expected["power"]["efficiency"] == pytest.approx(1.0)
        assert expected["waveforms"]["i_S"]["time"] == [0.5, 1.0]
        assert sorted(
            path.relative_to(tmp_path) for path in (tmp_path / "cache").rglob("*") if path.is_file()
        ) == cache_files

        cached_id, cached_snapshot = await _completed_task(tmp_path, orchestrator)
        assert cached_snapshot.result.cached is True
        cached = await _post(app, f"/api/v1/simulations/{cached_id}/quantities", body)
        assert cached.json() == {**expected, "task_id": cached_id}
    finally:
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_rest_and_mcp_map_the_same_errors(tmp_path):
    config = _config(tmp_path)
    orchestrator = SimulationOrchestrator(Adapter(), config=config)
    app = _get_app(config)
    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    catalogue = build_simulation_catalogue(orchestrator)
    try:
        task_id, _ = await _completed_task(tmp_path, orchestrator)

        missing = await _post(app, "/api/v1/simulations/nope/quantities", {"signal_map": SIGNAL_MAP})
        assert missing.status_code == 404
        assert "unknown Simulation Task" in (
            await catalogue.dispatch_async("simulation_quantities", {"task_id": "nope"})
        ).error

        bad_map = {"signal_map": {"components": {"S1": {"voltage": "v_nope"}}}}
        response = await _post(app, f"/api/v1/simulations/{task_id}/quantities", bad_map)
        tool = await catalogue.dispatch_async("simulation_quantities", {"task_id": task_id, **bad_map})
        assert response.status_code == 400 and "'v_nope'" in response.json()["detail"]
        assert not tool.success and "'v_nope'" in tool.error

        short = {"signal_map": SIGNAL_MAP, "window": {"switching_frequency": 1.0, "periods": 5}}
        response = await _post(app, f"/api/v1/simulations/{task_id}/quantities", short)
        assert response.status_code == 400 and "5 required" in response.json()["detail"]

        assert "/api/v1/simulations/{task_id}/quantities" in app.openapi()["paths"]
    finally:
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_non_completed_task_is_a_400_naming_the_status(tmp_path):
    release = threading.Event()

    class Blocking(Adapter):
        def simulate_batch(self, parameter_list):
            release.wait(timeout=5)
            return super().simulate_batch(parameter_list)

    config = _config(tmp_path)
    orchestrator = SimulationOrchestrator(Blocking(), config=config)
    app = _get_app(config)
    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    catalogue = build_simulation_catalogue(orchestrator)
    model = tmp_path / "buck.plecs"
    model.touch()
    try:
        task_id = await orchestrator.submit_simulation(
            SimulationRequest(model_file=str(model), parameters={"Vi": 1.0}, output_variables=["v_S", "i_S"])
        )
        response = await _post(app, f"/api/v1/simulations/{task_id}/quantities", {"signal_map": SIGNAL_MAP})
        tool = await catalogue.dispatch_async("simulation_quantities", {"task_id": task_id})

        assert response.status_code == 400 and "Current status:" in response.json()["detail"]
        assert not tool.success and "not completed" in tool.error
    finally:
        release.set()
        await orchestrator.stop()
