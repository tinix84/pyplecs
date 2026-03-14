# PyPLECS - Product Requirements Document (Current State)

**Version**: 1.0.0
**Date**: 2026-02-01
**Status**: Active Development

---

## Executive Summary

PyPLECS is a **thin execution engine** for PLECS power electronics simulation. It provides batch execution, caching, and API capabilities - designed to be called by NTBEES2 (the intelligent orchestrator) via TAS format.

**Core Principle**: PyPLECS does execution. NTBEES2 does intelligence.

```
NTBEES2 (Intelligence)
├── Advanced optimization (MA, NSGA-II/III)
├── Surrogate ML models
├── Design decisions
│
└── TAS ──→ PyPLECS (Execution)
            ├── TAS → .plecs generation
            ├── PLECS simulation
            ├── Caching
            ├── Parameter sweeps
            └── Waveform/KPI extraction
                    │
                    ▼
                 PLECS
```

---

## Problem Statement

### Target User

**NTBEES2** (primary) - needs a reliable PLECS execution backend
**Power Electronics Engineers** (secondary) - direct usage for simple tasks

### Pain Points

| Pain Point | Severity | Solution |
|------------|----------|----------|
| PLECS has no Python API | HIGH | XML-RPC wrapper |
| Repeated simulations waste time | HIGH | Hash-based caching |
| No batch automation | MEDIUM | Batch execution |
| Manual .plecs file creation | MEDIUM | TAS → .plecs generation |

### Origin Story

PyPLECS was created **before PLECS had native batch simulation** to:
1. Enable batch parameter sweeps via Python
2. Generate waveforms for component stress analysis
3. Feed simulation results into optimization loops (in NTBEES2)

---

## Current Product State (v1.0.0)

### What Works

| Feature | Status | Description |
|---------|--------|-------------|
| XML-RPC wrapper | ✅ Stable | `PlecsServer` class |
| Batch simulation | ✅ Stable | `simulate_batch()` |
| Hash-based caching | ✅ Stable | SHA256, Parquet storage |
| REST API | ✅ Stable | FastAPI endpoints |
| Web GUI | ✅ Stable | Dashboard, queue monitoring |
| Priority queue | ✅ Stable | CRITICAL/HIGH/NORMAL/LOW |

### What's Missing (for v2.0)

| Feature | Priority | Notes |
|---------|----------|-------|
| TAS → .plecs generation | 🔴 Critical | Can't receive NTBEES2 jobs |
| Parameter sweeps | 🟡 High | Grid, Latin Hypercube |
| Waveform extraction | 🟡 High | Stress analysis |
| KPI calculation | 🟡 High | Efficiency, losses |

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      PyPLECS v1.0.0                         │
├─────────────────────────────────────────────────────────────┤
│  Entry Points                                               │
│  pyplecs-setup | pyplecs-gui | pyplecs-api                  │
├─────────────────────────────────────────────────────────────┤
│  API Layer              │  Web Layer                        │
│  REST (FastAPI)         │  Dashboard (Jinja2)               │
├─────────────────────────┼───────────────────────────────────┤
│  Orchestration          │  Cache                            │
│  Priority queue         │  SHA256 hash                      │
│  Batch executor         │  Parquet storage                  │
├─────────────────────────┴───────────────────────────────────┤
│  Core: PlecsServer (XML-RPC wrapper)                        │
├─────────────────────────────────────────────────────────────┤
│  PLECS (external, requires license)                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Integration with NTBEES2

### TAS (Topology Agnostic Structure)

TAS is the **standardized JSON format** for power electronics. NTBEES2 generates TAS, PyPLECS consumes it.

**TAS is source of truth** → .plecs is generated artifact

### Data Flow

```
NTBEES2                          PyPLECS                      PLECS
   │                                │                           │
   │  TAS (operating points,        │                           │
   │       parameters, model ref)   │                           │
   ├───────────────────────────────►│                           │
   │                                │  .plecs (generated)       │
   │                                ├──────────────────────────►│
   │                                │                           │
   │                                │  Simulation results       │
   │                                │◄──────────────────────────┤
   │  TAS outputs (waveforms,       │                           │
   │       KPIs, efficiency)        │                           │
   │◄───────────────────────────────┤                           │
```

### TAS ↔ .plecs Mapping

| Direction | Scope | Status |
|-----------|-------|--------|
| TAS → .plecs | Generate model from TAS topology + params | ❌ Not implemented |
| .plecs → TAS | Extract component values | ❌ Not MVP |

**PLECS owns**: Layout, GUI elements, visual positioning
**TAS owns**: Topology, parameters, operating points

---

## Ecosystem Context

### Sibling Products (Same Pattern)

| Product | Domain | Integration |
|---------|--------|-------------|
| **PyPLECS** | Circuit simulation | TAS ↔ .plecs |
| **PyMKF** | Magnetic design | TAS ↔ MAS (OpenMagnetics) |
| **PyGecko** (planned) | Open-source sim | TAS ↔ GeckoCIRCUITS |
| **PyLTspice** (future) | SPICE validation | TAS ↔ .asc |

All are **thin execution engines** called by NTBEES2.

### What NTBEES2 Provides

| Capability | Location |
|------------|----------|
| Advanced optimization (MA, NSGA-II/III) | NTBEES2 |
| Surrogate ML models | NTBEES2 |
| Multi-tool orchestration | NTBEES2 |
| Design space exploration | NTBEES2 |
| Component database | NTBEES2 |

### What PyPLECS Provides

| Capability | Location |
|------------|----------|
| PLECS execution | PyPLECS |
| Caching | PyPLECS |
| Parameter sweeps (basic) | PyPLECS |
| Waveform extraction | PyPLECS |
| REST API | PyPLECS |

---

## File Structure

```
pyplecs/
├── __init__.py           # Package exports
├── pyplecs.py            # PlecsServer (XML-RPC)
├── config.py             # Configuration
├── core/models.py        # SimulationRequest, SimulationResult
├── orchestration/        # Priority queue, batch
├── cache/                # SHA256 caching
├── api/                  # REST endpoints
├── webgui/               # Dashboard
├── tas/                  # ⚠️ MISSING - TAS integration
│   ├── parser.py         # Parse TAS JSON
│   ├── generator.py      # Generate .plecs from TAS
│   └── extractor.py      # Extract results to TAS
└── sweeps/               # ⚠️ MISSING - Parameter sweeps
    ├── grid.py           # Grid search
    └── lhs.py            # Latin Hypercube
```

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Cache speedup | 100-1000x | Maintain |
| Batch speedup | 3-5x | Maintain |
| TAS integration | ❌ None | ✅ Full |
| NTBEES2 compatibility | ❌ | ✅ |

---

## References

- [PLECS Documentation](https://www.plexim.com/products/plecs)
- [TAS Sprint Planning](./tas_sprint_planning_converter_lib.md)
