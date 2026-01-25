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
__version__ = "1.0.0"
__author__ = "Riccardo Tinivella"
__email__ = "tinix84@gmail.com"

# Legacy imports (optional - only if pywinauto is available)
try:
    from .pyplecs import PlecsServer, PlecsApp
    # GenericConverterPlecsMdl and generate_variant_plecs_mdl removed in v1.0.0
    _legacy_available = True
except ImportError:
    # Create placeholder classes for missing dependencies
    PlecsServer = None
    PlecsApp = None
    _legacy_available = False

# New architecture imports
from .config import get_config, init_config
from .core import (
    SimulationRequest,
    SimulationResult,
    SimulationStatus,
    ComponentParameter,
    # ModelVariant removed in v1.0.0
    OptimizationRequest,
    OptimizationResult
)
from .orchestration import SimulationOrchestrator, TaskPriority
from .cache import SimulationCache

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

print(f'PyPLECS v{__version__} - Advanced PLECS Simulation Automation')
if not _legacy_available:
    print('Note: Legacy PLECS GUI automation not available (missing pywinauto)')

# Expose main classes and functions
__all__ = [
    # Legacy API (may be None if dependencies missing)
    'PlecsServer',
    # 'GenericConverterPlecsMdl',  # Removed in v1.0.0
    'PlecsApp',
    # 'generate_variant_plecs_mdl',  # Removed in v1.0.0

    # Configuration
    'get_config',
    'init_config',

    # Core models
    'SimulationRequest',
    'SimulationResult',
    'SimulationStatus',
    'ComponentParameter',
    # 'ModelVariant',  # Removed in v1.0.0
    'OptimizationRequest',
    'OptimizationResult',

    # Main services
    'SimulationOrchestrator',
    'TaskPriority',
    'SimulationCache',

    # Logging
    'get_logger',
    'init_logging',

    # Optional services
    'create_api_app',
    'create_web_app',
    'create_mcp_server',
    'OptimizationEngine',
]
