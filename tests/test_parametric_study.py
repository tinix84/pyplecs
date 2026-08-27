from dataclasses import dataclass

import pytest

from pyplecs.config import ConfigManager
from pyplecs.core.models import SimulationStatus
from pyplecs.orchestration import SimulationOrchestrator
from pyplecs.studies import (
    CollectResultsReducer,
    ExplicitParameterVectorStrategy,
    ParameterVector,
    ParametricStudy,
    ParametricStudyStatus,
)


class RecordingPlecsAdapter:
    def __init__(self):
        self.calls = []

    @staticmethod
    def is_available():
        return True

    def simulate_batch(self, parameter_list):
        parameters = [dict(vector) for vector in parameter_list]
        self.calls.append(parameters)
        return [
            {}
            if vector.get("fail")
            else {
                "Time": [0.0, 1.0],
                "Values": [[vector["value"], vector["value"]]],
            }
            for vector in parameters
        ]


def _config(tmp_path, *, batch_size=8):
    config = ConfigManager(search_paths=[])
    config.update("cache.directory", str(tmp_path / "cache"))
    config.update("orchestration.retry_attempts", 1)
    config.update("orchestration.retry_delay", 0)
    config.update("orchestration.max_concurrent_simulations", batch_size)
    return config


def _model(tmp_path):
    model = tmp_path / "model.plecs"
    model.write_text("PLECS model", encoding="utf-8")
    return model


def _vectors(*items):
    return ExplicitParameterVectorStrategy(
        [ParameterVector(name, parameters) for name, parameters in items]
    )


@pytest.mark.asyncio
async def test_invalid_study_fails_before_accepting_simulation_tasks(tmp_path):
    adapter = RecordingPlecsAdapter()
    orchestrator = SimulationOrchestrator(adapter, config=_config(tmp_path))
    study = ParametricStudy(orchestrator)
    try:
        with pytest.raises(ValueError, match="at least one"):
            await study.run(_model(tmp_path), ExplicitParameterVectorStrategy([]))

        with pytest.raises(ValueError, match="unique"):
            await study.run(
                _model(tmp_path),
                _vectors(("same", {"value": 1}), ("same", {"value": 2})),
            )

        assert orchestrator.get_orchestrator_stats()["total_submitted"] == 0
        assert adapter.calls == []
    finally:
        await orchestrator.stop()


@dataclass
class SuccessfulNamesReducer:
    def reduce(self, successful_points):
        return tuple(point.name for point in successful_points)


@pytest.mark.asyncio
async def test_study_preserves_requested_order_and_reduces_successes(tmp_path):
    adapter = RecordingPlecsAdapter()
    orchestrator = SimulationOrchestrator(
        adapter, batch_size=3, config=_config(tmp_path, batch_size=3)
    )
    study = ParametricStudy(orchestrator)
    try:
        outcome = await study.run(
            _model(tmp_path),
            _vectors(
                ("high", {"value": 3}),
                ("low", {"value": 1}),
                ("nominal", {"value": 2}),
            ),
            reducer=SuccessfulNamesReducer(),
            output_variables=["Vo"],
            use_cache=False,
        )

        assert outcome.status == ParametricStudyStatus.COMPLETED
        assert [point.name for point in outcome.points] == ["high", "low", "nominal"]
        assert all(point.status == SimulationStatus.COMPLETED for point in outcome.points)
        assert outcome.aggregate == ("high", "low", "nominal")
        assert orchestrator.get_orchestrator_stats()["total_submitted"] == 3
    finally:
        await orchestrator.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("vectors", "expected_status", "successful_names"),
    [
        (
            (("good", {"value": 1}), ("bad", {"value": 2, "fail": True})),
            ParametricStudyStatus.PARTIAL_FAILURE,
            ("good",),
        ),
        (
            (("bad-1", {"value": 1, "fail": True}), ("bad-2", {"value": 2, "fail": True})),
            ParametricStudyStatus.FAILED,
            (),
        ),
    ],
)
async def test_study_keeps_failed_points_explicit(
    tmp_path, vectors, expected_status, successful_names
):
    adapter = RecordingPlecsAdapter()
    orchestrator = SimulationOrchestrator(adapter, config=_config(tmp_path))
    study = ParametricStudy(orchestrator)
    try:
        outcome = await study.run(
            _model(tmp_path),
            _vectors(*vectors),
            reducer=SuccessfulNamesReducer(),
            use_cache=False,
        )

        assert outcome.status == expected_status
        assert [point.name for point in outcome.points] == [name for name, _ in vectors]
        assert outcome.aggregate == successful_names
        failed = [point for point in outcome.points if point.status == SimulationStatus.FAILED]
        assert all(point.error for point in failed)
    finally:
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_study_reuses_only_constituent_task_cache_records(tmp_path):
    adapter = RecordingPlecsAdapter()
    orchestrator = SimulationOrchestrator(adapter, config=_config(tmp_path))
    study = ParametricStudy(orchestrator)
    original = _vectors(("one", {"value": 1}), ("two", {"value": 2}))
    changed = _vectors(("one", {"value": 1}), ("two", {"value": 20}))
    try:
        first = await study.run(_model(tmp_path), original, reducer=CollectResultsReducer())
        second = await study.run(_model(tmp_path), original, reducer=CollectResultsReducer())
        third = await study.run(_model(tmp_path), changed, reducer=CollectResultsReducer())

        invoked = [vector["value"] for batch in adapter.calls for vector in batch]
        assert invoked == [1, 2, 20]
        assert [point.result.cached for point in first.points] == [False, False]
        assert [point.result.cached for point in second.points] == [True, True]
        assert [point.result.cached for point in third.points] == [True, False]
        assert len(first.aggregate) == len(second.aggregate) == len(third.aggregate) == 2
    finally:
        await orchestrator.stop()
