"""REST transport for Design Quantities of a completed Simulation Task."""

from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from pyplecs.core.models import SimulationStatus
from pyplecs.orchestration import SimulationOrchestrator
from pyplecs.quantities import QuantityError, design_quantities_payload


class QuantitiesRequest(BaseModel):
    """Signal Map plus optional window and waveform names; roles are never inferred."""

    signal_map: dict[str, Any] = Field(default_factory=dict)
    window: Optional[dict[str, Any]] = None
    waveforms: list[str] = Field(default_factory=list)


def create_quantities_router(
    orchestrator_dependency: Callable[[], SimulationOrchestrator],
) -> APIRouter:
    router = APIRouter(prefix="/simulations", tags=["quantities"])

    @router.post("/{task_id}/quantities")
    async def simulation_quantities(
        task_id: str,
        request: QuantitiesRequest,
        orchestrator: SimulationOrchestrator = Depends(orchestrator_dependency),
    ) -> dict[str, Any]:
        snapshot = await orchestrator.get_task_status(task_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Task not found")
        if snapshot.status != SimulationStatus.COMPLETED or snapshot.result is None:
            raise HTTPException(
                status_code=400,
                detail=f"Task not completed. Current status: {snapshot.status.value}",
            )
        try:
            return design_quantities_payload(
                snapshot.result,
                signal_map=request.signal_map,
                window=request.window,
                waveforms=request.waveforms,
            )
        except QuantityError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    return router


__all__ = ["QuantitiesRequest", "create_quantities_router"]
