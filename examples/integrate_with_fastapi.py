"""FastAPI integration example with PLECS simulation endpoints.

This example demonstrates how to create a web API for PLECS simulations using FastAPI.
It provides endpoints for running simulations, querying model parameters, and 
retrieving results with automatic plotting.

Features:
- Non-blocking PLECS initialization
- Real simulation execution with run_sim_with_datastream
- Comprehensive error handling and timeouts
- Background plot generation
- Interactive API documentation
"""
import time
import os
import sys
from pathlib import Path
import json
from typing import Dict, Any, List, Optional
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server deployment
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Setup for proper imports
script_dir = Path(__file__).parent
project_root = script_dir.parent
os.chdir(project_root)
sys.path.insert(0, str(project_root))

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.responses import JSONResponse, FileResponse
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("FastAPI not installed. Install with: pip install fastapi[all] uvicorn")
    exit(1)

try:
    from pyplecs.pyplecs import PlecsApp, PlecsServer
except ImportError:
    print("PyPLECS not properly installed. Please install with: pip install -e .")
    exit(1)


# Pydantic models for API requests/responses
class SimulationRequest(BaseModel):
    parameters: Dict[str, float]
    timeout: float = 30.0
    save_plot: bool = True


class SimulationResponse(BaseModel):
    simulation_id: str
    status: str
    message: str
    results: Optional[Dict[str, Any]] = None
    plot_url: Optional[str] = None


class ParameterInfo(BaseModel):
    name: str
    description: str
    default_value: float
    unit: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None


# Global variables for PLECS management
plecs_app = None
plecs_server = None
simulation_results = {}
plecs_initialized = False
initialization_error = None


def startup_plecs():
    """Initialize PLECS application and server."""
    global plecs_app, plecs_server, plecs_initialized, initialization_error
    
    try:
        print("Starting PLECS application...")
        model_path = Path('data')
        model_file = 'simple_buck.plecs'
        
        if not (model_path / model_file).exists():
            raise RuntimeError(f'PLECS file not found at {model_path / model_file}')
        
        plecs_app = PlecsApp()
        plecs_app.open_plecs()
        time.sleep(3)  # Wait for PLECS to start
        plecs_app.set_plecs_high_priority()
        
        plecs_server = PlecsServer(
            sim_path=str(model_path.absolute()),
            sim_name=model_file,
            port='1080',
            load=True
        )
        
        plecs_initialized = True
        print("✓ PLECS initialized successfully")
        
    except Exception as e:
        initialization_error = str(e)
        plecs_initialized = False
        print(f"✗ Failed to initialize PLECS: {e}")


def shutdown_plecs():
    """Clean up PLECS application."""
    global plecs_app, plecs_server, plecs_initialized
    
    if plecs_server:
        try:
            plecs_server.close()
        except:
            pass
    
    if plecs_app:
        try:
            plecs_app.kill_plecs()
        except:
            pass
    
    plecs_initialized = False
    print("PLECS shut down")


def ensure_plecs_ready():
    """Ensure PLECS is ready or raise appropriate error."""
    if not plecs_initialized:
        if initialization_error:
            raise HTTPException(
                status_code=500, 
                detail=f"PLECS initialization failed: {initialization_error}"
            )
        else:
            # Try to initialize if not done yet
            startup_plecs()
            if not plecs_initialized:
                raise HTTPException(
                    status_code=503, 
                    detail="PLECS server not ready. Please try again in a moment."
                )


# Create FastAPI application
app = FastAPI(
    title="PLECS Simulation API",
    description="REST API for running PLECS simulations",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Initialize PLECS on API startup (non-blocking)."""
    # Don't block startup - initialize in background
    print("FastAPI server starting...")
    print("PLECS will be initialized on first request")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up PLECS on API shutdown."""
    shutdown_plecs()


@app.get("/")
async def root():
    """API root endpoint."""
    status = "initialized" if plecs_initialized else "not_initialized"
    if initialization_error:
        status = f"error: {initialization_error}"
        
    return {
        "message": "PLECS Simulation API",
        "version": "1.0.0",
        "plecs_status": status,
        "endpoints": {
            "simulate": "/simulate",
            "parameters": "/parameters", 
            "results": "/results/{simulation_id}",
            "plot": "/plot/{simulation_id}",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "plecs_initialized": plecs_initialized,
        "initialization_error": initialization_error,
        "timestamp": time.time()
    }


@app.get("/parameters", response_model=List[ParameterInfo])
async def get_parameters():
    """Get available simulation parameters."""
    
    # Define available parameters for buck converter
    parameters = [
        ParameterInfo(
            name="Vin",
            description="Input voltage",
            default_value=400.0,
            unit="V",
            min_value=100.0,
            max_value=600.0
        ),
        ParameterInfo(
            name="Vout",
            description="Output voltage (target)",
            default_value=200.0,
            unit="V",
            min_value=50.0,
            max_value=500.0
        ),
        ParameterInfo(
            name="L",
            description="Inductance",
            default_value=1e-3,
            unit="H",
            min_value=0.1e-3,
            max_value=10e-3
        ),
        ParameterInfo(
            name="C",
            description="Capacitance",
            default_value=100e-6,
            unit="F",
            min_value=10e-6,
            max_value=1000e-6
        ),
        ParameterInfo(
            name="R",
            description="Load resistance",
            default_value=10.0,
            unit="Ω",
            min_value=1.0,
            max_value=100.0
        )
    ]
    
    return parameters


@app.post("/simulate", response_model=SimulationResponse)
async def run_simulation(request: SimulationRequest, 
                        background_tasks: BackgroundTasks):
    """Run a PLECS simulation with given parameters."""
    
    # Ensure PLECS is ready
    ensure_plecs_ready()
    
    # Generate unique simulation ID
    simulation_id = f"sim_{int(time.time()*1000)}"
    
    try:
        print(f"Running simulation {simulation_id}")
        print(f"Parameters: {request.parameters}")
        
        # Use the working run_sim_with_datastream method
        result = plecs_server.run_sim_with_datastream(
            param_dict=request.parameters
        )
        
        print(f"Simulation result type: {type(result)}")
        if result is not None:
            result_keys = list(result.keys()) if isinstance(result, dict) else "Not a dict"
            print(f"Result keys: {result_keys}")
        
        if result is not None:
            # Check if result contains simulation data
            has_time = 'Time' in result if isinstance(result, dict) else hasattr(result, 'Time')
            has_values = 'Values' in result if isinstance(result, dict) else hasattr(result, 'Values')
            
            if has_time and has_values:
                # Store results
                simulation_results[simulation_id] = {
                    'parameters': request.parameters,
                    'result': result,
                    'timestamp': time.time(),
                    'success': True
                }
                
                plot_url = None
                if request.save_plot:
                    # Schedule plot generation in background
                    background_tasks.add_task(
                        generate_simulation_plot, simulation_id, result
                    )
                    plot_url = f"/plot/{simulation_id}"
                
                # Extract basic info for response
                time_data = result['Time'] if isinstance(result, dict) else result.Time
                values_data = result['Values'] if isinstance(result, dict) else result.Values
                
                response = SimulationResponse(
                    simulation_id=simulation_id,
                    status="success",
                    message=f"Simulation completed successfully with {len(time_data)} time points",
                    results={
                        'time_points': len(time_data),
                        'output_signals': len(values_data) if hasattr(values_data, '__len__') else 1,
                        'parameters_used': request.parameters,
                        'has_plot': request.save_plot
                    },
                    plot_url=plot_url
                )
            else:
                # Simulation ran but no standard output data
                simulation_results[simulation_id] = {
                    'parameters': request.parameters,
                    'result': result,
                    'timestamp': time.time(),
                    'success': True
                }
                
                response = SimulationResponse(
                    simulation_id=simulation_id,
                    status="success",
                    message="Simulation completed (no Time/Values output data)",
                    results={
                        'result_type': str(type(result)),
                        'parameters_used': request.parameters
                    }
                )
        else:
            # Simulation returned None
            response = SimulationResponse(
                simulation_id=simulation_id,
                status="failed",
                message="Simulation returned no data"
            )
            
    except Exception as e:
        print(f"Error during simulation: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        response = SimulationResponse(
            simulation_id=simulation_id,
            status="error",
            message=f"Error during simulation: {str(e)}"
        )
    
    return response


@app.get("/results/{simulation_id}")
async def get_simulation_results(simulation_id: str):
    """Get detailed results for a specific simulation."""
    
    if simulation_id not in simulation_results:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    stored_result = simulation_results[simulation_id]
    result = stored_result['result']
    
    # Extract key metrics if data is available
    metrics = {}
    if 'data' in result:
        data = result['data']
        
        # Find time vector
        time_key = next((k for k in ['t', 'time', 'Time'] if k in data), None)
        if time_key:
            t = np.array(data[time_key]).flatten()
            steady_start = int(0.8 * len(t))  # Last 20% for steady-state
            
            # Calculate steady-state metrics
            for key_list, metric_name in [
                (['Vout', 'v_out', 'output_voltage'], 'output_voltage'),
                (['IL', 'i_L', 'inductor_current'], 'inductor_current'),
                (['Iin', 'i_in', 'input_current'], 'input_current'),
            ]:
                for data_key in key_list:
                    if data_key in data:
                        values = np.array(data[data_key]).flatten()
                        metrics[metric_name] = {
                            'mean': float(np.mean(values[steady_start:])),
                            'std': float(np.std(values[steady_start:])),
                            'min': float(np.min(values[steady_start:])),
                            'max': float(np.max(values[steady_start:]))
                        }
                        break
            
            # Calculate efficiency if possible
            params = stored_result['parameters']
            if 'output_voltage' in metrics and 'input_current' in metrics:
                v_out = metrics['output_voltage']['mean']
                i_in = metrics['input_current']['mean']
                vin = params.get('Vin', 400)
                r_load = params.get('R', 10)
                
                p_in = vin * i_in
                p_out = v_out**2 / r_load
                efficiency = (p_out / p_in * 100) if p_in > 0 else 0
                
                metrics['efficiency'] = {
                    'power_input': p_in,
                    'power_output': p_out,
                    'efficiency_percent': efficiency
                }
    
    return {
        'simulation_id': simulation_id,
        'parameters': stored_result['parameters'],
        'timestamp': stored_result['timestamp'],
        'status': result.get('status', 'unknown'),
        'data_keys': list(result.get('data', {}).keys()),
        'metrics': metrics
    }


@app.get("/plot/{simulation_id}")
async def get_simulation_plot(simulation_id: str):
    """Get the plot file for a specific simulation."""
    
    plot_file = Path('examples_output') / f'simulation_plot_{simulation_id}.png'
    
    if not plot_file.exists():
        raise HTTPException(status_code=404, detail="Plot not found")
    
    return FileResponse(plot_file, media_type='image/png')


def generate_simulation_plot(simulation_id: str, result: Dict[str, Any]):
    """Generate a plot for simulation results (background task)."""
    
    if 'data' not in result:
        return
    
    data = result['data']
    
    # Find time vector
    time_key = next((k for k in ['t', 'time', 'Time'] if k in data), None)
    if not time_key:
        return
    
    t = np.array(data[time_key]).flatten()
    
    # Create plot
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(f'Simulation Results - {simulation_id}')
    
    # Plot output voltage
    for voltage_key in ['Vout', 'v_out', 'output_voltage']:
        if voltage_key in data:
            v_out = np.array(data[voltage_key]).flatten()
            axes[0, 0].plot(t, v_out)
            axes[0, 0].set_title('Output Voltage')
            axes[0, 0].set_xlabel('Time (s)')
            axes[0, 0].set_ylabel('Voltage (V)')
            axes[0, 0].grid(True)
            break
    
    # Plot inductor current
    for current_key in ['IL', 'i_L', 'inductor_current']:
        if current_key in data:
            i_L = np.array(data[current_key]).flatten()
            axes[0, 1].plot(t, i_L)
            axes[0, 1].set_title('Inductor Current')
            axes[0, 1].set_xlabel('Time (s)')
            axes[0, 1].set_ylabel('Current (A)')
            axes[0, 1].grid(True)
            break
    
    # Plot input current
    for current_key in ['Iin', 'i_in', 'input_current']:
        if current_key in data:
            i_in = np.array(data[current_key]).flatten()
            axes[1, 0].plot(t, i_in)
            axes[1, 0].set_title('Input Current')
            axes[1, 0].set_xlabel('Time (s)')
            axes[1, 0].set_ylabel('Current (A)')
            axes[1, 0].grid(True)
            break
    
    # Plot power
    v_out_key = next((k for k in ['Vout', 'v_out', 'output_voltage'] if k in data), None)
    if v_out_key and simulation_id in simulation_results:
        v_out = np.array(data[v_out_key]).flatten()
        params = simulation_results[simulation_id]['parameters']
        r_load = params.get('R', 10)
        power = v_out**2 / r_load
        
        axes[1, 1].plot(t, power)
        axes[1, 1].set_title('Output Power')
        axes[1, 1].set_xlabel('Time (s)')
        axes[1, 1].set_ylabel('Power (W)')
        axes[1, 1].grid(True)
    
    plt.tight_layout()
    
    # Save plot
    output_dir = Path('examples_output')
    output_dir.mkdir(exist_ok=True)
    plot_file = output_dir / f'simulation_plot_{simulation_id}.png'
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    print(f"Plot saved for simulation {simulation_id}")


if __name__ == '__main__':
    print("Starting PLECS FastAPI server...")
    print("API will be available at: http://127.0.0.1:8000")
    print("Interactive docs at: http://127.0.0.1:8000/docs")
    
    uvicorn.run(app, host='127.0.0.1', port=8000)
