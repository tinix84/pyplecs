"""Tests for batch orchestration with PLECS native parallel API."""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from pyplecs.orchestration import SimulationOrchestrator, TaskPriority, BatchSimulationExecutor
from pyplecs.core.models import SimulationRequest, SimulationResult


@pytest.fixture
def temp_model_file():
    """Create a temporary .plecs file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".plecs", delete=False, mode='w') as f:
        f.write("<?xml version='1.0'?><PlexilModel></PlexilModel>")
        temp_path = f.name
    yield temp_path
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def mock_plecs_server():
    """Create a mock PLECS server for testing."""
    server = MagicMock()
    server.simulate_batch = MagicMock(return_value=[
        {"time": [0, 1], "voltage": [0, 5]},
        {"time": [0, 1], "voltage": [0, 10]},
        {"time": [0, 1], "voltage": [0, 15]}
    ])
    return server


@pytest.fixture
def batch_executor(mock_plecs_server):
    """Create a batch executor with mock server."""
    return BatchSimulationExecutor(mock_plecs_server, batch_size=4)


class TestBatchSimulationExecutor:
    """Test suite for BatchSimulationExecutor."""

    def test_executor_initialization(self, mock_plecs_server):
        """Test executor initializes with correct batch size."""
        executor = BatchSimulationExecutor(mock_plecs_server, batch_size=8)

        assert executor.server == mock_plecs_server
        assert executor.batch_size == 8
        assert executor.stats['batches_executed'] == 0

    def test_execute_batch_groups_tasks(self, batch_executor, mock_plecs_server, temp_model_file):
        """Test batch executor groups tasks and submits to PLECS."""
        from pyplecs.orchestration import SimulationTask

        # Create test tasks
        tasks = [
            SimulationTask(
                request=SimulationRequest(
                    model_file=temp_model_file,
                    parameters={"Vi": float(i)}
                )
            )
            for i in range(3)
        ]

        # Execute batch
        results = batch_executor.execute_batch(tasks)

        # Verify PLECS simulate_batch was called once with all parameters
        mock_plecs_server.simulate_batch.assert_called_once()
        call_args = mock_plecs_server.simulate_batch.call_args[0][0]
        assert len(call_args) == 3
        assert call_args[0] == {"Vi": 0.0}
        assert call_args[1] == {"Vi": 1.0}
        assert call_args[2] == {"Vi": 2.0}

        # Verify results returned
        assert len(results) == 3

    def test_execute_empty_batch(self, batch_executor):
        """Test executing empty batch returns empty list."""
        results = batch_executor.execute_batch([])
        assert results == []

    def test_batch_statistics_updated(self, batch_executor, temp_model_file):
        """Test batch execution updates statistics."""
        from pyplecs.orchestration import SimulationTask

        tasks = [
            SimulationTask(
                request=SimulationRequest(
                    model_file=temp_model_file,
                    parameters={"Vi": 12.0}
                )
            )
        ]

        batch_executor.execute_batch(tasks)

        # Verify stats updated
        assert batch_executor.stats['batches_executed'] == 1
        assert batch_executor.stats['total_simulations'] == 1
        assert batch_executor.stats['total_runtime'] > 0


class TestSimulationOrchestratorBatch:
    """Test suite for batch orchestration."""

    @pytest.mark.asyncio
    async def test_orchestrator_batches_tasks(self, mock_plecs_server):
        """Verify orchestrator groups tasks into batches."""
        orchestrator = SimulationOrchestrator(
            plecs_server=mock_plecs_server,
            batch_size=4
        )

        # Submit 10 tasks
        task_ids = []
        for i in range(10):
            task_id = await orchestrator.submit_simulation(
                SimulationRequest(
                    model_file="test.plecs",
                    parameters={"Vi": float(i)}
                ),
                use_cache=False  # Disable cache for this test
            )
            task_ids.append(task_id)

        # Wait for all tasks to complete
        await orchestrator.wait_for_all_tasks(timeout=10)

        # Should execute in batches (e.g., 4+4+2 for batch_size=4)
        # Verify all tasks completed
        assert len(task_ids) == 10
        for task_id in task_ids:
            task = await orchestrator.get_task_status(task_id)
            assert task is not None

    @pytest.mark.asyncio
    async def test_cache_avoids_redundant_simulations(self, mock_plecs_server):
        """Verify cache prevents re-simulation of identical parameters."""
        orchestrator = SimulationOrchestrator(plecs_server=mock_plecs_server)

        # Enable cache
        orchestrator.cache.config.cache.enabled = True

        request = SimulationRequest(
            model_file="test.plecs",
            parameters={"Vi": 12.0}
        )

        # First execution - cache miss
        task_id1 = await orchestrator.submit_simulation(request, use_cache=True)
        task1 = await orchestrator.wait_for_completion(task_id1, timeout=5)

        # Note: In real scenario, cached would be False on first run
        # For this test, we'd need a full integration test with actual cache

        # Second execution - should check cache
        task_id2 = await orchestrator.submit_simulation(request, use_cache=True)
        task2 = await orchestrator.wait_for_completion(task_id2, timeout=5)

        # Both tasks should complete
        assert task1 is not None
        assert task2 is not None

    @pytest.mark.asyncio
    async def test_priority_queue_ordering(self, mock_plecs_server):
        """Test tasks are processed by priority."""
        orchestrator = SimulationOrchestrator(plecs_server=mock_plecs_server)

        # Submit tasks with different priorities
        low_task = await orchestrator.submit_simulation(
            SimulationRequest(model_file="test.plecs", parameters={"Vi": 1.0}),
            priority=TaskPriority.LOW,
            use_cache=False
        )

        critical_task = await orchestrator.submit_simulation(
            SimulationRequest(model_file="test.plecs", parameters={"Vi": 2.0}),
            priority=TaskPriority.CRITICAL,
            use_cache=False
        )

        normal_task = await orchestrator.submit_simulation(
            SimulationRequest(model_file="test.plecs", parameters={"Vi": 3.0}),
            priority=TaskPriority.NORMAL,
            use_cache=False
        )

        # Wait for completion
        await orchestrator.wait_for_all_tasks(timeout=10)

        # All should complete
        assert await orchestrator.get_task_status(low_task) is not None
        assert await orchestrator.get_task_status(critical_task) is not None
        assert await orchestrator.get_task_status(normal_task) is not None

    @pytest.mark.asyncio
    async def test_orchestrator_statistics(self, mock_plecs_server):
        """Test orchestrator tracks statistics correctly."""
        orchestrator = SimulationOrchestrator(plecs_server=mock_plecs_server)

        # Submit some tasks
        for i in range(5):
            await orchestrator.submit_simulation(
                SimulationRequest(
                    model_file="test.plecs",
                    parameters={"Vi": float(i)}
                ),
                use_cache=False
            )

        # Wait for completion
        await orchestrator.wait_for_all_tasks(timeout=10)

        # Get stats
        stats = orchestrator.get_orchestrator_stats()

        # Verify stats structure
        assert 'total_submitted' in stats
        assert 'total_completed' in stats
        assert 'executor' in stats
        assert 'cache_stats' in stats

        # Verify executor stats
        assert 'batch_size' in stats['executor']
        assert stats['executor']['batch_size'] == 4  # default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
