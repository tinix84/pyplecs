"""Core data models for PyPLECS.

This module contains the foundational classes for the PyPLECS object-oriented architecture,
including model management, simulation orchestration, and application interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
import pandas as pd
from pathlib import Path
import asyncio
import time
import logging

# ============================================================================
# Core Configuration and Types
# ============================================================================

class SimulationStatus(Enum):
    """Simulation task status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class SimulationType(Enum):
    """Types of simulation execution."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    GUI = "gui"
    XRPC = "xrpc"


@dataclass
class NewSimulationResult:
    """Container for simulation results and metadata (new OOP interface)."""
    status: SimulationStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_legacy_result(self, task_id: str) -> 'SimulationResult':
        """Convert to legacy SimulationResult for backward compatibility."""
        return SimulationResult(
            task_id=task_id,
            success=(self.status == SimulationStatus.COMPLETED),
            timeseries_data=self.data.get('timeseries') if self.data else None,
            metadata=self.metadata,
            error_message=self.error,
            execution_time=self.execution_time or 0.0
        )


# ============================================================================
# Core PLECS Model Management
# ============================================================================

class PLECSModel:
    """Represents a PLECS simulation model file with OOP interface."""
    
    def __init__(self, filename: Union[str, Path]):
        """Initialize PLECSModel with backward compatibility.
        
        Args:
            filename: Path to the PLECS model file
            
        Raises:
            FileNotFoundError: If the model file doesn't exist
        """
        self.filename = filename
        self._variables = {}
        
    @property
    def filename(self) -> Path:
        """Get the full path to the model file."""
        return self._fullname
    
    @filename.setter  
    def filename(self, filename: Union[str, Path]):
        """Set the model filename and derived properties."""
        path_obj = Path(filename)
        if not path_obj.exists():
            raise FileNotFoundError(f"Model file not found: {filename}")
            
        # Convert to absolute path
        path_obj = path_obj.resolve()
        
        self._type = path_obj.suffix
        self._folder = path_obj.parent
        self._name = path_obj.name
        self._fullname = path_obj
        self._model_name = self._name.replace('.plecs', '')
    
    @property
    def folder(self) -> Path:
        """Get the model's parent directory."""
        return self._folder
    
    @property
    def model_name(self) -> str:
        """Get the model name without extension."""
        return self._model_name
    
    @property
    def simulation_name(self) -> str:
        """Get the simulation filename."""
        return self._name
    
    def set_variables(self, variables: Dict[str, Any]):
        """Set model variables for parameter sweeps.
        
        Args:
            variables: Dictionary of variable names and values
        """
        self._variables = {k: float(v) for k, v in variables.items()}
    
    def get_model_vars_opts(self) -> Dict[str, Any]:
        """Get formatted model variables for PLECS.
        
        Returns:
            Dictionary in PLECS-compatible format
        """
        return {'ModelVars': self._variables}


# ============================================================================
# PLECS Application Interface (Abstract Base Classes)
# ============================================================================

class PLECSApp(ABC):
    """Abstract base class for PLECS application interfaces."""
    
    def __init__(self, executable_path: str):
        """Initialize the PLECS application interface.
        
        Args:
            executable_path: Path to the PLECS executable
        """
        self.executable_path = executable_path
        self.is_running = False
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def start(self) -> bool:
        """Start the PLECS application.
        
        Returns:
            True if successfully started, False otherwise
        """
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """Stop the PLECS application.
        
        Returns:
            True if successfully stopped, False otherwise
        """
        pass
    
    @abstractmethod
    async def simulate(self, model: PLECSModel, 
                      **kwargs) -> NewSimulationResult:
        """Run a simulation with the given model.
        
        Args:
            model: PLECSModel instance to simulate
            **kwargs: Additional simulation parameters
            
        Returns:
            NewSimulationResult containing the outcome
        """
        pass


class PLECSGUIApp(PLECSApp):
    """PLECS GUI application interface for backward compatibility."""
    
    def __init__(self, executable_path: str, high_priority: bool = False):
        """Initialize PLECS GUI application.
        
        Args:
            executable_path: Path to PLECS executable
            high_priority: Whether to run with high priority
        """
        super().__init__(executable_path)
        self.high_priority = high_priority
        self.process = None
    
    async def start(self) -> bool:
        """Start PLECS GUI process.
        
        Returns:
            True if successfully started
        """
        try:
            import subprocess
            import psutil
            
            # Start PLECS process
            creation_flags = (psutil.HIGH_PRIORITY_CLASS 
                            if self.high_priority 
                            else psutil.ABOVE_NORMAL_PRIORITY_CLASS)
            
            self.process = subprocess.Popen(
                [self.executable_path], 
                creationflags=creation_flags
            )
            self.is_running = True
            self.logger.info(f"PLECS GUI started with PID {self.process.pid}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start PLECS GUI: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop PLECS GUI process.
        
        Returns:
            True if successfully stopped
        """
        try:
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=10)
            self.is_running = False
            self.logger.info("PLECS GUI stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop PLECS GUI: {e}")
            return False
    
    async def simulate(self, model: PLECSModel, 
                      **kwargs) -> NewSimulationResult:
        """Run simulation through GUI interface.
        
        Note: GUI automation is deprecated. Use XRPC interface instead.
        
        Args:
            model: PLECSModel to simulate
            **kwargs: Additional parameters
            
        Returns:
            NewSimulationResult with error status
        """
        return NewSimulationResult(
            status=SimulationStatus.FAILED,
            error="GUI automation is deprecated. Use XRPC interface instead."
        )


class PLECSXRPCApp(PLECSApp):
    """PLECS XRPC server interface for remote simulation."""
    
    def __init__(self, executable_path: str, port: int = 1080):
        """Initialize PLECS XRPC application.
        
        Args:
            executable_path: Path to PLECS executable  
            port: XML-RPC server port
        """
        super().__init__(executable_path)
        self.port = port
        self.server_process = None
        self._rpc_client = None
    
    async def start(self) -> bool:
        """Start PLECS XRPC server.
        
        Returns:
            True if successfully started
        """
        try:
            import subprocess
            import xmlrpc.client
            
            # Start PLECS with XRPC server
            cmd = [self.executable_path, '-server', str(self.port)]
            self.server_process = subprocess.Popen(cmd)
            
            # Wait for server to be ready and create client
            await asyncio.sleep(2)  # Give server time to start
            self._rpc_client = xmlrpc.client.Server(
                f'http://localhost:{self.port}/RPC2'
            )
            
            self.is_running = True
            self.logger.info(f"PLECS XRPC server started on port {self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start PLECS XRPC server: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop PLECS XRPC server.
        
        Returns:
            True if successfully stopped
        """
        try:
            if self.server_process:
                self.server_process.terminate()
                self.server_process.wait(timeout=10)
            self._rpc_client = None
            self.is_running = False
            self.logger.info("PLECS XRPC server stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop PLECS XRPC server: {e}")
            return False
    
    async def simulate(self, model: PLECSModel, 
                      **kwargs) -> NewSimulationResult:
        """Run simulation through XRPC interface.
        
        Args:
            model: PLECSModel to simulate
            **kwargs: Additional simulation parameters
            
        Returns:
            NewSimulationResult containing the outcome
        """
        if not self.is_running or not self._rpc_client:
            return NewSimulationResult(
                status=SimulationStatus.FAILED,
                error="XRPC server not running"
            )
        
        try:
            start_time = time.time()
            
            # Load model in PLECS
            model_path = str(model.filename)
            self._rpc_client.plecs.load(model_path)
            
            # Set model variables if any
            if model._variables:
                opt_struct = model.get_model_vars_opts()
                result_data = self._rpc_client.plecs.simulate(model.model_name, 
                                                            opt_struct)
            else:
                result_data = self._rpc_client.plecs.simulate(model.model_name)
            
            execution_time = time.time() - start_time
            
            return NewSimulationResult(
                status=SimulationStatus.COMPLETED,
                data={'rpc_result': result_data},  # Wrap RPC result properly
                execution_time=execution_time,
                metadata={'model_path': model_path}
            )
            
        except Exception as e:
            return NewSimulationResult(
                status=SimulationStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time
            )



# ============================================================================
# Simulation Management Classes
# ============================================================================


@dataclass
class SimulationPlan:
    """Defines a simulation plan with models and parameters."""
    
    models: List[PLECSModel]
    simulation_type: SimulationType
    parameters: Dict[str, Any] = field(default_factory=dict)
    parallel_workers: int = 1
    timeout: Optional[float] = None
    
    def add_model(self, model: PLECSModel):
        """Add a model to the simulation plan."""
        self.models.append(model)
    
    def set_parameter_sweep(self, parameter: str, values: List[Any]):
        """Define parameter sweep for simulations."""
        self.parameters[parameter] = values


class PLECSSimulation:
    """Manages individual simulation execution with status tracking."""
    
    def __init__(self,
                 model: PLECSModel,
                 app: PLECSApp,
                 simulation_id: Optional[str] = None):
        """Initialize simulation manager.
        
        Args:
            model: PLECSModel instance to simulate
            app: PLECSApp instance to use for execution
            simulation_id: Optional unique identifier
        """
        self.model = model
        self.app = app
        self.simulation_id = simulation_id or f"sim_{id(self)}"
        self.status = SimulationStatus.PENDING
        self.result = None
        self._callbacks = []
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def add_status_callback(self,
                            callback: Callable[['PLECSSimulation'], None]):
        """Add callback for status updates."""
        self._callbacks.append(callback)
    
    async def execute(self) -> NewSimulationResult:
        """Execute the simulation with status tracking."""
        try:
            self.status = SimulationStatus.RUNNING
            self._notify_callbacks()
            
            self.result = await self.app.simulate(self.model)
            self.status = self.result.status
            
        except Exception as e:
            self.result = NewSimulationResult(
                status=SimulationStatus.FAILED,
                error=str(e)
            )
            self.status = SimulationStatus.FAILED
        finally:
            self._notify_callbacks()
        
        return self.result
    
    def _notify_callbacks(self):
        """Notify all registered status callbacks."""
        for callback in self._callbacks:
            try:
                callback(self)
            except Exception as e:
                self.logger.error("Callback error: %s", e)


# ============================================================================
# Server Orchestration
# ============================================================================

class PLECSServer:
    """Main server class managing PLECS applications and simulations."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize PLECS server with configuration.
        
        Args:
            config: Configuration dictionary for server setup
        """
        self.config = config
        self.apps: Dict[str, PLECSApp] = {}
        self.active_simulations: Dict[str, PLECSSimulation] = {}
        self.simulation_queue = asyncio.Queue()
        self.cache_manager = None  # Integration with existing cache system
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def register_app(self, name: str, app: PLECSApp):
        """Register a PLECS application instance."""
        self.apps[name] = app
    
    def get_app(self, app_type: str = "default") -> Optional[PLECSApp]:
        """Get a PLECS application instance."""
        return self.apps.get(app_type)
    
    async def execute_simulation_plan(
            self, plan: SimulationPlan) -> List[NewSimulationResult]:
        """Execute a complete simulation plan.
        
        Args:
            plan: SimulationPlan defining what to execute
            
        Returns:
            List of simulation results
        """
        results = []
        
        if plan.simulation_type == SimulationType.SEQUENTIAL:
            results = await self._execute_sequential(plan)
        elif plan.simulation_type == SimulationType.PARALLEL:
            results = await self._execute_parallel(plan)
        else:
            msg = f"Unsupported simulation type: {plan.simulation_type}"
            raise ValueError(msg)
        
        return results
    
    async def _execute_sequential(
            self, plan: SimulationPlan) -> List[NewSimulationResult]:
        """Execute simulations sequentially."""
        results = []
        app = self.get_app("xrpc")  # Default to XRPC for sequential
        
        if not app:
            raise ValueError("No XRPC app available for sequential execution")
        
        for model in plan.models:
            simulation = PLECSSimulation(model, app)
            result = await simulation.execute()
            results.append(result)
        
        return results
    
    async def _execute_parallel(
            self, plan: SimulationPlan) -> List[NewSimulationResult]:
        """Execute simulations in parallel."""
        tasks = []
        app = self.get_app("gui")  # Use GUI for parallel execution
        
        if not app:
            raise ValueError("No GUI app available for parallel execution")
        
        for model in plan.models:
            simulation = PLECSSimulation(model, app)
            task = asyncio.create_task(simulation.execute())
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return list(results)
    
    async def start(self):
        """Start the PLECS server and initialize applications."""
        # Initialize applications based on config
        for app_name, app_config in self.config.get('apps', {}).items():
            if app_config['type'] == 'gui':
                app = PLECSGUIApp(
                    executable_path=app_config['executable_path'],
                    high_priority=app_config.get('high_priority', False)
                )
            elif app_config['type'] == 'xrpc':
                app = PLECSXRPCApp(
                    executable_path=app_config['executable_path'],
                    port=app_config.get('port', 1080)
                )
            else:
                continue
            
            await app.start()
            self.register_app(app_name, app)
    
    async def stop(self):
        """Stop the PLECS server and all applications."""
        for app in self.apps.values():
            await app.stop()


# ============================================================================
# Backward Compatibility - Existing Classes (Preserved)
# ============================================================================

@dataclass
class SimulationRequest:
    """Request for a PLECS simulation."""
    model_file: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    simulation_time: Optional[float] = None
    output_variables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize the request."""
        # Ensure model file exists
        if not Path(self.model_file).exists():
            raise FileNotFoundError(f"Model file not found: {self.model_file}")
        
        # Convert relative path to absolute
        self.model_file = str(Path(self.model_file).resolve())


@dataclass 
class SimulationResult:
    """Result of a PLECS simulation."""
    task_id: str
    success: bool
    timeseries_data: Optional[pd.DataFrame] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time: float = 0.0
    cached: bool = False
    plecs_version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'task_id': self.task_id,
            'success': self.success,
            'timeseries_data': (self.timeseries_data.to_dict()
                                if self.timeseries_data is not None
                                else None),
            'metadata': self.metadata,
            'error_message': self.error_message,
            'execution_time': self.execution_time,
            'cached': self.cached,
            'plecs_version': self.plecs_version
        }


@dataclass
class ComponentParameter:
    """Parameter for a PLECS component."""
    name: str
    value: Union[float, int, str]
    component_path: str
    parameter_name: str
    
    def to_plecs_reference(self) -> str:
        """Get PLECS reference string for this parameter."""
        return f"{self.component_path}/{self.parameter_name}"


@dataclass
class ModelVariant:
    """Represents a model variant with specific parameters."""
    name: str
    base_model: str
    parameters: Dict[str, Any]
    description: Optional[str] = None
    
    def generate_variant_file(self, output_dir: str) -> str:
        """Generate a variant PLECS file with the specified parameters."""
        from ..pyplecs import generate_variant_plecs_file
        
        output_path = Path(output_dir) / self.name / Path(self.base_model).name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        variant_file = str(output_path).replace('.plecs', f'_{self.name}.plecs')
        
        generate_variant_plecs_file(
            scr_filename=self.base_model,
            dst_filename=variant_file,
            modelvars=self.parameters
        )
        
        return variant_file


@dataclass
class OptimizationObjective:
    """Optimization objective definition."""
    name: str
    variable: str  # Variable name in simulation results
    target_value: Optional[float] = None
    minimize: bool = True
    weight: float = 1.0
    constraint_min: Optional[float] = None
    constraint_max: Optional[float] = None


@dataclass
class OptimizationParameter:
    """Parameter to be optimized."""
    name: str
    min_value: float
    max_value: float
    initial_value: Optional[float] = None
    parameter_type: str = "float"  # float, int, discrete
    discrete_values: List[Union[float, int]] = field(default_factory=list)


@dataclass
class OptimizationRequest:
    """Request for parameter optimization."""
    model_file: str
    objectives: List[OptimizationObjective]
    parameters: List[OptimizationParameter]
    algorithm: str = "scipy_minimize"
    algorithm_options: Dict[str, Any] = field(default_factory=dict)
    max_iterations: int = 100
    convergence_tolerance: float = 1e-6
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationResult:
    """Result of parameter optimization."""
    request_id: str
    success: bool
    optimal_parameters: Dict[str, float] = field(default_factory=dict)
    optimal_objectives: Dict[str, float] = field(default_factory=dict)
    convergence_history: List[Dict[str, Any]] = field(default_factory=list)
    total_iterations: int = 0
    total_simulations: int = 0
    execution_time: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebGuiState:
    """State information for web GUI."""
    simulation_queue: List[Dict[str, Any]] = field(default_factory=list)
    active_simulations: List[Dict[str, Any]] = field(default_factory=list)
    completed_simulations: List[Dict[str, Any]] = field(default_factory=list)
    system_stats: Dict[str, Any] = field(default_factory=dict)
    worker_stats: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class McpTool:
    """Model Context Protocol tool definition."""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable] = None


@dataclass
class McpResource:
    """Model Context Protocol resource definition."""
    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"
    content: Optional[str] = None


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: float
    level: str
    logger: str
    message: str
    task_id: Optional[str] = None
    worker_id: Optional[str] = None
    simulation_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp,
            'level': self.level,
            'logger': self.logger,
            'message': self.message,
            'task_id': self.task_id,
            'worker_id': self.worker_id,
            'simulation_hash': self.simulation_hash,
            'metadata': self.metadata
        }
