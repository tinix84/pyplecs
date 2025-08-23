"""Simple simulation example with PLECS integration.

This example demonstrates basic simulation setup and execution using PlecsApp.
It starts PLECS, runs a simulation, and plots the results.
"""
import time
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

try:
    from pyplecs import PlecsApp, PlecsServer
    print("Successfully imported PlecsApp and PlecsServer")
except ImportError as e:
    print(f"Import failed: {e}")
    print("PyPLECS not properly installed. Please install with: pip install -e .")
    exit(1)


def main():
    """Run a simple buck converter simulation and plot results."""
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
        
        print("Running simulation...")
        # Define simulation parameters
        inputs = {
            'Vin': 400.0,    # Input voltage
            'Vout': 200.0,   # Output voltage
            'L': 1e-3,       # Inductance
            'C': 100e-6,     # Capacitance
            'R': 10.0        # Load resistance
        }
        
        # Run simulation
        result = server.run_sim_single(inputs, timeout=30.0)
        
        if result and 'status' in result and result['status'] == 'success':
            print("Simulation completed successfully!")
            
            # Extract and plot results if available
            if 'data' in result:
                data = result['data']
                print(f"Simulation data keys: {list(data.keys())}")
                
                # Create plots
                fig, axes = plt.subplots(2, 2, figsize=(12, 8))
                fig.suptitle('Buck Converter Simulation Results')
                
                # Plot time domain results (assuming common PLECS scope names)
                time_key = None
                for key in ['t', 'time', 'Time']:
                    if key in data:
                        time_key = key
                        break
                
                if time_key:
                    t = np.array(data[time_key]).flatten()
                    
                    # Plot input voltage if available
                    for voltage_key in ['Vin', 'v_in', 'input_voltage']:
                        if voltage_key in data:
                            axes[0,0].plot(t, np.array(data[voltage_key]).flatten())
                            axes[0,0].set_title('Input Voltage')
                            axes[0,0].set_xlabel('Time (s)')
                            axes[0,0].set_ylabel('Voltage (V)')
                            axes[0,0].grid(True)
                            break
                    
                    # Plot output voltage if available
                    for voltage_key in ['Vout', 'v_out', 'output_voltage']:
                        if voltage_key in data:
                            axes[0,1].plot(t, np.array(data[voltage_key]).flatten())
                            axes[0,1].set_title('Output Voltage')
                            axes[0,1].set_xlabel('Time (s)')
                            axes[0,1].set_ylabel('Voltage (V)')
                            axes[0,1].grid(True)
                            break
                    
                    # Plot inductor current if available
                    for current_key in ['IL', 'i_L', 'inductor_current']:
                        if current_key in data:
                            axes[1,0].plot(t, np.array(data[current_key]).flatten())
                            axes[1,0].set_title('Inductor Current')
                            axes[1,0].set_xlabel('Time (s)')
                            axes[1,0].set_ylabel('Current (A)')
                            axes[1,0].grid(True)
                            break
                    
                    # Plot power if available or calculate from V*I
                    power_plotted = False
                    for power_key in ['P', 'power', 'output_power']:
                        if power_key in data:
                            axes[1,1].plot(t, np.array(data[power_key]).flatten())
                            axes[1,1].set_title('Output Power')
                            axes[1,1].set_xlabel('Time (s)')
                            axes[1,1].set_ylabel('Power (W)')
                            axes[1,1].grid(True)
                            power_plotted = True
                            break
                    
                    if not power_plotted:
                        # Try to calculate power from voltage and current
                        v_out = None
                        i_out = None
                        for v_key in ['Vout', 'v_out', 'output_voltage']:
                            if v_key in data:
                                v_out = np.array(data[v_key]).flatten()
                                break
                        for i_key in ['Iout', 'i_out', 'output_current']:
                            if i_key in data:
                                i_out = np.array(data[i_key]).flatten()
                                break
                        
                        if v_out is not None and i_out is not None:
                            power = v_out * i_out
                            axes[1,1].plot(t, power)
                            axes[1,1].set_title('Output Power (calculated)')
                            axes[1,1].set_xlabel('Time (s)')
                            axes[1,1].set_ylabel('Power (W)')
                            axes[1,1].grid(True)
                
                plt.tight_layout()
                plt.show()
                
                # Save plot
                output_dir = Path('examples_output')
                output_dir.mkdir(exist_ok=True)
                plt.savefig(output_dir / 'simple_simulation_results.png', dpi=300, bbox_inches='tight')
                print(f"Plot saved to {output_dir / 'simple_simulation_results.png'}")
                
            else:
                print("No simulation data returned")
        else:
            print(f"Simulation failed: {result}")
            
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


if __name__ == '__main__':
    main()
