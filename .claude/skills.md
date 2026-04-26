# PyPLECS Skills Reference

Deterministic command sequences for common tasks. Use exact commands below.

## Testing

### Run All Tests
```bash
pytest
```

### Run Specific Module
```bash
pytest tests/test_basic.py          # Legacy automation
pytest tests/test_refactored.py     # Modern architecture
pytest tests/test_webgui.py         # Web GUI
pytest tests/test_installer.py      # Installer
```

### Run Single Test
```bash
pytest tests/test_basic.py::BasicTestSuite::test04_pyplecs_xrpc_server
```

### Run with Coverage
```bash
pytest --cov=pyplecs tests/
```

## Code Quality

### Lint
```bash
ruff check .
```

### Format
```bash
ruff format .
```

### Full quality check
```bash
ruff check . && ruff format --check .
```

## Services

### Start Web GUI
```bash
pyplecs-gui
```

### Start REST API
```bash
pyplecs-api
```

### Start MCP Server
```bash
pyplecs-mcp
```

## Installation

### Dev Install
```bash
pip install -e .
```

### Setup Wizard
```bash
pyplecs-setup
```

### Windows Full Install
```bash
tools\installers\windows_installer.bat --yes --plecs-path "C:\Program Files\Plexim\PLECS 4.7 (64 bit)\plecs.exe"
```

## Key Files

| Purpose | Path |
|---------|------|
| Config | `config/default.yml` |
| Core PLECS wrapper | `pyplecs/pyplecs.py` |
| Data models (pyplecs-local) | `pyplecs/core/models.py` |
| Tool-agnostic ABC façade | `pyplecs/contracts.py` |
| Vendored ABCs (pinned) | `pyplecs/_contracts/` |
| Orchestration | `pyplecs/orchestration/__init__.py` |
| Cache | `pyplecs/cache/__init__.py` |
| REST API | `pyplecs/api/__init__.py` |
| Web GUI | `pyplecs/webgui/webgui.py` |
| Pre-push hook | `.claude/hooks/pre_push_lint.py` |
| Re-sync vendored ABCs | `tools/SYNC_PYCIRCUITSIM_CORE.md` |
| ABC compliance test | `tests/test_abc_contract.py` |

## Code Patterns

### Single Simulation
```python
from pyplecs import PlecsServer
with PlecsServer("model.plecs") as server:
    results = server.simulate({"Vi": 12.0, "Vo": 5.0})
```

### Batch Simulation (3-5x faster)
```python
with PlecsServer("model.plecs") as server:
    results = server.simulate_batch([
        {"Vi": 12.0}, {"Vi": 24.0}, {"Vi": 48.0}
    ])
```

### Orchestrated Simulation
```python
from pyplecs import SimulationOrchestrator, SimulationRequest
from pyplecs.orchestration import TaskPriority

request = SimulationRequest(
    model_file="model.plecs",
    parameters={"Vi": 12.0},
    output_variables=["Vo", "IL"]
)
task_id = await orchestrator.submit_simulation(request, priority=TaskPriority.HIGH)
result = await orchestrator.wait_for_completion(task_id)
```

### Tool-Agnostic Contracts (pyplecs.contracts)
```python
from pyplecs.contracts import (
    SimulationServer, SimulationCacheBase, SimulationOrchestratorBase,
    ConfigManagerBase, StructuredLoggerBase,
    SimulationRequest, SimulationResult, SimulationStatus, TaskPriority,
)
# Resolves to PyPI pycircuitsim_core if installed and major-version-compatible,
# otherwise to pyplecs._contracts. Diagnostic via `from pyplecs import contracts; contracts._source`.
```

## Entry Points

| Command | Module |
|---------|--------|
| `pyplecs-setup` | `pyplecs.cli.installer:main` |
| `pyplecs-gui` | `pyplecs.webgui:run_app` |
| `pyplecs-api` | `pyplecs.api:main` |
