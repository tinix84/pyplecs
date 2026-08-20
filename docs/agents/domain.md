# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

This is a **single-context** repo: one `CONTEXT.md` and one `docs/adr/` at the root.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — the ubiquitous-language glossary.
- **`docs/adr/`** — read the ADRs that touch the area you're about to work in.

If either doesn't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill (reached via `/grill-with-docs` and `/improve-codebase-architecture`) creates them lazily when terms or decisions actually get resolved.

## File structure

```
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-....md
│   └── 0002-....md
└── pyplecs/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to the synonyms the glossary explicitly lists under `_Avoid_`.

For example, `CONTEXT.md` defines **Cache Record**, **Raw PLECS Result**, **Simulation Result**, and **Simulation Task** — so write "Cache Record", not "cache entry" or "cached payload".

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_

## Known open question

This repo currently records architectural decisions in the `## Decision Log` table inside `CLAUDE.md`, while the global documentation-authority convention puts them in `docs/adr/`. Two homes for the same statement type; not yet reconciled. Until it is, check both before assuming a decision is unrecorded.
