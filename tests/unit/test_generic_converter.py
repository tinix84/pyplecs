import pytest
from pyplecs.pyplecs import GenericConverterPlecsMdl
from pathlib import Path
import tempfile


def test_repr_and_file_info():
    p = Path('data/simple_buck.plecs')
    assert p.exists(), "sample plecs file must exist for tests"
    mdl = GenericConverterPlecsMdl(str(p))
    # validate representation contains model name and file path
    r = repr(mdl)
    assert 'simple_buck' in r
    fi = mdl.get_file_info()
    assert fi['exists'] is True
    assert 'size' in fi


def test_load_modelvars_struct_from_plecs():
    p = Path('data/simple_buck.plecs')
    mdl = GenericConverterPlecsMdl(str(p))
    parsed = mdl.load_modelvars_struct_from_plecs()
    assert 'init_vars' in parsed
    assert isinstance(parsed['init_vars'], dict)
    # ensure optStruct was updated with ModelVars
    assert 'ModelVars' in mdl.optStruct
    assert isinstance(mdl.optStruct['ModelVars'], dict)


def test_init_properties():
    """Test GenericConverterPlecsMdl initialization and properties."""
    p = Path('data/simple_buck.plecs')
    mdl = GenericConverterPlecsMdl(str(p))
    
    assert mdl.filename == str(p)
    assert mdl.folder == str(p.parent)
    assert mdl.model_name == 'simple_buck'
    assert mdl.simulation_name == 'simple_buck.plecs'
    assert mdl._type == 'plecs'


def test_filename_setter():
    """Test setting filename property updates all internal paths."""
    mdl = GenericConverterPlecsMdl('test.plecs')
    new_path = 'data/simple_buck.plecs'
    mdl.filename = new_path
    
    assert Path(mdl.filename) == Path(new_path)
    assert mdl.model_name == 'simple_buck'
    assert mdl.simulation_name == 'simple_buck.plecs'


def test_validate_model_valid():
    """Test model validation with valid file."""
    p = Path('data/simple_buck.plecs')
    mdl = GenericConverterPlecsMdl(str(p))
    assert mdl.validate_model() is True


def test_validate_model_invalid():
    """Test model validation with non-existent file."""
    mdl = GenericConverterPlecsMdl('nonexistent.plecs')
    assert mdl.validate_model() is False


def test_validate_model_xml_extension():
    """Test model validation accepts XML extension."""
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
        tmp.write(b'<test>content</test>')
        tmp.flush()
        tmp_path = tmp.name
        
    mdl = GenericConverterPlecsMdl(tmp_path)
    assert mdl.validate_model() is True
    
    # Clean up
    try:
        Path(tmp_path).unlink()
    except (PermissionError, FileNotFoundError):
        pass  # Ignore cleanup errors in tests


def test_get_file_info_nonexistent():
    """Test get_file_info raises FileNotFoundError for missing file."""
    mdl = GenericConverterPlecsMdl('nonexistent.plecs')
    with pytest.raises(FileNotFoundError):
        mdl.get_file_info()


def test_load_modelvars_struct_file_not_found():
    """Test loading model vars from non-existent file."""
    mdl = GenericConverterPlecsMdl('nonexistent.plecs')
    with pytest.raises(FileNotFoundError):
        mdl.load_modelvars_struct_from_plecs()


def test_get_components():
    """Test getting components from model."""
    p = Path('data/simple_buck.plecs')
    mdl = GenericConverterPlecsMdl(str(p))
    components = mdl.get_components()
    assert isinstance(components, dict)


def test_get_parameters():
    """Test getting flattened parameters from model."""
    p = Path('data/simple_buck.plecs')
    mdl = GenericConverterPlecsMdl(str(p))
    params = mdl.get_parameters()
    assert isinstance(params, dict)


def test_set_default_model_vars():
    """Test default model variables setup."""
    mdl = GenericConverterPlecsMdl('test.plecs')
    defaults = mdl.set_default_model_vars()
    
    assert 'ModelVars' in defaults
    assert 'Vi' in defaults['ModelVars']
    assert 'Vo' in defaults['ModelVars']
    assert isinstance(defaults['ModelVars']['Vi'], float)
    assert isinstance(defaults['ModelVars']['Vo'], float)


def test_repr_fallback():
    """Test __repr__ fallback when file doesn't exist."""
    mdl = GenericConverterPlecsMdl('nonexistent.plecs')
    r = repr(mdl)
    assert 'GenericConverterPlecsMdl' in r
