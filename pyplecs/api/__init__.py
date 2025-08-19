"""REST API for PyPLECS simulation management."""

import asyncio
import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..config import get_config
from ..core.models import SimulationRequest, SimulationStatus
from ..orchestration import SimulationOrchestrator, TaskPriority


logger = logging.getLogger(__name__)


# Pydantic models for API
class SimulationRequestAPI(BaseModel):
    """API model for simulation requests."""
    model_file: str
    parameters: dict = {}
    simulation_time: Optional[float] = None
    output_variables: List[str] = []
    metadata: dict = {}
    priority: str = "NORMAL"
    use_cache: bool = True


class SimulationStatusAPI(BaseModel):
    """API model for simulation status."""
    task_id: str
    status: str
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    progress: Optional[float] = None


class SimulationResultAPI(BaseModel):
    """API model for simulation results."""
    task_id: str
    success: bool
    timeseries_data: Optional[dict] = None
    metadata: dict = {}
    error_message: Optional[str] = None
    execution_time: float = 0.0
    cached: bool = False


# Global orchestrator instance
orchestrator: Optional[SimulationOrchestrator] = None


def get_orchestrator() -> SimulationOrchestrator:
    """Get the global orchestrator instance."""
    global orchestrator
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")
    return orchestrator


def create_api_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    config = get_config()
    
    app = FastAPI(
        title="PyPLECS API",
        description="REST API for PLECS simulation management",
        version="1.0.0",
        docs_url="/docs" if config.api.docs_enabled else None,
        redoc_url="/redoc" if config.api.docs_enabled else None
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app


app = create_api_app()


@app.on_event("startup")
async def startup_event():
    """Initialize the orchestrator on startup."""
    global orchestrator
    orchestrator = SimulationOrchestrator()
    
    # Register a dummy simulation runner for now
    def dummy_runner(request: SimulationRequest):
        import time
        import pandas as pd
        from ..core.models import SimulationResult
        
        # Simulate some work
        time.sleep(1)
        
        # Create dummy result
        df = pd.DataFrame({
            'time': [0, 1, 2, 3, 4],
            'voltage': [0, 5, 10, 15, 20],
            'current': [0, 1, 2, 3, 4]
        })
        
        return SimulationResult(
            task_id="",
            success=True,
            timeseries_data=df,
            metadata={"simulation_completed": True},
            execution_time=1.0
        )
    
    orchestrator.register_simulation_runner(dummy_runner)
    await orchestrator.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of the orchestrator."""
    global orchestrator
    if orchestrator:
        await orchestrator.stop()


@app.post("/simulations", response_model=dict)
async def submit_simulation(
    request: SimulationRequestAPI,
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator)
):
    """Submit a new simulation for execution."""
    try:
        # Convert API model to core model
        sim_request = SimulationRequest(
            model_file=request.model_file,
            parameters=request.parameters,
            simulation_time=request.simulation_time,
            output_variables=request.output_variables,
            metadata=request.metadata
        )
        
        # Parse priority
        try:
            priority = TaskPriority[request.priority.upper()]
        except KeyError:
            priority = TaskPriority.NORMAL
        
        # Submit simulation
        task_id = await orchestrator.submit_simulation(
            sim_request,
            priority=priority,
            use_cache=request.use_cache
        )
        
        return {"task_id": task_id, "status": "submitted"}
        
    except Exception as e:
        logger.error(f"Error submitting simulation: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/simulations/{task_id}", response_model=SimulationStatusAPI)
async def get_simulation_status(
    task_id: str,
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator)
):
    """Get the status of a specific simulation."""
    task = await orchestrator.get_task_status(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return SimulationStatusAPI(
        task_id=task.id,
        status=task.status.value,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        error=task.error
    )


@app.get("/simulations/{task_id}/result", response_model=SimulationResultAPI)
async def get_simulation_result(
    task_id: str,
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator)
):
    """Get the result of a completed simulation."""
    task = await orchestrator.get_task_status(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != SimulationStatus.COMPLETED:
        raise HTTPException(
            status_code=400, 
            detail=f"Task not completed. Current status: {task.status.value}"
        )
    
    if not task.result:
        raise HTTPException(status_code=500, detail="Result not available")
    
    return SimulationResultAPI(
        task_id=task.result.task_id,
        success=task.result.success,
        timeseries_data=task.result.timeseries_data.to_dict() if task.result.timeseries_data is not None else None,
        metadata=task.result.metadata,
        error_message=task.result.error_message,
        execution_time=task.result.execution_time,
        cached=task.result.cached
    )


@app.delete("/simulations/{task_id}")
async def cancel_simulation(
    task_id: str,
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator)
):
    """Cancel a queued or running simulation."""
    success = await orchestrator.cancel_task(task_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
    
    return {"message": "Task cancelled successfully"}


@app.get("/simulations")
async def list_simulations(
    status: Optional[str] = None,
    limit: int = 100,
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator)
):
    """List simulations with optional status filter."""
    # Get all tasks
    all_tasks = []
    all_tasks.extend(orchestrator.active_tasks.values())
    all_tasks.extend(orchestrator.completed_tasks.values())
    
    # Filter by status if provided
    if status:
        try:
            status_filter = SimulationStatus(status.lower())
            all_tasks = [t for t in all_tasks if t.status == status_filter]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    # Sort by creation time (newest first) and limit
    all_tasks.sort(key=lambda t: t.created_at, reverse=True)
    all_tasks = all_tasks[:limit]
    
    # Convert to API format
    results = []
    for task in all_tasks:
        results.append({
            "task_id": task.id,
            "status": task.status.value,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "error": task.error,
            "model_file": task.request.model_file if task.request else None
        })
    
    return {"simulations": results, "total": len(results)}


@app.get("/stats")
async def get_system_stats(
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator)
):
    """Get system and orchestrator statistics."""
    return orchestrator.get_orchestrator_stats()


@app.post("/cache/clear")
async def clear_cache(
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator)
):
    """Clear the simulation cache."""
    orchestrator.cache.clear_cache()
    return {"message": "Cache cleared successfully"}


@app.get("/cache/stats")
async def get_cache_stats(
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator)
):
    """Get cache statistics."""
    return orchestrator.cache.get_cache_stats()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "PyPLECS API"}


if __name__ == "__main__":
    import uvicorn
    
    config = get_config()
    uvicorn.run(
        "pyplecs.api:app",
        host=config.api.host,
        port=config.api.port,
        reload=True
    )
