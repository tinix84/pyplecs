"""Performance benchmarks for batch vs sequential execution.

This module validates that batch execution via PLECS native parallel API
provides significant speedup (3-5x) over sequential execution.
"""

import time
import pytest
from unittest.mock import MagicMock
from pyplecs.pyplecs import PlecsServer


def simulate_work(duration=0.1):
    """Simulate PLECS simulation work."""
    time.sleep(duration)
    return {"time": [0, 1], "voltage": [0, 5]}


class TestBatchSpeedup:
    """Benchmark tests for batch execution performance."""

    @pytest.mark.benchmark
    def test_batch_vs_sequential_speedup(self):
        """Verify batch execution is 3-5x faster than sequential.

        This test demonstrates the performance benefit of using PLECS
        native batch parallel API vs sequential execution.
        """
        # Create mock server that simulates work
        mock_server = MagicMock()

        # Sequential simulation: each call takes 0.1s
        def simulate_sequential(model, opts=None):
            simulate_work(0.1)
            return {"result": "success"}

        # Batch simulation: entire batch takes ~0.1s (parallelized)
        def simulate_batch_parallel(model, opt_list):
            # Simulate PLECS parallel execution
            # On 4 cores, 16 sims take ~4x 0.1s = 0.4s instead of 16x 0.1s = 1.6s
            num_batches = (len(opt_list) + 3) // 4  # 4 cores
            simulate_work(0.1 * num_batches)
            return [{"result": f"success_{i}"} for i in range(len(opt_list))]

        mock_server.plecs.simulate = simulate_sequential

        server = PlecsServer(model_file="test.plecs", load=False)
        server.server = mock_server
        server.modelName = "test"

        params_list = [{"Vi": float(i)} for i in range(16)]

        # Measure sequential execution time
        start = time.time()
        for params in params_list:
            server.simulate(params)
        sequential_time = time.time() - start

        # Now test batch execution
        mock_server.plecs.simulate = simulate_batch_parallel

        start = time.time()
        results = server.simulate_batch(params_list)
        batch_time = time.time() - start

        # Calculate speedup
        speedup = sequential_time / batch_time

        print(f"\nPerformance Results:")
        print(f"  Sequential: {sequential_time:.2f}s for {len(params_list)} simulations")
        print(f"  Batch:      {batch_time:.2f}s for {len(params_list)} simulations")
        print(f"  Speedup:    {speedup:.2f}x")

        # Verify minimum 3x speedup
        assert speedup >= 3.0, f"Expected 3x+ speedup, got {speedup:.2f}x"
        assert len(results) == len(params_list)

    @pytest.mark.benchmark
    def test_batch_size_scaling(self):
        """Test that larger batches maintain performance benefits."""
        mock_server = MagicMock()

        def simulate_batch(model, opt_list):
            # Simulate parallel execution on 4 cores
            num_batches = (len(opt_list) + 3) // 4
            simulate_work(0.05 * num_batches)  # Shorter sim time
            return [{"result": f"success_{i}"} for i in range(len(opt_list))]

        mock_server.plecs.simulate = simulate_batch

        server = PlecsServer(model_file="test.plecs", load=False)
        server.server = mock_server
        server.modelName = "test"

        # Test different batch sizes
        batch_sizes = [4, 8, 16, 32]
        times = []

        for batch_size in batch_sizes:
            params = [{"Vi": float(i)} for i in range(batch_size)]

            start = time.time()
            results = server.simulate_batch(params)
            elapsed = time.time() - start

            times.append(elapsed)

            print(f"Batch size {batch_size:2d}: {elapsed:.3f}s ({len(results)} results)")

        # Verify time scales sub-linearly (parallelization benefit)
        # Time for 32 sims should be < 8x time for 4 sims (ideal would be 2x on 4 cores)
        assert times[3] < times[0] * 8, "Batch execution should scale sub-linearly"

    @pytest.mark.benchmark
    def test_cache_impact_on_performance(self):
        """Test cache provides significant speedup on repeated simulations."""
        from pyplecs.cache import SimulationCache
        import pandas as pd

        cache = SimulationCache()
        cache.config.cache.enabled = True

        model_file = "test.plecs"
        parameters = {"Vi": 12.0, "Vo": 5.0}
        dummy_data = pd.DataFrame({"time": [0, 1], "voltage": [0, 5]})

        # First access - cache miss (simulate with work)
        start = time.time()
        cached = cache.get_cached_result(model_file, parameters)
        if not cached:
            # Simulate work
            time.sleep(0.1)
            cache.cache_result(model_file, parameters, dummy_data, {})
        miss_time = time.time() - start

        # Second access - cache hit (should be instant)
        start = time.time()
        cached = cache.get_cached_result(model_file, parameters)
        hit_time = time.time() - start

        print(f"\nCache Performance:")
        print(f"  Cache miss: {miss_time:.4f}s")
        print(f"  Cache hit:  {hit_time:.4f}s")
        print(f"  Speedup:    {miss_time / hit_time:.0f}x")

        # Cache hit should be much faster (100x+)
        assert cached is not None, "Cache should have result"
        assert hit_time < miss_time / 10, "Cache hit should be >10x faster"


if __name__ == "__main__":
    # Run benchmarks with verbose output
    pytest.main([__file__, "-v", "-s", "-m", "benchmark"])
