# ADR-0008 — pyproject and uv own environment and dependencies

- **Status**: Accepted
- **Date**: 2026-08-20

## Context

Dependencies were declared in four places that disagreed with each other:

- `pyproject.toml` — a lean core plus `web`, `mcp` and `dev` extras.
- Seven `requirements*.txt` files — the same core, plus three whole extras
  (`gui`, `cache`, `opt`) that existed nowhere else, plus `web` auth packages
  and `dev` test/docs tools missing from `pyproject`.
- `setup.py` — read `requirements.txt` (which `-r`-includes web, gui and cache)
  straight into `install_requires`, so it declared as *mandatory* what
  `pyproject` declared optional. `pyproject` wins at build time, so `setup.py`
  was dead code that still read as authoritative.
- `docs/install.md` — twelve install variants across `pip install -e .` and
  various `-r` combinations.

Environment creation was equally scattered: `setup_env.bat` spent 315 lines
discovering Python and conda installations, choosing between an existing conda
env and a new venv, and recording the choice into a tracked config file so
`start_plecs.bat` could replay the activation. `tools/installers/` was a third
install path. `setup_env.sh` was a fourth.

Nothing here needed to be bespoke. A lockfile plus a tool that provisions its
own interpreter does all of it.

## Decision

**`pyproject.toml` is the only place a dependency is declared, and `uv` owns
the environment.** `uv.lock` is committed, so an install is reproducible.

Setup is two commands:

```
uv sync                        # interpreter, venv, pinned dependencies
uv run pyplecs-setup configure-plecs   # locate PLECS, write local config
```

`requirements*.txt` and `setup.py` are deleted. The three orphaned extras are
ported to `pyproject`. `pyarrow` moves to *core* dependencies rather than the
`cache` extra, because `pyplecs/__init__.py` imports `.cache` unguarded and
Parquet is the configured default — the extra classification was simply wrong,
and made the package unimportable without it.

Two responsibilities are deliberately kept apart:

- **Environment and dependencies** are `uv`'s, derived entirely from
  `pyproject.toml` + `uv.lock`.
- **Machine-local state** — where PLECS is installed, which host and port the
  API binds — is `config/default.yml`, which is **untracked**. A tracked
  `config/default.example.yml` carries the structure with no paths in it.
  `pyplecs-setup configure-plecs` seeds one from the other and fills in the
  discovered PLECS path.

The `python`/`conda_root` block that the old scripts wrote into config is gone;
`uv run` resolves the environment with no activation step to record.

## Consequences

- `setup_env.bat` drops from 315 lines to 47 and `start_plecs.bat` loses its
  conda-discovery block: `uv` downloads a matching interpreter if none exists,
  so there is nothing to discover. `setup_env.sh`, `tools/installers/`,
  `tools/configure_plecs.py` and `tools/read_plecs_path.py` are deleted, the
  last two folded into `pyplecs/cli/installer.py` where they are importable and
  testable.
- `_start_api.py` and `tools/start_webgui.py` are deleted as duplicates of the
  `pyplecs-api` and `pyplecs-gui` console scripts. Verified equivalent first:
  `ApiConfig` defaults to `0.0.0.0:8081`, exactly what `_start_api.py`
  hardcoded, and `run_app` defaults to `127.0.0.1:8001`. The only capability
  either script had over its entry point — `PYPLECS_HOST`/`PYPLECS_PORT` — was
  moved into `pyplecs-gui` rather than dropped.
- `uv` requires a network on first sync and its own installation. That is the
  cost accepted: the alternative was four disagreeing dependency manifests.
- Nobody's absolute PLECS path ships to a clone any more. The previously
  tracked `config/default.yml` contained one.
- The pre-push gate fails if any `requirements*.txt` or `setup.py` reappears,
  because a second dependency manifest is how this state was reached.
- Existing conda users lose the recorded-activation path. `uv sync` creates
  `.venv` in the repo; the choice is no longer configurable.
