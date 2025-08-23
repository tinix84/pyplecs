import pytest
from unittest.mock import Mock
import xmlrpc.client
from pathlib import Path

from pyplecs.pyplecs import PlecsApp, PlecsServer


def test_plecs_app_get_plecs_cpu_no_processes(monkeypatch):
    """Test get_plecs_cpu when no PLECS processes exist."""
    monkeypatch.setattr('psutil.process_iter', lambda attrs: [])
    app = PlecsApp()
    cpu_usage = app.get_plecs_cpu()
    assert cpu_usage is None


def test_plecs_app_get_plecs_cpu_non_plecs_process(monkeypatch):
    """Test get_plecs_cpu with non-PLECS processes."""
    mock_process = Mock()
    mock_process.info = {"name": "notepad.exe"}
    
    monkeypatch.setattr('psutil.process_iter', lambda attrs: [mock_process])
    app = PlecsApp()
    cpu_usage = app.get_plecs_cpu()
    assert cpu_usage is None


def test_plecs_app_set_plecs_high_priority_no_processes(monkeypatch):
    """Test set_plecs_high_priority when no PLECS processes exist."""
    monkeypatch.setattr('psutil.process_iter', lambda attrs: [])
    app = PlecsApp()
    app.set_plecs_high_priority()  # Should complete without error


def test_plecs_app_kill_plecs_no_processes(monkeypatch):
    """Test kill_plecs when no PLECS processes exist."""
    monkeypatch.setattr('psutil.process_iter', lambda attrs: [])
    app = PlecsApp()
    app.kill_plecs()  # Should complete without error


def test_plecs_app_open_plecs_exception(monkeypatch):
    """Test open_plecs when subprocess fails."""
    def mock_popen_fail(*args, **kwargs):
        raise Exception("Failed to start process")
    
    monkeypatch.setattr('subprocess.Popen', mock_popen_fail)
    
    app = PlecsApp()
    app.open_plecs()  # Should handle exception gracefully and print error


def test_plecs_server_load_modelvars_modelVars_format(monkeypatch):
    """Test load_modelvars with {'ModelVars': {...}} format."""
    srv = Mock()
    srv.plecs = Mock()
    monkeypatch.setattr(xmlrpc.client, 'Server', lambda url: srv)
    
    ps = PlecsServer(sim_path='.', sim_name='test.plecs', load=False)
    
    input_data = {'ModelVars': {'Vin': 400, 'Vout': 12}}
    result = ps.load_modelvars(input_data)
    
    assert result == input_data
    assert ps.optStruct == input_data


def test_plecs_server_load_model_vars_unified_yaml_error(monkeypatch, tmp_path):
    """Test load_model_vars_unified with invalid YAML file."""
    srv = Mock()
    srv.plecs = Mock()
    monkeypatch.setattr(xmlrpc.client, 'Server', lambda url: srv)
    
    # Create invalid YAML file
    yaml_file = tmp_path / "invalid.yaml"
    yaml_file.write_text("invalid: yaml: content: [")
    
    ps = PlecsServer(sim_path='.', sim_name='test.plecs', load=False)
    
    from pyplecs.pyplecs import FileLoadError
    with pytest.raises(FileLoadError, match='Failed to load YAML file'):
        ps.load_model_vars_unified(str(yaml_file))


def test_plecs_server_load_model_vars_unified_mat_error(monkeypatch, tmp_path):
    """Test load_model_vars_unified with invalid MAT file."""
    srv = Mock()
    srv.plecs = Mock()
    monkeypatch.setattr(xmlrpc.client, 'Server', lambda url: srv)
    
    # Create invalid MAT file (just text)
    mat_file = tmp_path / "invalid.mat"
    mat_file.write_bytes(b"not a mat file")
    
    ps = PlecsServer(sim_path='.', sim_name='test.plecs', load=False)
    
    from pyplecs.pyplecs import FileLoadError
    with pytest.raises(FileLoadError, match='Failed to load MAT file'):
        ps.load_model_vars_unified(str(mat_file))


def test_plecs_server_run_sim_single_value_error(monkeypatch):
    """Test run_sim_single with ValueError from input processing."""
    srv = Mock()
    srv.plecs = Mock()
    monkeypatch.setattr(xmlrpc.client, 'Server', lambda url: srv)
    
    def mock_dict_to_plecs_opts(varin):
        raise ValueError("Invalid input format")
    
    monkeypatch.setattr('pyplecs.pyplecs.dict_to_plecs_opts', mock_dict_to_plecs_opts)
    
    ps = PlecsServer(sim_path='.', sim_name='test.plecs', load=False)
    
    with pytest.raises(ValueError, match='Invalid inputs'):
        ps.run_sim_single({'invalid': 'data'})


def test_plecs_server_run_sim_single_unexpected_error(monkeypatch):
    """Test run_sim_single with unexpected error during simulation."""
    srv = Mock()
    srv.plecs = Mock()
    monkeypatch.setattr(xmlrpc.client, 'Server', lambda url: srv)
    
    def mock_rpc_wrapper(*args, **kwargs):
        raise RuntimeError("Unexpected error")
    
    monkeypatch.setattr('pyplecs.pyplecs.rpc_call_wrapper', mock_rpc_wrapper)
    
    ps = PlecsServer(sim_path='.', sim_name='test.plecs', load=False)
    
    from pyplecs.pyplecs import SimulationError
    with pytest.raises(SimulationError, match='Unexpected simulation error'):
        ps.run_sim_single({'test': 1})


def test_plecs_server_get_model_variables_file_not_found(monkeypatch):
    """Test get_model_variables when no .plecs file can be found."""
    srv = Mock()
    srv.plecs = Mock()
    # Remove getModelVariables to force parser fallback
    delattr(srv.plecs, 'getModelVariables')
    monkeypatch.setattr(xmlrpc.client, 'Server', lambda url: srv)
    
    ps = PlecsServer(sim_path='.', sim_name='nonexistent.plecs', load=False)
    
    with pytest.raises(RuntimeError, match='Could not retrieve model variables'):
        ps.get_model_variables()
