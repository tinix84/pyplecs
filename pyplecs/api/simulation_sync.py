"""Synchronous simulation endpoint for pyplecs.

Provides a blocking POST endpoint that runs a single PLECS simulation
and returns results directly (no task queue / polling).
"""

import logging
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..normalization import normalize_plecs_result, simulation_result_payload
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
async def run_simulation_sync(request: SyncSimulationRequest, http_request: Request):
    """Run a PLECS simulation synchronously and return results.

    This endpoint blocks until the simulation completes. Use for
    single-shot validation runs where polling overhead is undesirable.
    """
    t_start = time.perf_counter()
    plecs_config = getattr(getattr(http_request.app.state, "config", None), "plecs", None)
    server_options = (
        {"port": str(plecs_config.xmlrpc_port), "auto_launch": plecs_config.auto_launch}
        if plecs_config is not None
        else {}
    )

    try:
        with PlecsServer(model_file=request.model_file, **server_options) as server:
            raw = server.simulate(parameters=request.parameters or None)
    except Exception as e:
        logger.error("PLECS simulation failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e

    elapsed = time.perf_counter() - t_start

    result = normalize_plecs_result(
        raw,
        task_id="sync",
        signal_names=request.signal_map,
        metadata={"model_file": request.model_file},
        execution_time=elapsed,
    )
    if not result.success:
        logger.error("Failed to normalize PLECS result: %s", result.error_message)
        return SyncSimulationResponse(
            success=False,
            time=[],
            signals={},
            metadata=result.metadata,
            error_message=result.error_message,
        )

    return SyncSimulationResponse(
        success=True,
        **simulation_result_payload(result),
        metadata={**result.metadata, "execution_time": round(elapsed, 4)},
    )
