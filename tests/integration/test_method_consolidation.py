"""Integration tests for method consolidation and standardization."""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch

from pyplecs.pyplecs import PlecsServer
from pyplecs.exceptions import FileLoadError


class TestMethodConsolidation:
    """Test the consolidated load_model_vars method."""

    def test_load_model_vars_dict_input(self):
        """Test loading model vars from dictionary."""
        server = PlecsServer('test_path', 'test_model.plecs', load=False)
        
        # Test with bare dictionary
        vars_dict = {'Vin': 400, 'Vout': 200, 'Pout': 1000}
        result = server.load_model_vars(vars_dict)
        
        assert 'ModelVars' in result
        assert result['ModelVars']['Vin'] == 400.0
        assert result['ModelVars']['Vout'] == 200.0
        assert result['ModelVars']['Pout'] == 1000.0

    def test_load_model_vars_with_modelvars_key(self):
        """Test loading model vars with existing ModelVars key."""
        server = PlecsServer('test_path', 'test_model.plecs', load=False)
        
        # Test with ModelVars wrapper
        vars_dict = {'ModelVars': {'Vin': 400, 'Vout': 200}}
        result = server.load_model_vars(vars_dict)
        
        assert 'ModelVars' in result
        assert result['ModelVars']['Vin'] == 400.0
        assert result['ModelVars']['Vout'] == 200.0

    def test_load_model_vars_merge_behavior(self):
        """Test merge vs replace behavior."""
        server = PlecsServer('test_path', 'test_model.plecs', load=False)
        
        # Set initial variables
        server.optStruct = {'ModelVars': {'Vin': 300, 'fsw': 20000}}
        
        # Test merge=True (default)
        new_vars = {'Vin': 400, 'Vout': 200}
        result = server.load_model_vars(new_vars, merge=True)
        
        assert result['ModelVars']['Vin'] == 400.0  # Updated
        assert result['ModelVars']['Vout'] == 200.0  # Added
        assert result['ModelVars']['fsw'] == 20000.0  # Preserved
        
        # Test merge=False
        result = server.load_model_vars(new_vars, merge=False)
        
        assert result['ModelVars']['Vin'] == 400.0
        assert result['ModelVars']['Vout'] == 200.0
        assert 'fsw' not in result['ModelVars']  # Not preserved

    def test_load_model_vars_coercion(self):
        """Test type coercion behavior."""
        server = PlecsServer('test_path', 'test_model.plecs', load=False)
        
        # Test with mixed types
        vars_dict = {
            'int_val': 42,
            'float_val': 3.14,
            'str_numeric': '123.45',
            'str_expression': 'sin(2*pi*t)'
        }
        
        result = server.load_model_vars(vars_dict, coerce=True)
        
        assert result['ModelVars']['int_val'] == 42.0
        assert result['ModelVars']['float_val'] == 3.14
        assert result['ModelVars']['str_numeric'] == 123.45
        # Kept as string
        assert result['ModelVars']['str_expression'] == 'sin(2*pi*t)'

    def test_load_model_vars_mat_file(self):
        """Test loading from .mat file."""
        server = PlecsServer('test_path', 'test_model.plecs', load=False)
        
        # Mock the load_mat_file function
        with patch('pyplecs.pyplecs.load_mat_file') as mock_load:
            mock_load.return_value = {'Vin': 400, 'Vout': 200}
            
            result = server.load_model_vars('test_vars.mat')
            
            mock_load.assert_called_once_with('test_vars.mat')
            assert result['ModelVars']['Vin'] == 400.0
            assert result['ModelVars']['Vout'] == 200.0

    def test_load_model_vars_yaml_file(self):
        """Test loading from YAML file."""
        server = PlecsServer('test_path', 'test_model.plecs', load=False)
        
        # Mock the _load_yaml_vars method
        server._load_yaml_vars = Mock(return_value={'Vin': 400, 'Vout': 200})
        
        result = server.load_model_vars('test_vars.yml')
        
        server._load_yaml_vars.assert_called_once_with('test_vars.yml')
        assert result['ModelVars']['Vin'] == 400.0
        assert result['ModelVars']['Vout'] == 200.0

    def test_load_model_vars_unsupported_file(self):
        """Test error handling for unsupported file types."""
        server = PlecsServer('test_path', 'test_model.plecs', load=False)
        
        with pytest.raises(ValueError, match="Unsupported file type"):
            server.load_model_vars('test_vars.txt')

    def test_load_model_vars_invalid_type(self):
        """Test error handling for invalid input types."""
        server = PlecsServer('test_path', 'test_model.plecs', load=False)
        
        with pytest.raises(TypeError,
                           match="must be dict, file path string, or None"):
            server.load_model_vars(123)  # type: ignore

    def test_load_modelvars_deprecation_warning(self):
        """Test that old method shows deprecation warning."""
        server = PlecsServer('test_path', 'test_model.plecs', load=False)

        with pytest.warns(DeprecationWarning,
                          match="load_modelvars.*deprecated"):
            server.load_modelvars({'Vin': 400})


class TestYamlLoader:
    """Test YAML file loading functionality."""

    def test_load_yaml_vars_success(self):
        """Test successful YAML loading."""
        server = PlecsServer('test_path', 'test_model.plecs', load=False)
        
        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml',
                                        delete=False) as f:
            f.write("Vin: 400\nVout: 200\nPout: 1000\n")
            yaml_file = f.name
        
        try:
            with patch('builtins.open', mock_open_yaml()):
                with patch('yaml.safe_load') as mock_yaml:
                    mock_yaml.return_value = {'Vin': 400, 'Vout': 200}
                    
                    result = server._load_yaml_vars(yaml_file)
                    
                    assert result == {'Vin': 400, 'Vout': 200}
        finally:
            os.unlink(yaml_file)

    def test_load_yaml_vars_missing_yaml(self):
        """Test error when PyYAML is not available."""
        server = PlecsServer('test_path', 'test_model.plecs', load=False)
        
        with patch('builtins.__import__', side_effect=ImportError("No module named 'yaml'")):
            with pytest.raises(ImportError, match="PyYAML required"):
                server._load_yaml_vars('test.yml')

    def test_load_yaml_vars_file_error(self):
        """Test error handling for file I/O errors."""
        server = PlecsServer('test_path', 'test_model.plecs', load=False)
        
        with patch('builtins.open', side_effect=IOError("File not found")):
            with pytest.raises(FileLoadError, match="Failed to load YAML file"):
                server._load_yaml_vars('nonexistent.yml')


class TestResultStandardization:
    """Test standardized return value formats."""

    def test_consistent_return_format(self):
        """Test that all methods return consistent formats."""
        server = PlecsServer('test_path', 'test_model.plecs', load=False)
        
        # All variable loading methods should return the same format
        vars_dict = {'Vin': 400, 'Vout': 200}
        
        result1 = server.load_model_vars(vars_dict)
        
        # Check format consistency
        assert isinstance(result1, dict)
        assert 'ModelVars' in result1
        assert isinstance(result1['ModelVars'], dict)
        
        # All numeric values should be floats for XML-RPC compatibility
        for key, value in result1['ModelVars'].items():
            if isinstance(value, (int, float)):
                assert isinstance(value, float)

    def test_return_value_validation(self):
        """Test that return values are properly validated."""
        server = PlecsServer('test_path', 'test_model.plecs', load=False)
        
        # Test with None input
        result = server.load_model_vars(None)
        assert isinstance(result, dict)
        
        # Test with empty dict
        result = server.load_model_vars({})
        assert 'ModelVars' in result
        assert isinstance(result['ModelVars'], dict)


def mock_open_yaml():
    """Mock open for YAML testing."""
    from unittest.mock import mock_open
    return mock_open(read_data="Vin: 400\nVout: 200\n")


if __name__ == '__main__':
    pytest.main([__file__])
