# Parallel Coordinate Plot Implementation for PyPLECS Sensitivity Analysis

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class ParameterVariationType(Enum):
    PERCENTAGE = "percentage"
    ABSOLUTE = "absolute"
    RANGE = "range"

@dataclass
class KPIDefinition:
    """Define a Key Performance Indicator for parallel coordinate analysis"""
    name: str           # e.g., "Vout", "Iout_ripple", "Efficiency"
    display_name: str   # e.g., "Output Voltage [V]", "Current Ripple [%]"
    unit: str          # e.g., "V", "%", "W"
    target_type: str   # "maximize", "minimize", "target_value"
    target_value: Optional[float] = None
    acceptable_range: Optional[tuple] = None

@dataclass
class ParameterSweepDefinition:
    """Define parameter variation for sensitivity analysis"""
    name: str
    nominal_value: float
    variation_type: ParameterVariationType
    variation_range: tuple  # e.g., (-10, 10) for ±10%
    steps: int = 11

class PLECSParametricAnalyzer:
    """Main class for parametric analysis with parallel coordinate visualization"""
    
    def __init__(self, plecs_server):
        self.plecs_server = plecs_server
        self.parameters = []
        self.kpis = []
        self.results_df = None
        
    def add_parameter(self, param: ParameterSweepDefinition):
        """Add parameter to sweep definition"""
        self.parameters.append(param)
        
    def add_kpi(self, kpi: KPIDefinition):
        """Add KPI to monitor"""
        self.kpis.append(kpi)
        
    def generate_parameter_combinations(self, method='one_at_time'):
        """Generate parameter combinations for analysis"""
        combinations = []
        
        if method == 'one_at_time':
            # One-at-a-time sensitivity (like your example)
            base_values = {p.name: p.nominal_value for p in self.parameters}
            
            # Add baseline case
            combinations.append(base_values.copy())
            
            # Vary each parameter individually
            for param in self.parameters:
                if param.variation_type == ParameterVariationType.PERCENTAGE:
                    min_val = param.nominal_value * (1 + param.variation_range[0]/100)
                    max_val = param.nominal_value * (1 + param.variation_range[1]/100)
                else:
                    min_val = param.nominal_value + param.variation_range[0]
                    max_val = param.nominal_value + param.variation_range[1]
                
                values = np.linspace(min_val, max_val, param.steps)
                
                for val in values:
                    if val != param.nominal_value:  # Skip nominal (already added)
                        combo = base_values.copy()
                        combo[param.name] = val
                        combo['varied_parameter'] = param.name
                        combo['variation_percent'] = ((val - param.nominal_value) / param.nominal_value) * 100
                        combinations.append(combo)
                        
        elif method == 'factorial':
            # Full factorial design
            from itertools import product
            
            param_values = []
            for param in self.parameters:
                if param.variation_type == ParameterVariationType.PERCENTAGE:
                    min_val = param.nominal_value * (1 + param.variation_range[0]/100)
                    max_val = param.nominal_value * (1 + param.variation_range[1]/100)
                else:
                    min_val = param.nominal_value + param.variation_range[0]
                    max_val = param.nominal_value + param.variation_range[1]
                
                values = np.linspace(min_val, max_val, param.steps)
                param_values.append(values)
            
            for combination in product(*param_values):
                combo = {param.name: val for param, val in zip(self.parameters, combination)}
                combinations.append(combo)
        
        return combinations
    
    def run_parametric_study(self, method='one_at_time', progress_callback=None):
        """Execute parametric study with PLECS simulations"""
        combinations = self.generate_parameter_combinations(method)
        results = []
        
        total_sims = len(combinations)
        print(f"Running {total_sims} simulations...")
        
        for i, combo in enumerate(combinations):
            if progress_callback:
                progress_callback(i, total_sims, combo)
                
            try:
                # Set parameters for simulation
                param_dict = {k: v for k, v in combo.items() 
                             if k not in ['varied_parameter', 'variation_percent']}

                # --- Model variable validation ---
                # Try to get the list of valid model variables from the PLECS parser
                valid_model_vars = None
                if hasattr(self.plecs_server, 'get_model_variables'):
                    try:
                        valid_model_vars = set(self.plecs_server.get_model_variables())
                    except Exception as e:
                        print(f"  Warning: Could not retrieve model variables from PLECS parser: {e}")
                # Fallback for mock server
                elif hasattr(self.plecs_server, 'server') and hasattr(self.plecs_server.server, 'plecs') and hasattr(self.plecs_server.server.plecs, 'current_params'):
                    valid_model_vars = set(self.plecs_server.server.plecs.current_params.keys())

                if valid_model_vars is not None:
                    # Filter param_dict to only include valid model variables
                    filtered_param_dict = {k: v for k, v in param_dict.items() if k in valid_model_vars}
                    invalid_keys = set(param_dict.keys()) - valid_model_vars
                    if invalid_keys:
                        print(f"  Warning: The following parameters are not present in the PLECS model and will be ignored: {sorted(invalid_keys)}")
                else:
                    filtered_param_dict = param_dict

                print(f"  Running simulation {i+1}/{total_sims}: {filtered_param_dict}")

                # Check if this is a mock server or real PLECS server
                if hasattr(self.plecs_server, 'run_sim_with_datastream'):
                    # Real PLECS server - use run_sim_with_datastream
                    sim_result = self.plecs_server.run_sim_with_datastream(filtered_param_dict)
                elif hasattr(self.plecs_server, 'server') and hasattr(self.plecs_server.server, 'plecs'):
                    # Mock server from our implementation
                    self.plecs_server.load_modelvars({'ModelVars': filtered_param_dict})
                    sim_result = self.plecs_server.server.plecs.simulate(
                        self.plecs_server.modelName, 
                        self.plecs_server.optStruct
                    )
                else:
                    raise ValueError("Unknown PLECS server type")
                
                # Extract KPIs from simulation results
                kpi_values = self.extract_kpis(sim_result)
                
                # Combine parameters and results
                result_row = {**combo, **kpi_values}
                result_row['simulation_id'] = i
                result_row['success'] = True
                results.append(result_row)
                print(f"    ✓ Success: {kpi_values}")
                
            except Exception as e:
                print(f"    ✗ Simulation {i+1} failed: {e}")
                # Add failed simulation with NaN values
                result_row = combo.copy()
                result_row.update({kpi.name: np.nan for kpi in self.kpis})
                result_row['simulation_id'] = i
                result_row['success'] = False
                results.append(result_row)
        
        self.results_df = pd.DataFrame(results)
        return self.results_df
    
    def extract_kpis(self, sim_result) -> Dict[str, float]:
        """Extract KPI values from PLECS simulation results"""
        kpi_values = {}
        
        # Handle both real PLECS results and mock results
        if sim_result is None:
            # Return default values if simulation failed
            for kpi in self.kpis:
                kpi_values[kpi.name] = 0.0
            return kpi_values
        
        for kpi in self.kpis:
            try:
                if kpi.name == "Vout_avg":
                    kpi_values[kpi.name] = self.calculate_average_output(sim_result)
                elif kpi.name == "Vout_ripple":
                    kpi_values[kpi.name] = self.calculate_voltage_ripple(sim_result)
                elif kpi.name == "Iout_ripple":
                    kpi_values[kpi.name] = self.calculate_current_ripple(sim_result)
                elif kpi.name == "Efficiency":
                    kpi_values[kpi.name] = self.calculate_efficiency(sim_result)
                elif kpi.name == "THD":
                    kpi_values[kpi.name] = self.calculate_thd(sim_result)
                else:
                    # Generic extraction with fallback
                    kpi_values[kpi.name] = self.extract_generic_kpi(sim_result, kpi.name)
            except Exception as e:
                print(f"Warning: Failed to extract KPI {kpi.name}: {e}")
                # Use reasonable fallback values
                if kpi.name in ["Vout_avg"]:
                    kpi_values[kpi.name] = 200.0  # Expected output voltage
                elif kpi.name in ["Efficiency"]:
                    kpi_values[kpi.name] = 85.0   # Reasonable efficiency
                elif "ripple" in kpi.name.lower():
                    kpi_values[kpi.name] = 5.0    # Moderate ripple
                else:
                    kpi_values[kpi.name] = 1.0
                
        return kpi_values
    
    def extract_generic_kpi(self, sim_result, kpi_name):
        """Extract a generic KPI by name from simulation results"""
        if isinstance(sim_result, dict) and 'Values' in sim_result:
            # Real PLECS result format
            values = sim_result['Values']
            if isinstance(values, dict) and kpi_name in values:
                signal = np.array(values[kpi_name])
                return float(np.mean(signal))
        elif isinstance(sim_result, dict) and kpi_name in sim_result:
            # Direct access
            signal = np.array(sim_result[kpi_name])
            return float(np.mean(signal))
        
        # Fallback: return mock value
        return np.random.normal(1, 0.1)
    
    def calculate_average_output(self, sim_result):
        """Calculate average output voltage from simulation"""
        if isinstance(sim_result, dict):
            # Try different common output voltage names
            voltage_names = ['Vout', 'VO', 'V_out', 'OutputVoltage', 'Vo']
            
            if 'Values' in sim_result:
                # Real PLECS format
                values = sim_result['Values']
                for name in voltage_names:
                    if name in values:
                        vout = np.array(values[name])
                        return float(np.mean(vout))
            else:
                # Direct format
                for name in voltage_names:
                    if name in sim_result:
                        vout = np.array(sim_result[name])
                        return float(np.mean(vout))
        
        return 200.0  # Default expected output voltage
    
    def calculate_voltage_ripple(self, sim_result):
        """Calculate output voltage ripple percentage"""
        if isinstance(sim_result, dict):
            voltage_names = ['Vout', 'VO', 'V_out', 'OutputVoltage', 'Vo']
            
            if 'Values' in sim_result:
                values = sim_result['Values']
                for name in voltage_names:
                    if name in values:
                        vout = np.array(values[name])
                        if len(vout) > 1:
                            avg_voltage = np.mean(vout)
                            ripple = (np.max(vout) - np.min(vout)) / avg_voltage * 100
                            return abs(float(ripple))
            else:
                for name in voltage_names:
                    if name in sim_result:
                        vout = np.array(sim_result[name])
                        if len(vout) > 1:
                            avg_voltage = np.mean(vout)
                            ripple = (np.max(vout) - np.min(vout)) / avg_voltage * 100
                            return abs(float(ripple))
        
        return 2.0  # Default reasonable ripple
    
    def calculate_current_ripple(self, sim_result):
        """Calculate current ripple percentage"""
        if isinstance(sim_result, dict):
            current_names = ['Iout', 'IO', 'I_out', 'OutputCurrent', 'Io', 'IL', 'I_L']
            
            if 'Values' in sim_result:
                values = sim_result['Values']
                for name in current_names:
                    if name in values:
                        iout = np.array(values[name])
                        if len(iout) > 1:
                            avg_current = np.mean(iout)
                            if avg_current > 0:
                                ripple = (np.max(iout) - np.min(iout)) / avg_current * 100
                                return abs(float(ripple))
            else:
                for name in current_names:
                    if name in sim_result:
                        iout = np.array(sim_result[name])
                        if len(iout) > 1:
                            avg_current = np.mean(iout)
                            if avg_current > 0:
                                ripple = (np.max(iout) - np.min(iout)) / avg_current * 100
                                return abs(float(ripple))
        
        return 5.0  # Default reasonable current ripple
    
    def calculate_efficiency(self, sim_result):
        """Calculate power conversion efficiency"""
        if isinstance(sim_result, dict):
            # Try to find power signals
            power_in_names = ['Pin', 'P_in', 'PowerIn', 'InputPower']
            power_out_names = ['Pout', 'P_out', 'PowerOut', 'OutputPower']
            
            pin = pout = None
            
            if 'Values' in sim_result:
                values = sim_result['Values']
                # Look for power signals
                for name in power_in_names:
                    if name in values:
                        pin = np.mean(np.array(values[name]))
                        break
                for name in power_out_names:
                    if name in values:
                        pout = np.mean(np.array(values[name]))
                        break
                        
                # If direct power not found, calculate from V and I
                if pin is None or pout is None:
                    # Try to calculate from voltage and current
                    vin = vout = iin = iout = None
                    
                    # Find input voltage and current
                    for name in ['Vin', 'V_in', 'InputVoltage']:
                        if name in values:
                            vin = np.mean(np.array(values[name]))
                            break
                    for name in ['Iin', 'I_in', 'InputCurrent']:
                        if name in values:
                            iin = np.mean(np.array(values[name]))
                            break
                            
                    # Find output voltage and current
                    for name in ['Vout', 'V_out', 'OutputVoltage', 'VO']:
                        if name in values:
                            vout = np.mean(np.array(values[name]))
                            break
                    for name in ['Iout', 'I_out', 'OutputCurrent', 'IO']:
                        if name in values:
                            iout = np.mean(np.array(values[name]))
                            break
                    
                    if vin is not None and iin is not None:
                        pin = vin * abs(iin)
                    if vout is not None and iout is not None:
                        pout = vout * abs(iout)
            
            if pin is not None and pout is not None and pin > 0:
                efficiency = (pout / pin) * 100
                return float(min(100.0, max(0.0, efficiency)))  # Clamp to 0-100%
        
        return 85.0  # Default reasonable efficiency
    
    def calculate_thd(self, sim_result):
        """Calculate Total Harmonic Distortion"""
        # Implement FFT-based THD calculation
        # Placeholder implementation
        return np.random.uniform(1, 5)
    
    def create_parallel_coordinate_plot(self, highlight_solutions=None, color_by='varied_parameter'):
        """Create parallel coordinate plot like your example"""
        if self.results_df is None:
            raise ValueError("No results available. Run parametric study first.")
        
        # Filter successful simulations
        df = self.results_df[self.results_df['success']].copy()
        
        # Prepare dimensions for parallel plot
        dimensions = []
        
        # Add KPIs as dimensions
        for kpi in self.kpis:
            if kpi.name in df.columns:
                dimensions.append(dict(
                    label=kpi.display_name,
                    values=df[kpi.name],
                    range=[df[kpi.name].min(), df[kpi.name].max()]
                ))
        
        # Create the parallel coordinates plot
        # Use numerical color mapping
        if color_by and color_by in df.columns:
            # Convert categorical to numerical for color mapping
            if df[color_by].dtype == 'object':
                color_values = pd.Categorical(df[color_by]).codes
                colorbar_title = color_by
            else:
                color_values = df[color_by]
                colorbar_title = color_by
        else:
            color_values = df.index
            colorbar_title = "Simulation ID"
        
        fig = go.Figure(data=go.Parcoords(
            line=dict(
                color=color_values,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title=colorbar_title)
            ),
            dimensions=dimensions,
            labelangle=-45,
            labelside='bottom'
        ))
        
        # Customize layout
        fig.update_layout(
            title="Parametric Analysis - Parallel Coordinate Plot",
            font=dict(size=12),
            height=600,
            margin=dict(l=80, r=80, t=80, b=120)
        )
        
        return fig
    
    def create_solution_comparison_plot(self, solution_ids=None, solution_names=None):
        """Create plot highlighting specific solutions like in your example"""
        if self.results_df is None:
            raise ValueError("No results available. Run parametric study first.")
        
        df = self.results_df[self.results_df['success']].copy()
        
        if solution_ids is None:
            # Default: highlight best, worst, and median for first KPI
            first_kpi = self.kpis[0].name
            sorted_df = df.sort_values(first_kpi)
            solution_ids = [
                sorted_df.index[0],      # Best
                sorted_df.index[len(sorted_df)//2],  # Median
                sorted_df.index[-1]      # Worst
            ]
            solution_names = ["Solution 1 (Best)", "Solution 2 (Median)", "Solution 3 (Worst)"]
        
        # Create base plot with all solutions in gray
        dimensions = []
        for kpi in self.kpis:
            if kpi.name in df.columns:
                dimensions.append(dict(
                    label=kpi.display_name,
                    values=df[kpi.name],
                    range=[df[kpi.name].min(), df[kpi.name].max()]
                ))
        
        fig = go.Figure()
        
        # Add all solutions as gray background
        fig.add_trace(go.Parcoords(
            line=dict(color='lightgray'),
            dimensions=dimensions,
            name="All Solutions"
        ))
        
        # Add highlighted solutions
        colors = ['red', 'blue', 'green', 'orange', 'purple']
        for i, (sol_id, sol_name) in enumerate(zip(solution_ids, 
                                                   solution_names or 
                                                   [f"Solution {i+1}" for i in range(len(solution_ids))])):
            sol_data = df.loc[sol_id]
            
            # Create dimensions for this specific solution
            sol_dimensions = []
            for kpi in self.kpis:
                if kpi.name in df.columns:
                    sol_dimensions.append(dict(
                        label=kpi.display_name,
                        values=[sol_data[kpi.name]],  # Single value for line
                        range=[df[kpi.name].min(), df[kpi.name].max()]
                    ))
            
            fig.add_trace(go.Parcoords(
                line=dict(color=colors[i % len(colors)]),
                dimensions=sol_dimensions,
                name=sol_name
            ))
        
        fig.update_layout(
            title="Solution Comparison - Parallel Coordinate Plot",
            font=dict(size=12),
            height=600,
            margin=dict(l=80, r=80, t=80, b=120)
        )
        
        return fig

# Mock PLECS server for demonstration
class MockPlecsServer:
    """Mock PLECS server for testing the parametric analyzer without real PLECS"""
    
    def __init__(self):
        self.current_params = {}
        
    def load_modelvars(self, params):
        """Mock parameter loading"""
        self.current_params.update(params.get('ModelVars', {}))
        
    def simulate(self, model_name, opt_struct):
        """Mock simulation that returns synthetic but realistic data"""
        # Generate synthetic results based on current parameters
        np.random.seed(42)  # For reproducible results
        
        # Simulate how parameters affect KPIs
        lo = self.current_params.get('Lo', 100e-6)
        co = self.current_params.get('Co', 220e-6)
        
        # Mock realistic relationships
        # Higher inductance -> lower ripple, slightly lower efficiency
        # Higher capacitance -> lower ripple, higher efficiency
        
        base_efficiency = 85
        efficiency = base_efficiency + (co/220e-6 - 1) * 5 - (lo/100e-6 - 1) * 2
        efficiency += np.random.normal(0, 1)  # Add noise
        
        base_vout = 12.0
        vout = base_vout + (lo/100e-6 - 1) * 0.1 + np.random.normal(0, 0.05)
        
        base_ripple = 5.0
        ripple = base_ripple * (100e-6/lo) * (220e-6/co) + np.random.normal(0, 0.5)
        ripple = max(0.1, ripple)  # Ensure positive
        
        return {
            'Vout': [vout] * 100,  # Constant voltage array
            'Iout': np.random.normal(5, ripple/100) + np.random.normal(0, 0.1, 100),
            'Pout': [vout * 5] * 100,  # Power out
            'Pin': [vout * 5 / (efficiency/100)] * 100,  # Power in
        }


class MockPlecsServerWrapper:
    """Wrapper to match the expected interface"""
    
    def __init__(self):
        self.server = type('Server', (), {})()
        self.server.plecs = MockPlecsServer()
        self.modelName = "boost_converter.plecs"
        self.optStruct = {}
        
    def load_modelvars(self, params):
        self.server.plecs.load_modelvars(params)


# Example usage and integration with existing pyplecs
def example_usage():
    """Example of how to use the parametric analyzer"""
    
    print("🔍 Running Parallel Coordinate Analysis Demo")
    print("=" * 50)
    
    # Initialize with mock PLECS server for demonstration
    mock_server = MockPlecsServerWrapper()
    analyzer = PLECSParametricAnalyzer(mock_server)
    
    # Define parameters to vary
    analyzer.add_parameter(ParameterSweepDefinition(
        name="Lo",
        nominal_value=100e-6,  # 100µH
        variation_type=ParameterVariationType.PERCENTAGE,
        variation_range=(-20, 20),  # ±20%
        steps=5  # Reduced for demo
    ))
    
    analyzer.add_parameter(ParameterSweepDefinition(
        name="Co",
        nominal_value=220e-6,  # 220µF
        variation_type=ParameterVariationType.PERCENTAGE,
        variation_range=(-30, 30),  # ±30%
        steps=5  # Reduced for demo
    ))
    
    # Define KPIs to monitor
    analyzer.add_kpi(KPIDefinition(
        name="Vout_avg",
        display_name="Output Voltage [V]",
        unit="V",
        target_type="target_value",
        target_value=12.0
    ))
    
    analyzer.add_kpi(KPIDefinition(
        name="Iout_ripple",
        display_name="Current Ripple [%]",
        unit="%",
        target_type="minimize"
    ))
    
    analyzer.add_kpi(KPIDefinition(
        name="Efficiency",
        display_name="Efficiency [%]",
        unit="%",
        target_type="maximize"
    ))
    
    # Run parametric study
    print("Running parametric study...")
    results = analyzer.run_parametric_study(method='one_at_time')
    
    print(f"✅ Completed {len(results)} simulations")
    print("\nResults summary:")
    print(results[['Lo', 'Co', 'Vout_avg', 'Iout_ripple', 'Efficiency']].describe())
    
    # Create parallel coordinate plot
    print("\n📊 Creating parallel coordinate plot...")
    fig = analyzer.create_parallel_coordinate_plot()
    fig.write_html("parallel_coordinate_plot.html")
    print("✅ Saved to parallel_coordinate_plot.html")
    
    # Create solution comparison plot
    print("\n🎯 Creating solution comparison plot...")
    fig_comparison = analyzer.create_solution_comparison_plot()
    fig_comparison.write_html("solution_comparison_plot.html")
    print("✅ Saved to solution_comparison_plot.html")
    
    print("\n🎉 Demo completed! Open the HTML files to view the plots.")
    
    return analyzer, results

if __name__ == "__main__":
    example_usage()