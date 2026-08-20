# ADR-0001 — Circuit Model is the single interchange seam

- **Status**: Accepted
- **Date**: 2026-08-19

## Context

PyPLECS accumulated four separate issues proposing conversion to and from other
tools: `#9` (KiCad), `#10` (QSpice), `#11` (LTspice), and `#20` (PLECS → SPICE
`.cir` + LTspice `.asc`). The first three were one-line stubs; `#20` carries a
full design spec.

Read as four features they imply four independent parsers and emitters. They are
not independent: `#20` already emits LTspice, and its spec introduces a
tool-neutral **Circuit Model** (`Component` / `Net` / `Circuit`) sitting between
the `.plecs` parser and every emitter. Every other format is an adapter on that
same model.

## Decision

The **Circuit Model** is the single interchange seam. Exactly one module owns it.

- Reading a foreign format means writing a parser that produces a Circuit Model.
- Writing a foreign format means writing an emitter that consumes one.
- No format-to-format path may bypass the model.

Consequently no interchange format can be specified before the Circuit Model's
shape is fixed, and `#20` is what fixes it. `#9`, `#10` and `#11` are closed as
superseded and replaced by a single issue whose tracks are blocked by `#20`.

## Consequences

- Adding a format is bounded work — one adapter, not a pipeline.
- Component-type coverage is a property of the mapper, shared across formats,
  rather than being re-derived per tool.
- The Circuit Model becomes a load-bearing public shape; changing it is a
  breaking change for every adapter.
- Bidirectional conversion stays out of scope until an import adapter exists;
  `#20` is export-only by its own spec.
