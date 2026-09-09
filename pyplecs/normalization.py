"""Normalize model-dependent Raw PLECS Results into Simulation Results."""

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from .core.models import SimulationResult

TIME_COLUMN = "Time"


def normalize_plecs_result(
    raw_result: Any,
    *,
    task_id: str,
    signal_names: Mapping[int, str] | Sequence[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    execution_time: float = 0.0,
    cached: bool = False,
    plecs_version: str | None = None,
) -> SimulationResult:
    """Validate a supported Raw PLECS Result shape.

    Supported mappings are either PLECS ``Time``/``Values`` output, where
    ``Values`` is signal-major, or a column-oriented mapping of equal-length
    numeric vectors. Any other shape becomes an explicit failed result.
    """
    result_metadata = dict(metadata or {})
    try:
        timeseries_data = _normalize_mapping(raw_result, signal_names)
        n_points = len(timeseries_data.index)
        n_signals = len([column for column in timeseries_data.columns if column != "Time"])
        result_metadata.update(
            {
                "n_points": n_points,
                "n_signals": n_signals,
            }
        )
        return SimulationResult(
            task_id=task_id,
            success=True,
            timeseries_data=timeseries_data,
            metadata=result_metadata,
            execution_time=execution_time,
            cached=cached,
            plecs_version=plecs_version,
        )
    except (TypeError, ValueError) as error:
        return SimulationResult(
            task_id=task_id,
            success=False,
            metadata=result_metadata,
            error_message=f"Raw PLECS Result normalization failed: {error}",
            execution_time=execution_time,
            cached=cached,
            plecs_version=plecs_version,
        )


def simulation_result_payload(result: SimulationResult) -> dict[str, Any]:
    """The transport shape of a normalized Simulation Result: ``time`` plus named ``signals``.

    REST routes and the Simulation MCP Server all call this, so signal naming
    has exactly one locality (#46).
    """
    frame = result.timeseries_data
    if frame is None:
        return {"time": [], "signals": {}}
    return {
        "time": frame[TIME_COLUMN].tolist() if TIME_COLUMN in frame.columns else [],
        "signals": {column: frame[column].tolist() for column in frame.columns if column != TIME_COLUMN},
    }


def _normalize_mapping(
    raw_result: Any,
    signal_names: Mapping[int, str] | Sequence[str] | None,
) -> pd.DataFrame:
    if not isinstance(raw_result, Mapping):
        raise TypeError(f"expected a mapping, got {type(raw_result).__name__}")
    if not raw_result:
        raise ValueError("mapping is empty")

    has_time = "Time" in raw_result
    has_values = "Values" in raw_result
    if has_time or has_values:
        if not has_time or not has_values:
            raise ValueError("PLECS output must contain both 'Time' and 'Values'")
        return _normalize_time_values(raw_result, signal_names)

    columns: dict[str, list[float]] = {}
    expected_length: int | None = None
    for name, values in raw_result.items():
        if not isinstance(name, str) or not name:
            raise ValueError("column names must be non-empty strings")
        vector = _numeric_vector(values, f"column '{name}'")
        if expected_length is None:
            expected_length = len(vector)
        elif len(vector) != expected_length:
            raise ValueError("column-oriented vectors must have equal lengths")
        columns[name] = vector

    return pd.DataFrame(columns)


def _normalize_time_values(
    raw_result: Mapping[str, Any],
    signal_names: Mapping[int, str] | Sequence[str] | None,
) -> pd.DataFrame:
    time_vector = _numeric_vector(raw_result["Time"], "'Time'")
    raw_values = raw_result["Values"]
    if isinstance(raw_values, (str, bytes, Mapping)) or not isinstance(raw_values, Sequence):
        if hasattr(raw_values, "tolist"):
            raw_values = raw_values.tolist()
        else:
            raise TypeError("'Values' must be a sequence of signal vectors")

    columns: dict[str, list[float]] = {"Time": time_vector}
    for index, values in enumerate(raw_values):
        vector = _numeric_vector(values, f"signal {index}")
        if len(vector) != len(time_vector):
            raise ValueError(f"signal {index} has {len(vector)} points; expected {len(time_vector)}")
        name = _signal_name(index, signal_names)
        if name in columns:
            raise ValueError(f"duplicate signal name: {name}")
        columns[name] = vector

    return pd.DataFrame(columns)


def _signal_name(index: int, signal_names: Mapping[int, str] | Sequence[str] | None) -> str:
    name: Any = None
    if isinstance(signal_names, Mapping):
        name = signal_names.get(index)
    elif signal_names is not None and index < len(signal_names):
        name = signal_names[index]

    if name is None:
        return f"col_{index}"
    if not isinstance(name, str) or not name:
        raise ValueError(f"signal {index} name must be a non-empty string")
    return name


def _numeric_vector(value: Any, label: str) -> list[float]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        raise TypeError(f"{label} must be a numeric vector")

    vector = list(value)
    if any(isinstance(item, (Sequence, Mapping)) and not isinstance(item, (str, bytes)) for item in vector):
        raise ValueError(f"{label} must be one-dimensional")
    try:
        return [float(item) for item in vector]
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} contains non-numeric data") from error
