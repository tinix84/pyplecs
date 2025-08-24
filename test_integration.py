#!/usr/bin/env python3
"""Test integration between new OOP classes and existing PyPLECS functionality."""

import sys
from pathlib import Path

# Add the pyplecs directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyplecs.core import (
    PLECSModel, SimulationStatus, SimulationType,
    NewSimulationResult, SimulationRequest, SimulationResult
)


def test_backward_compatibility():
    """Test that new classes maintain backward compatibility."""
    print("Testing Backward Compatibility...")
    
    # Test 1: Legacy SimulationRequest still works
    print("\n1. Testing legacy SimulationRequest...")
    try:
        # Create dummy model file
        test_model = Path("legacy_test.plecs")
        test_model.write_text("# Legacy test model")
        
        request = SimulationRequest(
            model_file=str(test_model),
            parameters={"voltage": 12.0},
            simulation_time=1.0
        )
        print(f"   ✓ Legacy request created: {request.model_file}")
        print(f"   ✓ Parameters: {request.parameters}")
        
        # Clean up
        test_model.unlink()
        
    except Exception as e:
        print(f"   ✗ Legacy SimulationRequest failed: {e}")
    
    # Test 2: NewSimulationResult to legacy conversion
    print("\n2. Testing result conversion...")
    try:
        new_result = NewSimulationResult(
            status=SimulationStatus.COMPLETED,
            data={"timeseries": {"time": [0, 1], "voltage": [12, 15]}},
            execution_time=2.5,
            metadata={"model": "test_model"}
        )
        
        legacy_result = new_result.to_legacy_result("task_001")
        print(f"   ✓ New result: {new_result.status}")
        print(f"   ✓ Legacy result: success={legacy_result.success}, task_id={legacy_result.task_id}")
        print(f"   ✓ Execution time: {legacy_result.execution_time}")
        
    except Exception as e:
        print(f"   ✗ Result conversion failed: {e}")
    
    # Test 3: PLECSModel compatibility with existing code patterns
    print("\n3. Testing PLECSModel compatibility...")
    try:
        # Create dummy model file
        test_model = Path("compat_test.plecs") 
        test_model.write_text("# Compatibility test model")
        
        model = PLECSModel(test_model)
        
        # Test properties that existing code might expect
        print(f"   ✓ filename: {model.filename}")
        print(f"   ✓ folder: {model.folder}")
        print(f"   ✓ model_name: {model.model_name}")
        print(f"   ✓ simulation_name: {model.simulation_name}")
        
        # Test variable setting (new functionality)
        model.set_variables({"Vin": 400, "Vout": 200})
        opts = model.get_model_vars_opts()
        print(f"   ✓ ModelVars format: {opts}")
        
        # Clean up
        test_model.unlink()
        
    except Exception as e:
        print(f"   ✗ PLECSModel compatibility failed: {e}")
    
    print("\n✅ Backward compatibility testing completed!")


def test_integration_import():
    """Test that the core module exports work correctly."""
    print("\nTesting Module Integration...")
    
    try:
        from pyplecs.core import SimulationStatus, PLECSModel, PLECSServer
        print("   ✓ Core classes import successfully")
        
        # Test enum access
        status = SimulationStatus.PENDING
        print(f"   ✓ Enum access works: {status}")
        
        # Test class instantiation
        server_config = {'apps': {}}
        server = PLECSServer(server_config)
        print("   ✓ PLECSServer instantiation works")
        
    except Exception as e:
        print(f"   ✗ Module integration failed: {e}")
    
    print("✅ Module integration testing completed!")


if __name__ == "__main__":
    test_backward_compatibility()
    test_integration_import()
