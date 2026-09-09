"""The canonical buck oracle: stable steady-state invariants, never sample-by-sample goldens."""

from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np
import pandas as pd

from pyplecs.core.models import SimulationResult
from pyplecs.quantities import (
    QuantityError,
    SteadyStateWindow,
    capture_waveforms,
    signal_stress,
    time_weighted_rms,
)

from .manifest import Manifest

QUANTITY_FIELDS = ("mean", "rms", "minimum", "maximum", "peak_to_peak")


class OracleError(AssertionError):
    """A precondition failed: the comparison must not be made."""


def payload_to_result(payload: Mapping[str, Any], task_id: str = "payload") -> SimulationResult:
    """Rebuild a Simulation Result from the normalized ``time`` + ``signals`` transport payload."""
    frame = pd.DataFrame({"Time": list(payload["time"]), **{k: list(v) for k, v in payload["signals"].items()}})
    return SimulationResult(task_id=task_id, success=True, timeseries_data=frame)


def check_preconditions(result: SimulationResult, manifest: Manifest) -> SteadyStateWindow:
    """Fail closed, naming the cause, before any quantity is computed."""
    if not result.success or result.timeseries_data is None:
        raise OracleError(f"Simulation Result is a failure: {result.error_message}")
    frame = result.timeseries_data
    missing = [name for name in manifest.required_signals if name not in frame.columns]
    if missing:
        raise OracleError(f"required signals missing from the Simulation Result: {missing}")
    time = frame["Time"].to_numpy(dtype=float)
    if time.size < 2 or not np.all(np.diff(time) > 0):
        raise OracleError("time axis is not strictly increasing")
    for name in manifest.signals:
        if name in frame.columns and not np.isfinite(frame[name].to_numpy(dtype=float)).all():
            raise OracleError(f"signal {name} contains non-finite samples")
    window = SteadyStateWindow(switching_frequency=manifest.switching_frequency, periods=manifest.periods)
    try:
        window.start(time)
    except QuantityError as error:
        raise OracleError(f"steady-state window cannot be cut: {error}") from error
    threshold = float(manifest.tolerances["convergence"])
    for name in manifest.required_signals:
        spread = per_period_rms_spread(time, frame[name].to_numpy(dtype=float), window)
        if spread > threshold:
            raise OracleError(f"{name} has not converged: per-period RMS spread {spread:.3%} > {threshold:.1%}")
    return window


def per_period_rms_spread(time: np.ndarray, values: np.ndarray, window: SteadyStateWindow) -> float:
    """std/mean of the time-weighted RMS of each period in the window (ntbees2 convergence rule)."""
    start = window.start(time)
    period = 1.0 / window.switching_frequency
    rms_values = []
    for k in range(window.periods):
        lo, hi = start + k * period, start + (k + 1) * period
        grid = np.unique(np.concatenate(([lo, hi], time[(time > lo) & (time < hi)])))
        rms_values.append(time_weighted_rms(grid, np.interp(grid, time, values)))
    mean = float(np.mean(rms_values))
    return 0.0 if mean == 0 else float(np.std(rms_values) / mean)


def steady_state_quantities(result: SimulationResult, manifest: Manifest, window: SteadyStateWindow) -> dict[str, dict[str, float]]:
    """The Design Quantities the oracle compares: time-weighted mean/RMS and sampled min/max/peak-to-peak per mapped signal over the window."""
    present = [name for name in manifest.signals if name in result.timeseries_data.columns]
    waveforms = capture_waveforms(result, present, window=window)
    quantities: dict[str, dict[str, float]] = {}
    for name, waveform in waveforms.items():
        stress = signal_stress(name, waveform.time, waveform.values)
        quantities[name] = {field: float(getattr(stress, field)) for field in QUANTITY_FIELDS}
    return quantities


def analytic_invariants(quantities: Mapping[str, Mapping[str, float]], manifest: Manifest) -> list[dict[str, Any]]:
    """Physics a reader can check by hand; a wrong Signal Map fails here."""
    p = manifest.parameters
    derived = manifest.derived()
    duty, ro, ripple = derived["duty_ratio"], derived["load_resistance"], derived["inductor_ripple"]
    v_c, v_r, i_l, i_r = (quantities[n] for n in ("v_C", "v_R", "i_L", "i_R"))
    checks = [
        ("v_C mean within [0.9·D·Vi, D·Vi]", 0.9 * duty * p["Vi"] <= v_c["mean"] <= duty * p["Vi"], v_c["mean"]),
        ("v_C ≈ v_R (same node) within 0.1 %", _rel(v_c["mean"], v_r["mean"]) <= 1e-3, _rel(v_c["mean"], v_r["mean"])),
        ("i_R mean ≈ v_R mean / Ro within 2 %", _rel(i_r["mean"], v_r["mean"] / ro) <= 0.02, i_r["mean"]),
        ("i_L mean ≈ i_R mean within 2 %", _rel(i_l["mean"], i_r["mean"]) <= 0.02, i_l["mean"]),
        ("i_L peak-to-peak within 15 % of analytic ripple", _rel(i_l["peak_to_peak"], ripple) <= 0.15, i_l["peak_to_peak"]),
    ]
    return [{"check": name, "passed": bool(ok), "value": float(value)} for name, ok, value in checks]


def compare_quantities(
    actual: Mapping[str, Mapping[str, float]],
    reference: Mapping[str, Mapping[str, float]],
    manifest: Manifest,
    *,
    relative: Mapping[str, float] | None = None,
    absolute_floor: Mapping[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Symmetric relative error per quantity with per-unit absolute floors; both-below-floor passes.

    ``relative`` and ``absolute_floor`` default to the manifest tolerances; pass ``{}`` as the floor
    to demand the relative agreement everywhere (cross-transport equivalence does).
    """
    tolerances = manifest.tolerances
    relative = relative or tolerances["relative"]
    floors = tolerances["absolute_floor"] if absolute_floor is None else absolute_floor
    rows = []
    for signal, expected in reference.items():
        if signal not in actual:
            rows.append({"signal": signal, "quantity": "*", "error": math.inf, "passed": False, "reason": "signal missing"})
            continue
        floor = float(floors.get(manifest.units.get(signal, ""), 0.0))
        for quantity, expected_value in expected.items():
            value = actual[signal][quantity]
            below_floor = abs(value) < floor and abs(expected_value) < floor
            error = 0.0 if below_floor else _rel(value, expected_value)
            rows.append(
                {
                    "signal": signal,
                    "quantity": quantity,
                    "actual": float(value),
                    "expected": float(expected_value),
                    "error": float(error),
                    "tolerance": float(relative[quantity]),
                    "passed": bool(error <= relative[quantity]),
                }
            )
    return rows


def _rel(a: float, b: float) -> float:
    denominator = max(abs(a), abs(b))
    return 0.0 if denominator == 0 else abs(a - b) / denominator


def summary_table(rows: list[dict[str, Any]]) -> str:
    lines = ["| signal | quantity | actual | expected | error | tol | pass |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["quantity"] == "*":
            lines.append(f"| {r['signal']} | * | — | — | — | — | ✗ {r['reason']} |")
            continue
        lines.append(
            f"| {r['signal']} | {r['quantity']} | {r['actual']:.6g} | {r['expected']:.6g} | "
            f"{r['error']:.3%} | {r['tolerance']:.1%} | {'✓' if r['passed'] else '✗'} |"
        )
    return "\n".join(lines)
