"""Semi-manual converter acceptance: read a SPICE export, compare it to PLECS, retain evidence (#61)."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .manifest import Manifest
from .oracle import OracleError, check_preconditions, compare_metrics, payload_to_result, steady_state_metrics


class MissingEvidenceError(AssertionError):
    """The pack never skips: it names the file it expected and how to produce it."""


@dataclass(frozen=True)
class RawTrace:
    header: Mapping[str, str]
    time: np.ndarray
    variables: Mapping[str, np.ndarray]


def read_ltspice_ascii_raw(path: Path) -> RawTrace:
    """Parse an LTspice ``-ascii`` ``.raw`` transient export (real, forward)."""
    if not path.is_file():
        raise MissingEvidenceError(f"LTspice export not found: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    if "\x00" in text:  # LTspice writes UTF-16 when not asked for ASCII
        text = path.read_text(encoding="utf-16", errors="replace")
    head, _, body = text.partition("Values:")
    if not body:
        raise MissingEvidenceError(f"{path} holds no 'Values:' block — was LTspice run with -ascii, and did it finish?")
    header: dict[str, str] = {}
    names: list[str] = []
    in_variables = False
    for line in head.splitlines():
        if line.startswith("Variables:"):
            in_variables = True
            continue
        if in_variables:
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                names.append(parts[1].lower())
            continue
        key, _, value = line.partition(":")
        header[key.strip()] = value.strip()
    n_points = int(header.get("No. Points", "0") or 0)
    if n_points == 0:
        raise MissingEvidenceError(f"{path} recorded 0 points: LTspice did not run the deck (see its .log)")
    numbers = np.array([float(token) for token in body.split()], dtype=float)
    columns = len(names)
    if numbers.size != n_points * (columns + 1):
        raise MissingEvidenceError(f"{path} is truncated: expected {n_points} points × {columns} variables")
    table = numbers.reshape(n_points, columns + 1)[:, 1:]  # drop the point index
    variables = {name: table[:, index] for index, name in enumerate(names)}
    return RawTrace(header=header, time=variables.pop("time"), variables=variables)


_TERM = re.compile(r"\s*([+-]?)\s*([A-Za-z_]+\([^)]*\)|[A-Za-z_][\w:]*)")


def evaluate_expressions(trace: RawTrace, expressions: Mapping[str, str]) -> dict[str, np.ndarray]:
    """Map simulator variables to canonical names through explicit signed sums, e.g. ``V(n002)-V(n001)``."""
    signals: dict[str, np.ndarray] = {}
    for name, expression in expressions.items():
        total = np.zeros_like(trace.time)
        position = 0
        while position < len(expression):
            match = _TERM.match(expression, position)
            if match is None:
                raise ValueError(f"cannot parse SPICE expression for {name}: {expression!r}")
            sign, variable = match.groups()
            key = variable.lower()
            if key not in trace.variables:
                raise MissingEvidenceError(f"{name}: variable {variable} is not in the export; have {sorted(trace.variables)}")
            total = total + (-1.0 if sign == "-" else 1.0) * trace.variables[key]
            position = match.end()
        signals[name] = total
    return signals


def dedupe_time(time: np.ndarray, signals: Mapping[str, np.ndarray]) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """SPICE repeats time stamps at breakpoints; keep the last sample of each stamp so time is strictly increasing."""
    keep = np.r_[np.diff(time) > 0, True]
    return time[keep], {name: values[keep] for name, values in signals.items()}


def compare_pair(plecs: Mapping[str, Any], spice: Mapping[str, Any], manifest: Manifest) -> dict[str, Any]:
    """PLECS is the reference; steady-state metrics decide, NRMSE is advisory."""
    reference = payload_to_result(plecs, "plecs")
    candidate = payload_to_result(spice, "spice")
    window = check_preconditions(reference, manifest)
    try:
        check_preconditions(candidate, manifest)
    except OracleError as error:
        raise OracleError(f"SPICE export failed a precondition: {error}") from error
    plecs_metrics = steady_state_metrics(reference, manifest, window)
    spice_metrics = steady_state_metrics(candidate, manifest, window)
    rows = compare_metrics(spice_metrics, plecs_metrics, manifest)
    advisory = phase_aligned_nrmse(plecs, spice, manifest)
    return {
        "window": window.to_dict(),
        "plecs_metrics": plecs_metrics,
        "spice_metrics": spice_metrics,
        "comparison": rows,
        "passed": all(row["passed"] for row in rows),
        "advisory": advisory,
    }


def phase_aligned_nrmse(plecs: Mapping[str, Any], spice: Mapping[str, Any], manifest: Manifest, points: int = 1000) -> dict[str, Any]:
    """Last period, common grid, one lag from ``i_L`` applied to every signal; never asserted."""
    period = 1.0 / manifest.switching_frequency
    t_p, t_s = np.asarray(plecs["time"], float), np.asarray(spice["time"], float)
    grid = np.linspace(0.0, period, points, endpoint=False)

    def last_period(t: np.ndarray, values: Sequence[float]) -> np.ndarray:
        start = t[-1] - period
        return np.interp(grid, t - start, np.asarray(values, float))

    reference_name = "i_L"
    a = last_period(t_p, plecs["signals"][reference_name])
    b = last_period(t_s, spice["signals"][reference_name])
    a0, b0 = a - a.mean(), b - b.mean()
    correlation = np.array([np.dot(a0, np.roll(b0, shift)) for shift in range(points)])
    lag = int(np.argmax(correlation))
    per_signal = {}
    for name in manifest.signals:
        if name not in plecs["signals"] or name not in spice["signals"]:
            continue
        ref = last_period(t_p, plecs["signals"][name])
        cand = np.roll(last_period(t_s, spice["signals"][name]), lag)
        scale = float(np.ptp(ref)) or float(np.max(np.abs(ref))) or 1.0
        per_signal[name] = float(np.sqrt(np.mean((cand - ref) ** 2)) / scale)
    return {"reference": reference_name, "lag_samples": lag, "lag_seconds": lag * period / points, "nrmse": per_signal}


def overlay_svg(plecs: Mapping[str, Any], spice: Mapping[str, Any], manifest: Manifest, names: Sequence[str] = ("i_L", "v_C")) -> str:
    """Dependency-free last-period overlay: PLECS solid, SPICE dashed."""
    period = 1.0 / manifest.switching_frequency
    width, height, pad = 720, 200, 36
    panels = []
    for row, name in enumerate(names):
        traces = []
        lo = hi = None
        for payload in (plecs, spice):
            t = np.asarray(payload["time"], float)
            mask = t >= t[-1] - period
            x, y = t[mask] - (t[-1] - period), np.asarray(payload["signals"][name], float)[mask]
            lo = min(lo, y.min()) if lo is not None else y.min()
            hi = max(hi, y.max()) if hi is not None else y.max()
            traces.append((x, y))
        span = (hi - lo) or 1.0
        top = row * height
        for (x, y), style in zip(traces, ('stroke="#1f77b4"', 'stroke="#d62728" stroke-dasharray="6 4"')):
            pts = " ".join(
                f"{pad + xi / period * (width - 2 * pad):.1f},{top + height - pad - (yi - lo) / span * (height - 2 * pad):.1f}"
                for xi, yi in zip(x, y)
            )
            panels.append(f'<polyline fill="none" {style} stroke-width="1.5" points="{pts}"/>')
        panels.append(f'<text x="{pad}" y="{top + 18}" font-family="sans-serif" font-size="12">{name}: {lo:.4g} … {hi:.4g} ({manifest.units.get(name, "")}), last period, PLECS solid / SPICE dashed</text>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height * len(names)}" viewBox="0 0 {width} {height * len(names)}">'
        f'<rect width="100%" height="100%" fill="white"/>' + "".join(panels) + "</svg>"
    )


def asc_structure(asc_text: str) -> dict[str, int]:
    """What the LTspice schematic declares, for the structural check against the Circuit Model."""
    return {
        "symbols": sum(1 for line in asc_text.splitlines() if line.startswith("SYMBOL ")),
        "wires": sum(1 for line in asc_text.splitlines() if line.startswith("WIRE ")),
        "ground_flags": sum(1 for line in asc_text.splitlines() if line.startswith("FLAG ") and line.rstrip().endswith(" 0")),
    }


def run_ltspice(executable: Path, deck: Path, workdir: Path) -> tuple[Path, Path]:
    """Convenience only: batch-run one deck with ASCII raw output; returns (raw, log)."""
    workdir.mkdir(parents=True, exist_ok=True)
    target = workdir / deck.name
    shutil.copy(deck, target)
    subprocess.run([str(executable), "-b", "-ascii", target.name], cwd=workdir, check=False, timeout=300)
    return target.with_suffix(".raw"), target.with_suffix(".log")


def ltspice_version(log_path: Path) -> str:
    if not log_path.is_file():
        return "unknown"
    first = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
    return first[0].strip() if first else "unknown"
