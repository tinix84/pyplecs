# CLAUDE.md

PyPLECS: Python automation framework for PLECS power electronics simulation.

**Commands**: See `skills.md` for all development commands.

## Architecture

Two layers:
- **Core**: `pyplecs/pyplecs.py` - PLECS XML-RPC wrapper, GUI automation (Windows)
- **Modern**: REST API, web UI, caching, orchestration

### Module Map
```
pyplecs/
├── config.py              # YAML config management
├── pyplecs.py             # PlecsApp, PlecsServer classes
├── plecs_components.py    # Component definitions
├── core/models.py         # SimulationRequest, SimulationResult
├── orchestration/         # TaskPriority, SimulationOrchestrator
├── cache/                 # SimulationCache, CacheBackend
├── api/                   # FastAPI endpoints
├── webgui/                # Dashboard, templates, WebSocket
├── logging/               # Structured logging
└── cli/installer.py       # Setup wizard
```

## Key Classes

| Class | Purpose |
|-------|---------|
| `PlecsServer` | XML-RPC wrapper, `simulate()`, `simulate_batch()` |
| `PlecsApp` | Windows GUI automation via pywinauto |
| `SimulationOrchestrator` | Priority queue, batch execution |
| `SimulationCache` | SHA256 hash-based caching |

## PLECS Communication

1. **XML-RPC** (primary): Port 1080, cross-platform
2. **GUI Automation** (legacy): pywinauto, Windows-only

## Priority Queue

| Level | Value |
|-------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| NORMAL | 2 |
| LOW | 3 |

## v1.0.0 API

**Removed**: `generate_variant_plecs_file()`, `GenericConverterPlecsMdl`, `ModelVariant`

**Deprecated** (use alternatives):
- `run_sim_with_datastream()` → `simulate()`
- `load_modelvars()` → pass params to `simulate()`

**Use**:
```python
# Single
server.simulate({"Vi": 12.0})

# Batch (3-5x faster)
server.simulate_batch([{"Vi": 12.0}, {"Vi": 24.0}])
```

## Config

`config/default.yml` - PLECS paths, XML-RPC, cache, orchestration settings.

Search order:
1. Current directory
2. Parent directories (3 levels)
3. Package directory
4. `~/.pyplecs/config.yml`

## Platform Notes

- **Windows**: pywinauto for GUI, psutil for priority
- **Linux/WSL**: XML-RPC only

## Gotchas

1. Port 1080 conflicts - change `plecs.xmlrpc.port`
2. Use absolute paths for model files
3. Missing pywinauto degrades gracefully
4. Run `pyplecs-setup` if PLECS not found
5. Batch size = CPU cores for best performance
