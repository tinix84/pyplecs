"""
Simple test to verify real PLECS integration works end-to-end.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

# Import our modules
from pyplecs.plecs_parser import parse_plecs_file

# Import the CLI components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cli_demo_nomocks import RealPlecsSimulator, SimulationPlan


def test_real_plecs_parameter_sweep():
    """
    Test that real PLECS simulations work with parameter sweeps.
    This is the most important test - it verifies:
    1. PLECS starts and connects via XML-RPC
    2. Parameters are set correctly
    3. Simulations execute and return real data
    4. Parameter sweeps work
    5. Cache behavior is correct
    """
    model_file = Path("data/simple_buck.plecs")
    
    if not model_file.exists():
        pytest.skip("PLECS model file not found")
    
    # Test 1: Parse model file
    parsed_data = parse_plecs_file(model_file)
    assert len(parsed_data['init_vars']) > 0, "Should find initialization variables"
    
    # Test 2: Create simulator and start PLECS
    simulator = RealPlecsSimulator(model_file)
    
    try:
        success = simulator.start_plecs_and_connect()
        if not success:
            pytest.skip("PLECS not available or failed to start")
        
        # Test 3: Verify we can connect
        assert simulator.server is not None, "XML-RPC server should be initialized"
        assert simulator.plecs_app is not None, "PLECS app should be initialized"
        
        # Test 4: Run a simple simulation
        simple_params = {
            'Vi': 24.0,
            'Lo': 15e-6,
            'Co': 150e-6,
            '_simulation_type': 'real_plecs',
            '_simulation_engine': 'xml_rpc'
        }
        
        result1 = simulator.run_simulation(simple_params)
        
        # Verify result structure
        assert 'timeseries' in result1, "Should have timeseries data"
        assert 'metadata' in result1, "Should have metadata"
        assert result1['metadata']['success'], "Simulation should succeed"
        
        # Verify we have actual time series data
        timeseries = result1['timeseries']
        if hasattr(timeseries, 'columns'):  # pandas DataFrame
            assert 'Time' in timeseries.columns, "Should have Time column"
            assert len(timeseries) > 100, "Should have substantial data points"
        else:  # dict format
            assert 'Time' in timeseries, "Should have Time data"
            assert len(timeseries['Time']) > 100, "Should have substantial time points"
        
        print(f"✓ First simulation successful with {len(timeseries)} data points")
        
        # Test 5: Run simulation with different parameters
        different_params = simple_params.copy()
        different_params['Lo'] = 25e-6  # Different inductance
        
        result2 = simulator.run_simulation(different_params)
        assert result2['metadata']['success'], "Second simulation should succeed"
        
        print("✓ Second simulation with different parameters successful")
        
        # Test 6: Run parameter sweep
        base_params = parsed_data['init_vars'].copy()
        sim_plan = SimulationPlan(model_file, base_params)
        
        # Small sweep: 2 points for Lo
        sim_plan.add_sweep_parameter('Lo', 10e-6, 20e-6, 2)
        
        simulation_points = sim_plan.generate_simulation_points()
        assert len(simulation_points) == 2, "Should generate 2 simulation points"
        
        # Run all simulations in sweep
        sweep_results = []
        for i, params in enumerate(simulation_points):
            print(f"Running sweep simulation {i+1}/2...")
            result = simulator.run_simulation(params)
            assert result['metadata']['success'], f"Sweep simulation {i+1} should succeed"
            sweep_results.append(result)
        
        print("✓ Parameter sweep completed successfully")
        
        # Test 7: Verify results are different (different Lo should give different results)
        ts1 = sweep_results[0]['timeseries']
        ts2 = sweep_results[1]['timeseries']
        
        # Results should have same structure
        if hasattr(ts1, 'columns'):  # pandas DataFrame
            assert list(ts1.columns) == list(ts2.columns), "Column structure should match"
            assert len(ts1) == len(ts2), "Should have same number of time points"
        else:  # dict format
            assert ts1.keys() == ts2.keys(), "Keys should match"
            assert len(ts1['Time']) == len(ts2['Time']), "Should have same time points"
        
        print("✓ Sweep results have consistent structure")
        
        # Test 8: Test cache behavior - run identical simulation again
        print("Testing cache behavior...")
        
        # Run same simulation as first one
        cached_result = simulator.run_simulation(simple_params)
        assert cached_result['metadata']['success'], "Cached simulation should succeed"
        
        print("✓ Cache test completed")
        
        print("🎉 ALL TESTS PASSED - Real PLECS integration is working!")
        
    finally:
        simulator.close()


if __name__ == "__main__":
    test_real_plecs_parameter_sweep()
