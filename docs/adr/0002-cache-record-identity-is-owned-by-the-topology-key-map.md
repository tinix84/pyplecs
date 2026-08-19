# ADR-0002 — Cache Record identity is owned by the topology-key map, not the architecture epic

- **Status**: Accepted
- **Date**: 2026-08-19

## Context

Two efforts write the same statement.

`#30` is a `wayfinder:map` — *Wayfinder: topology-based simulation cache key* —
whose entire purpose is to decide what a **Cache Record**'s identity is made of:
which `Plecs{}` fields are topology, whether environment identity (PLECS
version) participates, how canonicalization degrades and what the coverage
record holds.

`#29` is an architecture epic whose track 1, *Deepen the Cache Record lifecycle*,
states that one deep cache module "owns Cache Record **identity**, expiration,
payload, metadata, invalidation, clearing, and statistics", and whose deletion
test names *hashing*.

Left as written, `#29` would settle by refactor a question `#30` exists to
settle by design.

## Decision

**Cache Record identity is owned by `#30`.** Track 1 of `#29` is reduced to
Cache Record *lifecycle*: expiration, invalidation, clearing, statistics, and
removal of the one-adapter `CacheBackend` seam. Identity and hashing are struck
from its scope and carry a pointer to `#30`.

`#29` does **not** block on `#30`. Lifecycle is orthogonal to what the key is
made of, and tracks 2–5 never touched identity, so both efforts proceed in
parallel.

## Consequences

- `#30`'s outcome lands in a cache module that has already been deepened, which
  is the easier order.
- The two efforts touch `pyplecs/cache/__init__.py` concurrently; the boundary
  between them is "what the key is" versus "what happens to the record", and
  reviewers should enforce it.
- If `#30` concludes that identity cannot be separated from lifecycle, this ADR
  is the thing to reopen.
