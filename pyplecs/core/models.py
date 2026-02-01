"""Core data models for PyPLECS."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import pandas as pd
from pathlib import Path


class SimulationStatus(Enum):
    """Simulation task status."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SimulationRequest:
    """Request for a PLECS simulation."""

    model_file: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    simulation_time: Optional[float] = None
    output_variables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and normalize the request."""
        # Ensure model file exists
        if not Path(self.model_file).exists():
            raise FileNotFoundError(f"Model file not found: {self.model_file}")

        # Convert relative path to absolute
        self.model_file = str(Path(self.model_file).resolve())


@dataclass
class SimulationResult:
    """Result of a PLECS simulation."""

    task_id: str
    success: bool
    timeseries_data: Optional[pd.DataFrame] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time: float = 0.0
    cached: bool = False
    plecs_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "task_id": self.task_id,
            "success": self.success,
            "timeseries_data": self.timeseries_data.to_dict()
            if self.timeseries_data is not None
            else None,
            "metadata": self.metadata,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "cached": self.cached,
            "plecs_version": self.plecs_version,
        }


@dataclass
class ComponentParameter:
    """Parameter for a PLECS component."""

    name: str
    value: Union[float, int, str]
    component_path: str
    parameter_name: str

    def to_plecs_reference(self) -> str:
        """Get PLECS reference string for this parameter."""
        return f"{self.component_path}/{self.parameter_name}"


# DEPRECATED: ModelVariant class removed in v1.0.0
# Use SimulationRequest with parameters dict instead
# PLECS native ModelVars handles parameter variations without file generation


@dataclass
class OptimizationObjective:
    """Optimization objective definition."""

    name: str
    variable: str  # Variable name in simulation results
    target_value: Optional[float] = None
    minimize: bool = True
    weight: float = 1.0
    constraint_min: Optional[float] = None
    constraint_max: Optional[float] = None


@dataclass
class OptimizationParameter:
    """Parameter to be optimized."""

    name: str
    min_value: float
    max_value: float
    initial_value: Optional[float] = None
    parameter_type: str = "float"  # float, int, discrete
    discrete_values: List[Union[float, int]] = field(default_factory=list)


@dataclass
class OptimizationRequest:
    """Request for parameter optimization."""

    model_file: str
    objectives: List[OptimizationObjective]
    parameters: List[OptimizationParameter]
    algorithm: str = "scipy_minimize"
    algorithm_options: Dict[str, Any] = field(default_factory=dict)
    max_iterations: int = 100
    convergence_tolerance: float = 1e-6
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationResult:
    """Result of parameter optimization."""

    request_id: str
    success: bool
    optimal_parameters: Dict[str, float] = field(default_factory=dict)
    optimal_objectives: Dict[str, float] = field(default_factory=dict)
    convergence_history: List[Dict[str, Any]] = field(default_factory=list)
    total_iterations: int = 0
    total_simulations: int = 0
    execution_time: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebGuiState:
    """State information for web GUI."""

    simulation_queue: List[Dict[str, Any]] = field(default_factory=list)
    active_simulations: List[Dict[str, Any]] = field(default_factory=list)
    completed_simulations: List[Dict[str, Any]] = field(default_factory=list)
    system_stats: Dict[str, Any] = field(default_factory=dict)
    worker_stats: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class McpTool:
    """Model Context Protocol tool definition."""

    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[callable] = None


@dataclass
class McpResource:
    """Model Context Protocol resource definition."""

    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"
    content: Optional[str] = None


@dataclass
class LogEntry:
    """Structured log entry."""

    timestamp: float
    level: str
    logger: str
    message: str
    task_id: Optional[str] = None
    worker_id: Optional[str] = None
    simulation_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "logger": self.logger,
            "message": self.message,
            "task_id": self.task_id,
            "worker_id": self.worker_id,
            "simulation_hash": self.simulation_hash,
            "metadata": self.metadata,
        }
