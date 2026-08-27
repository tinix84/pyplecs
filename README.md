# PyPLECS

Python automation framework for [PLECS](https://www.plexim.com/products/plecs)
power electronics simulation.

PyPLECS drives PLECS over XML-RPC so a converter model can be run hundreds of
times without being hand-driven: batched and parallel execution, result caching,
a REST API, and a web dashboard. It executes simulations; it does not decide
which ones to run ([ADR-0005](https://github.com/tinix84/pyplecs/blob/master/docs/adr/0005-pyplecs-is-a-thin-execution-engine.md)).

Requires a licensed PLECS installation listening on XML-RPC port 1080.

## Install

Needs [uv](https://docs.astral.sh/uv/getting-started/installation/); it
provisions a matching Python itself, so nothing else is a prerequisite.

```bash
uv sync --extra web                     # environment + pinned dependencies
uv run pyplecs-setup configure-plecs    # find PLECS, write config/default.yml
```

Extras, combinable: `web` (REST API + dashboard), `cache` (HDF5, diskcache and
Redis backends — Parquet is built in), `gui` (Windows desktop automation),
`mcp` (MCP server), `opt`, `dev`. `pyproject.toml` is the only place a
dependency is declared ([ADR-0008](https://github.com/tinix84/pyplecs/blob/master/docs/adr/0008-pyproject-and-uv-own-dependencies.md)).

`config/default.yml` is untracked machine-local state, seeded from the tracked
`config/default.example.yml`. On Windows, `setup_env.bat` runs both commands
above and `start_plecs.bat` launches PLECS plus the API.

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

### Portable TAS execution

PyPLECS can consume the supported electrical projection of a decoded
[TAS v2](https://github.com/Power-Supply-Manufacturers-Association/TAS)
document without installing TAS, CIAS, PEAS, or a component database. The
Band 1 projection is deliberately narrow: one self-contained non-isolated
buck switching stage, optional virtual control, inline R/C/single-winding L/
MOSFET/diode data, PWM stimulus, transient analysis, and resistive Operating
Point loads. Thermal and magnetic-domain simulation are future work; preserved
unsupported data is diagnosed rather than claimed as consumed.

```python
from pyplecs import SimulationOrchestrator, TasExecutionService

async def run_tas(tas_document, plecs_adapter):
    # Compile once, expand named TAS Operating Points into ordinary Simulation
    # Tasks, and return one ordered terminal envelope.
    orchestrator = SimulationOrchestrator(plecs_adapter)
    try:
        return await TasExecutionService(orchestrator).execute(tas_document)
    finally:
        await orchestrator.stop()
```

The web extra exposes the same service under the configured API prefix:

- `POST /tas/studies/sync` waits for the terminal envelope.
- `POST /tas/studies` returns a process-local study ID.
- `GET /tas/studies/{study_id}` returns public Operating-Point progress or the
  terminal envelope.

URI-valued circuits or components require a caller-supplied resolver in the
Python API. REST intake performs no implicit filesystem or network resolution.

Console entry points:

| Command | Does |
|---|---|
| `pyplecs-setup configure-plecs` | Locate PLECS, write local config |
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
├── studies/            finite Parametric Study expansion and reduction
├── tas/                standalone TAS electrical projection and service
├── converter/          Circuit Model plus deterministic emitters
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
uv run ruff check .    # must be clean
uv run pytest   # full suite: needs Windows + PLECS on port 1080
```

Platform-independent subset, which is also what the pre-push gate runs:

```bash
uv run pytest -q tests/test_installer.py tests/test_entrypoint.py \
          tests/test_install_full.py tests/test_abc_contract.py \
          tests/test_plecs_expert.py
```

The Band 1 live TAS smoke is opt-in and skips clearly when PLECS XML-RPC is not
available:

```bash
PYPLECS_RUN_LIVE_TAS=1 uv run pytest -q tests/test_tas_live.py
```

There is no GitHub Actions CI — a pre-push hook covers lint and the
platform-independent tests; PLECS-dependent tests are run by hand on Windows.

Licensed under the terms in [LICENSE](https://github.com/tinix84/pyplecs/blob/master/LICENSE).
