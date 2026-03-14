# PyPLECS — Architecture

## Overview

Python automation framework for PLECS power electronics simulation. Wraps PLECS' XML-RPC interface with batch execution, caching, REST API, and web dashboard.

## Two-Layer Design

### Layer 1 — Core (`pyplecs/pyplecs.py`)

Thin XML-RPC wrapper around PLECS on port 1080.

- **`PlecsServer`**: Context manager providing `simulate()` and `simulate_batch()`.
- **`PlecsApp`**: Windows GUI automation via pywinauto.

### Layer 2 — Modern Features

Built on top of the core:

| Module | Purpose |
|--------|---------|
| `orchestration/` | Priority queue (CRITICAL=0, HIGH=1, NORMAL=2, LOW=3), batch grouping, retry logic via `SimulationOrchestrator` |
| `cache/` | SHA256 hash-based result deduplication with Parquet/HDF5/CSV backends via `SimulationCache` |
| `api/` | FastAPI REST endpoints (`create_api_app()`) |
| `webgui/` | Flask/Starlette dashboard with WebSocket updates |
| `core/models.py` | Pydantic data models (`SimulationRequest`, `SimulationResult`, etc.) |
| `config.py` | YAML config management; searches: cwd -> parent dirs (3 levels) -> package dir -> `~/.pyplecs/config.yml` |
| `cli/installer.py` | Setup wizard that auto-detects PLECS installation |

## Key Patterns

```python
# Single simulation
with PlecsServer("model.plecs") as server:
    results = server.simulate({"Vi": 12.0, "Vo": 5.0})

# Batch simulation (3-5x faster, uses PLECS native parallel API)
with PlecsServer("model.plecs") as server:
    results = server.simulate_batch([{"Vi": 12.0}, {"Vi": 24.0}, {"Vi": 48.0}])
```

## Data Flow

```
User/NTBEES2 -> SimulationRequest (Pydantic)
  -> SimulationOrchestrator (priority queue)
    -> SimulationCache (SHA256 check)
      -> HIT:  return cached Parquet
      -> MISS: PlecsServer.simulate() via XML-RPC
               -> cache result -> return
```

## Project Structure

```
pyplecs/
├── CLAUDE.md                # Claude Code guidance (<50 lines)
├── README.md                # Public-facing documentation
├── mkdocs.yml               # Documentation site config
├── pyproject.toml            # Package metadata
├── config/
│   └── default.yml           # Default PLECS + orchestration config
├── .claude/
│   ├── settings.json         # Permissions + hooks (bootstrap-managed)
│   ├── settings.local.json   # User overrides (never auto-modified)
│   ├── skills.md             # Project-specific command reference
│   └── hooks/                # Claude Code PostToolUse hooks (Python)
│       ├── post_commit_remind.py
│       ├── post_tool_regen_docs.py
│       └── post_tool_build_mkdocs.py
├── docs/
│   ├── index.md              # MkDocs landing page
│   ├── prd.md                # Product requirements
│   ├── architecture.md       # This file
│   ├── auto-context.md       # Generated project summary
│   ├── api.md                # REST API reference
│   ├── install.md            # Installation guide
│   ├── webgui.md             # Web dashboard guide
│   ├── migration.md          # v0.x -> v1.0.0 upgrade
│   ├── changelog.md          # Version history
│   ├── contributing.md       # Development workflow
│   └── sprints/              # Sprint plans
├── pyplecs/                  # Source package
│   ├── __init__.py
│   ├── pyplecs.py            # Core XML-RPC wrapper
│   ├── config.py             # Configuration management
│   ├── core/models.py        # Pydantic data models
│   ├── orchestration/        # Priority queue, batch execution
│   ├── cache/                # SHA256 caching
│   ├── api/                  # FastAPI REST endpoints
│   ├── webgui/               # Flask/Starlette dashboard
│   ├── cli/                  # Setup wizard
│   ├── mcp/                  # MCP server (planned)
│   └── optimizer/            # Optimization algorithms
└── tests/                    # Test suite
```

## Hooks System

PyPLECS uses Claude Code PostToolUse hooks for development workflow automation. Because this is a native Windows project, hooks are **local Python scripts** (not centralized bash like WSL projects).

| Hook | Trigger | Action |
|------|---------|--------|
| `post_commit_remind.py` | `git commit` | Reminds to update docs if behavior changed |
| `post_tool_regen_docs.py` | `git push main` | Checks doc staleness, suggests regeneration |
| `post_tool_build_mkdocs.py` | `git push` | Reminds to rebuild mkdocs if `mkdocs.yml` exists |

Hooks read JSON from stdin (Claude Code hook protocol) and output non-blocking reminders.

## Documentation Pipeline

```
docs/*.md --> mkdocs build --> site/
                                |
                    mkdocs gh-deploy --force
                                |
                                v
                    gh-pages branch (GitHub)
                                |
                                v
                    tinix84.github.io/pyplecs
```

## Entry Points

| Command | Module |
|---------|--------|
| `pyplecs-setup` | `pyplecs.cli.installer:main` |
| `pyplecs-gui` | `pyplecs.webgui:run_app` |
| `pyplecs-api` | `pyplecs.api:main` |
| `pyplecs-mcp` | `pyplecs.mcp:main` |

## v1.0.0 API Changes

**Removed**: `generate_variant_plecs_file()`, `GenericConverterPlecsMdl`, `ModelVariant`

**Deprecated** -> replacements:
- `run_sim_with_datastream()` -> `simulate()`
- `load_modelvars()` -> pass params to `simulate()`

## Gotchas

1. Port 1080 conflicts — change via `plecs.xmlrpc.port` in config
2. Model files require absolute paths
3. Missing pywinauto degrades gracefully (GUI automation disabled, XML-RPC still works)
4. Batch size = CPU cores for best throughput
5. Windows-only: GUI automation (`PlecsApp`), psutil process priority. Linux/macOS: XML-RPC only

## Integration Context

PyPLECS is a sibling product in an ecosystem:
- **NTBEES2**: Intelligence (optimization, design decisions, ML models)
- **PyPLECS**: Execution (circuit simulation via PLECS)
- **PyMKF**: Magnetic design (similar pattern)

Integration point: **TAS format** (Topology Agnostic Structure) — standardized JSON for power electronics that NTBEES2 generates and PyPLECS consumes.
