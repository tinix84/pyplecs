"""Verify pyplecs concrete classes satisfy pycircuitsim_core ABCs.

Runs without PLECS — uses class-level introspection only.
"""
from __future__ import annotations

import pytest


def test_contracts_facade_resolves():
    """The façade resolves to a known source."""
    from pyplecs import contracts

    assert contracts._source in ("pypi", "vendored")
    assert contracts.__contract_version__ == "1.0"


def test_plecs_server_subclasses_simulation_server():
    """PlecsServer inherits from contracts.SimulationServer."""
    from pyplecs.contracts import SimulationServer
    from pyplecs.pyplecs import PlecsServer

    assert issubclass(PlecsServer, SimulationServer)
    assert PlecsServer.__abstractmethods__ == frozenset(), (
        f"PlecsServer has unimplemented abstracts: {PlecsServer.__abstractmethods__}"
    )


def test_simulation_cache_subclasses_cache_base():
    from pyplecs.cache import SimulationCache
    from pyplecs.contracts import SimulationCacheBase

    assert issubclass(SimulationCache, SimulationCacheBase)
    assert SimulationCache.__abstractmethods__ == frozenset(), (
        f"SimulationCache has unimplemented abstracts: {SimulationCache.__abstractmethods__}"
    )


def test_config_manager_subclasses_config_base():
    from pyplecs.config import ConfigManager
    from pyplecs.contracts import ConfigManagerBase

    assert issubclass(ConfigManager, ConfigManagerBase)
    assert ConfigManager.__abstractmethods__ == frozenset(), (
        f"ConfigManager has unimplemented abstracts: {ConfigManager.__abstractmethods__}"
    )


def test_structured_logger_subclasses_logger_base():
    pytest.importorskip("structlog")
    from pyplecs.contracts import StructuredLoggerBase
    from pyplecs.logging import StructuredLogger

    assert issubclass(StructuredLogger, StructuredLoggerBase)
    assert StructuredLogger.__abstractmethods__ == frozenset(), (
        f"StructuredLogger has unimplemented abstracts: {StructuredLogger.__abstractmethods__}"
    )


def test_simulation_orchestrator_subclasses_orchestrator_base():
    from pyplecs.contracts import SimulationOrchestratorBase
    from pyplecs.orchestration import SimulationOrchestrator

    assert issubclass(SimulationOrchestrator, SimulationOrchestratorBase)
    assert SimulationOrchestrator.__abstractmethods__ == frozenset(), (
        f"SimulationOrchestrator has unimplemented abstracts: "
        f"{SimulationOrchestrator.__abstractmethods__}"
    )


def test_contracts_exports_complete():
    """Façade re-exports every name promised in the spec."""
    from pyplecs import contracts

    expected = {
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
    }
    missing = expected - set(dir(contracts))
    assert not missing, f"Missing from pyplecs.contracts: {missing}"
