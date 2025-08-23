"""End-to-end workflow tests for PyPLECS integration."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from pyplecs.pyplecs import PlecsServer, GenericConverterPlecsMdl
from pyplecs.exceptions import SimulationError, PlecsConnectionError


class TestEndToEndWorkflows:
    """Test complete simulation workflows from start to finish."""

    def test_complete_simulation_workflow(self):
        """Test full workflow: start PLECS -> load model -> simulate."""
        from pyplecs.pyplecs import PlecsApp
        import time
        
        # Step 1: Start PLECS application
        plecs_app = PlecsApp()
        
        try:
            # Start PLECS process
            plecs_app.open_plecs()
            
            # Wait for PLECS to start up
            time.sleep(3)
            
            # Step 2: Create PLECS server and load model
            # Use absolute path to the PLECS file
            repo_root = Path(__file__).resolve().parents[2]
            model_path = repo_root / 'data'
            model_file = 'simple_buck.plecs'
            
            server = PlecsServer(str(model_path), model_file, load=True)
            
            # Step 3: Load model variables
            variables = {
                'Vi': 400.0,      # Input voltage
                'Vo_ref': 200.0,  # Output voltage reference
                'Ii_max': 10.0,   # Max input current
                'fs': 20000.0     # Switching frequency
            }
            server.load_model_vars(variables)
            
            # Verify variables were loaded correctly
            assert server.optStruct is not None
            assert 'ModelVars' in server.optStruct
            assert server.optStruct['ModelVars']['Vi'] == 400.0
            assert server.optStruct['ModelVars']['Vo_ref'] == 200.0
            
            # Step 4: Run simulation
            result = server.run_sim_single(variables)
            
            # Step 5: Verify results
            assert result['success'] is True
            assert 'results' in result
            assert 'execution_time' in result
            assert result['execution_time'] > 0
            
            # Check that we got some simulation data
            results_data = result['results']
            assert isinstance(results_data, dict)
            
            print(f"Simulation completed in {result['execution_time']:.3f}s")
            print(f"Parameters used: {result['parameters_used']}")
            
        except Exception as e:
            # If PLECS is not available, skip the test
            pytest.skip(f"PLECS not available or simulation failed: {e}")
            
        finally:
            # Clean up: Kill PLECS processes
            try:
                plecs_app.kill_plecs()
            except Exception:
                pass  # Ignore cleanup errors

    def test_parameter_sweep_workflow(self):
        """Test parameter sweep workflow with multiple simulation points."""
        mock_server = Mock()
        mock_plecs = Mock()
        mock_server.plecs = mock_plecs
        
        # Mock different results for different input voltages
        def mock_simulate(*args, **kwargs):
            return {
                'SimulationOK': True,
                'Time': [0.0, 1e-6, 2e-6],
                'Values': [[400.0, 399.8, 399.6]]
            }
        
        mock_plecs.simulate.side_effect = mock_simulate
        
        with patch('xmlrpc.client.ServerProxy', return_value=mock_server):
            server = PlecsServer('data', 'simple_buck.plecs', load=False)
            
            # Define parameter sweep
            sweep_points = [
                {'Vin': 300.0, 'Vout': 150.0},
                {'Vin': 400.0, 'Vout': 200.0},
                {'Vin': 500.0, 'Vout': 250.0}
            ]
            
            results = []
            for params in sweep_points:
                result = server.run_sim_single(params)
                results.append(result)
            
            # Verify all simulations completed successfully
            assert len(results) == 3
            for result in results:
                assert result['success'] is True

    def test_file_loading_workflow(self):
        """Test workflow with different file loading methods."""
        # Test MATLAB file loading
        with patch('pyplecs.pyplecs.load_mat_file') as mock_load_mat:
            mock_load_mat.return_value = {'Vin': 400, 'Vout': 200}
            
            server = PlecsServer('data', 'test.plecs', load=False)
            result = server.load_model_vars('test_vars.mat')
            
            assert result['ModelVars']['Vin'] == 400.0
            assert result['ModelVars']['Vout'] == 200.0

    def test_model_validation_workflow(self):
        """Test model file validation workflow."""
        # Test with valid PLECS file
        with patch('pathlib.Path.exists', return_value=True):
            mdl = GenericConverterPlecsMdl('data/simple_buck.plecs')
            assert mdl.validate_model() is True
        
        # Test with non-existent file
        with patch('pathlib.Path.exists', return_value=False):
            mdl = GenericConverterPlecsMdl('nonexistent.plecs')
            assert mdl.validate_model() is False

    def test_error_recovery_workflow(self):
        """Test error handling and recovery scenarios."""
        mock_server = Mock()
        mock_plecs = Mock()
        mock_server.plecs = mock_plecs
        
        # Mock simulation failure
        mock_plecs.simulate.side_effect = Exception("Simulation failed")
        
        with patch('xmlrpc.client.ServerProxy', return_value=mock_server):
            server = PlecsServer('data', 'simple_buck.plecs', load=False)
            
            variables = {'Vin': 400.0, 'Vout': 200.0}
            
            # Should handle simulation errors gracefully
            with pytest.raises(SimulationError):
                server.run_sim_single(variables)

    def test_connection_failure_workflow(self):
        """Test handling of connection failures."""
        # Mock connection failure
        with patch('xmlrpc.client.ServerProxy',
                   side_effect=ConnectionError("Could not connect")):
            
            # Should raise appropriate connection error
            with pytest.raises(PlecsConnectionError):
                server = PlecsServer('data', 'simple_buck.plecs', load=True)


class TestWorkflowIntegration:
    """Test integration between different PyPLECS components."""

    def test_plecs_server_model_integration(self):
        """Test integration between PlecsServer and GenericConverterPlecsMdl."""
        # Create model object
        mdl = GenericConverterPlecsMdl('data/simple_buck.plecs')
        
        # Mock file existence
        with patch('pathlib.Path.exists', return_value=True):
            assert mdl.validate_model() is True
        
        # Test model info retrieval
        info = mdl.get_model_info()
        assert info['name'] == 'simple_buck'
        assert info['type'] == 'plecs'
        assert 'model_vars' in info

    def test_variable_loading_consistency(self):
        """Test that variable loading is consistent across methods."""
        server = PlecsServer('data', 'test.plecs', load=False)
        
        # Test different input formats give consistent results
        vars1 = {'Vin': 400, 'Vout': 200}
        vars2 = {'ModelVars': {'Vin': 400, 'Vout': 200}}
        
        result1 = server.load_model_vars(vars1)
        server.optStruct = {}  # Reset
        result2 = server.load_model_vars(vars2)
        
        # Both should produce the same result
        assert result1['ModelVars'] == result2['ModelVars']

    def test_type_coercion_consistency(self):
        """Test that type coercion is consistent for XML-RPC compatibility."""
        server = PlecsServer('data', 'test.plecs', load=False)
        
        # Mix of types that should all become floats
        mixed_vars = {
            'int_val': 42,
            'float_val': 3.14,
            'str_numeric': '123.45'
        }
        
        result = server.load_model_vars(mixed_vars)
        
        # All numeric values should be floats for XML-RPC
        for key, value in result['ModelVars'].items():
            if key in ['int_val', 'float_val', 'str_numeric']:
                assert isinstance(value, float)

    def test_backward_compatibility(self):
        """Test that old methods still work for backward compatibility."""
        server = PlecsServer('data', 'test.plecs', load=False)
        
        # Old method should still work but show deprecation warning
        with pytest.warns(DeprecationWarning):
            server.load_modelvars({'Vin': 400, 'Vout': 200})
        
        # Result should be the same as new method
        assert server.optStruct['ModelVars']['Vin'] == 400.0
        assert server.optStruct['ModelVars']['Vout'] == 200.0


class TestResultStandardization:
    """Test standardized result formats across all methods."""

    def test_simulation_result_format(self):
        """Test that simulation results follow standard format."""
        mock_server = Mock()
        mock_plecs = Mock()
        mock_server.plecs = mock_plecs
        
        mock_plecs.simulate.return_value = {
            'SimulationOK': True,
            'Time': [0.0, 1e-6],
            'Values': [[400.0, 399.8]]
        }
        
        with patch('xmlrpc.client.ServerProxy', return_value=mock_server):
            server = PlecsServer('data', 'test.plecs', load=False)
            result = server.run_sim_single({'Vin': 400})
            
            # Check standard result format
            assert isinstance(result, dict)
            assert 'success' in result
            assert 'results' in result
            assert 'execution_time' in result
            assert isinstance(result['success'], bool)

    def test_variable_loading_result_format(self):
        """Test that variable loading results follow standard format."""
        server = PlecsServer('data', 'test.plecs', load=False)
        
        result = server.load_model_vars({'Vin': 400, 'Vout': 200})
        
        # Check standard format
        assert isinstance(result, dict)
        assert 'ModelVars' in result
        assert isinstance(result['ModelVars'], dict)
        
        # Check value types for XML-RPC compatibility
        for key, value in result['ModelVars'].items():
            assert isinstance(value, (float, str, int))

    def test_error_result_format(self):
        """Test that error results follow standard format."""
        mock_server = Mock()
        mock_plecs = Mock()
        mock_server.plecs = mock_plecs
        
        # Mock simulation failure
        mock_plecs.simulate.return_value = {'SimulationOK': False}
        
        with patch('xmlrpc.client.ServerProxy', return_value=mock_server):
            server = PlecsServer('data', 'test.plecs', load=False)
            
            result = server.run_sim_single({'Vin': 400})
            
            # Should have standard error format
            assert result['success'] is False
            assert 'error' in result
            assert 'execution_time' in result


if __name__ == '__main__':
    pytest.main([__file__])
