"""Design Quantities computed on demand from one Simulation Result.

Every quantity here is a pure function of a Simulation Result, a caller-owned
Signal Map and an optional steady-state window. Nothing is inferred from
signal names and nothing is stored back into the Cache Record.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from .core.models import SimulationResult

TIME_COLUMN = "Time"


class QuantityError(ValueError):
    """A Design Quantity could not be computed from the given inputs."""


class MissingSignalError(QuantityError):
    """A Signal Map or capture named a column the Simulation Result lacks."""


class WindowError(QuantityError):
    """The steady-state window cannot be cut from the run."""


@dataclass(frozen=True)
class SteadyStateWindow:
    """The last ``periods`` complete switching periods, anchored at the end of the run."""

    switching_frequency: float
    periods: int = 5

    def __post_init__(self) -> None:
        if not (self.switching_frequency > 0) or not math.isfinite(self.switching_frequency):
            raise QuantityError("invalid window: switching_frequency must be a positive number")
        if int(self.periods) != self.periods or self.periods < 1:
            raise QuantityError("invalid window: periods must be a positive integer")

    @property
    def duration(self) -> float:
        return self.periods / self.switching_frequency

    def start(self, time: np.ndarray) -> float:
        available = (time[-1] - time[0]) * self.switching_frequency
        if available + 1e-9 < self.periods:
            raise WindowError(
                f"run holds {available:.6g} complete periods of {self.switching_frequency:g} Hz; "
                f"{self.periods} required"
            )
        return float(time[-1] - self.duration)

    def to_dict(self) -> dict[str, Any]:
        return {"switching_frequency": self.switching_frequency, "periods": self.periods}


@dataclass(frozen=True)
class Waveform:
    """One named time-series over the requested window."""

    name: str
    time: tuple[float, ...]
    values: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "time": list(self.time), "values": list(self.values)}


@dataclass(frozen=True)
class SignalPair:
    """The voltage and current columns declared for one component or port."""

    voltage: Optional[str] = None
    current: Optional[str] = None
    sign: int = 1

    def __post_init__(self) -> None:
        if self.voltage is None and self.current is None:
            raise QuantityError("a signal pair must declare a voltage, a current, or both")
        if self.sign not in (1, -1):
            raise QuantityError("sign must be 1 or -1")


@dataclass(frozen=True)
class SignalMap:
    """Caller-declared roles: which column is which component's or port's voltage/current."""

    components: Mapping[str, SignalPair] = field(default_factory=dict)
    ports: Mapping[str, SignalPair] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SignalMap":
        if not isinstance(data, Mapping):
            raise QuantityError("signal map must be an object")
        unexpected = sorted(set(data) - {"components", "ports"})
        if unexpected:
            raise QuantityError(f"signal map has unexpected key(s): {', '.join(unexpected)}")
        return cls(
            components=_pairs(data.get("components", {}), "components"),
            ports=_pairs(data.get("ports", {}), "ports"),
        )


@dataclass(frozen=True)
class SignalStress:
    """Time-weighted and sampled statistics of one signal over the window."""

    signal: str
    mean: float
    rms: float
    peak: float
    minimum: float
    maximum: float
    peak_to_peak: float
    max_slew_rate: float

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class ComponentStress:
    component: str
    voltage: Optional[SignalStress]
    current: Optional[SignalStress]

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "voltage": None if self.voltage is None else self.voltage.to_dict(),
            "current": None if self.current is None else self.current.to_dict(),
        }


@dataclass(frozen=True)
class PowerBalance:
    input_power: float
    output_power: float
    efficiency: float
    total_loss: float
    component_losses: Mapping[str, float]
    unattributed_loss: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_power": self.input_power,
            "output_power": self.output_power,
            "efficiency": self.efficiency,
            "total_loss": self.total_loss,
            "component_losses": dict(self.component_losses),
            "unattributed_loss": self.unattributed_loss,
        }


@dataclass(frozen=True)
class DesignQuantities:
    """Everything one request derives from one Simulation Result."""

    task_id: str
    window: Optional[SteadyStateWindow]
    waveforms: Mapping[str, Waveform]
    stress: Mapping[str, ComponentStress]
    power: Optional[PowerBalance]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "window": None if self.window is None else self.window.to_dict(),
            "waveforms": {name: waveform.to_dict() for name, waveform in self.waveforms.items()},
            "stress": {name: stress.to_dict() for name, stress in self.stress.items()},
            "power": None if self.power is None else self.power.to_dict(),
        }


# --- time-weighted metrics -------------------------------------------------


def time_weighted_mean(time: Sequence[float], values: Sequence[float]) -> float:
    """Mean of a piecewise-linear signal: exact integral of each segment."""
    t, x = _arrays(time, values)
    span = t[-1] - t[0]
    if span <= 0:
        return float(x[0])
    dt = np.diff(t)
    return float(np.sum((x[:-1] + x[1:]) / 2.0 * dt) / span)


def time_weighted_rms(time: Sequence[float], values: Sequence[float]) -> float:
    """RMS of a piecewise-linear signal: exact integral of x² on each segment."""
    t, x = _arrays(time, values)
    span = t[-1] - t[0]
    if span <= 0:
        return float(abs(x[0]))
    a, b = x[:-1], x[1:]
    dt = np.diff(t)
    return float(math.sqrt(np.sum((a * a + a * b + b * b) / 3.0 * dt) / span))


def time_weighted_product_mean(
    time: Sequence[float], first: Sequence[float], second: Sequence[float]
) -> float:
    """Mean of the product of two piecewise-linear signals (instantaneous power)."""
    t, u = _arrays(time, first)
    _, v = _arrays(time, second)
    span = t[-1] - t[0]
    if span <= 0:
        return float(u[0] * v[0])
    a1, b1, a2, b2 = u[:-1], u[1:], v[:-1], v[1:]
    dt = np.diff(t)
    segment = (2 * a1 * a2 + a1 * b2 + b1 * a2 + 2 * b1 * b2) / 6.0
    return float(np.sum(segment * dt) / span)


def signal_stress(name: str, time: Sequence[float], values: Sequence[float]) -> SignalStress:
    t, x = _arrays(time, values)
    dt = np.diff(t)
    finite = dt > 0
    slew = float(np.max(np.abs(np.diff(x)[finite] / dt[finite]))) if np.any(finite) else 0.0
    return SignalStress(
        signal=name,
        mean=time_weighted_mean(t, x),
        rms=time_weighted_rms(t, x),
        peak=float(np.max(np.abs(x))),
        minimum=float(np.min(x)),
        maximum=float(np.max(x)),
        peak_to_peak=float(np.max(x) - np.min(x)),
        max_slew_rate=slew,
    )


# --- quantities ----------------------------------------------------------------


def capture_waveforms(
    result: SimulationResult,
    names: Sequence[str],
    *,
    window: Optional[SteadyStateWindow] = None,
) -> dict[str, Waveform]:
    """Return the named signals of a Simulation Result over the window."""
    columns = _window_columns(result, names, window)
    time = columns.pop(TIME_COLUMN)
    return {
        name: Waveform(name=name, time=tuple(time.tolist()), values=tuple(values.tolist()))
        for name, values in columns.items()
    }


def component_stress(
    result: SimulationResult,
    signal_map: SignalMap,
    *,
    window: Optional[SteadyStateWindow] = None,
) -> dict[str, ComponentStress]:
    """Per-component stress of every declared voltage and current."""
    needed = _declared_columns(signal_map.components)
    columns = _window_columns(result, needed, window)
    time = columns[TIME_COLUMN]
    stress: dict[str, ComponentStress] = {}
    for component, pair in signal_map.components.items():
        stress[component] = ComponentStress(
            component=component,
            voltage=None if pair.voltage is None else signal_stress(pair.voltage, time, columns[pair.voltage]),
            current=None if pair.current is None else signal_stress(pair.current, time, columns[pair.current]),
        )
    return stress


def power_balance(
    result: SimulationResult,
    signal_map: SignalMap,
    *,
    window: Optional[SteadyStateWindow] = None,
) -> PowerBalance:
    """Efficiency and loss breakdown from declared ports and components."""
    for port in ("input", "output"):
        pair = signal_map.ports.get(port)
        if pair is None:
            raise QuantityError(f"power balance requires an '{port}' port in the signal map")
        if pair.voltage is None or pair.current is None:
            raise QuantityError(f"port '{port}' must declare both a voltage and a current")
    complete = {
        name: pair
        for name, pair in signal_map.components.items()
        if pair.voltage is not None and pair.current is not None
    }
    needed = _declared_columns(signal_map.ports) + _declared_columns(complete)
    columns = _window_columns(result, needed, window)
    time = columns[TIME_COLUMN]

    def mean_power(pair: SignalPair) -> float:
        return pair.sign * time_weighted_product_mean(time, columns[pair.voltage], columns[pair.current])

    input_power = mean_power(signal_map.ports["input"])
    output_power = mean_power(signal_map.ports["output"])
    if input_power == 0:
        raise QuantityError("input power is zero over the window; efficiency is undefined")
    component_losses = {name: mean_power(pair) for name, pair in complete.items()}
    total_loss = input_power - output_power
    return PowerBalance(
        input_power=input_power,
        output_power=output_power,
        efficiency=output_power / input_power,
        total_loss=total_loss,
        component_losses=component_losses,
        unattributed_loss=total_loss - sum(component_losses.values()),
    )


def design_quantities(
    result: SimulationResult,
    signal_map: SignalMap,
    *,
    window: Optional[SteadyStateWindow] = None,
    waveforms: Sequence[str] = (),
) -> DesignQuantities:
    """Waveforms, stress and power balance for one Simulation Result in one call."""
    return DesignQuantities(
        task_id=result.task_id,
        window=window,
        waveforms=capture_waveforms(result, waveforms, window=window) if waveforms else {},
        stress=component_stress(result, signal_map, window=window) if signal_map.components else {},
        power=power_balance(result, signal_map, window=window) if signal_map.ports else None,
    )


def design_quantities_payload(
    result: SimulationResult,
    *,
    signal_map: Mapping[str, Any],
    window: Optional[Mapping[str, Any]] = None,
    waveforms: Sequence[str] = (),
) -> dict[str, Any]:
    """The one JSON shape every transport (Python, REST, MCP) returns for a request body."""
    if window is not None:
        if not isinstance(window, Mapping):
            raise QuantityError("window must be an object with switching_frequency and periods")
        unexpected = sorted(set(window) - {"switching_frequency", "periods"})
        if unexpected:
            raise QuantityError(f"window has unexpected key(s): {', '.join(unexpected)}")
        if "switching_frequency" not in window:
            raise QuantityError("window requires switching_frequency")
        try:
            steady_state = SteadyStateWindow(
                switching_frequency=float(window["switching_frequency"]),
                periods=int(window.get("periods", 5)),
            )
        except QuantityError:
            raise
        except (TypeError, ValueError) as error:
            raise QuantityError(f"invalid window: {error}") from error
    else:
        steady_state = None
    if isinstance(waveforms, str) or not all(isinstance(name, str) for name in waveforms):
        raise QuantityError("waveforms must be a list of signal names")
    return design_quantities(
        result, SignalMap.from_dict(signal_map), window=steady_state, waveforms=list(waveforms)
    ).to_dict()


# --- internals -------------------------------------------------------------------


def _arrays(time: Sequence[float], values: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    t = np.asarray(time, dtype=float)
    x = np.asarray(values, dtype=float)
    if t.ndim != 1 or t.shape != x.shape or t.size == 0:
        raise QuantityError("time and values must be non-empty vectors of equal length")
    return t, x


def _pairs(data: Any, section: str) -> dict[str, SignalPair]:
    if not isinstance(data, Mapping):
        raise QuantityError(f"signal map '{section}' must be an object")
    pairs: dict[str, SignalPair] = {}
    for name, spec in data.items():
        if not isinstance(spec, Mapping):
            raise QuantityError(f"signal map {section}['{name}'] must be an object")
        unexpected = sorted(set(spec) - {"voltage", "current", "sign"})
        if unexpected:
            raise QuantityError(
                f"signal map {section}['{name}'] has unexpected key(s): {', '.join(unexpected)}"
            )
        try:
            pairs[str(name)] = SignalPair(
                voltage=spec.get("voltage"), current=spec.get("current"), sign=spec.get("sign", 1)
            )
        except QuantityError as error:
            raise QuantityError(f"signal map {section}['{name}']: {error}") from error
    return pairs


def _declared_columns(pairs: Mapping[str, SignalPair]) -> list[str]:
    seen: dict[str, None] = {}
    for pair in pairs.values():
        for column in (pair.voltage, pair.current):
            if column is not None:
                seen[column] = None
    return list(seen)


def _window_columns(
    result: SimulationResult,
    names: Sequence[str],
    window: Optional[SteadyStateWindow],
) -> dict[str, np.ndarray]:
    frame = result.timeseries_data
    if frame is None:
        raise QuantityError(
            f"Simulation Result {result.task_id} has no timeseries data"
            + (f": {result.error_message}" if result.error_message else "")
        )
    if TIME_COLUMN not in frame.columns:
        raise QuantityError(f"Simulation Result {result.task_id} has no '{TIME_COLUMN}' column")
    available = [column for column in frame.columns if column != TIME_COLUMN]
    missing = [name for name in names if name not in frame.columns or name == TIME_COLUMN]
    if missing:
        raise MissingSignalError(
            f"signal(s) {', '.join(repr(name) for name in missing)} not in Simulation Result; "
            f"available: {', '.join(available)}"
        )

    time = frame[TIME_COLUMN].to_numpy(dtype=float)
    if time.size == 0:
        raise QuantityError("Simulation Result timeseries is empty")
    if np.any(np.diff(time) < 0):
        raise QuantityError("time axis must be non-decreasing (increasing between distinct samples)")

    columns = {name: frame[name].to_numpy(dtype=float) for name in dict.fromkeys(names)}
    if window is None:
        return {TIME_COLUMN: time, **columns}

    start = window.start(time)
    first = int(np.searchsorted(time, start, side="left"))
    cut_time = time[first:]
    cut = {name: values[first:] for name, values in columns.items()}
    if first > 0 and cut_time[0] > start:
        previous = time[first - 1]
        weight = (start - previous) / (time[first] - previous)
        cut_time = np.concatenate([[start], cut_time])
        cut = {
            name: np.concatenate(
                [[columns[name][first - 1] + weight * (columns[name][first] - columns[name][first - 1])], values]
            )
            for name, values in cut.items()
        }
    return {TIME_COLUMN: cut_time, **cut}


__all__ = [
    "ComponentStress",
    "DesignQuantities",
    "MissingSignalError",
    "PowerBalance",
    "QuantityError",
    "SignalMap",
    "SignalPair",
    "SignalStress",
    "SteadyStateWindow",
    "Waveform",
    "WindowError",
    "capture_waveforms",
    "component_stress",
    "design_quantities",
    "design_quantities_payload",
    "power_balance",
    "signal_stress",
    "time_weighted_mean",
    "time_weighted_product_mean",
    "time_weighted_rms",
]
