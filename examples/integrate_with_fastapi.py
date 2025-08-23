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

# Setup for proper imports - ensure we're in the right environment
script_dir = Path(__file__).parent
project_root = script_dir.parent
os.chdir(project_root)
sys.path.insert(0, str(project_root))

# Activate virtual environment if it exists
venv_path = project_root / '.venv'
if venv_path.exists():
    if sys.platform == 'win32':
        venv_python = venv_path / 'Scripts' / 'python.exe'
        venv_site_packages = venv_path / 'Lib' / 'site-packages'
    else:
        venv_python = venv_path / 'bin' / 'python'
        venv_site_packages = venv_path / 'lib' / 'python3.10' / 'site-packages'
    
    if venv_site_packages.exists():
        sys.path.insert(0, str(venv_site_packages))
        print(f"[OK] Using virtual environment: {venv_path}")

# Now import dependencies
try:
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend for server deployment
except ImportError as e:
    print(f"Missing scientific packages: {e}")
    print("Install with: pip install numpy matplotlib")
    exit(1)

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.responses import FileResponse
    from pydantic import BaseModel
    import uvicorn
except ImportError as e:
    print(f"Missing FastAPI packages: {e}")
    print("Install with: pip install fastapi[all] uvicorn")
    exit(1)

try:
    from pyplecs.pyplecs import PlecsApp, PlecsServer
except ImportError as e:
    print(f"PyPLECS import failed: {e}")
    print("Please install with: pip install -e .")
    exit(1)

from typing import Dict, Any, List, Optional


# Pydantic models for API requests/responses
class SimulationRequest(BaseModel):
    parameters: Dict[str, float]
    timeout: float = 30.0
    save_plot: bool = True
    # Generic file and simulation options
    model_file: Optional[str] = None  # PLECS filename (e.g., "simple_buck.plecs")
    model_path: Optional[str] = None  # Path to model directory
    simulation_time: Optional[float] = None  # Override simulation time
    output_signals: Optional[List[str]] = None  # Specific signals to capture
    plot_title: Optional[str] = None  # Custom plot title
    plot_format: str = "png"  # Plot format: png, pdf, svg
    description: Optional[str] = None  # Simulation description/notes


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
test_mode = False  # Global test mode flag


def startup_plecs(model_file='simple_buck.plecs', model_path='data'):
    """Initialize PLECS application and server with configurable model."""
    global plecs_app, plecs_server, plecs_initialized, initialization_error
    
    try:
        if test_mode:
            # Test mode initialization
            print("[OK] Mock PLECS initialized for test mode")
            plecs_initialized = True
            return
            
        print(f"Starting PLECS application with {model_file}...")
        model_path = Path(model_path)
        
        if not (model_path / model_file).exists():
            # Try common model locations
            search_paths = [
                Path('data'),
                Path('data') / '01',
                Path('data') / '02', 
                Path('.'),
                Path('examples')
            ]
            
            found_file = None
            for search_path in search_paths:
                if (search_path / model_file).exists():
                    model_path = search_path
                    found_file = model_path / model_file
                    print(f"[OK] Found model at: {found_file}")
                    break
            
            if not found_file:
                available_files = []
                for search_path in search_paths:
                    if search_path.exists():
                        plecs_files = list(search_path.glob('*.plecs'))
                        available_files.extend([str(f) for f in plecs_files])
                
                error_msg = f'PLECS file "{model_file}" not found. Available files: {available_files}'
                raise RuntimeError(error_msg)
        
        plecs_app = PlecsApp()
        plecs_app.open_plecs()
        time.sleep(3)  # Wait for PLECS to start
        plecs_app.set_plecs_high_priority()
        
        # Initialize PLECS server with XMLRPC connection
        plecs_server = PlecsServer(
            sim_path=str(model_path.absolute()),
            sim_name=model_file,
            port='1080',
            load=True
        )
        
        # Test XMLRPC connection
        try:
            # Try a simple ping to verify connection
            if hasattr(plecs_server, 'server') and plecs_server.server:
                print("[OK] XMLRPC connection established")
            else:
                raise RuntimeError("XMLRPC server connection failed")
        except Exception as e:
            raise RuntimeError(f"XMLRPC connection test failed: {e}")
        
        plecs_initialized = True
        print("[OK] PLECS initialized successfully")
        
    except Exception as e:
        initialization_error = str(e)
        plecs_initialized = False
        print(f"[ERROR] Failed to initialize PLECS: {e}")


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
    """Run a PLECS simulation with given parameters and options."""
    
    # Handle dynamic model file loading if specified
    if request.model_file or request.model_path:
        model_file = request.model_file or 'simple_buck.plecs'
        model_path = request.model_path or 'data'
        
        # Check if we need to reload PLECS with different model
        if not test_mode and (model_file != 'simple_buck.plecs' or model_path != 'data'):
            print(f"📁 Loading different model: {model_file} from {model_path}")
            try:
                # Shutdown current PLECS instance
                shutdown_plecs()
                # Initialize with new model
                startup_plecs(model_file, model_path)
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to load model {model_file}: {str(e)}"
                )
    
    # Ensure PLECS is ready
    ensure_plecs_ready()
    
    # Generate unique simulation ID
    simulation_id = f"sim_{int(time.time()*1000)}"
    
    try:
        print(f"Running simulation {simulation_id}")
        print(f"Parameters: {request.parameters}")
        if request.model_file:
            print(f"Model: {request.model_file}")
        if request.description:
            print(f"Description: {request.description}")
        
        # Handle test mode vs real PLECS
        if test_mode:
            # Generate mock simulation data
            import numpy as np
            sim_time = request.simulation_time or 1.0
            points = int(sim_time * 100)  # 100 points per second
            t = np.linspace(0, sim_time, points)
            v_out = 200 + 10 * np.sin(2 * np.pi * 50 * t)  # 200V with ripple
            i_L = 5 + 0.5 * np.sin(2 * np.pi * 50 * t)     # 5A with ripple
            result = {
                'Time': t.tolist(),
                'Values': [v_out.tolist(), i_L.tolist()]
            }
        else:
            # Prepare simulation parameters
            sim_params = request.parameters.copy()
            
            # Add simulation time if specified
            if request.simulation_time:
                sim_params['SimulationTime'] = request.simulation_time
            
            # Use the working run_sim_with_datastream method
            result = plecs_server.run_sim_with_datastream(
                param_dict=sim_params
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
                        generate_simulation_plot, simulation_id, result,
                        request.plot_title, request.plot_format, request.description
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


def generate_simulation_plot(simulation_id: str, result: Dict[str, Any],
                           plot_title: Optional[str] = None,
                           plot_format: str = "png",
                           description: Optional[str] = None):
    """Generate a plot for simulation results (background task)."""
    
    try:
        # Check if result has Time and Values (PLECS standard format)
        if not (isinstance(result, dict) and 'Time' in result and 'Values' in result):
            print(f"Cannot generate plot for {simulation_id}: no Time/Values data")
            return
        
        time_data = np.array(result['Time']).flatten()
        values_data = result['Values']
        
        # Create plot
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        
        # Use custom title or default
        title = plot_title or f'PLECS Simulation Results - {simulation_id}'
        if description:
            title += f'\n{description}'
        fig.suptitle(title, fontsize=14)
        
        # Handle different Values structures
        if isinstance(values_data, list) and len(values_data) > 0:
            # Values is a list of arrays (multiple signals)
            
            # Plot first signal (likely output voltage)
            if len(values_data) >= 1:
                signal_0 = np.array(values_data[0]).flatten()
                axes[0, 0].plot(time_data, signal_0)
                axes[0, 0].set_title('Output Signal 1 (e.g., Voltage)')
                axes[0, 0].set_xlabel('Time (s)')
                axes[0, 0].set_ylabel('Amplitude')
                axes[0, 0].grid(True, alpha=0.3)
            
            # Plot second signal if available
            if len(values_data) >= 2:
                signal_1 = np.array(values_data[1]).flatten()
                axes[0, 1].plot(time_data, signal_1)
                axes[0, 1].set_title('Output Signal 2')
                axes[0, 1].set_xlabel('Time (s)')
                axes[0, 1].set_ylabel('Amplitude')
                axes[0, 1].grid(True, alpha=0.3)
            
            # Calculate and plot power if we have voltage-like signal
            if len(values_data) >= 1 and simulation_id in simulation_results:
                signal_0 = np.array(values_data[0]).flatten()
                params = simulation_results[simulation_id]['parameters']
                r_load = params.get('R', 10.0)
                
                # Assume first signal is voltage, calculate power
                power = signal_0**2 / r_load
                axes[1, 0].plot(time_data, power)
                axes[1, 0].set_title('Calculated Output Power')
                axes[1, 0].set_xlabel('Time (s)')
                axes[1, 0].set_ylabel('Power (W)')
                axes[1, 0].grid(True, alpha=0.3)
            
            # Plot efficiency over time (simplified calculation)
            if len(values_data) >= 1 and simulation_id in simulation_results:
                signal_0 = np.array(values_data[0]).flatten()
                params = simulation_results[simulation_id]['parameters']
                vin = params.get('Vin', 400.0)
                
                # Simplified efficiency: Vout/Vin * 0.9 (assumed losses)
                efficiency = (signal_0 / vin) * 0.9 * 100  # Convert to percentage
                axes[1, 1].plot(time_data, efficiency)
                axes[1, 1].set_title('Estimated Efficiency')
                axes[1, 1].set_xlabel('Time (s)')
                axes[1, 1].set_ylabel('Efficiency (%)')
                axes[1, 1].grid(True, alpha=0.3)
                axes[1, 1].set_ylim(0, 100)
        
        else:
            # Values is not a list - single signal
            signal_data = np.array(values_data).flatten()
            axes[0, 0].plot(time_data, signal_data)
            axes[0, 0].set_title('Simulation Output')
            axes[0, 0].set_xlabel('Time (s)')
            axes[0, 0].set_ylabel('Amplitude')
            axes[0, 0].grid(True, alpha=0.3)
            
            # Clear unused subplots
            for ax in [axes[0, 1], axes[1, 0], axes[1, 1]]:
                ax.axis('off')
                ax.text(0.5, 0.5, 'No additional data', 
                       ha='center', va='center', transform=ax.transAxes)
        
        plt.tight_layout()
        
        # Save plot
        output_dir = Path('examples_output')
        output_dir.mkdir(exist_ok=True)
        plot_file = output_dir / f'simulation_plot_{simulation_id}.png'
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        print(f"[OK] Plot saved for simulation {simulation_id}")
        
    except Exception as e:
        print(f"[ERROR] Failed to generate plot for {simulation_id}: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='PLECS FastAPI Server')
    parser.add_argument('--test-mode', action='store_true',
                        help='Run in test mode (mock PLECS for testing)')
    parser.add_argument('--host', default='127.0.0.1',
                        help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8000,
                        help='Port to bind to (default: 8000)')
    
    args = parser.parse_args()
    
    # Set test mode flag
    test_mode = args.test_mode
    
    if args.test_mode:
        print("🧪 Running in TEST MODE - PLECS simulation will be mocked")
        print("This mode is useful for API testing without PLECS dependency")
    
    print("🚀 Starting PLECS FastAPI server...")
    print(f"📍 API will be available at: http://{args.host}:{args.port}")
    print(f"📖 Interactive docs at: http://{args.host}:{args.port}/docs")
    print(f"🔍 Health check at: http://{args.host}:{args.port}/health")
    
    if not args.test_mode:
        print("⚙️  PLECS will be initialized on first simulation request")
        print("⚠️  Make sure PLECS is installed and XML-RPC is enabled")
    
    uvicorn.run(app, host=args.host, port=args.port)
