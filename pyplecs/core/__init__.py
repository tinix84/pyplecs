"""Core PyPLECS module."""

from .models import (
    ComponentParameter,
    LogEntry,
    McpResource,
    McpTool,
    # ModelVariant removed in v1.0.0 - use SimulationRequest with parameters instead
    OptimizationObjective,
    OptimizationParameter,
    OptimizationRequest,
    OptimizationResult,
    SimulationRequest,
    SimulationResult,
    SimulationStatus,
    WebGuiState,
)

__all__ = [
    "SimulationRequest",
    "SimulationResult",
    "SimulationStatus",
    "ComponentParameter",
    # 'ModelVariant',  # Removed in v1.0.0
    "OptimizationObjective",
    "OptimizationParameter",
    "OptimizationRequest",
    "OptimizationResult",
    "WebGuiState",
    "McpTool",
    "McpResource",
    "LogEntry",
]
