# PyPLECS - Future Product Vision (v2.0)

**Version**: 2.0.0 (Target)
**Date**: 2026-02-01
**Target Release**: Q3 2026 (6 months)
**Status**: Planning

---

## Vision Statement

**PyPLECS 2.0** is a **thin, fast, reliable execution engine** for PLECS simulation. It receives TAS-formatted requests from NTBEES2, executes simulations, and returns results. Intelligence stays in NTBEES2.

> "Run PLECS simulations at scale. Fast. Cached. API-driven."

---

## Core Principle: Thin Execution Engine

```
┌─────────────────────────────────────────────────────────────────┐
│                    NTBEES2 (Intelligence)                       │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Optimizer   │  │ Surrogate   │  │ Design      │             │
│  │ MA, NSGA-II │  │ ML Models   │  │ Decisions   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │ TAS
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PyPLECS 2.0 (Execution)                      │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ TAS→.plecs  │  │ Execution   │  │ Caching     │             │
│  │ Generator   │  │ XML-RPC     │  │ SHA256      │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Param Sweep │  │ Waveform    │  │ REST API    │             │
│  │ Grid, LHS   │  │ Extraction  │  │ Sync+Async  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
                        PLECS
```

---

## Scope Definition

### IN Scope (PyPLECS 2.0)

| Feature | Description | Priority |
|---------|-------------|----------|
| TAS → .plecs generation | Generate PLECS model from TAS | 🔴 Critical |
| PLECS execution | Run simulations via XML-RPC | ✅ Exists |
| Caching | Hash-based result caching | ✅ Exists |
| Parameter sweeps | Grid search, Latin Hypercube | 🟡 High |
| Waveform extraction | Time-series outputs | 🟡 High |
| KPI calculation | Efficiency, losses, stress | 🟡 High |
| REST API | Sync + async modes | ✅ Exists |
| Batch execution | Parallel simulation | ✅ Exists |

### OUT of Scope (Lives in NTBEES2)

| Feature | Reason |
|---------|--------|
| Advanced optimization (NSGA-II, MA) | NTBEES2 orchestrates |
| Surrogate ML models | NTBEES2 owns training data |
| Design decisions | NTBEES2 has domain knowledge |
| Component database | NTBEES2 manages |
| Multi-tool orchestration | NTBEES2 coordinates |

### NOT Priority

| Feature | Status |
|---------|--------|
| MCP/LLM integration | Defer to later |
| .plecs → TAS parsing | Not MVP |
| Cloud execution | Defer to later |

---

## Feature Roadmap (6 Months)

### Phase 1: TAS Integration (Months 1-2)

**Goal**: PyPLECS can receive TAS, generate .plecs, run simulation, return TAS outputs

#### Task 1.1: TAS Parser (1 week)

Parse incoming TAS JSON to extract:
- Operating points (parameters, frequency, duty cycle)
- Component values to sweep
- Output variables to capture

```python
# pyplecs/tas/parser.py
class TASParser:
    def parse(self, tas_json: dict) -> SimulationConfig:
        """Extract simulation config from TAS."""
        return SimulationConfig(
            operating_points=self._parse_operating_points(tas_json),
            parameters=self._parse_parameters(tas_json),
            outputs=self._parse_outputs(tas_json),
            plecs_model=tas_json["converter"]["plecs_model"]
        )
```

#### Task 1.2: .plecs Generator (2 weeks)

Generate PLECS XML from TAS topology + parameters:

```python
# pyplecs/tas/generator.py
class PlecsGenerator:
    def generate(self, tas: TAS, template: Path) -> Path:
        """Generate .plecs file from TAS.

        Args:
            tas: Parsed TAS document
            template: Base .plecs template with topology

        Returns:
            Path to generated .plecs file with parameters applied
        """
        # Load template
        plecs_xml = self._load_template(template)

        # Apply parameters from TAS
        for param, value in tas.parameters.items():
            plecs_xml = self._set_parameter(plecs_xml, param, value)

        # Write generated file
        output_path = self._get_output_path(tas)
        self._write_plecs(plecs_xml, output_path)

        return output_path
```

#### Task 1.3: TAS Result Formatter (1 week)

Format simulation results as TAS outputs:

```python
# pyplecs/tas/extractor.py
class TASExtractor:
    def extract(self, sim_result: SimulationResult) -> dict:
        """Format results as TAS outputs section."""
        return {
            "outputs": {
                "operating_point_results": [{
                    "operating_point": sim_result.operating_point,
                    "waveforms": self._extract_waveforms(sim_result),
                    "efficiency": self._calculate_efficiency(sim_result),
                    "losses": self._calculate_losses(sim_result),
                    "component_stress": self._extract_stress(sim_result)
                }]
            }
        }
```

#### Task 1.4: API Endpoints (1 week)

New TAS-aware endpoints:

```python
# Sync execution
POST /api/v1/simulate/tas
{
    "tas": { ... },
    "options": {
        "cache": true,
        "extract_waveforms": ["Vout", "Iout"]
    }
}

# Async execution
POST /api/v1/simulate/tas/async
→ Returns task_id

GET /api/v1/simulate/tas/{task_id}
→ Returns status or results
```

**Deliverable**: NTBEES2 can send TAS, get TAS outputs back

---

### Phase 2: Parameter Sweeps (Month 2-3)

**Goal**: Built-in support for parameter space exploration

#### Task 2.1: Grid Search (1 week)

```python
# pyplecs/sweeps/grid.py
class GridSweep:
    def generate(self, space: dict) -> List[dict]:
        """Generate grid of parameter combinations.

        Args:
            space: {"Lout": [10e-6, 50e-6, 100e-6], "fsw": [50e3, 100e3]}

        Returns:
            List of parameter dicts to simulate
        """
        keys = list(space.keys())
        values = list(space.values())

        combinations = []
        for combo in itertools.product(*values):
            combinations.append(dict(zip(keys, combo)))

        return combinations
```

#### Task 2.2: Latin Hypercube Sampling (1 week)

```python
# pyplecs/sweeps/lhs.py
from scipy.stats import qmc

class LatinHypercubeSweep:
    def generate(self, space: dict, n_samples: int) -> List[dict]:
        """Generate Latin Hypercube samples.

        Args:
            space: {"Lout": (10e-6, 100e-6), "fsw": (50e3, 200e3)}
            n_samples: Number of samples to generate

        Returns:
            List of parameter dicts
        """
        sampler = qmc.LatinHypercube(d=len(space))
        samples = sampler.random(n=n_samples)

        # Scale to parameter ranges
        return self._scale_samples(samples, space)
```

#### Task 2.3: Sweep API (1 week)

```python
POST /api/v1/sweep
{
    "tas": { ... },
    "sweep": {
        "type": "latin_hypercube",
        "parameters": {
            "Lout": {"min": 10e-6, "max": 100e-6},
            "fsw": {"min": 50e3, "max": 200e3}
        },
        "n_samples": 50
    }
}

# Response
{
    "task_id": "sweep-123",
    "total_simulations": 50,
    "cached": 12,
    "to_run": 38
}
```

**Deliverable**: NTBEES2 can request parameter sweeps

---

### Phase 3: Waveform & KPI Extraction (Month 3-4)

**Goal**: Extract useful metrics from simulation results

#### Task 3.1: Waveform Capture (1 week)

```python
# pyplecs/analysis/waveforms.py
class WaveformCapture:
    def capture(self, sim_result, variables: List[str]) -> dict:
        """Capture time-series waveforms.

        Returns:
            {
                "Vout": {"time": [...], "values": [...]},
                "Iout": {"time": [...], "values": [...]}
            }
        """
```

#### Task 3.2: Stress Analysis (1 week)

Extract component stress metrics for sizing:

```python
# pyplecs/analysis/stress.py
class StressAnalyzer:
    def analyze(self, waveforms: dict) -> dict:
        """Calculate component stress metrics.

        Returns:
            {
                "Q_HS": {
                    "Vds_peak": 850,
                    "Vds_rms": 420,
                    "Id_peak": 25,
                    "Id_rms": 12.5,
                    "dVdt_max": 50e9
                },
                "C_out": {
                    "I_ripple_rms": 8.2,
                    "V_ripple_pp": 0.5
                }
            }
        """
```

#### Task 3.3: Efficiency & Loss Calculation (1 week)

```python
# pyplecs/analysis/efficiency.py
class EfficiencyCalculator:
    def calculate(self, sim_result) -> dict:
        """Calculate efficiency and loss breakdown.

        Returns:
            {
                "efficiency": 97.2,
                "losses": {
                    "total": 140,
                    "conduction": 60,
                    "switching": 50,
                    "magnetic": 25,
                    "other": 5
                }
            }
        """
```

**Deliverable**: Rich KPIs returned to NTBEES2

---

### Phase 4: Robustness & Performance (Month 4-5)

**Goal**: Production-ready reliability

| Task | Description | Effort |
|------|-------------|--------|
| Error handling | Graceful failure, retry logic | 1 week |
| Timeout management | Kill stuck simulations | 3 days |
| Parallel execution | Maximize PLECS batch API | 1 week |
| Cache optimization | LRU eviction, size limits | 1 week |
| Logging & monitoring | Structured logs, metrics | 1 week |

---

### Phase 5: Testing & Documentation (Month 5-6)

| Task | Description | Effort |
|------|-------------|--------|
| Unit tests | 80% coverage target | 2 weeks |
| Integration tests | TAS round-trip tests | 1 week |
| E2E tests with NTBEES2 | Real workflow validation | 1 week |
| API documentation | OpenAPI spec, examples | 1 week |
| User guide | How to use with NTBEES2 | 3 days |

---

## Architecture (v2.0)

```
┌────────────────────────────────────────────────────────────────┐
│                        PyPLECS 2.0                             │
├────────────────────────────────────────────────────────────────┤
│  API Layer                                                     │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐   │
│  │ REST API       │  │ Web GUI        │  │ CLI            │   │
│  │ /simulate/tas  │  │ Dashboard      │  │ pyplecs-cli    │   │
│  │ /sweep         │  │ Queue monitor  │  │                │   │
│  └────────────────┘  └────────────────┘  └────────────────┘   │
├────────────────────────────────────────────────────────────────┤
│  TAS Integration Layer (NEW)                                   │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐   │
│  │ TAS Parser     │  │ .plecs Gen     │  │ TAS Formatter  │   │
│  │ JSON → Config  │  │ Config → XML   │  │ Results → JSON │   │
│  └────────────────┘  └────────────────┘  └────────────────┘   │
├────────────────────────────────────────────────────────────────┤
│  Sweep Layer (NEW)                                             │
│  ┌────────────────┐  ┌────────────────┐                       │
│  │ Grid Search    │  │ Latin Hypercube│                       │
│  └────────────────┘  └────────────────┘                       │
├────────────────────────────────────────────────────────────────┤
│  Analysis Layer (NEW)                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐   │
│  │ Waveform       │  │ Stress         │  │ Efficiency     │   │
│  │ Capture        │  │ Analysis       │  │ Calculator     │   │
│  └────────────────┘  └────────────────┘  └────────────────┘   │
├────────────────────────────────────────────────────────────────┤
│  Execution Layer (existing)                                    │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐   │
│  │ Orchestrator   │  │ Cache          │  │ Logging        │   │
│  │ Queue, batch   │  │ SHA256         │  │ Structured     │   │
│  └────────────────┘  └────────────────┘  └────────────────┘   │
├────────────────────────────────────────────────────────────────┤
│  Core: PlecsServer (XML-RPC)                                   │
├────────────────────────────────────────────────────────────────┤
│  PLECS (external)                                              │
└────────────────────────────────────────────────────────────────┘
```

---

## File Structure (v2.0)

```
pyplecs/
├── __init__.py
├── pyplecs.py              # PlecsServer (existing)
├── config.py               # Configuration (existing)
│
├── tas/                    # NEW: TAS integration
│   ├── __init__.py
│   ├── parser.py           # TAS JSON → SimulationConfig
│   ├── generator.py        # SimulationConfig → .plecs XML
│   └── extractor.py        # SimulationResult → TAS outputs
│
├── sweeps/                 # NEW: Parameter sweeps
│   ├── __init__.py
│   ├── grid.py             # Grid search
│   └── lhs.py              # Latin Hypercube
│
├── analysis/               # NEW: Result analysis
│   ├── __init__.py
│   ├── waveforms.py        # Waveform capture
│   ├── stress.py           # Component stress
│   └── efficiency.py       # Loss calculation
│
├── core/                   # Existing
│   └── models.py
├── orchestration/          # Existing
├── cache/                  # Existing
├── api/                    # Existing (+ new endpoints)
└── webgui/                 # Existing
```

---

## API Contract with NTBEES2

### Request: Simulate with TAS

```json
POST /api/v1/simulate/tas
{
    "tas": {
        "metadata": {"name": "Buck 5kW"},
        "inputs": {
            "operating_points": [
                {
                    "name": "nominal",
                    "parameters": {"Vi": 800, "Vo": 400, "Po": 5000}
                }
            ]
        },
        "converter": {
            "topology_type": {"family": "dc_dc", "type": "buck"},
            "plecs_model": "templates/buck_5kw.plecs"
        }
    },
    "options": {
        "cache": true,
        "outputs": ["Vout", "Iout", "Vsw", "Isw"]
    }
}
```

### Response: TAS Outputs

```json
{
    "status": "completed",
    "cached": false,
    "execution_time": 2.3,
    "tas_outputs": {
        "operating_point_results": [
            {
                "operating_point": "nominal",
                "efficiency": 97.2,
                "losses": {
                    "total": 140,
                    "by_component": {
                        "Q_HS": {"conduction": 35, "switching": 25},
                        "Q_LS": {"conduction": 30, "switching": 20},
                        "L_out": {"core": 15, "winding": 15}
                    }
                },
                "waveforms": {
                    "Vout": {"time": [...], "values": [...]},
                    "Iout": {"time": [...], "values": [...]}
                },
                "component_stress": {
                    "Q_HS": {"Vds_peak": 850, "Id_rms": 12.5},
                    "C_out": {"I_ripple_rms": 8.2}
                }
            }
        ]
    }
}
```

---

## Success Metrics

| Metric | Current | v2.0 Target |
|--------|---------|-------------|
| TAS integration | ❌ None | ✅ Full |
| NTBEES2 E2E test | ❌ | ✅ Pass |
| Sweep support | ❌ | ✅ Grid + LHS |
| Waveform extraction | ❌ | ✅ Any variable |
| API response time | N/A | <100ms (cached) |
| Test coverage | ~30% | 80% |

---

## Comparison: Ecosystem Tools

| Tool | Domain | Input | Output | Intelligence |
|------|--------|-------|--------|--------------|
| **PyPLECS** | PLECS sim | TAS | Waveforms, KPIs | ❌ Thin |
| **PyMKF** | Magnetics | MAS | Core losses, thermal | ❌ Thin |
| **PyGecko** | GeckoCIRCUITS | TAS | Waveforms, KPIs | ❌ Thin |
| **NTBEES2** | Orchestration | Design spec | Optimized design | ✅ Smart |

All execution tools are thin. NTBEES2 is smart.

---

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1: TAS Integration | 2 months | TAS → simulate → TAS outputs |
| Phase 2: Parameter Sweeps | 1 month | Grid + LHS support |
| Phase 3: Waveform/KPI | 1 month | Stress, efficiency extraction |
| Phase 4: Robustness | 1 month | Production-ready |
| Phase 5: Testing/Docs | 1 month | 80% coverage, docs |

**Total**: 6 months → Q3 2026

---

## References

- [TAS Sprint Planning](./docs/TAS_SPRINT_PLANNING_NTBEES2.md)
- [PLECS XML-RPC Documentation](https://www.plexim.com/support/application_notes)
- [Latin Hypercube Sampling](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.LatinHypercube.html)
