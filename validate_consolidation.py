"""Simple validation script for method consolidation."""

from pyplecs.pyplecs import PlecsServer
import warnings

def test_load_model_vars_consolidation():
    """Test that the new unified load_model_vars method works."""
    print("Testing unified load_model_vars method...")
    
    # Create server without loading PLECS
    server = PlecsServer('data', 'simple_buck.plecs', load=False)
    
    # Test 1: Basic dictionary loading
    print("Test 1: Basic dictionary loading")
    vars_dict = {'Vin': 400, 'Vout': 200, 'Pout': 1000}
    result = server.load_model_vars(vars_dict)
    
    print(f"Result: {result}")
    assert 'ModelVars' in result
    assert result['ModelVars']['Vin'] == 400.0
    assert result['ModelVars']['Vout'] == 200.0
    print("✓ Basic dictionary loading works")
    
    # Test 2: Merge behavior
    print("\nTest 2: Merge behavior")
    new_vars = {'Vin': 450, 'Iout': 5}  # Update Vin, add Iout
    result = server.load_model_vars(new_vars, merge=True)
    
    print(f"Result: {result}")
    assert result['ModelVars']['Vin'] == 450.0  # Updated
    assert result['ModelVars']['Vout'] == 200.0  # Preserved
    assert result['ModelVars']['Iout'] == 5.0    # Added
    print("✓ Merge behavior works")
    
    # Test 3: Deprecation warning for old method
    print("\nTest 3: Deprecation warning")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        server.load_modelvars({'test': 123})
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "deprecated" in str(w[0].message)
    print("✓ Deprecation warning works")
    
    # Test 4: Type coercion
    print("\nTest 4: Type coercion")
    mixed_vars = {
        'int_val': 42,
        'float_val': 3.14,
        'str_numeric': '123.45',
        'str_expression': 'sin(t)'
    }
    result = server.load_model_vars(mixed_vars, merge=False)
    
    print(f"Result: {result}")
    assert isinstance(result['ModelVars']['int_val'], float)
    assert isinstance(result['ModelVars']['float_val'], float)
    assert isinstance(result['ModelVars']['str_numeric'], float)
    assert isinstance(result['ModelVars']['str_expression'], str)
    print("✓ Type coercion works")
    
    print("\n🎉 All method consolidation tests passed!")

def test_model_info_methods():
    """Test the new model information methods."""
    print("\nTesting model information methods...")
    
    from pyplecs.pyplecs import GenericConverterPlecsMdl
    
    # Create model object
    mdl = GenericConverterPlecsMdl('data/simple_buck.plecs')
    
    # Test __repr__ method
    print("Test: __repr__ method")
    repr_str = repr(mdl)
    print(f"Repr: {repr_str}")
    assert 'GenericConverterPlecsMdl' in repr_str
    assert 'simple_buck' in repr_str
    print("✓ __repr__ method works")
    
    # Test get_model_info method
    print("\nTest: get_model_info method")
    info = mdl.get_model_info()
    print(f"Model info: {info}")
    
    assert 'name' in info
    assert 'file_path' in info
    assert 'type' in info
    assert 'folder' in info
    assert 'model_vars' in info
    assert info['name'] == 'simple_buck'
    assert info['type'] == 'plecs'
    print("✓ get_model_info method works")
    
    print("\n🎉 All model info tests passed!")

if __name__ == '__main__':
    test_load_model_vars_consolidation()
    test_model_info_methods()
    print("\n✅ All validation tests completed successfully!")
