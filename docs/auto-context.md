# PyPLECS — Auto-Context

> Auto-generated project summary. Last updated: 2026-04-26.

## Project Type

Python package (v1.0.0) — PLECS power electronics simulation automation framework. Standalone-installable; no transitive dependency on the umbrella `pycircuitsim-core` package.

## Package Structure

```
pyplecs/
├── __init__.py              # Public exports: PlecsServer, SimulationOrchestrator,
│                            # SimulationCache, SimulationRequest, SimulationResult,
│                            # TaskPriority, get_config, get_logger, etc.
├── pyplecs.py               # Core XML-RPC wrapper (PlecsServer, PlecsApp)
├── contracts.py             # Public façade for shared simulation ABCs.
│                            # Prefers external pycircuitsim_core when installed
│                            # AND major-version-compatible; falls back to vendored
│                            # copy below. Reports source via _source attribute.
├── _contracts/              # Vendored copy of pycircuitsim_core ABCs.
│   ├── __init__.py          # Exports SimulationServer, SimulationCacheBase, etc.
│   │                        # Pinned to tinix84/pycircuitsim@<sha> (header in each
│   │                        # file). __contract_version__ = "1.0".
│   ├── server.py            # SimulationServer ABC
│   ├── cache.py             # SimulationCacheBase ABC + compute_hash helper
│   ├── config.py            # ConfigManagerBase ABC + shared config dataclasses
│   ├── logging.py           # StructuredLoggerBase ABC
│   ├── orchestration.py     # SimulationOrchestratorBase ABC
│   └── models.py            # Pydantic SimulationRequest, SimulationResult,
│                            # SimulationStatus, TaskPriority, SyncSimulationRequest,
│                            # SyncSimulationResponse
├── config.py                # YAML config management (search hierarchy)
├── core/
│   └── models.py            # pyplecs-local dataclass models (SimulationRequest,
│                            # SimulationResult, ComponentParameter, OptimizationRequest,
│                            # OptimizationResult). Distinct namespace from
│                            # pycircuitsim_core.models — see spec for rationale.
├── orchestration/
│   └── __init__.py          # SimulationOrchestrator: priority queue, batch
│                            # execution, retry logic. Inherits SimulationOrchestratorBase.
├── cache/
│   └── __init__.py          # SimulationCache: SHA256-keyed result caching
│                            # (Parquet/HDF5/CSV). Inherits SimulationCacheBase.
├── api/
│   ├── __init__.py          # FastAPI REST endpoints (create_api_app)
│   └── simulation_sync.py   # Sync simulation endpoint
├── webgui/
│   ├── __init__.py
│   ├── webgui.py            # Flask/Starlette dashboard with WebSocket updates
│   ├── static/
│   └── templates/
├── cli/
│   ├── __init__.py
│   └── installer.py         # Setup wizard (pyplecs-setup)
├── mcp/                     # Model Context Protocol server (planned, gracefully degraded)
├── optimizer/               # Optimization algorithms (planned, gracefully degraded)
└── logging/
    └── __init__.py          # StructuredLogger inheriting StructuredLoggerBase
```

## Entry Points

| Command | Module | Purpose |
|---------|--------|---------|
| `pyplecs-setup` | `pyplecs.cli.installer:main` | Setup wizard |
| `pyplecs-gui` | `pyplecs.webgui:run_app` | Web dashboard |
| `pyplecs-api` | `pyplecs.api:main` | REST API server |
| `pyplecs-mcp` | `pyplecs.mcp:main` | MCP server (planned) |

## Dependencies

- **Runtime** (`pyproject.toml` `[project].dependencies`): numpy, scipy, pandas, pyyaml, pydantic>=2.0, structlog>=21.1.0, click>=8.0.0, python-dotenv>=0.19.0, packaging>=21.0. **No `pycircuitsim-core`** — the ABC layer is vendored at `pyplecs/_contracts/`.
- **Optional `[web]` extras**: fastapi, uvicorn, jinja2, aiofiles, websockets, python-multipart, plotly, rich, tqdm.
- **Windows-only (not declared)**: pywinauto (GUI automation via `PlecsApp`), psutil (process priority). Missing → public `PlecsServer`/`PlecsApp` exports become `None`.
- **Dev** (`requirements-dev.txt`): pytest, pytest-asyncio, pytest-cov, **ruff** (single tool for lint + format), mkdocs, mkdocs-material.

## Configuration

- Default config: `config/default.yml`
- Search order (in `pyplecs/config.py`): cwd → parent dirs (3 levels up) → package dir → `~/.pyplecs/config.yml` → `/etc/pyplecs/config.yml`.
- Key settings: PLECS executable path, XML-RPC port (1080), cache backend (file/Redis/memory), max concurrent simulations (4).

## Test Structure

```
tests/
├── test_abc_contract.py             # ABC compliance — runs without PLECS
├── test_installer.py                # Setup wizard (no PLECS)
├── test_entrypoint.py               # Entry points (no PLECS)
├── test_install_full.py             # Full installation (no PLECS)
├── test_basic.py                    # Legacy automation (Windows + PLECS)
├── test_plecs_server_refactored.py  # Core API (Windows + PLECS)
├── test_orchestrator_batch.py       # Orchestration (Windows + PLECS)
├── test_refactored.py               # Modern architecture (Windows + PLECS)
├── test_webgui.py                   # Web GUI (Windows + PLECS)
└── benchmark_batch_speedup.py       # Performance benchmarks
```

**Pre-push enforcement** (`.claude/hooks/pre_push_lint.py`): runs `ruff check .` + the 4 platform-independent test files (`test_installer.py`, `test_entrypoint.py`, `test_install_full.py`, `test_abc_contract.py`) on `git push`. No GitHub Actions CI.

## Public Façade for Tool-Agnostic Contracts

`pyplecs.contracts` is the stable public namespace for shared simulation ABCs and pydantic models. Resolution order:

1. PyPI `pycircuitsim_core` if importable AND major-version-compatible (`__contract_version__` or `__version__` major matches `1`).
2. Vendored `pyplecs._contracts` (always works, ships with pyplecs).

`contracts._source` reports `"pypi"` or `"vendored"`. If a partial PyPI install is detected (importable but missing names), the shim falls back to vendored automatically.

Re-sync procedure for the vendored copy: `tools/SYNC_PYCIRCUITSIM_CORE.md`.

## Documentation

- Static site: built via `mkdocs build`, deployed to https://tinix84.github.io/pyplecs/.
- Articles (LinkedIn, Substack, diagrams) live at `docs/articles/` so they ship with the site.
- Specs: `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`.
- Plans: `docs/superpowers/plans/YYYY-MM-DD-<topic>.md`.

## Integration Context

- **Upstream**: NTBEES2 sends TAS (Topology Agnostic Structure) JSON.
- **Downstream**: PLECS via XML-RPC on port 1080.
- **Sibling tools** (planned via shared `pycircuitsim_core` ABC contract): PyMKF (magnetics), PyGeckoCircuit (open-source sim).
- **Umbrella**: `tinix84/pycircuitsim` monorepo coordinates the shared ABC contract; PyPLECS stays standalone-installable.

## Key Metrics

| Metric | Value |
|--------|-------|
| Batch speedup | 3–5x (vs sequential, via PLECS native parallel API) |
| Cache speedup | 100–1000x (repeated simulations) |
| Concurrency | 4 parallel simulations (configurable) |
