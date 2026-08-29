"""Opt-in live proof: the canonical buck answer holds up on the installed PLECS (ADR-0013).

    uv run pytest -m live_plecs
"""

import json

import pytest

from pyplecs.orchestration import SimulationOrchestrator
from pyplecs.orchestration.live import LivePlecsAdapter

from .verification.evidence import EvidenceBundle, utc_stamp
from .verification.oracle import (
    analytic_invariants,
    check_preconditions,
    compare_quantities,
    payload_to_result,
    steady_state_quantities,
    summary_table,
)
from .verification.transports import through_python

pytestmark = pytest.mark.live_plecs


@pytest.mark.asyncio
async def test_python_api_answer_holds_up_against_physics_and_the_recorded_reference(live_config, canonical_buck):
    manifest = canonical_buck
    orchestrator = SimulationOrchestrator(LivePlecsAdapter(live_config), config=live_config)
    try:
        payload = await through_python(orchestrator, manifest)
        result = payload_to_result(payload)
    finally:
        await orchestrator.stop()

    window = check_preconditions(result, manifest)
    quantities = steady_state_quantities(result, manifest, window)
    invariants = analytic_invariants(quantities, manifest)

    reference_path = manifest.reference_path()
    first_recording = not reference_path.exists()
    if first_recording:
        reference_path.write_text(
            json.dumps({"plecs_version": manifest.plecs_version, "window": window.to_dict(), "quantities": quantities}, indent=2)
            + "\n",
            encoding="utf-8",
        )
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    comparison = compare_quantities(quantities, reference["quantities"], manifest)

    bundle = EvidenceBundle(manifest.evidence_directory(utc_stamp()))
    bundle.write_json("manifest", manifest.data)
    bundle.write_json(
        "environment",
        bundle.environment(
            plecs_version=manifest.plecs_version,
            endpoint="%s:%d" % manifest.endpoint,
            raw_result={"samples": len(payload["time"]), "signals": len(payload["signals"]), "time_span": [payload["time"][0], payload["time"][-1]]},
        ),
    )
    bundle.write_json("quantities", {"window": window.to_dict(), "quantities": quantities, "invariants": invariants, "comparison": comparison})
    bundle.write_series("python", payload["time"], payload["signals"])
    bundle.write_text(
        "summary.md",
        f"# {manifest.model_name} / {manifest.operating_point_name} — Python API\n\n"
        f"PLECS {manifest.plecs_version}; {'reference recorded' if first_recording else 'compared to recorded reference'}.\n\n"
        "## Analytic invariants\n\n"
        + "\n".join(f"- {'✓' if c['passed'] else '✗'} {c['check']} (value {c['value']:.6g})" for c in invariants)
        + "\n\n## Steady-state Design Quantities vs reference\n\n"
        + summary_table(comparison)
        + "\n",
    )

    failed_invariants = [c for c in invariants if not c["passed"]]
    assert not failed_invariants, failed_invariants
    failed = [r for r in comparison if not r["passed"]]
    assert not failed, summary_table(failed)
