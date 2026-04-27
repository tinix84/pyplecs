---
name: plecs-expert
description: PLECS authoring help, .plecs schematic format, XML-RPC API, and SPICE-mapping reference. Use when answering "how do I X in PLECS", working on the netlist converter, or extending the PlecsServer XML-RPC wrapper.
allowed-tools: Read, Grep, Glob, WebFetch, Bash
---

# PLECS Expert

Lookup-first PLECS reference grounded in docs.plexim.com. Two layers:

- **Layer A — offline docs**: `references/`. Verbatim factual tables + caveman prose.
- **Layer B — pyplecs code**: `pyplecs.plecs_components`, `pyplecs.pyplecs.PlecsServer`. Live introspection.

## Routing

| Topic | File |
|-------|------|
| Electrical passives (R, L, C, transformer) | `references/components/electrical-passive.md` |
| Sources (V, I, signal) | `references/components/electrical-sources.md` |
| Switches (MOSFET, IGBT, diode) | `references/components/electrical-switches.md` |
| Meters & scopes | `references/components/electrical-meters.md` |
| Magnetic blocks | `references/components/magnetic.md` |
| Thermal blocks | `references/components/thermal.md` |
| Control library | `references/components/control.md` |
| Subsystems & masks | `references/components/system.md` |
| XML-RPC API | `references/rpc-api.md` |
| `.plecs` XML grammar | `references/plecs-xml-grammar.md` |
| Solver | `references/solver.md` |
| Codegen (PLECS Coder) | `references/codegen.md` |
| C-Script block | `references/cscript.md` |
| Long-tail topics | `references/url-index.md` (then WebFetch the listed URL) |

## Composition rule

For component or RPC questions, check Layer B first. If a `*PlecsMdl` class exists in `pyplecs.plecs_components`, cite the wrapper. If a method exists on `PlecsServer`, cite it. Else cite Layer A. Else WebFetch from `references/url-index.md`.

## Citation rule

Every answer cites a `references/*` path or a `docs.plexim.com` URL. No ungrounded claims.

## Style

Generated prose follows `style/caveman.md`: fragments OK, drop articles/hedging/filler, pattern `[thing] [action] [reason]. [next step].`.

## Boundary

This skill does not cover: PLECS RT Box (separate future skill), license/purchasing, third-party libraries.
