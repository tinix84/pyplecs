import json
import math

import numpy as np
import pandas as pd
import pytest

from pyplecs.core.models import SimulationResult
from pyplecs.quantities import (
    MissingSignalError,
    QuantityError,
    SignalMap,
    SignalPair,
    SteadyStateWindow,
    WindowError,
    capture_waveforms,
    component_stress,
    design_quantities,
    power_balance,
    time_weighted_mean,
    time_weighted_rms,
)


def _result(frame: pd.DataFrame, **kwargs) -> SimulationResult:
    return SimulationResult(task_id="t", success=True, timeseries_data=frame, **kwargs)


def _nonuniform_time(t_end: float, n: int, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    gaps = rng.uniform(0.2, 1.8, n - 1)
    time = np.concatenate([[0.0], np.cumsum(gaps)])
    return time / time[-1] * t_end


def test_time_weighted_mean_and_rms_match_closed_forms_on_a_nonuniform_grid():
    time = _nonuniform_time(1.0, 401)

    constant = np.full_like(time, 3.0)
    assert time_weighted_mean(time, constant) == pytest.approx(3.0)
    assert time_weighted_rms(time, constant) == pytest.approx(3.0)

    ramp = 2.0 * time
    assert time_weighted_mean(time, ramp) == pytest.approx(1.0)
    assert time_weighted_rms(time, ramp) == pytest.approx(2.0 / math.sqrt(3))

    duty = 0.3
    edge_time = np.array([0.0, duty, duty, 1.0])
    square = np.array([5.0, 5.0, 0.0, 0.0])
    assert time_weighted_mean(edge_time, square) == pytest.approx(5.0 * duty)
    assert time_weighted_rms(edge_time, square) == pytest.approx(5.0 * math.sqrt(duty))

    dense = np.linspace(0.0, 1.0, 20001)
    sine = 4.0 * np.sin(2 * math.pi * dense)
    assert time_weighted_mean(dense, sine) == pytest.approx(0.0, abs=1e-9)
    assert time_weighted_rms(dense, sine) == pytest.approx(4.0 / math.sqrt(2), rel=1e-6)


def test_capture_returns_exactly_the_last_n_periods_anchored_at_the_final_sample():
    f_sw = 10.0  # period 0.1 s
    time = np.linspace(0.0, 1.0, 1001)
    frame = pd.DataFrame({"Time": time, "i_L": time * 2.0, "v_out": np.ones_like(time)})

    captured = capture_waveforms(
        _result(frame), ["i_L"], window=SteadyStateWindow(switching_frequency=f_sw, periods=5)
    )

    assert set(captured) == {"i_L"}
    waveform = captured["i_L"]
    assert waveform.time[0] == pytest.approx(0.5)
    assert waveform.time[-1] == pytest.approx(1.0)
    assert min(waveform.time) >= 0.5 - 1e-12
    assert waveform.values[0] == pytest.approx(1.0)
    assert waveform.to_dict()["name"] == "i_L"
    assert len(waveform.time) == len(waveform.values)


def test_window_start_is_interpolated_when_it_falls_between_samples():
    frame = pd.DataFrame({"Time": [0.0, 0.4, 0.8, 1.2], "x": [0.0, 4.0, 8.0, 12.0]})
    window = SteadyStateWindow(switching_frequency=1.0, periods=1)  # [0.2, 1.2]

    waveform = capture_waveforms(_result(frame), ["x"], window=window)["x"]

    assert list(waveform.time) == pytest.approx([0.2, 0.4, 0.8, 1.2])
    assert list(waveform.values) == pytest.approx([2.0, 4.0, 8.0, 12.0])


def test_no_window_means_the_whole_run():
    frame = pd.DataFrame({"Time": [0.0, 1.0, 2.0], "x": [1.0, 2.0, 3.0]})
    waveform = capture_waveforms(_result(frame), ["x"])["x"]
    assert list(waveform.time) == [0.0, 1.0, 2.0]
    assert list(waveform.values) == [1.0, 2.0, 3.0]


def test_too_short_run_fails_naming_available_and_required_periods():
    frame = pd.DataFrame({"Time": np.linspace(0.0, 0.3, 31), "x": np.zeros(31)})
    window = SteadyStateWindow(switching_frequency=10.0, periods=5)

    with pytest.raises(WindowError, match=r"3(\.0+)? complete period.*5 required"):
        capture_waveforms(_result(frame), ["x"], window=window)


def test_missing_signal_fails_naming_it_and_listing_the_available_ones():
    frame = pd.DataFrame({"Time": [0.0, 1.0], "i_L": [0.0, 1.0], "v_out": [1.0, 1.0]})

    with pytest.raises(MissingSignalError, match=r"'i_l'.*i_L, v_out"):
        capture_waveforms(_result(frame), ["i_l"])


def test_non_monotonic_time_axis_and_failed_results_are_explicit_errors():
    frame = pd.DataFrame({"Time": [0.0, 2.0, 1.0], "x": [0.0, 0.0, 0.0]})
    with pytest.raises(QuantityError, match="must not decrease"):
        capture_waveforms(_result(frame), ["x"])

    failed = SimulationResult(task_id="t", success=False, error_message="boom")
    with pytest.raises(QuantityError, match="no timeseries"):
        capture_waveforms(failed, ["x"])

    with pytest.raises(QuantityError, match="invalid"):
        SteadyStateWindow(switching_frequency=0.0, periods=5)
    with pytest.raises(QuantityError, match="invalid"):
        SteadyStateWindow(switching_frequency=1.0, periods=0)


# --- #81: component stress, efficiency and losses --------------------------------


def _buck_like_frame() -> pd.DataFrame:
    """Lossless DC frame with one resistive drop declared on 'R_s': v = 2 V, i = 3 A."""
    time = _nonuniform_time(1.0, 101)
    ones = np.ones_like(time)
    return pd.DataFrame(
        {
            "Time": time,
            "v_in": 48.0 * ones,
            "i_in": 1.0 * ones,
            "v_out": 12.0 * ones,
            "i_out": 3.5 * ones,
            "v_Rs": 2.0 * ones,
            "i_Rs": 3.0 * ones,
        }
    )


def test_component_stress_matches_closed_forms_and_reports_slew_rate():
    time = np.array([0.0, 0.5, 0.5, 1.0])
    frame = pd.DataFrame({"Time": time, "v_S": [10.0, 10.0, 0.0, 0.0], "i_S": 2.0 * time})
    signal_map = SignalMap(components={"S1": SignalPair(voltage="v_S", current="i_S")})

    stress = component_stress(_result(frame), signal_map)["S1"]

    assert stress.voltage.mean == pytest.approx(5.0)
    assert stress.voltage.rms == pytest.approx(10.0 * math.sqrt(0.5))
    assert stress.voltage.peak == pytest.approx(10.0)
    assert stress.voltage.peak_to_peak == pytest.approx(10.0)
    assert stress.voltage.max_slew_rate == 0.0  # only an ideal (zero-length) step
    assert stress.current.rms == pytest.approx(2.0 / math.sqrt(3))
    assert stress.current.max_slew_rate == pytest.approx(2.0)
    assert stress.current.minimum == 0.0 and stress.current.maximum == 2.0


def test_power_balance_attributes_declared_losses_and_reports_the_remainder():
    frame = _buck_like_frame()
    signal_map = SignalMap(
        ports={
            "input": SignalPair(voltage="v_in", current="i_in"),
            "output": SignalPair(voltage="v_out", current="i_out"),
        },
        components={"R_s": SignalPair(voltage="v_Rs", current="i_Rs"), "L": SignalPair(current="i_out")},
    )

    balance = power_balance(_result(frame), signal_map)

    assert balance.input_power == pytest.approx(48.0)
    assert balance.output_power == pytest.approx(42.0)
    assert balance.efficiency == pytest.approx(42.0 / 48.0)
    assert balance.total_loss == pytest.approx(6.0)
    assert balance.component_losses == {"R_s": pytest.approx(6.0)}
    assert balance.unattributable_components == ("L",)  # declared a current only: named, not silently dropped
    assert balance.unattributed_loss == pytest.approx(0.0)


def test_lossless_fixture_has_unit_efficiency_and_output_sign_convention_is_declared():
    frame = _buck_like_frame()
    frame["i_out"] = -4.0  # measured into the load: sign=-1 flips it
    signal_map = SignalMap(
        ports={
            "input": SignalPair(voltage="v_in", current="i_in"),
            "output": SignalPair(voltage="v_out", current="i_out", sign=-1),
        }
    )

    balance = power_balance(_result(frame), signal_map)

    assert balance.efficiency == pytest.approx(1.0)
    assert balance.unattributed_loss == pytest.approx(0.0)


def test_signal_map_fails_closed():
    with pytest.raises(QuantityError, match="voltage, a current, or both"):
        SignalPair()
    with pytest.raises(QuantityError, match=r"components\['S1'\]"):
        SignalMap.from_dict({"components": {"S1": {}}})
    with pytest.raises(QuantityError, match="unexpected key"):
        SignalMap.from_dict({"components": {"S1": {"volts": "v"}}})
    with pytest.raises(QuantityError, match="requires an 'input' port"):
        power_balance(_result(_buck_like_frame()), SignalMap(ports={"output": SignalPair("v_out", "i_out")}))
    with pytest.raises(QuantityError, match="both a voltage and a current"):
        power_balance(
            _result(_buck_like_frame()),
            SignalMap(ports={"input": SignalPair(voltage="v_in"), "output": SignalPair("v_out", "i_out")}),
        )
    with pytest.raises(MissingSignalError, match="'v_nope'"):
        component_stress(_result(_buck_like_frame()), SignalMap(components={"X": SignalPair(voltage="v_nope")}))


def test_design_quantities_are_json_ready_and_identical_for_cached_results():
    frame = _buck_like_frame()
    signal_map = SignalMap.from_dict(
        {
            "components": {"R_s": {"voltage": "v_Rs", "current": "i_Rs"}},
            "ports": {"input": {"voltage": "v_in", "current": "i_in"}, "output": {"voltage": "v_out", "current": "i_out"}},
        }
    )
    window = SteadyStateWindow(switching_frequency=10.0, periods=2)

    fresh = design_quantities(_result(frame), signal_map, window=window, waveforms=["v_out"])
    cached = design_quantities(_result(frame.copy(), cached=True), signal_map, window=window, waveforms=["v_out"])

    payload = fresh.to_dict()
    json.dumps(payload)  # no pandas / numpy objects leak
    assert payload["window"] == {"switching_frequency": 10.0, "periods": 2}
    assert payload["waveforms"]["v_out"]["time"][0] == pytest.approx(0.8)
    assert payload["stress"]["R_s"]["current"]["rms"] == pytest.approx(3.0)
    assert payload["power"]["efficiency"] == pytest.approx(42.0 / 48.0)
    assert payload == cached.to_dict()
