"""The step-response comparator proven on synthetic first-order responses, without any simulator."""

import numpy as np
import pytest

from .verification.oracle import OracleError
from .verification.transient import compare_step_response, overlay_svg

TAU, STEP, SPAN = 1e-3, 1.0, 5e-3


def _response(points=1001, *, tau=TAU, step=STEP, offset=0.0, span=SPAN):
    t = np.linspace(0.0, span, points)
    return {"time": t.tolist(), "signals": {"v_C": (step * (1 - np.exp(-t / tau)) + offset).tolist()}}


def test_two_grids_of_the_same_response_agree_and_match_the_analytic_form():
    report = compare_step_response(_response(1001), _response(5018), signal="v_C", step=STEP, tau=TAU, span=SPAN)
    assert report["passed"] and report["analytic_passed"]
    assert report["max_relative_difference"] < 1e-4
    assert set(report["checkpoints"]) == {"tau", "3tau", "end"}
    assert report["checkpoints"]["tau"]["analytic"] == pytest.approx(0.6321, abs=1e-4)


def test_a_wrong_time_constant_fails_the_pointwise_and_analytic_checks():
    report = compare_step_response(_response(), _response(tau=1.2e-3), signal="v_C", step=STEP, tau=TAU, span=SPAN)
    assert not report["passed"] and not report["analytic_passed"]
    assert report["max_relative_difference"] > 0.05
    assert 0 < report["at_time"] < SPAN


def test_an_offset_within_tolerance_passes_but_is_reported():
    report = compare_step_response(_response(), _response(offset=0.005), signal="v_C", step=STEP, tau=TAU, span=SPAN, tolerance=0.01)
    assert report["passed"] and report["max_relative_difference"] == pytest.approx(0.005, abs=1e-6)


def test_bad_inputs_fail_closed():
    with pytest.raises(OracleError, match="not monotonic"):
        compare_step_response(_response(), {"time": [0.0, 2e-3, 1e-3], "signals": {"v_C": [0.0, 1.0, 0.5]}}, signal="v_C", step=STEP, tau=TAU, span=SPAN)
    with pytest.raises(OracleError, match="positive span"):
        compare_step_response(_response(), _response(), signal="v_C", step=STEP, tau=TAU, span=0.0)


def test_overlay_is_plain_svg():
    svg = overlay_svg(_response(), _response(), signal="v_C", span=SPAN, unit="V")
    assert svg.startswith("<svg") and svg.count("<polyline") == 2 and "v_C" in svg
