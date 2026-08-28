# ADR-0013 — Live verification is opt-in and metric-based

- **Status**: Accepted
- **Date**: 2026-08-28

## Context

PyPLECS answers through three transports — the Python API, the REST API and the
Simulation MCP Server — and emits `.cir`/`.asc` netlists through the Circuit
Model. Until Band 4 nothing proved that the answer *holds up*: that one
Operating Point yields the same, physically credible Simulation Result whichever
transport carried it, on the PLECS actually installed, and that a converted
netlist is the same circuit. The live checks that existed were one-off
environment-variable scripts, and `pyplecs-mcp-sim` had only ever met a fake
`PlecsServer`.

Three forces constrain how such proof can be built:

- PLECS is licensed and host-bound. It is not in generic CI and must never be
  assumed by the default `uv run pytest` or by the pre-push gate (ADR-0004's
  gate must stay runnable by anyone).
- Waveform samples are not stable identities. A solver or PLECS-version change
  moves step placement without changing the circuit; a sample-by-sample golden
  would fail on every upgrade and pass on a wrong Signal Map.
- The second simulator for converter acceptance (LTspice, ngspice) is run by a
  person. A check that silently skips when its input is missing is
  indistinguishable from a pass.

## Decision

1. **Selection by marker, deselected by default.** Everything that talks to
   PLECS carries the `live_plecs` pytest marker; the semi-manual converter pack
   carries `converter_acceptance`. Both are excluded by the default
   configuration and run only when named: `uv run pytest -m live_plecs`,
   `uv run pytest -m converter_acceptance`. Neither ever joins the pre-push gate.
2. **Availability is probed, never assumed, never launched.** A live test
   probes the configured XML-RPC endpoint once and skips with host and port in
   its reason. Tests do not auto-launch PLECS.
3. **Isolation.** Live tests build their own `ConfigManager` with no discovery
   paths, a temporary cache directory and the manifest's PLECS version; they
   never read the machine's `config/default.yml`.
4. **The canonical Operating Point is data.** One tracked manifest names the
   model, the Operating Point, the Signal Map for every probe output, the
   required signals, the steady-state window, the tolerances and the observed
   PLECS facts. Every transport and the converter pack compare the same thing.
5. **Metrics decide, samples inform.** Pass/fail rests on stable invariants —
   strictly increasing time, at least five complete periods, required signals
   present and finite, per-period RMS convergence, analytic bounds a reader can
   check by hand — and on time-weighted mean/RMS/min/max/peak-to-peak of the
   last five switching periods compared to a *recorded reference* within stated
   tolerances (mean/RMS 2 %, min/max 5 %, peak-to-peak 10 %, absolute floors
   10 mA / 50 mV). Sample-level differences and phase-aligned NRMSE are
   recorded as evidence, never asserted.
6. **Fail closed; never skip on missing evidence.** A precondition failure names
   its cause and no comparison is made. The converter pack fails naming the
   export file it expected; a defect it exposes is reported on the converter
   issue, not patched around in the pack.
7. **Every acceptance run leaves an Evidence Bundle** under the tests tree:
   manifest snapshot, tool versions, metrics, machine-readable comparison,
   human-readable summary and overlay. Raw series and overlays are untracked;
   manifests, references and summaries are tracked so a reviewer can sign off
   without re-running.

## Consequences

- Verification code lives under `tests/`; it reuses the Design Quantities
  window and time-weighted math (ADR-0012) and adds no runtime API.
- The default suite proves the harness itself (selection, skip reason,
  isolation, oracle on synthetic waveforms, export reader, comparator) with
  in-memory adapters, so `uv run pytest` covers the verification code without
  PLECS.
- Tolerances are provisional until two recorded runs on pinned PLECS and
  LTspice versions exist; the Evidence Bundle is how they are calibrated and
  then frozen in the manifest.
- Cross-transport equivalence is asserted on metrics within 0.1 %, even though
  PLECS proved deterministic (max |Δsample| = 0) — determinism is evidence, not
  a contract.
- To supersede this: a hosted, licensed PLECS reachable from CI would allow the
  live marker to gate merges; a stable sample-level identity across PLECS
  versions would allow goldens. Neither exists today.
