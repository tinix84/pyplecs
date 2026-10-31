# ADR-0015 — PyPLECS does not import LTspice schematics

- **Status**: Accepted
- **Date**: 2026-10-30

## Context

PyPLECS built an LTspice import: a `.asc` parser into the Circuit Model, then
the existing emitter out to a runnable `.plecs`. An RC step response proved the
electrical result against PLECS. The drawing did not hold up. The emitted
schematic placed components badly, so the import was reverted on 2026-09-12.

To make the import usable, PyPLECS needs auto-placement and orthogonal wire
routing. That is drawing work, not simulation work. It competes with the
PLECS-side work for a single maintainer: the PlecsServer wrapper, the Cache
Record follow-up, and the GUI round-trip check.

Three options were open:

1. Continue the import and build auto-placement.
2. Stop all LTspice work and remove the merged LTspice pieces.
3. Stop the import only, and keep the merged LTspice pieces as they are.

Two LTspice pieces are already merged and work. The converter exports a
`.plecs` model to an LTspice `.asc` schematic through the Circuit Model. The
converter acceptance pack runs a `.cir` deck in LTspice as the reference
simulator and compares its result with PLECS. Removing them would delete
working, tested code and the only independent reference the acceptance pack
has.

## Decision

**PyPLECS does not import LTspice schematics.** Development focuses on PLECS.

The merged LTspice pieces stay, frozen:

- the `.plecs` to `.asc` export emitter, and
- LTspice as the reference simulator in the converter acceptance pack.

Frozen means fixes that keep them working are in scope. New LTspice features
are not.

ADR-0001 still holds. If an import comes back, it is a parser that produces a
Circuit Model.

## Consequences

- An issue that proposes LTspice import, auto-placement for imported
  schematics, or a new LTspice export feature contradicts this ADR and must
  supersede it first.
- The frozen pieces keep a cost. The export emitter must follow changes to the
  Circuit Model, and the acceptance reference check needs an LTspice
  installation to run.
- The reverted commits `11096a3` (import) and `6e11cd8` (drawing fidelity) hold
  the earlier work. A superseding ADR can start from them.
