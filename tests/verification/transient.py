"""Transient (step-response) comparison: two simulators, one waveform, a common time grid.

A step response is not periodic, so the steady-state window oracle does not apply.
Both series are interpolated onto one grid and compared point-wise; the analytic
first-order response is a third, independent witness.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np

from .oracle import OracleError


def resample(payload: Mapping[str, Any], name: str, grid: np.ndarray) -> np.ndarray:
    time = np.asarray(payload["time"], dtype=float)
    values = np.asarray(payload["signals"][name], dtype=float)
    if time.size < 2 or not np.all(np.diff(time) >= 0):
        raise OracleError(f"{name}: time axis is not monotonic")
    if not np.isfinite(values).all():
        raise OracleError(f"{name}: non-finite samples")
    return np.interp(grid, time, values)


def compare_step_response(
    reference: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    signal: str,
    step: float,
    tau: float,
    span: float,
    tolerance: float = 0.01,
    points: int = 2001,
) -> dict[str, Any]:
    """Point-wise agreement of two step responses, normalised to the step amplitude.

    ``reference`` and ``candidate`` are ``time`` + ``signals`` payloads. Pass/fail is the maximum
    absolute difference over the grid divided by ``step`` against ``tolerance``; both series are also
    checked against the analytic ``step·(1 − e^(−t/τ))`` at τ, 3τ and the end of the span.
    """
    if not (span > 0 and tau > 0 and step != 0):
        raise OracleError("compare_step_response needs a positive span and tau and a non-zero step")
    grid = np.linspace(0.0, span, points)
    a = resample(reference, signal, grid)
    b = resample(candidate, signal, grid)
    analytic = step * (1.0 - np.exp(-grid / tau))
    difference = np.abs(a - b)
    worst = int(np.argmax(difference))
    checkpoints = {}
    for label, t in (("tau", tau), ("3tau", 3 * tau), ("end", span)):
        if t > span:
            continue
        expected = step * (1.0 - math.exp(-t / tau))
        checkpoints[label] = {
            "t": t,
            "analytic": expected,
            "reference": float(np.interp(t, grid, a)),
            "candidate": float(np.interp(t, grid, b)),
            "reference_error": abs(float(np.interp(t, grid, a)) - expected) / abs(step),
            "candidate_error": abs(float(np.interp(t, grid, b)) - expected) / abs(step),
        }
    max_error = float(difference[worst] / abs(step))
    analytic_error = {
        "reference": float(np.max(np.abs(a - analytic)) / abs(step)),
        "candidate": float(np.max(np.abs(b - analytic)) / abs(step)),
    }
    return {
        "signal": signal,
        "grid": {"points": points, "span": span},
        "max_relative_difference": max_error,
        "at_time": float(grid[worst]),
        "tolerance": tolerance,
        "passed": bool(max_error <= tolerance),
        "checkpoints": checkpoints,
        "max_relative_error_vs_analytic": analytic_error,
        "analytic_passed": bool(max(analytic_error.values()) <= tolerance),
    }


def overlay_svg(reference: Mapping[str, Any], candidate: Mapping[str, Any], *, signal: str, span: float, unit: str = "") -> str:
    """Dependency-free full-span overlay: reference solid, candidate dashed."""
    width, height, pad = 720, 240, 36
    series = []
    lo = hi = None
    for payload in (reference, candidate):
        t = np.asarray(payload["time"], dtype=float)
        y = np.asarray(payload["signals"][signal], dtype=float)
        mask = t <= span
        t, y = t[mask], y[mask]
        lo = y.min() if lo is None else min(lo, y.min())
        hi = y.max() if hi is None else max(hi, y.max())
        series.append((t, y))
    scale = (hi - lo) or 1.0
    parts = []
    for (t, y), style in zip(series, ('stroke="#1f77b4"', 'stroke="#d62728" stroke-dasharray="6 4"')):
        pts = " ".join(f"{pad + ti / span * (width - 2 * pad):.1f},{height - pad - (yi - lo) / scale * (height - 2 * pad):.1f}" for ti, yi in zip(t, y))
        parts.append(f'<polyline fill="none" {style} stroke-width="1.5" points="{pts}"/>')
    parts.append(f'<text x="{pad}" y="18" font-family="sans-serif" font-size="12">{signal}: {lo:.4g} … {hi:.4g} {unit}, 0 … {span:g} s, reference solid / candidate dashed</text>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        '<rect width="100%" height="100%" fill="white"/>' + "".join(parts) + "</svg>"
    )
