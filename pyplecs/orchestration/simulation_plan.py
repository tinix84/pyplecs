"""Simulation planning and orchestration functionality.

This module provides classes for managing parameter sweeps and plans.
"""

import json
from typing import Dict, List, Any

try:
    import numpy as np
    HAS_NUMPY_PANDAS = True
except ImportError:
    HAS_NUMPY_PANDAS = False


class SimulationPlan:
    """Class to manage simulation parameter sweep plans."""
    
    def __init__(self, model_file: str, base_parameters: Dict[str, Any]):
        """Initialize simulation plan.
        
        Args:
            model_file: Path to the PLECS model file
            base_parameters: Base parameter values for all simulations
        """
        self.model_file = model_file
        self.base_parameters = base_parameters
        self.sweep_configs = []
        self.simulation_points = []
        
    def add_sweep_parameter(self, param_name: str, min_val: float,
                            max_val: float, n_points: int):
        """Add a parameter sweep configuration.
        
        Args:
            param_name: Name of parameter to sweep
            min_val: Minimum value for sweep
            max_val: Maximum value for sweep
            n_points: Number of points in sweep
        """
        if HAS_NUMPY_PANDAS:
            values = np.linspace(min_val, max_val, n_points).tolist()
        else:
            # Simple implementation without numpy
            if n_points == 1:
                values = [min_val]
            else:
                step = (max_val - min_val) / (n_points - 1)
                values = [min_val + i * step for i in range(n_points)]
        
        sweep_config = {
            'parameter': param_name,
            'min_value': min_val,
            'max_value': max_val,
            'n_points': n_points,
            'values': values
        }
        self.sweep_configs.append(sweep_config)
        
    def generate_simulation_points(self) -> List[Dict[str, Any]]:
        """Generate all simulation parameter combinations.
        
        Returns:
            List of parameter dictionaries for each simulation
        """
        if not self.sweep_configs:
            return [self.base_parameters.copy()]
            
        # Create meshgrid for all sweep parameters
        param_names = [config['parameter'] for config in self.sweep_configs]
        param_values = [config['values'] for config in self.sweep_configs]
        
        # Generate cartesian product of all parameter values
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
        """Convert simulation plan to dictionary for storage.
        
        Returns:
            Dictionary representation of simulation plan
        """
        return {
            'model_file': self.model_file,
            'base_parameters': self.base_parameters,
            'sweep_configs': self.sweep_configs,
            'simulation_points': self.simulation_points,
            'total_simulations': len(self.simulation_points)
        }
    
    def save_to_file(self, filepath: str):
        """Save simulation plan to JSON file.
        
        Args:
            filepath: Path to save JSON file
        """
        plan_dict = self.to_dict()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(plan_dict, f, indent=2, default=str)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'SimulationPlan':
        """Load simulation plan from JSON file.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            SimulationPlan instance
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            plan_dict = json.load(f)
        
        plan = cls(plan_dict['model_file'], plan_dict['base_parameters'])
        plan.sweep_configs = plan_dict.get('sweep_configs', [])
        plan.simulation_points = plan_dict.get('simulation_points', [])
        
        return plan
