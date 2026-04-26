# Vendored from tinix84/pycircuitsim@a065438297155d73469ebce83ef6ecb051aec8aa
# Source: packages/pycircuitsim-core/pycircuitsim_core/__init__.py
# DO NOT EDIT — re-sync via tools/SYNC_PYCIRCUITSIM_CORE.md.
#
# Local divergence: StructuredLoggerBase is added to __all__
# (upstream defines it in logging.py but omits from its __all__).

"""pycircuitsim-core — Shared interfaces for circuit simulation tools.

Provides abstract base classes that both pyplecs and pygeckocircuit implement,
enabling tool-agnostic simulation scripts.
"""

from pyplecs._contracts.cache import SimulationCacheBase
from pyplecs._contracts.config import ConfigManagerBase
from pyplecs._contracts.logging import StructuredLoggerBase
from pyplecs._contracts.models import (
    SimulationRequest,
    SimulationResult,
    SimulationStatus,
    SyncSimulationRequest,
    SyncSimulationResponse,
    TaskPriority,
)
from pyplecs._contracts.orchestration import SimulationOrchestratorBase
from pyplecs._contracts.server import SimulationServer

__version__ = "1.0.0"
__contract_version__ = "1.0"

__all__ = [
    "SimulationServer",
    "SimulationCacheBase",
    "SimulationOrchestratorBase",
    "ConfigManagerBase",
    "StructuredLoggerBase",
    "SimulationRequest",
    "SimulationResult",
    "SimulationStatus",
    "SyncSimulationRequest",
    "SyncSimulationResponse",
    "TaskPriority",
    "__contract_version__",
]
