import pytest
from unittest.mock import Mock, patch
import xmlrpc.client
from pathlib import Path

from pyplecs.pyplecs import PlecsApp, PlecsServer, GenericConverterPlecsMdl


def test_plecs_app_config_errors(monkeypatch):
    """Test PlecsApp handling config manager errors."""
    def mock_config_manager_fail(config_path):
        config = Mock()
        # Simulate attribute access failure
        del config.plecs
        return config
    
    monkeypatch.setattr('pyplecs.pyplecs.ConfigManager', mock_config_manager_fail)
    monkeypatch.setattr(Path, 'exists', lambda self: False)
    monkeypatch.setattr('shutil.which', lambda x: None)
    
    with pytest.raises(FileNotFoundError):
        PlecsApp()


def test_plecs_server_load_model_vars_original_method(monkeypatch):
    """Test the original load_model_vars method (backward compatibility)."""
    srv = Mock()
    srv.plecs = Mock()
    monkeypatch.setattr(xmlrpc.client, 'Server', lambda url: srv)
    
    ps = PlecsServer(sim_path='.', sim_name='test.plecs', load=False)
    ps.optStruct = {'ModelVars': {'existing': 1.0}}
    
    result = ps.load_model_vars({'new_var': 2})
    
    assert 'ModelVars' in result
    assert result['ModelVars']['existing'] == 1.0
    assert result['ModelVars']['new_var'] == 2.0


def test_plecs_server_load_model_var_no_optstruct(monkeypatch):
    """Test load_model_var when optStruct doesn't exist."""
    srv = Mock()
    srv.plecs = Mock()
    monkeypatch.setattr(xmlrpc.client, 'Server', lambda url: srv)
    
    ps = PlecsServer(sim_path='.', sim_name='test.plecs', load=False)
    # Remove optStruct to test the initialization branch
    delattr(ps, 'optStruct')
    
    ps.load_model_var('test_var', 42)
    
    assert hasattr(ps, 'optStruct')
    assert ps.optStruct['ModelVars']['test_var'] == 42.0


def test_plecs_server_get_model_variables_fault_handling(monkeypatch):
    """Test get_model_variables handling XML-RPC faults."""
    srv = Mock()
    srv.plecs = Mock()
    srv.plecs.getModelVariables.side_effect = xmlrpc.client.Fault(-32601, 'Method not found')
    monkeypatch.setattr(xmlrpc.client, 'Server', lambda url: srv)
    
    ps = PlecsServer(sim_path='.', sim_name='simple_buck.plecs', load=False)
    # This should fall back to parser
    variables = ps.get_model_variables()
    assert isinstance(variables, list)


def test_plecs_server_get_model_variables_other_fault(monkeypatch):
    """Test get_model_variables with non-method-not-found fault."""
    srv = Mock()
    srv.plecs = Mock()
    srv.plecs.getModelVariables.side_effect = xmlrpc.client.Fault(500, 'Server error')
    monkeypatch.setattr(xmlrpc.client, 'Server', lambda url: srv)
    
    ps = PlecsServer(sim_path='.', sim_name='test.plecs', load=False)
    
    with pytest.raises(RuntimeError):
        ps.get_model_variables()


def test_generic_converter_load_modelvars_struct_parser_error(monkeypatch):
    """Test GenericConverterPlecsMdl when parser is not available."""
    def mock_import_error(*args, **kwargs):
        raise ImportError("No module named 'plecs_parser'")
    
    monkeypatch.setattr('builtins.__import__', mock_import_error)
    
    mdl = GenericConverterPlecsMdl('data/simple_buck.plecs')
    with pytest.raises(RuntimeError, match='plecs_parser module not available'):
        mdl.load_modelvars_struct_from_plecs()


def test_plecs_server_load_model_vars_unified_validation_error(monkeypatch):
    """Test load_model_vars_unified with validation errors."""
    srv = Mock()
    srv.plecs = Mock()
    srv.plecs.getModelVariables.return_value = ['allowed_var']
    monkeypatch.setattr(xmlrpc.client, 'Server', lambda url: srv)
    
    ps = PlecsServer(sim_path='.', sim_name='test.plecs', load=False)
    
    with pytest.raises(ValueError, match='Unknown model variables'):
        ps.load_model_vars_unified({'unknown_var': 123}, validate=True)


def test_plecs_server_load_model_vars_unified_unsupported_file_type(monkeypatch):
    """Test load_model_vars_unified with unsupported file extension."""
    srv = Mock()
    srv.plecs = Mock()
    monkeypatch.setattr(xmlrpc.client, 'Server', lambda url: srv)
    
    ps = PlecsServer(sim_path='.', sim_name='test.plecs', load=False)
    
    # Create a temporary file with unsupported extension
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
        tmp.write(b'test content')
        tmp_path = tmp.name
    
    try:
        from pyplecs.pyplecs import FileLoadError
        with pytest.raises(FileLoadError, match='Unsupported variable file type'):
            ps.load_model_vars_unified(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_plecs_server_load_model_vars_unified_type_error(monkeypatch):
    """Test load_model_vars_unified with invalid input type."""
    srv = Mock()
    srv.plecs = Mock()
    monkeypatch.setattr(xmlrpc.client, 'Server', lambda url: srv)
    
    ps = PlecsServer(sim_path='.', sim_name='test.plecs', load=False)
    
    with pytest.raises(TypeError, match='model_vars must be a dict or path'):
        ps.load_model_vars_unified(123)  # Invalid type


def test_plecs_server_run_sim_single_connection_error(monkeypatch):
    """Test run_sim_single with connection errors."""
    srv = Mock()
    srv.plecs = Mock()
    monkeypatch.setattr(xmlrpc.client, 'Server', lambda url: srv)
    
    def mock_rpc_wrapper(*args, **kwargs):
        import socket
        raise socket.error("Connection refused")
    
    monkeypatch.setattr('pyplecs.pyplecs.rpc_call_wrapper', mock_rpc_wrapper)
    
    ps = PlecsServer(sim_path='.', sim_name='test.plecs', load=False)
    
    from pyplecs.pyplecs import PlecsConnectionError
    with pytest.raises(PlecsConnectionError):
        ps.run_sim_single({'test': 1})


def test_process_simulation_results_with_exception(monkeypatch):
    """Test _process_simulation_results when object attribute access fails."""
    srv = Mock()
    srv.plecs = Mock()
    monkeypatch.setattr(xmlrpc.client, 'Server', lambda url: srv)
    
    class BadMockResult:
        @property
        def Time(self):
            raise Exception("Attribute access failed")
        
        @property  
        def Values(self):
            return [1, 2, 3]
    
    ps = PlecsServer(sim_path='.', sim_name='test.plecs', load=False)
    result = ps._process_simulation_results(BadMockResult())
    
    # Should fall back to raw when attribute processing fails
    assert 'raw' in result
