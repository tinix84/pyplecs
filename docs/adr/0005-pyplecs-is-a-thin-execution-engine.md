# ADR-0005 — PyPLECS is a thin execution engine

- **Status**: Accepted
- **Date**: 2026-08-20

## Context

`pyplecs/optimizer` exists as an unimplemented placeholder. `requirements-opt.txt`
declared `optuna`, `scikit-optimize`, `deap`, `scikit-learn`, `seaborn` and
`matplotlib` for it — a full optimization stack of dependencies for code that
was never written.

The now-deleted PRDs explained why: PyPLECS was always meant to execute, and to
let the caller decide. They stated it as a boundary against one specific
orchestrator, listed advanced optimization (NSGA-II, memetic algorithms),
surrogate ML models, design-space exploration, component databases and
multi-tool coordination as out of scope, and described sibling execution tools
for magnetics and other simulators as thin in the same way.

Naming one orchestrator in the decision would be a mistake: the boundary is
worth keeping regardless of who calls, and a caller-specific rule invites the
reading that a different caller justifies a different answer. What matters is
the shape of the boundary, not the identity of the caller.

Without the decision written down, the reasoning is invisible. The placeholder
package reads as an unfinished feature rather than a deliberate exclusion, and
the next reader completes it.

## Decision

**PyPLECS executes simulations. It does not decide what to simulate.**

In scope: driving PLECS over XML-RPC, generating and parameterizing models,
expanding a Parametric Study into Simulation Tasks, scheduling and batching
them, caching Simulation Results, extracting waveforms and computing metrics
from them, and exposing all of it over an API.

Out of scope, permanently, and delegated to whatever orchestrator calls
PyPLECS: optimization algorithms, surrogate or learned models, design-space
exploration strategy, component databases, and coordination across multiple
simulation tools.

The line is *who chooses the next parameter vector*. PyPLECS accepts a set of
vectors and runs them. Choosing them adaptively from previous results is the
caller's job.

Sampling strategies that need no simulation results to produce their vectors —
a full-factorial grid, Latin hypercube, Monte Carlo draws — are in scope. They
are expansions of a Parametric Study, not decisions.

## Consequences

- `pyplecs/optimizer` is a placeholder for something that will not be built.
  The `opt` extra carries its declared dependencies but nothing imports them.
- The API surface is request/response over explicit parameter sets. PyPLECS
  never calls back into a caller to ask what to run next.
- Any issue proposing an optimizer, a surrogate model, or an adaptive search
  loop inside PyPLECS contradicts this ADR and must supersede it first.
- The boundary is stated without naming a caller, so it holds for every
  orchestrator, script, or notebook that drives PyPLECS.
- Result extraction is deliberately on the PyPLECS side of the line: efficiency,
  losses and component stress are computed *from* a Simulation Result, which
  needs no knowledge of why the simulation was requested.
