"""Semi-manual converter acceptance pack (#61): PLECS versus the emitted .cir and .asc (ADR-0013).

    uv run pytest -m converter_acceptance

The maintainer supplies LTspice exports in the evidence inbox
``tests/evidence/<model>/<operating point>/spice/{cir,asc}.raw`` — by running
``LTspice.exe -b -ascii <deck>`` by hand, or by pointing ``PYPLECS_LTSPICE`` at
the executable so this test runs it. PLECS is the reference and must be live.
Nothing here skips: missing evidence fails naming the file it expected.
"""

import os
import shutil
from pathlib import Path

import pytest

from pyplecs.converter import parse_plecs, plecs_to_ltspice, plecs_to_spice
from pyplecs.orchestration import SimulationOrchestrator
from pyplecs.orchestration.live import LivePlecsAdapter
from pyplecs.pyplecs import _is_plecs_xmlrpc_alive

from .verification.evidence import EvidenceBundle, utc_stamp
from .verification.manifest import REPO_ROOT, isolated_config
from .verification.oracle import summary_table
from .verification.spice import (
    MissingEvidenceError,
    asc_structure,
    compare_pair,
    dedupe_time,
    evaluate_expressions,
    ltspice_version,
    netlist_node_count,
    overlay_svg,
    read_ltspice_ascii_raw,
    run_ltspice,
)
from .verification.transports import through_python

pytestmark = pytest.mark.converter_acceptance

KNOWN_ASC_DEFECT = "#20: the .asc emitter wires symbol origins rather than pin offsets and omits the ground flag and gate source"


def _inbox(manifest) -> Path:
    return manifest.evidence_directory("spice")


async def _plecs_series(manifest, tmp_path):
    """PLECS is the reference: it must be live, never a stale recording."""
    host, port = manifest.endpoint
    if not _is_plecs_xmlrpc_alive(host, port, 3.0):
        raise MissingEvidenceError(f"PLECS is the reference for this comparison and {host}:{port} does not answer XML-RPC")
    config = isolated_config(tmp_path, manifest)
    orchestrator = SimulationOrchestrator(LivePlecsAdapter(config), config=config)
    try:
        return await through_python(orchestrator, manifest)
    finally:
        await orchestrator.stop()


def _decks(manifest, bundle: EvidenceBundle):
    circuit = parse_plecs(manifest.model_file)
    cir = bundle.directory / f"{manifest.model_name}.cir"
    asc = bundle.directory / f"{manifest.model_name}.asc"
    plecs_to_spice(circuit, cir)
    plecs_to_ltspice(circuit, asc)
    bundle.write_text(
        "conversion.md",
        f"```\nuv run pyplecs-convert {manifest.model_file.relative_to(REPO_ROOT).as_posix()} --format all -o {bundle.directory.relative_to(REPO_ROOT).as_posix()}\n```\n"
        f"Circuit Model: {len(circuit.components)} components, {len(circuit.nets)} nets.\n",
    )
    return circuit, cir, asc


def _export(manifest, deck: Path, kind: str) -> tuple[Path, Path]:
    """The LTspice export for one deck: run it when PYPLECS_LTSPICE is set, else expect it in the inbox."""
    inbox = _inbox(manifest)
    raw, log = inbox / f"{kind}.raw", inbox / f"{kind}.log"
    executable = os.environ.get("PYPLECS_LTSPICE")
    if executable:
        produced_raw, produced_log = run_ltspice(Path(executable), deck, inbox / f"run-{kind}")
        inbox.mkdir(parents=True, exist_ok=True)
        for produced, target in ((produced_raw, raw), (produced_log, log), (produced_raw.with_suffix(".net"), inbox / f"{kind}.net")):
            if produced.exists():
                shutil.copy(produced, target)
    if not raw.exists():
        raise MissingEvidenceError(
            f"missing LTspice export {raw.relative_to(REPO_ROOT)} — run `LTspice.exe -b -ascii {deck.name}` and copy the "
            f".raw there, or set PYPLECS_LTSPICE to the LTspice executable"
        )
    return raw, log


def _spice_payload(manifest, raw: Path):
    trace = read_ltspice_ascii_raw(raw)
    time, signals = dedupe_time(trace.time, evaluate_expressions(trace, manifest.data["spice"]["signals"]))
    return {"time": time.tolist(), "signals": {name: values.tolist() for name, values in signals.items()}}, trace.header


@pytest.mark.asyncio
async def test_emitted_cir_reproduces_plecs_steady_state_quantities(canonical_buck, tmp_path):
    manifest = canonical_buck
    bundle = EvidenceBundle(manifest.evidence_directory(utc_stamp() + "-converter"))
    bundle.write_json("manifest", manifest.data)
    _circuit, cir, _asc = _decks(manifest, bundle)
    plecs = await _plecs_series(manifest, tmp_path)
    raw, log = _export(manifest, cir, "cir")
    spice, header = _spice_payload(manifest, raw)

    report = compare_pair(plecs, spice, manifest)
    bundle.write_json("comparison", report)
    bundle.write_json(
        "environment",
        bundle.environment(
            plecs=f"live PLECS {manifest.plecs_version} at %s:%d" % manifest.endpoint,
            plecs_solver="radau, MaxStep 1e-6 (model settings)",
            ltspice=ltspice_version(log),
            ltspice_command=header.get("Command", ""),
            ltspice_directives=".tran 1e-3 (emitted), method trap (LTspice default)",
        ),
    )
    bundle.write_series("plecs", plecs["time"], plecs["signals"])
    bundle.write_series("spice_cir", spice["time"], spice["signals"])
    bundle.write_text("overlay.svg", overlay_svg(plecs, spice, manifest))
    bundle.write_text(
        "summary.md",
        f"# {manifest.model_name} / {manifest.operating_point_name} — emitted .cir versus PLECS\n\n"
        f"PLECS {manifest.plecs_version}. LTspice: {ltspice_version(log)}. Window: last {manifest.periods} periods at {manifest.switching_frequency:g} Hz.\n\n"
        f"**Verdict: {'PASS' if report['passed'] else 'FAIL'}** on steady-state Design Quantities.\n\n"
        + summary_table(report["comparison"])
        + "\n\n## Advisory (never asserted)\n\n"
        + f"Phase reference `{report['advisory']['reference']}`, lag {report['advisory']['lag_seconds']:.3g} s.\n\n"
        + "\n".join(f"- NRMSE {name}: {value:.3%}" for name, value in report["advisory"]["nrmse"].items())
        + "\n",
    )
    assert report["passed"], summary_table([row for row in report["comparison"] if not row["passed"]])


@pytest.mark.asyncio
async def test_emitted_asc_loads_runs_and_matches_key_scalars(canonical_buck, tmp_path):
    """Load/run checklist, two key scalars, structural counts. The known emitter defect is an xfail;
    a missing export or an unreachable PLECS is a plain failure."""
    manifest = canonical_buck
    bundle = EvidenceBundle(manifest.evidence_directory(utc_stamp() + "-converter-asc"))
    circuit, _cir, asc = _decks(manifest, bundle)
    asc_text = asc.read_text(encoding="utf-8")
    structure = asc_structure(asc_text)
    checklist = {
        "symbols_equal_circuit_model_components": structure["symbols"] == len(circuit.components),
        "has_ground_flag": structure["ground_flags"] >= 1,
        "has_gate_source": "V_GATE" in asc_text,
    }
    plecs = await _plecs_series(manifest, tmp_path)
    raw, log = _export(manifest, asc, "asc")
    net = raw.with_name("asc.net")
    if net.exists():
        checklist["nets_equal_circuit_model_nets"] = netlist_node_count(net.read_text(encoding="utf-8", errors="replace")) == len(circuit.nets)
    bundle.write_json(
        "asc_structure",
        {"asc": structure, "circuit_model": {"components": len(circuit.components), "nets": len(circuit.nets)}, "checklist": checklist},
    )

    def write_checklist(extra: str = "") -> None:
        bundle.write_text("asc_checklist.md", "".join(f"- {'✓' if ok else '✗'} {name}\n" for name, ok in checklist.items()) + extra)

    try:
        spice, _header = _spice_payload(manifest, raw)
        checklist["loads_and_runs"] = True
    except MissingEvidenceError as error:
        checklist["loads_and_runs"] = False
        write_checklist(f"- ✗ loads and runs: {error}\n")
        if not all(checklist.values()):
            pytest.xfail(f"{KNOWN_ASC_DEFECT}; LTspice: {error}")
        raise

    report = compare_pair(plecs, spice, manifest)
    scalars = {
        f"{signal}.{quantity}": {
            "plecs": report["plecs_quantities"][signal][quantity],
            "spice": report["spice_quantities"][signal][quantity],
            "passed": next(r["passed"] for r in report["comparison"] if r["signal"] == signal and r["quantity"] == quantity),
        }
        for signal, quantity in manifest.data["spice"]["asc_key_scalars"]
    }
    bundle.write_json("asc_scalars", scalars)
    write_checklist("".join(f"- {'✓' if s['passed'] else '✗'} {name}: PLECS {s['plecs']:.5g} / LTspice {s['spice']:.5g}\n" for name, s in scalars.items()))
    assert all(checklist.values()), checklist
    assert all(s["passed"] for s in scalars.values()), scalars
