#!/usr/bin/env python3
"""
PyPLECS End-to-End CLI Workflow Demo (No Mocks)

This script demonstrates the complete workflow with real PLECS simulation:
1. Parse PLECS file structure from data/simple_buck.plecs
2. Start PLECS application automatically and connect via XML-RPC
3. Interactive parameter sweep setup using parsed initialization variables
4. Simulation plan creation
5. Real PLECS simulation execution via XML-RPC
6. Result collection and storage
7. Interactive simulation result viewer

Requirements:
- PLECS Standalone installed and accessible
- XML-RPC will be enabled automatically (default port 1080)
- PLECS will be started automatically by this script
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path for imports first
sys.path.insert(0, str(Path(__file__).parent))

# Import PyPLECS modules
from pyplecs.plecs_parser import parse_plecs_file
from pyplecs.cache import SimulationCache
from pyplecs.pyplecs import PlecsServer, GenericConverterPlecsMdl, PlecsApp
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


class RealPlecsSimulator:
    """Real PLECS simulation executor using XML-RPC."""
    
    def __init__(self, model_file: str, port: str = '1080'):
        """Initialize PLECS simulator.
        
        Args:
            model_file: Path to the .plecs model file
            port: PLECS XML-RPC server port (default: 1080)
        """
        self.model_file = Path(model_file)
        self.port = port
        # Use absolute path for GenericConverterPlecsMdl like in working tests
        full_sim_name = str(self.model_file.absolute())
        self.plecs_model = GenericConverterPlecsMdl(full_sim_name)
        self.server = None
        self.plecs_app = None
        
    def start_plecs_and_connect(self) -> bool:
        """Start PLECS application and connect via XML-RPC.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            print("Starting PLECS application...")
            
            # Start PLECS application (like in test_basic.py)
            self.plecs_app = PlecsApp()
            self.plecs_app.kill_plecs()  # Kill any existing PLECS processes
            time.sleep(1)
            self.plecs_app.open_plecs()  # Start new PLECS instance
            time.sleep(3)  # Give PLECS time to start and enable XML-RPC
            
            print("✓ PLECS application started")
            
            # Create PlecsServer instance using the same pattern as
            # working tests
            self.server = PlecsServer(
                sim_path=self.plecs_model.folder,
                sim_name=self.plecs_model.simulation_name,
                port=self.port,
                load=True
            )
            print(f"✓ Connected to PLECS on port {self.port}")
            print(f"✓ Loaded model: {self.model_file.name}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to start PLECS or connect: {e}")
            print("  Troubleshooting:")
            print("  1. Make sure PLECS is properly installed")
            print("  2. Check if XML-RPC is enabled in PLECS preferences")
            print(f"  3. Verify port {self.port} is available")
            return False
    
    def set_parameters(self, parameters: Dict[str, Any]) -> None:
        """Set model variables in PLECS.
        
        Args:
            parameters: Dictionary of parameter name -> value pairs
        """
        if not self.server:
            raise RuntimeError("Not connected to PLECS server")

        # Separate simple variables from expressions
        simple_vars = {}
        for name, value in parameters.items():
            if name.startswith('_'):  # Skip internal parameters like _sweep_id
                continue
            
            # Check if value looks like an expression (contains operators)
            if isinstance(value, str):
                # Skip expressions that contain mathematical operators
                operators = ['/', '*', '+', '-', '^', '(', ')']
                has_operators = any(op in str(value) for op in operators)
                if has_operators:
                    print(f"      ~ Skipping expression: {name} = {value}")
                    continue
                    
                # Try to convert string to float
                try:
                    simple_vars[name] = float(value)
                except ValueError:
                    print(f"      ~ Skipping non-numeric: {name} = {value}")
                    continue
            else:
                # It's already numeric
                simple_vars[name] = float(value)
        
        print(f"    ⚙ Setting {len(simple_vars)} PLECS variables")
        for name, value in simple_vars.items():
            print(f"      {name} = {value}")
            
        # Use the load_modelvars method to set parameters
        if simple_vars:
            self.server.load_modelvars(simple_vars)
        else:
            print("    ⚠ No simple variables to set")
        
    def run_simulation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Run PLECS simulation with given parameters.
        
        Args:
            parameters: Dictionary of simulation parameters
            
        Returns:
            Dictionary containing simulation results with 'timeseries'
            and 'metadata'
        """
        if not self.server:
            raise RuntimeError("Not connected to PLECS server")
        
        # Set parameters in PLECS
        self.set_parameters(parameters)
        
        # Run simulation
        print("    Running PLECS simulation with parameters:")
        for name, value in parameters.items():
            if not name.startswith('_'):
                print(f"      {name} = {value}")
        
        start_time = time.time()
        
        try:
            # Execute simulation via XML-RPC
            result = self.server.run_sim_with_datastream(param_dict=None)
            
            sim_time = time.time() - start_time
            
            print(f"    ✓ PLECS simulation completed in {sim_time:.2f}s")
            
            if result is None:
                raise RuntimeError("Simulation returned no data")
            
            # Debug: Print result structure
            print(f"    Debug: Result type: {type(result)}")
            if hasattr(result, '__dict__'):
                attrs = list(result.__dict__.keys())
                print(f"    Debug: Result attributes: {attrs}")
            
            # Handle different PLECS result structures
            timeseries_data = {}
            
            # Check for standard PLECS XML-RPC result structure
            if hasattr(result, 'Time') and hasattr(result, 'Values'):
                print("    Processing PLECS XML-RPC result structure")
                if HAS_NUMPY_PANDAS:
                    time_vec = np.array(result.Time)
                    values_array = np.array(result.Values)
                else:
                    time_vec = result.Time
                    values_array = result.Values
                
                timeseries_data['Time'] = time_vec
                
                # Handle single or multiple output signals
                if HAS_NUMPY_PANDAS and hasattr(values_array, 'ndim'):
                    if values_array.ndim == 2:
                        # Multiple signals - each column is a signal
                        for i in range(values_array.shape[1]):
                            timeseries_data[f'Signal_{i}'] = values_array[:, i]
                    else:
                        # Single signal
                        timeseries_data['Signal_0'] = values_array
                else:
                    # Fallback for non-numpy case
                    is_list = isinstance(values_array, list)
                    if is_list and len(values_array) > 0:
                        if isinstance(values_array[0], list):
                            # Multiple signals
                            for i, signal in enumerate(values_array):
                                timeseries_data[f'Signal_{i}'] = signal
                        else:
                            # Single signal
                            timeseries_data['Signal_0'] = values_array
                    else:
                        timeseries_data['Signal_0'] = values_array
                        
            elif isinstance(result, dict):
                print("    Processing dictionary result structure")
                print(f"    Debug: Dict keys: {list(result.keys())}")
                
                if 'Time' in result and 'Values' in result:
                    time_data = result['Time']
                    values_data = result['Values']
                    
                    print(f"    Debug: Time length: {len(time_data)}")
                    print(f"    Debug: Values type: {type(values_data)}")
                    print(f"    Debug: Values length: {len(values_data)}")
                    
                    # Check if Values is a list of signals
                    if isinstance(values_data, list) and len(values_data) > 0:
                        # Check first element to see if it's an array/list
                        first_val = values_data[0]
                        print(f"    Debug: First value type: {type(first_val)}")
                        if hasattr(first_val, '__len__'):
                            print(f"    Debug: First value length: {len(first_val)}")
                    
                    timeseries_data = {'Time': time_data}
                    
                    # Handle Values array structure
                    if isinstance(values_data, list):
                        if len(values_data) > 0 and hasattr(values_data[0], '__len__'):
                            # Values is a list of arrays - each element is a signal
                            for i, signal_data in enumerate(values_data):
                                timeseries_data[f'Signal_{i}'] = signal_data
                                print(f"    Added Signal_{i} with {len(signal_data)} points")
                        else:
                            # Values is a single array
                            timeseries_data['Signal_0'] = values_data
                            print(f"    Added single signal with {len(values_data)} points")
                    else:
                        # Values is not a list - treat as single signal
                        timeseries_data['Signal_0'] = values_data
                        print(f"    Added single signal")
                else:
                    # Generic dictionary - use as-is but add debug info
                    for key, value in result.items():
                        if hasattr(value, '__len__'):
                            print(f"    Debug: {key} length: {len(value)}")
                        else:
                            print(f"    Debug: {key} type: {type(value)}")
                    timeseries_data = result
                
            else:
                result_type = type(result)
                msg = f"    Warning: Unexpected result structure: {result_type}"
                print(msg[:79] + "..." if len(msg) > 79 else msg)
                # Create minimal timeseries data
                timeseries_data = {
                    'Time': [0.0],
                    'Signal_0': [0.0]
                }
            
            # Create DataFrame if we have numpy/pandas
            if HAS_NUMPY_PANDAS:
                timeseries_df = pd.DataFrame(timeseries_data)
            else:
                timeseries_df = timeseries_data
                
            metadata = {
                'parameters': parameters,
                'simulation_time': sim_time,
                'success': True,
                'timestamp': time.time(),
                'model_file': str(self.model_file),
                'simulation_type': 'real_plecs'
            }
            
            return {
                'timeseries': timeseries_df,
                'metadata': metadata
            }
            
        except Exception as e:
            # Return error result
            return {
                'timeseries': None,
                'metadata': {
                    'parameters': parameters,
                    'simulation_time': time.time() - start_time,
                    'success': False,
                    'error': str(e),
                    'timestamp': time.time(),
                    'model_file': str(self.model_file)
                }
            }
    
    def close(self):
        """Close connection to PLECS and stop application."""
        if self.server:
            try:
                self.server.close()
                print("✓ Closed PLECS model")
            except Exception as e:
                print(f"Warning: Error closing PLECS model: {e}")
        
        if self.plecs_app:
            try:
                self.plecs_app.kill_plecs()
                print("✓ Stopped PLECS application")
            except Exception as e:
                print(f"Warning: Error stopping PLECS application: {e}")


def interactive_parameter_sweep_setup(
        available_vars: List[str]) -> List[Dict[str, Any]]:
    """Interactive setup of parameter sweeps."""
    print("\n=== Parameter Sweep Setup ===")
    var_str = ', '.join(available_vars)
    print(f"Available variables for parameter sweep: {var_str}")
    note_msg = ("Note: These are simple numeric variables. "
                "Expressions like D=Vo_ref/Vi will be calculated "
                "automatically.")
    print(note_msg)
    
    sweep_configs = []
    
    while True:
        param_name = get_user_input(
            "\nEnter parameter name to sweep (or 'done' to finish)",
            "done"
        )
        
        if param_name.lower() == 'done' or not param_name:
            break
            
        if param_name not in available_vars:
            warn_msg = (f"Warning: '{param_name}' not found in PLECS "
                        "initialization variables.")
            print(warn_msg)
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
            if result['metadata']['success'] and 'timeseries' in result:
                ts = result['timeseries']
                if isinstance(ts, dict):
                    print(f"  Variables: {list(ts.keys())}")
        return
    
    # Filter successful results
    successful_results = [r for r in results_data if r['metadata']['success']]
    
    if not successful_results:
        print("No successful simulation results to view.")
        return
    
    viewer = SimulationViewer(successful_results)
    available_vars = viewer.list_available_variables()
    
    print("\n=== Simulation Result Viewer ===")
    print(f"Found {len(successful_results)} successful simulation results")
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
            count = len(successful_results)
            print(f"\nSimulation Results ({count} successful):")
            for i, result in enumerate(successful_results):
                params = result['metadata']['parameters']
                success = result['metadata']['success']
                status = "✓" if success else "✗"
                print(f"  {status} {i+1}. {params}")
        
        elif choice == "4" or choice.lower() == 'exit':
            break
        
        else:
            print("Invalid option. Please choose 1-4.")


def main():
    """Main workflow function."""
    print("PyPLECS v0.1.0 - Advanced PLECS Simulation Automation")
    print("=" * 60)
    print("PyPLECS End-to-End CLI Workflow (Real PLECS)")
    print("=" * 60)
    print()
    print("This demo automatically starts PLECS and uses real "
          "simulation via XML-RPC.")
    print("Requirements:")
    print("- PLECS Standalone must be installed")
    print("- XML-RPC will be enabled automatically")
    print("- PLECS will be started by this script")
    print()
    
    # Step 1: Parse PLECS file structure
    print("=== Step 1: Parsing PLECS file ===")
    model_file = "data/simple_buck.plecs"
    
    if not Path(model_file).exists():
        print(f"Error: Model file '{model_file}' not found.")
        print("Please ensure the file exists and try again.")
        return 1
    
    try:
        parsed_data = parse_plecs_file(model_file)
        
        print(f"✓ Parsed file: {parsed_data['file']}")
        print(f"✓ Found {len(parsed_data['components'])} components")
        print(f"✓ Found {len(parsed_data['init_vars'])} "
              "initialization variables")
        
        # Use parsed initialization variables for parameter sweeps
        # Filter to only simple numeric variables (not expressions)
        init_vars = parsed_data['init_vars']
        available_vars = []
        for var_name, var_value in init_vars.items():
            # Only include simple numeric variables (not expressions)
            if isinstance(var_value, str):
                operators = ['/', '*', '+', '-', '^', '(', ')']
                has_operators = any(op in str(var_value) for op in operators)
                if has_operators:
                    continue  # Skip expressions
                try:
                    float(var_value)  # Test if it's convertible to float
                    available_vars.append(var_name)
                except ValueError:
                    continue  # Skip non-numeric strings
            else:
                available_vars.append(var_name)
        
        print(f"Available variables for parameter sweep: "
              f"{', '.join(available_vars)}")
        print(f"Note: Found {len(init_vars)} total variables, "
              f"{len(available_vars)} are sweepable")
        
    except (FileNotFoundError, IOError, OSError) as e:
        print(f"Error parsing PLECS file: {e}")
        return 1
    
    # Step 2: Start PLECS and connect
    print("\n=== Step 2: Starting PLECS and Connecting ===")
    simulator = RealPlecsSimulator(model_file)
    
    if not simulator.start_plecs_and_connect():
        print("Failed to start PLECS or connect. Please check:")
        print("1. PLECS installation path")
        print("2. XML-RPC server configuration")
        print("3. Port availability")
        return 1
    
    # Step 3: Interactive parameter sweep setup
    sweep_configs = interactive_parameter_sweep_setup(available_vars)
    
    if not sweep_configs:
        print("No parameter sweeps configured. Exiting.")
        simulator.close()
        return 0
    
    # Step 4: Create simulation plan
    print("\n=== Step 4: Creating simulation plan ===")
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
    plan_file = metadata_dir / 'simulation_plan_real.json'
    sim_plan.save_to_file(str(plan_file))
    print(f"✓ Saved simulation plan to {plan_file}")
    
    # Step 5: Execute simulations with PLECS
    print(f"\n=== Step 5: Executing {total_sims} PLECS simulations ===")
    
    # Initialize cache
    cache = SimulationCache()
    
    # Option to clear cache for fresh real simulations
    clear_cache = get_user_input(
        "Clear existing cache to force real simulations? (y/n)", "y"
    ).lower()
    if clear_cache == 'y':
        try:
            cache.backend.clear()
            print("✓ Cache cleared - will run fresh PLECS simulations")
        except Exception as e:
            print(f"Warning: Could not clear cache: {e}")
    
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
        
        # Add simulation type to parameters to differentiate from mock
        # simulations
        params_with_type = params.copy()
        params_with_type['_simulation_type'] = 'real_plecs'
        params_with_type['_simulation_engine'] = 'xml_rpc'
        
        # Check cache first with modified parameters
        cached_result = cache.get_cached_result(model_file, params_with_type)
        
        if cached_result:
            print("  ✓ Using cached result")
            results_data.append(cached_result)
        else:
            print("  ⚙ Running PLECS simulation...")
            
            try:
                # Real PLECS simulation execution
                plecs_result = simulator.run_simulation(params)
                
                if plecs_result['metadata']['success']:
                    # Store in cache with modified parameters
                    cache.cache_result(
                        model_file,
                        params_with_type,  # Use params with simulation type
                        plecs_result['timeseries'],
                        plecs_result['metadata']
                    )
                    
                    results_data.append(plecs_result)
                    print("  ✓ Simulation completed and cached")
                else:
                    error_msg = plecs_result['metadata'].get(
                        'error', 'Unknown error')
                    print(f"  ✗ Simulation failed: {error_msg}")
                    results_data.append(plecs_result)  # Include failed results
                
            except Exception as e:
                print(f"  ✗ Simulation execution failed: {e}")
                # Create error result
                error_result = {
                    'timeseries': None,
                    'metadata': {
                        'parameters': params,
                        'simulation_time': 0,
                        'success': False,
                        'error': str(e),
                        'timestamp': time.time(),
                        'model_file': model_file
                    }
                }
                results_data.append(error_result)
    
    successful_count = sum(1 for r in results_data if r['metadata']['success'])
    print(f"\n✓ Completed {len(results_data)} simulations "
          f"({successful_count} successful)")
    
    # Step 6: Interactive result viewer
    print("\n=== Step 6: Interactive Result Viewer ===")
    interactive_result_viewer(results_data)
    
    # Cleanup
    print("\n=== Cleanup ===")
    simulator.close()
    
    print("\n" + "=" * 60)
    print("Real PLECS workflow completed!")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
