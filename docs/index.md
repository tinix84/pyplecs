# PyPLECS

**Fast, cached, scalable PLECS simulation framework with REST API and Web GUI**

PyPLECS automates [PLECS](https://www.plexim.com/plecs) power electronics simulation with modern software engineering practices.

## Key Features

- **5x faster** batch simulations leveraging PLECS native parallel API
- **100-1000x cache speedup** on repeated simulations (hash-based deduplication)
- **REST API** for language-agnostic integration
- **Web GUI** for real-time monitoring and control
- **Priority queue** with automatic retry logic
- **Flexible caching** with Parquet, HDF5, or CSV storage

## Quick Start

```bash
pip install -e .
```

```python
from pyplecs import PlecsServer

with PlecsServer("model.plecs") as server:
    results = server.simulate({"Vi": 12.0, "Vo": 5.0})
```

## Documentation

| Document | Description |
|----------|-------------|
| [PRD](prd.md) | Product requirements and roadmap |
| [Architecture](architecture.md) | System design, layers, data flow |
| [API Reference](api.md) | REST API endpoints and examples |
| [Installation](install.md) | Setup, configuration, troubleshooting |
| [Web GUI](webgui.md) | Dashboard features and usage |
| [Migration](migration.md) | v0.x to v1.0.0 upgrade guide |
| [Changelog](changelog.md) | Version history |
| [Contributing](contributing.md) | Development setup and workflow |
| [Auto-Context](auto-context.md) | Generated project summary |

## Architecture

Two-layer design:

1. **Core Layer** (`pyplecs.py`): Thin wrapper around PLECS XML-RPC + GUI automation
2. **Value-Add Layer**: Orchestration, caching, API, web UI

## Links

- [GitHub Repository](https://github.com/tinix84/pyplecs)
- [PLECS by Plexim](https://www.plexim.com/plecs)
