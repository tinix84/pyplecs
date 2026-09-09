# ADR-0010 — Cache Record identity is a composite topology key that never claims equality it cannot prove

- **Status**: Accepted
- **Date**: 2026-08-28

## Context

A Cache Record was addressed by one digest of the model file *path*, the
entire file *bytes*, and the runtime parameters. Two consequences made repeat
work the rule rather than the exception:

- Any cosmetic edit — dragging a component, a no-op re-save, a scope window
  moved — changed the bytes and busted every record of that model.
- The digest ignored the PLECS installation. `Reference` blocks are library
  links resolved at load time whose internals never enter the file, so a PLECS
  upgrade silently served pre-upgrade waveforms
  ([research](../research/2026-08-19-plecs-reference-semantics.md)).

The wayfinder map *topology-based simulation cache key* (`#30`) charted the
replacement; ADR-0002 reserved identity for it. The tracked evidence corpus is
five `.plecs` models, none containing a `Subsystem`.

## Decision

A Cache Record is addressed by **four independently computed ids**, and a hit
requires all four:

| id | What it digests | Invariant to |
|---|---|---|
| `topology_id` | the canonical topology document: nodes (type, name, parameter *symbols*), nets (one edge set, tagged electrical/signal), subsystem ids and interfaces | layout, cosmetics, declaration order, line endings, `Goto`/`From` tag names, annotations, file `Version` |
| `params_id` | symbol bindings from `InitializationCommands`, overridden by runtime `ModelVars` | parameter *layout* in the file |
| `solver_id` | every top-level `Plecs{}` field classified as run-shaping, including initial/system state and diagnostic severities | `CodeGen*`, dialog geometry, `Name`, `Version` |
| `environment_id` | the PLECS version, resolved without starting PLECS (configuration, then executable metadata, then install directory name) | — |

Three rules govern every id:

1. **The key never claims equality it cannot prove.** A construct the
   canonicalizer does not recognise — an unknown component field, a connection
   domain it does not model, a `From` without a local `Goto`, a script
   statement that is not a scalar assignment, an unclassified top-level field —
   is folded in as lightly normalized bytes at the granularity of that
   construct, so it causes a miss, never a wrong hit. Which regions degraded is
   recorded in the document's coverage section and copied into the record
   manifest. A file that does not parse degrades whole; a file that does not
   exist is keyed by its path.
2. **An unknown environment disables caching.** Two unknown PLECS versions are
   not equal, so no key is formed and nothing is stored or served. The
   producing version is always recorded in the manifest. Excluding the
   environment from the key was rejected: it would be a practical trade-off,
   not a principled one, and it reintroduces the silently-stale failure.
3. **The canonical document is persisted and inspectable.** Records live under
   a versioned layout keyed first by `topology_id`, the document is stored once
   and shared by every parameter point, and a miss can be explained by naming
   the id that differed. Earlier records are orphaned, not migrated.

Two charting premises were overturned by the implementation and are recorded
here so nobody reopens them by accident:

- **The Circuit Model is not the canonicalizer's input.** The converter's
  Circuit Model is an electrical projection that drops signal connections,
  control blocks, subsystems and library links — all key-relevant. Both the
  canonicalizer and the Circuit Model consume the same parsed block tree; that
  parser is the "one parse". ADR-0001 is unaffected: the Circuit Model remains
  the only *interchange* seam.
- **Diagnostic severities are solver, not ignored.** A severity of `error`
  aborts a run; `warning` lets it finish. They decide whether a result exists.

## Consequences

- Repeat work after a cosmetic edit is a hit; a rewiring, a retyped component,
  a changed solver tolerance, a different PLECS version, or an edited initial
  state is a miss, and the cache can say which.
- Polarity is carried by connectivity (which terminal joins which net), so
  `Direction`/`Flipped` can be dropped for every type.
- `Subsystem` handling — one id per subsystem, interface order part of the id —
  is specified from documentation and a synthetic test fixture, not from the
  tracked corpus. The first tracked model with a subsystem should be run
  through the invariance tests before the scheme is trusted further.
- Measurement blocks (`Scope`, `Display`, `PlecsProbe`, meters) are part of
  `topology_id`. Whether they deserve an "outputs" dimension of their own is
  deferred until a caller needs results shared across probe layouts.
- A range-aware lookup (a 5 ms run answering a 1 ms request) is not offered;
  `StartTime`/`TimeSpan`/`Refine` are equality-keyed in `solver_id`.
- The one HITL acceptance step the map required — a real PLECS GUI round-trip
  showing what a no-op save rewrites — is still owed; until it lands, the
  invariance set rests on synthetic perturbation of the corpus and on the
  cosmetic variants already present in the local model set.
- Superseding this ADR means changing what a Cache Record *is*; changing what
  happens to one (expiration, clearing, statistics) does not touch it.
