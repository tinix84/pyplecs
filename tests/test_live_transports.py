"""Opt-in live proof: Python, REST and a real MCP client session agree on the canonical buck (ADR-0013).

    uv run pytest -m live_plecs
"""

import numpy as np
import pytest

from pyplecs.orchestration import SimulationOrchestrator
from pyplecs.orchestration.live import LivePlecsAdapter

from .verification.evidence import EvidenceBundle, utc_stamp
from .verification.oracle import (
    QUANTITY_FIELDS,
    check_preconditions,
    compare_quantities,
    payload_to_result,
    steady_state_quantities,
    summary_table,
)
from .verification.transports import (
    mcp_client,
    rest_app,
    through_mcp,
    through_python,
    through_rest_async,
    through_rest_sync,
)

pytestmark = pytest.mark.live_plecs

LIFECYCLE_TOOLS = {"simulation_submit", "simulation_status", "simulation_wait", "simulation_result", "simulation_cancel", "simulation_list"}


def _quantities(payload, manifest):
    result = payload_to_result(payload)
    return steady_state_quantities(result, manifest, check_preconditions(result, manifest))


@pytest.mark.asyncio
async def test_every_transport_returns_the_same_normalized_answer(live_config, canonical_buck):
    manifest = canonical_buck
    orchestrator = SimulationOrchestrator(LivePlecsAdapter(live_config), config=live_config)
    app = rest_app(orchestrator, live_config)
    answers = {}
    try:
        answers["python"] = await through_python(orchestrator, manifest)
        answers["rest_async"] = await through_rest_async(app, manifest)
        answers["rest_sync"] = await through_rest_sync(app, manifest, live_config.api.prefix)
        async with mcp_client(orchestrator) as session:
            tools = {tool.name for tool in (await session.list_tools()).tools}
            assert LIFECYCLE_TOOLS <= tools, tools
            answers["mcp"] = await through_mcp(session, manifest)
    finally:
        await orchestrator.stop()

    reference = _quantities(answers["python"], manifest)
    agreement = float(manifest.tolerances["transport_agreement"])
    report, failures = {}, []
    for transport, payload in answers.items():
        assert list(payload["signals"]) == manifest.signals, (transport, list(payload["signals"]))
        assert len(payload["time"]) == len(answers["python"]["time"]), (transport, len(payload["time"]))
        # the relative agreement applies to every quantity: no absolute floors here
        rows = compare_quantities(
            _quantities(payload, manifest),
            reference,
            manifest,
            relative={field: agreement for field in QUANTITY_FIELDS},
            absolute_floor={},
        )
        max_abs_diff = max(
            float(np.max(np.abs(np.asarray(payload["signals"][name]) - np.asarray(answers["python"]["signals"][name]))))
            for name in manifest.signals
        )
        report[transport] = {"samples": len(payload["time"]), "max_abs_sample_diff": max_abs_diff, "comparison": rows}
        failures += [{"transport": transport, **row} for row in rows if not row["passed"]]

    bundle = EvidenceBundle(manifest.evidence_directory(utc_stamp() + "-transports"))
    bundle.write_json("manifest", manifest.data)
    bundle.write_json("environment", bundle.environment(plecs_version=manifest.plecs_version, endpoint="%s:%d" % manifest.endpoint))
    bundle.write_json("transports", report)
    for transport, payload in answers.items():
        bundle.write_series(transport, payload["time"], payload["signals"])
    bundle.write_text(
        "summary.md",
        f"# {manifest.model_name} / {manifest.operating_point_name} — cross-transport equivalence\n\n"
        + "\n".join(
            f"- {name}: {entry['samples']} samples, max |Δsample| vs Python = {entry['max_abs_sample_diff']:.3g}, "
            f"Design Quantities within {agreement:.1%}: {'✓' if all(r['passed'] for r in entry['comparison']) else '✗'}"
            for name, entry in report.items()
        )
        + "\n",
    )
    assert not failures, summary_table(failures)


@pytest.mark.asyncio
async def test_a_second_transport_hits_the_cache_record_the_first_one_wrote(live_config, canonical_buck):
    manifest = canonical_buck
    orchestrator = SimulationOrchestrator(LivePlecsAdapter(live_config), config=live_config)
    try:
        first = await through_python(orchestrator, manifest, use_cache=True)
        async with mcp_client(orchestrator) as session:
            second = await through_mcp(session, manifest, use_cache=True)
    finally:
        await orchestrator.stop()
    assert first["cached"] is False and second["cached"] is True
    assert second["time"] == first["time"] and second["signals"] == first["signals"]
