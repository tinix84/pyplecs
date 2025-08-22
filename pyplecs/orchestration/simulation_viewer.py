"""Result viewer functionality for simulation orchestration.

This module provides classes for viewing and analyzing simulation results.
"""

from typing import Dict, List, Any, Optional

try:
    import pandas as pd
    HAS_NUMPY_PANDAS = True
except ImportError:
    HAS_NUMPY_PANDAS = False


class SimulationViewer:
    """Class to interactively view and plot simulation results."""
    
    def __init__(self, results_data: List[Dict[str, Any]]):
        """Initialize simulation viewer.
        
        Args:
            results_data: List of simulation result dictionaries
        """
        self.results_data = results_data
        self.available_variables = self._extract_available_variables()
        
    def _extract_available_variables(self) -> List[str]:
        """Extract all available variables from simulation results.
        
        Returns:
            List of variable names available for analysis
        """
        if not HAS_NUMPY_PANDAS:
            # Fallback for non-pandas case
            variables = set()
            for result in self.results_data:
                if 'timeseries' in result and result['timeseries'] is not None:
                    if isinstance(result['timeseries'], dict):
                        variables.update(result['timeseries'].keys())
            return sorted(list(variables))
        
        variables = set()
        for result in self.results_data:
            if 'timeseries' in result and result['timeseries'] is not None:
                if isinstance(result['timeseries'], pd.DataFrame):
                    variables.update(result['timeseries'].columns)
                elif isinstance(result['timeseries'], dict):
                    variables.update(result['timeseries'].keys())
        return sorted(list(variables))
    
    def list_available_variables(self) -> List[str]:
        """List all available variables for plotting.
        
        Returns:
            List of variable names
        """
        return self.available_variables
    
    def plot_variable(
        self, variable_name: str, sweep_param: Optional[str] = None
    ):
        """Plot a specific variable across all simulations.
        
        Args:
            variable_name: Name of variable to plot
            sweep_param: Optional sweep parameter for legend labels
            
        Returns:
            matplotlib Figure object or None if matplotlib unavailable
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("Matplotlib not available. Cannot create plots.")
            return None
            
        if not HAS_NUMPY_PANDAS:
            print("Pandas not available. Limited plotting functionality.")
            return None
            
        fig, ax = plt.subplots(figsize=(10, 6))
        
        for i, result in enumerate(self.results_data):
            if 'timeseries' not in result or result['timeseries'] is None:
                continue
                
            df = result['timeseries']
            if not isinstance(df, pd.DataFrame):
                continue
                
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
    
    def summary_statistics(
        self, variable_name: str
    ) -> Optional['pd.DataFrame']:
        """Calculate summary statistics for a variable across simulations.
        
        Args:
            variable_name: Name of variable to analyze
            
        Returns:
            DataFrame with summary statistics or None if pandas unavailable
        """
        if not HAS_NUMPY_PANDAS:
            print("Pandas not available. Cannot generate summary statistics.")
            return None
            
        stats_data = []
        
        for i, result in enumerate(self.results_data):
            if 'timeseries' not in result or result['timeseries'] is None:
                continue
                
            df = result['timeseries']
            if not isinstance(df, pd.DataFrame):
                continue
                
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
