import pytest

from pyplecs.config import ConfigManager
from pyplecs.core.models import SimulationRequest
from pyplecs.mcp.simulation_server import build_orchestrator
from pyplecs.orchestration import PlecsUnavailableError, SimulationOrchestrator
from pyplecs.orchestration.live import LivePlecsAdapter


class FakePlecsServer:
    """Records one PLECS model session and answers with the parameters it was given."""

    sessions: list[dict] = []

    def __init__(self, model_file, port, auto_launch):
        self.record = {"model_file": model_file, "port": port, "auto_launch": auto_launch, "closed": False}
        FakePlecsServer.sessions.append(self.record)

    def simulate_batch(self, parameter_list):
        return [{"Time": [0.0, 1.0], "Values": [[vector["Vi"], vector["Vi"]]]} for vector in parameter_list]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.record["closed"] = True
        return False


def _config(tmp_path):
    config = ConfigManager(search_paths=[])
    config.update("cache.directory", str(tmp_path / "cache"))
    config.update("plecs.version", "test")
    config.update("plecs.xmlrpc.port", 1081)
    config.update("plecs.auto_launch", False)
    config.update("orchestration.retry_attempts", 1)
    config.update("orchestration.retry_delay", 0)
    return config


def test_requests_are_grouped_by_model_file_and_answered_in_request_order(tmp_path):
    FakePlecsServer.sessions = []
    adapter = LivePlecsAdapter(_config(tmp_path), server_factory=FakePlecsServer, probe=lambda *_: True)
    buck, boost = str(tmp_path / "buck.plecs"), str(tmp_path / "boost.plecs")
    (tmp_path / "buck.plecs").touch()
    (tmp_path / "boost.plecs").touch()
    requests = [
        SimulationRequest(model_file=buck, parameters={"Vi": 1.0}),
        SimulationRequest(model_file=boost, parameters={"Vi": 2.0}),
        SimulationRequest(model_file=buck, parameters={"Vi": 3.0}),
    ]

    results = adapter.simulate_requests(requests)

    assert [raw["Values"][0][0] for raw in results] == [1.0, 2.0, 3.0]
    assert [session["model_file"] for session in FakePlecsServer.sessions] == [buck, boost]
    assert all(session["closed"] and session["port"] == "1081" and session["auto_launch"] is False
               for session in FakePlecsServer.sessions)
    with pytest.raises(RuntimeError, match="whole Simulation Requests"):
        adapter.simulate_batch([{"Vi": 1.0}])


def test_availability_is_the_configured_endpoint_probe(tmp_path):
    probed = []

    def probe(host, port, timeout):
        probed.append((host, port, timeout))
        return False

    adapter = LivePlecsAdapter(_config(tmp_path), server_factory=FakePlecsServer, probe=probe)

    assert adapter.is_available() is False
    assert probed == [("localhost", 1081, 30.0)]


@pytest.mark.asyncio
async def test_orchestrator_uses_the_live_seam_and_rejects_submission_when_unreachable(tmp_path):
    FakePlecsServer.sessions = []
    config = _config(tmp_path)
    model = tmp_path / "buck.plecs"
    model.touch()
    reachable = LivePlecsAdapter(config, server_factory=FakePlecsServer, probe=lambda *_: True)
    orchestrator = SimulationOrchestrator(reachable, config=config)
    try:
        task_id = await orchestrator.submit_simulation(
            SimulationRequest(model_file=str(model), parameters={"Vi": 7.0}, output_variables=["Vo"])
        )
        snapshot = await orchestrator.wait_for_completion(task_id, timeout=5)
        assert snapshot.status.value == "completed"
        assert snapshot.result.timeseries_data["Vo"].tolist() == [7.0, 7.0]
        assert FakePlecsServer.sessions[0]["model_file"] == str(model)
    finally:
        await orchestrator.stop()

    unreachable = SimulationOrchestrator(
        LivePlecsAdapter(config, server_factory=FakePlecsServer, probe=lambda *_: False), config=config
    )
    with pytest.raises(PlecsUnavailableError, match="PLECS"):
        await unreachable.submit_simulation(SimulationRequest(model_file=str(model)))


def test_console_orchestrator_is_wired_to_the_live_adapter_without_opening_plecs(tmp_path):
    orchestrator = build_orchestrator(_config(tmp_path))
    assert isinstance(orchestrator._plecs, LivePlecsAdapter)
    assert orchestrator.is_running is False
