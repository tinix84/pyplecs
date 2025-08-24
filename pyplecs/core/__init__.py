"""Core PyPLECS module with OOP architecture support."""

from .models import (
    # Enums and status types
    SimulationStatus,
    SimulationType,
    
    # New OOP Architecture classes
    NewSimulationResult,
    PLECSModel,
    PLECSApp,
    PLECSGUIApp,
    PLECSXRPCApp,
    SimulationPlan,
    PLECSSimulation,
    PLECSServer,
    
    # Legacy classes (backward compatibility)
    SimulationRequest,
    SimulationResult,
    ComponentParameter,
    ModelVariant,
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
    # Enums and status
    'SimulationStatus',
    'SimulationType',
    
    # New OOP Architecture
    'NewSimulationResult',
    'PLECSModel',
    'PLECSApp',
    'PLECSGUIApp',
    'PLECSXRPCApp',
    'SimulationPlan',
    'PLECSSimulation',
    'PLECSServer',
    
    # Legacy (backward compatibility)
    'SimulationRequest',
    'SimulationResult',
    'ComponentParameter',
    'ModelVariant',
    'OptimizationObjective',
    'OptimizationParameter',
    'OptimizationRequest',
    'OptimizationResult',
    'WebGuiState',
    'McpTool',
    'McpResource',
    'LogEntry'
]
