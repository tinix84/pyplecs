"""Thin REST transport for TAS execution services."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from pyplecs.core.models import SimulationResult
from pyplecs.orchestration import PlecsUnavailableError, SimulationOrchestrator
from pyplecs.tas import (
    TasCapture,
    TasCompilationError,
    TasDiagnostic,
    TasExecutionEnvelope,
    TasExecutionService,
)

from .tas_registry import ProcessTasStudyRegistry


class TasCaptureAPI(BaseModel):
    """Transport-only capture request kept outside the TAS document."""

    name: str
    kind: str
    target: str
    signal: str


class TasStudySyncRequest(BaseModel):
    """Synchronous TAS study request."""

    tas: dict[str, Any]
    captures: list[TasCaptureAPI] = Field(default_factory=list)
    timeout: float | None = Field(default=None, gt=0)
    use_cache: bool = True


class TasStudyRequest(BaseModel):
    """Asynchronous TAS study submission."""

    tas: dict[str, Any]
    captures: list[TasCaptureAPI] = Field(default_factory=list)
    use_cache: bool = True


def create_tas_router(
    orchestrator_dependency: Callable[[], SimulationOrchestrator],
    *,
    artifact_directory: str | Path,
) -> APIRouter:
    """Build TAS routes without importing API globals into the service layer."""
    router = APIRouter(prefix="/tas/studies", tags=["tas"])
    registry = ProcessTasStudyRegistry(artifact_directory, serialize_tas_envelope)

    @router.post("/sync")
    async def execute_tas_sync(
        request: TasStudySyncRequest,
        orchestrator: SimulationOrchestrator = Depends(orchestrator_dependency),
    ) -> dict[str, Any]:
        service = TasExecutionService(
            orchestrator, artifact_directory=artifact_directory
        )
        captures = transport_captures(request.captures)
        try:
            operation = service.execute(
                request.tas,
                captures=captures,
                use_cache=request.use_cache,
            )
            envelope = await asyncio.wait_for(operation, timeout=request.timeout)
        except TasCompilationError as error:
            raise HTTPException(
                status_code=422,
                detail=[serialize_diagnostic(diagnostic) for diagnostic in error.diagnostics],
            ) from error
        except PlecsUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except asyncio.TimeoutError as error:
            raise HTTPException(status_code=504, detail="TAS study timed out") from error
        return serialize_tas_envelope(envelope)

    @router.post("", status_code=202)
    async def submit_tas_study(
        request: TasStudyRequest,
        orchestrator: SimulationOrchestrator = Depends(orchestrator_dependency),
    ) -> dict[str, Any]:
        try:
            return registry.submit(
                request.tas,
                transport_captures(request.captures),
                orchestrator,
                use_cache=request.use_cache,
            )
        except TasCompilationError as error:
            raise HTTPException(
                status_code=422,
                detail=[serialize_diagnostic(diagnostic) for diagnostic in error.diagnostics],
            ) from error
        except PlecsUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @router.get("/{study_id}")
    async def get_tas_study(study_id: str) -> dict[str, Any]:
        study = registry.get(study_id)
        if study is None:
            raise HTTPException(status_code=404, detail="TAS study not found")
        return study

    return router


def transport_captures(captures: list[TasCaptureAPI]) -> list[TasCapture]:
    return [
        TasCapture(capture.name, capture.kind, capture.target, capture.signal)
        for capture in captures
    ]


def serialize_tas_envelope(envelope: TasExecutionEnvelope) -> dict[str, Any]:
    """Serialize public TAS execution truth without task internals."""
    return {
        "tas": envelope.source,
        "status": envelope.status.value,
        "points": [
            {
                "name": point.name,
                "parameters": dict(point.parameters),
                "task_id": point.task_id,
                "status": point.status.value,
                "result": serialize_simulation_result(point.result),
                "error": point.error,
            }
            for point in envelope.points
        ],
        "aggregate": serialize_value(envelope.aggregate),
        "diagnostics": [
            serialize_diagnostic(diagnostic) for diagnostic in envelope.diagnostics
        ],
    }


def serialize_simulation_result(result: SimulationResult | None) -> dict[str, Any] | None:
    """Serialize normalized time-series data in stable column order."""
    if result is None:
        return None
    timeseries = result.timeseries_data
    time_values = (
        timeseries["Time"].tolist()
        if timeseries is not None and "Time" in timeseries
        else []
    )
    signals = (
        {
            column: timeseries[column].tolist()
            for column in timeseries.columns
            if column != "Time"
        }
        if timeseries is not None
        else {}
    )
    return {
        "task_id": result.task_id,
        "success": result.success,
        "time": time_values,
        "signals": signals,
        "metadata": serialize_value(result.metadata),
        "error_message": result.error_message,
        "execution_time": result.execution_time,
        "cached": result.cached,
        "plecs_version": result.plecs_version,
    }


def serialize_diagnostic(diagnostic: TasDiagnostic) -> dict[str, str]:
    return {
        "code": diagnostic.code,
        "location": diagnostic.location,
        "severity": diagnostic.severity.value,
        "message": diagnostic.message,
    }


def serialize_value(value: Any) -> Any:
    if isinstance(value, SimulationResult):
        return serialize_simulation_result(value)
    if isinstance(value, dict):
        return {str(key): serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_value(item) for item in value]
    return value


__all__ = [
    "TasCaptureAPI",
    "TasStudyRequest",
    "TasStudySyncRequest",
    "create_tas_router",
    "serialize_tas_envelope",
]
