# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PyPLECS is a Python automation framework for PLECS (power electronics simulation) with two architectural layers:
1. **Legacy layer**: Direct GUI automation via pywinauto for controlling PLECS desktop application
2. **Modern layer**: REST API, web UI, caching, and orchestration for scalable simulation workflows

The project underwent major refactoring (commit b96a69d) to add modern capabilities while maintaining backward compatibility.

## Development Commands

### Installation & Setup

```bash
# Install package in development mode
pip install -e .

# Install from requirements.txt
pip install -r requirements.txt

# Run installer/setup wizard (creates config, checks PLECS paths)
pyplecs-setup
# Or on Windows with advanced features:
tools\installers\windows_installer.bat --yes --plecs-path "C:\Program Files\Plexim\PLECS 4.7 (64 bit)\plecs.exe"
```

### Testing

```bash
# Run all tests
pytest

# Run specific test modules
pytest tests/test_basic.py          # Legacy automation tests
pytest tests/test_refactored.py     # Modern architecture tests
pytest tests/test_webgui.py         # Web GUI tests
pytest tests/test_installer.py      # Installer tests

# Run with coverage
pytest --cov=pyplecs tests/

# Run single test
pytest tests/test_basic.py::BasicTestSuite::test04_pyplecs_xrpc_server
```

### Running Services

```bash
# Start web GUI
pyplecs-gui
# Or directly:
python -m pyplecs.webgui
python start_webgui.py

# Start REST API server
pyplecs-api
# Or directly:
python -m pyplecs.api

# Start MCP server (Model Context Protocol)
pyplecs-mcp
# Or directly:
python -m pyplecs.mcp
```

### Code Quality

```bash
# Format code with black
black pyplecs/

# Check with flake8
flake8 pyplecs/

# Type checking with mypy
mypy pyplecs/

# Sort imports with isort
isort pyplecs/
```

## Architecture Overview

### Refactored Design (v1.0.0)

**Core Layer** (`pyplecs/pyplecs.py`, `pyplecs/plecs_components.py`):
- Thin wrapper around PLECS XML-RPC (PlecsServer class)
- Batch parallel simulation support via PLECS native API (simulate_batch)
- Windows-only GUI automation using pywinauto (PlecsApp class)
- Direct process control (start/stop PLECS.exe, set priority)
- Classes: `PlecsApp`, `PlecsServer`

**Value-Add Layer** (modern modules):
- Cross-platform simulation orchestration with batch optimization
- Hash-based caching for 100-1000x speedup on repeated simulations
- REST API and web UI for ecosystem integration
- Priority queue (CRITICAL/HIGH/NORMAL/LOW) with retry logic
- Async task queue leveraging PLECS batch parallel API
- Structured logging and monitoring

**Key Improvements (v1.0.0)**:
- ❌ Removed file-based variant generation (use PLECS ModelVars natively)
- ❌ Removed GenericConverterPlecsMdl class (use pathlib.Path directly)
- ✅ Added batch parallel API for 3-5x speedup
- ✅ Simplified orchestrator using PLECS native parallelization
- ✅ 39% code reduction (4,081 → ~2,500 LOC)

### Module Organization

```
pyplecs/
├── config.py              # Configuration management (YAML-based)
├── pyplecs.py             # Legacy PLECS automation (Windows-specific)
├── plecs_components.py    # Legacy component definitions
│
├── core/
│   └── models.py          # Data models: SimulationRequest, SimulationResult, etc.
│
├── orchestration/         # Task queue, workers, priority handling
│   └── __init__.py        # SimulationOrchestrator, TaskPriority, SimulationTask
│
├── cache/                 # Hash-based simulation result caching
│   └── __init__.py        # SimulationCache, CacheBackend (file/redis/memory)
│
├── api/                   # FastAPI REST endpoints
│   └── __init__.py        # /simulations, /stats, /cache endpoints
│
├── webgui/                # Web monitoring interface
│   ├── webgui.py          # FastAPI app with WebSocket support
│   ├── templates/         # Jinja2 templates
│   └── static/            # CSS, JS, assets
│
├── logging/               # Structured logging (console, file, JSON)
│   └── __init__.py
│
├── optimizer/             # Parameter optimization (genetic, PSO, Bayesian)
│   └── __init__.py        # Placeholder for future implementation
│
├── mcp/                   # Model Context Protocol server
│   └── __init__.py        # Placeholder for future implementation
│
└── cli/
    └── installer.py       # Setup wizard and environment checks
```

### Key Configuration File

`config/default.yml` is the central configuration file. It contains:
- PLECS executable paths (auto-detected or user-specified)
- XML-RPC server settings (host, port, timeout)
- Orchestration settings (max concurrent simulations, queue size, retries)
- Cache settings (storage format: parquet/hdf5/csv, compression, TTL)
- Web GUI and API ports
- Logging configuration (file rotation, structured JSON logs)

The config system uses dataclasses defined in `config.py` with hot-reload support.

## Important Patterns & Conventions

### Backward Compatibility (v1.0.0)

**Removed in v1.0.0** (see MIGRATION.md):
- `generate_variant_plecs_file()`, `generate_variant_plecs_mdl()` - Use PLECS ModelVars instead
- `GenericConverterPlecsMdl` class - Use `pathlib.Path` and `PlecsServer` directly
- `ModelVariant` class - Use `SimulationRequest` with parameters

**Deprecated (still works in v1.0.0, removed in v2.0.0)**:
- `run_sim_with_datastream()` → Use `simulate()`
- `load_modelvars()` → Pass parameters directly to `simulate()`
- Legacy `PlecsServer(sim_path, sim_name)` → Use `PlecsServer(model_file)`

**Recommended usage**:
```python
# Modern API (v1.0.0+)
from pyplecs import PlecsServer, SimulationOrchestrator, SimulationCache

# Single simulation
with PlecsServer("model.plecs") as server:
    results = server.simulate({"Vi": 12.0, "Vo": 5.0})

# Batch simulations (3-5x faster)
with PlecsServer("model.plecs") as server:
    params_list = [{"Vi": 12.0}, {"Vi": 24.0}, {"Vi": 48.0}]
    results = server.simulate_batch(params_list)

# Orchestrated simulations with cache
orchestrator = SimulationOrchestrator(plecs_server=server)
task_id = await orchestrator.submit_simulation(request)
```

If optional dependencies are missing (e.g., pywinauto, fastapi), the package degrades gracefully with None placeholders.

### PLECS Communication Methods

1. **XML-RPC** (primary method, cross-platform):
   - PLECS runs with XML-RPC server enabled (default port 1080)
   - Python sends commands via `xmlrpc.client.Server`
   - Used by `PlecsServer` class and modern orchestration

2. **GUI Automation** (legacy, Windows-only):
   - Uses pywinauto to control PLECS desktop app
   - Sends keyboard shortcuts (Ctrl+T for simulation)
   - Used by `PlecsApp` class for parallel GUI simulations

3. **~~File-based Variants~~** (REMOVED in v1.0.0):
   - ❌ **Replaced by PLECS native ModelVars**
   - Old approach generated physical .plecs files (unnecessary)
   - New approach: Pass parameters directly via `simulate({"Vi": 12.0})`
   - See MIGRATION.md for migration examples

### Simulation Workflow

**Modern Pattern (Preferred)**:
```python
# 1. Initialize orchestrator with config
config = get_config()
orchestrator = SimulationOrchestrator()

# 2. Create simulation request
request = SimulationRequest(
    model_file="path/to/model.plecs",
    parameters={"Vi": 12.0, "Vo": 5.0},
    output_variables=["Vo", "IL"]
)

# 3. Submit with priority
task_id = await orchestrator.submit_simulation(request, priority=TaskPriority.HIGH)

# 4. Wait for result (automatically cached)
result = await orchestrator.wait_for_completion(task_id)
```

**Batch Parallel Pattern (v1.0.0+, FAST)**:
```python
# For multiple simulations - 3-5x faster than sequential
with PlecsServer("model.plecs") as server:
    # Prepare parameter list
    params_list = [
        {"Vi": 12.0, "Vo": 5.0},
        {"Vi": 24.0, "Vo": 10.0},
        {"Vi": 48.0, "Vo": 20.0}
    ]

    # PLECS parallelizes internally across CPU cores
    results = server.simulate_batch(params_list)
```

**Legacy Pattern (Deprecated, Removed in v2.0.0)**:
```python
# OLD - File-based variant generation (REMOVED in v1.0.0)
# plecs_mdl = GenericConverterPlecsMdl("path/to/model.plecs")
# variant_mdl = generate_variant_plecs_mdl(plecs_mdl, "01", {"Vi": 12.0})

# DEPRECATED - Use simulate() instead
server = PlecsServer(sim_path="./", sim_name="model.plecs")
server.load_modelvars({"Vi": 12.0, "Vo": 5.0})
results = server.run_sim_with_datastream()

# MODERN - Direct simulation
with PlecsServer("model.plecs") as server:
    results = server.simulate({"Vi": 12.0, "Vo": 5.0})
```

### Caching Strategy

The caching system uses SHA256 hashes of:
- Model file content (if `include_files: true`)
- Simulation parameters (if `include_parameters: true`)
- Excluding fields like "timestamp" and "run_id" (configurable)

Storage formats:
- **Timeseries data**: Parquet (default, fast), HDF5 (large data), CSV (compatibility)
- **Metadata**: JSON (default), YAML
- **Compression**: Snappy (default, fast), GZIP, LZ4

Cache backends:
- **File** (implemented): Stores in `./cache` directory
- **Redis** (placeholder): For distributed systems
- **Memory** (placeholder): For temporary caching

### Priority Queue System

`SimulationOrchestrator` uses a priority queue with 4 levels:
- `CRITICAL` (0): Highest priority
- `HIGH` (1): Important simulations
- `NORMAL` (2): Default priority
- `LOW` (3): Background/batch jobs

Tasks with same priority are ordered by submission time (FIFO).

**Batch Execution (v1.0.0+)**:
- Orchestrator collects tasks from priority queue
- Groups tasks into batches (default: 4 simulations per batch)
- Submits batches to PLECS via `simulate_batch()` for parallel execution
- PLECS distributes work across CPU cores automatically
- Result: 3-5x faster than sequential execution

### Error Handling & Retries

Simulations can fail due to:
- PLECS executable not found
- XML-RPC connection timeout
- Simulation convergence issues
- Invalid model parameters

The orchestrator supports:
- Configurable retry attempts (default: 3)
- Retry delay between attempts (default: 5 seconds)
- Status tracking: QUEUED → RUNNING → COMPLETED/FAILED/CANCELLED

## Platform-Specific Notes

### Windows
- GUI automation features require pywinauto
- PLECS.exe paths typically: `C:\Program Files\Plexim\PLECS X.X (64 bit)\plecs.exe`
- Installer: `tools\installers\windows_installer.bat` or `windows_installer.ps1`
- Process priority control via psutil (HIGH_PRIORITY_CLASS)

### Linux/WSL
- Only XML-RPC mode supported (no GUI automation)
- PLECS paths may be: `/usr/local/bin/plecs` or custom installs
- Some tests may require Wine to run PLECS on Linux

### Configuration File Auto-Detection
The config system searches for `config/default.yml` in:
1. Current working directory
2. Parent directories (up to 3 levels)
3. Package installation directory
4. User home directory (`~/.pyplecs/config.yml`)

## Web GUI Structure

The web interface (`pyplecs/webgui/webgui.py`) provides:
- **Dashboard**: Real-time simulation monitoring
- **Simulations page**: Submit new simulations, view queue
- **Settings page**: Edit configuration (planned)
- **WebSocket**: Live updates at `/ws` endpoint

Technologies:
- FastAPI for routing
- Jinja2 for templates
- WebSocket for real-time updates
- Plotly for visualization (via static files)

## Testing Patterns

Legacy tests (`tests/test_basic.py`) demonstrate:
- `test03`: Open PLECS with high priority
- `test04`: XML-RPC server simulation
- `test07`: Sequential simulations (deprecated file-based variant approach)
- `test09`: Parallel GUI simulations with multiple PLECS instances

Refactored tests (v1.0.0+):
- `tests/test_plecs_server_refactored.py`: New PlecsServer batch API
  - Test batch parallel simulation via `simulate_batch()`
  - Verify PLECS native parallelization
  - Context manager and parameter conversion
- `tests/test_orchestrator_batch.py`: Batch orchestration
  - Task batching and priority queueing
  - Cache integration with batch execution
  - Statistics tracking
- `tests/benchmark_batch_speedup.py`: Performance validation
  - Verify 3-5x speedup vs sequential execution
  - Batch size scaling tests
  - Cache performance impact

Modern tests (`tests/test_refactored.py`) cover:
- Configuration loading
- Orchestrator task submission
- Cache hit/miss behavior
- API endpoint responses

## Common Gotchas

1. **XML-RPC Port Conflicts**: If port 1080 is in use, PLECS XML-RPC server won't start. Change `plecs.xmlrpc.port` in config.

2. **Model File Paths**: Must be absolute paths. Use `Path.resolve()` to convert relative paths.

3. **Missing pywinauto**: GUI automation features degrade gracefully but print warnings. Install with `pip install pywinauto` on Windows.

4. **PLECS Executable Not Found**: Run `pyplecs-setup` to configure paths, or manually edit `config/default.yml`.

5. **Cache Directory Permissions**: Ensure write access to `./cache` directory or change `cache.directory` in config.

6. **MATLAB .mat Files**: Results are saved in MATLAB v5 format via `scipy.io`. Use `load_mat_file()` helper to exclude metadata keys.

7. **Migration from v0.x**: See `MIGRATION.md` for upgrading guide. File-based variant generation and `GenericConverterPlecsMdl` were removed in v1.0.0.

8. **Batch Size Tuning**: For optimal performance, set `orchestration.max_concurrent_simulations` in config to match your CPU cores (default: 4).

## Entry Points

The package exposes multiple entry points in `setup.py`:
- `pyplecs-setup`: Run installer wizard (`pyplecs.cli.installer:main`)
- `pyplecs-gui`: Start web GUI (`pyplecs.webgui:main`)
- `pyplecs-api`: Start REST API (`pyplecs.api:main`)
- `pyplecs-mcp`: Start MCP server (`pyplecs.mcp:main`)

## Git Workflow

Current branch: `dev`
Main branch: `master` (use for PRs)

Recent work includes:
- Advanced PowerShell installer with logging and JSON status output
- Web GUI with settings and simulations pages
- Major refactoring (v1.0.0) - 39% code reduction, 5x performance improvement:
  - Eliminated file-based variant generation (use PLECS ModelVars)
  - Added batch parallel API via PLECS native parallelization
  - Simplified orchestrator to use batch execution
  - See MIGRATION.md for upgrading from v0.x
