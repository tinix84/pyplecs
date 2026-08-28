"""Simulation MCP Server tools: a transport over the Simulation Task lifecycle.

Every tool here is a thin adapter on ``SimulationOrchestrator``. The catalogue
owns schemas, validation and error text; the orchestrator owns acceptance,
scheduling, caching and terminal truth (ADR-0011).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from pyplecs.contracts import TaskPriority

from ..core.models import SimulationRequest, SimulationResult, SimulationStatus
from ..orchestration import TERMINAL_STATUSES, SimulationOrchestrator, SimulationTaskSnapshot
from .plecs_tools import ToolCatalogue, ToolDefinition

MAX_WAIT_SECONDS = 600.0
PRIORITY_NAMES = tuple(priority.name for priority in TaskPriority)
STATUS_VALUES = tuple(status.value for status in SimulationStatus)


def snapshot_payload(snapshot: SimulationTaskSnapshot) -> dict[str, Any]:
    """The one Simulation Task shape every progress tool returns."""
    return {
        "task_id": snapshot.id,
        "model_file": snapshot.model_file,
        "status": snapshot.status.value,
        "priority": snapshot.priority.name,
        "created_at": snapshot.created_at,
        "started_at": snapshot.started_at,
        "completed_at": snapshot.completed_at,
        "retry_count": snapshot.retry_count,
        "error": snapshot.error,
        "terminal": snapshot.status in TERMINAL_STATUSES,
    }


def result_payload(result: SimulationResult) -> dict[str, Any]:
    """The normalized Simulation Result: ``time`` plus named ``signals``."""
    frame = result.timeseries_data
    time: list[float] = []
    signals: dict[str, list[float]] = {}
    if frame is not None:
        time = frame["Time"].tolist() if "Time" in frame.columns else []
        signals = {column: frame[column].tolist() for column in frame.columns if column != "Time"}
    return {
        "task_id": result.task_id,
        "success": result.success,
        "time": time,
        "signals": signals,
        "metadata": dict(result.metadata),
        "cached": result.cached,
        "execution_time": result.execution_time,
        "plecs_version": result.plecs_version,
        "error_message": result.error_message,
    }


def build_simulation_catalogue(orchestrator: SimulationOrchestrator) -> ToolCatalogue:
    """Tools over one orchestrator; tests inject an in-memory PLECS adapter."""

    async def require_snapshot(task_id: str) -> SimulationTaskSnapshot:
        snapshot = await orchestrator.get_task_status(task_id)
        if snapshot is None:
            raise ValueError(f"unknown Simulation Task id: {task_id}")
        return snapshot

    async def simulation_submit(
        model_file: str,
        parameters: Optional[dict[str, Any]] = None,
        output_variables: Optional[list[str]] = None,
        simulation_time: Optional[float] = None,
        priority: str = "NORMAL",
        use_cache: bool = True,
    ) -> dict[str, Any]:
        path = Path(model_file)
        if not path.is_file():
            raise ValueError(f"model file does not exist: {model_file}")
        request = SimulationRequest(
            model_file=str(path),
            parameters=dict(parameters or {}),
            simulation_time=simulation_time,
            output_variables=list(output_variables or []),
        )
        task_id = await orchestrator.submit_simulation(
            request, priority=TaskPriority[priority], use_cache=use_cache
        )
        snapshot = await require_snapshot(task_id)
        return {"task_id": task_id, "status": snapshot.status.value}

    async def simulation_status(task_id: str) -> dict[str, Any]:
        return snapshot_payload(await require_snapshot(task_id))

    async def simulation_wait(task_id: str, timeout_s: float = 30.0) -> dict[str, Any]:
        await require_snapshot(task_id)
        terminal = await orchestrator.wait_for_completion(task_id, timeout=timeout_s)
        return snapshot_payload(terminal or await require_snapshot(task_id))

    async def simulation_result(task_id: str) -> dict[str, Any]:
        snapshot = await require_snapshot(task_id)
        if snapshot.status not in TERMINAL_STATUSES:
            raise ValueError(
                f"Simulation Task {task_id} is not terminal (status: {snapshot.status.value})"
            )
        if snapshot.result is None:
            raise ValueError(f"Simulation Task {task_id} has no Simulation Result")
        return result_payload(snapshot.result)

    async def simulation_cancel(task_id: str) -> dict[str, Any]:
        return {"task_id": task_id, "cancelled": await orchestrator.cancel_task(task_id)}

    def simulation_list(status: Optional[str] = None, limit: int = 100) -> dict[str, Any]:
        snapshots = orchestrator.list_tasks(
            status=None if status is None else SimulationStatus(status), limit=limit
        )
        return {"tasks": [snapshot_payload(snapshot) for snapshot in snapshots], "total": len(snapshots)}

    task_id_property = {"type": "string", "minLength": 1, "description": "Opaque Simulation Task id."}

    return ToolCatalogue(
        [
            ToolDefinition(
                name="simulation_submit",
                description=(
                    "Submit one PLECS simulation as a Simulation Task and return its id. "
                    "Rejected with an explicit error when PLECS is unavailable."
                ),
                input_schema=_schema(
                    {
                        "model_file": {
                            "type": "string",
                            "minLength": 1,
                            "description": "Path to an existing .plecs model file.",
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Model variable values for this Operating Point.",
                        },
                        "output_variables": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Names for the model's output signals, in output order.",
                        },
                        "simulation_time": {"type": "number", "exclusiveMinimum": 0},
                        "priority": {"type": "string", "enum": list(PRIORITY_NAMES)},
                        "use_cache": {"type": "boolean"},
                    },
                    required=["model_file"],
                ),
                handler=simulation_submit,
            ),
            ToolDefinition(
                name="simulation_status",
                description="Return the current snapshot of one Simulation Task.",
                input_schema=_schema({"task_id": task_id_property}, required=["task_id"]),
                handler=simulation_status,
            ),
            ToolDefinition(
                name="simulation_wait",
                description=(
                    "Wait up to timeout_s for a Simulation Task to become terminal and return its "
                    "snapshot; a timeout returns the non-terminal snapshot, not an error."
                ),
                input_schema=_schema(
                    {
                        "task_id": task_id_property,
                        "timeout_s": {
                            "type": "number",
                            "exclusiveMinimum": 0,
                            "maximum": MAX_WAIT_SECONDS,
                        },
                    },
                    required=["task_id"],
                ),
                handler=simulation_wait,
            ),
            ToolDefinition(
                name="simulation_result",
                description=(
                    "Return the normalized Simulation Result (time plus named signals) of a "
                    "terminal Simulation Task; a failed task is a result with success=false."
                ),
                input_schema=_schema({"task_id": task_id_property}, required=["task_id"]),
                handler=simulation_result,
            ),
            ToolDefinition(
                name="simulation_cancel",
                description="Cancel a queued or running Simulation Task.",
                input_schema=_schema({"task_id": task_id_property}, required=["task_id"]),
                handler=simulation_cancel,
            ),
            ToolDefinition(
                name="simulation_list",
                description="List recent Simulation Tasks, optionally filtered by status.",
                input_schema=_schema(
                    {
                        "status": {"type": "string", "enum": list(STATUS_VALUES)},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    }
                ),
                handler=simulation_list,
            ),
        ]
    )


def _schema(properties: dict[str, Any], required: Optional[list[str]] = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(required or []),
        "additionalProperties": False,
    }


__all__ = [
    "MAX_WAIT_SECONDS",
    "build_simulation_catalogue",
    "result_payload",
    "snapshot_payload",
]
