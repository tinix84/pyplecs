"""Simulation Task lifecycle orchestration."""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field, replace
from queue import Empty, Full, PriorityQueue
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence, runtime_checkable

from pyplecs.contracts import SimulationOrchestratorBase, TaskPriority

from ..cache import SimulationCache
from ..config import ConfigManager, get_config
from ..core.models import SimulationRequest, SimulationResult, SimulationStatus
from ..normalization import normalize_plecs_result

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = frozenset(
    {
        SimulationStatus.COMPLETED,
        SimulationStatus.FAILED,
        SimulationStatus.CANCELLED,
    }
)


class PlecsUnavailableError(RuntimeError):
    """Raised when a Simulation Task cannot be accepted without PLECS."""


@runtime_checkable
class PlecsSimulationPort(Protocol):
    """The PLECS seam used by orchestration and in-memory test adapters."""

    def is_available(self) -> bool:
        """Return whether this adapter can execute a Simulation Task now."""

    def simulate_batch(self, parameter_list: Sequence[Dict[str, Any]]) -> Sequence[Any]:
        """Execute one batch and return one Raw PLECS Result per parameter vector."""


class _CallablePlecsAdapter:
    """Compatibility adapter for the historical per-request runner hook."""

    def __init__(self, runner: Callable[[SimulationRequest], SimulationResult]):
        self._runner = runner

    @staticmethod
    def is_available() -> bool:
        return True

    def simulate_batch(self, parameter_list: Sequence[Dict[str, Any]]) -> Sequence[Any]:
        raise RuntimeError("Callable adapter requires complete Simulation Requests")

    def simulate_requests(
        self, requests: Sequence[SimulationRequest]
    ) -> Sequence[SimulationResult]:
        return [self._runner(request) for request in requests]


@dataclass
class _SimulationTask:
    request: SimulationRequest
    priority: TaskPriority = TaskPriority.NORMAL
    use_cache: bool = True
    max_retries: int = 3
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: SimulationStatus = SimulationStatus.QUEUED
    result: Optional[SimulationResult] = None
    error: Optional[str] = None
    retry_count: int = 0

    def __lt__(self, other: "_SimulationTask") -> bool:
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


@dataclass(frozen=True)
class SimulationTaskSnapshot:
    """Immutable query view of one accepted Simulation Task."""

    id: str
    model_file: str
    priority: TaskPriority
    created_at: float
    started_at: Optional[float]
    completed_at: Optional[float]
    status: SimulationStatus
    result: Optional[SimulationResult]
    error: Optional[str]
    retry_count: int


class SimulationOrchestrator(SimulationOrchestratorBase):
    """Own acceptance, scheduling, retries, caching, and terminal truth."""

    def __init__(
        self,
        plecs_server: Optional[PlecsSimulationPort] = None,
        batch_size: Optional[int] = None,
        *,
        config: Optional[ConfigManager] = None,
        cache: Optional[SimulationCache] = None,
    ):
        self.config = config or get_config()
        self._cache = cache or SimulationCache(self.config.cache)
        self._plecs: Optional[PlecsSimulationPort] = plecs_server
        self.batch_size = (
            batch_size or self.config.orchestration.max_concurrent_simulations
        )

        self._task_queue: PriorityQueue[_SimulationTask] = PriorityQueue(
            maxsize=self.config.orchestration.queue_size
        )
        self._tasks: Dict[str, _SimulationTask] = {}
        self._accepted_task_ids: set[str] = set()
        self._state_changed = asyncio.Event()

        self.is_running = False
        self._orchestrator_task: Optional[asyncio.Task[None]] = None
        self._batch_tasks: set[asyncio.Task[None]] = set()

        self._batches_executed = 0
        self._simulations_executed = 0
        self._total_runtime = 0.0
        self._cache_hits = 0

        self._callbacks: Dict[str, List[Callable[..., Any]]] = {
            "on_task_started": [],
            "on_task_completed": [],
            "on_task_failed": [],
            "on_task_cancelled": [],
            "on_queue_empty": [],
            "on_batch_started": [],
            "on_batch_completed": [],
        }

    def set_plecs_server(self, plecs_server: PlecsSimulationPort) -> None:
        """Set or replace the production PLECS adapter."""
        self._plecs = plecs_server

    def ensure_plecs_available(self) -> None:
        """Fail before acceptance when the configured PLECS collaborator is unavailable."""
        self._require_available_plecs()

    def register_simulation_runner(
        self, runner: Callable[[SimulationRequest], SimulationResult]
    ) -> None:
        """Adapt the legacy per-request runner API to the PLECS collaborator seam."""
        self._plecs = _CallablePlecsAdapter(runner)

    def add_callback(self, event: str, callback: Callable[..., Any]) -> None:
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def remove_callback(self, event: str, callback: Callable[..., Any]) -> None:
        callbacks = self._callbacks.get(event, [])
        if callback in callbacks:
            callbacks.remove(callback)

    async def submit_simulation(
        self,
        request: SimulationRequest,
        priority: TaskPriority = TaskPriority.NORMAL,
        use_cache: bool = True,
    ) -> str:
        """Accept one Simulation Task only when PLECS is available."""
        self._require_available_plecs()
        if self._task_queue.full():
            raise RuntimeError("Simulation Task queue is full")

        task = _SimulationTask(
            request=request,
            priority=priority,
            use_cache=use_cache,
            max_retries=self.config.orchestration.retry_attempts,
        )
        self._tasks[task.id] = task
        self._accepted_task_ids.add(task.id)
        self._notify_state_change()

        cached_result = self._read_cache(task)
        if cached_result is not None:
            self._complete_success(task, self._cached_simulation_result(task, cached_result))
            return task.id

        self._task_queue.put_nowait(task)
        self._notify_state_change()
        logger.info("Simulation Task %s queued with priority %s", task.id, priority.name)

        if not self.is_running:
            await self.start()
        return task.id

    async def get_task_status(
        self, task_id: str
    ) -> Optional[SimulationTaskSnapshot]:
        task = self._tasks.get(task_id)
        return self._snapshot(task) if task is not None else None

    def list_tasks(
        self,
        status: Optional[SimulationStatus] = None,
        limit: int = 100,
    ) -> List[SimulationTaskSnapshot]:
        """Query Simulation Tasks without exposing lifecycle collections."""
        tasks = self._tasks.values()
        if status is not None:
            tasks = (task for task in tasks if task.status == status)
        ordered = sorted(tasks, key=lambda task: task.created_at, reverse=True)
        return [self._snapshot(task) for task in ordered[:limit]]

    async def cancel_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None or task.status in TERMINAL_STATUSES:
            return False
        if task.status not in {SimulationStatus.QUEUED, SimulationStatus.RUNNING}:
            return False

        result = SimulationResult(
            task_id=task.id,
            success=False,
            metadata={"model_file": task.request.model_file},
            error_message="Simulation Task cancelled",
        )
        self._finish_terminal(
            task,
            SimulationStatus.CANCELLED,
            result,
            "Simulation Task cancelled",
            "on_task_cancelled",
        )
        return True

    async def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self._orchestrator_task = asyncio.create_task(
            self._orchestrator_loop(), name="pyplecs-orchestrator"
        )
        logger.info("Simulation orchestrator started")

    async def stop(self) -> None:
        self.is_running = False
        if self._orchestrator_task is not None:
            self._orchestrator_task.cancel()
            try:
                await self._orchestrator_task
            except asyncio.CancelledError:
                pass
            self._orchestrator_task = None

        pending_batches = list(self._batch_tasks)
        if pending_batches:
            await asyncio.gather(*pending_batches, return_exceptions=True)
        logger.info("Simulation orchestrator stopped")

    async def wait_for_completion(
        self, task_id: str, timeout: Optional[float] = None
    ) -> Optional[SimulationTaskSnapshot]:
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            state_changed = self._state_changed
            task = self._tasks.get(task_id)
            if task is None:
                return None
            if task.status in TERMINAL_STATUSES:
                return self._snapshot(task)
            if not await self._wait_for_state_change(state_changed, deadline):
                return None

    async def wait_for_all_tasks(self, timeout: Optional[float] = None) -> bool:
        """Return true only when every accepted Simulation Task is terminal."""
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            state_changed = self._state_changed
            if all(
                self._tasks[task_id].status in TERMINAL_STATUSES
                for task_id in self._accepted_task_ids
            ):
                return True
            if not await self._wait_for_state_change(state_changed, deadline):
                return False

    def get_orchestrator_stats(self) -> Dict[str, Any]:
        status_counts = {
            status: sum(task.status == status for task in self._tasks.values())
            for status in SimulationStatus
        }
        return {
            "total_submitted": len(self._accepted_task_ids),
            "total_completed": status_counts[SimulationStatus.COMPLETED],
            "total_failed": status_counts[SimulationStatus.FAILED],
            "total_cancelled": status_counts[SimulationStatus.CANCELLED],
            "total_cached_hits": self._cache_hits,
            "total_batches": self._batches_executed,
            "queue_size": sum(
                task.status == SimulationStatus.QUEUED for task in self._tasks.values()
            ),
            "active_tasks": status_counts[SimulationStatus.RUNNING],
            "executor": {
                "batch_size": self.batch_size,
                "batches_executed": self._batches_executed,
                "total_simulations": self._simulations_executed,
                "total_runtime": self._total_runtime,
                "is_processing": bool(self._batch_tasks),
            },
            "cache_stats": self._cache.get_cache_stats(),
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Query cache state without exposing cache implementation."""
        return self._cache.get_cache_stats()

    def clear_cache(self) -> None:
        """Clear cache state without exposing cache implementation."""
        self._cache.clear_cache()

    def _require_available_plecs(self) -> None:
        if self._plecs is None:
            raise PlecsUnavailableError(
                "Cannot accept Simulation Task: no PLECS adapter is configured"
            )
        try:
            available = self._plecs.is_available()
        except Exception as error:
            raise PlecsUnavailableError(
                f"Cannot accept Simulation Task: PLECS availability check failed: {error}"
            ) from error
        if not available:
            raise PlecsUnavailableError(
                "Cannot accept Simulation Task: PLECS adapter is unavailable"
            )

    async def _orchestrator_loop(self) -> None:
        try:
            while self.is_running:
                batch = self._dequeue_batch()
                if not batch:
                    self._trigger_callbacks("on_queue_empty")
                    await asyncio.sleep(0.01)
                    continue

                batch_task = asyncio.create_task(
                    self._execute_batch(batch), name="pyplecs-simulation-batch"
                )
                self._track_batch(batch_task)
                await asyncio.shield(batch_task)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Unexpected orchestrator loop failure")

    def _dequeue_batch(self) -> List[_SimulationTask]:
        batch: List[_SimulationTask] = []
        while len(batch) < self.batch_size:
            try:
                task = self._task_queue.get_nowait()
            except Empty:
                break
            if task.status == SimulationStatus.QUEUED:
                batch.append(task)
        return batch

    def _track_batch(self, batch_task: asyncio.Task[None]) -> None:
        self._batch_tasks.add(batch_task)

        def observe(completed: asyncio.Task[None]) -> None:
            self._batch_tasks.discard(completed)
            if completed.cancelled():
                return
            error = completed.exception()
            if error is not None:
                logger.error(
                    "Observed simulation batch failure",
                    exc_info=(type(error), error, error.__traceback__),
                )

        batch_task.add_done_callback(observe)

    async def _execute_batch(self, tasks: List[_SimulationTask]) -> None:
        executable: List[_SimulationTask] = []
        for task in tasks:
            if task.status != SimulationStatus.QUEUED:
                continue
            cached_result = self._read_cache(task)
            if cached_result is not None:
                self._complete_success(
                    task, self._cached_simulation_result(task, cached_result)
                )
                continue
            task.status = SimulationStatus.RUNNING
            task.started_at = task.started_at or time.time()
            executable.append(task)
            self._notify_state_change()
            self._trigger_callbacks("on_task_started", self._snapshot(task))

        if not executable:
            return

        self._trigger_callbacks(
            "on_batch_started", [self._snapshot(task) for task in executable]
        )
        started = time.perf_counter()
        try:
            if self._plecs is None:
                raise PlecsUnavailableError("PLECS adapter was removed after submission")
            if isinstance(self._plecs, _CallablePlecsAdapter):
                raw_results = await asyncio.to_thread(
                    self._plecs.simulate_requests,
                    [task.request for task in executable],
                )
            else:
                raw_results = await asyncio.to_thread(
                    self._plecs.simulate_batch,
                    [task.request.parameters for task in executable],
                )
            if not isinstance(raw_results, Sequence) or len(raw_results) != len(executable):
                raise ValueError(
                    "PLECS batch returned a different number of Raw PLECS Results"
                )

            self._batches_executed += 1
            self._simulations_executed += len(executable)
            self._total_runtime += time.perf_counter() - started
            normalized_results = []
            for task, raw_result in zip(executable, raw_results):
                if task.status == SimulationStatus.CANCELLED:
                    continue
                if isinstance(raw_result, SimulationResult):
                    result = replace(
                        raw_result,
                        task_id=task.id,
                        metadata={
                            **task.request.metadata,
                            "model_file": task.request.model_file,
                            **raw_result.metadata,
                        },
                    )
                else:
                    result = normalize_plecs_result(
                        raw_result,
                        task_id=task.id,
                        signal_names=task.request.output_variables,
                        metadata={
                            **task.request.metadata,
                            "model_file": task.request.model_file,
                        },
                    )
                normalized_results.append(result)
                if result.success:
                    self._complete_success(task, result)
                else:
                    await self._handle_failure(task, result.error_message or "Unknown failure")

            self._trigger_callbacks(
                "on_batch_completed",
                [self._snapshot(task) for task in executable],
                normalized_results,
            )
        except Exception as error:
            self._batches_executed += 1
            self._simulations_executed += len(executable)
            self._total_runtime += time.perf_counter() - started
            logger.error("Simulation batch failed: %s", error)
            for task in executable:
                if task.status not in TERMINAL_STATUSES:
                    await self._handle_failure(task, str(error))

    async def _handle_failure(self, task: _SimulationTask, error_message: str) -> None:
        if task.status in TERMINAL_STATUSES:
            return
        task.error = error_message
        task.retry_count += 1
        if task.retry_count < task.max_retries:
            task.status = SimulationStatus.QUEUED
            self._notify_state_change()
            if self.config.orchestration.retry_delay:
                await asyncio.sleep(self.config.orchestration.retry_delay)
            if task.status == SimulationStatus.QUEUED:
                try:
                    self._task_queue.put_nowait(task)
                except Full:
                    retry_error = f"{error_message}; retry queue is full"
                    result = SimulationResult(
                        task_id=task.id,
                        success=False,
                        metadata={
                            **task.request.metadata,
                            "model_file": task.request.model_file,
                        },
                        error_message=retry_error,
                    )
                    self._finish_terminal(
                        task,
                        SimulationStatus.FAILED,
                        result,
                        retry_error,
                        "on_task_failed",
                    )
                else:
                    self._notify_state_change()
            return

        result = SimulationResult(
            task_id=task.id,
            success=False,
            metadata={**task.request.metadata, "model_file": task.request.model_file},
            error_message=error_message,
        )
        self._finish_terminal(
            task,
            SimulationStatus.FAILED,
            result,
            error_message,
            "on_task_failed",
        )

    def _complete_success(
        self, task: _SimulationTask, result: SimulationResult
    ) -> None:
        if task.status in TERMINAL_STATUSES:
            return
        if task.use_cache and self._cache.config.enabled and not result.cached:
            try:
                self._cache.cache_result(
                    task.request.model_file,
                    task.request.parameters,
                    result.timeseries_data,
                    result.metadata,
                )
            except Exception:
                logger.exception("Failed to cache Simulation Result for task %s", task.id)
        self._finish_terminal(
            task,
            SimulationStatus.COMPLETED,
            result,
            None,
            "on_task_completed",
        )

    def _finish_terminal(
        self,
        task: _SimulationTask,
        status: SimulationStatus,
        result: SimulationResult,
        error: Optional[str],
        callback_event: str,
    ) -> None:
        task.status = status
        task.result = result
        task.error = error
        task.completed_at = time.time()
        self._notify_state_change()
        self._trigger_callbacks(callback_event, self._snapshot(task))

    def _read_cache(self, task: _SimulationTask) -> Optional[Dict[str, Any]]:
        if not task.use_cache or not self._cache.config.enabled:
            return None
        return self._cache.get_cached_result(
            task.request.model_file, task.request.parameters
        )

    def _cached_simulation_result(
        self, task: _SimulationTask, cached_result: Dict[str, Any]
    ) -> SimulationResult:
        self._cache_hits += 1
        return SimulationResult(
            task_id=task.id,
            success=True,
            timeseries_data=cached_result["timeseries"],
            metadata=cached_result["metadata"],
            cached=True,
        )

    def _trigger_callbacks(self, event: str, *args: Any) -> None:
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args)
            except Exception:
                logger.exception("Callback failed for %s", event)

    def _notify_state_change(self) -> None:
        state_changed = self._state_changed
        self._state_changed = asyncio.Event()
        state_changed.set()

    async def _wait_for_state_change(
        self,
        state_changed: asyncio.Event,
        deadline: Optional[float],
    ) -> bool:
        if deadline is None:
            await state_changed.wait()
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        try:
            await asyncio.wait_for(state_changed.wait(), timeout=remaining)
            return True
        except asyncio.TimeoutError:
            return False

    @staticmethod
    def _snapshot(task: _SimulationTask) -> SimulationTaskSnapshot:
        return SimulationTaskSnapshot(
            id=task.id,
            model_file=task.request.model_file,
            priority=task.priority,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            status=task.status,
            result=task.result,
            error=task.error,
            retry_count=task.retry_count,
        )


__all__ = [
    "PlecsSimulationPort",
    "PlecsUnavailableError",
    "SimulationOrchestrator",
    "SimulationTaskSnapshot",
    "TaskPriority",
]
