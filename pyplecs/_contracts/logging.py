# Vendored from tinix84/pycircuitsim@a065438297155d73469ebce83ef6ecb051aec8aa
# Source: packages/pycircuitsim-core/pycircuitsim_core/logging.py
# DO NOT EDIT — re-sync via tools/SYNC_PYCIRCUITSIM_CORE.md.

"""Abstract base class for structured logging."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class StructuredLoggerBase(ABC):
    """Abstract structured logger interface."""

    @abstractmethod
    def log_simulation_start(
        self,
        task_id: str,
        model_file: str,
        parameters: dict[str, Any],
        worker_id: Optional[str] = None,
    ) -> None:
        """Log simulation start."""

    @abstractmethod
    def log_simulation_complete(
        self,
        task_id: str,
        success: bool,
        execution_time: float,
        worker_id: Optional[str] = None,
        cached: bool = False,
    ) -> None:
        """Log simulation completion."""

    @abstractmethod
    def log_simulation_error(
        self, task_id: str, error_message: str, worker_id: Optional[str] = None
    ) -> None:
        """Log simulation error."""

    @abstractmethod
    def log_cache_hit(self, task_id: str, simulation_hash: str, model_file: str) -> None:
        """Log cache hit."""

    @abstractmethod
    def log_cache_miss(self, task_id: str, simulation_hash: str, model_file: str) -> None:
        """Log cache miss."""

    @abstractmethod
    def log_api_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time: float,
        client_ip: Optional[str] = None,
    ) -> None:
        """Log API request."""
