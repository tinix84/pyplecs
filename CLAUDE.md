# PyPLECS — Python automation framework for PLECS power electronics simulation

**Stack**: python | **Version**: 1.0.0

## Build & Test
```bash
pip install -e ".[dev]"        # ruff + pytest
ruff check .                   # lint (must be clean)
pytest                         # full suite (Windows + PLECS on port 1080)
pytest -q tests/test_installer.py tests/test_entrypoint.py tests/test_install_full.py tests/test_abc_contract.py tests/test_plecs_expert.py  # platform-independent subset
```

**No GitHub Actions CI.** A Claude Code pre-push hook (`.claude/hooks/pre_push_lint.py`) runs `ruff check .` plus the 5 platform-independent test files on `git push`; PLECS XML-RPC tests run manually on Windows.

## Architecture quick reference
- **Two layers** (full detail in [architecture.md](docs/architecture.md)): `pyplecs/pyplecs.py` is a thin XML-RPC wrapper over PLECS; the orchestration / cache / api / webgui packages are built on top.
- **Tool-agnostic ABCs at `pyplecs.contracts`** — public façade that prefers an installed PyPI `pycircuitsim_core` (when major-version-compatible) and falls back to the vendored copy at `pyplecs/_contracts/`. **Hard rule:** PyPLECS is standalone — never add `pycircuitsim-core` to `pyproject.toml` dependencies. See `tools/SYNC_PYCIRCUITSIM_CORE.md` for re-sync procedure.
- **Optional deps degrade to `None`** — `pyplecs/__init__.py` sets `PlecsServer`, `create_api_app`, `create_web_app`, etc. to `None` when their optional packages aren't installed; callers must handle `None`.

## Key Documents
- [PRD](docs/prd.md) — requirements and roadmap
- [Architecture](docs/architecture.md) — system design, layers, data flow
- [Auto-Context](docs/auto-context.md) — generated project summary
- [API](docs/api.md) — REST API reference
- [Install](docs/install.md) — installation and configuration
- [Migration](docs/migration.md) — v0.x to v1.0.0 upgrade
- [Contributing](docs/contributing.md) — development workflow

## Specs & Plans
- Specs: `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
- Plans: `docs/superpowers/plans/YYYY-MM-DD-<topic>.md`
- Sprint plans (legacy): `docs/sprints/sprint-*.md`
- Default execution model: **sonnet**

## Skills
Local skills reference: [`.claude/skills.md`](.claude/skills.md) — canonical command sequences (ruff, pytest, entry points, code patterns).
Central pool (WSL): `\\wsl$\Ubuntu\home\tinix\claude_wsl\agents_pool\` | Domain: pe-expert.

## Task Protocol
1. **90% Rule**: Ask clarifying questions until task is >= 90% clear
2. Multi-step tasks -> spec in `docs/superpowers/specs/` -> plan in `docs/superpowers/plans/` -> execute with sonnet (use the superpowers skills)
3. Run tests after changes: `ruff check . && pytest`
4. On commit: update CLAUDE.md, prd.md, architecture.md if behavior changed; new architectural decisions go in the Decision Log below

## Decision Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-24 | Align with agents_pool standard | Consistent hooks, CLAUDE.md, settings across all projects |
| 2026-02-24 | Local Python hooks (not bash) | Native Windows project; Python hooks are cross-platform |
| 2026-02-24 | Architecture details in docs/ | Keep CLAUDE.md <50 lines; link to detailed docs |
| 2026-02-24 | All doc filenames lowercase | URL-friendly mkdocs output; consistent across projects |
| 2026-02-24 | mkdocs gh-deploy to GitHub Pages | Public docs at tinix84.github.io/pyplecs |
| 2026-04-25 | Remove GitHub Actions CI | Single-maintainer project; pre-push hook covers lint + platform-independent tests; PLECS-dependent tests run manually on Windows. |
| 2026-04-25 | Vendor `pycircuitsim_core` ABCs at `pyplecs/_contracts/`, expose via `pyplecs.contracts` façade with PyPI passthrough | PyPLECS must work standalone (no transitive dep on `pycircuitsim-core`); umbrella PyCircuitSim ecosystem is auto-detected when present. Vendored copy stays forever; no exit clause. |
| 2026-04-25 | Move `articles/` under `docs/articles/` | Ship long-form posts via mkdocs to GitHub Pages instead of bloating repo root. |
| 2026-04-25 | Unify lint on ruff (drop black/flake8/mypy/isort) | Single tool covers format + lint + isort; one config in `pyproject.toml`. |
