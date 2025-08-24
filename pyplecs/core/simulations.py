
"""
Simulation management classes for PyPLECS
Implements orchestration, status tracking, parameter sweep, and migration helpers.
"""
from typing import List, Dict, Any, Optional, Callable, Sequence
import asyncio
import logging
from enum import Enum

class SimulationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class SimulationPlan:
    """Defines a simulation plan with models and parameters."""
    def __init__(self, models: Optional[List[Any]] = None, simulation_type: str = "sequential",
                 parameters: Optional[Dict[str, Sequence[Any]]] = None, parallel_workers: int = 1, timeout: Optional[float] = None):
        self.models = models or []
        self.simulation_type = simulation_type
        self.parameters = parameters or {}
        self.parallel_workers = parallel_workers
        self.timeout = timeout

    def add_model(self, model: Any):
        self.models.append(model)

    def set_parameter_sweep(self, parameter: str, values: Sequence[Any]):
        self.parameters[parameter] = values

    def generate_parameter_sweeps(self) -> List[Dict[str, Any]]:
        """Generate all combinations for parameter sweeps."""
        import itertools
        keys = list(self.parameters.keys())
        value_lists = [self.parameters[k] for k in keys]
        combos = [dict(zip(keys, vals)) for vals in itertools.product(*value_lists)]
        return combos if combos else [{}]

class PLECSSimulation:
    """Manages individual simulation execution with status tracking and callbacks."""
    def __init__(self, model: Any, app: Any, simulation_id: Optional[str] = None):
        self.model = model
        self.app = app
        self.simulation_id = simulation_id or f"sim_{id(self)}"
        self.status = SimulationStatus.PENDING
        self.result = None
        self._callbacks: List[Callable] = []
        self.logger = logging.getLogger(self.__class__.__name__)

    def add_status_callback(self, callback: Callable[["PLECSSimulation"], None]):
        self._callbacks.append(callback)

    async def execute(self, timeout: Optional[float] = None) -> Any:
        try:
            self.status = SimulationStatus.RUNNING
            self._notify_callbacks()
            coro = self.app.simulate(self.model)
            if timeout:
                self.result = await asyncio.wait_for(coro, timeout=timeout)
            else:
                self.result = await coro
            self.status = SimulationStatus.COMPLETED
        except asyncio.TimeoutError:
            self.status = SimulationStatus.CANCELLED
            self.result = {"status": "cancelled", "error": "Simulation timed out"}
        except Exception as e:
            self.status = SimulationStatus.FAILED
            self.result = {"status": "failed", "error": str(e)}
        finally:
            self._notify_callbacks()
        return self.result

    def _notify_callbacks(self):
        for callback in self._callbacks:
            try:
                callback(self)
            except Exception as e:
                self.logger.error("Callback error: %s", e)

# --- Migration helpers ---
def migrate_simulation_call(model, app, timeout=None, callback=None):
    """Helper to migrate old simulation calls to new PLECSSimulation class."""
    sim = PLECSSimulation(model, app)
    if callback:
        sim.add_status_callback(callback)
    return sim.execute(timeout=timeout)
