# PyPLECS — Python automation framework for PLECS power electronics simulation

**Stack**: python | **Version**: 1.0.0

## Build & Test
```bash
pip install -e ".[dev]"
pytest
ruff check .
```

CI runs only platform-independent tests on Ubuntu. PLECS XML-RPC tests require a running PLECS instance (Windows).

## Key Documents
- [PRD](docs/prd.md) — requirements and roadmap
- [Architecture](docs/architecture.md) — system design, layers, data flow
- [Auto-Context](docs/auto-context.md) — generated project summary
- [API](docs/api.md) — REST API reference
- [Install](docs/install.md) — installation and configuration
- [Changelog](docs/changelog.md) — version history
- [Web GUI](docs/webgui.md) — dashboard guide
- [Contributing](docs/contributing.md) — development workflow
- [Migration](docs/migration.md) — v0.x to v1.0.0 upgrade

## Sprint Plans
Convention: `docs/sprints/sprint-*.md` | Default model: **sonnet**

## Skills
Central pool (WSL): `\\wsl$\Ubuntu\home\tinix\claude_wsl\agents_pool\`
```bash
python -m src.cli list           # List all skills
python -m src.cli run sw-arch .  # Run architecture analysis
```
Domain: pe-expert | Local skills reference: `.claude/skills.md`

## Task Protocol
1. **90% Rule**: Ask clarifying questions until task is >= 90% clear
2. Complex tasks -> sprint plan in `docs/sprints/` -> execute with sonnet
3. Run tests after changes: `pytest`
4. On commit: update CLAUDE.md, prd.md, architecture.md if behavior changed

## Decision Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-24 | Align with agents_pool standard | Consistent hooks, CLAUDE.md, settings across all projects |
| 2026-02-24 | Local Python hooks (not bash) | Native Windows project; Python hooks are cross-platform |
| 2026-02-24 | Architecture details in docs/ | Keep CLAUDE.md <50 lines; link to detailed docs |
| 2026-02-24 | All doc filenames lowercase | URL-friendly mkdocs output; consistent across projects |
| 2026-02-24 | mkdocs gh-deploy to GitHub Pages | Public docs at tinix84.github.io/pyplecs |
