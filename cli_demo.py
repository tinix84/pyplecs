#!/usr/bin/env python3
"""
PyPLECS End-to-End CLI Workflow Demo

This script demonstrates the complete workflow:
1. Parse PLECS file structure from data/simple_buck.plecs
2. Interactive parameter sweep setup
3. Simulation plan creation
4. Cached simulation execution
5. Result collection and storage
6. Interactive simulation result viewer
"""

import sys
import time
import random
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path for imports first
sys.path.insert(0, str(Path(__file__).parent))

# Import PyPLECS modules
from pyplecs.plecs_parser import parse_plecs_file, plecs_overview
from pyplecs.cache import SimulationCache
from tests.test_end_to_end_cli import SimulationPlan, SimulationViewer

# Check for optional dependencies
HAS_NUMPY_PANDAS = False
try:
    import numpy as np
    import pandas as pd
    HAS_NUMPY_PANDAS = True
except ImportError:
    print("Warning: numpy/pandas not available. Limited functionality.")


def get_user_input(prompt: str, default: str = None) -> str:
    """Get user input with optional default value."""
    if default:
        response = input(f"{prompt} [{default}]: ").strip()
        return response if response else default
    return input(f"{prompt}: ").strip()


def get_float_input(prompt: str, default: float = None) -> float:
    """Get float input from user."""
    while True:
        try:
            if default is not None:
                response = input(f"{prompt} [{default}]: ").strip()
                if not response:
                    return default
                return float(response)
            else:
                return float(input(f"{prompt}: "))
        except ValueError:
            print("Please enter a valid number.")


def get_int_input(prompt: str, default: int = None) -> int:
    """Get integer input from user."""
    while True:
        try:
            if default is not None:
                response = input(f"{prompt} [{default}]: ").strip()
                if not response:
                    return default
                return int(response)
            else:
                return int(input(f"{prompt}: "))
        except ValueError:
            print("Please enter a valid integer.")


def mock_simulation_execution(parameters: Dict[str, Any],
                              model_file: str) -> Dict[str, Any]:
    """Mock simulation execution for demonstration."""
    print(f"    Simulating with parameters: {parameters}")
    time.sleep(0.5)  # Simulate simulation time
    
    if not HAS_NUMPY_PANDAS:
        # Simple mock without numpy/pandas
        return {
            'timeseries': {
                'Time': [0.0, 0.5, 1.0],
                'Vi': [parameters.get('Vi', 100)] * 3,
                'Vo': [parameters.get('Vo_ref', 20)] * 3,
                'Ii': [random.uniform(1, 5) for _ in range(3)],
                'Io': [random.uniform(0.5, 2) for _ in range(3)]
            },
            'metadata': {
                'parameters': parameters,
                'simulation_time': 1.0,
                'success': True,
                'timestamp': time.time(),
                'model_file': model_file
            }
        }    # Generate mock timeseries data with numpy/pandas
    time_vec = np.linspace(0, 1, 100)
    
    # Create mock waveforms based on parameters
    vi = parameters.get('Vi', 100)
    vo_ref = parameters.get('Vo_ref', 20)
    
    # Add some noise to make it more realistic
    noise_scale = 0.05
    
    vo_waveform = (vo_ref * (1 - np.exp(-time_vec/0.1)) *
                   (1 + noise_scale * np.random.randn(100)))
    mock_data = {
        'Time': time_vec,
        'Vi': vi * (1 + noise_scale * np.random.randn(100)),
        'Vo': vo_waveform,
        'Ii': (vi / 10) * (1 + noise_scale * np.random.randn(100)),
        'Io': (vo_ref / 5) * (1 + noise_scale * np.random.randn(100))
    }
    
    timeseries_df = pd.DataFrame(mock_data)
    
    metadata = {
        'parameters': parameters,
        'simulation_time': 1.0,
        'success': True,
        'timestamp': time.time(),
        'model_file': model_file
    }
    
    return {
        'timeseries': timeseries_df,
        'metadata': metadata
    }


def interactive_parameter_sweep_setup(
        available_vars: List[str]) -> List[Dict[str, Any]]:
    """Interactive setup of parameter sweeps."""
    print("\n=== Parameter Sweep Setup ===")
    print(f"Available variables: {', '.join(available_vars)}")
    
    sweep_configs = []
    
    while True:
        param_name = get_user_input(
            "\nEnter parameter name to sweep (or 'done' to finish)",
            "done"
        )
        
        if param_name.lower() == 'done' or not param_name:
            break
            
        if param_name not in available_vars:
            print(f"Warning: '{param_name}' not found in available variables.")
            continue_anyway = get_user_input(
                "Continue anyway? (y/n)", "n"
            ).lower()
            if continue_anyway != 'y':
                continue
        
        min_val = get_float_input(f"Minimum value for {param_name}")
        max_val = get_float_input(f"Maximum value for {param_name}")
        n_points = get_int_input(f"Number of points for {param_name}", 3)
        
        if min_val >= max_val:
            print("Error: Minimum value must be less than maximum value.")
            continue
        
        if n_points < 2:
            print("Error: Number of points must be at least 2.")
            continue
        
        sweep_config = {
            'parameter': param_name,
            'min_value': min_val,
            'max_value': max_val,
            'n_points': n_points
        }
        
        sweep_configs.append(sweep_config)
        print(f"Added sweep: {param_name} from {min_val} to "
              f"{max_val} with {n_points} points")
    
    return sweep_configs


def interactive_result_viewer(results_data: List[Dict[str, Any]]):
    """Interactive viewer for simulation results."""
    if not results_data:
        print("No simulation results to view.")
        return
    
    if not HAS_NUMPY_PANDAS:
        print("\nSimulation Results (Limited View - "
              "numpy/pandas not available):")
        for i, result in enumerate(results_data):
            print(f"\nSimulation {i+1}:")
            print(f"  Parameters: {result['metadata']['parameters']}")
            print(f"  Success: {result['metadata']['success']}")
            if 'timeseries' in result:
                ts = result['timeseries']
                if isinstance(ts, dict):
                    print(f"  Variables: {list(ts.keys())}")
        return
    
    viewer = SimulationViewer(results_data)
    available_vars = viewer.list_available_variables()
    
    print("\n=== Simulation Result Viewer ===")
    print(f"Found {len(results_data)} simulation results")
    print(f"Available variables: {', '.join(available_vars)}")
    
    while True:
        print("\nOptions:")
        print("1. View summary statistics for a variable")
        print("2. Plot variable vs time")
        print("3. List all simulations")
        print("4. Exit viewer")
        
        choice = get_user_input("Choose option (1-4)", "4")
        
        if choice == "1":
            if not available_vars:
                print("No variables available for analysis.")
                continue
                
            print(f"\nAvailable variables: {', '.join(available_vars)}")
            var_name = get_user_input("Variable name")
            
            if var_name in available_vars:
                stats = viewer.summary_statistics(var_name)
                print(f"\nSummary statistics for {var_name}:")
                print(stats.to_string(index=False))
            else:
                print(f"Variable '{var_name}' not found.")
        
        elif choice == "2":
            if not available_vars:
                print("No variables available for plotting.")
                continue
                
            print(f"\nAvailable variables: {', '.join(available_vars)}")
            var_name = get_user_input("Variable name to plot")
            
            if var_name in available_vars:
                try:
                    fig = viewer.plot_variable(var_name)
                    if fig:
                        print(f"Plot created for {var_name}. "
                              "Close plot window to continue.")
                        import matplotlib.pyplot as plt
                        plt.show()
                except ImportError:
                    print("Matplotlib not available for plotting.")
            else:
                print(f"Variable '{var_name}' not found.")
        
        elif choice == "3":
            print(f"\nSimulation Results ({len(results_data)} total):")
            for i, result in enumerate(results_data):
                params = result['metadata']['parameters']
                print(f"  {i+1}. {params}")
        
        elif choice == "4" or choice.lower() == 'exit':
            break
        
        else:
            print("Invalid option. Please choose 1-4.")


def main():
    """Main workflow function."""
    print("=" * 60)
    print("PyPLECS End-to-End CLI Workflow")
    print("=" * 60)
    
    # Step 1: Parse PLECS file structure
    print("\n=== Step 1: Parsing PLECS file ===")
    model_file = "data/simple_buck.plecs"
    
    if not Path(model_file).exists():
        print(f"Error: Model file '{model_file}' not found.")
        print("Please ensure the file exists and try again.")
        return 1
    
    try:
        parsed_data = parse_plecs_file(model_file)
        # Remove unused overview variable
        plecs_overview(model_file)
        
        print(f"✓ Parsed file: {parsed_data['file']}")
        print(f"✓ Found {len(parsed_data['components'])} components")
        print(f"✓ Found {len(parsed_data['init_vars'])} "
              "initialization variables")
        
        available_vars = list(parsed_data['init_vars'].keys())
        print(f"Available variables: {', '.join(available_vars)}")
        
    except (FileNotFoundError, IOError, OSError) as e:
        print(f"Error parsing PLECS file: {e}")
        return 1
    
    # Step 2: Interactive parameter sweep setup
    sweep_configs = interactive_parameter_sweep_setup(available_vars)
    
    if not sweep_configs:
        print("No parameter sweeps configured. Exiting.")
        return 0
    
    # Step 3: Create simulation plan
    print("\n=== Step 3: Creating simulation plan ===")
    base_params = parsed_data['init_vars'].copy()
    sim_plan = SimulationPlan(model_file, base_params)
    
    for config in sweep_configs:
        sim_plan.add_sweep_parameter(
            config['parameter'],
            config['min_value'],
            config['max_value'],
            config['n_points']
        )
    
    simulation_points = sim_plan.generate_simulation_points()
    total_sims = len(simulation_points)
    
    print(f"✓ Generated {total_sims} simulation points")
    
    # Save simulation plan
    metadata_dir = Path('./cli_metadata')
    metadata_dir.mkdir(exist_ok=True)
    plan_file = metadata_dir / 'simulation_plan.json'
    sim_plan.save_to_file(str(plan_file))
    print(f"✓ Saved simulation plan to {plan_file}")
    
    # Step 4: Execute simulations with caching
    print(f"\n=== Step 4: Executing {total_sims} simulations ===")
    
    # Initialize cache
    cache = SimulationCache()
    results_data = []
    
    # Ask if user wants to run all simulations
    if total_sims > 5:
        run_all = get_user_input(
            f"Run all {total_sims} simulations? (y/n)", "n"
        ).lower()
        if run_all != 'y':
            max_sims = get_int_input("Maximum simulations to run", 5)
            simulation_points = simulation_points[:max_sims]
    
    for i, params in enumerate(simulation_points):
        print(f"\nRunning simulation {i+1}/{len(simulation_points)}")
        
        # Check cache first
        cached_result = cache.get_cached_result(model_file, params)
        
        if cached_result:
            print("  ✓ Using cached result")
            results_data.append(cached_result)
        else:
            print("  ⚙ Running new simulation...")
            
            try:
                # Mock simulation execution
                mock_result = mock_simulation_execution(params, model_file)
                
                # Store in cache
                cache.cache_result(
                    model_file,
                    params,
                    mock_result['timeseries'],
                    mock_result['metadata']
                )
                
                results_data.append(mock_result)
                print("  ✓ Simulation completed and cached")
                
            except (RuntimeError, ValueError) as e:
                print(f"  ✗ Simulation failed: {e}")
                continue
    
    print(f"\n✓ Completed {len(results_data)} simulations")
    
    # Step 5: Interactive result viewer
    print("\n=== Step 5: Interactive Result Viewer ===")
    interactive_result_viewer(results_data)
    
    print("\n" + "=" * 60)
    print("Workflow completed successfully!")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
