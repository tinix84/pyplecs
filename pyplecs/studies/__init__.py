"""Finite Parametric Studies built from ordinary Simulation Tasks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence, runtime_checkable

from pyplecs.contracts import TaskPriority
from pyplecs.core.models import SimulationRequest, SimulationResult, SimulationStatus
from pyplecs.orchestration import SimulationOrchestrator


class ParametricStudyStatus(str, Enum):
    """Truthful terminal status for a finite Parametric Study."""

    COMPLETED = "completed"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"


@dataclass(frozen=True)
class ParameterVector:
    """One uniquely named set of ModelVars for a Parametric Study point."""

    name: str
    parameters: Mapping[str, Any]


@runtime_checkable
class ParameterVectorStrategy(Protocol):
    """Produce one finite, ordered sequence of named parameter vectors."""

    def generate(self) -> Sequence[ParameterVector]:
        """Return all parameter vectors before task submission begins."""


class ExplicitParameterVectorStrategy:
    """Return a caller-supplied finite sequence without optimizer behavior."""

    def __init__(self, vectors: Sequence[ParameterVector]):
        self._vectors = tuple(vectors)

    def generate(self) -> Sequence[ParameterVector]:
        return self._vectors


@dataclass(frozen=True)
class ParametricPointOutcome:
    """Terminal truth for one requested Parametric Study point."""

    name: str
    parameters: Mapping[str, Any]
    task_id: str
    status: SimulationStatus
    result: SimulationResult | None
    error: str | None


@runtime_checkable
class ResultReducer(Protocol):
    """Reduce only successful point outcomes into a caller-defined aggregate."""

    def reduce(self, successful_points: Sequence[ParametricPointOutcome]) -> Any:
        """Return an aggregate derived from successful points."""


class CollectResultsReducer:
    """Collect successful Simulation Results in requested point order."""

    def reduce(
        self, successful_points: Sequence[ParametricPointOutcome]
    ) -> tuple[SimulationResult, ...]:
        return tuple(
            point.result for point in successful_points if point.result is not None
        )


@dataclass(frozen=True)
class ParametricStudyOutcome:
    """Ordered point outcomes and their reduction."""

    status: ParametricStudyStatus
    points: tuple[ParametricPointOutcome, ...]
    aggregate: Any


class ParametricStudy:
    """Expand finite vectors through the existing Simulation Task lifecycle."""

    def __init__(self, orchestrator: SimulationOrchestrator):
        self._orchestrator = orchestrator

    async def run(
        self,
        model_file: str | Path,
        strategy: ParameterVectorStrategy,
        *,
        reducer: ResultReducer | None = None,
        output_variables: Sequence[str] = (),
        metadata: Mapping[str, Any] | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        use_cache: bool = True,
        on_point_terminal: Callable[[ParametricPointOutcome], None] | None = None,
    ) -> ParametricStudyOutcome:
        """Execute all points and return one ordered, truthful outcome."""
        vectors = tuple(strategy.generate())
        self._validate_vectors(vectors)

        # Construct every request first so local setup errors cannot leave a
        # partially accepted study behind.
        requests = tuple(
            SimulationRequest(
                model_file=str(model_file),
                parameters=dict(vector.parameters),
                output_variables=list(output_variables),
                metadata={**dict(metadata or {}), "parametric_point": vector.name},
            )
            for vector in vectors
        )

        task_ids = []
        for request in requests:
            task_ids.append(
                await self._orchestrator.submit_simulation(
                    request, priority=priority, use_cache=use_cache
                )
            )

        points_list = []
        for vector, task_id in zip(vectors, task_ids):
            snapshot = await self._orchestrator.wait_for_completion(task_id)
            if snapshot is None:
                raise RuntimeError("An accepted Simulation Task disappeared")
            point = ParametricPointOutcome(
                name=vector.name,
                parameters=dict(vector.parameters),
                task_id=task_id,
                status=snapshot.status,
                result=snapshot.result,
                error=snapshot.error,
            )
            points_list.append(point)
            if on_point_terminal is not None:
                on_point_terminal(point)
        points = tuple(points_list)
        successful = tuple(
            point
            for point in points
            if point.status == SimulationStatus.COMPLETED
            and point.result is not None
            and point.result.success
        )
        aggregate = (reducer or CollectResultsReducer()).reduce(successful)
        return ParametricStudyOutcome(
            status=self._status(len(successful), len(points)),
            points=points,
            aggregate=aggregate,
        )

    @staticmethod
    def _validate_vectors(vectors: Sequence[ParameterVector]) -> None:
        if not vectors:
            raise ValueError("A Parametric Study requires at least one parameter vector")
        names = [vector.name for vector in vectors]
        if any(not isinstance(name, str) or not name.strip() for name in names):
            raise ValueError("Every parameter vector requires a non-empty name")
        if len(names) != len(set(names)):
            raise ValueError("Parameter vector names must be unique")
        if any(not isinstance(vector.parameters, Mapping) for vector in vectors):
            raise ValueError("Parameter vector values must be mappings")

    @staticmethod
    def _status(successes: int, total: int) -> ParametricStudyStatus:
        if successes == total:
            return ParametricStudyStatus.COMPLETED
        if successes == 0:
            return ParametricStudyStatus.FAILED
        return ParametricStudyStatus.PARTIAL_FAILURE


__all__ = [
    "CollectResultsReducer",
    "ExplicitParameterVectorStrategy",
    "ParameterVector",
    "ParameterVectorStrategy",
    "ParametricPointOutcome",
    "ParametricStudy",
    "ParametricStudyOutcome",
    "ParametricStudyStatus",
    "ResultReducer",
]
