import asyncio
import threading
from dataclasses import FrozenInstanceError

import pytest

from pyplecs.cache import SimulationCache
from pyplecs.config import ConfigManager
from pyplecs.core.models import SimulationRequest, SimulationStatus
from pyplecs.orchestration import (
    PlecsUnavailableError,
    SimulationOrchestrator,
    TaskPriority,
)


class InMemoryPlecsAdapter:
    def __init__(self, outcomes=None, *, available=True):
        self.available = available
        self.outcomes = list(outcomes or [])
        self.calls = []

    def is_available(self):
        return self.available

    def simulate_batch(self, parameter_list):
        copied_parameters = [dict(parameters) for parameters in parameter_list]
        self.calls.append(copied_parameters)
        if self.outcomes:
            outcome = self.outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            if callable(outcome):
                return outcome(copied_parameters)
            return outcome
        return [
            {
                "Time": [0.0, 1.0],
                "Values": [[parameters.get("Vi", 0.0), parameters.get("Vi", 0.0)]],
            }
            for parameters in copied_parameters
        ]


class BlockingPlecsAdapter(InMemoryPlecsAdapter):
    def __init__(self):
        super().__init__()
        self.started = threading.Event()
        self.release = threading.Event()

    def simulate_batch(self, parameter_list):
        self.started.set()
        if not self.release.wait(timeout=5):
            raise TimeoutError("test adapter was not released")
        return super().simulate_batch(parameter_list)


class BlockingFailingPlecsAdapter(InMemoryPlecsAdapter):
    def __init__(self):
        super().__init__()
        self.started = threading.Event()
        self.release = threading.Event()

    def simulate_batch(self, parameter_list):
        self.started.set()
        if not self.release.wait(timeout=5):
            raise TimeoutError("test adapter was not released")
        raise RuntimeError("transient")


def _config(tmp_path, *, retries=1, batch_size=4):
    config = ConfigManager(search_paths=[])
    config.update("cache.directory", str(tmp_path / "cache"))
    config.update("orchestration.retry_attempts", retries)
    config.update("orchestration.retry_delay", 0)
    config.update("orchestration.max_concurrent_simulations", batch_size)
    return config


def _request(tmp_path, vi=24.0):
    model = tmp_path / "model.plecs"
    model.touch(exist_ok=True)
    return SimulationRequest(
        model_file=str(model), parameters={"Vi": vi}, output_variables=["Vo"]
    )


@pytest.mark.asyncio
async def test_submission_requires_an_available_plecs_adapter(tmp_path):
    config = _config(tmp_path)
    missing = SimulationOrchestrator(config=config)
    unavailable = SimulationOrchestrator(
        InMemoryPlecsAdapter(available=False), config=config
    )

    with pytest.raises(PlecsUnavailableError, match="no PLECS adapter"):
        await missing.submit_simulation(_request(tmp_path))
    with pytest.raises(PlecsUnavailableError, match="unavailable"):
        await unavailable.submit_simulation(_request(tmp_path))

    assert missing.get_orchestrator_stats()["total_submitted"] == 0
    assert unavailable.get_orchestrator_stats()["total_submitted"] == 0


@pytest.mark.asyncio
async def test_priority_is_owned_by_the_orchestrator_interface(tmp_path):
    adapter = InMemoryPlecsAdapter()
    orchestrator = SimulationOrchestrator(
        adapter, batch_size=3, config=_config(tmp_path, batch_size=3)
    )
    try:
        await asyncio.gather(
            orchestrator.submit_simulation(
                _request(tmp_path, 1.0), priority=TaskPriority.LOW, use_cache=False
            ),
            orchestrator.submit_simulation(
                _request(tmp_path, 2.0), priority=TaskPriority.CRITICAL, use_cache=False
            ),
            orchestrator.submit_simulation(
                _request(tmp_path, 3.0), priority=TaskPriority.NORMAL, use_cache=False
            ),
        )

        assert await orchestrator.wait_for_all_tasks(timeout=2)
        assert [parameters["Vi"] for parameters in adapter.calls[0]] == [2.0, 3.0, 1.0]
    finally:
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_cache_hit_and_execution_share_terminal_completion(tmp_path):
    config = _config(tmp_path, batch_size=1)
    adapter = InMemoryPlecsAdapter()
    orchestrator = SimulationOrchestrator(adapter, batch_size=1, config=config)
    completions = []
    orchestrator.add_callback("on_task_completed", completions.append)
    try:
        first_id = await orchestrator.submit_simulation(_request(tmp_path, 24.0))
        first = await orchestrator.wait_for_completion(first_id, timeout=2)
        second_id = await orchestrator.submit_simulation(_request(tmp_path, 24.0))
        second = await orchestrator.wait_for_completion(second_id, timeout=2)

        assert first.status == SimulationStatus.COMPLETED
        assert first.result.cached is False
        assert second.status == SimulationStatus.COMPLETED
        assert second.result.cached is True
        assert len(adapter.calls) == 1
        assert [snapshot.status for snapshot in completions] == [
            SimulationStatus.COMPLETED,
            SimulationStatus.COMPLETED,
        ]
        stats = orchestrator.get_orchestrator_stats()
        assert stats["total_submitted"] == 2
        assert stats["total_completed"] == 2
        assert stats["total_cached_hits"] == 1
    finally:
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_failed_attempt_is_retried_then_completed(tmp_path):
    adapter = InMemoryPlecsAdapter(outcomes=[RuntimeError("transient")])
    orchestrator = SimulationOrchestrator(
        adapter, batch_size=1, config=_config(tmp_path, retries=2, batch_size=1)
    )
    try:
        task_id = await orchestrator.submit_simulation(
            _request(tmp_path), use_cache=False
        )

        task = await orchestrator.wait_for_completion(task_id, timeout=2)

        assert task.status == SimulationStatus.COMPLETED
        assert task.retry_count == 1
        assert len(adapter.calls) == 2
    finally:
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_retry_racing_with_a_full_queue_still_reaches_terminal_truth(tmp_path):
    config = _config(tmp_path, retries=2, batch_size=1)
    config.update("orchestration.queue_size", 1)
    adapter = BlockingFailingPlecsAdapter()
    orchestrator = SimulationOrchestrator(adapter, batch_size=1, config=config)
    try:
        first_id = await orchestrator.submit_simulation(
            _request(tmp_path, 1.0), use_cache=False
        )
        assert await asyncio.to_thread(adapter.started.wait, 1)
        await orchestrator.submit_simulation(_request(tmp_path, 2.0), use_cache=False)

        adapter.release.set()
        first = await orchestrator.wait_for_completion(first_id, timeout=2)

        assert first.status == SimulationStatus.FAILED
        assert "retry queue is full" in first.error
    finally:
        adapter.release.set()
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_running_task_can_be_cancelled_to_a_terminal_outcome(tmp_path):
    adapter = BlockingPlecsAdapter()
    orchestrator = SimulationOrchestrator(
        adapter, batch_size=1, config=_config(tmp_path, batch_size=1)
    )
    try:
        task_id = await orchestrator.submit_simulation(
            _request(tmp_path), use_cache=False
        )
        assert await asyncio.to_thread(adapter.started.wait, 1)

        assert await orchestrator.cancel_task(task_id) is True
        task = await orchestrator.wait_for_completion(task_id, timeout=1)

        assert task.status == SimulationStatus.CANCELLED
        assert task.result.success is False
        assert "cancelled" in task.result.error_message
        assert await orchestrator.cancel_task(task_id) is False
    finally:
        adapter.release.set()
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_batch_failure_gives_every_task_a_failed_terminal_outcome(tmp_path):
    adapter = InMemoryPlecsAdapter(outcomes=[RuntimeError("PLECS crashed")])
    orchestrator = SimulationOrchestrator(
        adapter, batch_size=2, config=_config(tmp_path, retries=1, batch_size=2)
    )
    try:
        task_ids = await asyncio.gather(
            orchestrator.submit_simulation(_request(tmp_path, 1), use_cache=False),
            orchestrator.submit_simulation(_request(tmp_path, 2), use_cache=False),
        )

        assert await orchestrator.wait_for_all_tasks(timeout=2)
        tasks = [await orchestrator.get_task_status(task_id) for task_id in task_ids]
        assert [task.status for task in tasks] == [
            SimulationStatus.FAILED,
            SimulationStatus.FAILED,
        ]
        assert all("PLECS crashed" in task.error for task in tasks)
        assert orchestrator.get_orchestrator_stats()["total_failed"] == 2
    finally:
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_all_complete_requires_terminal_truth_not_queue_emptiness(tmp_path):
    adapter = BlockingPlecsAdapter()
    orchestrator = SimulationOrchestrator(
        adapter, batch_size=1, config=_config(tmp_path, batch_size=1)
    )
    try:
        await orchestrator.submit_simulation(_request(tmp_path), use_cache=False)
        assert await asyncio.to_thread(adapter.started.wait, 1)
        assert orchestrator.get_orchestrator_stats()["queue_size"] == 0
        assert orchestrator.get_orchestrator_stats()["executor"]["is_processing"] is True

        assert await orchestrator.wait_for_all_tasks(timeout=0.05) is False
        adapter.release.set()
        assert await orchestrator.wait_for_all_tasks(timeout=2) is True
        await asyncio.sleep(0)
        assert orchestrator.get_orchestrator_stats()["executor"]["is_processing"] is False
    finally:
        adapter.release.set()
        await orchestrator.stop()


@pytest.mark.asyncio
async def test_queries_do_not_expose_task_collections_or_cache_internals(tmp_path):
    config = _config(tmp_path)
    cache = SimulationCache(config.cache)
    orchestrator = SimulationOrchestrator(
        InMemoryPlecsAdapter(), config=config, cache=cache
    )
    try:
        task_id = await orchestrator.submit_simulation(_request(tmp_path), use_cache=False)
        assert await orchestrator.wait_for_all_tasks(timeout=2)

        snapshot = await orchestrator.get_task_status(task_id)
        listed = orchestrator.list_tasks()

        assert listed == [snapshot]
        with pytest.raises(FrozenInstanceError):
            snapshot.status = SimulationStatus.FAILED
        assert not hasattr(orchestrator, "active_tasks")
        assert not hasattr(orchestrator, "completed_tasks")
        assert not hasattr(orchestrator, "cache")
        assert orchestrator.get_cache_stats() == cache.get_cache_stats()
        orchestrator.clear_cache()
        assert orchestrator.get_cache_stats()["total_entries"] == 0
    finally:
        await orchestrator.stop()
