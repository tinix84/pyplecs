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

### Format
```bash
black pyplecs/
```

### Lint
```bash
flake8 pyplecs/
```

### Type Check
```bash
mypy pyplecs/
```

### Sort Imports
```bash
isort pyplecs/
```

### Full Quality Check
```bash
black pyplecs/ && isort pyplecs/ && flake8 pyplecs/ && mypy pyplecs/
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
| Data models | `pyplecs/core/models.py` |
| Orchestration | `pyplecs/orchestration/__init__.py` |
| Cache | `pyplecs/cache/__init__.py` |
| REST API | `pyplecs/api/__init__.py` |
| Web GUI | `pyplecs/webgui/webgui.py` |

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

## Entry Points

| Command | Module |
|---------|--------|
| `pyplecs-setup` | `pyplecs.cli.installer:main` |
| `pyplecs-gui` | `pyplecs.webgui:main` |
| `pyplecs-api` | `pyplecs.api:main` |
| `pyplecs-mcp` | `pyplecs.mcp:main` |
