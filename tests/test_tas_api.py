import asyncio
import json
import threading
from pathlib import Path

import httpx
import pytest

from pyplecs.api import _get_app, get_orchestrator
from pyplecs.config import ConfigManager
from pyplecs.orchestration import SimulationOrchestrator

FIXTURE = Path(__file__).parent / "fixtures" / "tas_buck_inline.json"


def _document():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _config(tmp_path, *, prefix="/api/v1", batch_size=8):
    config = ConfigManager(search_paths=[])
    config.update("cache.directory", str(tmp_path / "cache"))
    config.update("orchestration.retry_attempts", 1)
    config.update("orchestration.retry_delay", 0)
    config.update("orchestration.max_concurrent_simulations", batch_size)
    config.update("api.prefix", prefix)
    return config


class ApiPlecsAdapter:
    def __init__(self, *, fail_vin=None, available=True):
        self.fail_vin = fail_vin
        self.available = available
        self.calls = []

    def is_available(self):
        return self.available

    def simulate_batch(self, parameter_list):
        parameters = [dict(vector) for vector in parameter_list]
        self.calls.append(parameters)
        return [
            {}
            if vector["Vin"] == self.fail_vin
            else {
                "Time": [0.0, vector["T_sim"]],
                "Values": [
                    [vector["Vin"] + signal, vector["Vin"] + signal]
                    for signal in range(4)
                ],
            }
            for vector in parameters
        ]


class BlockingApiPlecsAdapter(ApiPlecsAdapter):
    def __init__(self):
        super().__init__()
        self.started = threading.Event()
        self.release = threading.Event()

    def simulate_batch(self, parameter_list):
        self.started.set()
        if not self.release.wait(timeout=5):
            raise TimeoutError("test adapter was not released")
        return super().simulate_batch(parameter_list)


def _app(tmp_path, adapter, *, prefix="/api/v1", batch_size=8):
    config = _config(tmp_path, prefix=prefix, batch_size=batch_size)
    orchestrator = SimulationOrchestrator(adapter, config=config)
    app = _get_app(config)
    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    return app, orchestrator


async def _post(app, path, body):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(path, json=body)


async def _get(app, path):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


async def _wait_terminal(app, study_id, *, timeout=2):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        response = await _get(app, f"/api/v1/tas/studies/{study_id}")
        body = response.json()
        if body["status"] in {"completed", "partial_failure", "failed"}:
            return response
        await asyncio.sleep(0.01)
    raise AssertionError("TAS study did not become terminal")


@pytest.mark.asyncio
async def test_sync_tas_route_returns_the_python_execution_envelope(tmp_path):
    app, orchestrator = _app(tmp_path, ApiPlecsAdapter())
    source = _document()
    source["outputs"] = {"existing": "unchanged"}
    try:
        response = await _post(
            app,
            "/api/v1/tas/studies/sync",
            {"tas": source, "timeout": 2, "use_cache": False},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["tas"] == source
        assert body["tas"]["outputs"] == {"existing": "unchanged"}
        assert body["status"] == "completed"
        assert [point["name"] for point in body["points"]] == ["nominal", "high_line"]
        assert list(body["points"][0]["result"]["signals"]) == [
            "Vin.voltage",
            "Vin.current",
            "Vout.voltage",
            "Vout.current",
        ]
        assert len(body["aggregate"]) == 2
        assert all(set(diagnostic) == {"code", "location", "severity", "message"} for diagnostic in body["diagnostics"])
        assert "_tasks" not in response.text
    finally:
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_sync_tas_route_returns_partial_failure_as_terminal_answer(tmp_path):
    app, orchestrator = _app(tmp_path, ApiPlecsAdapter(fail_vin=14.0))
    try:
        response = await _post(
            app,
            "/api/v1/tas/studies/sync",
            {"tas": _document(), "use_cache": False},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "partial_failure"
        assert [point["status"] for point in body["points"]] == ["completed", "failed"]
        assert body["points"][1]["error"]
    finally:
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_sync_tas_route_maps_preflight_failures(tmp_path):
    app, orchestrator = _app(tmp_path, ApiPlecsAdapter(available=False))
    try:
        invalid = await _post(
            app,
            "/api/v1/tas/studies/sync",
            {
                "tas": _document(),
                "captures": [
                    {"name": "bad", "kind": "net", "target": "missing", "signal": "voltage"}
                ],
            },
        )
        assert invalid.status_code == 422
        assert invalid.json()["detail"][0]["code"] == "TAS_UNKNOWN_CAPTURE_TARGET"
        assert orchestrator.get_orchestrator_stats()["total_submitted"] == 0

        unavailable = await _post(
            app,
            "/api/v1/tas/studies/sync",
            {"tas": _document()},
        )
        assert unavailable.status_code == 503
        assert orchestrator.get_orchestrator_stats()["total_submitted"] == 0
    finally:
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_sync_tas_route_maps_caller_timeout(tmp_path):
    adapter = BlockingApiPlecsAdapter()
    app, orchestrator = _app(tmp_path, adapter)
    try:
        response = await _post(
            app,
            "/api/v1/tas/studies/sync",
            {"tas": _document(), "timeout": 0.01, "use_cache": False},
        )

        assert response.status_code == 504
        assert "timed out" in response.json()["detail"]
    finally:
        adapter.release.set()
        await orchestrator.stop()


def test_tas_routes_follow_custom_api_prefix(tmp_path):
    app, _ = _app(tmp_path, ApiPlecsAdapter(), prefix="/custom")

    assert "/custom/tas/studies/sync" in app.openapi()["paths"]
    assert "/custom/tas/studies" in app.openapi()["paths"]
    assert "/api/v1/tas/studies/sync" not in app.openapi()["paths"]


@pytest.mark.asyncio
async def test_async_tas_submit_and_poll_is_stable_and_reuses_task_cache(tmp_path):
    adapter = ApiPlecsAdapter()
    app, orchestrator = _app(tmp_path, adapter, batch_size=1)
    try:
        accepted = await _post(
            app,
            "/api/v1/tas/studies",
            {"tas": _document()},
        )

        assert accepted.status_code == 202
        accepted_body = accepted.json()
        assert accepted_body["status"] == "queued"
        assert accepted_body["progress"] == {"completed": 0, "total": 2}
        study_id = accepted_body["study_id"]

        terminal = await _wait_terminal(app, study_id)
        terminal_body = terminal.json()
        assert terminal_body["status"] == "completed"
        assert terminal_body["progress"] == {"completed": 2, "total": 2}
        assert [point["name"] for point in terminal_body["points"]] == [
            "nominal",
            "high_line",
        ]
        repeated = await _get(app, f"/api/v1/tas/studies/{study_id}")
        assert repeated.json() == terminal_body

        call_count = len(adapter.calls)
        resubmitted = await _post(
            app,
            "/api/v1/tas/studies",
            {"tas": _document()},
        )
        cached_terminal = await _wait_terminal(app, resubmitted.json()["study_id"])
        assert cached_terminal.json()["status"] == "completed"
        assert len(adapter.calls) == call_count
        assert all(
            point["result"]["cached"] for point in cached_terminal.json()["points"]
        )
    finally:
        await orchestrator.stop()


class SequencedApiPlecsAdapter(ApiPlecsAdapter):
    def __init__(self):
        super().__init__()
        self.second_started = threading.Event()
        self.release_second = threading.Event()

    def simulate_batch(self, parameter_list):
        if self.calls:
            self.second_started.set()
            if not self.release_second.wait(timeout=5):
                raise TimeoutError("second Operating Point was not released")
        return super().simulate_batch(parameter_list)


@pytest.mark.asyncio
async def test_async_tas_progress_comes_from_public_point_outcomes(tmp_path):
    adapter = SequencedApiPlecsAdapter()
    app, orchestrator = _app(tmp_path, adapter, batch_size=1)
    try:
        accepted = await _post(
            app,
            "/api/v1/tas/studies",
            {"tas": _document(), "use_cache": False},
        )
        study_id = accepted.json()["study_id"]
        assert await asyncio.to_thread(adapter.second_started.wait, 1)

        for _ in range(100):
            progress = (await _get(app, f"/api/v1/tas/studies/{study_id}")).json()
            if progress["progress"]["completed"] == 1:
                break
            await asyncio.sleep(0.01)
        assert progress["status"] == "running"
        assert progress["progress"] == {"completed": 1, "total": 2}
        assert [point["status"] for point in progress["points"]] == [
            "completed",
            "pending",
        ]

        adapter.release_second.set()
        terminal = await _wait_terminal(app, study_id)
        assert terminal.json()["status"] == "completed"
    finally:
        adapter.release_second.set()
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_async_tas_preflight_and_unknown_identifier(tmp_path):
    app, orchestrator = _app(tmp_path, ApiPlecsAdapter(available=False))
    try:
        invalid = await _post(
            app,
            "/api/v1/tas/studies",
            {
                "tas": _document(),
                "captures": [
                    {"name": "bad", "kind": "net", "target": "missing", "signal": "voltage"}
                ],
            },
        )
        assert invalid.status_code == 422

        unavailable = await _post(
            app,
            "/api/v1/tas/studies",
            {"tas": _document()},
        )
        assert unavailable.status_code == 503
        assert orchestrator.get_orchestrator_stats()["total_submitted"] == 0

        missing = await _get(app, "/api/v1/tas/studies/not-found")
        assert missing.status_code == 404
    finally:
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_async_tas_partial_failure_is_terminal(tmp_path):
    app, orchestrator = _app(tmp_path, ApiPlecsAdapter(fail_vin=14.0))
    try:
        accepted = await _post(
            app,
            "/api/v1/tas/studies",
            {"tas": _document(), "use_cache": False},
        )
        terminal = await _wait_terminal(app, accepted.json()["study_id"])

        assert terminal.json()["status"] == "partial_failure"
        assert [point["status"] for point in terminal.json()["points"]] == [
            "completed",
            "failed",
        ]
    finally:
        await orchestrator.stop()
