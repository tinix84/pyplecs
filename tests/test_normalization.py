import numpy as np
import pandas as pd
import pytest

from pyplecs.api import simulation_sync
from pyplecs.normalization import normalize_plecs_result


def test_normalizes_time_values_with_explicit_signal_names_and_metadata():
    raw = {
        "Time": np.array([0.0, 0.5, 1.0]),
        "Values": [[0, 6, 12], np.array([1, 2, 3])],
    }

    result = normalize_plecs_result(
        raw,
        task_id="task-1",
        signal_names={0: "Vo", 1: "IL"},
        metadata={"model_file": "buck.plecs"},
    )

    assert result.success is True
    pd.testing.assert_frame_equal(
        result.timeseries_data,
        pd.DataFrame(
            {
                "Time": [0.0, 0.5, 1.0],
                "Vo": [0.0, 6.0, 12.0],
                "IL": [1.0, 2.0, 3.0],
            }
        ),
    )
    assert result.metadata == {
        "model_file": "buck.plecs",
        "n_points": 3,
        "n_signals": 2,
    }


def test_time_values_falls_back_to_stable_column_names():
    result = normalize_plecs_result(
        {"Time": [0, 1], "Values": [[2, 3], [4, 5]]}, task_id="task-1"
    )

    assert result.success is True
    assert list(result.timeseries_data.columns) == ["Time", "col_0", "col_1"]


def test_normalizes_column_oriented_mapping():
    result = normalize_plecs_result(
        {"seconds": [0, 1], "power": [10, 12]}, task_id="task-1"
    )

    assert result.success is True
    pd.testing.assert_frame_equal(
        result.timeseries_data,
        pd.DataFrame({"seconds": [0.0, 1.0], "power": [10.0, 12.0]}),
    )
    assert result.metadata == {"n_points": 2, "n_signals": 2}


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ({"Time": [0, 1]}, "both 'Time' and 'Values'"),
        ({"Time": [0, 1], "Values": [[1]]}, "expected 2"),
        ({"a": [1], "b": [1, 2]}, "equal lengths"),
        ({"a": ["not-a-number"]}, "non-numeric"),
        ([], "expected a mapping"),
        ({}, "mapping is empty"),
    ],
)
def test_malformed_or_unknown_shapes_are_explicit_failures(raw, message):
    result = normalize_plecs_result(raw, task_id="task-1")

    assert result.success is False
    assert result.timeseries_data is None
    assert message in result.error_message


def _http_request():
    """A request whose app carries no resolved config: the route falls back to PlecsServer defaults."""
    from types import SimpleNamespace

    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))


@pytest.mark.asyncio
async def test_synchronous_adapter_uses_shared_normalization(monkeypatch):
    class FakePlecsServer:
        def __init__(self, model_file):
            self.model_file = model_file

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def simulate(self, parameters):
            assert parameters == {"Vi": 24.0}
            return {"Time": [0, 1], "Values": [[5, 12]]}

    monkeypatch.setattr(simulation_sync, "PlecsServer", FakePlecsServer)
    request = simulation_sync.SyncSimulationRequest(
        model_file="buck.plecs",
        parameters={"Vi": 24.0},
        signal_map={0: "Vo"},
    )

    response = await simulation_sync.run_simulation_sync(request, _http_request())

    assert response.success is True
    assert response.time == [0.0, 1.0]
    assert response.signals == {"Vo": [5.0, 12.0]}
    assert response.metadata["n_points"] == 2
    assert response.metadata["n_signals"] == 1


@pytest.mark.asyncio
async def test_synchronous_adapter_returns_failed_simulation_result(monkeypatch):
    class FakePlecsServer:
        def __init__(self, model_file):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def simulate(self, parameters):
            return {"Time": [0, 1], "Values": [[5]]}

    monkeypatch.setattr(simulation_sync, "PlecsServer", FakePlecsServer)

    response = await simulation_sync.run_simulation_sync(
        simulation_sync.SyncSimulationRequest(model_file="buck.plecs"),
        _http_request(),
    )

    assert response.success is False
    assert response.time == []
    assert response.signals == {}
    assert "normalization failed" in response.error_message
