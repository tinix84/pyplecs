# ADR-0009 — TAS remains broader than the PyPLECS electrical projection

- **Status**: Accepted
- **Date**: 2026-08-27

## Context

TAS is a topology-agnostic interchange structure for sharing a complete
power-converter design across software. Its schema family can carry design
requirements, Operating Points, circuit topology and components, simulation
intent and model constraints, and computed outputs across electrical, thermal,
and magnetic domains.

Treating TAS as a PyPLECS request containing only a model reference and
parameters would erase that broader meaning and bypass the Circuit Model seam
from ADR-0001. Depending on the complete TAS schema family or a component
database at runtime would instead violate the standalone boundary from
ADR-0003 and the thin-execution boundary from ADR-0005.

## Decision

TAS remains the external, simulator-agnostic source of truth. Each simulator
consumes an explicitly bounded **projection** of it; no simulator-specific
projection redefines TAS itself.

PyPLECS consumes a standalone electrical projection. Translation crosses the
public Circuit Model before reaching a PLECS emitter. PyPLECS preserves the
complete decoded TAS source and emits structured diagnostics for content it
does not consume. Unsupported content that would change electrical execution
fails before simulation; unrelated future-domain content remains preserved
with a warning.

The projection performs no implicit repository, filesystem, network, or
component-database lookup. URI resolution is an explicit caller-supplied
capability. TAS Operating Points become ordinary Parametric Study inputs, while
PyPLECS waveforms and task outcomes stay in a PyPLECS result envelope rather
than being written into TAS computed outputs.

## Consequences

- PyPLECS must qualify compatibility claims with the supported projection; a
  successful run never means complete TAS support.
- Thermal and magnetic execution can deepen the same TAS boundary later
  without replacing it or changing the meaning of TAS.
- Adding supported TAS fields requires explicit validation, Circuit Model
  mapping where applicable, diagnostics, and regression evidence.
- PyPLECS remains portable without TAS repositories or databases installed.
- Any proposal to use TAS as a private request shape or bypass Circuit Model
  must supersede this ADR and ADR-0001.
