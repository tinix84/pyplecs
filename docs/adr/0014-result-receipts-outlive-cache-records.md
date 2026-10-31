# ADR-0014 — Result Receipts outlive Cache Records

- **Status**: Accepted
- **Date**: 2026-09-13

## Context

Band 2 requires Repeat-work Rate and Answer Traceability to remain readable
from stored state after a process restart. A Cache Record exists to decide
whether a waveform may be reused; its ordinary lifecycle includes expiration,
invalidation and clearing. Using that same lifecycle for delivery history would
erase evidence whenever an engineer performs normal cache maintenance. Keeping
waveform payloads solely for auditability would instead defeat expiration and
unnecessarily retain large results.

## Decision

Every successfully delivered Simulation Result has a Result Receipt linking its
Simulation Task to the resolution path and Result Provenance. Result Receipts
have a lifecycle independent from Cache Records: Cache Record expiration,
invalidation and `clear_cache` do not remove them. Receipts contain no waveform
payload and are removed only through a separate, explicit retention or pruning
operation.

## Consequences

- Historical Repeat-work Rate and per-task provenance remain available after
  cache maintenance and process restarts.
- A Result Receipt may remain after its Cache Record and waveform payload are
  gone; its immutable producing identity remains meaningful without making the
  result reusable.
- Successful deliveries add small durable records, so retention limits and
  explicit pruning need their own design and must not be hidden inside cache
  operations.

