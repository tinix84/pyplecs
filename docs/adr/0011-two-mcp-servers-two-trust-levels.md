# ADR-0011 — The Simulation MCP Server is a second server, not a mode of the first

- **Status**: Accepted
- **Date**: 2026-08-28

## Context

`pyplecs-mcp` is a stdio, read-only Documentation MCP Server: eight tools that
answer questions *about* PLECS from the offline reference. Band 3 asks for an
MCP surface over PyPLECS itself — submit a simulation, follow the Simulation
Task, read the Simulation Result (#24).

The two surfaces have different consequences when handed to a client. A docs
server can be given to anyone; nothing it does costs more than a file read. A
server that accepts a Simulation Task can start PLECS, occupy a licence, write
a Cache Record and run for minutes. Putting both behind one process means every
client that wants documentation also holds the power to run simulations, and
the only guard would be an authorization layer MCP does not provide over stdio.

Simulations are also long-running, while MCP tool calls are request/response.
The choice was between a streaming transport (HTTP/SSE) and reusing the
Simulation Task lifecycle the orchestrator already owns.

## Decision

**Two servers, two console commands, disjoint tool names.**

- `pyplecs-mcp` stays the Documentation MCP Server. It never gains a tool that
  creates a Simulation Task. Its eight tool names and behaviours are frozen.
- `pyplecs-mcp-sim` is the Simulation MCP Server: a transport over
  `SimulationOrchestrator` exposing submission, task identity and progress,
  result retrieval, cancellation, Cache Record lookup and model discovery.
- The split *is* the authorization story: the operator decides which process
  a client may launch. No tool in either server reaches the other's catalogue.
- Transport is stdio with **submit/poll over opaque task ids** plus a bounded
  wait. The lifecycle already exists; MCP only carries it. No HTTP/SSE.
- PLECS unavailability is an explicit tool error at submission, and no
  Simulation Task is created. Every other tool answers without PLECS.
- The result payload is the same normalized shape the REST sync route returns
  (`time` + named `signals`); no third result model is defined.

## Consequences

- Clients that only need documentation are unaffected by this ADR.
- Running simulations from an MCP client requires launching a second process;
  that friction is the point.
- A future streaming transport is an addition to the Simulation MCP Server,
  not a reason to merge the servers.
- Superseding this would mean either an authenticated transport that can tell
  clients apart, or a decision that the docs server may execute — either is a
  new ADR.
