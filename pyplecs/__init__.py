# -*- coding: utf-8 -*-
"""
PyPLECS - Advanced PLECS Simulation Automation

A comprehensive Python package for automating PLECS simulations with:
- Web UI for monitoring and control
- REST API for integration
- Intelligent caching system
- Parameter optimization
- Model Context Protocol (MCP) server
- Structured logging and monitoring

Created on Wed Oct 23 17:51:58 2019
Refactored: August 2025

@author: tinivella
"""

# Version info
import sys as _sys

__version__ = "1.0.0"
__author__ = "Riccardo Tinivella"
__email__ = "tinix84@gmail.com"

# Legacy imports (optional - only if pywinauto is available)
try:
    from .pyplecs import PlecsApp, PlecsServer

    # GenericConverterPlecsMdl and generate_variant_plecs_mdl removed in v1.0.0
    _legacy_available = True
except ImportError:
    # Create placeholder classes for missing dependencies
    PlecsServer = None
    PlecsApp = None
    _legacy_available = False

# New architecture imports
from .cache import SimulationCache
from .config import get_config, init_config
from .core import (
    ComponentParameter,
    # ModelVariant removed in v1.0.0
    OptimizationRequest,
    OptimizationResult,
    SimulationRequest,
    SimulationResult,
    SimulationStatus,
)
from .normalization import normalize_plecs_result
from .orchestration import SimulationOrchestrator, TaskPriority
from .quantities import (
    DesignQuantities,
    SignalMap,
    SignalPair,
    SteadyStateWindow,
    capture_waveforms,
    component_stress,
    design_quantities,
    power_balance,
)
from .studies import (
    CollectResultsReducer,
    ExplicitParameterVectorStrategy,
    ParameterVector,
    ParametricPointOutcome,
    ParametricStudy,
    ParametricStudyOutcome,
    ParametricStudyStatus,
)
from .tas import (
    DiagnosticSeverity,
    TasCapture,
    TasCompilation,
    TasCompilationError,
    TasCompiler,
    TasDiagnostic,
    TasExecutionEnvelope,
    TasExecutionService,
)

# Optional logging (requires structlog)
try:
    from .logging import get_logger, init_logging
except ImportError:
    get_logger = None
    init_logging = None

# Optional imports (only if dependencies are available)
try:
    from .api import create_api_app
except ImportError:
    create_api_app = None

try:
    from .webgui import create_web_app
except ImportError:
    create_web_app = None

try:
    from .mcp import create_mcp_server
except ImportError:
    create_mcp_server = None

try:
    from .optimizer import OptimizationEngine
except ImportError:
    OptimizationEngine = None

# Informational only, and on stderr: a library that writes to stdout at import
# time corrupts the output of anything that parses it -- start_plecs.bat reads
# the configured PLECS path from a `uv run python -c ...` call.
print(
    f"PyPLECS v{__version__} - Advanced PLECS Simulation Automation",
    file=_sys.stderr,
)
if not _legacy_available:
    print(
        "Note: Legacy PLECS GUI automation not available (missing pywinauto)",
        file=_sys.stderr,
    )

# Expose main classes and functions
__all__ = [
    # Legacy API (may be None if dependencies missing)
    "PlecsServer",
    # 'GenericConverterPlecsMdl',  # Removed in v1.0.0
    "PlecsApp",
    # 'generate_variant_plecs_mdl',  # Removed in v1.0.0
    # Configuration
    "get_config",
    "init_config",
    # Core models
    "SimulationRequest",
    "SimulationResult",
    "SimulationStatus",
    "normalize_plecs_result",
    "ComponentParameter",
    # 'ModelVariant',  # Removed in v1.0.0
    "OptimizationRequest",
    "OptimizationResult",
    # Main services
    "SimulationOrchestrator",
    "TaskPriority",
    "SimulationCache",
    # Parametric Study
    "CollectResultsReducer",
    "ExplicitParameterVectorStrategy",
    "ParameterVector",
    "ParametricPointOutcome",
    "ParametricStudy",
    "ParametricStudyOutcome",
    "ParametricStudyStatus",
    # Design Quantities
    "DesignQuantities",
    "SignalMap",
    "SignalPair",
    "SteadyStateWindow",
    "capture_waveforms",
    "component_stress",
    "design_quantities",
    "power_balance",
    # TAS electrical projection
    "DiagnosticSeverity",
    "TasCapture",
    "TasCompilation",
    "TasCompilationError",
    "TasCompiler",
    "TasDiagnostic",
    "TasExecutionEnvelope",
    "TasExecutionService",
    # Logging
    "get_logger",
    "init_logging",
    # Optional services
    "create_api_app",
    "create_web_app",
    "create_mcp_server",
    "OptimizationEngine",
]
