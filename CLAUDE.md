# PyPLECS — Python automation framework for PLECS power electronics simulation

**Stack**: python | **Version**: 1.0.0

## Build & Test
```bash
uv sync --extra dev                    # env + pinned deps (ADR-0008)
uv run pyplecs-setup configure-plecs   # locate PLECS, write config/default.yml (untracked)
uv run ruff check .                    # lint (must be clean)
uv run pytest                          # full suite (Windows + PLECS on port 1080)
uv run pytest -q tests/test_installer.py tests/test_entrypoint.py tests/test_install_full.py tests/test_abc_contract.py tests/test_plecs_expert.py  # platform-independent subset
```

Extras: `web`, `cache`, `gui`, `mcp`, `opt`, `dev`. `pyproject.toml` is the only
place a dependency is declared — the gate rejects any `requirements*.txt` or
`setup.py`.

**No GitHub Actions CI.** The git `pre-push` hook at `.githooks/pre-push` (wired via `core.hooksPath`) runs the ADR-0004 structural checks, `ruff check .`, vulture, and the 5 platform-independent test files; PLECS XML-RPC tests run manually on Windows. Claude Code's `PostToolUse` hooks fire *after* a command completes and can never block a push — don't put a gate there.

## Architecture quick reference
- **Two layers**: `pyplecs/pyplecs.py` is a thin XML-RPC wrapper over PLECS; the orchestration / cache / api / webgui packages are built on top. There is no architecture document — the code is the only description of what exists (ADR-0004).
- **PyPLECS executes; the caller decides** (ADR-0005). Optimization, surrogate models, adaptive search and component databases are permanently out of scope. `pyplecs/optimizer` is a placeholder for something that will not be built.
- **Two model flavors** (ADR-0006): `pyplecs.contracts.*` is the upstream pydantic flavor, `pyplecs.*` the local dataclass flavor. Field-level incompatible, deliberately not merged.
- **Tool-agnostic ABCs at `pyplecs.contracts`** — public façade that prefers an installed PyPI `pycircuitsim_core` (when major-version-compatible) and falls back to the vendored copy at `pyplecs/_contracts/`. **Hard rule:** PyPLECS is standalone — never add `pycircuitsim-core` to `pyproject.toml` dependencies. See `tools/SYNC_PYCIRCUITSIM_CORE.md` for re-sync procedure.
- **Optional deps degrade to `None`** — `pyplecs/__init__.py` sets `PlecsServer`, `create_api_app`, `create_web_app`, etc. to `None` when their optional packages aren't installed; callers must handle `None`.
- **PLECS docs reference at `.claude/skills/plecs-expert/`** — single source of truth for the skill, `/plecs` command, and `pyplecs-mcp` MCP server. Refresh procedure in `.claude/skills/plecs-expert/tools/REFRESH.md`.

## Where statements live (ADR-0004)

| Kind of statement | Owner |
|---|---|
| What a word means | [`CONTEXT.md`](CONTEXT.md) |
| Why we chose X over Y | [`docs/adr/`](docs/adr/README.md) — index also mirrored in the Decision Log below |
| The long-term outcome | [`docs/story-map.md`](docs/story-map.md) — solution-neutral, status-free |
| What we found out | [`docs/research/`](docs/research/README.md) |
| What to build, and its status | GitHub issues, via `gh` |
| How to install and use it | [`README.md`](README.md) — capped at 150 lines |
| What the code does | the code |
| How agents consume this repo | [`docs/agents/`](docs/agents/domain.md) |

`docs/` holds nothing else, and the pre-push hook enforces that.

- [PLECS Expert Skill](.claude/skills/plecs-expert/SKILL.md) — PLECS docs reference (offline + URL fallback), content posture in ADR-0007.

## Plans
- Plans: `docs/superpowers/plans/YYYY-MM-DD-<topic>.md` — **gitignored and disposable**. Never cited from a tracked doc or an issue.
- Specs are issues. There is no spec artifact on disk.
- Default execution model: **sonnet**

## Skills
Local skills reference: [`.claude/skills.md`](.claude/skills.md) — canonical command sequences (ruff, pytest, entry points, code patterns).
Central pool (WSL): `\\wsl$\Ubuntu\home\tinix\claude_wsl\agents_pool\` | Domain: pe-expert.

## Task Protocol
1. **90% Rule**: Ask clarifying questions until task is >= 90% clear
2. Multi-step tasks -> spec as a GitHub issue -> plan in `docs/superpowers/plans/` -> execute with sonnet (use the superpowers skills)
3. Run tests after changes: `ruff check . && pytest`
4. On commit: a new decision means an ADR in `docs/adr/` **and** a Decision Log row below. Never describe behaviour in a tracked doc.

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
| 2026-04-27 | Add `plecs-expert` skill + `pyplecs-mcp` MCP server | Ground PLECS authoring help, netlist converter, and PlecsServer wrapper in docs.plexim.com via offline caveman-style reference. Closes #23. |
| 2026-08-20 | Code is the only architecture truth ([ADR-0004](docs/adr/0004-code-is-the-only-architecture-truth.md)) | `docs/architecture.md`, both PRDs and the user-doc set all drifted from the code. `docs/` now holds only ADRs, the story map, research, and agent conventions; README is the one user-facing doc. Supersedes the 2026-02-24 "Architecture details in docs/" and 2026-04-25 "Move `articles/`" rows. |
| 2026-08-20 | PyPLECS is a thin execution engine ([ADR-0005](docs/adr/0005-pyplecs-is-a-thin-execution-engine.md)) | PyPLECS runs the parameter vectors it is given; choosing them adaptively belongs to the caller. Stated without naming any orchestrator, so it holds for all of them. |
| 2026-08-20 | Two model flavors, no merge ([ADR-0006](docs/adr/0006-two-model-flavors-no-merge.md)) | Vendored contract models are field-level incompatible with `pyplecs/core/models.py`; merging would break every `result.timeseries_data` call site. Name-level ABC conformance only; interop adapter deferred. |
| 2026-08-20 | Verbatim tables, rewritten prose ([ADR-0007](docs/adr/0007-verbatim-tables-rewritten-prose.md)) | `plecs-expert` mirrors proprietary PLECS docs into a public repo. Factual tables verbatim, all prose original in caveman style, `LICENSE-NOTES.md` as the auditable boundary. |
| 2026-08-20 | pyproject + uv own environment and dependencies ([ADR-0008](docs/adr/0008-pyproject-and-uv-own-dependencies.md)) | Four disagreeing manifests: pyproject, 7 `requirements*.txt`, a `setup.py` that declared extras as mandatory, and 12 documented install variants. Deleted all but pyproject; `uv.lock` committed; machine-local `config/default.yml` untracked with a tracked example. |

## Agent skills

### Issue tracker

GitHub Issues on `tinix84/pyplecs`, via the `gh` CLI. See [docs/agents/issue-tracker.md](docs/agents/issue-tracker.md).

### Triage labels

The five canonical roles, each label string equal to its name. See [docs/agents/triage-labels.md](docs/agents/triage-labels.md).

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See [docs/agents/domain.md](docs/agents/domain.md).
