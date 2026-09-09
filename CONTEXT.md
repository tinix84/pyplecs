# PyPLECS

PyPLECS executes and coordinates PLECS simulations, preserving their requests and results across synchronous, batched, and cached workflows.

## Language

**Cache Key**:
The composite identity of a Cache Record: a topology id, a params id, a solver id and an environment id, each computed independently. A hit requires all four to match, so a miss can name the one that differed.
_Avoid_: Simulation hash, model hash, cache hash

**Cache Record**:
The stored representation of one simulation result for one Cache Key, including its expiration information. It exists and expires as a whole.
_Avoid_: Cache entry, cached payload

**Circuit Model**:
The tool-neutral representation of one circuit as components and nets, produced by a parser and consumed by an emitter. It is the single seam every interchange format passes through; no format-to-format path bypasses it.
_Avoid_: Netlist model, intermediate representation, circuit graph

**Coverage**:
The part of a Topology Document that records which regions of a schematic the canonicalizer understood and which it folded in as normalized bytes. A degraded region can cause a miss, never a wrong hit.
_Avoid_: Fallback list, unsupported list

**Design Quantity**:
A number or named waveform an engineer's decision turns on — stress, efficiency, loss, ripple — computed on demand from one Simulation Result under a Signal Map and an optional steady-state window. It is never stored in a Cache Record.
_Avoid_: Derived result, post-processing, metric, KPI

**Documentation MCP Server**:
The read-only MCP surface that exposes the PLECS and PyPLECS documentation catalogue. It helps an Orchestrator discover APIs and component information, but cannot create a Simulation Task.
_Avoid_: PyPLECS MCP, live MCP

**Evidence Bundle**:
What a reviewer retains from one acceptance run: the manifest as it was, the tool versions, the Design Quantities and their comparison, a human-readable summary and an overlay. It is the record that lets a run be signed off without being repeated.
_Avoid_: Test output, artifacts, debug plots

**Operating Point**:
One named parameter vector describing a condition the converter is asked to run at. It carries values, not results; a set of them is what a Parametric Study expands over.
_Avoid_: OP, test point, working point, case

**Orchestrator**:
Any caller that decides which simulations PyPLECS should run — a script, a notebook, or an external design tool. PyPLECS never names a specific one, and never decides on its behalf.
_Avoid_: Client, driver, the framework

**Parametric Study**:
One request that expands into many Simulation Tasks over a set of parameter vectors, and reduces their Simulation Results into a single aggregate outcome. How the vectors are generated is a strategy, not part of the study itself.
_Avoid_: Sweep, batch run, parameter scan

**PLECS Environment**:
The PLECS installation whose results a Cache Record holds, identified by its version. An unknown environment disables caching rather than being treated as equal to another unknown.
_Avoid_: PLECS install, runtime, host

**Raw PLECS Result**:
The unvalidated outcome returned by PLECS for one simulation. Its shape depends on the simulated model and requested outputs.
_Avoid_: PLECS response, raw result data

**Simulation Result**:
The validated PyPLECS outcome of one simulation, representing either successful output or an explicit failure.
_Avoid_: Parsed result, response payload

**Signal Map**:
The caller's declaration of which Simulation Result columns are the voltage and current of each component and port. PyPLECS infers no role from a signal name; a role not declared is not computed.
_Avoid_: Probe convention, naming convention, channel list

**Simulation MCP Server**:
The executable MCP surface that accepts simulation requests, exposes Simulation Task progress, and returns Simulation Results. It is a transport over PyPLECS simulation behavior, not a documentation catalogue.
_Avoid_: PyPLECS MCP, docs MCP, live MCP

**Simulation Task**:
The tracked execution of one simulation request from acceptance through a terminal outcome.
_Avoid_: Job, queue item

**TAS (Topology Agnostic Structure)**:
A simulator-agnostic interchange structure for a complete power-converter design. It carries design requirements and Operating Points, a topology assembled from circuit stages and components, optional simulation intent and model constraints, and optional computed outputs. Each tool consumes the domains it supports; TAS remains broader than any one simulator.
_Avoid_: TAS request, topology format, TAS file, spec JSON

**TAS Electrical Projection**:
The explicitly bounded electrical view of TAS that PyPLECS can consume without redefining or discarding the broader source structure. It is one tool's capability boundary, not a smaller TAS format.
_Avoid_: TAS support, TAS converter, partial TAS

**Topology Document**:
The persisted, inspectable canonical form of one schematic: what it is, minus how it is drawn. Its digest is the topology id of a Cache Key; two documents can be diffed to explain a miss.
_Avoid_: Canonical form, normalized model, topology hash

**Weighted OP Table**:
A set of operating points, each a parameter vector carrying the fraction of time a mission profile spends there. It is the input shape of a Parametric Study driven by a mission profile.
_Avoid_: Histogram, OP list, binned profile
