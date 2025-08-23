import pytest
from unittest.mock import Mock, patch, MagicMock
import psutil
import subprocess
from pathlib import Path

from pyplecs.pyplecs import PlecsApp, PlecsConnectionError


@pytest.fixture
def mock_config_manager():
    """Mock ConfigManager for testing."""
    config = Mock()
    config.plecs.executable_paths = [r"C:\PLECS\PLECS.exe"]
    config.plecs.fallback_paths = [r"C:\Program Files\PLECS\PLECS.exe"]
    config.plecs.rpc_port = 1080
    return config


def test_plecs_app_init_finds_executable(monkeypatch, mock_config_manager):
    """Test PlecsApp initialization finds PLECS executable."""
    # Mock Path.exists to return True for first path
    def mock_exists(self):
        return str(self) == r"C:\PLECS\PLECS.exe"
    
    monkeypatch.setattr(Path, 'exists', mock_exists)
    monkeypatch.setattr('pyplecs.pyplecs.ConfigManager', lambda x: mock_config_manager)
    
    app = PlecsApp()
    assert app.command == r"C:\PLECS\PLECS.exe"


def test_plecs_app_init_fallback_path(monkeypatch, mock_config_manager):
    """Test PlecsApp uses fallback paths when primary paths don't exist."""
    mock_config_manager.plecs.executable_paths = []
    
    def mock_exists(self):
        return str(self) == r"C:\Program Files\PLECS\PLECS.exe"
    
    monkeypatch.setattr(Path, 'exists', mock_exists)
    monkeypatch.setattr('pyplecs.pyplecs.ConfigManager', lambda x: mock_config_manager)
    
    app = PlecsApp()
    assert app.command == r"C:\Program Files\PLECS\PLECS.exe"


def test_plecs_app_init_uses_which(monkeypatch, mock_config_manager):
    """Test PlecsApp uses shutil.which as last resort."""
    mock_config_manager.plecs.executable_paths = []
    mock_config_manager.plecs.fallback_paths = []
    
    monkeypatch.setattr(Path, 'exists', lambda self: False)
    monkeypatch.setattr('pyplecs.pyplecs.ConfigManager', lambda x: mock_config_manager)
    monkeypatch.setattr('shutil.which', lambda x: r"C:\Windows\PLECS.exe" if x == "PLECS.exe" else None)
    
    app = PlecsApp()
    assert app.command == r"C:\Windows\PLECS.exe"


def test_plecs_app_init_not_found(monkeypatch, mock_config_manager):
    """Test PlecsApp raises FileNotFoundError when PLECS not found."""
    mock_config_manager.plecs.executable_paths = []
    mock_config_manager.plecs.fallback_paths = []
    
    monkeypatch.setattr(Path, 'exists', lambda self: False)
    monkeypatch.setattr('pyplecs.pyplecs.ConfigManager', lambda x: mock_config_manager)
    monkeypatch.setattr('shutil.which', lambda x: None)
    
    with pytest.raises(FileNotFoundError):
        PlecsApp()


def test_set_plecs_high_priority(monkeypatch):
    """Test setting PLECS process to high priority."""
    mock_process = Mock()
    mock_process.info = {"name": "PLECS.exe"}
    mock_process.pid = 1234
    
    mock_proc_obj = Mock()
    monkeypatch.setattr('psutil.process_iter', lambda attrs: [mock_process])
    monkeypatch.setattr('psutil.Process', lambda pid: mock_proc_obj)
    monkeypatch.setattr('psutil.HIGH_PRIORITY_CLASS', 128)
    
    app = PlecsApp()
    app.set_plecs_high_priority()
    
    mock_proc_obj.nice.assert_called_once_with(128)


def test_open_plecs(monkeypatch):
    """Test opening PLECS process."""
    mock_popen = Mock()
    mock_popen.pid = 5678
    monkeypatch.setattr('subprocess.Popen', lambda args, **kwargs: mock_popen)
    monkeypatch.setattr('psutil.ABOVE_NORMAL_PRIORITY_CLASS', 32768)
    
    app = PlecsApp()
    app.open_plecs()
    # No exception should be raised


def test_kill_plecs(monkeypatch):
    """Test killing PLECS processes."""
    mock_process = Mock()
    mock_process.info = {"name": "PLECS.exe"}
    
    monkeypatch.setattr('psutil.process_iter', lambda attrs: [mock_process])
    
    app = PlecsApp()
    app.kill_plecs()
    
    mock_process.kill.assert_called_once()


def test_kill_plecs_no_such_process(monkeypatch):
    """Test killing PLECS when process doesn't exist."""
    mock_process = Mock()
    mock_process.info = {"name": "PLECS.exe"}
    mock_process.kill.side_effect = psutil.NoSuchProcess(1234)
    
    monkeypatch.setattr('psutil.process_iter', lambda attrs: [mock_process])
    
    app = PlecsApp()
    app.kill_plecs()  # Should not raise exception


def test_get_plecs_cpu(monkeypatch):
    """Test getting PLECS CPU usage."""
    mock_process1 = Mock()
    mock_process1.info = {"name": "PLECS.exe"}
    mock_process1.cpu_percent.return_value = 25.5
    
    mock_process2 = Mock()
    mock_process2.info = {"name": "PLECS.exe"}
    mock_process2.cpu_percent.return_value = 15.2
    
    monkeypatch.setattr('psutil.process_iter', lambda attrs: [mock_process1, mock_process2])
    
    app = PlecsApp()
    cpu_usage = app.get_plecs_cpu()
    
    # Should return max CPU usage among PLECS processes
    assert cpu_usage in [25.5, 15.2]


def test_run_simulation_by_gui_not_implemented():
    """Test that GUI simulation raises NotImplementedError."""
    app = PlecsApp()
    with pytest.raises(NotImplementedError):
        app.run_simulation_by_gui(None)


def test_load_file_gui_mode_not_implemented():
    """Test that GUI mode for load_file raises NotImplementedError."""
    app = PlecsApp()
    with pytest.raises(NotImplementedError):
        app.load_file(None, mode='gui')


@patch('pyplecs.pyplecs.PlecsServer')
def test_load_file_xmlrpc_mode(mock_plecs_server):
    """Test loading file in XML-RPC mode."""
    mock_model = Mock()
    mock_model.folder = '/test'
    mock_model.simulation_name = 'test.plecs'
    
    app = PlecsApp()
    result = app.load_file(mock_model, mode='XML-RPC')
    
    mock_plecs_server.assert_called_once_with('/test', 'test.plecs', load=True)
    assert result is None


def test_load_file_invalid_mode():
    """Test that invalid mode raises exception."""
    app = PlecsApp()
    with pytest.raises(Exception):
        app.load_file(None, mode='invalid')


@patch('xmlrpc.client.Server')
def test_check_if_simulation_running_with_status(mock_server_class):
    """Test checking simulation status using server status method."""
    mock_server = Mock()
    mock_server.plecs.status.return_value = {'running': True}
    mock_server_class.return_value = mock_server
    
    app = PlecsApp()
    result = app.check_if_simulation_running(None)
    
    assert result['running'] is True
    assert result['server_available'] is True


@patch('xmlrpc.client.Server')
def test_check_if_simulation_running_rpc_error_with_process(mock_server_class):
    """Test simulation check falling back to process scan when RPC fails."""
    mock_server_class.side_effect = Exception("Connection failed")
    
    mock_process = Mock()
    mock_process.info = {"name": "PLECS.exe"}
    
    with patch('psutil.process_iter', return_value=[mock_process]):
        app = PlecsApp()
        with pytest.raises(PlecsConnectionError):
            app.check_if_simulation_running(None)


@patch('xmlrpc.client.Server')
def test_check_if_simulation_running_no_process(mock_server_class):
    """Test simulation check when no RPC and no process found."""
    mock_server_class.side_effect = Exception("Connection failed")
    
    with patch('psutil.process_iter', return_value=[]):
        app = PlecsApp()
        with pytest.raises(PlecsConnectionError):
            app.check_if_simulation_running(None)
