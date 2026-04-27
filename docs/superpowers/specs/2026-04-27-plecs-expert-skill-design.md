# PLECS-Expert Skill — Design Spec

**Date**: 2026-04-27
**Status**: Draft (awaiting user review)
**Author**: Riccardo Tinivella + Claude
**Branch**: `feature/plecs-expert-skill`
**Closes**: [#23 — add skills for claude](https://github.com/tinix84/pyplecs/issues/23)

## Summary

Add a `plecs-expert` Claude Code skill grounded in [docs.plexim.com/plecs/latest](https://docs.plexim.com/plecs/latest/), exposed three ways: as a Claude Code skill, as a `/plecs` slash command, and as a stdio MCP server (`pyplecs-mcp`). The skill answers PLECS authoring questions, supports the `.plecs → SPICE` netlist converter, and grounds the `PlecsServer` XML-RPC wrapper in the official API.

Content uses a hybrid sourcing strategy — verbatim factual tables (parameters, RPC signatures, XML grammar — facts, not copyrightable) plus prose rewritten in the [caveman](https://github.com/juliusbrussee/caveman) terse-fragment style — and composes answers from two layers: the offline PLECS docs reference and live introspection of `pyplecs` modules. The skill is tied to the pyplecs repo (not portable standalone) so it can call `pyplecs` as a token-saving runtime tool.

## Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | New dedicated skill (not extending `pe-expert`) | `pe-expert` stays tool-agnostic (Erickson/Maksimovic theory). Tool-specific PLECS knowledge belongs in its own skill. |
| 2 | Use-case priority: authoring → converter → wrapper | User-set ranking. Authoring is daily; converter and wrapper are bounded sub-projects benefiting from the same content. |
| 3 | Hybrid sourcing: offline reference + URL fallback | Lookup speed for common topics (offline), coverage breadth for long-tail (WebFetch). |
| 4 | Full content scope minus RT Box | RT Box becomes a separate future skill. All other PLECS chapters (components, RPC, XML, solver, masks, codegen, magnetics/thermal, C-Script, control library) are in scope. |
| 5 | Stance C: factual tables verbatim, prose rewritten | Facts aren't copyrightable; rewritten prose avoids the gray-zone of mirroring proprietary docs. Repo is public. |
| 6 | Caveman style for all rewritten prose | Token efficiency, uniform style, defensive against accidental verbatim copying. |
| 7 | Skill lives in `pyplecs/.claude/skills/plecs-expert/` (not in WSL agents_pool) | Tied to pyplecs so the skill can use pyplecs as a runtime introspection tool. |
| 8 | Production pipeline: scripted extractor for tables, hand-authored caveman prose | Caveman quality stays high (humans do it); tables stay accurate cheaply. |
| 9 | Triple delivery surface: Skill + slash command + MCP server | Same `references/` content, three access paths. |
| 10 | Stdio-only MCP transport | Matches Claude Desktop and existing `pyplecs-mcp` advertisement. HTTP excluded. |
| 11 | MCP surface read-only | No simulation execution. Future `plecs-runner` skill if needed. |
| 12 | Live introspection over snapshot for pyplecs layer | MCP server already imports pyplecs; `inspect.getmembers` is free and drift-free by construction. |

## Architecture

Two knowledge layers composed at query time:

```
┌─────────────────────────────────────────────────────────────────┐
│              pyplecs/.claude/skills/plecs-expert/               │
│                                                                 │
│   Layer A: PLECS docs (offline + URL fallback)                  │
│     references/components/*.md, rpc-api.md, plecs-xml-grammar.md│
│     solver.md, codegen.md, cscript.md, url-index.md             │
│                                                                 │
│   Layer B: PyPLECS code (live introspection)                    │
│     pyplecs.plecs_components → wrapper classes                  │
│     pyplecs.pyplecs.PlecsServer → XML-RPC surface               │
│                                                                 │
│   Composer: SKILL.md routing + MCP tool implementations         │
│     1. Wrapper exists in Layer B? → cite wrapper                │
│     2. Else Layer A? → cite reference file                      │
│     3. Else url-index.md? → WebFetch + cite URL                 │
└─────────────────────────────────────────────────────────────────┘
                ↓             ↓                ↓
        Claude Code   /plecs slash    pyplecs-mcp (stdio)
        skill auto-   command         MCP server consumed
        triggered                     by external clients
```

## File layout

```
pyplecs/
├── .claude/
│   ├── commands/
│   │   └── plecs.md                    # NEW: /plecs slash command
│   └── skills/
│       └── plecs-expert/               # NEW: single source of truth (read by skill, /plecs, MCP)
│           ├── SKILL.md                # Frontmatter + activation + index (≤ 4 KB)
│           ├── LICENSE-NOTES.md        # Verbatim/rewritten boundary, source URLs
│           ├── style/
│           │   └── caveman.md          # Prose style rules (banned words, patterns)
│           ├── references/
│           │   ├── components/
│           │   │   ├── electrical-passive.md
│           │   │   ├── electrical-sources.md
│           │   │   ├── electrical-switches.md
│           │   │   ├── electrical-meters.md
│           │   │   ├── magnetic.md
│           │   │   ├── thermal.md
│           │   │   ├── control.md
│           │   │   └── system.md
│           │   ├── rpc-api.md
│           │   ├── plecs-xml-grammar.md
│           │   ├── solver.md
│           │   ├── codegen.md
│           │   ├── cscript.md
│           │   └── url-index.md
│           ├── manifest.json           # Source URL → content hash (drift detection)
│           └── tools/
│               ├── sync_tables.py      # Scrape & extract factual tables verbatim
│               ├── check_drift.py      # Diff manifest hashes; diff pyplecs introspection
│               └── REFRESH.md          # Human refresh procedure
└── pyplecs/
    └── mcp/
        ├── __init__.py                 # CHANGE: implement create_mcp_server / main
        ├── server.py                   # NEW: MCP stdio server boilerplate
        └── plecs_tools.py              # NEW: tool implementations (read references + introspect)
```

## SKILL.md shape

Frontmatter:

```yaml
---
name: plecs-expert
description: PLECS authoring help, .plecs schematic format, XML-RPC API, and SPICE-mapping reference. Use when answering "how do I X in PLECS", working on the netlist converter, or extending the PlecsServer XML-RPC wrapper.
allowed-tools: Read, Grep, Glob, WebFetch, Bash
---
```

Body sections (caveman style, ≤ 4 KB total):

1. **What this skill knows** — topic → file table.
2. **How to use** — terse routing rules: components → `references/components/<family>.md`; RPC → `references/rpc-api.md`; XML → `references/plecs-xml-grammar.md`; long-tail → `references/url-index.md` + WebFetch.
3. **Composition rule** — check `pyplecs.plecs_components` and `PlecsServer` first; cite wrapper if present; else cite reference; else WebFetch URL.
4. **Citation rule** — every answer cites a `references/*` path or a `docs.plexim.com` URL. No ungrounded claims.
5. **Caveman style enforcement** — generated prose follows `style/caveman.md`.
6. **Boundary** — does not cover RT Box, license/purchasing decisions, or third-party libraries. RT Box → future skill.

## MCP surface

All read-only, stdio transport, registered via `pyplecs-mcp = "pyplecs.mcp:main"`.

| Tool | Layer | Purpose |
|------|-------|---------|
| `plecs_lookup(topic)` | docs | Read `references/<topic>.md` |
| `plecs_search(query)` | docs | Grep across `references/` |
| `plecs_component(name)` | composed | pyplecs wrapper if present, else docs reference |
| `plecs_rpc(function)` | composed | introspect `PlecsServer.<function>` if present, else docs |
| `plecs_xml(element)` | docs | `.plecs` XML element grammar lookup |
| `plecs_url(topic)` | docs | docs.plexim.com URL fallback |
| `pyplecs_wrappers()` | pyplecs | List `*PlecsMdl` classes in `pyplecs.plecs_components` |
| `pyplecs_rpc_surface()` | pyplecs | List `PlecsServer` public methods |

Excluded: anything that runs PLECS, opens models, or writes files.

## Content posture & licensing

`docs.plexim.com` content is Plexim's proprietary documentation. The repo is public. Posture:

- **Verbatim** — factual tables only: parameter names, defaults, units, RPC function signatures, `.plecs` XML element grammar. Facts are not copyrightable in any jurisdiction relevant here.
- **Rewritten** — all explanatory prose, in caveman style per `style/caveman.md`. Original authorship; no copy/paste from Plexim docs.
- **`LICENSE-NOTES.md`** — for every `references/*.md` file, classifies sections as `verbatim:tables` or `rewritten:prose` and lists the source URL. Auditable boundary.

If Plexim ever objects, the verbatim factual tables are the only thing that could carry risk; the rewritten prose is original. The `LICENSE-NOTES.md` makes a takedown surgical rather than a full skill removal.

## Refresh procedure

Pinned to a PLECS minor version per refresh cycle. Recorded in `manifest.json`.

1. `python .claude/skills/plecs-expert/tools/check_drift.py`
   - Fetches each URL in `manifest.json`, hashes content, compares to stored hash.
   - Introspects `pyplecs.plecs_components` and `PlecsServer`, diffs against last snapshot.
   - Output: a Markdown report listing prose pages to re-author + wrapped/not-wrapped status flips.
2. `python .claude/skills/plecs-expert/tools/sync_tables.py`
   - Re-extracts factual tables verbatim from URLs in `manifest.json`.
   - Updates table sections of each `references/*.md` in place; leaves prose untouched.
   - Refreshes `manifest.json` hashes.
3. Human pass: re-author flagged prose in caveman style per `style/caveman.md`.
4. `pytest tests/test_plecs_expert.py`.
5. Commit.

## Testing

New file `tests/test_plecs_expert.py`. All tests platform-independent (no PLECS instance, no network) so they run in the pre-push hook subset.

| Test | Checks | Why |
|------|--------|-----|
| `test_skill_md_under_4kb` | `SKILL.md` size budget | Body must stay lookup-fast |
| `test_references_no_dead_links` | every `[label](path)` resolves to an existing file | Skill answers depend on file existence |
| `test_url_index_resolvable` | URLs in `url-index.md` are syntactically valid (no fetch) | Cheap sanity, not a network test |
| `test_caveman_compliance` | rewritten prose blocks pass caveman lint (banned filler list) | Style enforcement |
| `test_license_notes_complete` | every `references/*.md` is listed in `LICENSE-NOTES.md` with classification | Auditability |
| `test_pyplecs_wrappers_introspectable` | `pyplecs.plecs_components` imports clean, has expected `*PlecsMdl` classes | MCP composition layer works |
| `test_mcp_tools_register` | importing `pyplecs.mcp` exposes the expected tool names via the registry | MCP server is wired (no subprocess required in CI) |
| `test_slash_command_routes` | `.claude/commands/plecs.md` exists and references the `plecs-expert` skill | Slash command path works |

## Completion criteria

1. `pyplecs/.claude/skills/plecs-expert/` exists with `SKILL.md`, `LICENSE-NOTES.md`, `style/caveman.md`, populated `references/` for the Full scope minus RT Box, `manifest.json`, `tools/`.
2. `pyplecs/.claude/commands/plecs.md` slash-command stub exists.
3. `pyplecs/pyplecs/mcp/` implements `create_mcp_server()` + `main()` over stdio with the 8 read-only tools.
4. `pyproject.toml` registers `pyplecs-mcp = "pyplecs.mcp:main"`.
5. `tests/test_plecs_expert.py` passes in the platform-independent subset.
6. `ruff check .` clean.
7. Manual smoke test: `pyplecs-mcp` invoked from Claude Desktop responds to `plecs_component("Inductor")` with composed pyplecs+docs answer.
8. Issue #23 closed by the merging PR.

## Out of scope

- RT Box content (separate future skill).
- Simulation execution via MCP (separate future `plecs-runner` skill).
- HTTP MCP transport.
- Auto-publish of `references/` to mkdocs / GitHub Pages — content lives under `.claude/`, not `docs/`, on purpose.
- Rewriting `pyplecs.plecs_components.py` to expand wrapper coverage (separate work; this skill consumes what's there).
- Portability of the skill folder as standalone drop-in (it depends on pyplecs as a runtime tool).

## Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| Plexim doc-site HTML structure changes break `sync_tables.py` | Parser is ≤ 200 LOC; refresh procedure expects to occasionally hand-fix it. Not run in CI. |
| Caveman-style enforcement test produces false positives on legitimate technical prose | Banned-words list is small and reviewed; test prints offending file:line for easy override via inline `<!-- caveman:allow -->` markers. |
| MCP server import-time errors brick `pyplecs-mcp` startup | `test_mcp_tools_register` imports the module + checks the tool registry; subprocess smoke is part of completion-criteria #7 (manual). |
| Live introspection of `PlecsServer` triggers network calls | `pyplecs_rpc_surface()` uses `inspect.getmembers` only — no instantiation, no XML-RPC connection. |
| Public repo accidentally publishes verbatim Plexim prose | `test_caveman_compliance` + `LICENSE-NOTES.md` discipline. PR review checks `LICENSE-NOTES.md` was updated alongside any `references/*.md` change. |
