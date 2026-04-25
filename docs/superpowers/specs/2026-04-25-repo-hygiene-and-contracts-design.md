# Repo Hygiene and Tool-Agnostic Contracts — Design

**Date:** 2026-04-25
**Status:** Approved (brainstorming)
**Scope:** four bundled cleanups (A: vendor ABCs, B: drop CI, C: ruff-only, D: articles → mkdocs)

## Context

PyPLECS sits inside a planned ecosystem where an umbrella orchestrator (PyCircuitSim, NTBEES2) interfaces with multiple simulation tools (PyPLECS, PyGecko, PyLTspice, ...). The umbrella expects each tool to satisfy a shared abstract contract. Today, `pyplecs` formally inherits from those contracts (commit `d1f0ccb`) but the contracts themselves are empty marker classes — PR #22 vendored stubs into `pycircuitsim_core/` so `pip install pyplecs` would not fail when the upstream `pycircuitsim-core` PyPI package was unavailable.

In parallel, three smaller forms of debt have accumulated:
- A GitHub Actions CI that runs only 3 of ~10 test files and provides little signal.
- Documentation/scripts that still reference `black`/`flake8`/`mypy`/`isort` even though `pyproject.toml` standardized on `ruff`.
- An `articles/` tree (LinkedIn posts, Substack drafts, diagrams, animations) bloating every checkout.

This spec bundles all four into one PR.

## Hard constraints

1. `pip install pyplecs` must work standalone, with no transitive dep on PyCircuitSim — ever.
2. `pyplecs` must not squat the top-level `pycircuitsim_core` import name. A user who later installs the upstream `pycircuitsim-core` from PyPI must not collide with our vendored copy.
3. Existing public imports — `from pyplecs import PlecsServer, SimulationRequest, SimulationResult, TaskPriority` — keep working unchanged.

## Item A — Vendor `pycircuitsim_core` ABCs at `pyplecs._contracts/`

### Source of truth
Upstream: [`tinix84/pycircuitsim`](https://github.com/tinix84/pycircuitsim) monorepo, path `packages/pycircuitsim-core/pycircuitsim_core/`. We port verbatim, pinned by commit SHA in a header on every vendored file.

### Layout

```
pyplecs/
├── _contracts/                      # vendored copy (private, hidden by underscore)
│   ├── __init__.py                  # exports same surface as upstream
│   ├── server.py                    # SimulationServer(ABC)
│   ├── cache.py                     # SimulationCacheBase(ABC)
│   ├── config.py                    # ConfigManagerBase(ABC)
│   ├── logging.py                   # StructuredLoggerBase
│   ├── orchestration.py             # SimulationOrchestratorBase(ABC)
│   └── models.py                    # TaskPriority, SimulationRequest, SimulationResult,
│                                    # SimulationStatus, SyncSimulationRequest, SyncSimulationResponse
└── contracts.py                     # PUBLIC façade with PyPI passthrough + version guard
```

The pre-existing top-level `pycircuitsim_core/` directory and the `pyproject.toml`
`include = ["...","pycircuitsim_core*"]` line are removed.

The vendored `_contracts/__init__.py` re-exports the same names as upstream
`pycircuitsim_core/__init__.py` **plus** `StructuredLoggerBase` (which upstream
defines in `logging.py` but omits from its `__all__`). Both export lists are
kept identical apart from this single addition; the SHA header makes the
divergence auditable on each re-sync.

### `pyplecs/contracts.py` — PyPI passthrough shim

```python
"""Stable namespace for shared simulation contracts.

Imports are tried in this order:
  1. The PyPI ``pycircuitsim-core`` package, if installed AND its contract
     version matches what pyplecs was tested against.
  2. The vendored copy at ``pyplecs._contracts``.

This means pyplecs works standalone (vendored) AND silently picks up the
canonical upstream package when the umbrella PyCircuitSim ecosystem is
present, as long as the contract is compatible.
"""

from __future__ import annotations

# Contract version pyplecs has been tested against. Bumped only when the
# vendored copy is re-synced from upstream.
__contract_version__ = "1.0"

try:
    import pycircuitsim_core as _ext  # PyPI package
    _ext_version = getattr(_ext, "__contract_version__", None) or _ext.__version__
    _major = _ext_version.split(".")[0]
    if _major != __contract_version__.split(".")[0]:
        raise ImportError(
            f"pycircuitsim-core {_ext_version} disagrees with pyplecs contract "
            f"{__contract_version__}; falling back to vendored copy"
        )
    from pycircuitsim_core import (
        SimulationServer, SimulationCacheBase, SimulationOrchestratorBase,
        ConfigManagerBase, StructuredLoggerBase,
        SimulationRequest, SimulationResult, SimulationStatus,
        SyncSimulationRequest, SyncSimulationResponse, TaskPriority,
    )
    _source = "pypi"
except ImportError:
    from pyplecs._contracts import (
        SimulationServer, SimulationCacheBase, SimulationOrchestratorBase,
        ConfigManagerBase, StructuredLoggerBase,
        SimulationRequest, SimulationResult, SimulationStatus,
        SyncSimulationRequest, SyncSimulationResponse, TaskPriority,
    )
    _source = "vendored"

__all__ = [
    "SimulationServer", "SimulationCacheBase", "SimulationOrchestratorBase",
    "ConfigManagerBase", "StructuredLoggerBase",
    "SimulationRequest", "SimulationResult", "SimulationStatus",
    "SyncSimulationRequest", "SyncSimulationResponse", "TaskPriority",
    "__contract_version__",
]
```

The `_source` private attribute is queryable for diagnostics. Upstream `pycircuitsim_core/__init__.py` must expose `__contract_version__`; our vendored copy is amended to do so during the port.

### Models — two flavors, no merge

**Audit finding (2026-04-25, during writing-plans):** upstream `pycircuitsim_core.models` is incompatible with `pyplecs/core/models.py` at the field level:

| Type | Upstream | pyplecs local |
|---|---|---|
| `SimulationRequest` | pydantic `BaseModel`, has `time_step` + `options` | dataclass, has `output_variables` + validates file existence in `__post_init__` |
| `SimulationResult` | pydantic, `time: list[float]` + `signals: dict[str, list[float]]` + `execution_time_ms` | dataclass, `timeseries_data: pd.DataFrame` + `execution_time` |
| `SimulationStatus` | `str, Enum` with uppercase values | plain `Enum` with lowercase values |
| `TaskPriority` | `Enum` | (current vendored stub uses `IntEnum`) |

Re-exporting from upstream would silently break every `result.timeseries_data` call site in pyplecs.

**Decision:** keep both flavors, distinct namespaces. **Do not modify** `pyplecs/core/models.py`. Instead:

- Vendored `_contracts/models.py` ships the **upstream flavor** verbatim. Reachable via `pyplecs.contracts.SimulationRequest` etc.
- Local `pyplecs/core/models.py` keeps the **pyplecs flavor** unchanged. Reachable via `pyplecs.SimulationRequest` etc. (existing public re-exports in `pyplecs/__init__.py` keep working).
- Concrete classes (`PlecsServer`, `SimulationCache`, ...) keep their existing method signatures using **local pyplecs types**. They inherit from contracts ABCs by name (already done in commit `d1f0ccb`); Python's `abstractmethod` machinery checks method *presence*, not signature equivalence, so instantiation succeeds even though static type-checkers would flag a signature mismatch.
- A future ecosystem-level adapter (when PyCircuitSim umbrella exists) is responsible for translating pyplecs-local model instances ↔ upstream model instances at the orchestrator boundary. **Out of scope for this spec.**

This honestly admits there's an unfinished interop gap, while satisfying the constraint that `from pyplecs import SimulationRequest` keeps working unchanged for existing users.

### Concrete-class adaptation

For each of `PlecsServer`, `SimulationCache`, `ConfigManager`, `StructuredLogger`, `SimulationOrchestrator`:

1. Update the import: `from pyplecs.contracts import <Base>` (no longer `from pycircuitsim_core ...`). The shim resolves to the vendored copy by default, the PyPI package when present and version-compatible.
2. Audit each abstract method declared on the base class against the concrete class. For methods present on both: leave the concrete method's existing signature unchanged (it operates on local pyplecs models). For methods declared abstract but missing on the concrete: add a minimal stub that delegates to the closest existing method or raises `NotImplementedError("Pending interop port — see spec 2026-04-25")`. **Do not** rewrite existing methods to match upstream signatures — that's the future interop work that's out of scope here.
3. Verify `Class.__abstractmethods__` is empty after the changes (Python's check during instantiation). If any abstract method has no concrete counterpart at all, add the `NotImplementedError` stub from step 2.

Specifically: upstream `SimulationServer` declares 4 abstract methods — `simulate`, `simulate_batch`, `is_available`, `health_check`. Existing `PlecsServer` already has all four (the latter two were added in commit `d1f0ccb`). Verify with `assert not PlecsServer.__abstractmethods__`. Repeat for the other four classes.

If any class ends up with more than 1–2 `NotImplementedError` stubs, that's a signal the contract doesn't fit and we should revisit upstream — but we expect 0 such stubs based on the d1f0ccb commit.

### Sync policy

- One file: `tools/SYNC_PYCIRCUITSIM_CORE.md` documents the source URL, current commit SHA, and the 3-step re-sync procedure (copy 7 files, update SHA in header, run contract tests).
- The vendored copy stays forever — no exit clause.
- If the upstream package contract bumps a major version (e.g., 1.x → 2.x), a re-sync is a deliberate decision that includes a contract-version bump and may break passthrough until pyplecs is also updated. The shim's version guard handles this gracefully by falling back to vendored.

### Tests

`tests/test_abc_contract.py` — runs without PLECS, included in the pre-push test list:

```python
def test_plecs_server_satisfies_simulation_server():
    from pyplecs import PlecsServer
    from pyplecs.contracts import SimulationServer
    assert issubclass(PlecsServer, SimulationServer)
    # Instantiation will raise TypeError if any @abstractmethod is unimplemented.
    # Use a no-op fake here; no XML-RPC connection needed.
    instance = PlecsServer.__new__(PlecsServer)  # bypass __init__
    # Verify methods exist with right names; deeper checks live in PLECS-required tests.

def test_contracts_source_reports_consistently():
    from pyplecs import contracts
    assert contracts._source in ("pypi", "vendored")

# Repeat for SimulationCache, ConfigManager, StructuredLogger, SimulationOrchestrator.
```

### Risk

- **Signature drift** — upstream ABC method signatures use upstream's pydantic models, while pyplecs concrete methods use pyplecs's local dataclass models. Mitigation: rely on Python's name-only abstractmethod check; defer signature reconciliation to a future ecosystem-level adapter. Static type-checkers (mypy, pyright) will warn — that's acceptable noise for now.
- **Passthrough silently broken by upstream** — version guard + `_source` diagnostic mitigate.
- **`__contract_version__` not present in upstream yet** — handled by the shim's `getattr(_ext, "__contract_version__", None) or _ext.__version__` fallback to the package's regular `__version__` (upstream already exposes `__version__ = "1.0.0"`). The vendored `_contracts/__init__.py` adds `__contract_version__` so pyplecs has an authoritative answer locally.

## Item B — Replace GitHub Actions CI with pre-push hook

| Action | Detail |
|---|---|
| Delete | `.github/workflows/ci.yml` |
| Modify | `.claude/hooks/pre_push_lint.py` runs `ruff check . && pytest -q tests/test_installer.py tests/test_entrypoint.py tests/test_install_full.py tests/test_abc_contract.py`; non-zero exit blocks push. |
| Modify | `CLAUDE.md` Decision Log: `2026-04-25 \| Remove GitHub Actions CI \| Single-maintainer project; pre-push hook covers lint + platform-independent tests; PLECS-dependent tests run manually on Windows.` |
| Modify | `README.md` — drop the CI badge if present; rewrite "Run Tests" sentences to describe the local hook. |
| Modify | `docs/contributing.md` — same. |

If the test list ever grows enough to be slow, the hook can be split into `pre_push_lint.py` (always) and `pre_push_test.py` (skippable with an env flag).

External contributors lose the green-checkmark feedback signal. Acceptable per user decision (single maintainer). The hook's test list is deliberately a shell-callable list so it can be lifted back into a workflow file mechanically if needed later.

## Item C — Unify lint on ruff

| File | Change |
|---|---|
| `.claude/skills.md` | Replace the `## Code Quality` block with a single `ruff check . && ruff format .`. Drop black/flake8/mypy/isort sub-sections. |
| `docs/contributing.md` | Same find/replace. |
| `README.md` | "Code Quality" section: ruff only. |
| `requirements-dev.txt` | Audit; drop `black`/`flake8`/`mypy`/`isort` lines if present. Keep `pytest`, `ruff`. |
| `pyproject.toml` | Already `[dev] = ["pytest", "ruff"]` — no change. |

No `.pre-commit-config.yaml` in the repo, so nothing else to update. CI workflow is deleted in Item B so its `flake8` invocation goes with it.

## Item D — Move `articles/` into `docs/articles/` for mkdocs

| Action | Detail |
|---|---|
| Move | `git mv articles/ docs/articles/` (preserves history). |
| Modify | `mkdocs.yml` — add `Articles:` nav section pointing at `articles/linkedin/`, `articles/substack/`, `articles/linkedin-posts/` (relative to `docs/`). |
| Add | `docs/articles/README.md` — lightweight section landing page. |
| Modify | `README.md` — any reference to `articles/...` becomes `docs/articles/...` or links to the deployed mkdocs URL. |
| Audit | `articles/diagrams/generate_all.py`, `articles/animations/generate_linkedin_gifs.py` — fix any hard-coded `articles/` paths to `docs/articles/`. |
| Verify | `.gitignore` does not ignore `docs/articles/*` after the move. |

### mkdocs build size watch

`articles/animations/*.gif` are large. If `mkdocs build` output exceeds a comfortable size for GitHub Pages:
- Option 1: add `exclude_docs: '*.gif'` and reference GIFs via raw GitHub URLs in the article markdown.
- Option 2: accept the size — Pages limit is 1 GB and per-file 100 MB, well above current GIF totals.

Decision deferred to first build measurement; defaulting to keeping GIFs in-tree.

### Build verification

`mkdocs build --strict` must succeed (catches broken links and missing nav entries). Strongly recommended addition to the pre-push hook from Item B.

## Implementation order — one PR, four commits

1. `chore: remove GitHub Actions CI in favor of pre-push hook` (B) — smallest, least risky.
2. `chore: unify lint on ruff` (C) — docs only, no behavior change.
3. `chore: move articles under docs/articles for mkdocs` (D) — git-rename + nav update.
4. `feat: vendor pycircuitsim_core ABCs at pyplecs._contracts with PyPI passthrough` (A) — largest diff, most likely to need iteration. If it gets blocked, the first three have already landed.

## Acceptance criteria

- `pip install -e .` from a clean venv succeeds with **no** mention of `pycircuitsim-core` in `pip` output.
- `pip install pycircuitsim-core==<future-pypi-version>` (when available) is picked up by `pyplecs.contracts._source == "pypi"`; if version-incompatible, `_source == "vendored"`.
- `pytest tests/test_abc_contract.py` passes with `pyplecs` installed alone.
- `ruff check .` and `ruff format --check .` pass.
- `mkdocs build --strict` succeeds and renders the Articles nav section.
- `git push` triggers the pre-push hook, which runs ruff + the 4 platform-independent test files (incl. `test_abc_contract.py`).
- No `.github/workflows/ci.yml` file remains.
- No top-level `pycircuitsim_core/` directory remains; `pyplecs/_contracts/` exists with the SHA-pinned vendored files.

## Out of scope

- Publishing `pycircuitsim-core` to PyPI (separate effort in `tinix84/pycircuitsim` monorepo).
- Reconciling pyplecs's local pydantic-incompatible models (`SimulationRequest`, `SimulationResult`, `SimulationStatus`, `TaskPriority`) with upstream's. The two flavors coexist in distinct namespaces; ecosystem-level interop is a future effort.
- Reviving CI as GitHub Actions if/when contributors return — explicitly deferred.
- Cleaning up `pyplecs/__init__.py`'s graceful-degradation `None` fallbacks for missing optional deps. Worth doing eventually, not in this spec.
