"""Tests for refactored PlecsServer with batch API support."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from pyplecs.pyplecs import PlecsServer, dict_to_plecs_opts


class TestPlecsServerRefactored:
    """Test suite for refactored PlecsServer class."""

    @patch('pyplecs.pyplecs.xmlrpc.client.Server')
    def test_init_with_model_file(self, mock_server_class):
        """Test initialization with model_file parameter (new API)."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server

        # Create server with model file path
        server = PlecsServer(model_file="test_model.plecs")

        # Verify XML-RPC server was created
        mock_server_class.assert_called_once_with('http://localhost:1080/RPC2')

        # Verify model was loaded
        mock_server.plecs.load.assert_called_once()
        assert 'test_model.plecs' in mock_server.plecs.load.call_args[0][0]

    @patch('pyplecs.pyplecs.xmlrpc.client.Server')
    def test_init_with_legacy_api(self, mock_server_class):
        """Test initialization with sim_path and sim_name (legacy API)."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server

        # Create server with legacy parameters
        server = PlecsServer(sim_path="/path/to/models", sim_name="test.plecs")

        # Verify model was loaded with legacy path format
        mock_server.plecs.load.assert_called_once_with("/path/to/models//test.plecs")

    @patch('pyplecs.pyplecs.xmlrpc.client.Server')
    def test_simulate_without_parameters(self, mock_server_class):
        """Test simulate() without parameters runs with defaults."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.plecs.simulate.return_value = {"result": "success"}

        server = PlecsServer(model_file="test.plecs", load=False)
        server.modelName = "test"

        # Run simulation without parameters
        result = server.simulate()

        # Verify PLECS simulate was called with model name only
        mock_server.plecs.simulate.assert_called_once_with("test")
        assert result == {"result": "success"}

    @patch('pyplecs.pyplecs.xmlrpc.client.Server')
    def test_simulate_with_parameters(self, mock_server_class):
        """Test simulate() with parameters converts to ModelVars."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.plecs.simulate.return_value = {"result": "success"}

        server = PlecsServer(model_file="test.plecs", load=False)
        server.modelName = "test"

        # Run simulation with parameters
        params = {"Vi": 12.0, "Vo": 5.0}
        result = server.simulate(parameters=params)

        # Verify PLECS simulate was called with ModelVars options
        call_args = mock_server.plecs.simulate.call_args
        assert call_args[0][0] == "test"
        assert 'ModelVars' in call_args[0][1]
        assert call_args[0][1]['ModelVars'] == {"Vi": 12.0, "Vo": 5.0}

    @patch('pyplecs.pyplecs.xmlrpc.client.Server')
    def test_simulate_batch_uses_plecs_native_api(self, mock_server_class):
        """Verify batch API leverages PLECS native parallelization."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.plecs.simulate.return_value = [
            {"result": "success_1"},
            {"result": "success_2"},
            {"result": "success_3"}
        ]

        server = PlecsServer(model_file="test.plecs", load=False)
        server.modelName = "test"

        # Submit batch of simulations
        params = [
            {"Vi": 12.0},
            {"Vi": 24.0},
            {"Vi": 48.0}
        ]
        results = server.simulate_batch(params)

        # Verify PLECS received array of optStructs (not sequential calls)
        assert mock_server.plecs.simulate.call_count == 1
        call_args = mock_server.plecs.simulate.call_args
        assert call_args[0][0] == "test"

        # Verify second argument is array of ModelVars structs
        opt_structs = call_args[0][1]
        assert isinstance(opt_structs, list)
        assert len(opt_structs) == 3
        assert all('ModelVars' in opt for opt in opt_structs)
        assert opt_structs[0]['ModelVars'] == {"Vi": 12.0}
        assert opt_structs[1]['ModelVars'] == {"Vi": 24.0}
        assert opt_structs[2]['ModelVars'] == {"Vi": 48.0}

        # Verify results match
        assert len(results) == 3

    @patch('pyplecs.pyplecs.xmlrpc.client.Server')
    def test_context_manager(self, mock_server_class):
        """Test context manager automatically closes model."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server

        # Use as context manager
        with PlecsServer(model_file="test.plecs", load=False) as server:
            server.modelName = "test"
            pass

        # Verify close was called on exit
        mock_server.plecs.close.assert_called_once_with("test")

    @patch('pyplecs.pyplecs.xmlrpc.client.Server')
    def test_backward_compatibility_run_sim_with_datastream(self, mock_server_class):
        """Test legacy method run_sim_with_datastream still works."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.plecs.simulate.return_value = {"result": "success"}

        server = PlecsServer(model_file="test.plecs", load=False)
        server.modelName = "test"

        # Call legacy method
        result = server.run_sim_with_datastream({"Vi": 12.0})

        # Verify it still works (calls simulate internally)
        assert result == {"result": "success"}

    def test_dict_to_plecs_opts(self):
        """Test parameter dict to PLECS opts conversion."""
        params = {"Vi": 12, "Vo": 5, "Ri": 0.1}

        opts = dict_to_plecs_opts(params)

        # Verify structure
        assert 'ModelVars' in opts
        assert len(opts['ModelVars']) == 3

        # Verify values are floats (required by XML-RPC)
        assert all(isinstance(v, float) for v in opts['ModelVars'].values())
        assert opts['ModelVars']['Vi'] == 12.0
        assert opts['ModelVars']['Vo'] == 5.0
        assert opts['ModelVars']['Ri'] == 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
