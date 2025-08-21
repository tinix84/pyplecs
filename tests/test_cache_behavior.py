"""
Tests for cache behavior with file changes and simulation type isolation.
"""

# Move imports to the top
import pytest
import tempfile
import shutil
from pathlib import Path
from pyplecs.cache import SimulationCache
from cli_demo_nomocks import RealPlecsSimulator


class TestCacheBehavior:
    """Tests for simulation cache behavior."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def cache(self):
        """Create simulation cache instance."""
        return SimulationCache()

    def test_cache_differentiates_simulation_types(self, cache, temp_dir):
        """Test that mock and real simulations don't share cache."""
        # Create test PLECS file
        test_file = temp_dir / "test.plecs"
        test_file.write_text(
            "Plecs { Name 'test' InitializationCommands 'Vi=24;' }"
        )
        
        # Same base parameters but different simulation types
        base_params = {'Vi': 24.0, 'Lo': 15e-6}
        
        mock_params = base_params.copy()
        mock_params['_simulation_type'] = 'mock'  # type: ignore
        mock_params['_simulation_engine'] = 'mock'  # type: ignore
        
        real_params = base_params.copy()
        real_params['_simulation_type'] = 'real_plecs'  # type: ignore
        real_params['_simulation_engine'] = 'xml_rpc'  # type: ignore
        
        # Create mock result structure
        mock_result_data = {'Time': [0, 1, 2], 'Signal_0': [1, 2, 3]}
        mock_metadata = {'simulation_type': 'mock', 'success': True}
        
        # Cache mock result
        cache.cache_result(
            str(test_file),
            mock_params,
            mock_result_data,
            mock_metadata
        )
        
        # Check that real simulation parameters don't hit mock cache
        cached_result = cache.get_cached_result(str(test_file), real_params)
        assert cached_result is None, "Real params should not hit mock cache"
        
        # Create and cache real result
        real_result_data = {'Time': [0, 1, 2], 'Signal_0': [4, 5, 6]}
        real_metadata = {'simulation_type': 'real_plecs', 'success': True}
        
        cache.cache_result(
            str(test_file),
            real_params,
            real_result_data,
            real_metadata
        )
        
        # Verify both types have separate cache entries
        mock_cached = cache.get_cached_result(str(test_file), mock_params)
        real_cached = cache.get_cached_result(str(test_file), real_params)
        
        assert mock_cached is not None, "Mock result should be cached"
        assert real_cached is not None, "Real result should be cached"
        # Compare metadata to verify they're different cache entries
        assert mock_cached['metadata'] != real_cached['metadata'], (
            "Should have different cached results"
        )

    def test_cache_detects_file_changes(self, cache, temp_dir):
        """Test that cache misses when PLECS file content changes."""
        test_file = temp_dir / "test.plecs"
        
        # Create initial file
        initial_content = (
            "Plecs { Name 'test1' InitializationCommands 'Vi=24;' }"
        )
        test_file.write_text(initial_content)
        
        params = {
            'Vi': 24.0,
            '_simulation_type': 'real_plecs',
            '_simulation_engine': 'xml_rpc'
        }
        
        # Cache initial result
        initial_result = {'Time': [0, 1], 'Signal_0': [1, 2]}
        initial_metadata = {'success': True, 'file_content': initial_content}
        
        cache.cache_result(
            str(test_file), params, initial_result, initial_metadata
        )
        
        # Verify cache hit
        cached = cache.get_cached_result(str(test_file), params)
        assert cached is not None, (
            "Should find cached result for original file"
        )
        
        # Modify file content
        modified_content = (
            "Plecs { Name 'test2' InitializationCommands 'Vi=48;' }"
        )
        test_file.write_text(modified_content)
        
        # Should get cache miss for modified file
        cached_after_change = cache.get_cached_result(str(test_file), params)
        assert cached_after_change is None, (
            "Should miss cache after file change"
        )

    def test_cache_performance_with_real_simulator(self):
        """Test cache performance with real PLECS simulator."""
        model_file = Path("data/simple_buck.plecs")
        if not model_file.exists():
            pytest.skip("PLECS model file not found")
        
        simulator = RealPlecsSimulator(str(model_file))
        success = simulator.start_plecs_and_connect()
        if not success:
            simulator.close()
            pytest.skip("PLECS not available")
        
        try:
            params = {
                'Vi': 24.0,
                'Lo': 15e-6,
                '_simulation_type': 'real_plecs',
                '_simulation_engine': 'xml_rpc'
            }
            
            # First run - should execute simulation
            import time
            start = time.time()
            result1 = simulator.run_simulation(params)
            time1 = time.time() - start
            
            assert result1['metadata']['success'], "First simulation failed"
            
            # Second run - should use cache
            start = time.time()
            result2 = simulator.run_simulation(params)
            time2 = time.time() - start
            
            assert result2['metadata']['success'], "Second simulation failed"
            
            # Cache should provide significant speedup
            speedup = time1 / time2 if time2 > 0 else float('inf')
            assert speedup > 1.5, (
                f"Cache not effective: {time1:.3f}s vs {time2:.3f}s"
            )
            
        finally:
            simulator.close()

    def test_cache_format_compatibility(self, cache, temp_dir):
        """Test compatibility between DataFrame and configured formats."""
        import pandas as pd
        import pyarrow as pa
        import pyarrow.parquet as pq
        import json

        # Create mock DataFrame
        df = pd.DataFrame({
            'Time': [0, 1, 2],
            'Signal_0': [1.0, 2.0, 3.0]
        })

        # Convert DataFrame to parquet
        parquet_file = temp_dir / "timeseries.parquet"
        table = pa.Table.from_pandas(df)
        with parquet_file.open('wb') as f:
            pq.write_table(table, f)

        # Read back parquet file
        read_table = pq.read_table(parquet_file)
        read_df = read_table.to_pandas()
        assert df.equals(read_df), "Parquet format mismatch"

        # Convert metadata to JSON
        metadata = {'simulation_type': 'real_plecs', 'success': True}
        json_file = temp_dir / "metadata.json"
        with json_file.open('w', encoding='utf-8') as f:
            json.dump(metadata, f)

        # Read back JSON file
        with json_file.open('r', encoding='utf-8') as f:
            read_metadata = json.load(f)
        assert metadata == read_metadata, "JSON format mismatch"

        # Cache and retrieve using both formats
        params = {
            'Vi': 24.0,
            '_simulation_type': 'real_plecs',
            '_simulation_engine': 'xml_rpc'
        }
        cache.cache_result(str(parquet_file), params, read_df, read_metadata)
        cached_result = cache.get_cached_result(str(parquet_file), params)
        assert cached_result is not None, "Cached result not found"
        assert cached_result['timeseries'].equals(read_df), (
            "Cached timeseries mismatch"
        )
        assert cached_result['metadata'] == read_metadata, (
            "Cached metadata mismatch"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
