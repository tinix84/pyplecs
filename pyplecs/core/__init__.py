"""Core PyPLECS module."""

from .models import (
    SimulationRequest,
    SimulationResult,
    SimulationStatus,
    ComponentParameter,
    # ModelVariant removed in v1.0.0 - use SimulationRequest with parameters instead
    OptimizationObjective,
    OptimizationParameter,
    OptimizationRequest,
    OptimizationResult,
    WebGuiState,
    McpTool,
    McpResource,
    LogEntry
)

__all__ = [
    'SimulationRequest',
    'SimulationResult',
    'SimulationStatus',
    'ComponentParameter',
    # 'ModelVariant',  # Removed in v1.0.0
    'OptimizationObjective',
    'OptimizationParameter',
    'OptimizationRequest',
    'OptimizationResult',
    'WebGuiState',
    'McpTool',
    'McpResource',
    'LogEntry'
]
