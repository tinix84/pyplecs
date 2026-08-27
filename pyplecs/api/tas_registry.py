"""Process-local tracking for submitted TAS studies."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

from pyplecs.orchestration import SimulationOrchestrator
from pyplecs.tas import TasCapture, TasExecutionEnvelope, TasExecutionService


@dataclass
class _StudyRecord:
    study_id: str
    names: tuple[str, ...]
    status: str = "queued"
    point_statuses: dict[str, str] = field(default_factory=dict)
    envelope: TasExecutionEnvelope | None = None
    error: str | None = None
    task: asyncio.Task[None] | None = None


class ProcessTasStudyRegistry:
    """Own ephemeral study IDs and public Operating-Point progress."""

    def __init__(
        self,
        artifact_directory: str | Path,
        serializer: Callable[[TasExecutionEnvelope], dict[str, Any]],
    ):
        self._artifact_directory = artifact_directory
        self._serializer = serializer
        self._records: dict[str, _StudyRecord] = {}

    def submit(
        self,
        document: dict[str, Any],
        captures: Sequence[TasCapture],
        orchestrator: SimulationOrchestrator,
        *,
        use_cache: bool,
    ) -> dict[str, Any]:
        """Preflight, issue an ID, and schedule the shared TAS service."""
        service = TasExecutionService(
            orchestrator, artifact_directory=self._artifact_directory
        )
        compilation = service.prepare(document, captures=captures)
        orchestrator.ensure_plecs_available()

        study_id = str(uuid.uuid4())
        names = tuple(point.name for point in compilation.operating_points)
        record = _StudyRecord(
            study_id=study_id,
            names=names,
            point_statuses={name: "pending" for name in names},
        )
        self._records[study_id] = record
        record.task = asyncio.create_task(
            self._execute(record, service, compilation, use_cache=use_cache),
            name=f"pyplecs-tas-study-{study_id}",
        )
        return self._serialize_record(record)

    def get(self, study_id: str) -> dict[str, Any] | None:
        record = self._records.get(study_id)
        return self._serialize_record(record) if record is not None else None

    async def _execute(
        self,
        record: _StudyRecord,
        service: TasExecutionService,
        compilation,
        *,
        use_cache: bool,
    ) -> None:
        record.status = "running"

        def point_terminal(point) -> None:
            record.point_statuses[point.name] = point.status.value

        try:
            envelope = await service.execute_prepared(
                compilation,
                use_cache=use_cache,
                on_point_terminal=point_terminal,
            )
        except Exception as error:
            record.status = "failed"
            record.error = str(error)
            return
        record.envelope = envelope
        record.status = envelope.status.value

    def _serialize_record(self, record: _StudyRecord) -> dict[str, Any]:
        completed = sum(status != "pending" for status in record.point_statuses.values())
        progress = {"completed": completed, "total": len(record.names)}
        if record.envelope is not None:
            return {
                "study_id": record.study_id,
                **self._serializer(record.envelope),
                "progress": progress,
            }
        return {
            "study_id": record.study_id,
            "status": record.status,
            "progress": progress,
            "points": [
                {"name": name, "status": record.point_statuses[name]}
                for name in record.names
            ],
            "error": record.error,
        }


__all__ = ["ProcessTasStudyRegistry"]
