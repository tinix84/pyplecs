# Architecture Decision Records

Why we chose X over Y. One decision per file, numbered in the order they were
accepted, never edited after acceptance — a decision that changes is
**superseded** by a new ADR that says so.

An ADR does not describe what the code does (ADR-0004: the code does that) and
does not carry status (the issue tracker does that).

| # | Decision | Status |
|---|---|---|
| [0001](0001-circuit-model-is-the-single-interchange-seam.md) | Circuit Model is the single interchange seam | Accepted |
| [0002](0002-cache-record-identity-is-owned-by-the-topology-key-map.md) | Cache Record identity is owned by the topology key map | Accepted |
| [0003](0003-only-contracts-are-promotable-to-pycircuitsim-core.md) | Only contracts are promotable to `pycircuitsim-core` | Accepted |
| [0004](0004-code-is-the-only-architecture-truth.md) | Code is the only architecture truth | Accepted |
| [0005](0005-pyplecs-is-a-thin-execution-engine.md) | PyPLECS is a thin execution engine | Accepted |
| [0006](0006-two-model-flavors-no-merge.md) | Two model flavors, no merge | Accepted |
| [0007](0007-verbatim-tables-rewritten-prose.md) | Verbatim tables, rewritten prose | Accepted |
| [0008](0008-pyproject-and-uv-own-dependencies.md) | pyproject and uv own environment and dependencies | Accepted |
| [0009](0009-tas-is-broader-than-pyplecs-electrical-projection.md) | TAS remains broader than the PyPLECS electrical projection | Accepted |
| [0010](0010-cache-record-identity-is-a-composite-topology-key.md) | Cache Record identity is a composite topology key that never claims equality it cannot prove | Accepted |

## Writing one

```markdown
# ADR-NNNN — <decision, as a statement>

- **Status**: Accepted
- **Date**: YYYY-MM-DD

## Context
What forced a choice. The constraints, and what breaks under the alternatives.

## Decision
What we chose, stated so a reader can apply it without reading Context.

## Consequences
What follows — including the costs accepted and what would have to change to
supersede this.
```

Add a row above, and a row in the Decision Log table in `CLAUDE.md`. The
Decision Log is an index; this directory is the authority.
