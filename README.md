# PyPLECS

Python automation framework for [PLECS](https://www.plexim.com/products/plecs)
power electronics simulation.

PyPLECS drives PLECS over XML-RPC so a converter model can be run hundreds of
times without being hand-driven: batched and parallel execution, result caching,
a REST API, and a web dashboard. It executes simulations; it does not decide
which ones to run ([ADR-0005](https://github.com/tinix84/pyplecs/blob/master/docs/adr/0005-pyplecs-is-a-thin-execution-engine.md)).

Requires a licensed PLECS installation listening on XML-RPC port 1080.

## Install

```bash
pip install -e ".[dev]"
```

Optional extras, combinable: `web` (REST API + dashboard), `cache` (Parquet,
HDF5, Redis backends), `gui` (Windows desktop automation), `mcp` (MCP server),
`opt`, `dev`.

```bash
pip install -e ".[web,cache]"
```

Then point PyPLECS at your PLECS executable:

```bash
pyplecs-setup
```

Optional dependencies degrade to `None` rather than failing at import — if
`pyplecs.PlecsServer` or `pyplecs.create_web_app` is `None`, the matching extra
is not installed.

## Quickstart

```python
from pyplecs import PlecsServer

# Single simulation
with PlecsServer("model.plecs") as server:
    results = server.simulate({"Vi": 12.0, "Vo": 5.0})

# Batch — uses PLECS' own parallel batch API
with PlecsServer("model.plecs") as server:
    results = server.simulate_batch([{"Vi": 12.0}, {"Vi": 24.0}, {"Vi": 48.0}])
```

Console entry points:

| Command | Does |
|---|---|
| `pyplecs-setup` | Locate PLECS, write local config |
| `pyplecs-api` | Start the REST API |
| `pyplecs-gui` | Start the web dashboard |
| `pyplecs-mcp` | Start the MCP server (stdio) |

## Where things live

```
pyplecs/
├── pyplecs.py          PlecsServer — thin XML-RPC wrapper over PLECS
├── contracts.py        tool-agnostic ABCs (PyPI passthrough → _contracts/)
├── _contracts/         vendored copy of the ABCs, verbatim
├── core/               local request/result models
├── orchestration/      priority queue, batch execution
├── cache/              simulation result caching
├── api/                REST endpoints
├── webgui/             dashboard
├── mcp/                MCP server
├── cli/                pyplecs-setup
└── config.py           configuration loading
```

Everything above the `pyplecs.py` wrapper is built on it — that is the whole
layering.

| Question | Answer lives in |
|---|---|
| What a term means | [`CONTEXT.md`](https://github.com/tinix84/pyplecs/blob/master/CONTEXT.md) |
| Why we chose X over Y | [`docs/adr/`](https://github.com/tinix84/pyplecs/blob/master/docs/adr/README.md) |
| Where this is going | [`docs/story-map.md`](https://github.com/tinix84/pyplecs/blob/master/docs/story-map.md) |
| What is being built, and its status | [GitHub issues](https://github.com/tinix84/pyplecs/issues) |
| What we found out | [`docs/research/`](https://github.com/tinix84/pyplecs/blob/master/docs/research/README.md) |
| What the code does | the code ([ADR-0004](https://github.com/tinix84/pyplecs/blob/master/docs/adr/0004-code-is-the-only-architecture-truth.md)) |

## Contributing

Branch off `master` (`feat/`, `fix/`, `docs/`, `test/` + short description),
commit in [Conventional Commits](https://www.conventionalcommits.org/) form,
open a PR. Never push to `master` directly.

```bash
ruff check .    # must be clean
pytest          # full suite: needs Windows + PLECS on port 1080
```

Platform-independent subset, which is also what the pre-push gate runs:

```bash
pytest -q tests/test_installer.py tests/test_entrypoint.py \
          tests/test_install_full.py tests/test_abc_contract.py \
          tests/test_plecs_expert.py
```

There is no GitHub Actions CI — a pre-push hook covers lint and the
platform-independent tests; PLECS-dependent tests are run by hand on Windows.

Licensed under the terms in [LICENSE](https://github.com/tinix84/pyplecs/blob/master/LICENSE).
