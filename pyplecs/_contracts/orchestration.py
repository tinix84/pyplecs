# Vendored from tinix84/pycircuitsim@a065438297155d73469ebce83ef6ecb051aec8aa
# Source: packages/pycircuitsim-core/pycircuitsim_core/orchestration.py
# DO NOT EDIT — re-sync via tools/SYNC_PYCIRCUITSIM_CORE.md.

"""Abstract base class for simulation orchestration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from pyplecs._contracts.models import SimulationRequest, SimulationResult, TaskPriority


class SimulationOrchestratorBase(ABC):
    """Abstract simulation orchestrator interface."""

    @abstractmethod
    async def submit_simulation(
        self,
        request: SimulationRequest,
        priority: TaskPriority = TaskPriority.NORMAL,
        use_cache: bool = True,
    ) -> str:
        """Submit a simulation for execution. Returns task ID."""

    @abstractmethod
    async def get_task_status(self, task_id: str) -> Optional[dict[str, Any]]:
        """Get status of a specific task."""

    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a queued or running task."""

    @abstractmethod
    async def start(self) -> None:
        """Start the orchestrator loop."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the orchestrator loop."""

    @abstractmethod
    def get_orchestrator_stats(self) -> dict[str, Any]:
        """Get orchestrator statistics."""

    @abstractmethod
    async def wait_for_completion(
        self, task_id: str, timeout: Optional[float] = None
    ) -> Optional[SimulationResult]:
        """Wait for a specific task to complete."""

    @abstractmethod
    async def wait_for_all_tasks(self, timeout: Optional[float] = None) -> bool:
        """Wait for all tasks to complete. Returns True if all done, False if timeout."""

    @abstractmethod
    def add_callback(self, event: str, callback: Callable) -> None:
        """Add callback for orchestrator events.

        Events: on_task_started, on_task_completed, on_task_failed,
                on_queue_empty, on_batch_started, on_batch_completed
        """

    @abstractmethod
    def remove_callback(self, event: str, callback: Callable) -> None:
        """Remove a previously registered callback."""
