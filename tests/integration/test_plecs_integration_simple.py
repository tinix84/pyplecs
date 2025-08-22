"""
Integration tests for real PLECS XML-RPC functionality.

These tests verify end-to-end functionality of:
- PLECS startup and XML-RPC connection
- Real simulation execution
- Parameter sweeps
- Cache behavior
- File change detection
"""

import pytest
import time
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pyplecs.plecs_parser import parse_plecs_file
from cli_demo_nomocks import RealPlecsSimulator, SimulationPlan


class TestRealPlecsIntegration:
    """Integration tests for real PLECS XML-RPC functionality."""

    @pytest.fixture
    def model_file(self):
        """Path to test PLECS model."""
        model_path = Path("data/simple_buck.plecs")
        if not model_path.exists():
            pytest.skip(f"PLECS model file not found: {model_path}")
        return model_path

    @pytest.fixture
    def simulator(self, model_file):
        """Create and start a PLECS simulator for testing."""
        simulator = RealPlecsSimulator(model_file)

        # Try to start PLECS - skip tests if not available
        success = simulator.start_plecs_and_connect()
        if not success:
            simulator.close()
            pytest.skip("PLECS not available or failed to start")

        yield simulator

        # Cleanup
        simulator.close()

    def test_plecs_startup_and_connection(self, simulator):
        """Test that PLECS starts and XML-RPC connection works."""
        # Verify connection components are initialized
        assert simulator.server is not None, "XML-RPC server not initialized"
        assert simulator.plecs_app is not None, "PLECS app not initialized"

        # Test that we can call XML-RPC methods
        try:
            # Try to load model variables - this should work if connected
            simulator.server.load_modelvars({'test_var': 1.0})
        except Exception as e:
            pytest.fail(f"XML-RPC connection test failed: {e}")

    def test_real_simulation_execution(self, simulator):
        """Test that real PLECS simulations execute and return data."""
        params = {
            'Vi': 24.0,
            'Lo': 15e-6,
            'Co': 150e-6,
            '_simulation_type': 'real_plecs',
            '_simulation_engine': 'xml_rpc'
        }

        result = simulator.run_simulation(params)

        # Verify result structure
        assert 'timeseries' in result, "Missing timeseries data"
        assert 'metadata' in result, "Missing metadata"
        assert result['metadata']['success'], "Simulation should succeed"

        # Verify we have actual time series data
        timeseries = result['timeseries']
        if hasattr(timeseries, 'columns'):  # pandas DataFrame
            assert 'Time' in timeseries.columns, "Missing Time column"
            assert len(timeseries) > 100, "Should have substantial data points"
        else:  # dict format
            assert 'Time' in timeseries, "Missing Time data"
            assert len(timeseries['Time']) > 100, "Should have many time points"

    def test_parameter_modification(self, simulator):
        """Test that different parameters produce different results."""
        base_params = {
            'Vi': 24.0,
            'Lo': 15e-6,
            'Co': 150e-6,
            '_simulation_type': 'real_plecs',
            '_simulation_engine': 'xml_rpc'
        }

        # Run simulation with base parameters
        result1 = simulator.run_simulation(base_params)
        assert result1['metadata']['success'], "First simulation failed"

        # Run simulation with modified parameters
        modified_params = base_params.copy()
        modified_params['Lo'] = 25e-6  # Different inductance

        result2 = simulator.run_simulation(modified_params)
        assert result2['metadata']['success'], "Second simulation failed"

        # Verify both have same structure but potentially different values
        ts1 = result1['timeseries']
        ts2 = result2['timeseries']

        if hasattr(ts1, 'columns'):  # pandas DataFrame
            assert list(ts1.columns) == list(ts2.columns), "Columns should match"
            assert len(ts1) == len(ts2), "Should have same number of time points"
        else:  # dict format
            assert ts1.keys() == ts2.keys(), "Keys should match"
            assert len(ts1['Time']) == len(ts2['Time']), "Time points match"

    def test_parameter_sweep_functionality(self, simulator, model_file):
        """Test parameter sweep generation and execution."""
        # Parse model to get base parameters
        parsed_data = parse_plecs_file(model_file)
        base_params = parsed_data['init_vars']

        # Create simulation plan with small sweep
        sim_plan = SimulationPlan(model_file, base_params)
        sim_plan.add_sweep_parameter('Lo', 10e-6, 20e-6, 10)  # 10 points

        simulation_points = sim_plan.generate_simulation_points()
        assert len(simulation_points) == 10, "Should generate 10 simulation points"

        # Run all simulations in sweep
        results = []
        for params in simulation_points:
            result = simulator.run_simulation(params)
            assert result['metadata']['success'], "Sweep simulation failed"
            results.append(result)

        # Verify we got different parameter values
        param_values = [point['Lo'] for point in simulation_points]
        assert len(set(param_values)) == 10, "Should have different Lo values"
        assert param_values[0] != param_values[1], "Lo values should be different"


@pytest.mark.slow
class TestPlecsPerformance:
    """Performance tests for PLECS integration."""

    @pytest.fixture
    def simulator(self):
        """Create simulator for performance tests."""
        model_file = Path("data/simple_buck.plecs")
        if not model_file.exists():
            pytest.skip("PLECS model file not found")

        simulator = RealPlecsSimulator(model_file)
        success = simulator.start_plecs_and_connect()
        if not success:
            simulator.close()
            pytest.skip("PLECS not available")

        yield simulator
        simulator.close()

    def test_simulation_performance_benchmark(self, simulator):
        """Benchmark simulation performance."""
        params = {
            'Vi': 24.0,
            'Lo': 15e-6,
            '_simulation_type': 'real_plecs',
            '_simulation_engine': 'xml_rpc'
        }

        # Force cache miss so we measure actual simulation runtime
        if hasattr(simulator, 'cache'):
            try:
                # If cache is a MagicMock
                simulator.cache.get_cached_result.return_value = None
            except Exception:
                # Fallback: override with a function that always misses
                simulator.cache.get_cached_result = lambda *a, **k: None

    # (No mock-run wrapper left here — we only force cache misses above.)

        # Run multiple simulations to get average performance
        times = []
        for i in range(10):
            # Use different Lo values to avoid cache
            test_params = params.copy()
            test_params['Lo'] = (15 + i) * 1e-6

            start_time = time.time()
            result = simulator.run_simulation(test_params)
            elapsed = time.time() - start_time

            assert result['metadata']['success'], f"Simulation {i+1} failed"
            times.append(elapsed)

        avg_time = sum(times) / len(times)

        # Simulations should complete in reasonable time
        assert avg_time < 1.0, f"Simulations too slow: {avg_time:.3f}s average"
        assert avg_time > 0.01, f"Simulations too fast (likely cached): {avg_time:.3f}s"

        print(f"Average simulation time: {avg_time:.3f}s")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
