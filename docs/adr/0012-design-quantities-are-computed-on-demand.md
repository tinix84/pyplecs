# ADR-0012 — Design Quantities are computed on demand under a caller-declared Signal Map, never cached

- **Status**: Accepted
- **Date**: 2026-08-28

## Context

Band 3 turns traces into the quantities a design decision needs (#52):
per-component stress, efficiency, loss breakdown, settled waveforms. Two
questions were open.

*Where does the attribution come from?* Loss per component needs to know which
result column is that component's voltage and which its current. The options
were a naming convention (`v_S1`, `i_S1`), a probe convention inside the
model, or an explicit declaration from the caller. Conventions produce vacuous
answers when violated — ntbees2's comparison helpers silently skipped missing
signals (#58), which is exactly the failure a converter acceptance cannot
afford.

*Where does the derived output live?* Storing quantities in the Cache Record or
the Simulation Result means a record written before a derivation existed, or
before a bug in it was fixed, answers a request it cannot satisfy. The Cache
Key (ADR-0010) identifies the *simulation*; it has no term for the analysis
version, and adding one would bust every record on every analysis change.

## Decision

- **The caller declares roles in a Signal Map.** Per component and per port,
  which column is the voltage and which the current, plus a sign for ports.
  PyPLECS infers nothing from names. An undeclared role is not computed; a
  declared column that is missing is an error, never a zero.
- **Design Quantities are a pure function** of one Simulation Result, one
  Signal Map and an optional steady-state window. They are computed on demand
  by every transport (Python, REST, Simulation MCP Server) and stored nowhere.
  The Cache Record keeps holding traces only.
- **The steady-state window is deterministic**: the last N complete periods of
  the declared switching frequency, anchored at the end of the run, with the
  window start interpolated between samples. A run shorter than N periods is an
  error, not a shorter window.
- **Design Quantities are time-weighted** with exact piecewise-linear integration
  (trapezoidal for the mean, exact quadratic for RMS and power), so a
  variable-step solver's sample density does not bias them.
- Consistent with ADR-0005, the quantities are reported, never judged: no
  ratings, derating or pass/fail live here.

## Consequences

- Quantities from a cached and a fresh Simulation Result are identical by
  construction; caching stays invisible to column 5.
- Recomputation cost is paid per request. Traces are already in memory when a
  task is queried; the arithmetic is linear in samples.
- Loss attribution by mechanism (conduction vs switching vs magnetic) is not
  derivable from ideal electrical traces and is deferred until PLECS thermal
  outputs are normalized into the Simulation Result.
- Superseding this — persisting quantities — requires an analysis-version term
  in the Cache Key or a second, separately keyed store; either is a new ADR.
