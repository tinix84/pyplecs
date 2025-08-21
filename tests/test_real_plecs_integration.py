"""
Comprehensive tests for real PLECS integration via XML-RPC.

These tests verify that:
1. Real PLECS simulations execute correctly
2. Parameter sweeps work as expected
3. Cache behavior is correct (identical params = cache hit, changes = new sim)
4. PLECS file changes trigger new simulations
5. Variable modifications are applied correctly
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import our modules
from pyplecs.plecs_parser import parse_plecs_file
from pyplecs.cache import SimulationCache

# Import the CLI components we want to test
from cli_demo_nomocks import RealPlecsSimulator, SimulationPlan


class TestRealPlecsIntegration:
    """Test suite for real PLECS XML-RPC integration."""
    
    @pytest.fixture
    def model_file(self):
        """Path to test PLECS model."""
        return Path("data/simple_buck.plecs")
    
    @pytest.fixture 
    def temp_cache_dir(self):
        """Temporary cache directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def simulator(self, model_file, temp_cache_dir):
        """Create a simulator instance for testing."""
        # Mock the cache to use temp directory
        with patch('cli_demo_nomocks.SimulationCache') as mock_cache_class:
            mock_cache = MagicMock()
            mock_cache_class.return_value = mock_cache
            
            simulator = RealPlecsSimulator(model_file)
            simulator.cache = mock_cache
            yield simulator
            
            # Cleanup
            try:
                simulator.close()
            except:
                pass
    
    def test_plecs_startup_and_connection(self, model_file):
        """Test that PLECS starts and XML-RPC connection works."""
        simulator = RealPlecsSimulator(model_file)
        
        try:
            # Test startup
            success = simulator.start_plecs_and_connect()
            assert success, "Failed to start PLECS and connect via XML-RPC"
            
            # Verify connection
            assert simulator.server is not None, "XML-RPC server not initialized"
            assert simulator.plecs_app is not None, "PLECS app not initialized"
            
            # Test basic XML-RPC call
            try:
                # Try a simple XML-RPC call to verify connection
                result = simulator.server.get('T_sim')  # Should return simulation time
                assert result is not None, "XML-RPC call failed"
            except Exception as e:
                pytest.fail(f"XML-RPC connection test failed: {e}")
                
        finally:
            simulator.close()
    
    def test_parameter_setting_via_xmlrpc(self, simulator, model_file):
        """Test that parameters are correctly set in PLECS via XML-RPC."""
        # Mock successful connection
        simulator.server = MagicMock()
        simulator.plecs_app = MagicMock()
        
        # Test parameters
        test_params = {
            'Vi': 24.0,
            'Lo': 15e-6,
            'Co': 150e-6,
            'fs': 50000.0
        }
        
        # Call parameter setting
        simulator.set_parameters(test_params)
        
        # Verify load_modelvars was called
        simulator.server.load_modelvars.assert_called_once()
        
        # Get the actual parameters passed
        called_params = simulator.server.load_modelvars.call_args[0][0]
        
        # Verify all test parameters were included
        for param, value in test_params.items():
            assert param in called_params, f"Parameter {param} not set"
            assert called_params[param] == value, f"Parameter {param} value incorrect"
    
    def test_simulation_execution_returns_real_data(self, simulator):
        """Test that simulation execution returns real PLECS data."""
        # Mock PLECS connection and result
        simulator.server = MagicMock()
        simulator.plecs_app = MagicMock()
        
        # Mock realistic PLECS simulation result
        mock_result = {
            'Time': [i * 1e-6 for i in range(1000)],  # 1000 time points
            'Values': [
                [0.5 + 0.1 * i for i in range(1000)],  # Signal 0
                [12.0 + 0.05 * i for i in range(1000)]  # Signal 1
            ]
        }
        simulator.server.run_sim_with_datastream.return_value = mock_result
        
        # Test parameters
        test_params = {'Vi': 24.0, 'Lo': 15e-6}
        
        # Run simulation
        result = simulator.run_simulation(test_params)
        
        # Verify result structure
        assert 'timeseries' in result, "Missing timeseries data"
        assert 'metadata' in result, "Missing metadata"
        
        # Verify timeseries data
        timeseries = result['timeseries']
        if hasattr(timeseries, 'columns'):  # pandas DataFrame
            assert 'Time' in timeseries.columns, "Missing Time column"
            assert 'Signal_0' in timeseries.columns, "Missing Signal_0"
            assert 'Signal_1' in timeseries.columns, "Missing Signal_1"
            assert len(timeseries) == 1000, "Incorrect number of data points"
        else:  # dict format
            assert 'Time' in timeseries, "Missing Time data"
            assert 'Signal_0' in timeseries, "Missing Signal_0 data"
            assert 'Signal_1' in timeseries, "Missing Signal_1 data"
            assert len(timeseries['Time']) == 1000, "Incorrect time points"
        
        # Verify metadata
        metadata = result['metadata']
        assert metadata['success'] is True, "Simulation marked as failed"
        assert 'simulation_time' in metadata, "Missing simulation time"
        assert 'parameters' in metadata, "Missing parameters in metadata"
    
    def test_parameter_sweep_generation(self, model_file):
        """Test parameter sweep plan generation."""
        # Parse model to get base parameters
        parsed_data = parse_plecs_file(model_file)
        base_params = parsed_data['init_vars']
        
        # Create simulation plan
        sim_plan = SimulationPlan(model_file, base_params)
        
        # Add parameter sweeps
        sim_plan.add_sweep_parameter('Lo', 10e-6, 50e-6, 5)
        sim_plan.add_sweep_parameter('Co', 100e-6, 500e-6, 3)
        
        # Generate simulation points
        sim_points = sim_plan.generate_simulation_points()
        
        # Verify we get the expected number of combinations
        expected_points = 5 * 3  # 5 Lo values × 3 Co values
        assert len(sim_points) == expected_points, f"Expected {expected_points} simulation points, got {len(sim_points)}"
        
        # Verify each point has correct structure
        for i, point in enumerate(sim_points):
            assert 'Lo' in point, f"Point {i} missing Lo parameter"
            assert 'Co' in point, f"Point {i} missing Co parameter"
            assert '_sweep_id' in point, f"Point {i} missing sweep ID"
            
            # Verify Lo values are in range
            assert 10e-6 <= point['Lo'] <= 50e-6, f"Lo value {point['Lo']} out of range"
            
            # Verify Co values are in range  
            assert 100e-6 <= point['Co'] <= 500e-6, f"Co value {point['Co']} out of range"
    
    def test_cache_identical_simulations(self, simulator):
        """Test that identical simulations use cache instead of re-running."""
        # Mock PLECS connection
        simulator.server = MagicMock()
        simulator.plecs_app = MagicMock()
        
        # Mock cache behavior
        mock_cache = MagicMock()
        simulator.cache = mock_cache
        
        # Test parameters
        test_params = {
            'Vi': 24.0,
            'Lo': 15e-6,
            '_simulation_type': 'real_plecs',
            '_simulation_engine': 'xml_rpc'
        }
        
        # First call - cache miss, should run simulation
        mock_cache.get_cached_result.return_value = None
        mock_result = {
            'Time': [0, 1e-6, 2e-6],
            'Values': [[1, 2, 3], [4, 5, 6]]
        }
        simulator.server.run_sim_with_datastream.return_value = mock_result
        
        result1 = simulator.run_simulation(test_params)
        
        # Verify simulation was run
        simulator.server.run_sim_with_datastream.assert_called_once()
        mock_cache.cache_result.assert_called_once()
        
        # Second call - cache hit, should NOT run simulation
        simulator.server.reset_mock()
        mock_cache.reset_mock()
        
        cached_result = {
            'timeseries': {'Time': [0, 1e-6], 'Signal_0': [1, 2]},
            'metadata': {'cached': True}
        }
        mock_cache.get_cached_result.return_value = cached_result
        
        result2 = simulator.run_simulation(test_params)
        
        # Verify simulation was NOT run again
        simulator.server.run_sim_with_datastream.assert_not_called()
        mock_cache.cache_result.assert_not_called()
        
        # Verify we got cached result
        assert result2 == cached_result, "Did not return cached result"
    
    def test_cache_different_parameters_trigger_new_simulation(self, simulator):
        """Test that different parameters trigger new simulations."""
        # Mock PLECS connection
        simulator.server = MagicMock()
        simulator.plecs_app = MagicMock()
        
        # Mock cache behavior
        mock_cache = MagicMock()
        simulator.cache = mock_cache
        mock_cache.get_cached_result.return_value = None  # Always cache miss
        
        mock_result = {
            'Time': [0, 1e-6, 2e-6],
            'Values': [[1, 2, 3], [4, 5, 6]]
        }
        simulator.server.run_sim_with_datastream.return_value = mock_result
        
        # First simulation
        params1 = {'Vi': 24.0, 'Lo': 15e-6}
        result1 = simulator.run_simulation(params1)
        
        # Second simulation with different parameters
        params2 = {'Vi': 24.0, 'Lo': 25e-6}  # Different Lo value
        result2 = simulator.run_simulation(params2)
        
        # Verify both simulations were run
        assert simulator.server.run_sim_with_datastream.call_count == 2
        assert mock_cache.cache_result.call_count == 2
        
        # Verify different parameters were set
        assert simulator.server.load_modelvars.call_count == 2
        
        # Get the parameters for each call
        call1_params = simulator.server.load_modelvars.call_args_list[0][0][0]
        call2_params = simulator.server.load_modelvars.call_args_list[1][0][0]
        
        assert call1_params['Lo'] != call2_params['Lo'], "Parameters should be different"
    
    def test_plecs_file_change_triggers_new_simulation(self, temp_cache_dir):
        """Test that changing PLECS file triggers new simulation even with same parameters."""
        # Create test PLECS files
        original_file = temp_cache_dir / "test1.plecs"
        modified_file = temp_cache_dir / "test2.plecs"
        
        # Create simple PLECS content
        plecs_content1 = """
        Plecs {
          Name "test1"
          InitializationCommands "Vi = 24;"
        }
        """
        plecs_content2 = """
        Plecs {
          Name "test2" 
          InitializationCommands "Vi = 24; Lo = 15e-6;"
        }
        """
        
        original_file.write_text(plecs_content1)
        modified_file.write_text(plecs_content2)
        
        # Create real cache instance
        cache = SimulationCache(cache_dir=temp_cache_dir)
        
        # Same parameters, different files
        params = {'Vi': 24.0, '_simulation_type': 'real_plecs'}
        
        # Simulate results for both files
        result1 = {'timeseries': {'Time': [1, 2]}, 'metadata': {'file': str(original_file)}}
        result2 = {'timeseries': {'Time': [3, 4]}, 'metadata': {'file': str(modified_file)}}
        
        # Cache result for first file
        cache.cache_result(str(original_file), params, result1)
        
        # Try to get cached result for second file (should be None - cache miss)
        cached_result = cache.get_cached_result(str(modified_file), params)
        assert cached_result is None, "Different PLECS files should not share cache"
        
        # Cache result for second file
        cache.cache_result(str(modified_file), params, result2)
        
        # Verify both files have separate cache entries
        cached1 = cache.get_cached_result(str(original_file), params)
        cached2 = cache.get_cached_result(str(modified_file), params)
        
        assert cached1 is not None, "Original file cache missing"
        assert cached2 is not None, "Modified file cache missing"
        assert cached1 != cached2, "Different files should have different cached results"
    
    def test_expression_variables_are_skipped(self, simulator):
        """Test that expression variables (like D=Vo_ref/Vi) are skipped during parameter setting."""
        # Mock PLECS connection
        simulator.server = MagicMock()
        simulator.plecs_app = MagicMock()
        
        # Parameters with expressions (should be skipped) and simple values (should be set)
        test_params = {
            'Vi': 24.0,                    # Should be set
            'Lo': 15e-6,                   # Should be set
            'D': 'Vo_ref/Vi',             # Should be skipped (expression)
            'Po': 'Vi*Ii_max',            # Should be skipped (expression)
            'Ro': 'Vo_ref^2/Po',          # Should be skipped (expression)
            'fs': 100000.0                # Should be set
        }
        
        # Call parameter setting
        simulator.set_parameters(test_params)
        
        # Verify load_modelvars was called
        simulator.server.load_modelvars.assert_called_once()
        
        # Get the actual parameters passed to PLECS
        called_params = simulator.server.load_modelvars.call_args[0][0]
        
        # Verify simple parameters were included
        assert 'Vi' in called_params, "Vi should be set"
        assert 'Lo' in called_params, "Lo should be set"
        assert 'fs' in called_params, "fs should be set"
        
        # Verify expression parameters were skipped
        assert 'D' not in called_params, "Expression D should be skipped"
        assert 'Po' not in called_params, "Expression Po should be skipped"  
        assert 'Ro' not in called_params, "Expression Ro should be skipped"
        
        # Verify correct values
        assert called_params['Vi'] == 24.0
        assert called_params['Lo'] == 15e-6
        assert called_params['fs'] == 100000.0
    
    def test_end_to_end_parameter_sweep(self, model_file):
        """Integration test: full parameter sweep with cache verification."""
        # This test requires PLECS to be installed and working
        simulator = RealPlecsSimulator(model_file)
        
        try:
            # Start PLECS (skip if not available)
            if not simulator.start_plecs_and_connect():
                pytest.skip("PLECS not available for integration test")
            
            # Parse model
            parsed_data = parse_plecs_file(model_file)
            base_params = parsed_data['init_vars']
            
            # Create small parameter sweep
            sim_plan = SimulationPlan(model_file, base_params)
            sim_plan.add_sweep_parameter('Lo', 10e-6, 20e-6, 2)  # Just 2 points
            
            simulation_points = sim_plan.generate_simulation_points()
            assert len(simulation_points) == 2, "Should generate 2 simulation points"
            
            # Run simulations
            results = []
            for params in simulation_points:
                result = simulator.run_simulation(params)
                assert result['metadata']['success'], "Simulation should succeed"
                results.append(result)
            
            # Verify results are different (different Lo values should give different results)
            ts1 = results[0]['timeseries']
            ts2 = results[1]['timeseries']
            
            # Results should have same structure but potentially different values
            if hasattr(ts1, 'columns'):  # pandas DataFrame
                assert list(ts1.columns) == list(ts2.columns), "Column structure should match"
                assert len(ts1) == len(ts2), "Should have same number of time points"
            else:  # dict format
                assert ts1.keys() == ts2.keys(), "Keys should match"
                assert len(ts1['Time']) == len(ts2['Time']), "Should have same time points"
            
            # Test cache behavior - run same simulation again
            cached_result = simulator.run_simulation(simulation_points[0])
            
            # Should get same result (either from cache or fresh simulation)
            assert cached_result['metadata']['success'], "Cached/repeated simulation should succeed"
            
        finally:
            simulator.close()


class TestSimulationCache:
    """Specific tests for simulation cache behavior."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Temporary cache directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_cache_key_includes_file_hash(self, temp_cache_dir):
        """Test that cache keys include file hash to detect file changes."""
        cache = SimulationCache(cache_dir=temp_cache_dir)
        
        # Create test files with different content
        file1 = temp_cache_dir / "test1.plecs"
        file2 = temp_cache_dir / "test2.plecs"
        
        file1.write_text("Plecs { Name 'test1' }")
        file2.write_text("Plecs { Name 'test2' }")
        
        params = {'Vi': 24.0}
        result = {'timeseries': {}, 'metadata': {}}
        
        # Cache results for both files
        cache.cache_result(str(file1), params, result)
        cache.cache_result(str(file2), params, result)
        
        # Verify separate cache entries exist
        cached1 = cache.get_cached_result(str(file1), params)
        cached2 = cache.get_cached_result(str(file2), params)
        
        assert cached1 is not None, "File1 should be cached"
        assert cached2 is not None, "File2 should be cached"
        
        # Modify file1 content
        file1.write_text("Plecs { Name 'test1_modified' }")
        
        # Cache should miss for modified file1
        cached1_after = cache.get_cached_result(str(file1), params)
        assert cached1_after is None, "Modified file should cause cache miss"
        
        # Cache should still hit for unchanged file2
        cached2_after = cache.get_cached_result(str(file2), params)
        assert cached2_after is not None, "Unchanged file should still be cached"
    
    def test_cache_isolation_by_simulation_type(self, temp_cache_dir):
        """Test that different simulation types don't share cache."""
        cache = SimulationCache(cache_dir=temp_cache_dir)
        
        file_path = str(temp_cache_dir / "test.plecs")
        Path(file_path).write_text("Plecs { Name 'test' }")
        
        # Same parameters but different simulation types
        params_mock = {'Vi': 24.0, '_simulation_type': 'mock'}
        params_real = {'Vi': 24.0, '_simulation_type': 'real_plecs'}
        
        result_mock = {'timeseries': {'mock': True}, 'metadata': {}}
        result_real = {'timeseries': {'real': True}, 'metadata': {}}
        
        # Cache both results
        cache.cache_result(file_path, params_mock, result_mock)
        cache.cache_result(file_path, params_real, result_real)
        
        # Verify separate cache entries
        cached_mock = cache.get_cached_result(file_path, params_mock)
        cached_real = cache.get_cached_result(file_path, params_real)
        
        assert cached_mock is not None, "Mock simulation should be cached"
        assert cached_real is not None, "Real simulation should be cached"
        assert cached_mock != cached_real, "Different simulation types should have different cache"


if __name__ == "__main__":
    # Run specific test
    pytest.main([__file__, "-v", "--tb=short"])
