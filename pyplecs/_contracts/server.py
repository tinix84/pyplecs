# Vendored from tinix84/pycircuitsim@a065438297155d73469ebce83ef6ecb051aec8aa
# Source: packages/pycircuitsim-core/pycircuitsim_core/server.py
# DO NOT EDIT — re-sync via tools/SYNC_PYCIRCUITSIM_CORE.md.

"""Abstract base class for simulation servers.

Both PlecsServer (XML-RPC) and GeckoServer (REST API) implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pyplecs._contracts.models import SimulationRequest, SimulationResult


class SimulationServer(ABC):
    """Abstract simulation server interface.

    Implementations must support:
    - Single simulation (blocking)
    - Batch simulation (parallel where possible)
    - Health check
    - Context manager protocol
    """

    @abstractmethod
    def simulate(self, request: SimulationRequest) -> SimulationResult:
        """Run a single simulation (blocking)."""

    @abstractmethod
    def simulate_batch(self, requests: list[SimulationRequest]) -> list[SimulationResult]:
        """Run multiple simulations (parallel where the backend supports it)."""

    def simulate_raw(
        self,
        model_file: str,
        parameters: dict[str, Any] | None = None,
        simulation_time: float | None = None,
        time_step: float | None = None,
        **options: Any,
    ) -> SimulationResult:
        """Convenience wrapper that builds SimulationRequest internally."""
        req = SimulationRequest(
            model_file=model_file,
            parameters=parameters or {},
            simulation_time=simulation_time,
            time_step=time_step,
            options=options,
        )
        return self.simulate(req)

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the simulation backend is reachable."""

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Return detailed health info from the backend."""

    def close(self) -> None:
        """Release resources. Override if cleanup is needed."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False
