#!/usr/bin/env python3
"""Test script to validate the new PyPLECS foundational classes."""

import asyncio
import sys
from pathlib import Path

# Add the pyplecs directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyplecs.core.models import (
    SimulationStatus, SimulationType, NewSimulationResult,
    PLECSModel, PLECSApp, PLECSGUIApp, PLECSXRPCApp,
    SimulationPlan, PLECSSimulation, PLECSServer
)


async def test_foundational_classes():
    """Test the foundational PyPLECS classes."""
    print("Testing PyPLECS Foundational Classes...")
    
    # Test 1: PLECSModel creation
    print("\n1. Testing PLECSModel...")
    try:
        # Create a dummy model file for testing
        test_model_path = Path("test_model.plecs")
        test_model_path.write_text("# Dummy PLECS model for testing")
        
        model = PLECSModel(test_model_path)
        print(f"   ✓ Model created: {model.model_name}")
        print(f"   ✓ Model path: {model.filename}")
        print(f"   ✓ Folder: {model.folder}")
        
        # Test variable setting
        model.set_variables({"voltage": 12.0, "frequency": 50.0})
        vars_opts = model.get_model_vars_opts()
        print(f"   ✓ Variables set: {vars_opts}")
        
        # Clean up
        test_model_path.unlink()
        
    except Exception as e:
        print(f"   ✗ PLECSModel test failed: {e}")
    
    # Test 2: SimulationResult
    print("\n2. Testing NewSimulationResult...")
    try:
        result = NewSimulationResult(
            status=SimulationStatus.COMPLETED,
            data={"test": "data"},
            execution_time=1.5,
            metadata={"model": "test"}
        )
        print(f"   ✓ Result created: {result.status}")
        
        # Test conversion to legacy format
        legacy_result = result.to_legacy_result("test_task_123")
        print(f"   ✓ Legacy conversion: task_id={legacy_result.task_id}, success={legacy_result.success}")
        
    except Exception as e:
        print(f"   ✗ NewSimulationResult test failed: {e}")
    
    # Test 3: SimulationPlan
    print("\n3. Testing SimulationPlan...")
    try:
        # Create dummy model files
        model1_path = Path("model1.plecs")
        model2_path = Path("model2.plecs")
        model1_path.write_text("# Model 1")
        model2_path.write_text("# Model 2")
        
        model1 = PLECSModel(model1_path)
        model2 = PLECSModel(model2_path)
        
        plan = SimulationPlan(
            models=[model1],
            simulation_type=SimulationType.SEQUENTIAL
        )
        plan.add_model(model2)
        plan.set_parameter_sweep("voltage", [12.0, 15.0, 18.0])
        
        print(f"   ✓ Plan created with {len(plan.models)} models")
        print(f"   ✓ Simulation type: {plan.simulation_type}")
        print(f"   ✓ Parameter sweep: {plan.parameters}")
        
        # Clean up
        model1_path.unlink()
        model2_path.unlink()
        
    except Exception as e:
        print(f"   ✗ SimulationPlan test failed: {e}")
    
    # Test 4: PLECSServer basic functionality
    print("\n4. Testing PLECSServer...")
    try:
        config = {
            'apps': {
                'gui_app': {
                    'type': 'gui',
                    'executable_path': 'dummy_path.exe',
                    'high_priority': True
                },
                'xrpc_app': {
                    'type': 'xrpc', 
                    'executable_path': 'dummy_path.exe',
                    'port': 1080
                }
            }
        }
        
        server = PLECSServer(config)
        print(f"   ✓ Server created with config")
        print(f"   ✓ Available app configs: {list(config['apps'].keys())}")
        
        # Test app registration manually (without starting actual PLECS)
        dummy_app = PLECSGUIApp("dummy_path.exe")
        server.register_app("test_app", dummy_app)
        retrieved_app = server.get_app("test_app")
        
        if retrieved_app is dummy_app:
            print("   ✓ App registration and retrieval works")
        else:
            print("   ✗ App registration failed")
        
    except Exception as e:
        print(f"   ✗ PLECSServer test failed: {e}")
    
    print("\n✅ Foundational classes testing completed!")


if __name__ == "__main__":
    asyncio.run(test_foundational_classes())
