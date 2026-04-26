# Vendored from tinix84/pycircuitsim@a065438297155d73469ebce83ef6ecb051aec8aa
# Source: packages/pycircuitsim-core/pycircuitsim_core/models.py
# DO NOT EDIT — re-sync via tools/SYNC_PYCIRCUITSIM_CORE.md.

"""Shared data models for circuit simulation tools.

These models define the common interface between pyplecs and pygeckocircuit.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

import pandas as pd
from pydantic import BaseModel, Field


class SimulationStatus(str, Enum):
    """Simulation task status (common across all tools)."""

    QUEUED = "QUEUED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskPriority(Enum):
    """Task priority levels for orchestration."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class SimulationRequest(BaseModel):
    """Tool-agnostic simulation request."""

    model_file: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    simulation_time: Optional[float] = None
    time_step: Optional[float] = None
    output_variables: list[str] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SimulationResult(BaseModel):
    """Tool-agnostic simulation result."""

    task_id: str = ""
    success: bool = False
    time: list[float] = Field(default_factory=list)
    signals: dict[str, list[float]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None
    cached: bool = False

    def to_dataframe(self) -> pd.DataFrame:
        """Convert result to pandas DataFrame with time index."""
        data = {"time": self.time, **self.signals}
        return pd.DataFrame(data)


class SyncSimulationRequest(BaseModel):
    """Request for sync simulation endpoints (FastAPI proxy)."""

    model_file: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    signal_map: Optional[dict[str, str]] = None


class SyncSimulationResponse(BaseModel):
    """Response from sync simulation endpoints."""

    success: bool
    time: list[float] = Field(default_factory=list)
    signals: dict[str, list[float]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
