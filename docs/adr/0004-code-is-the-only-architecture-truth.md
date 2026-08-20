# ADR-0004 — Code is the only architecture truth

- **Status**: Accepted
- **Date**: 2026-08-20

## Context

`docs/` had grown to 97 files. Among them were four surfaces that each asserted
what PyPLECS is or must do:

- `docs/architecture.md` (156 lines) — layers, data flow, a file-structure tree.
- `docs/prd.md` (215 lines) — a feature table with a Status column.
- `docs/prd_future.md` (562 lines) — a six-month phase plan with code samples
  for classes that do not exist.
- `docs/tas_sprint_planning_converter_lib.md` (1569 lines) — sprint planning.

All four drifted. `prd.md` claimed a `pyplecs/tas/` package that was never
written; `prd_future.md` specified method bodies that predate the Circuit Model
seam of ADR-0001; the architecture tree listed `docs/prd.md` as a live document
describing a v2.0 that no issue tracks. A reader could not tell which of the
four to believe, and none of them was the code.

Alongside them sat a full user-documentation set (`install.md`, `api.md`,
`webgui.md`, `migration.md`, `contributing.md`, 12 install variants across
several files) and 47 files of marketing articles. `docs/superpowers/`
tracked four plan and spec files in git, which the documentation-authority
convention classifies as temporary and gitignored.

The general failure is structural, not editorial: a prose description of what
the code does is a second source of truth that nothing checks, and it always
loses to the code.

## Decision

**The code is the only description of what PyPLECS is.** No tracked document
describes structure, layers, data flow, or behaviour.

`docs/` holds exactly four kinds of statement, and nothing else:

| Path | Owns |
|---|---|
| `docs/adr/` | Why we chose X over Y |
| `docs/story-map.md` | The long-term outcome and the shape of the journey — solution-neutral, status-free |
| `docs/research/` | Findings and their sources |
| `docs/agents/` | How agents should consume this repo |

Plus `docs/index.md`, which is a one-line snippet include of `README.md` so
mkdocs has a home page and no text is duplicated.

Terminology lives in `CONTEXT.md` at the root. Specs and status live as GitHub
issues. Plans are gitignored and disposable. `README.md` is the single
user-facing document, capped at 150 lines across five fixed sections.

Removal means `git rm --cached` plus a move into the gitignored `.trash/`;
git history is the archive.

## Consequences

- ~88 files leave `docs/`. Their content is recoverable through
  `git log --diff-filter=D`.
- The published mkdocs site shrinks to Home / Story Map / ADRs / Agents /
  Research. The `articles/` decision of 2026-04-25 is superseded.
- The install story compresses into README. Twelve documented install variants
  become one, which is only possible because ADR-0008 makes `uv` own the
  environment.
- Three rules become machine-checked in the pre-push gate, because a rule
  nothing checks is how `docs/` reached 97 files: `docs/` may contain nothing
  outside the allowlist; no `requirements*.txt` or `setup.py` may reappear;
  `README.md` stays within its line cap.
- The global documentation-authority map loses its "what exists now →
  `docs/architecture.md`" and "what the product must do → `docs/prd.md`" rows.
  Without that amendment the next authority-driven session recreates both files.
- Anyone wanting an architectural overview reads `pyplecs/__init__.py`, the
  ADRs, and the package map in README. There is no narrative middle layer, and
  adding one back is a decision that supersedes this ADR.
