import asyncio
import threading
from pathlib import Path

import pytest
import tomllib

from pyplecs.config import ConfigManager
from pyplecs.mcp.plecs_tools import TOOL_CATALOGUE, ToolCatalogue, ToolDefinition
from pyplecs.mcp.simulation_server import SERVER_NAME, build_simulation_server
from pyplecs.mcp.simulation_tools import build_simulation_catalogue
from pyplecs.orchestration import SimulationOrchestrator

REPO_ROOT = Path(__file__).resolve().parent.parent

DOCS_TOOL_NAMES = (
    "plecs_lookup",
    "plecs_search",
    "plecs_xml",
    "plecs_url",
    "plecs_component",
    "plecs_rpc",
    "pyplecs_wrappers",
    "pyplecs_rpc_surface",
)


class InMemoryPlecsAdapter:
    def __init__(self, *, available=True, raw=None):
        self.available = available
        self.raw = raw
        self.calls = []

    def is_available(self):
        return self.available

    def simulate_batch(self, parameter_list):
        parameters = [dict(vector) for vector in parameter_list]
        self.calls.append(parameters)
        if self.raw is not None:
            return [self.raw for _ in parameters]
        return [
            {"Time": [0.0, 1.0], "Values": [[vector["Vi"], vector["Vi"]], [1.0, 2.0]]}
            for vector in parameters
        ]


class BlockingPlecsAdapter(InMemoryPlecsAdapter):
    def __init__(self):
        super().__init__()
        self.started = threading.Event()
        self.release = threading.Event()

    def simulate_batch(self, parameter_list):
        self.started.set()
        if not self.release.wait(timeout=5):
            raise TimeoutError("test adapter was not released")
        return super().simulate_batch(parameter_list)


def _config(tmp_path, *, retries=1):
    config = ConfigManager(search_paths=[])
    config.update("cache.directory", str(tmp_path / "cache"))
    config.update("plecs.version", "test")
    config.update("orchestration.retry_attempts", retries)
    config.update("orchestration.retry_delay", 0)
    return config


def _catalogue(tmp_path, adapter, **config_kwargs):
    orchestrator = SimulationOrchestrator(adapter, config=_config(tmp_path, **config_kwargs))
    return build_simulation_catalogue(orchestrator), orchestrator


def _model(tmp_path):
    model = tmp_path / "buck.plecs"
    model.write_text('Plecs {\n  Name "buck"\n  InitializationCommands "Vi = 24;"\n}\n', encoding="utf-8")
    return str(model)


async def _call(catalogue, name, **arguments):
    outcome = await catalogue.dispatch_async(name, arguments)
    assert outcome.success, outcome.error
    return outcome.value


async def _error(catalogue, name, **arguments):
    outcome = await catalogue.dispatch_async(name, arguments)
    assert not outcome.success
    return outcome.error


@pytest.mark.asyncio
async def test_submit_wait_result_round_trip_and_cache_hit(tmp_path):
    adapter = InMemoryPlecsAdapter()
    catalogue, orchestrator = _catalogue(tmp_path, adapter)
    model = _model(tmp_path)
    try:
        submitted = await _call(
            catalogue,
            "simulation_submit",
            model_file=model,
            parameters={"Vi": 24.0},
            output_variables=["Vo", "IL"],
            priority="HIGH",
        )
        assert submitted["status"] in {"queued", "running", "completed"}

        waited = await _call(catalogue, "simulation_wait", task_id=submitted["task_id"], timeout_s=5)
        assert waited["terminal"] is True and waited["status"] == "completed"
        assert waited["model_file"] == model and waited["priority"] == "HIGH"

        result = await _call(catalogue, "simulation_result", task_id=submitted["task_id"])
        assert result["success"] is True and result["cached"] is False
        assert result["time"] == [0.0, 1.0]
        assert result["signals"] == {"Vo": [24.0, 24.0], "IL": [1.0, 2.0]}
        assert result["metadata"]["model_file"] == model

        again = await _call(catalogue, "simulation_submit", model_file=model, parameters={"Vi": 24.0})
        snapshot = await _call(catalogue, "simulation_wait", task_id=again["task_id"], timeout_s=5)
        cached = await _call(catalogue, "simulation_result", task_id=again["task_id"])
        assert snapshot["status"] == "completed" and cached["cached"] is True
        assert len(adapter.calls) == 1

        listed = await _call(catalogue, "simulation_list", status="completed")
        assert listed["total"] == 2 and {task["task_id"] for task in listed["tasks"]} == {
            submitted["task_id"],
            again["task_id"],
        }
    finally:
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_failed_simulation_is_a_result_not_a_tool_error(tmp_path):
    catalogue, orchestrator = _catalogue(tmp_path, InMemoryPlecsAdapter(raw={}), retries=1)
    try:
        submitted = await _call(catalogue, "simulation_submit", model_file=_model(tmp_path))
        waited = await _call(catalogue, "simulation_wait", task_id=submitted["task_id"], timeout_s=5)
        result = await _call(catalogue, "simulation_result", task_id=submitted["task_id"])

        assert waited["status"] == "failed" and waited["terminal"] is True
        assert result["success"] is False and "normalization failed" in result["error_message"]
        assert result["time"] == [] and result["signals"] == {}
    finally:
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_unavailable_plecs_rejects_submission_while_other_tools_answer(tmp_path):
    catalogue, orchestrator = _catalogue(tmp_path, InMemoryPlecsAdapter(available=False))
    try:
        error = await _error(catalogue, "simulation_submit", model_file=_model(tmp_path))
        assert "PLECS" in error
        assert (await _call(catalogue, "simulation_list"))["total"] == 0
        assert "unknown Simulation Task" in await _error(catalogue, "simulation_status", task_id="nope")
    finally:
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_non_terminal_result_is_an_error_and_cancel_is_terminal(tmp_path):
    adapter = BlockingPlecsAdapter()
    catalogue, orchestrator = _catalogue(tmp_path, adapter)
    try:
        submitted = await _call(catalogue, "simulation_submit", model_file=_model(tmp_path))
        await asyncio.to_thread(adapter.started.wait, 5)

        waited = await _call(catalogue, "simulation_wait", task_id=submitted["task_id"], timeout_s=0.05)
        assert waited["terminal"] is False and waited["status"] == "running"
        assert "running" in await _error(catalogue, "simulation_result", task_id=submitted["task_id"])

        cancelled = await _call(catalogue, "simulation_cancel", task_id=submitted["task_id"])
        assert cancelled == {"task_id": submitted["task_id"], "cancelled": True}
        result = await _call(catalogue, "simulation_result", task_id=submitted["task_id"])
        assert result["success"] is False and "cancelled" in result["error_message"]
        assert (await _call(catalogue, "simulation_cancel", task_id=submitted["task_id"]))["cancelled"] is False
    finally:
        adapter.release.set()
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_arguments_are_validated_locally_before_any_submission(tmp_path):
    adapter = InMemoryPlecsAdapter()
    catalogue, orchestrator = _catalogue(tmp_path, adapter)
    model = _model(tmp_path)
    try:
        assert "priority" in await _error(catalogue, "simulation_submit", model_file=model, priority="URGENT")
        assert "parameters" in await _error(catalogue, "simulation_submit", model_file=model, parameters=[1])
        assert "timeout_s" in await _error(catalogue, "simulation_wait", task_id="x", timeout_s=0)
        assert "status" in await _error(catalogue, "simulation_list", status="done")
        assert "does not exist" in await _error(catalogue, "simulation_submit", model_file=str(tmp_path / "no.plecs"))
        assert adapter.calls == [] and (await _call(catalogue, "simulation_list"))["total"] == 0
    finally:
        await orchestrator.stop()


def test_simulation_and_documentation_catalogues_are_disjoint_and_docs_are_frozen(tmp_path):
    catalogue, _ = _catalogue(tmp_path, InMemoryPlecsAdapter())

    assert TOOL_CATALOGUE.names == DOCS_TOOL_NAMES
    assert not set(catalogue.names) & set(TOOL_CATALOGUE.names)
    assert set(catalogue.names) >= {
        "simulation_submit",
        "simulation_status",
        "simulation_wait",
        "simulation_result",
        "simulation_cancel",
        "simulation_list",
    }
    for definition in catalogue.definitions:
        assert definition.description and definition.input_schema["additionalProperties"] is False


def test_sync_dispatch_refuses_coroutine_handlers_and_async_dispatch_awaits_them():
    async def handler():
        return {"ok": True}

    catalogue = ToolCatalogue(
        [ToolDefinition("async_tool", "test", {"type": "object", "properties": {}, "required": []}, handler)]
    )

    refused = catalogue.dispatch("async_tool", {})
    assert not refused.success and "async" in refused.error
    assert asyncio.run(catalogue.dispatch_async("async_tool", {})).value == {"ok": True}


def test_simulation_server_and_console_command_are_registered(tmp_path):
    _, orchestrator = _catalogue(tmp_path, InMemoryPlecsAdapter())
    server = build_simulation_server(orchestrator)
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert server.name == SERVER_NAME == "pyplecs-mcp-sim"
    assert server.get_request_handler("tools/list") is not None
    assert server.get_request_handler("tools/call") is not None
    assert project["project"]["scripts"]["pyplecs-mcp-sim"] == "pyplecs.mcp.simulation_server:main"
