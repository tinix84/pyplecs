"""
End-to-end CLI test for PyPLECS simulation workflow.

This test demonstrates the complete workflow:
1. Parse PLECS file structure
2. Interactive parameter sweep setup
3. Simulation plan creation
4. Cached simulation execution
5. Result collection and storage
6. Interactive simulation result viewer
"""

import unittest
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import patch
import time

# Import PyPLECS modules
from pyplecs.plecs_parser import parse_plecs_file, plecs_overview
from pyplecs.cache import SimulationCache

# Optional imports for testing
try:
    import numpy as np
    import pandas as pd
    HAS_NUMPY_PANDAS = True
except ImportError:
    HAS_NUMPY_PANDAS = False


class SimulationPlan:
    """Class to manage simulation parameter sweep plans."""
    
    def __init__(self, model_file: str, base_parameters: Dict[str, Any]):
        self.model_file = model_file
        self.base_parameters = base_parameters
        self.sweep_configs = []
        self.simulation_points = []
        
    def add_sweep_parameter(self, param_name: str, min_val: float,
                            max_val: float, n_points: int):
        """Add a parameter sweep configuration."""
        sweep_config = {
            'parameter': param_name,
            'min_value': min_val,
            'max_value': max_val,
            'n_points': n_points,
            'values': np.linspace(min_val, max_val, n_points).tolist()
        }
        self.sweep_configs.append(sweep_config)
        
    def generate_simulation_points(self) -> List[Dict[str, Any]]:
        """Generate all simulation parameter combinations."""
        if not self.sweep_configs:
            return [self.base_parameters.copy()]
            
        # Create meshgrid for all sweep parameters
        param_names = [config['parameter'] for config in self.sweep_configs]
        param_values = [config['values'] for config in self.sweep_configs]
        
        # Generate cartesian product of all parameter values
        if not HAS_NUMPY_PANDAS:
            # Simple implementation without numpy
            import itertools
            combinations = list(itertools.product(*param_values))
        else:
            import itertools
            combinations = list(itertools.product(*param_values))
        
        self.simulation_points = []
        for i, combo in enumerate(combinations):
            sim_params = self.base_parameters.copy()
            for param_name, value in zip(param_names, combo):
                sim_params[param_name] = value
            sim_params['_sweep_id'] = i
            self.simulation_points.append(sim_params)
            
        return self.simulation_points
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert simulation plan to dictionary for storage."""
        return {
            'model_file': self.model_file,
            'base_parameters': self.base_parameters,
            'sweep_configs': self.sweep_configs,
            'simulation_points': self.simulation_points,
            'total_simulations': len(self.simulation_points)
        }
    
    def save_to_file(self, filepath: str):
        """Save simulation plan to JSON file."""
        plan_dict = self.to_dict()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(plan_dict, f, indent=2, default=str)


class SimulationViewer:
    """Class to interactively view and plot simulation results."""
    
    def __init__(self, results_data: List[Dict[str, Any]]):
        self.results_data = results_data
        self.available_variables = self._extract_available_variables()
        
    def _extract_available_variables(self) -> List[str]:
        """Extract all available variables from simulation results."""
        variables = set()
        for result in self.results_data:
            if 'timeseries' in result and result['timeseries'] is not None:
                if isinstance(result['timeseries'], pd.DataFrame):
                    variables.update(result['timeseries'].columns)
        return sorted(list(variables))
    
    def list_available_variables(self) -> List[str]:
        """List all available variables for plotting."""
        return self.available_variables
    
    def plot_variable(
        self, variable_name: str, sweep_param: Optional[str] = None
    ):
        """Plot a specific variable across all simulations."""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("Matplotlib not available. Cannot create plots.")
            return None
            
        fig, ax = plt.subplots(figsize=(10, 6))
        
        for i, result in enumerate(self.results_data):
            if 'timeseries' not in result or result['timeseries'] is None:
                continue
                
            df = result['timeseries']
            if variable_name not in df.columns:
                continue
                
            # Get sweep parameter value for legend
            sweep_val = None
            if sweep_param and 'metadata' in result:
                params = result['metadata'].get('parameters', {})
                sweep_val = params.get(sweep_param)
            
            label = f"Sim {i}"
            if sweep_val is not None:
                label = f"{sweep_param}={sweep_val}"
                
            ax.plot(df['Time'], df[variable_name], label=label)
        
        ax.set_xlabel('Time [s]')
        ax.set_ylabel(variable_name)
        ax.set_title(f'{variable_name} vs Time')
        ax.legend()
        ax.grid(True)
        
        return fig
    
    def summary_statistics(self, variable_name: str) -> 'pd.DataFrame':
        """Calculate summary statistics for a variable across simulations."""
        stats_data = []
        
        for i, result in enumerate(self.results_data):
            if 'timeseries' not in result or result['timeseries'] is None:
                continue
                
            df = result['timeseries']
            if variable_name not in df.columns:
                continue
                
            variable_data = df[variable_name]
            final_val = (variable_data.iloc[-1]
                         if len(variable_data) > 0 else None)
            stats = {
                'simulation_id': i,
                'mean': variable_data.mean(),
                'std': variable_data.std(),
                'min': variable_data.min(),
                'max': variable_data.max(),
                'final_value': final_val
            }
            
            # Add sweep parameter values if available
            if 'metadata' in result and 'parameters' in result['metadata']:
                for param, value in result['metadata']['parameters'].items():
                    if not param.startswith('_'):  # Skip internal parameters
                        stats[f'param_{param}'] = value
                        
            stats_data.append(stats)
        
        return pd.DataFrame(stats_data)


class EndToEndCLITestSuite(unittest.TestCase):
    """End-to-end CLI test suite for PyPLECS workflow."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_model_file = 'data/simple_buck.plecs'
        self.cache_dir = Path('./test_cache')
        self.metadata_dir = Path('./test_metadata')
        
        # Create test directories
        self.cache_dir.mkdir(exist_ok=True)
        self.metadata_dir.mkdir(exist_ok=True)
        
        # Initialize cache system
        self.cache = SimulationCache()
        
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        if self.metadata_dir.exists():
            shutil.rmtree(self.metadata_dir)
    
    @patch('builtins.input')
    @unittest.skipUnless(HAS_NUMPY_PANDAS, "Requires numpy and pandas")
    def test_end_to_end_workflow_mock(self, mock_input):
        """Test complete end-to-end workflow with mocked user input."""
        
        # Mock user inputs for parameter selection and plotting
        mock_input.side_effect = [
            'Vi',           # First parameter to sweep
            '100',          # Min value
            '300',          # Max value
            '3',            # Number of points
            'Vo_ref',       # Second parameter to sweep
            '10',           # Min value
            '30',           # Max value
            '2',            # Number of points
            '',             # No more parameters
            '1',            # Select first simulation to plot
            'quit'          # Exit viewer
        ]
        
        # Step 1: Parse PLECS file structure
        print("\n=== Step 1: Parsing PLECS file ===")
        parsed_data = parse_plecs_file(self.test_model_file)
        plecs_overview(self.test_model_file)  # Test overview function
        
        print(f"Parsed file: {parsed_data['file']}")
        print(f"Found {len(parsed_data['components'])} components")
        print(f"Found {len(parsed_data['init_vars'])} initialization vars")
        print("Available variables:", list(parsed_data['init_vars'].keys()))
        
        # Verify parsing worked
        self.assertIn('components', parsed_data)
        self.assertIn('init_vars', parsed_data)
        self.assertGreater(len(parsed_data['init_vars']), 0)
        
        # Step 2: Create simulation plan with mocked CLI interaction
        print("\n=== Step 2: Creating simulation plan ===")
        base_params = parsed_data['init_vars'].copy()
        sim_plan = SimulationPlan(self.test_model_file, base_params)
        
        # Simulate CLI parameter selection
        available_vars = list(parsed_data['init_vars'].keys())
        print(f"Available variables: {available_vars}")
        
        # Add first parameter sweep (Vi: 100-300, 3 points)
        if 'Vi' in available_vars:
            sim_plan.add_sweep_parameter('Vi', 100, 300, 3)
            print("Added Vi sweep: 100-300, 3 points")
        
        # Add second parameter sweep (Vo_ref: 10-30, 2 points)
        if 'Vo_ref' in available_vars:
            sim_plan.add_sweep_parameter('Vo_ref', 10, 30, 2)
            print("Added Vo_ref sweep: 10-30, 2 points")
        
        # Generate simulation points
        simulation_points = sim_plan.generate_simulation_points()
        total_sims = len(simulation_points)
        
        print(f"Generated {total_sims} simulation points")
        self.assertGreater(total_sims, 0)
        
        # Save simulation plan
        plan_file = self.metadata_dir / 'simulation_plan.json'
        sim_plan.save_to_file(str(plan_file))
        print(f"Saved simulation plan to {plan_file}")
        
        # Step 3: Execute simulations with caching
        print("\n=== Step 3: Executing simulations with caching ===")
        results_data = []
        
        # Limit to first 2 for testing
        for i, params in enumerate(simulation_points[:2]):
            print(f"Running simulation {i+1}/{min(2, total_sims)}")
            
            # Check cache first
            cached_result = self.cache.get_cached_result(
                self.test_model_file, params
            )
            
            if cached_result:
                print("  Using cached result")
                results_data.append(cached_result)
            else:
                print("  Running new simulation")
                
                # Mock simulation execution
                mock_result = self._mock_simulation_execution(params)
                
                # Store in cache
                self.cache.cache_result(
                    self.test_model_file,
                    params,
                    mock_result['timeseries'],
                    mock_result['metadata']
                )
                
                results_data.append(mock_result)
        
        print(f"Completed {len(results_data)} simulations")
        self.assertEqual(len(results_data), 2)
        
        # Step 4: Interactive result viewer
        print("\n=== Step 4: Interactive result viewer ===")
        viewer = SimulationViewer(results_data)
        
        available_vars = viewer.list_available_variables()
        print(f"Available variables for plotting: {available_vars}")
        
        # Mock interactive selection and plotting
        if available_vars:
            print(f"Generating summary statistics for {available_vars[0]}")
            stats = viewer.summary_statistics(available_vars[0])
            print(stats.head())
            self.assertIsInstance(stats, pd.DataFrame)
        
        print("=== End-to-end workflow completed successfully ===")
    
    def _mock_simulation_execution(
            self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Mock simulation execution for testing."""
        if not HAS_NUMPY_PANDAS:
            # Simple mock without numpy/pandas
            return {
                'timeseries': {
                    'Time': [0.0, 0.5, 1.0],
                    'Vi': [parameters.get('Vi', 100)] * 3,
                    'Vo': [parameters.get('Vo_ref', 20)] * 3
                },
                'metadata': {
                    'parameters': parameters,
                    'simulation_time': 1.0,
                    'success': True,
                    'timestamp': time.time(),
                    'model_file': self.test_model_file
                }
            }
        
        # Generate mock timeseries data with numpy/pandas
        time_vec = np.linspace(0, 1, 100)
        
        # Create mock waveforms based on parameters
        vi = parameters.get('Vi', 100)
        vo_ref = parameters.get('Vo_ref', 20)
        
        mock_data = {
            'Time': time_vec,
            'Vi': vi * np.ones_like(time_vec),
            'Vo': vo_ref * (1 - np.exp(-time_vec/0.1)),
            'Ii': (vi / 10) * np.ones_like(time_vec),
            'Io': (vo_ref / 5) * np.ones_like(time_vec)
        }
        
        timeseries_df = pd.DataFrame(mock_data)
        
        metadata = {
            'parameters': parameters,
            'simulation_time': 1.0,
            'success': True,
            'timestamp': time.time(),
            'model_file': self.test_model_file
        }
        
        return {
            'timeseries': timeseries_df,
            'metadata': metadata
        }
    
    def test_simulation_plan_creation(self):
        """Test simulation plan creation and serialization."""
        base_params = {'Vi': 100, 'Vo_ref': 20, 'R_load': 5}
        plan = SimulationPlan(self.test_model_file, base_params)
        
        # Add parameter sweeps
        plan.add_sweep_parameter('Vi', 50, 150, 3)
        plan.add_sweep_parameter('Vo_ref', 10, 30, 2)
        
        # Generate points
        points = plan.generate_simulation_points()
        
        # Should have 3 * 2 = 6 simulation points
        self.assertEqual(len(points), 6)
        
        # Check that all points have required parameters
        for point in points:
            self.assertIn('Vi', point)
