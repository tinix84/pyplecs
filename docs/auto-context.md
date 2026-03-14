# PyPLECS — Auto-Context

> Auto-generated project summary. Last updated: 2026-02-24.

## Project Type

Python package (v1.0.0) — PLECS power electronics simulation automation framework.

## Package Structure

```
pyplecs/
├── __init__.py              # Package exports: PlecsServer, SimulationOrchestrator, etc.
├── pyplecs.py               # Core XML-RPC wrapper (PlecsServer, PlecsApp)
├── config.py                # YAML config management (search hierarchy)
├── core/
│   └── models.py            # Pydantic models (SimulationRequest, SimulationResult)
├── orchestration/
│   └── __init__.py          # Priority queue, batch execution, retry logic
├── cache/
│   └── __init__.py          # SHA256 hash-based result caching (Parquet/HDF5/CSV)
├── api/
│   └── __init__.py          # FastAPI REST endpoints (create_api_app)
├── webgui/
│   └── webgui.py            # Flask/Starlette dashboard with WebSocket updates
├── cli/
│   └── installer.py         # Setup wizard (pyplecs-setup)
├── mcp/                     # Model Context Protocol server (planned)
├── optimizer/               # Optimization algorithms
└── logging/                 # Structured logging
```

## Entry Points

| Command | Module | Purpose |
|---------|--------|---------|
| `pyplecs-setup` | `pyplecs.cli.installer:main` | Setup wizard |
| `pyplecs-gui` | `pyplecs.webgui:run_app` | Web dashboard |
| `pyplecs-api` | `pyplecs.api:main` | REST API server |
| `pyplecs-mcp` | `pyplecs.mcp:main` | MCP server (planned) |

## Dependencies

- **Runtime**: xmlrpc (stdlib), pydantic, fastapi, uvicorn, flask, pyyaml, pandas, pyarrow
- **Windows-only**: pywinauto (GUI automation), psutil (process priority)
- **Dev**: pytest, black, isort, flake8, mypy

## Configuration

- Default config: `config/default.yml`
- Search order: cwd -> parent dirs (3 levels) -> package dir -> `~/.pyplecs/config.yml`
- Key settings: PLECS path, XML-RPC port (1080), cache backend, concurrency (4)

## Test Structure

```
tests/
├── test_basic.py                      # Legacy automation tests
├── test_plecs_server_refactored.py    # Core API tests
├── test_orchestrator_batch.py         # Orchestration tests
├── test_refactored.py                 # Modern architecture
├── test_webgui.py                     # Web GUI tests
├── test_installer.py                  # Setup wizard (CI-safe)
├── test_entrypoint.py                 # Entry points (CI-safe)
├── test_install_full.py               # Full installation (CI-safe)
└── benchmark_batch_speedup.py         # Performance benchmarks
```

CI runs only platform-independent tests (installer, entrypoint, install_full) on Ubuntu.
PLECS XML-RPC tests require a running PLECS instance on Windows.

## Integration Context

- **Upstream**: NTBEES2 sends TAS (Topology Agnostic Structure) JSON
- **Downstream**: PLECS via XML-RPC on port 1080
- **Siblings**: PyMKF (magnetics), PyGecko (open-source sim, planned)

## Key Metrics

| Metric | Value |
|--------|-------|
| Batch speedup | 3-5x (vs sequential) |
| Cache speedup | 100-1000x (repeated simulations) |
| Concurrency | 4 parallel simulations (configurable) |
