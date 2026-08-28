import copy
import json
from pathlib import Path

import pytest

from pyplecs.config import ConfigManager
from pyplecs.core.models import SimulationStatus
from pyplecs.orchestration import PlecsUnavailableError, SimulationOrchestrator
from pyplecs.studies import ParametricStudyStatus
from pyplecs.tas import TasCapture, TasCompilationError, TasExecutionService

FIXTURE = Path(__file__).parent / "fixtures" / "tas_buck_inline.json"


def _document():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _config(tmp_path):
    config = ConfigManager(search_paths=[])
    config.update("cache.directory", str(tmp_path / "cache"))
    config.update("plecs.version", "test")
    config.update("orchestration.retry_attempts", 1)
    config.update("orchestration.retry_delay", 0)
    config.update("orchestration.max_concurrent_simulations", 8)
    return config


class TasPlecsAdapter:
    def __init__(self, signal_count=4, *, fail_vin=None, available=True):
        self.signal_count = signal_count
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
                    for signal in range(self.signal_count)
                ],
            }
            for vector in parameters
        ]


@pytest.mark.asyncio
async def test_execute_tas_end_to_end_with_stable_capture_names(tmp_path):
    source = _document()
    original = copy.deepcopy(source)
    adapter = TasPlecsAdapter(signal_count=6)
    orchestrator = SimulationOrchestrator(adapter, config=_config(tmp_path))
    service = TasExecutionService(orchestrator, artifact_directory=tmp_path / "models")
    captures = [
        TasCapture("switch_voltage", "net", "power_stage.sw_node", "voltage"),
        TasCapture("inductor_current", "component", "power_stage.L1", "current"),
    ]
    try:
        envelope = await service.execute(source, captures=captures, use_cache=False)

        assert source == original
        assert envelope.source == original
        assert envelope.status == ParametricStudyStatus.COMPLETED
        assert [point.name for point in envelope.points] == ["nominal", "high_line"]
        assert all(point.status == SimulationStatus.COMPLETED for point in envelope.points)
        assert len(envelope.aggregate) == 2
        assert adapter.calls[0] == [
            {
                "D": 0.42,
                "R_load": 2.5,
                "T_sim": 0.0005,
                "Vin": 12.0,
                "fs": 500000.0,
                "max_step": 2e-08,
            },
            {
                "D": 0.42,
                "R_load": 5.0,
                "T_sim": 0.0005,
                "Vin": 14.0,
                "fs": 500000.0,
                "max_step": 2e-08,
            },
        ]
        expected_columns = [
            "Time",
            "Vin.voltage",
            "Vin.current",
            "Vout.voltage",
            "Vout.current",
            "switch_voltage",
            "inductor_current",
        ]
        assert list(envelope.points[0].result.timeseries_data.columns) == expected_columns
        ambient = [
            diagnostic
            for diagnostic in envelope.diagnostics
            if diagnostic.code == "TAS_AMBIENT_TEMPERATURE_PRESERVED"
        ]
        assert len(ambient) == 2
    finally:
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_partial_failure_stays_correlated_to_operating_point(tmp_path):
    adapter = TasPlecsAdapter(fail_vin=14.0)
    orchestrator = SimulationOrchestrator(adapter, config=_config(tmp_path))
    service = TasExecutionService(orchestrator, artifact_directory=tmp_path / "models")
    try:
        envelope = await service.execute(_document(), use_cache=False)

        assert envelope.status == ParametricStudyStatus.PARTIAL_FAILURE
        assert [(point.name, point.status) for point in envelope.points] == [
            ("nominal", SimulationStatus.COMPLETED),
            ("high_line", SimulationStatus.FAILED),
        ]
        assert envelope.points[1].error
        assert len(envelope.aggregate) == 1
    finally:
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_preflight_errors_accept_no_simulation_tasks(tmp_path):
    unavailable = SimulationOrchestrator(
        TasPlecsAdapter(available=False), config=_config(tmp_path)
    )
    service = TasExecutionService(unavailable, artifact_directory=tmp_path / "models")

    with pytest.raises(TasCompilationError):
        await service.execute(
            _document(), captures=[TasCapture("bad", "net", "missing", "voltage")]
        )
    assert unavailable.get_orchestrator_stats()["total_submitted"] == 0

    with pytest.raises(PlecsUnavailableError):
        await service.execute(_document())
    assert unavailable.get_orchestrator_stats()["total_submitted"] == 0


@pytest.mark.asyncio
async def test_changing_first_operating_point_only_misses_that_cache_entry(tmp_path):
    adapter = TasPlecsAdapter()
    orchestrator = SimulationOrchestrator(adapter, config=_config(tmp_path))
    service = TasExecutionService(orchestrator, artifact_directory=tmp_path / "models")
    changed = _document()
    changed["inputs"]["operatingPoints"][0]["inputVoltage"] = 11.0
    try:
        first = await service.execute(_document())
        second = await service.execute(changed)

        assert first.artifact_path == second.artifact_path
        assert adapter.calls == [
            [
                first.points[0].parameters,
                first.points[1].parameters,
            ],
            [second.points[0].parameters],
        ]
        assert second.points[1].result.cached is True
    finally:
        await orchestrator.stop()


def test_synchronous_service_waits_on_the_same_operation(tmp_path):
    adapter = TasPlecsAdapter()
    orchestrator = SimulationOrchestrator(adapter, config=_config(tmp_path))
    service = TasExecutionService(orchestrator, artifact_directory=tmp_path / "models")

    envelope = service.execute_sync(_document(), timeout=2, use_cache=False)

    assert envelope.status == ParametricStudyStatus.COMPLETED
    assert [point.name for point in envelope.points] == ["nominal", "high_line"]
    assert orchestrator.is_running is False
