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
