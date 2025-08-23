"""Buck converter parameter study example.

This example demonstrates how to parse a PLECS model to understand its structure,
then run simulations with different parameter combinations and plot the results.
"""
import time
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

try:
    from pyplecs import PlecsApp, PlecsServer
    from pyplecs.plecs_parser import plecs_overview
except ImportError as e:
    print(f"PyPLECS not properly installed: {e}")
    print("Please install with: pip install -e .")
    exit(1)


def main():
    """Parse model structure and run parameter studies."""
    model_path = Path(__file__).parent.parent / 'data'
    model_file = 'simple_buck.plecs'
    
    if not (model_path / model_file).exists():
        print(f'PLECS file not found at {model_path / model_file}')
        return

    # First, parse the model to understand its structure
    print("Parsing PLECS model structure...")
    try:
        overview = plecs_overview(str(model_path / model_file))
        print('Model overview:')
        for k, v in overview.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"Error parsing model: {e}")
        return

    print("\nStarting PLECS application...")
    app = PlecsApp()
    
    try:
        # Start PLECS
        app.open_plecs()
        time.sleep(3)  # Wait for PLECS to start
        
        # Set high priority for better performance
        app.set_plecs_high_priority()
        
        print("Connecting to PLECS server...")
        # Connect to PLECS server
        server = PlecsServer(
            sim_path=str(model_path),
            sim_name=model_file,
            port='1080',
            load=True
        )
        
        # Define parameter study cases
        study_cases = [
            {'name': 'Low Power', 'Vin': 300.0, 'Vout': 150.0, 'R': 20.0},
            {'name': 'Medium Power', 'Vin': 400.0, 'Vout': 200.0, 'R': 10.0},
            {'name': 'High Power', 'Vin': 500.0, 'Vout': 250.0, 'R': 5.0},
        ]
        
        results = []
        print(f"\nRunning {len(study_cases)} simulation cases...")
        
        for i, case in enumerate(study_cases):
            print(f"Case {i+1}: {case['name']}")
            
            # Prepare simulation inputs
            inputs = {
                'Vin': case['Vin'],
                'Vout': case['Vout'],
                'R': case['R'],
                'L': 1e-3,       # Fixed inductance
                'C': 100e-6,     # Fixed capacitance
            }
            
            print(f"  Parameters: {inputs}")
            
            # Run simulation
            result = server.run_sim_single(inputs, timeout=30.0)
            
            if result and 'status' in result and result['status'] == 'success':
                print("  ✓ Simulation successful")
                result['case_name'] = case['name']
                result['parameters'] = inputs
                results.append(result)
            else:
                print(f"  ✗ Simulation failed: {result}")
        
        # Plot comparison results
        if results:
            print(f"\nPlotting results from {len(results)} successful cases...")
            plot_parameter_study(results)
        else:
            print("No successful simulations to plot")
            
    except Exception as e:
        print(f"Error during simulation: {e}")
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


def plot_parameter_study(results):
    """Plot comparison of different parameter study cases."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Buck Converter Parameter Study Results')
    
    colors = ['blue', 'red', 'green', 'orange', 'purple']
    
    for i, result in enumerate(results):
        case_name = result['case_name']
        color = colors[i % len(colors)]
        
        if 'data' in result:
            data = result['data']
            
            # Find time vector
            time_key = None
            for key in ['t', 'time', 'Time']:
                if key in data:
                    time_key = key
                    break
            
            if time_key:
                t = np.array(data[time_key]).flatten()
                
                # Plot output voltage
                for voltage_key in ['Vout', 'v_out', 'output_voltage']:
                    if voltage_key in data:
                        v_out = np.array(data[voltage_key]).flatten()
                        axes[0, 0].plot(t, v_out, label=case_name, color=color)
                        break
                
                # Plot inductor current
                for current_key in ['IL', 'i_L', 'inductor_current']:
                    if current_key in data:
                        i_L = np.array(data[current_key]).flatten()
                        axes[0, 1].plot(t, i_L, label=case_name, color=color)
                        break
                
                # Plot efficiency vs time (if available)
                efficiency_plotted = False
                for eff_key in ['efficiency', 'eta']:
                    if eff_key in data:
                        eff = np.array(data[eff_key]).flatten()
                        axes[1, 0].plot(t, eff * 100, label=case_name, color=color)
                        efficiency_plotted = True
                        break
                
                if not efficiency_plotted:
                    # Calculate approximate efficiency from P_out/P_in
                    v_in_key = next((k for k in ['Vin', 'v_in', 'input_voltage'] if k in data), None)
                    i_in_key = next((k for k in ['Iin', 'i_in', 'input_current'] if k in data), None)
                    v_out_key = next((k for k in ['Vout', 'v_out', 'output_voltage'] if k in data), None)
                    
                    if v_in_key and i_in_key and v_out_key:
                        v_in = np.array(data[v_in_key]).flatten()
                        i_in = np.array(data[i_in_key]).flatten()
                        v_out = np.array(data[v_out_key]).flatten()
                        R = result['parameters']['R']
                        
                        p_in = v_in * i_in
                        p_out = v_out**2 / R
                        efficiency = np.where(p_in > 0, p_out / p_in * 100, 0)
                        
                        axes[1, 0].plot(t, efficiency, label=case_name, color=color)
    
    # Set up plot properties
    axes[0, 0].set_title('Output Voltage')
    axes[0, 0].set_xlabel('Time (s)')
    axes[0, 0].set_ylabel('Voltage (V)')
    axes[0, 0].grid(True)
    axes[0, 0].legend()
    
    axes[0, 1].set_title('Inductor Current')
    axes[0, 1].set_xlabel('Time (s)')
    axes[0, 1].set_ylabel('Current (A)')
    axes[0, 1].grid(True)
    axes[0, 1].legend()
    
    axes[1, 0].set_title('Efficiency')
    axes[1, 0].set_xlabel('Time (s)')
    axes[1, 0].set_ylabel('Efficiency (%)')
    axes[1, 0].grid(True)
    axes[1, 0].legend()
    
    # Plot parameter summary
    axes[1, 1].axis('off')
    summary_text = "Parameter Study Summary:\n\n"
    for result in results:
        params = result['parameters']
        summary_text += f"{result['case_name']}:\n"
        summary_text += f"  Vin: {params['Vin']} V\n"
        summary_text += f"  Vout: {params['Vout']} V\n"
        summary_text += f"  R: {params['R']} Ω\n"
        summary_text += f"  Power: {params['Vout']**2/params['R']:.1f} W\n\n"
    
    axes[1, 1].text(0.1, 0.9, summary_text, transform=axes[1, 1].transAxes,
                    verticalalignment='top', fontsize=10, fontfamily='monospace')
    
    plt.tight_layout()
    plt.show()
    
    # Save plot
    output_dir = Path('examples_output')
    output_dir.mkdir(exist_ok=True)
    plt.savefig(output_dir / 'parameter_study_results.png', dpi=300, bbox_inches='tight')
    print(f"Plot saved to {output_dir / 'parameter_study_results.png'}")


if __name__ == '__main__':
    main()
