# ADR-0003 — Only contracts are promotable to pycircuitsim-core

- **Status**: Accepted
- **Date**: 2026-08-19

## Context

`CLAUDE.md` carries a hard rule: PyPLECS is standalone and
`pycircuitsim-core` is never added to `pyproject.toml` dependencies. The
mechanism is `pyplecs.contracts`, a façade that prefers an installed,
major-version-compatible PyPI `pycircuitsim_core` and otherwise falls back to
the vendored copy at `pyplecs/_contracts/`.

`#13` (mission profile → weighted operating points) proposed that the converter
"may be promoted to `pycircuitsim-core` to serve multiple simulator backends".
Taken literally that either adds the forbidden dependency, or vendors an
implementation.

The vendored package holds only ABCs, dataclasses and enums —
`SimulationCacheBase`, `SimulationRequest`, `SimulationResult`,
`SimulationOrchestratorBase`, the config and logging bases. Vendoring works
because a contract duplicated verbatim cannot drift in behaviour. An
implementation duplicated verbatim is just duplicated code.

## Decision

Only **contracts** — abstract base classes, dataclasses, enums, protocols — are
promotable to `pycircuitsim-core`. Implementations stay in PyPLECS permanently.

For `#13` specifically: `WeightedOPTable` (the shape) is promotable and would
join the vendored contracts behind the `pyplecs.contracts` façade;
`mission_profile_to_histogram` (the code) is not.

## Consequences

- The standalone rule survives ecosystem growth — no optional extra, no
  degrade-to-`None` path, no new dependency.
- Sharing behaviour across simulator backends requires each backend to implement
  the shared contract, not to import PyPLECS code.
- Any future issue proposing to "move X to pycircuitsim-core" must first say
  whether X is a contract or an implementation.
