"""Opt-in live proof: the canonical buck answer holds up on the installed PLECS (ADR-0013).

    uv run pytest -m live_plecs
"""

import json

import pytest

from pyplecs.core.models import SimulationRequest
from pyplecs.orchestration import SimulationOrchestrator
from pyplecs.orchestration.live import LivePlecsAdapter

from .verification.evidence import EvidenceBundle, utc_stamp
from .verification.oracle import (
    analytic_invariants,
    check_preconditions,
    compare_metrics,
    result_payload,
    steady_state_metrics,
    summary_table,
)

pytestmark = pytest.mark.live_plecs


async def run_canonical_point(orchestrator, manifest, *, use_cache=False):
    request = SimulationRequest(
        model_file=str(manifest.model_file),
        parameters=manifest.parameters,
        output_variables=manifest.signals,
    )
    task_id = await orchestrator.submit_simulation(request, use_cache=use_cache)
    snapshot = await orchestrator.wait_for_completion(task_id, timeout=120)
    assert snapshot is not None and snapshot.status.value == "completed", snapshot
    return snapshot.result


@pytest.mark.asyncio
async def test_python_api_answer_holds_up_against_physics_and_the_recorded_reference(live_config, canonical_buck):
    manifest = canonical_buck
    orchestrator = SimulationOrchestrator(LivePlecsAdapter(live_config), config=live_config)
    try:
        result = await run_canonical_point(orchestrator, manifest)
    finally:
        await orchestrator.stop()

    window = check_preconditions(result, manifest)
    metrics = steady_state_metrics(result, manifest, window)
    invariants = analytic_invariants(metrics, manifest)

    reference_path = manifest.reference_path()
    first_recording = not reference_path.exists()
    if first_recording:
        reference_path.write_text(
            json.dumps({"plecs_version": manifest.plecs_version, "window": window.to_dict(), "metrics": metrics}, indent=2)
            + "\n",
            encoding="utf-8",
        )
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    comparison = compare_metrics(metrics, reference["metrics"], manifest)

    payload = result_payload(result)
    bundle = EvidenceBundle(manifest.evidence_directory(utc_stamp()))
    bundle.write_json("manifest", manifest.data)
    bundle.write_json(
        "environment",
        bundle.environment(
            plecs_version=manifest.plecs_version,
            endpoint="%s:%d" % manifest.endpoint,
            raw_result={"samples": len(payload["time"]), "signals": len(payload["signals"]), "time_span": [payload["time"][0], payload["time"][-1]]},
            execution_time_s=result.execution_time,
        ),
    )
    bundle.write_json("metrics", {"window": window.to_dict(), "metrics": metrics, "invariants": invariants, "comparison": comparison})
    bundle.write_series("python", payload["time"], payload["signals"])
    bundle.write_text(
        "summary.md",
        f"# {manifest.model_name} / {manifest.operating_point_name} — Python API\n\n"
        f"PLECS {manifest.plecs_version}; {'reference recorded' if first_recording else 'compared to recorded reference'}.\n\n"
        "## Analytic invariants\n\n"
        + "\n".join(f"- {'✓' if c['passed'] else '✗'} {c['check']} (value {c['value']:.6g})" for c in invariants)
        + "\n\n## Steady-state metrics vs reference\n\n"
        + summary_table(comparison)
        + "\n",
    )

    failed_invariants = [c for c in invariants if not c["passed"]]
    assert not failed_invariants, failed_invariants
    failed_metrics = [r for r in comparison if not r["passed"]]
    assert not failed_metrics, summary_table(failed_metrics)
