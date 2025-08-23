"""Load model and set variables example with live parameter adjustment.

This example demonstrates:
1. Loading a PLECS model
2. Querying available model variables
3. Setting variable values dynamically
4. Running simulations with different parameter sets
5. Comparing results with parameter changes
"""
import time
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

try:
    from pyplecs import PlecsApp, PlecsServer
except ImportError:
    print("PyPLECS not properly installed. Please install with: pip install -e .")
    exit(1)


def main():
    """Demonstrate model loading and variable manipulation."""
    model_path = Path(__file__).parent.parent / 'data'
    model_file = 'simple_buck.plecs'
    
    if not (model_path / model_file).exists():
        print(f'PLECS file not found at {model_path / model_file}')
        return

    print("Starting PLECS application...")
    app = PlecsApp()
    
    try:
        # Start PLECS
        app.open_plecs()
        time.sleep(3)  # Wait for PLECS to start
        app.set_plecs_high_priority()
        
        print("Connecting to PLECS server...")
        # Connect to PLECS server
        server = PlecsServer(
            sim_path=str(model_path),
            sim_name=model_file,
            port='1080',
            load=True
        )
        
        print("Querying model variables...")
        # Get available model variables
        try:
            variables = server.get_model_variables()
            print(f"Found {len(variables)} model variables:")
            for var in variables[:10]:  # Show first 10
                print(f"  {var.get('name', 'Unknown')}: {var.get('value', 'N/A')}")
            if len(variables) > 10:
                print(f"  ... and {len(variables) - 10} more variables")
        except Exception as e:
            print(f"Could not query variables: {e}")
            variables = []
        
        # Define test scenarios with different parameter values
        scenarios = [
            {
                'name': 'Baseline',
                'params': {'Vin': 400.0, 'L': 1e-3, 'C': 100e-6, 'R': 10.0},
                'color': 'blue'
            },
            {
                'name': 'High Input Voltage',
                'params': {'Vin': 500.0, 'L': 1e-3, 'C': 100e-6, 'R': 10.0},
                'color': 'red'
            },
            {
                'name': 'Low Inductance',
                'params': {'Vin': 400.0, 'L': 0.5e-3, 'C': 100e-6, 'R': 10.0},
                'color': 'green'
            },
            {
                'name': 'High Capacitance',
                'params': {'Vin': 400.0, 'L': 1e-3, 'C': 200e-6, 'R': 10.0},
                'color': 'orange'
            }
        ]
        
        results = []
        
        print(f"\nRunning {len(scenarios)} parameter scenarios...")
        
        for scenario in scenarios:
            print(f"\nScenario: {scenario['name']}")
            
            # Set each parameter individually
            for param_name, param_value in scenario['params'].items():
                try:
                    print(f"  Setting {param_name} = {param_value}")
                    server.set_value(param_name, param_value)
                except Exception as e:
                    print(f"  Warning: Could not set {param_name}: {e}")
            
            # Run simulation
            print("  Running simulation...")
            try:
                result = server.run_sim_single(scenario['params'], timeout=30.0)
                
                if result and 'status' in result and result['status'] == 'success':
                    print("  ✓ Simulation successful")
                    result['scenario'] = scenario
                    results.append(result)
                else:
                    print(f"  ✗ Simulation failed: {result}")
                    
            except Exception as e:
                print(f"  ✗ Error in simulation: {e}")
        
        # Plot comparison results
        if results:
            print(f"\nPlotting comparison of {len(results)} scenarios...")
            plot_parameter_comparison(results)
        else:
            print("No successful simulations to compare")
            
    except Exception as e:
        print(f"Error during model operations: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("Cleaning up...")
        # Clean up PLECS
        try:
            server.close()
        except:
            pass
        app.kill_plecs()


def plot_parameter_comparison(results):
    """Plot comparison of different parameter scenarios."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Parameter Variation Comparison')
    
    for result in results:
        scenario = result['scenario']
        color = scenario['color']
        label = scenario['name']
        
        if 'data' not in result:
            continue
            
        data = result['data']
        
        # Find time vector
        time_key = next((k for k in ['t', 'time', 'Time'] if k in data), None)
        if not time_key:
            continue
            
        t = np.array(data[time_key]).flatten()
        
        # Plot output voltage
        for voltage_key in ['Vout', 'v_out', 'output_voltage']:
            if voltage_key in data:
                v_out = np.array(data[voltage_key]).flatten()
                axes[0, 0].plot(t, v_out, label=label, color=color, linewidth=2)
                break
        
        # Plot inductor current
        for current_key in ['IL', 'i_L', 'inductor_current']:
            if current_key in data:
                i_L = np.array(data[current_key]).flatten()
                axes[0, 1].plot(t, i_L, label=label, color=color, linewidth=2)
                break
        
        # Plot input current
        for current_key in ['Iin', 'i_in', 'input_current']:
            if current_key in data:
                i_in = np.array(data[current_key]).flatten()
                axes[1, 0].plot(t, i_in, label=label, color=color, linewidth=2)
                break
        
        # Calculate and plot instantaneous power
        v_out_key = next((k for k in ['Vout', 'v_out', 'output_voltage'] 
                         if k in data), None)
        if v_out_key:
            v_out = np.array(data[v_out_key]).flatten()
            R = scenario['params']['R']
            power = v_out**2 / R
            axes[1, 1].plot(t, power, label=label, color=color, linewidth=2)
    
    # Configure subplots
    axes[0, 0].set_title('Output Voltage')
    axes[0, 0].set_xlabel('Time (s)')
    axes[0, 0].set_ylabel('Voltage (V)')
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].legend()
    
    axes[0, 1].set_title('Inductor Current')
    axes[0, 1].set_xlabel('Time (s)')
    axes[0, 1].set_ylabel('Current (A)')
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].legend()
    
    axes[1, 0].set_title('Input Current')
    axes[1, 0].set_xlabel('Time (s)')
    axes[1, 0].set_ylabel('Current (A)')
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].legend()
    
    axes[1, 1].set_title('Output Power')
    axes[1, 1].set_xlabel('Time (s)')
    axes[1, 1].set_ylabel('Power (W)')
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].legend()
    
    plt.tight_layout()
    plt.show()
    
    # Save plot
    output_dir = Path('examples_output')
    output_dir.mkdir(exist_ok=True)
    plt.savefig(output_dir / 'parameter_variation_comparison.png', 
                dpi=300, bbox_inches='tight')
    print(f"Plot saved to {output_dir / 'parameter_variation_comparison.png'}")
    
    # Print parameter summary
    print("\nParameter Variation Summary:")
    print("=" * 50)
    for result in results:
        scenario = result['scenario']
        params = scenario['params']
        print(f"\n{scenario['name']}:")
        for param, value in params.items():
            if param == 'L':
                print(f"  {param}: {value*1000:.1f} mH")
            elif param == 'C':
                print(f"  {param}: {value*1e6:.0f} μF")
            elif param in ['Vin', 'R']:
                print(f"  {param}: {value:.1f} {'V' if param.startswith('V') else 'Ω'}")
            else:
                print(f"  {param}: {value}")


if __name__ == '__main__':
    main()
