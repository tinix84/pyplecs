# ADR-0006 — Two model flavors, no merge

- **Status**: Accepted
- **Date**: 2026-08-20

## Context

ADR-0003 settled what may be promoted to `pycircuitsim-core`: contracts, never
implementations. It did not settle what happens when a vendored contract's data
models disagree with the ones PyPLECS already uses.

They disagree at the field level. An audit during the contracts work found:

| Type | Vendored (upstream flavor) | `pyplecs/core/models.py` |
|---|---|---|
| `SimulationRequest` | pydantic `BaseModel`; `time_step`, `options` | dataclass; `output_variables`, validates file existence in `__post_init__` |
| `SimulationResult` | pydantic; `time: list[float]`, `signals: dict[str, list[float]]`, `execution_time_ms` | dataclass; `timeseries_data: pd.DataFrame`, `execution_time` |
| `SimulationStatus` | `str, Enum`, uppercase values | plain `Enum`, lowercase values |
| `TaskPriority` | `Enum` | `IntEnum` |

Re-exporting the upstream flavor would break every `result.timeseries_data`
call site in PyPLECS. Rewriting the vendored copy would defeat the point of
vendoring — a contract only stays trustworthy while it is verbatim.

## Decision

**Both flavors ship, in distinct namespaces, and neither is rewritten to match
the other.**

- `pyplecs.contracts.SimulationRequest` and friends resolve to the upstream
  flavor — the installed PyPI `pycircuitsim_core` when major-version
  compatible, the verbatim vendored copy at `pyplecs/_contracts/` otherwise.
- `pyplecs.SimulationRequest` and friends stay the local flavor, unchanged.
  `pyplecs/core/models.py` is not modified.
- Concrete classes (`PlecsServer`, `SimulationCache`, `ConfigManager`,
  `StructuredLogger`, `SimulationOrchestrator`) inherit from the contract ABCs
  by name while keeping their existing signatures over local types.

This works because Python's `@abstractmethod` machinery checks method
*presence*, not signature compatibility, so instantiation succeeds. It is
deliberately exploited, not accidental.

Translating between the two flavors is the job of a future ecosystem-level
adapter at the orchestrator boundary. It is not built, and this ADR does not
commit to building it.

## Consequences

- `from pyplecs import SimulationRequest` keeps working unchanged for existing
  users. That constraint is what forced the decision.
- Static type checkers will flag signature mismatches between each contract ABC
  and its concrete implementation. That warning noise is accepted; the runtime
  contract is name-level only.
- The interop gap is real and admitted: nothing today converts a local
  `SimulationResult` into an upstream one. Code that needs both must convert by
  hand.
- `tests/test_abc_contract.py` guards the name-level contract and runs without
  PLECS, so it is in the pre-push gate.
- If a future re-sync makes the flavors converge, this ADR can be superseded by
  one that merges them — but it must then handle every `timeseries_data` call
  site.
