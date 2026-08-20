# PyPLECS

PyPLECS executes and coordinates PLECS simulations, preserving their requests and results across synchronous, batched, and cached workflows.

## Language

**Cache Record**:
The stored representation of one simulation result for one model-and-parameter identity, including its expiration information. It exists and expires as a whole.
_Avoid_: Cache entry, cached payload

**Circuit Model**:
The tool-neutral representation of one circuit as components and nets, produced by a parser and consumed by an emitter. It is the single seam every interchange format passes through; no format-to-format path bypasses it.
_Avoid_: Netlist model, intermediate representation, circuit graph

**Parametric Study**:
One request that expands into many Simulation Tasks over a set of parameter vectors, and reduces their Simulation Results into a single aggregate outcome. How the vectors are generated is a strategy, not part of the study itself.
_Avoid_: Sweep, batch run, parameter scan

**Raw PLECS Result**:
The unvalidated outcome returned by PLECS for one simulation. Its shape depends on the simulated model and requested outputs.
_Avoid_: PLECS response, raw result data

**Simulation Result**:
The validated PyPLECS outcome of one simulation, representing either successful output or an explicit failure.
_Avoid_: Parsed result, response payload

**Simulation Task**:
The tracked execution of one simulation request from acceptance through a terminal outcome.
_Avoid_: Job, queue item

**Weighted OP Table**:
A set of operating points, each a parameter vector carrying the fraction of time a mission profile spends there. It is the input shape of a Parametric Study driven by a mission profile.
_Avoid_: Histogram, OP list, binned profile
