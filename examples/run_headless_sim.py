"""Headless simulation example with batch processing.

This example demonstrates running multiple PLECS simulations in headless mode
using the XML-RPC interface, processing results, and generating summary reports.
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
    """Run headless batch simulations and generate summary report."""
    model_path = Path(__file__).parent.parent / 'data'
    model_file = 'simple_buck.plecs'
    
    if not (model_path / model_file).exists():
        print(f'PLECS file not found at {model_path / model_file}')
        return

    print("Starting PLECS in headless mode...")
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
        
        # Define batch simulation test matrix
        test_matrix = generate_test_matrix()
        
        print(f"Running {len(test_matrix)} headless simulations...")
        
        results = []
        failed_cases = []
        
        for i, test_case in enumerate(test_matrix):
            print(f"\nTest {i+1}/{len(test_matrix)}: {test_case['name']}")
            print(f"  Parameters: {test_case['params']}")
            
            try:
                # Run simulation with datastream (headless mode)
                result = server.run_sim_with_datastream(
                    test_case['params'],
                    timeout=30.0
                )
                
                if result and 'status' in result and result['status'] == 'success':
                    print("  ✓ Simulation completed")
                    result['test_case'] = test_case
                    results.append(result)
                else:
                    print(f"  ✗ Simulation failed: {result}")
                    failed_cases.append(test_case)
                    
            except Exception as e:
                print(f"  ✗ Error: {e}")
                failed_cases.append(test_case)
        
        # Process and analyze results
        if results:
            print(f"\nProcessing {len(results)} successful simulations...")
            process_batch_results(results, failed_cases)
        else:
            print("No successful simulations to process")
            
    except Exception as e:
        print(f"Error during headless simulation batch: {e}")
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


def generate_test_matrix():
    """Generate a test matrix for batch simulations."""
    
    # Define parameter ranges for design space exploration
    input_voltages = [300, 400, 500]
    voltage_ratios = [0.4, 0.5, 0.6]
    load_powers = [100, 200, 300]  # Watts
    
    test_matrix = []
    
    for vin in input_voltages:
        for ratio in voltage_ratios:
            for power in load_powers:
                vout = vin * ratio
                r_load = vout**2 / power  # Calculate load resistance
                
                test_case = {
                    'name': f'V{vin}_R{ratio:.1f}_P{power}W',
                    'params': {
                        'Vin': vin,
                        'Vout': vout,
                        'R': r_load,
                        'L': 1e-3,    # Fixed inductance
                        'C': 100e-6,  # Fixed capacitance
                    },
                    'expected_power': power,
                    'voltage_ratio': ratio,
                    'input_voltage': vin
                }
                test_matrix.append(test_case)
    
    return test_matrix


def process_batch_results(results, failed_cases):
    """Process batch simulation results and generate analysis."""
    
    print("Extracting performance metrics...")
    
    # Extract key performance metrics
    metrics = []
    
    for result in results:
        test_case = result['test_case']
        
        if 'data' not in result:
            continue
            
        data = result['data']
        
        # Find time vector
        time_key = next((k for k in ['t', 'time', 'Time'] if k in data), None)
        if not time_key:
            continue
            
        t = np.array(data[time_key]).flatten()
        
        # Calculate steady-state metrics (last 20% of simulation)
        steady_start = int(0.8 * len(t))
        
        metric = {
            'test_name': test_case['name'],
            'input_voltage': test_case['input_voltage'],
            'voltage_ratio': test_case['voltage_ratio'],
            'expected_power': test_case['expected_power'],
            'load_resistance': test_case['params']['R']
        }
        
        # Extract steady-state values
        for key_list, metric_name in [
            (['Vout', 'v_out', 'output_voltage'], 'output_voltage'),
            (['Vin', 'v_in', 'input_voltage'], 'input_voltage_actual'),
            (['IL', 'i_L', 'inductor_current'], 'inductor_current'),
            (['Iin', 'i_in', 'input_current'], 'input_current'),
        ]:
            for data_key in key_list:
                if data_key in data:
                    values = np.array(data[data_key]).flatten()
                    metric[metric_name] = np.mean(values[steady_start:])
                    metric[f'{metric_name}_ripple'] = np.std(values[steady_start:])
                    break
        
        # Calculate derived performance metrics
        if 'output_voltage' in metric and 'input_current' in metric:
            p_in = metric['input_voltage'] * metric['input_current']
            p_out = metric['output_voltage']**2 / metric['load_resistance']
            
            metric['power_input'] = p_in
            metric['power_output'] = p_out
            metric['efficiency'] = (p_out / p_in * 100) if p_in > 0 else 0
            metric['power_error'] = abs(p_out - metric['expected_power']) / metric['expected_power'] * 100
            
            # Voltage regulation
            expected_vout = metric['input_voltage'] * metric['voltage_ratio']
            metric['voltage_regulation'] = abs(metric['output_voltage'] - expected_vout) / expected_vout * 100
        
        metrics.append(metric)
    
    # Generate analysis plots
    create_batch_analysis_plots(metrics, failed_cases)
    
    # Generate summary report
    generate_summary_report(metrics, failed_cases)


def create_batch_analysis_plots(metrics, failed_cases):
    """Create comprehensive analysis plots for batch results."""
    
    if not metrics:
        print("No metrics available for plotting")
        return
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Headless Batch Simulation Analysis', fontsize=16)
    
    # Extract data for plotting
    input_voltages = [m['input_voltage'] for m in metrics]
    efficiencies = [m.get('efficiency', 0) for m in metrics]
    power_errors = [m.get('power_error', 0) for m in metrics]
    voltage_regulations = [m.get('voltage_regulation', 0) for m in metrics]
    power_outputs = [m.get('power_output', 0) for m in metrics]
    voltage_ratios = [m['voltage_ratio'] for m in metrics]
    
    # Plot 1: Efficiency vs Input Voltage
    scatter1 = axes[0, 0].scatter(input_voltages, efficiencies, 
                                 c=voltage_ratios, cmap='viridis', s=60, alpha=0.7)
    axes[0, 0].set_xlabel('Input Voltage (V)')
    axes[0, 0].set_ylabel('Efficiency (%)')
    axes[0, 0].set_title('Efficiency vs Input Voltage')
    axes[0, 0].grid(True, alpha=0.3)
    plt.colorbar(scatter1, ax=axes[0, 0], label='Voltage Ratio')
    
    # Plot 2: Power Error vs Expected Power
    expected_powers = [m['expected_power'] for m in metrics]
    axes[0, 1].scatter(expected_powers, power_errors, c=input_voltages, 
                      cmap='plasma', s=60, alpha=0.7)
    axes[0, 1].set_xlabel('Expected Power (W)')
    axes[0, 1].set_ylabel('Power Error (%)')
    axes[0, 1].set_title('Power Accuracy')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Plot 3: Voltage Regulation vs Voltage Ratio
    axes[0, 2].scatter(voltage_ratios, voltage_regulations, c=input_voltages,
                      cmap='coolwarm', s=60, alpha=0.7)
    axes[0, 2].set_xlabel('Voltage Ratio')
    axes[0, 2].set_ylabel('Voltage Regulation (%)')
    axes[0, 2].set_title('Voltage Regulation Performance')
    axes[0, 2].grid(True, alpha=0.3)
    
    # Plot 4: Efficiency Distribution
    axes[1, 0].hist(efficiencies, bins=10, alpha=0.7, edgecolor='black')
    axes[1, 0].set_xlabel('Efficiency (%)')
    axes[1, 0].set_ylabel('Frequency')
    axes[1, 0].set_title('Efficiency Distribution')
    axes[1, 0].axvline(np.mean(efficiencies), color='red', linestyle='--', 
                      label=f'Mean: {np.mean(efficiencies):.1f}%')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Plot 5: Power Output vs Input Power
    power_inputs = [m.get('power_input', 0) for m in metrics]
    axes[1, 1].scatter(power_inputs, power_outputs, c=efficiencies,
                      cmap='RdYlGn', s=60, alpha=0.7)
    axes[1, 1].plot([0, max(power_inputs)], [0, max(power_inputs)], 
                   'k--', alpha=0.5, label='100% Efficiency')
    axes[1, 1].set_xlabel('Input Power (W)')
    axes[1, 1].set_ylabel('Output Power (W)')
    axes[1, 1].set_title('Power Transfer Characteristics')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    # Plot 6: Test Results Summary
    axes[1, 2].axis('off')
    
    # Create summary statistics
    summary_text = f"""
Batch Simulation Summary
{'='*25}
Total Tests: {len(metrics) + len(failed_cases)}
Successful: {len(metrics)}
Failed: {len(failed_cases)}

Performance Statistics:
Average Efficiency: {np.mean(efficiencies):.1f}%
Min Efficiency: {np.min(efficiencies):.1f}%
Max Efficiency: {np.max(efficiencies):.1f}%

Average Power Error: {np.mean(power_errors):.2f}%
Average Voltage Reg: {np.mean(voltage_regulations):.2f}%

Input Voltage Range: {min(input_voltages)}-{max(input_voltages)}V
Power Range: {min(expected_powers)}-{max(expected_powers)}W
"""
    
    axes[1, 2].text(0.1, 0.9, summary_text, transform=axes[1, 2].transAxes,
                    verticalalignment='top', fontsize=10, fontfamily='monospace')
    
    plt.tight_layout()
    plt.show()
    
    # Save plot
    output_dir = Path('examples_output')
    output_dir.mkdir(exist_ok=True)
    plt.savefig(output_dir / 'headless_batch_analysis.png', 
                dpi=300, bbox_inches='tight')
    print(f"Analysis plot saved to {output_dir / 'headless_batch_analysis.png'}")


def generate_summary_report(metrics, failed_cases):
    """Generate and save a detailed summary report."""
    
    output_dir = Path('examples_output')
    output_dir.mkdir(exist_ok=True)
    
    report_file = output_dir / 'headless_simulation_report.txt'
    
    with open(report_file, 'w') as f:
        f.write("HEADLESS BATCH SIMULATION REPORT\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"Execution Summary:\n")
        f.write(f"  Total test cases: {len(metrics) + len(failed_cases)}\n")
        f.write(f"  Successful simulations: {len(metrics)}\n")
        f.write(f"  Failed simulations: {len(failed_cases)}\n")
        f.write(f"  Success rate: {len(metrics)/(len(metrics)+len(failed_cases))*100:.1f}%\n\n")
        
        if failed_cases:
            f.write("Failed Test Cases:\n")
            for case in failed_cases:
                f.write(f"  - {case['name']}\n")
            f.write("\n")
        
        if metrics:
            efficiencies = [m.get('efficiency', 0) for m in metrics]
            power_errors = [m.get('power_error', 0) for m in metrics]
            voltage_regs = [m.get('voltage_regulation', 0) for m in metrics]
            
            f.write("Performance Statistics:\n")
            f.write(f"  Efficiency - Mean: {np.mean(efficiencies):.1f}%, ")
            f.write(f"Std: {np.std(efficiencies):.1f}%, ")
            f.write(f"Range: {np.min(efficiencies):.1f}-{np.max(efficiencies):.1f}%\n")
            
            f.write(f"  Power Error - Mean: {np.mean(power_errors):.2f}%, ")
            f.write(f"Std: {np.std(power_errors):.2f}%, ")
            f.write(f"Max: {np.max(power_errors):.2f}%\n")
            
            f.write(f"  Voltage Regulation - Mean: {np.mean(voltage_regs):.2f}%, ")
            f.write(f"Std: {np.std(voltage_regs):.2f}%, ")
            f.write(f"Max: {np.max(voltage_regs):.2f}%\n\n")
            
            f.write("Detailed Results:\n")
            f.write("-" * 80 + "\n")
            header = f"{'Test Name':<20} {'Eff(%)':<8} {'P_Err(%)':<10} {'V_Reg(%)':<10} {'P_Out(W)':<10}\n"
            f.write(header)
            f.write("-" * 80 + "\n")
            
            for m in metrics:
                line = f"{m['test_name']:<20} "
                line += f"{m.get('efficiency', 0):>7.1f} "
                line += f"{m.get('power_error', 0):>9.2f} "
                line += f"{m.get('voltage_regulation', 0):>9.2f} "
                line += f"{m.get('power_output', 0):>9.1f}\n"
                f.write(line)
    
    print(f"Detailed report saved to {report_file}")
    
    # Also save metrics as CSV for further analysis
    try:
        import pandas as pd
        df = pd.DataFrame(metrics)
        csv_file = output_dir / 'headless_simulation_metrics.csv'
        df.to_csv(csv_file, index=False)
        print(f"Metrics CSV saved to {csv_file}")
    except ImportError:
        print("pandas not available, skipping CSV export")


if __name__ == '__main__':
    main()
