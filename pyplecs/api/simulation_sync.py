"""Synchronous simulation endpoint for pyplecs.

Provides a blocking POST endpoint that runs a single PLECS simulation
and returns results directly (no task queue / polling).
"""

import logging
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..pyplecs import PlecsServer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sync"])


class SyncSimulationRequest(BaseModel):
    """Request model for synchronous simulation."""

    model_file: str
    parameters: dict[str, float] = {}
    signal_map: dict[int, str] | None = None


class SyncSimulationResponse(BaseModel):
    """Response model for synchronous simulation."""

    success: bool
    time: list[float]
    signals: dict[str, list[float]]
    metadata: dict = {}
    error_message: str | None = None


@router.post("/simulations/sync", response_model=SyncSimulationResponse)
async def run_simulation_sync(request: SyncSimulationRequest):
    """Run a PLECS simulation synchronously and return results.

    This endpoint blocks until the simulation completes. Use for
    single-shot validation runs where polling overhead is undesirable.
    """
    t_start = time.perf_counter()

    try:
        with PlecsServer(model_file=request.model_file) as server:
            raw = server.simulate(parameters=request.parameters or None)
    except Exception as e:
        logger.error("PLECS simulation failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e

    elapsed = time.perf_counter() - t_start

    # Parse PLECS result: {'Time': [...], 'Values': [[...], ...]}
    try:
        time_vec = _to_list(raw.get("Time", []))
        raw_values = raw.get("Values", [])

        signals: dict[str, list[float]] = {}
        signal_map = request.signal_map or {}

        for col_idx, col_data in enumerate(raw_values):
            name = signal_map.get(col_idx, f"col_{col_idx}")
            signals[name] = _to_list(col_data)

    except Exception as e:
        logger.error("Failed to parse PLECS result: %s", e)
        return SyncSimulationResponse(
            success=False,
            time=[],
            signals={},
            error_message=f"Result parsing error: {e}",
        )

    return SyncSimulationResponse(
        success=True,
        time=time_vec,
        signals=signals,
        metadata={
            "execution_time": round(elapsed, 4),
            "n_points": len(time_vec),
            "n_signals": len(signals),
            "model_file": request.model_file,
        },
    )


def _to_list(obj) -> list[float]:
    """Convert array-like or nested xmlrpc result to plain list of floats."""
    if hasattr(obj, "tolist"):
        return obj.tolist()
    if isinstance(obj, (list, tuple)):
        return [float(v) for v in obj]
    return list(obj)
