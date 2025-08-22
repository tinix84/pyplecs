"""Simulation orchestration and queue management."""

import asyncio
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

# Import simulation planning and viewing classes
from .simulation_plan import SimulationPlan
from .simulation_viewer import SimulationViewer
from queue import Queue, PriorityQueue
import threading

from ..config import get_config
from ..cache import SimulationCache
from ..core.models import SimulationRequest, SimulationResult, SimulationStatus


logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


@dataclass
class SimulationTask:
    """Represents a simulation task in the queue."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request: SimulationRequest = None
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: SimulationStatus = SimulationStatus.QUEUED
    result: Optional[SimulationResult] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __lt__(self, other):
        """For priority queue ordering."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


class SimulationWorker:
    """Worker that executes simulation tasks."""
    
    def __init__(self, worker_id: str, simulation_runner: Callable):
        self.worker_id = worker_id
        self.simulation_runner = simulation_runner
        self.current_task: Optional[SimulationTask] = None
        self.is_busy = False
        self.stats = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_runtime': 0.0
        }
    
    async def execute_task(self, task: SimulationTask) -> SimulationResult:
        """Execute a simulation task."""
        self.current_task = task
        self.is_busy = True
        task.status = SimulationStatus.RUNNING
        task.started_at = time.time()
        
        try:
            logger.info(f"Worker {self.worker_id} starting task {task.id}")
            
            # Run simulation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(
                    executor, 
                    self.simulation_runner, 
                    task.request
                )
            
            task.result = result
            task.status = SimulationStatus.COMPLETED
            task.completed_at = time.time()
            
            runtime = task.completed_at - task.started_at
            self.stats['tasks_completed'] += 1
            self.stats['total_runtime'] += runtime
            
            logger.info(f"Worker {self.worker_id} completed task {task.id} in {runtime:.2f}s")
            
            return result
            
        except Exception as e:
            task.error = str(e)
            task.status = SimulationStatus.FAILED
            task.completed_at = time.time()
            
            self.stats['tasks_failed'] += 1
            
            logger.error(f"Worker {self.worker_id} failed task {task.id}: {e}")
            raise
            
        finally:
            self.current_task = None
            self.is_busy = False


class SimulationOrchestrator:
    """Orchestrates simulation execution with caching, queuing, and worker management."""
    
    def __init__(self):
        self.config = get_config()
        self.cache = SimulationCache()
        
        # Task management
        self.task_queue = PriorityQueue()
        self.active_tasks: Dict[str, SimulationTask] = {}
        self.completed_tasks: Dict[str, SimulationTask] = {}
        
        # Worker management  
        self.workers: List[SimulationWorker] = []
        self.max_workers = self.config.get('orchestration.max_concurrent_simulations', 4)
        
        # State management
        self.is_running = False
        self.orchestrator_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'total_submitted': 0,
            'total_completed': 0,
            'total_failed': 0,
            'total_cached_hits': 0,
            'queue_size': 0,
            'active_tasks': 0
        }
        
        # Callbacks
        self.task_callbacks: Dict[str, List[Callable]] = {
            'on_task_started': [],
            'on_task_completed': [],
            'on_task_failed': [],
            'on_queue_empty': []
        }
    
    def register_simulation_runner(self, runner: Callable):
        """Register the simulation runner function."""
        self.simulation_runner = runner
        
        # Initialize workers
        for i in range(self.max_workers):
            worker = SimulationWorker(f"worker-{i}", runner)
            self.workers.append(worker)
    
    def add_callback(self, event: str, callback: Callable):
        """Add callback for orchestrator events."""
        if event in self.task_callbacks:
            self.task_callbacks[event].append(callback)
    
    def remove_callback(self, event: str, callback: Callable):
        """Remove callback for orchestrator events."""
        if event in self.task_callbacks and callback in self.task_callbacks[event]:
            self.task_callbacks[event].remove(callback)
    
    def _trigger_callbacks(self, event: str, *args, **kwargs):
        """Trigger callbacks for an event."""
        for callback in self.task_callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")
    
    async def submit_simulation(self, 
                              request: SimulationRequest,
                              priority: TaskPriority = TaskPriority.NORMAL,
                              use_cache: bool = True) -> str:
        """Submit a simulation for execution.
        
        Args:
            request: Simulation request
            priority: Task priority
            use_cache: Whether to use cached results if available
            
        Returns:
            Task ID for tracking
        """
        task = SimulationTask(
            request=request,
            priority=priority,
            max_retries=self.config.get('orchestration.retry_attempts', 3)
        )
        
        # Check cache first if enabled
        if use_cache and self.cache.config.cache.enabled:
            cached_result = self.cache.get_cached_result(
                request.model_file,
                request.parameters
            )
            
            if cached_result:
                task.status = SimulationStatus.COMPLETED
                task.result = SimulationResult(
                    task_id=task.id,
                    success=True,
                    timeseries_data=cached_result['timeseries'],
                    metadata=cached_result['metadata'],
                    execution_time=0.0,
                    cached=True
                )
                task.completed_at = time.time()
                
                self.completed_tasks[task.id] = task
                self.stats['total_cached_hits'] += 1
                
                logger.info(f"Task {task.id} served from cache")
                self._trigger_callbacks('on_task_completed', task)
                
                return task.id
        
        # Add to queue
        with self._lock:
            self.task_queue.put(task)
            self.active_tasks[task.id] = task
            self.stats['total_submitted'] += 1
            self.stats['queue_size'] = self.task_queue.qsize()
        
        logger.info(f"Task {task.id} queued with priority {priority.name}")
        
        # Start orchestrator if not running
        if not self.is_running:
            await self.start()
        
        return task.id
    
    async def get_task_status(self, task_id: str) -> Optional[SimulationTask]:
        """Get status of a specific task."""
        # Check active tasks
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        
        # Check completed tasks
        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id]
        
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a queued or running task."""
        with self._lock:
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                
                if task.status == SimulationStatus.QUEUED:
                    task.status = SimulationStatus.CANCELLED
                    del self.active_tasks[task_id]
                    self.completed_tasks[task_id] = task
                    return True
                elif task.status == SimulationStatus.RUNNING:
                    # Mark for cancellation - worker will check this
                    task.status = SimulationStatus.CANCELLED
                    return True
        
        return False
    
    async def start(self):
        """Start the orchestrator."""
        if self.is_running:
            return
        
        self.is_running = True
        self.orchestrator_task = asyncio.create_task(self._orchestrator_loop())
        logger.info("Simulation orchestrator started")
    
    async def stop(self):
        """Stop the orchestrator."""
        self.is_running = False
        
        if self.orchestrator_task:
            self.orchestrator_task.cancel()
            try:
                await self.orchestrator_task
            except asyncio.CancelledError:
                pass
        
        # Wait for running tasks to complete
        while any(worker.is_busy for worker in self.workers):
            await asyncio.sleep(0.1)
        
        logger.info("Simulation orchestrator stopped")
    
    async def _orchestrator_loop(self):
        """Main orchestrator loop."""
        try:
            while self.is_running:
                # Check for available workers and pending tasks
                available_workers = [w for w in self.workers if not w.is_busy]
                
                if available_workers and not self.task_queue.empty():
                    # Get next task
                    try:
                        task = self.task_queue.get_nowait()
                        worker = available_workers[0]
                        
                        # Execute task in background
                        asyncio.create_task(self._execute_task_with_worker(worker, task))
                        
                    except Exception as e:
                        logger.error(f"Error processing task: {e}")
                
                # Update statistics
                with self._lock:
                    self.stats['queue_size'] = self.task_queue.qsize()
                    self.stats['active_tasks'] = sum(1 for w in self.workers if w.is_busy)
                
                # Check if queue is empty and trigger callback
                if self.task_queue.empty() and not any(w.is_busy for w in self.workers):
                    self._trigger_callbacks('on_queue_empty')
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
        except asyncio.CancelledError:
            logger.info("Orchestrator loop cancelled")
        except Exception as e:
            logger.error(f"Orchestrator loop error: {e}")
    
    async def _execute_task_with_worker(self, worker: SimulationWorker, task: SimulationTask):
        """Execute a task with a specific worker."""
        try:
            self._trigger_callbacks('on_task_started', task)
            
            result = await worker.execute_task(task)
            
            # Cache result if successful
            if result and result.success and self.cache.config.cache.enabled:
                self.cache.cache_result(
                    task.request.model_file,
                    task.request.parameters,
                    result.timeseries_data,
                    result.metadata
                )
            
            # Move to completed tasks
            with self._lock:
                if task.id in self.active_tasks:
                    del self.active_tasks[task.id]
                self.completed_tasks[task.id] = task
                self.stats['total_completed'] += 1
            
            self._trigger_callbacks('on_task_completed', task)
            
        except Exception as e:
            # Handle task failure
            task.retry_count += 1
            
            if task.retry_count < task.max_retries:
                # Retry task
                logger.info(f"Retrying task {task.id} (attempt {task.retry_count + 1})")
                task.status = SimulationStatus.QUEUED
                
                # Add delay before retry
                retry_delay = self.config.get('orchestration.retry_delay', 5)
                await asyncio.sleep(retry_delay)
                
                with self._lock:
                    self.task_queue.put(task)
            else:
                # Max retries reached
                task.status = SimulationStatus.FAILED
                
                with self._lock:
                    if task.id in self.active_tasks:
                        del self.active_tasks[task.id]
                    self.completed_tasks[task.id] = task
                    self.stats['total_failed'] += 1
                
                self._trigger_callbacks('on_task_failed', task)
                logger.error(f"Task {task.id} failed after {task.max_retries} retries")
    
    def get_orchestrator_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        with self._lock:
            worker_stats = {
                f"worker_{w.worker_id}": {
                    'is_busy': w.is_busy,
                    'current_task': w.current_task.id if w.current_task else None,
                    'tasks_completed': w.stats['tasks_completed'],
                    'tasks_failed': w.stats['tasks_failed'],
                    'total_runtime': w.stats['total_runtime']
                }
                for w in self.workers
            }
            
            return {
                **self.stats,
                'workers': worker_stats,
                'cache_stats': self.cache.get_cache_stats()
            }
    
    async def wait_for_completion(self, task_id: str, timeout: Optional[float] = None) -> Optional[SimulationTask]:
        """Wait for a specific task to complete.
        
        Args:
            task_id: Task ID to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            Completed task or None if timeout
        """
        start_time = time.time()
        
        while True:
            task = await self.get_task_status(task_id)
            
            if not task:
                return None
            
            if task.status in [SimulationStatus.COMPLETED, SimulationStatus.FAILED, SimulationStatus.CANCELLED]:
                return task
            
            if timeout and (time.time() - start_time) > timeout:
                return None
            
            await asyncio.sleep(0.1)
    
    async def wait_for_all_tasks(self, timeout: Optional[float] = None) -> bool:
        """Wait for all tasks to complete.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if all tasks completed, False if timeout
        """
        start_time = time.time()
        
        while True:
            if self.task_queue.empty() and not any(w.is_busy for w in self.workers):
                return True
            
            if timeout and (time.time() - start_time) > timeout:
                return False
            
            await asyncio.sleep(0.1)
