"""LTspice → PLECS acceptance: an RC low-pass step response authored in LTspice, run in both simulators (#43 track 1).

    PYPLECS_LTSPICE="C:/Program Files/ADI/LTspice/LTspice.exe" uv run pytest -m converter_acceptance

The `.asc` is the source of truth. It is imported into the Circuit Model, emitted as a `.plecs`
with a probe on the capacitor voltage, simulated on the live PLECS, and compared point-wise with
LTspice's own run of the schematic and with the analytic response. Nothing skips: missing
LTspice evidence or an unreachable PLECS fails naming the cause.
"""

import os
import shutil
from pathlib import Path

import pytest

from pyplecs.converter import ltspice_to_plecs, parse_ltspice
from pyplecs.core.models import SimulationRequest
from pyplecs.normalization import simulation_result_payload
from pyplecs.orchestration import SimulationOrchestrator
from pyplecs.orchestration.live import LivePlecsAdapter
from pyplecs.pyplecs import _is_plecs_xmlrpc_alive

from .verification.evidence import EvidenceBundle, utc_stamp
from .verification.manifest import EVIDENCE_ROOT, FIXTURES, REPO_ROOT, isolated_config
from .verification.spice import (
    MissingEvidenceError,
    dedupe_time,
    evaluate_expressions,
    ltspice_version,
    read_ltspice_ascii_raw,
    run_ltspice,
)
from .verification.transient import compare_step_response, overlay_svg

pytestmark = pytest.mark.converter_acceptance

RC_STEP = FIXTURES / "rc_step.asc"
STEP_V, R_OHM, C_F, SPAN_S = 1.0, 1e3, 1e-6, 5e-3  # the fixture's .param values; tau = 1 ms
SIGNAL = "v_C"
LTSPICE_EXPRESSIONS = {SIGNAL: "V(n002)", "i_R": "I(R1)"}


def _inbox() -> Path:
    return EVIDENCE_ROOT / "rc_step" / "step" / "spice"


def _ltspice_payload() -> tuple[dict, Path]:
    inbox = _inbox()
    raw, log = inbox / "asc.raw", inbox / "asc.log"
    executable = os.environ.get("PYPLECS_LTSPICE")
    if executable:
        produced_raw, produced_log = run_ltspice(Path(executable), RC_STEP, inbox / "run-asc")
        inbox.mkdir(parents=True, exist_ok=True)
        for produced, target in ((produced_raw, raw), (produced_log, log)):
            if produced.exists():
                shutil.copy(produced, target)
    if not raw.exists():
        raise MissingEvidenceError(
            f"missing LTspice export {raw.relative_to(REPO_ROOT)} — run `LTspice.exe -b -ascii rc_step.asc` and copy the .raw there, "
            f"or set PYPLECS_LTSPICE to the LTspice executable"
        )
    trace = read_ltspice_ascii_raw(raw)
    time, signals = dedupe_time(trace.time, evaluate_expressions(trace, LTSPICE_EXPRESSIONS))
    return {"time": time.tolist(), "signals": {k: v.tolist() for k, v in signals.items()}}, log


async def _plecs_payload(model: Path, tmp_path, canonical_buck) -> dict:
    host, port = canonical_buck.endpoint
    if not _is_plecs_xmlrpc_alive(host, port, 3.0):
        raise MissingEvidenceError(f"PLECS at {host}:{port} does not answer XML-RPC; the imported schematic cannot be simulated")
    config = isolated_config(tmp_path, canonical_buck)
    orchestrator = SimulationOrchestrator(LivePlecsAdapter(config), config=config)
    try:
        task_id = await orchestrator.submit_simulation(
            SimulationRequest(model_file=str(model), output_variables=[SIGNAL, "i_R"]), use_cache=False
        )
        snapshot = await orchestrator.wait_for_completion(task_id, timeout=120)
    finally:
        await orchestrator.stop()
    assert snapshot is not None and snapshot.status.value == "completed", snapshot
    return simulation_result_payload(snapshot.result)


@pytest.mark.asyncio
async def test_rc_step_authored_in_ltspice_gives_the_same_response_in_plecs(canonical_buck, tmp_path):
    bundle = EvidenceBundle(EVIDENCE_ROOT / "rc_step" / "step" / (utc_stamp() + "-ltspice-import"))
    circuit = parse_ltspice(RC_STEP)
    model = bundle.directory / "rc_step.plecs"
    ltspice_to_plecs(circuit, model, probes=(("C1", "Capacitor voltage"), ("R1", "Resistor current")))
    bundle.write_text(
        "conversion.md",
        "```\nuv run pyplecs-convert tests/fixtures/rc_step.asc --format plecs "
        f"--probe 'C1:Capacitor voltage' --probe 'R1:Resistor current' -o {bundle.directory.relative_to(REPO_ROOT).as_posix()}\n```\n"
        f"Circuit Model: {len(circuit.components)} components, {len(circuit.nets)} nets; parameters {circuit.raw_params}.\n"
        "The step is applied at t = 0: DC source with the capacitor's initial voltage 0 in both simulators (`ic=0` + `uic` in LTspice).\n",
    )
    shutil.copy(RC_STEP, bundle.directory / "rc_step.asc")

    ltspice, log = _ltspice_payload()
    plecs = await _plecs_payload(model, tmp_path, canonical_buck)

    report = compare_step_response(ltspice, plecs, signal=SIGNAL, step=STEP_V, tau=R_OHM * C_F, span=SPAN_S)
    bundle.write_json("comparison", report)
    bundle.write_json(
        "environment",
        bundle.environment(
            ltspice=ltspice_version(log),
            plecs=f"live PLECS {canonical_buck.plecs_version} at %s:%d" % canonical_buck.endpoint,
            samples={"ltspice": len(ltspice["time"]), "plecs": len(plecs["time"])},
        ),
    )
    bundle.write_series("ltspice", ltspice["time"], ltspice["signals"])
    bundle.write_series("plecs", plecs["time"], plecs["signals"])
    bundle.write_text("overlay.svg", overlay_svg(ltspice, plecs, signal=SIGNAL, span=SPAN_S, unit="V"))
    checkpoints = "\n".join(
        f"| {label} | {c['t']:.4g} | {c['analytic']:.5g} | {c['reference']:.5g} | {c['candidate']:.5g} | {c['reference_error']:.3%} | {c['candidate_error']:.3%} |"
        for label, c in report["checkpoints"].items()
    )
    bundle.write_text(
        "summary.md",
        "# rc_step — LTspice schematic imported to PLECS, step response compared\n\n"
        f"{ltspice_version(log)} (reference, {len(ltspice['time'])} samples) vs PLECS {canonical_buck.plecs_version} "
        f"({len(plecs['time'])} samples) on `{SIGNAL}`, 0 … {SPAN_S:g} s, τ = {R_OHM * C_F:g} s.\n\n"
        f"**Verdict: {'PASS' if report['passed'] else 'FAIL'}** — max |Δ| / step = {report['max_relative_difference']:.3e} "
        f"(tolerance {report['tolerance']:.1%}) at t = {report['at_time']:.4g} s; "
        f"vs analytic: LTspice {report['max_relative_error_vs_analytic']['reference']:.3e}, PLECS {report['max_relative_error_vs_analytic']['candidate']:.3e}.\n\n"
        "| point | t [s] | analytic | LTspice | PLECS | LTspice err | PLECS err |\n|---|---|---|---|---|---|---|\n" + checkpoints + "\n",
    )
    assert report["passed"], report
    assert report["analytic_passed"], report["max_relative_error_vs_analytic"]
