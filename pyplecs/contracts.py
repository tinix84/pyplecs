"""Stable public namespace for shared simulation contracts.

Imports are tried in this order:
  1. The PyPI ``pycircuitsim_core`` package, if installed AND its contract
     version matches what pyplecs was tested against.
  2. The vendored copy at ``pyplecs._contracts``.

This means pyplecs works standalone (vendored) AND silently picks up the
canonical upstream package when the umbrella pyCircuitSim ecosystem is
present, as long as the contract major version matches.
"""

from __future__ import annotations

# Contract major version pyplecs has been tested against.
# Bumped only when the vendored copy is re-synced from upstream.
__contract_version__ = "1.0"


def _resolve_source() -> str:
    """Decide whether to use external or vendored implementations.

    Returns 'pypi' if external pycircuitsim_core is importable AND
    version-compatible; otherwise 'vendored'. Result is cached at
    module import time via the assignments below.
    """
    try:
        import pycircuitsim_core as _ext
    except ImportError:
        return "vendored"

    ext_version = (
        getattr(_ext, "__contract_version__", None)
        or getattr(_ext, "__version__", "0.0")
    )
    ext_major = str(ext_version).split(".")[0]
    our_major = __contract_version__.split(".")[0]
    if ext_major != our_major:
        return "vendored"
    return "pypi"


_source = _resolve_source()


if _source == "pypi":
    try:
        # StructuredLoggerBase is missing from upstream __all__; import directly:
        from pycircuitsim_core.logging import StructuredLoggerBase  # type: ignore[import-not-found]

        from pycircuitsim_core import (  # type: ignore[import-not-found]
            ConfigManagerBase,
            SimulationCacheBase,
            SimulationOrchestratorBase,
            SimulationRequest,
            SimulationResult,
            SimulationServer,
            SimulationStatus,
            SyncSimulationRequest,
            SyncSimulationResponse,
            TaskPriority,
        )
    except ImportError:
        # External pycircuitsim_core is importable as a package but one or
        # more expected names is missing (upstream rename, partial install,
        # contract drift not caught by the major-version check). Fall back
        # to the vendored copy so pyplecs.contracts always loads.
        _source = "vendored"

if _source == "vendored":
    from pyplecs._contracts import (  # noqa: F811 - intentional fallback override
        ConfigManagerBase,
        SimulationCacheBase,
        SimulationOrchestratorBase,
        SimulationRequest,
        SimulationResult,
        SimulationServer,
        SimulationStatus,
        StructuredLoggerBase,
        SyncSimulationRequest,
        SyncSimulationResponse,
        TaskPriority,
    )


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
