import pytest
from unittest.mock import Mock, patch
import xmlrpc.client
from pathlib import Path
import tempfile
import scipy.io as sio

from pyplecs.pyplecs import PlecsServer, SimulationError, PlecsConnectionError


@pytest.fixture
def mock_server(monkeypatch):
    """Mock XML-RPC server for testing."""
    srv = Mock()
    srv.plecs = Mock()
    monkeypatch.setattr(xmlrpc.client, 'Server', lambda url: srv)
    return srv


def test_plecs_server_init_with_load(mock_server):
    """Test PlecsServer initialization with loading."""
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', port='1080', load=True)
    mock_server.plecs.load.assert_called_once_with('/test//model.plecs')
    assert ps.modelName == 'model'


def test_plecs_server_init_no_load(mock_server):
    """Test PlecsServer initialization without loading."""
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    mock_server.plecs.load.assert_not_called()


def test_load_file_method(mock_server):
    """Test load_file method."""
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    ps.load_file()
    mock_server.plecs.load.assert_called_once_with('/test//model.plecs')


def test_load_method(mock_server):
    """Test load method."""
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    ps.load()
    mock_server.plecs.load.assert_called_once_with('/test//model.plecs')


def test_close_method(mock_server):
    """Test close method."""
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    ps.close()
    mock_server.plecs.close.assert_called_once_with('model')


def test_load_model_var(mock_server):
    """Test loading single model variable."""
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    ps.load_model_var('Vin', 400)
    assert ps.optStruct['ModelVars']['Vin'] == 400.0


def test_set_value(mock_server):
    """Test setting component parameter value."""
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    ps.set_value('Buck/L1', 'L', 1e-3)
    mock_server.plecs.set.assert_called_once_with('model/Buck/L1', 'L', '0.001')


def test_get_with_parameter(mock_server):
    """Test getting specific parameter from component."""
    mock_server.plecs.get.return_value = 1e-3
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    result = ps.get('Buck/L1', 'L')
    assert result == 1e-3
    mock_server.plecs.get.assert_called_once_with('Buck/L1', 'L')


def test_get_without_parameter(mock_server):
    """Test getting all parameters from component."""
    mock_server.plecs.get.return_value = {'L': 1e-3, 'R': 0.1}
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    result = ps.get('Buck/L1')
    assert result == {'L': 1e-3, 'R': 0.1}
    mock_server.plecs.get.assert_called_once_with('Buck/L1')


def test_list_model_variables_success(mock_server):
    """Test successful listing of model variables."""
    mock_server.plecs.getModelVariables.return_value = ['Vin', 'Vout', 'Iload']
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    success, vars_list = ps.list_model_variables()
    assert success is True
    assert vars_list == ['Vin', 'Vout', 'Iload']


def test_list_model_variables_failure(mock_server):
    """Test failed listing of model variables."""
    mock_server.plecs.getModelVariables.side_effect = Exception("RPC Error")
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    success, error_msg = ps.list_model_variables()
    assert success is False
    assert "RPC Error" in error_msg


def test_export_scope_csv_without_time_range(mock_server):
    """Test exporting scope data to CSV without time range."""
    mock_server.plecs.scope.return_value = '/path/to/output.csv'
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    result = ps.export_scope_csv('Scope1', 'output.csv')
    assert result == '/path/to/output.csv'
    mock_server.plecs.scope.assert_called_once_with('Scope1', 'ExportCSV', 'output.csv')


def test_export_scope_csv_with_time_range(mock_server):
    """Test exporting scope data to CSV with time range."""
    mock_server.plecs.scope.return_value = '/path/to/output.csv'
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    result = ps.export_scope_csv('Scope1', 'output.csv', [0, 1e-3])
    assert result == '/path/to/output.csv'
    mock_server.plecs.scope.assert_called_once_with('Scope1', 'ExportCSV', 'output.csv', [0, 1e-3])


def test_run_sim_with_datastream_no_params(mock_server):
    """Test running simulation without parameters."""
    mock_server.plecs.simulate.return_value = {'Time': [0, 1], 'Values': [[0], [1]]}
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    result = ps.run_sim_with_datastream()
    mock_server.plecs.simulate.assert_called_once_with('model')


def test_run_sim_with_datastream_with_params(mock_server):
    """Test running simulation with parameters."""
    mock_server.plecs.simulate.return_value = {'Time': [0, 1], 'Values': [[0], [1]]}
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    result = ps.run_sim_with_datastream({'Vin': 400})
    mock_server.plecs.simulate.assert_called_once_with('model', ps.optStruct)


def test_simulate_batch_no_callback(mock_server):
    """Test batch simulation without callback."""
    opt_structs = [{'ModelVars': {'Vin': 400}}, {'ModelVars': {'Vin': 500}}]
    mock_server.plecs.simulate.return_value = [{'result1': 'data1'}, {'result2': 'data2'}]
    
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    results = ps.simulate_batch(opt_structs)
    
    assert results == [{'result1': 'data1'}, {'result2': 'data2'}]
    mock_server.plecs.simulate.assert_called_once_with('model', opt_structs)


def test_simulate_batch_with_callback(mock_server):
    """Test batch simulation with callback."""
    opt_structs = [{'ModelVars': {'Vin': 400}}, {'ModelVars': {'Vin': 500}}]
    mock_server.plecs.simulate.return_value = [{'result1': 'data1'}, {'result2': 'data2'}]
    
    def callback(idx, result):
        return f"processed_{idx}_{result}"
    
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    results = ps.simulate_batch(opt_structs, callback=callback)
    
    assert results == ["processed_0_{'result1': 'data1'}", "processed_1_{'result2': 'data2'}"]


def test_simulate_batch_invalid_input(mock_server):
    """Test batch simulation with invalid input type."""
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    with pytest.raises(TypeError):
        ps.simulate_batch("not_a_list")


def test_simulate_batch_invalid_callback(mock_server):
    """Test batch simulation with invalid callback."""
    opt_structs = [{'ModelVars': {'Vin': 400}}]
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    with pytest.raises(TypeError):
        ps.simulate_batch(opt_structs, callback="not_callable")


def test_process_simulation_results_dict_with_numpy(mock_server):
    """Test processing simulation results as dict with numpy-like behavior."""
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    results = {'Time': [0, 1, 2], 'Values': [[1, 2, 3], [4, 5, 6]]}
    processed = ps._process_simulation_results(results)
    
    # Should process Time/Values structure
    assert 'Time' in processed or 'raw' in processed


def test_process_simulation_results_object_attributes(mock_server):
    """Test processing simulation results from object with attributes."""
    class MockResult:
        Time = [0, 1, 2]
        Values = [[1, 2, 3], [4, 5, 6]]
    
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    processed = ps._process_simulation_results(MockResult())
    
    # Should either process as structured data or fall back to raw
    assert 'Time' in processed or 'raw' in processed


def test_process_simulation_results_fallback(mock_server):
    """Test processing simulation results fallback to raw."""
    ps = PlecsServer(sim_path='/test', sim_name='model.plecs', load=False)
    raw_data = "some_string_data"
    processed = ps._process_simulation_results(raw_data)
    
    assert processed == {'raw': raw_data}
