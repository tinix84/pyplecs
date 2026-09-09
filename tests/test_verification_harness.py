"""The verification layer proven without PLECS: selection, skip, isolation, manifest, oracle, comparator."""

import re
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from pyplecs.core.models import SimulationResult

from .verification.manifest import (
    CANONICAL_BUCK,
    REPO_ROOT,
    isolated_config,
    load_manifest,
    require_live_plecs,
)
from .verification.oracle import (
    OracleError,
    analytic_invariants,
    check_preconditions,
    compare_quantities,
    steady_state_quantities,
)

LIVE_TEST_FILES = ("tests/test_live_canonical_buck.py", "tests/test_tas_live.py")
ACCEPTANCE_TEST_FILES = ("tests/test_converter_acceptance.py",)


def test_canonical_buck_manifest_matches_the_tracked_model():
    manifest = load_manifest(CANONICAL_BUCK)
    assert manifest.model_file.is_file()
    probe_block = manifest.model_file.read_text(encoding="utf-8").split('Name          "all_prb"')[1].split("Component {")[0]
    probed = re.findall(r'"([^"]+)"', "".join(re.findall(r"Signals\s+\{([^}]*)\}", probe_block)))
    assert len(probed) == len(manifest.signals) == 13
    assert set(manifest.required_signals) <= set(manifest.signals)
    assert set(manifest.units) == set(manifest.signals)
    assert manifest.switching_frequency == 100e3 and manifest.periods == 5
    assert manifest.derived() == pytest.approx({"duty_ratio": 0.5, "load_resistance": 3.0, "inductor_ripple": 6.0})
    declared = {name for pair in manifest.signal_map["components"].values() for name in pair.values()}
    declared |= {name for pair in manifest.signal_map["ports"].values() for name in pair.values()}
    assert declared <= set(manifest.signals)


def test_live_and_acceptance_tests_are_deselected_by_default_and_selected_by_marker():
    collect = [sys.executable, "-m", "pytest", "--collect-only", "-q", *LIVE_TEST_FILES]
    default = subprocess.run(collect, cwd=REPO_ROOT, capture_output=True, text=True)
    assert "deselected" in default.stdout and "::test_" not in default.stdout, default.stdout
    opted_in = subprocess.run([*collect, "-m", "live_plecs"], cwd=REPO_ROOT, capture_output=True, text=True)
    assert opted_in.stdout.count("::test_") >= 2, opted_in.stdout

    collect = [sys.executable, "-m", "pytest", "--collect-only", "-q", *ACCEPTANCE_TEST_FILES]
    default = subprocess.run(collect, cwd=REPO_ROOT, capture_output=True, text=True)
    assert "deselected" in default.stdout and "::test_" not in default.stdout, default.stdout
    opted_in = subprocess.run([*collect, "-m", "converter_acceptance"], cwd=REPO_ROOT, capture_output=True, text=True)
    assert opted_in.stdout.count("::test_") == 2, opted_in.stdout


def test_unreachable_plecs_skips_with_the_endpoint_in_the_reason():
    launched = []
    with pytest.raises(pytest.skip.Exception, match=r"unavailable at plecs-host:1234"):
        require_live_plecs("plecs-host", 1234, lambda *args: launched.append(args) or False)
    assert launched == [("plecs-host", 1234, 3.0)]


def test_isolated_config_never_reads_the_machine_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "default.yml").write_text("plecs:\n  version: 'machine-local'\n", encoding="utf-8")
    config = isolated_config(tmp_path, load_manifest(CANONICAL_BUCK))
    assert config.config_path is None
    assert config.plecs.version == "4.7.7" and config.plecs.auto_launch is False
    assert config.cache.directory == str(tmp_path / "cache")
    assert (config.plecs.xmlrpc_host, config.plecs.xmlrpc_port) == ("localhost", 1080)


# --- the oracle itself, on synthetic waveforms -----------------------------------------------


def _synthetic_buck(manifest, *, span=1e-3, points=20001, ripple=6.0, growth=0.0, drop=(), time=None):
    """A settled buck at the manifest's Operating Point: triangular i_L, flat v_C, everything mapped."""
    p, d = manifest.parameters, manifest.derived()
    t = np.linspace(0.0, span, points) if time is None else np.asarray(time, dtype=float)
    phase = (t * p["fs"] + 1e-9) % 1.0  # nudge off the exact duty boundary so both grids classify edges alike
    tri = np.where(phase < d["duty_ratio"], phase / d["duty_ratio"], (1 - phase) / (1 - d["duty_ratio"])) - 0.5
    v_out = 0.98 * d["duty_ratio"] * p["Vi"]
    i_out = v_out / d["load_resistance"]
    i_l = i_out + ripple * tri * (1.0 + growth * t / span)
    gate = (phase < d["duty_ratio"]).astype(float)
    frame = {
        "Time": t,
        "v_in": np.full_like(t, p["Vi"]), "i_in": i_l * gate,
        "v_S": p["Vi"] * (1 - gate), "i_S": i_l * gate, "gate_S": gate,
        "v_D": -p["Vi"] * gate, "i_D": i_l * (1 - gate),
        "i_L": i_l, "v_L": np.where(gate > 0, p["Vi"] - v_out, -v_out),
        "v_C": np.full_like(t, v_out), "i_C": i_l - i_out,
        "v_R": np.full_like(t, v_out), "i_R": np.full_like(t, i_out),
    }
    for name in drop:
        frame.pop(name)
    return SimulationResult(task_id="synthetic", success=True, timeseries_data=pd.DataFrame(frame))


def test_oracle_passes_a_settled_synthetic_buck_and_its_quantities_match_themselves():
    manifest = load_manifest(CANONICAL_BUCK)
    result = _synthetic_buck(manifest)
    window = check_preconditions(result, manifest)
    quantities = steady_state_quantities(result, manifest, window)
    assert all(check["passed"] for check in analytic_invariants(quantities, manifest)), analytic_invariants(quantities, manifest)
    assert quantities["i_L"]["peak_to_peak"] == pytest.approx(6.0, rel=0.02)
    assert all(row["passed"] for row in compare_quantities(quantities, quantities, manifest))


@pytest.mark.parametrize(
    "kwargs, cause",
    [
        ({"drop": ("v_C",)}, "required signals missing"),
        ({"time": np.r_[np.linspace(0, 5e-4, 10000), np.linspace(5e-4, 1e-3, 10001)]}, "strictly increasing"),
        ({"span": 2e-5, "points": 401}, "window cannot be cut"),
        ({"growth": 20.0}, "has not converged"),
    ],
)
def test_oracle_fails_closed_with_a_named_cause(kwargs, cause):
    manifest = load_manifest(CANONICAL_BUCK)
    with pytest.raises(OracleError, match=cause):
        check_preconditions(_synthetic_buck(manifest, **kwargs), manifest)


def test_oracle_rejects_a_failed_simulation_result():
    manifest = load_manifest(CANONICAL_BUCK)
    with pytest.raises(OracleError, match="failure"):
        check_preconditions(SimulationResult(task_id="x", success=False, error_message="boom"), manifest)


def test_quantity_comparison_uses_symmetric_error_and_per_unit_floors():
    manifest = load_manifest(CANONICAL_BUCK)
    reference = {"i_L": {"mean": 4.0, "peak_to_peak": 6.0}, "v_in": {"peak_to_peak": 0.0}, "i_C": {"mean": 0.0}}
    actual = {"i_L": {"mean": 4.1, "peak_to_peak": 6.5}, "v_in": {"peak_to_peak": 0.04}, "i_C": {"mean": 0.009}}
    rows = {(r["signal"], r["quantity"]): r for r in compare_quantities(actual, reference, manifest)}
    assert rows[("i_L", "mean")]["error"] == pytest.approx(0.1 / 4.1) and rows[("i_L", "mean")]["passed"] is False
    assert rows[("i_L", "peak_to_peak")]["passed"] is True  # 7.7 % < 10 %
    assert rows[("v_in", "peak_to_peak")]["passed"] is True  # both below the 50 mV floor
    assert rows[("i_C", "mean")]["passed"] is True  # both below the 10 mA floor
    missing = compare_quantities({}, reference, manifest)
    assert all(row["passed"] is False and row["reason"] == "signal missing" for row in missing)
    strict = {(r["signal"], r["quantity"]): r for r in compare_quantities(actual, reference, manifest, absolute_floor={})}
    assert strict[("i_C", "mean")]["passed"] is False  # without floors the relative rule applies everywhere


# --- the converter acceptance pack, without LTspice --------------------------------------------

from .verification.spice import (  # noqa: E402
    MissingEvidenceError,
    asc_structure,
    compare_pair,
    dedupe_time,
    evaluate_expressions,
    overlay_svg,
    phase_aligned_nrmse,
    read_ltspice_ascii_raw,
)

RAW_SAMPLE = REPO_ROOT / "tests" / "fixtures" / "ltspice_ascii_sample.raw"


def test_ltspice_ascii_raw_reader_and_signed_expressions():
    trace = read_ltspice_ascii_raw(RAW_SAMPLE)
    assert trace.header["Plotname"] == "Transient Analysis" and list(trace.time) == [0.0, 5e-4, 1e-3]
    mapped = evaluate_expressions(trace, {"v_S": "V(n002)-V(n001)", "i_in": "-I(VDCin)", "v_in": "v(N002)"})
    assert list(mapped["v_S"]) == [23.0, 22.0, 21.0]
    assert list(mapped["i_in"]) == [2.0, 3.0, 4.0]
    assert list(mapped["v_in"]) == [24.0, 24.0, 24.0]
    with pytest.raises(MissingEvidenceError, match="not in the export"):
        evaluate_expressions(trace, {"x": "I(L1)"})
    with pytest.raises(MissingEvidenceError, match="not found"):
        read_ltspice_ascii_raw(RAW_SAMPLE.with_name("nope.raw"))


def test_ltspice_reader_refuses_a_deck_that_did_not_run(tmp_path):
    empty = tmp_path / "asc.raw"
    empty.write_text(RAW_SAMPLE.read_text(encoding="utf-8").replace("No. Points:            3", "No. Points:            0"), encoding="utf-8")
    with pytest.raises(MissingEvidenceError, match="0 points"):
        read_ltspice_ascii_raw(empty)


def test_repeated_spice_time_stamps_are_collapsed_to_a_strictly_increasing_axis():
    time, signals = dedupe_time(np.array([0.0, 1.0, 1.0, 2.0]), {"x": np.array([0.0, 1.0, 5.0, 2.0])})
    assert list(time) == [0.0, 1.0, 2.0] and list(signals["x"]) == [0.0, 5.0, 2.0]


def _payload(result):
    frame = result.timeseries_data
    return {"time": frame["Time"].tolist(), "signals": {c: frame[c].tolist() for c in frame.columns if c != "Time"}}


def test_comparator_passes_an_equivalent_pair_and_fails_a_drifted_one():
    manifest = load_manifest(CANONICAL_BUCK)
    plecs = _payload(_synthetic_buck(manifest))
    spice = _payload(_synthetic_buck(manifest, points=30001))  # a denser, non-multiple grid of the same circuit
    report = compare_pair(plecs, spice, manifest)
    assert report["passed"], [r for r in report["comparison"] if not r["passed"]]
    assert report["advisory"]["reference"] == "i_L" and report["advisory"]["nrmse"]["i_L"] < 0.05

    drifted = _payload(_synthetic_buck(manifest, ripple=7.0))  # 17 % more inductor ripple than PLECS
    report = compare_pair(plecs, drifted, manifest)
    failed = {(r["signal"], r["quantity"]) for r in report["comparison"] if not r["passed"]}
    assert not report["passed"] and ("i_L", "peak_to_peak") in failed

    with pytest.raises(OracleError, match="SPICE export failed a precondition"):
        compare_pair(plecs, _payload(_synthetic_buck(manifest, drop=("v_C",))), manifest)


def test_phase_alignment_uses_one_lag_for_every_signal():
    manifest = load_manifest(CANONICAL_BUCK)
    plecs = _payload(_synthetic_buck(manifest))
    shifted = _synthetic_buck(manifest, time=np.linspace(0.0, 1e-3, 20001) + 2.5e-6)  # quarter period late
    advisory = phase_aligned_nrmse(plecs, _payload(shifted), manifest)
    assert advisory["lag_samples"] == pytest.approx(250, abs=2)
    assert max(advisory["nrmse"].values()) < 0.05


def test_overlay_and_asc_structure_are_plain_text():
    manifest = load_manifest(CANONICAL_BUCK)
    payload = _payload(_synthetic_buck(manifest))
    svg = overlay_svg(payload, payload, manifest)
    assert svg.startswith("<svg") and svg.count("<polyline") == 4
    asc = "Version 4\nSHEET 1 880 680\nWIRE 0 0 1 1\nSYMBOL res 0 0 R0\nSYMBOL cap 0 0 R0\nFLAG 0 0 0\n"
    assert asc_structure(asc) == {"symbols": 2, "wires": 1, "ground_flags": 1}
