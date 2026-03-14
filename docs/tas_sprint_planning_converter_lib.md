# Sprint Planning: TAS Implementation in converter_lib

**Versione:** 1.0  
**Data:** 2026-01-25  
**Durata stimata:** 8 Sprint (16 settimane)  
**Effort:** ~160-200 ore totali

---

## 📊 Executive Summary

### Obiettivo
Integrare il formato TAS (Topology Agnostic Structure) nel framework converter_lib per abilitare:
- Definizione standardizzata di topologie power electronics
- Import/export verso strumenti esterni (PLECS, LTspice, MAS)
- Validazione JSON Schema per garantire integrità dati
- Generazione automatica netlist e waveforms

### Stato Attuale converter_lib
| Componente | Stato | Riutilizzabile per TAS |
|------------|-------|------------------------|
| TimeSeries/TimeMatrix | ✅ Complete | ✅ Per waveforms |
| Electrical KPI | ✅ Complete | ✅ Per outputs.losses |
| Pydantic Models | ✅ In uso | ✅ Per TAS validation |
| Logging Infrastructure | ✅ Complete | ✅ Debug TAS parsing |
| ODE Integration | 🔄 In progress | ✅ Per simulation |
| pymoo Optimization | ✅ Available | ✅ Per design space |

### Mapping TAS → converter_lib Architecture (Ewald)

```
TAS Structure              converter_lib Architecture
─────────────────────────────────────────────────
inputs.design_requirements → ConverterSpec
inputs.operating_points    → OperatingPoint + TimeSeries
inputs.constraints         → OptimizationConstraints
converter.topology_type    → TopologyDefinition (NEW)
converter.sub_networks     → SnDT (Sub-network Digital Twin)
converter.components       → CDT (Component Digital Twin)
converter.netlist          → ElectricalNetlist (NEW)
outputs.losses             → ElectricalKPI (esistente)
outputs.thermal            → ThermalKPI (NEW)
outputs.waveforms          → TimeSeries (esistente)
```

---

## 🗓️ Sprint Overview

| Sprint | Focus | Ore | Deliverable |
|--------|-------|-----|-------------|
| S1 | Core TAS Models (Pydantic) | 20h | `tas/models/` |
| S2 | Inputs Section + Waveforms | 20h | `tas/inputs/` |
| S3 | Converter Section + Netlist | 25h | `tas/converter/` |
| S4 | Components Database | 20h | `tas/components/` |
| S5 | Outputs + KPI Integration | 20h | `tas/outputs/` |
| S6 | MAS Integration | 15h | `tas/integrations/mas/` |
| S7 | Export (PLECS/LTspice) | 25h | `tas/exporters/` |
| S8 | Validation + Documentation | 15h | Tests + Docs |

---

## 📋 Sprint 1: Core TAS Models (Pydantic)
**Durata:** 2 settimane  
**Ore stimate:** 20h  
**Priorità:** 🔴 Critical

### Obiettivi
1. Definire struttura base TAS con Pydantic
2. Implementare validazione JSON Schema
3. Creare base classes per PhysicalQuantity

### Tasks

#### 1.1 PhysicalQuantity Base Model (4h)
```python
# tas/models/quantities.py
from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum

class Unit(str, Enum):
    VOLT = "V"
    AMPERE = "A"
    WATT = "W"
    HERTZ = "Hz"
    OHM = "Ω"
    HENRY = "H"
    FARAD = "F"
    KELVIN = "K"
    CELSIUS = "°C"
    METER = "m"
    # ... complete enumeration

class PhysicalQuantity(BaseModel):
    """Base class for all physical quantities with units."""
    value: float
    unit: Unit
    conditions: Optional[dict] = None
    tolerance: Optional[float] = None
    
    def to_si(self) -> float:
        """Convert to SI base units."""
        ...
    
    def __mul__(self, other): ...
    def __add__(self, other): ...

class RangeQuantity(BaseModel):
    """Quantity with min/max range."""
    nominal: PhysicalQuantity
    min: Optional[PhysicalQuantity] = None
    max: Optional[PhysicalQuantity] = None
```

#### 1.2 TAS Root Model (4h)
```python
# tas/models/tas_root.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TASMetadata(BaseModel):
    name: str
    author: Optional[str] = None
    created: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    description: Optional[str] = None
    tags: list[str] = []

class TAS(BaseModel):
    """Root TAS document model."""
    schema_url: str = Field(
        alias="$schema",
        default="https://openpowerelectronics.org/schemas/TAS/v1.0/tas.json"
    )
    version: str = "1.0.0"
    metadata: TASMetadata
    inputs: "TASInputs"
    converter: "TASConverter"
    outputs: Optional["TASOutputs"] = None
    
    class Config:
        populate_by_name = True  # Pydantic v2

    @classmethod
    def from_json(cls, path: str) -> "TAS":
        """Load TAS from JSON file with validation."""
        ...
    
    def to_json(self, path: str, indent: int = 2) -> None:
        """Export TAS to JSON file."""
        ...
```

#### 1.3 Waveform Models (6h)
```python
# tas/models/waveforms.py
from typing import Union, Literal
from converter_lib.core.time_series import TimeSeries  # Riuso esistente!

class WaveformSampled(BaseModel):
    """Sampled time-domain waveform."""
    type: Literal["sampled"] = "sampled"
    time: list[float]
    data: list[float]
    unit: Unit
    
    def to_timeseries(self) -> TimeSeries:
        """Convert to converter_lib TimeSeries."""
        return TimeSeries(
            time=np.array(self.time),
            values=np.array(self.data),
            unit=str(self.unit)
        )

class WaveformPWL(BaseModel):
    """Piecewise-linear waveform."""
    type: Literal["piecewise_linear"] = "piecewise_linear"
    time: list[float]
    data: list[float]
    unit: Unit

class WaveformAnalytical(BaseModel):
    """Analytically defined waveform."""
    type: Literal["analytical"] = "analytical"
    expression: str  # e.g., "I0 + dI*sin(2*pi*f*t)"
    parameters: dict[str, PhysicalQuantity]
    
class WaveformReference(BaseModel):
    """Reference to external waveform file."""
    type: Literal["reference"] = "reference"
    file: str  # HDF5 or CSV path
    dataset: Optional[str] = None  # For HDF5

Waveform = Union[WaveformSampled, WaveformPWL, WaveformAnalytical, WaveformReference]
```

#### 1.4 JSON Schema Validator (3h)
```python
# tas/validation/schema_validator.py
import jsonschema
from pathlib import Path

class TASValidator:
    """Validate TAS documents against JSON Schema."""
    
    SCHEMA_PATH = Path(__file__).parent / "schemas" / "tas.json"
    
    def __init__(self):
        self.schema = self._load_schema()
        self.validator = jsonschema.Draft7Validator(self.schema)
    
    def validate(self, tas_dict: dict) -> tuple[bool, list[str]]:
        """Validate TAS document, return (valid, errors)."""
        errors = list(self.validator.iter_errors(tas_dict))
        return len(errors) == 0, [str(e) for e in errors]
    
    def validate_file(self, path: str) -> tuple[bool, list[str]]:
        """Validate TAS JSON file."""
        ...
```

#### 1.5 Unit Tests (3h)
```python
# tests/tas/test_models.py
import pytest
from tas.models import PhysicalQuantity, TAS, WaveformSampled

class TestPhysicalQuantity:
    def test_creation(self):
        q = PhysicalQuantity(value=800, unit="V")
        assert q.value == 800
        
    def test_unit_conversion(self):
        q = PhysicalQuantity(value=1, unit="kV")
        assert q.to_si() == 1000.0

class TestWaveform:
    def test_to_timeseries(self):
        wf = WaveformSampled(
            time=[0, 1e-6, 2e-6],
            data=[0, 10, 0],
            unit="A"
        )
        ts = wf.to_timeseries()
        assert isinstance(ts, TimeSeries)
        assert ts.rms() > 0
```

### Acceptance Criteria S1
- [ ] Tutti i model Pydantic validano correttamente
- [ ] PhysicalQuantity supporta operazioni matematiche
- [ ] Waveform → TimeSeries conversion funziona
- [ ] 100% test coverage su models
- [ ] JSON Schema validation implementata

### File Structure dopo S1
```
converter_lib/
├── tas/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── quantities.py       # PhysicalQuantity, Unit
│   │   ├── waveforms.py        # Waveform types
│   │   ├── tas_root.py         # TAS, TASMetadata
│   │   └── validators.py       # Custom validators
│   ├── validation/
│   │   ├── __init__.py
│   │   └── schema_validator.py
│   └── schemas/
│       └── tas.json            # JSON Schema (from /home/claude)
└── tests/
    └── tas/
        └── test_models.py
```

---

## 📋 Sprint 2: Inputs Section + Operating Points
**Durata:** 2 settimane  
**Ore stimate:** 20h  
**Priorità:** 🔴 Critical

### Obiettivi
1. Implementare TASInputs con DesignRequirements
2. Creare OperatingPoint model con excitations
3. Integrare constraints per optimization

### Tasks

#### 2.1 Design Requirements Model (5h)
```python
# tas/models/inputs/design_requirements.py
from pydantic import BaseModel
from typing import Optional, Literal
from ..quantities import PhysicalQuantity, RangeQuantity

class IsolationSpec(BaseModel):
    required: bool = False
    type: Optional[Literal["basic", "reinforced", "functional"]] = None
    voltage: Optional[PhysicalQuantity] = None  # Test voltage

class CoolingSpec(BaseModel):
    type: Literal["natural_convection", "forced_air", "liquid", "conduction"]
    ambient_temperature: PhysicalQuantity
    airflow: Optional[PhysicalQuantity] = None  # m³/min
    coolant_temperature: Optional[PhysicalQuantity] = None

class DesignRequirements(BaseModel):
    """Design requirements section of TAS inputs."""
    name: str
    application: Optional[str] = None  # telecom, automotive, solar, medical
    
    # Voltage specs
    input_voltage: RangeQuantity
    output_voltage: RangeQuantity
    
    # Power specs
    power: RangeQuantity
    
    # Performance targets
    efficiency_target: Optional[PhysicalQuantity] = None
    power_density_target: Optional[PhysicalQuantity] = None  # kW/dm³
    
    # Other specs
    isolation: Optional[IsolationSpec] = None
    cooling: CoolingSpec
    standards: list[str] = []  # CISPR22, IEC61000-4-5, etc.
    
    def get_voltage_transfer_ratio(self) -> float:
        """Calculate Vout/Vin ratio."""
        return self.output_voltage.nominal.value / self.input_voltage.nominal.value
```

#### 2.2 Operating Point Model (6h)
```python
# tas/models/inputs/operating_point.py
from pydantic import BaseModel, model_validator
from typing import Optional
from ..waveforms import Waveform
from ..quantities import PhysicalQuantity

class Excitation(BaseModel):
    """Current/voltage excitation for a port."""
    current: Optional[Waveform] = None
    voltage: Optional[Waveform] = None
    
    # Processed values (optional, can be computed)
    processed: Optional["ProcessedWaveform"] = None

class ProcessedWaveform(BaseModel):
    """Pre-computed waveform characteristics."""
    rms: Optional[PhysicalQuantity] = None
    peak: Optional[PhysicalQuantity] = None
    average: Optional[PhysicalQuantity] = None
    ripple_pp: Optional[PhysicalQuantity] = None
    thd: Optional[float] = None  # Total harmonic distortion

class OperatingPoint(BaseModel):
    """Single operating point definition."""
    name: str
    
    # Timing
    frequency: PhysicalQuantity  # Switching frequency
    duty_cycle: Optional[PhysicalQuantity] = None
    
    # Environment
    conditions: Optional["OperatingConditions"] = None
    
    # Excitations per port
    excitations: dict[str, Excitation] = {}  # port_name -> Excitation
    
    @model_validator(mode='after')
    def validate_duty_cycle(self):
        if self.duty_cycle and not (0 < self.duty_cycle.value < 1):
            raise ValueError("Duty cycle must be between 0 and 1")
        return self
    
    def to_converter_lib_operating_point(self):
        """Convert to converter_lib OperatingPoint class."""
        from converter_lib.core.operating_point import OperatingPoint as NTOperatingPoint
        # ... mapping logic
```

#### 2.3 Constraints Model (4h)
```python
# tas/models/inputs/constraints.py
from pydantic import BaseModel
from typing import Optional

class ComponentConstraints(BaseModel):
    """Constraints on component selection."""
    
    class SwitchConstraints(BaseModel):
        allowed_manufacturers: list[str] = []
        technology: list[str] = []  # SiC_MOSFET, GaN_HEMT, Si_IGBT
        package: list[str] = []
        max_junction_temperature: Optional[PhysicalQuantity] = None
    
    class MagneticConstraints(BaseModel):
        core_materials: list[str] = []
        max_temperature_rise: Optional[PhysicalQuantity] = None
        max_flux_density: Optional[PhysicalQuantity] = None
    
    class CapacitorConstraints(BaseModel):
        types: list[str] = []  # MLCC, film, electrolytic
        voltage_derating: float = 0.8
    
    switches: Optional[SwitchConstraints] = None
    magnetics: Optional[MagneticConstraints] = None
    capacitors: Optional[CapacitorConstraints] = None

class GeometricConstraints(BaseModel):
    """Physical size constraints."""
    max_dimensions: Optional["BoxDimensions"] = None
    form_factor: Optional[str] = None  # 1U, 2U, custom
    max_volume: Optional[PhysicalQuantity] = None

class ThermalConstraints(BaseModel):
    """Thermal performance constraints."""
    max_surface_temperature: Optional[PhysicalQuantity] = None
    cspi_target: Optional[PhysicalQuantity] = None  # W/(K·dm³)

class Constraints(BaseModel):
    """All constraints for optimization."""
    component_constraints: Optional[ComponentConstraints] = None
    geometric_constraints: Optional[GeometricConstraints] = None
    thermal_constraints: Optional[ThermalConstraints] = None
```

#### 2.4 TASInputs Aggregator (3h)
```python
# tas/models/inputs/__init__.py
from pydantic import BaseModel
from .design_requirements import DesignRequirements
from .operating_point import OperatingPoint
from .constraints import Constraints

class TASInputs(BaseModel):
    """Complete inputs section of TAS."""
    design_requirements: DesignRequirements
    operating_points: list[OperatingPoint] = []
    constraints: Optional[Constraints] = None
    
    def get_nominal_operating_point(self) -> OperatingPoint:
        """Get the nominal operating point."""
        for op in self.operating_points:
            if "nominal" in op.name.lower():
                return op
        return self.operating_points[0] if self.operating_points else None
    
    def get_frequency_range(self) -> tuple[float, float]:
        """Get min/max switching frequency across all OPs."""
        freqs = [op.frequency.value for op in self.operating_points]
        return min(freqs), max(freqs)
```

#### 2.5 Integration Tests (2h)
```python
# tests/tas/test_inputs.py
import pytest
from tas.models.inputs import TASInputs, DesignRequirements, OperatingPoint

class TestDesignRequirements:
    def test_voltage_transfer_ratio(self):
        dr = DesignRequirements(
            name="Test",
            input_voltage=RangeQuantity(nominal=PhysicalQuantity(value=800, unit="V")),
            output_voltage=RangeQuantity(nominal=PhysicalQuantity(value=400, unit="V")),
            power=RangeQuantity(nominal=PhysicalQuantity(value=5000, unit="W")),
            cooling=CoolingSpec(type="forced_air", ambient_temperature=PhysicalQuantity(value=45, unit="°C"))
        )
        assert dr.get_voltage_transfer_ratio() == 0.5

class TestOperatingPoint:
    def test_excitation_to_timeseries(self):
        # Test waveform conversion
        ...
```

### Acceptance Criteria S2
- [ ] DesignRequirements parsing completo
- [ ] OperatingPoint supporta tutti i waveform types
- [ ] Constraints mappa a pymoo optimization bounds
- [ ] Integration con TimeSeries esistente verificata

---

## 📋 Sprint 3: Converter Section + Netlist
**Durata:** 2 settimane  
**Ore stimate:** 25h  
**Priorità:** 🔴 Critical

### Obiettivi
1. Implementare TopologyType enumeration
2. Creare SubNetwork models (switching cell, magnetics, filters)
3. Implementare Netlist con electrical connectivity

### Tasks

#### 3.1 Topology Type Enumeration (3h)
```python
# tas/models/converter/topology_types.py
from enum import Enum
from typing import Literal

class TopologyFamily(str, Enum):
    NON_ISOLATED_DC_DC = "non_isolated_dc_dc"
    ISOLATED_DC_DC = "isolated_dc_dc"
    AC_DC = "ac_dc"
    DC_AC = "dc_ac"
    AC_AC = "ac_ac"

# Type-specific enums
class NonIsolatedDCDCType(str, Enum):
    BUCK = "buck"
    BOOST = "boost"
    BUCK_BOOST = "buck_boost"
    CUK = "cuk"
    SEPIC = "sepic"
    ZETA = "zeta"
    INTERLEAVED_BUCK = "interleaved_buck"
    MULTIPHASE_BUCK = "multiphase_buck"

class IsolatedDCDCType(str, Enum):
    FLYBACK = "flyback"
    FORWARD = "forward"
    HALF_BRIDGE = "half_bridge"
    FULL_BRIDGE = "full_bridge"
    PHASE_SHIFTED_FULL_BRIDGE = "phase_shifted_full_bridge"
    LLC = "llc"
    LCC = "lcc"
    CLLC = "cllc"
    DAB = "dab"
    TAB = "tab"

class TopologyType(BaseModel):
    """Topology type specification."""
    family: TopologyFamily
    type: str  # Specific type within family
    variant: Optional[str] = None  # e.g., "with_current_doubler"
    
    @model_validator(mode='after')
    def validate_type_in_family(self):
        # Validate type matches family
        ...
```

#### 3.2 SubNetwork Models (8h)
```python
# tas/models/converter/sub_networks.py
from pydantic import BaseModel
from typing import Union, Literal, Optional

class SubNetworkBase(BaseModel):
    """Base class for all sub-networks."""
    id: str
    type: str
    terminals: list[str] = []  # External connection points
    
class SwitchingCellSubNetwork(SubNetworkBase):
    """Switching cell sub-network (half-bridge, full-bridge, etc.)."""
    type: Literal["switching_cell"] = "switching_cell"
    configuration: Literal["half_bridge", "full_bridge", "npc", "flying_cap"]
    components: list[str] = []  # Component IDs
    gate_driver: Optional[str] = None  # Gate driver component ID
    deadtime: Optional[PhysicalQuantity] = None

class MagneticsSubNetwork(SubNetworkBase):
    """Magnetics sub-network (inductor, transformer, coupled inductors)."""
    type: Literal["magnetics"] = "magnetics"
    magnetic_type: Literal["inductor", "transformer", "coupled_inductor", "cm_choke"]
    
    # Option 1: MAS reference
    mas_reference: Optional[str] = None  # file://... or openmagnetics://...
    
    # Option 2: Inline specification
    magnetic_specification: Optional["MagneticSpec"] = None

class FilterSubNetwork(SubNetworkBase):
    """Filter sub-network (EMI, DM, CM, output)."""
    type: Literal["filter"] = "filter"
    filter_type: Literal["emi_input", "emi_output", "dm", "cm", "lc_output", "clc"]
    stages: int = 1
    components: list[str] = []

class CoolingSubNetwork(SubNetworkBase):
    """Cooling system sub-network."""
    type: Literal["cooling"] = "cooling"
    cooling_type: Literal["heatsink", "coldplate", "fan", "heatpipe"]
    cspi: Optional[PhysicalQuantity] = None  # Cooling system performance index
    thermal_resistance: Optional[PhysicalQuantity] = None

class CapacitorBankSubNetwork(SubNetworkBase):
    """Capacitor bank sub-network."""
    type: Literal["capacitor_bank"] = "capacitor_bank"
    function: Literal["dc_link", "input_filter", "output_filter", "flying_cap"]
    components: list[str] = []

SubNetwork = Union[
    SwitchingCellSubNetwork,
    MagneticsSubNetwork,
    FilterSubNetwork,
    CoolingSubNetwork,
    CapacitorBankSubNetwork
]
```

#### 3.3 Netlist Model (6h)
```python
# tas/models/converter/netlist.py
from pydantic import BaseModel
from typing import Optional

class NetConnection(BaseModel):
    """Single net connection."""
    component_id: str
    terminal: str  # P, N, D, S, G, etc.
    
    def __str__(self) -> str:
        return f"{self.component_id}.{self.terminal}"

class Net(BaseModel):
    """Single electrical net."""
    name: str
    connections: list[str]  # "ComponentID.Terminal" format
    net_type: Optional[str] = None  # power, signal, ground
    
    def get_connections(self) -> list[NetConnection]:
        """Parse connection strings to NetConnection objects."""
        result = []
        for conn_str in self.connections:
            parts = conn_str.split(".")
            result.append(NetConnection(component_id=parts[0], terminal=parts[1]))
        return result

class Netlist(BaseModel):
    """Complete electrical netlist."""
    nets: list[Net] = []
    
    def get_net_by_name(self, name: str) -> Optional[Net]:
        """Find net by name."""
        for net in self.nets:
            if net.name == name:
                return net
        return None
    
    def get_component_connections(self, component_id: str) -> dict[str, str]:
        """Get all connections for a component."""
        connections = {}
        for net in self.nets:
            for conn in net.connections:
                if conn.startswith(f"{component_id}."):
                    terminal = conn.split(".")[1]
                    connections[terminal] = net.name
        return connections
    
    def to_spice_netlist(self) -> str:
        """Export to SPICE netlist format."""
        lines = ["* TAS Generated SPICE Netlist"]
        # ... netlist generation
        return "\n".join(lines)
    
    def validate_connectivity(self) -> tuple[bool, list[str]]:
        """Check for floating nodes, shorts, etc."""
        errors = []
        # ... validation logic
        return len(errors) == 0, errors
```

#### 3.4 TASConverter Aggregator (4h)
```python
# tas/models/converter/__init__.py
from pydantic import BaseModel
from typing import Optional
from .topology_types import TopologyType
from .sub_networks import SubNetwork
from .netlist import Netlist
from ..quantities import PhysicalQuantity

class ConverterParameters(BaseModel):
    """Global converter parameters."""
    switching_frequency: Optional[PhysicalQuantity] = None
    transformer_turns_ratio: Optional[float] = None
    dead_time: Optional[PhysicalQuantity] = None
    modulation_index: Optional[float] = None

class TASConverter(BaseModel):
    """Complete converter section of TAS."""
    name: str
    topology_type: TopologyType
    parameters: Optional[ConverterParameters] = None
    sub_networks: list[SubNetwork] = []
    components: list["Component"] = []  # Forward ref
    netlist: Netlist
    
    def get_sub_network(self, sn_id: str) -> Optional[SubNetwork]:
        """Get sub-network by ID."""
        for sn in self.sub_networks:
            if sn.id == sn_id:
                return sn
        return None
    
    def get_component(self, comp_id: str) -> Optional["Component"]:
        """Get component by ID."""
        for comp in self.components:
            if comp.id == comp_id:
                return comp
        return None
    
    def get_switching_cells(self) -> list[SwitchingCellSubNetwork]:
        """Get all switching cell sub-networks."""
        return [sn for sn in self.sub_networks if sn.type == "switching_cell"]
    
    def to_ewald_cnvdt(self):
        """Convert to Ewald CnvDT format."""
        # Mapping to converter_lib converter digital twin
        ...
```

#### 3.5 Tests (4h)
```python
# tests/tas/test_converter.py
class TestNetlist:
    def test_connection_parsing(self):
        netlist = Netlist(nets=[
            Net(name="Vin+", connections=["C_in.P", "Q_HS.D"]),
            Net(name="SW", connections=["Q_HS.S", "Q_LS.D", "L1.P"]),
        ])
        assert netlist.get_net_by_name("Vin+") is not None
        
    def test_spice_export(self):
        # Test SPICE netlist generation
        ...
        
class TestTopologyType:
    def test_buck_topology(self):
        tt = TopologyType(
            family=TopologyFamily.NON_ISOLATED_DC_DC,
            type="buck"
        )
        assert tt.family == TopologyFamily.NON_ISOLATED_DC_DC
```

### Acceptance Criteria S3
- [ ] Tutte le topology families supportate
- [ ] SubNetwork polymorphism funziona
- [ ] Netlist export to SPICE verificato
- [ ] Connectivity validation implementata

---

## 📋 Sprint 4: Components Database
**Durata:** 2 settimane  
**Ore stimate:** 20h  
**Priorità:** 🟡 High

### Obiettivi
1. Implementare Component models (Switch, Capacitor, etc.)
2. Creare database loader (JSON/SQLite)
3. Supportare component lookup by part number

### Tasks

#### 4.1 Switch Component Model (5h)
```python
# tas/models/components/switch.py
from pydantic import BaseModel
from typing import Optional, Literal
from ..quantities import PhysicalQuantity

class SwitchStaticParameters(BaseModel):
    """Static (DC) parameters of a switch."""
    Vds_max: PhysicalQuantity
    Id_max: PhysicalQuantity
    Rds_on: PhysicalQuantity
    Vgs_th: PhysicalQuantity
    
class SwitchDynamicParameters(BaseModel):
    """Dynamic (switching) parameters."""
    Ciss: PhysicalQuantity
    Coss: PhysicalQuantity
    Crss: PhysicalQuantity
    Qg: PhysicalQuantity
    Qgd: Optional[PhysicalQuantity] = None
    
class SwitchingLosses(BaseModel):
    """Switching loss model."""
    model: Literal["piecewise_linear", "polynomial", "lookup_table"]
    Eon: PhysicalQuantity  # Turn-on energy
    Eoff: PhysicalQuantity  # Turn-off energy
    Err: Optional[PhysicalQuantity] = None  # Reverse recovery
    at_conditions: dict  # Vds, Id at which measured

class ThermalParameters(BaseModel):
    """Thermal parameters."""
    Rth_jc: PhysicalQuantity  # Junction to case
    Rth_cs: Optional[PhysicalQuantity] = None  # Case to sink
    Tj_max: PhysicalQuantity
    Tc_max: Optional[PhysicalQuantity] = None

class SwitchComponent(BaseModel):
    """Complete switch component model."""
    id: str
    type: Literal["switch"] = "switch"
    
    # Identification
    manufacturer: str
    part_number: str
    technology: Literal["Si_MOSFET", "SiC_MOSFET", "GaN_HEMT", "Si_IGBT", "SiC_IGBT"]
    package: str
    
    # Parameters
    static: SwitchStaticParameters
    dynamic: SwitchDynamicParameters
    switching_losses: SwitchingLosses
    thermal: ThermalParameters
    
    # Optional datasheet link
    datasheet_url: Optional[str] = None
    
    def calculate_conduction_loss(self, i_rms: float, duty: float) -> float:
        """Calculate conduction losses."""
        return self.static.Rds_on.value * (i_rms ** 2) * duty
    
    def calculate_switching_loss(self, v_ds: float, i_d: float, f_sw: float) -> float:
        """Calculate switching losses (simplified)."""
        E_total = self.switching_losses.Eon.value + self.switching_losses.Eoff.value
        # Scale from test conditions
        scale = (v_ds / self.switching_losses.at_conditions["Vds"]) * \
                (i_d / self.switching_losses.at_conditions["Id"])
        return E_total * scale * f_sw
```

#### 4.2 Capacitor Component Model (4h)
```python
# tas/models/components/capacitor.py
class CapacitorComponent(BaseModel):
    """Capacitor component model."""
    id: str
    type: Literal["capacitor"] = "capacitor"
    
    # Identification
    manufacturer: str
    part_number: str
    cap_type: Literal["MLCC", "film", "electrolytic", "polymer", "ceramic"]
    
    # Electrical parameters
    capacitance: PhysicalQuantity
    voltage_rating: PhysicalQuantity
    esr: PhysicalQuantity  # At specified frequency
    esl: Optional[PhysicalQuantity] = None
    ripple_current: PhysicalQuantity  # Max RMS ripple
    
    # Frequency dependency
    esr_vs_freq: Optional[list[tuple[float, float]]] = None  # (freq_Hz, ESR_Ohm)
    
    # Thermal
    temperature_coefficient: Optional[str] = None  # X7R, C0G, etc.
    max_temperature: PhysicalQuantity
    
    def get_esr_at_frequency(self, freq: float) -> float:
        """Interpolate ESR at given frequency."""
        ...
    
    def calculate_loss(self, i_rms: float, freq: float) -> float:
        """Calculate capacitor loss."""
        esr = self.get_esr_at_frequency(freq)
        return esr * (i_rms ** 2)
```

#### 4.3 Component Database (6h)
```python
# tas/database/component_db.py
from pathlib import Path
import json
from typing import Optional, Union
from ..models.components import SwitchComponent, CapacitorComponent

Component = Union[SwitchComponent, CapacitorComponent]

class ComponentDatabase:
    """Component database with lookup capabilities."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(__file__).parent / "data"
        self._switches: dict[str, SwitchComponent] = {}
        self._capacitors: dict[str, CapacitorComponent] = {}
        self._load_database()
    
    def _load_database(self):
        """Load component data from JSON files."""
        # Load switches
        switch_file = self.db_path / "switches.json"
        if switch_file.exists():
            data = json.loads(switch_file.read_text())
            for item in data["switches"]:
                comp = SwitchComponent(**item)
                self._switches[comp.part_number] = comp
        
        # Load capacitors
        cap_file = self.db_path / "capacitors.json"
        if cap_file.exists():
            data = json.loads(cap_file.read_text())
            for item in data["capacitors"]:
                comp = CapacitorComponent(**item)
                self._capacitors[comp.part_number] = comp
    
    def get_switch(self, part_number: str) -> Optional[SwitchComponent]:
        """Lookup switch by part number."""
        return self._switches.get(part_number)
    
    def get_capacitor(self, part_number: str) -> Optional[CapacitorComponent]:
        """Lookup capacitor by part number."""
        return self._capacitors.get(part_number)
    
    def search_switches(
        self,
        technology: Optional[str] = None,
        v_ds_min: Optional[float] = None,
        manufacturer: Optional[str] = None
    ) -> list[SwitchComponent]:
        """Search switches by criteria."""
        results = list(self._switches.values())
        if technology:
            results = [s for s in results if s.technology == technology]
        if v_ds_min:
            results = [s for s in results if s.static.Vds_max.value >= v_ds_min]
        if manufacturer:
            results = [s for s in results if s.manufacturer == manufacturer]
        return results
```

#### 4.4 Sample Component Data (3h)
```json
// tas/database/data/switches.json
{
  "switches": [
    {
      "id": "Q1",
      "manufacturer": "Wolfspeed",
      "part_number": "C3M0065100K",
      "technology": "SiC_MOSFET",
      "package": "TO-247-4",
      "static": {
        "Vds_max": {"value": 1000, "unit": "V"},
        "Id_max": {"value": 35, "unit": "A"},
        "Rds_on": {"value": 65, "unit": "mΩ"},
        "Vgs_th": {"value": 2.5, "unit": "V"}
      },
      "dynamic": {
        "Ciss": {"value": 1200, "unit": "pF"},
        "Coss": {"value": 80, "unit": "pF"},
        "Crss": {"value": 8, "unit": "pF"},
        "Qg": {"value": 62, "unit": "nC"}
      },
      "switching_losses": {
        "model": "piecewise_linear",
        "Eon": {"value": 0.35, "unit": "mJ"},
        "Eoff": {"value": 0.25, "unit": "mJ"},
        "at_conditions": {"Vds": 800, "Id": 20}
      },
      "thermal": {
        "Rth_jc": {"value": 0.24, "unit": "K/W"},
        "Tj_max": {"value": 175, "unit": "°C"}
      }
    }
  ]
}
```

#### 4.5 Tests (2h)
```python
# tests/tas/test_components.py
class TestComponentDatabase:
    def test_switch_lookup(self):
        db = ComponentDatabase()
        switch = db.get_switch("C3M0065100K")
        assert switch is not None
        assert switch.technology == "SiC_MOSFET"
        
    def test_loss_calculation(self):
        db = ComponentDatabase()
        switch = db.get_switch("C3M0065100K")
        p_cond = switch.calculate_conduction_loss(i_rms=10, duty=0.5)
        assert p_cond > 0
```

### Acceptance Criteria S4
- [ ] Switch/Capacitor models completi
- [ ] Database lookup funziona
- [ ] Almeno 10 switch reali in database
- [ ] Loss calculations verificate vs datasheet

---

## 📋 Sprint 5: Outputs + KPI Integration
**Durata:** 2 settimane  
**Ore stimate:** 20h  
**Priorità:** 🟡 High

### Obiettivi
1. Implementare TASOutputs con loss breakdown
2. Integrare con ElectricalKPI esistente
3. Creare ThermalKPI per temperature calculations

### Tasks

#### 5.1 Loss Breakdown Model (4h)
```python
# tas/models/outputs/losses.py
from pydantic import BaseModel
from typing import Optional

class ComponentLosses(BaseModel):
    """Losses for a single component."""
    component_id: str
    conduction: Optional[PhysicalQuantity] = None
    switching: Optional[PhysicalQuantity] = None
    gate_driver: Optional[PhysicalQuantity] = None
    core: Optional[PhysicalQuantity] = None  # For magnetics
    winding: Optional[PhysicalQuantity] = None  # For magnetics
    dielectric: Optional[PhysicalQuantity] = None  # For capacitors
    total: PhysicalQuantity
    
    @property
    def calculated_total(self) -> float:
        """Sum all loss components."""
        losses = [
            self.conduction, self.switching, self.gate_driver,
            self.core, self.winding, self.dielectric
        ]
        return sum(l.value for l in losses if l is not None)

class LossBreakdown(BaseModel):
    """Complete loss breakdown for operating point."""
    total: PhysicalQuantity
    by_component: list[ComponentLosses] = []
    by_subnetwork: dict[str, PhysicalQuantity] = {}
    by_category: dict[str, PhysicalQuantity] = {}  # conduction, switching, magnetic, etc.
    
    @classmethod
    def from_converter_lib_kpi(cls, kpi: "ElectricalKPI") -> "LossBreakdown":
        """Create from converter_lib ElectricalKPI."""
        # Mapping from existing KPI system
        ...
```

#### 5.2 Thermal Results Model (4h)
```python
# tas/models/outputs/thermal.py
class ThermalResults(BaseModel):
    """Thermal simulation results."""
    junction_temperatures: dict[str, PhysicalQuantity] = {}  # component_id -> Tj
    case_temperatures: dict[str, PhysicalQuantity] = {}
    heatsink_temperature: Optional[PhysicalQuantity] = None
    ambient_temperature: PhysicalQuantity
    
    # Magnetics thermal
    magnetics_hotspot: Optional[PhysicalQuantity] = None
    magnetics_average: Optional[PhysicalQuantity] = None
    
    # Margins
    thermal_margins: dict[str, PhysicalQuantity] = {}  # component_id -> margin to Tj_max
    
    def check_limits(self, component_db: ComponentDatabase) -> tuple[bool, list[str]]:
        """Check if all temperatures within limits."""
        violations = []
        for comp_id, tj in self.junction_temperatures.items():
            comp = component_db.get_switch(comp_id)
            if comp and tj.value > comp.thermal.Tj_max.value:
                violations.append(f"{comp_id}: Tj={tj.value}°C > Tj_max={comp.thermal.Tj_max.value}°C")
        return len(violations) == 0, violations
```

#### 5.3 Volume & Power Density (3h)
```python
# tas/models/outputs/volumes.py
class VolumeBreakdown(BaseModel):
    """Volume breakdown by component/subnetwork."""
    total: PhysicalQuantity  # dm³
    by_subnetwork: dict[str, PhysicalQuantity] = {}
    by_category: dict[str, PhysicalQuantity] = {}  # switching_cell, magnetics, heatsink, etc.

class PowerDensityMetrics(BaseModel):
    """Power density and related metrics."""
    power_density: PhysicalQuantity  # kW/dm³
    specific_power: Optional[PhysicalQuantity] = None  # kW/kg
    cspi: Optional[PhysicalQuantity] = None  # W/(K·dm³)
```

#### 5.4 TASOutputs Aggregator (4h)
```python
# tas/models/outputs/__init__.py
class OperatingPointResults(BaseModel):
    """Results for a single operating point."""
    operating_point: str  # Reference to OP name
    losses: LossBreakdown
    efficiency: PhysicalQuantity
    thermal: ThermalResults
    waveforms: Optional["WaveformResults"] = None

class TASOutputs(BaseModel):
    """Complete outputs section of TAS."""
    calculated: bool = False
    calculation_timestamp: Optional[datetime] = None
    
    # Per operating point
    operating_point_results: list[OperatingPointResults] = []
    
    # Global results
    volumes: Optional[VolumeBreakdown] = None
    power_density: Optional[PhysicalQuantity] = None
    specific_power: Optional[PhysicalQuantity] = None
    cost_estimate: Optional[PhysicalQuantity] = None
    
    def get_results(self, op_name: str) -> Optional[OperatingPointResults]:
        """Get results for specific operating point."""
        for opr in self.operating_point_results:
            if opr.operating_point == op_name:
                return opr
        return None
    
    def get_efficiency_curve(self) -> list[tuple[float, float]]:
        """Get efficiency vs load curve."""
        # Return [(load_%, efficiency_%)]
        ...
```

#### 5.5 Integration with converter_lib KPI (5h)
```python
# tas/integration/converter_lib_bridge.py
from converter_lib.kpi.electrical_kpi import ElectricalKPI
from ..models.outputs import TASOutputs, LossBreakdown, OperatingPointResults

class converter_libBridge:
    """Bridge between TAS and converter_lib internal structures."""
    
    @staticmethod
    def electrical_kpi_to_loss_breakdown(kpi: ElectricalKPI) -> LossBreakdown:
        """Convert converter_lib ElectricalKPI to TAS LossBreakdown."""
        return LossBreakdown(
            total=PhysicalQuantity(value=kpi.total_losses, unit="W"),
            by_category={
                "conduction": PhysicalQuantity(value=kpi.conduction_losses, unit="W"),
                "switching": PhysicalQuantity(value=kpi.switching_losses, unit="W"),
                "magnetic": PhysicalQuantity(value=kpi.magnetic_losses, unit="W"),
            }
        )
    
    @staticmethod
    def tas_to_operating_point(tas_op: "OperatingPoint"):
        """Convert TAS OperatingPoint to converter_lib format."""
        from converter_lib.core.operating_point import OperatingPoint as NTOperatingPoint
        ...
    
    @staticmethod
    def populate_tas_outputs(tas: TAS, converter_lib_results: dict) -> TAS:
        """Populate TAS outputs from converter_lib calculation results."""
        ...
```

### Acceptance Criteria S5
- [ ] LossBreakdown completo con tutte le categorie
- [ ] ThermalResults con thermal margin check
- [ ] Integration con ElectricalKPI funzionante
- [ ] Power density calculation verificata

---

## 📋 Sprint 6: OpenMagnetics MAS Integration
**Durata:** 2 settimane  
**Ore stimate:** 15h  
**Priorità:** 🟡 High

### Obiettivi
1. Implementare MAS file loader
2. Creare wrapper per magnetic component specs
3. Supportare both inline e file reference

### Tasks

#### 6.1 MAS Schema Integration (4h)
```python
# tas/integrations/mas/mas_loader.py
from pathlib import Path
import json
from typing import Optional, Union

class MASLoader:
    """Load and parse OpenMagnetics MAS files."""
    
    def __init__(self):
        self._cache: dict[str, dict] = {}
    
    def load(self, reference: str) -> dict:
        """Load MAS from file:// or openmagnetics:// reference."""
        if reference in self._cache:
            return self._cache[reference]
        
        if reference.startswith("file://"):
            path = Path(reference[7:])
            data = json.loads(path.read_text())
        elif reference.startswith("openmagnetics://"):
            # Fetch from OpenMagnetics catalog API
            data = self._fetch_from_catalog(reference)
        else:
            raise ValueError(f"Unknown MAS reference format: {reference}")
        
        self._cache[reference] = data
        return data
    
    def _fetch_from_catalog(self, reference: str) -> dict:
        """Fetch from OpenMagnetics online catalog."""
        # Parse: openmagnetics://catalog/ETD49_N87_100uH
        # Use OpenMagnetics API
        ...
```

#### 6.2 MAS to converter_lib Magnetic Model (6h)
```python
# tas/integrations/mas/mas_converter.py
class MASToconverter_libConverter:
    """Convert MAS magnetic definition to converter_lib format."""
    
    def convert_inductor(self, mas_data: dict) -> "InductorModel":
        """Convert MAS inductor to converter_lib InductorModel."""
        # Extract core parameters
        core = mas_data.get("magnetic", {}).get("core", {})
        winding = mas_data.get("magnetic", {}).get("winding", {})
        
        # Map to converter_lib structure
        return InductorModel(
            core_type=core.get("shape"),
            core_material=core.get("material"),
            air_gap=core.get("gapping", [{}])[0].get("length"),
            turns=winding.get("turns_description", [{}])[0].get("number_turns"),
            wire_type=winding.get("layers_description", [{}])[0].get("wire_type"),
            # ... more mappings
        )
    
    def convert_transformer(self, mas_data: dict) -> "TransformerModel":
        """Convert MAS transformer to converter_lib format."""
        ...
```

#### 6.3 Bidirectional Export (3h)
```python
# tas/integrations/mas/mas_exporter.py
class converter_libToMASExporter:
    """Export converter_lib magnetic models to MAS format."""
    
    def export_inductor(self, inductor: "InductorModel") -> dict:
        """Export inductor to MAS JSON structure."""
        return {
            "magnetic": {
                "core": {
                    "shape": inductor.core_type,
                    "material": inductor.core_material,
                    "gapping": [{"type": "subtractive", "length": inductor.air_gap}]
                },
                "winding": {
                    "turns_description": [{"number_turns": inductor.turns}]
                }
            }
        }
```

#### 6.4 Tests (2h)
```python
# tests/tas/test_mas_integration.py
class TestMASIntegration:
    def test_load_local_mas_file(self):
        loader = MASLoader()
        data = loader.load("file://samples/inductor.mas.json")
        assert "magnetic" in data
        
    def test_convert_to_converter_lib(self):
        converter = MASToconverter_libConverter()
        mas_data = {...}  # Sample MAS
        inductor = converter.convert_inductor(mas_data)
        assert inductor.core_type is not None
```

### Acceptance Criteria S6
- [ ] MAS files load correctly
- [ ] OpenMagnetics catalog API integration
- [ ] Bidirectional conversion funziona
- [ ] Tested con almeno 3 magnetic components

---

## 📋 Sprint 7: Export to Simulation Tools
**Durata:** 2 settimane  
**Ore stimate:** 25h  
**Priorità:** 🟢 Medium

### Obiettivi
1. PLECS netlist export
2. LTspice .asc export
3. GeckoCircuits export

### Tasks

#### 7.1 PLECS Exporter (10h)
```python
# tas/exporters/plecs_exporter.py
class PLECSExporter:
    """Export TAS to PLECS simulation file."""
    
    def __init__(self, tas: TAS):
        self.tas = tas
        
    def export(self, output_path: str) -> None:
        """Export to PLECS .plecs file."""
        # PLECS uses XML format internally
        ...
    
    def _create_component_block(self, comp: Component) -> str:
        """Create PLECS component block."""
        if isinstance(comp, SwitchComponent):
            return self._create_mosfet_block(comp)
        elif isinstance(comp, CapacitorComponent):
            return self._create_capacitor_block(comp)
        ...
    
    def _generate_netlist(self) -> str:
        """Generate PLECS netlist from TAS."""
        ...
```

#### 7.2 LTspice Exporter (8h)
```python
# tas/exporters/ltspice_exporter.py
class LTspiceExporter:
    """Export TAS to LTspice .asc file."""
    
    def export(self, output_path: str) -> None:
        """Export to LTspice schematic."""
        lines = []
        lines.append("Version 4")
        lines.append("SHEET 1 880 680")
        
        # Add components
        for comp in self.tas.converter.components:
            lines.extend(self._component_to_ltspice(comp))
        
        # Add wires from netlist
        lines.extend(self._netlist_to_wires())
        
        Path(output_path).write_text("\n".join(lines))
    
    def _component_to_ltspice(self, comp: Component) -> list[str]:
        """Convert component to LTspice format."""
        ...
```

#### 7.3 GeckoCircuits Exporter (5h)
```python
# tas/exporters/gecko_exporter.py
class GeckoCircuitsExporter:
    """Export TAS to GeckoCircuits .ipes file."""
    
    def export(self, output_path: str) -> None:
        """Export to GeckoCircuits format."""
        # GeckoCircuits uses custom XML format
        ...
```

#### 7.4 Generic Netlist Format (2h)
```python
# tas/exporters/netlist_exporter.py
class GenericNetlistExporter:
    """Export to generic SPICE-compatible netlist."""
    
    def export_spice(self, output_path: str) -> None:
        """Export to .cir SPICE file."""
        lines = [f"* {self.tas.metadata.name}"]
        lines.append(f"* Generated from TAS on {datetime.now()}")
        lines.append("")
        
        # Add subcircuits for complex components
        # Add main circuit
        # Add analysis commands
        
        Path(output_path).write_text("\n".join(lines))
```

### Acceptance Criteria S7
- [ ] PLECS export produce simulazione funzionante
- [ ] LTspice export verificato con test case
- [ ] Netlist format valido per tutti i simulatori

---

## 📋 Sprint 8: Validation + Documentation
**Durata:** 2 settimane  
**Ore stimate:** 15h  
**Priorità:** 🟢 Medium

### Tasks

#### 8.1 End-to-End Validation (5h)
```python
# tests/tas/test_e2e.py
class TestEndToEnd:
    def test_buck_converter_complete_flow(self):
        """Test complete TAS workflow for buck converter."""
        # 1. Load TAS
        tas = TAS.from_json("samples/buck_5kW_sic.tas.json")
        
        # 2. Validate
        validator = TASValidator()
        valid, errors = validator.validate(tas.model_dump())
        assert valid, errors
        
        # 3. Run converter_lib analysis
        bridge = converter_libBridge()
        results = bridge.analyze(tas)
        
        # 4. Populate outputs
        tas = bridge.populate_tas_outputs(tas, results)
        
        # 5. Export to PLECS
        exporter = PLECSExporter(tas)
        exporter.export("output/buck_5kW.plecs")
        
        # 6. Verify outputs
        assert tas.outputs.calculated
        assert tas.outputs.power_density.value > 0
```

#### 8.2 Documentation (5h)
```markdown
# tas/docs/index.md

## Quick Start

```python
from tas import TAS, ComponentDatabase

# Load TAS file
tas = TAS.from_json("my_converter.tas.json")

# Access design requirements
print(f"Power: {tas.inputs.design_requirements.power.nominal}")

# Run analysis
from converter_lib import analyze
results = analyze(tas)

# Export
tas.to_plecs("simulation.plecs")
```

## API Reference
...
```

#### 8.3 Sample Files (5h)
- Buck converter (già creato)
- Boost PFC
- LLC converter
- Vienna rectifier

### Acceptance Criteria S8
- [ ] E2E test passa per tutti i samples
- [ ] Documentation completa
- [ ] 4+ sample files validati

---

## 📊 Dependency Graph

```
S1 (Core Models)
    │
    ├──▶ S2 (Inputs)
    │       │
    │       └──▶ S3 (Converter)
    │               │
    │               ├──▶ S4 (Components DB)
    │               │       │
    │               │       └──▶ S5 (Outputs)
    │               │               │
    │               │               └──▶ S8 (Validation)
    │               │
    │               └──▶ S6 (MAS Integration)
    │                       │
    │                       └──▶ S8 (Validation)
    │
    └──▶ S7 (Exporters) ──▶ S8 (Validation)
```

---

## 🎯 Definition of Done (DoD)

Per ogni Sprint:
- [ ] Tutti i task completati
- [ ] Unit tests con coverage > 80%
- [ ] Integration tests passano
- [ ] Code review completata
- [ ] Documentazione aggiornata
- [ ] No critical/high bugs aperti

---

## 📈 Metriche di Successo

| Metrica | Target | Verifica |
|---------|--------|----------|
| Test Coverage | > 85% | pytest-cov |
| JSON Schema Validation | 100% | jsonschema |
| PLECS Export Accuracy | < 1% error | Cross-validation |
| MAS Compatibility | 100% | OpenMagnetics test suite |
| Documentation | Complete | All public APIs documented |

---

## 🚨 Rischi e Mitigazioni

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| OpenMagnetics API changes | Media | Alto | Pin versione, local fallback |
| PLECS format undocumented | Alta | Medio | Reverse engineering, test-driven |
| Performance con large netlists | Bassa | Medio | Lazy loading, caching |
| Pydantic v1/v2 compatibility | Bassa | Alto | Target Pydantic v2 only |

---

## 📝 Note Implementative

### Convenzioni Codice
- Python 3.10+ con type hints
- Pydantic v2 per validazione
- Black + isort per formatting
- pytest per testing

### Struttura File Finale
```
converter_lib/
├── tas/
│   ├── __init__.py
│   ├── models/
│   │   ├── quantities.py
│   │   ├── waveforms.py
│   │   ├── tas_root.py
│   │   ├── inputs/
│   │   ├── converter/
│   │   ├── outputs/
│   │   └── components/
│   ├── validation/
│   ├── database/
│   ├── integrations/
│   │   └── mas/
│   ├── exporters/
│   └── schemas/
├── tests/
│   └── tas/
└── docs/
```

---

*Documento creato: 2026-01-25*  
*Autore: converter_lib Team*
