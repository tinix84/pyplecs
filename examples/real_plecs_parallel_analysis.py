#!/usr/bin/env python3
"""
Real PLECS Parallel Coordinate Analysis
Runs parametric analysis using real PLECS simulations
"""

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd

# Add pyplecs to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the parallel coordinate implementation
from parallel_coordinate_implementation import (
    PLECSParametricAnalyzer, 
    ParameterSweepDefinition, 
    KPIDefinition,
    ParameterVariationType
)

# Import PyPLECS
from pyplecs import PlecsServer


def real_plecs_demo():
    """Run parallel coordinate analysis with real PLECS simulation"""
    
    print("🔍 Running Real PLECS Parallel Coordinate Analysis")
    print("=" * 55)
    
    # Initialize PLECS and load model directly with PlecsServer
    print("🚀 Connecting to PLECS and loading model...")
    try:
        # Define paths like in the examples
        model_path = Path(__file__).parent.parent / 'data'
        model_file = 'simple_buck.plecs'
        
        if not (model_path / model_file).exists():
            print(f'❌ PLECS file not found at {model_path / model_file}')
            return None
        
        print(f"📁 Loading model: {model_path / model_file}")
        # Use the correct PlecsServer initialization pattern
        # The PlecsServer expects sim_path + '//' + sim_name internally
        plecs_server = PlecsServer(
            sim_path=str(model_path),
            sim_name=model_file,
            port='1080',
            load=True  # This loads the model automatically!
        )
        print("✅ PLECS connected and model loaded successfully")
    except Exception as e:
        print(f"❌ Failed to connect to PLECS and load model: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure PLECS is installed")
        print("2. If PLECS is running, enable XML-RPC server in File > Preferences > XML-RPC")
        print("3. Check that the port is set to 1080")
        print("4. Make sure the model file exists")
        print("5. Try starting PLECS manually first")
        return None
    
    # Create analyzer with real PLECS
    analyzer = PLECSParametricAnalyzer(plecs_server)
    
    # Define parameters to vary (matching simple_buck model)
    print("\n📋 Setting up parameter sweep...")
    analyzer.add_parameter(ParameterSweepDefinition(
        name="Vin",
        nominal_value=400.0,  # 400V input
        variation_type=ParameterVariationType.PERCENTAGE,
        variation_range=(-10, 10),  # ±10%
        steps=3  # Reduced for real simulation
    ))
    
    analyzer.add_parameter(ParameterSweepDefinition(
        name="L",
        nominal_value=0.001,  # 1mH inductance
        variation_type=ParameterVariationType.PERCENTAGE,
        variation_range=(-20, 20),  # ±20%
        steps=3  # Reduced for real simulation
    ))
    
    analyzer.add_parameter(ParameterSweepDefinition(
        name="C",
        nominal_value=0.0001,  # 100µF capacitance
        variation_type=ParameterVariationType.PERCENTAGE,
        variation_range=(-30, 30),  # ±30%
        steps=3  # Reduced for real simulation
    ))
    
    # Define KPIs to monitor (these will be extracted from real PLECS results)
    print("📊 Setting up KPI monitoring...")
    analyzer.add_kpi(KPIDefinition(
        name="Vout_avg",
        display_name="Output Voltage [V]",
        unit="V",
        target_type="target_value",
        target_value=200.0
    ))
    
    analyzer.add_kpi(KPIDefinition(
        name="Efficiency",
        display_name="Efficiency [%]",
        unit="%",
        target_type="maximize"
    ))
    
    analyzer.add_kpi(KPIDefinition(
        name="Vout_ripple",
        display_name="Voltage Ripple [%]",
        unit="%",
        target_type="minimize"
    ))
    
    # Run parametric study
    print("\n🔄 Running parametric study with real PLECS simulations...")
    print("This will take longer than the mock version...")
    
    def progress_callback(i, total, combo):
        percent = (i / total) * 100
        print(f"  Progress: {i+1}/{total} ({percent:.1f}%) - {combo}")
    
    try:
        results = analyzer.run_parametric_study(
            method='one_at_time',
            progress_callback=progress_callback
        )
        
        print(f"\n✅ Completed {len(results)} real PLECS simulations!")
        
        # Show results summary
        print("\n📈 Results Summary:")
        successful_results = results[results['success']]
        print(f"  Successful simulations: {len(successful_results)}/{len(results)}")
        
        if len(successful_results) > 0:
            kpi_cols = [kpi.name for kpi in analyzer.kpis if kpi.name in results.columns]
            param_cols = [p.name for p in analyzer.parameters if p.name in results.columns]
            
            print("\nParameter ranges:")
            for col in param_cols:
                print(f"  {col}: {results[col].min():.6f} to {results[col].max():.6f}")
                
            print("\nKPI ranges:")
            for col in kpi_cols:
                valid_data = successful_results[col].dropna()
                if len(valid_data) > 0:
                    print(f"  {col}: {valid_data.min():.3f} to {valid_data.max():.3f}")
        
        # Create plots
        if len(successful_results) >= 3:  # Need at least 3 points for meaningful plots
            print("\n📊 Creating parallel coordinate plots...")
            
            # Main parallel coordinate plot
            fig = analyzer.create_parallel_coordinate_plot()
            fig.write_html("real_plecs_parallel_plot.html")
            print("✅ Saved to real_plecs_parallel_plot.html")
            
            # Solution comparison plot
            fig_comparison = analyzer.create_solution_comparison_plot()
            fig_comparison.write_html("real_plecs_solution_comparison.html")
            print("✅ Saved to real_plecs_solution_comparison.html")
            
            print("\n🎉 Real PLECS parallel coordinate analysis completed!")
            print("📁 Open the HTML files to view the interactive plots.")
        else:
            print("⚠️  Not enough successful simulations to create meaningful plots")
            
    except Exception as e:
        print(f"❌ Parametric study failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    return analyzer, results


if __name__ == "__main__":
    result = real_plecs_demo()
    
    if result is not None:
        analyzer, results = result
        print(f"\n📋 Final Results Shape: {results.shape}")
        print("\nFirst few results:")
        print(results.head())
    else:
        print("\n❌ Real PLECS not available - showing mock demo instead")
        print("\n🔧 To run with real PLECS:")
        print("1. Start PLECS application")
        print("2. Enable XML-RPC server in File > Preferences > XML-RPC")
        print("3. Set port to 1080")
        print("4. Re-run this script")
        
        # Show what the analysis would look like
        print("\n📋 This analysis would run the following:")
        print("  Parameters to sweep:")
        print("    - Vin: 360V to 440V (±10%)")
        print("    - L: 0.8mH to 1.2mH (±20%)")
        print("    - C: 70µF to 130µF (±30%)")
        print("  KPIs to monitor:")
        print("    - Output Voltage [V] (target: 200V)")
        print("    - Efficiency [%] (maximize)")
        print("    - Voltage Ripple [%] (minimize)")
        print("  Total simulations: 27 (3×3×3)")
        print("\n💡 Run parallel_coordinate_implementation.py for mock version")
