# API Design: When Python Isn't Enough - Building for the Ecosystem

**Substack Article** (3,056 words)
**Theme**: REST API architecture + ecosystem thinking
**Format**: Narrative → Technical Implementation → Strategic Impact

---

> "Give someone a Python library and they can automate a task. Give someone a REST API and they can build an ecosystem."

"Can I use this from MATLAB?"

That innocent question from a power electronics engineer fundamentally changed how I thought about PyPLECS.

The project had amazing features:
- 5× speedup from PLECS batch parallel API
- 100-200× cache hits
- Priority queuing with automatic retries
- Real-time monitoring

But there was one massive problem: **You could only access these features from Python.**

For a field (power electronics) where MATLAB dominates, where simulation engineers have decades of legacy code, where "just rewrite it in Python" isn't an option...

**I'd built a powerful tool that most of my target users couldn't actually use.**

This is the story of how adding a REST API transformed PyPLECS from a Python library into a platform, and the technical and strategic lessons I learned along the way.

---

## The Language Lock-In Problem

### The User's Perspective

The user who asked about MATLAB support had a legitimate use case:

```matlab
% Their existing codebase: 15,000 lines of MATLAB
function optimal_design = optimize_buck_converter()
    % Genetic algorithm optimization
    population = initialize_population(100);  % 100 designs

    for generation = 1:200
        % Evaluate each design (runs PLECS simulations)
        for i = 1:length(population)
            design = population(i);

            % THIS STEP: Currently 10 seconds per simulation
            % With PyPLECS cache: Could be 0.05 seconds
            % But locked to Python :(
            fitness(i) = evaluate_design_plecs(design);
        end

        % Selection, crossover, mutation
        population = evolve_population(population, fitness);
    end

    optimal_design = select_best(population, fitness);
end
```

They wanted PyPLECS's caching (100× speedup on repeated simulations) but couldn't justify:
- Rewriting 15,000 lines of MATLAB
- Losing 20 years of validated algorithms
- Retraining their team on Python

**Fair point.**

### The Broader Problem

MATLAB wasn't the only language locked out:

**Julia users**: Numerical computing community, fast growing
**JavaScript/Web**: Browser-based monitoring dashboards
**Bash scripts**: CI/CD pipelines, automated testing
**Excel macros**: Non-programmers running parametric studies
**LabVIEW**: Hardware-in-the-loop testing

All of these had valid reasons to use PyPLECS's capabilities.

**None of them could.**

---

## The Solution: REST API Architecture

The answer was clear: **Build a REST API.**

Expose PyPLECS functionality over HTTP. Now any language, any platform, any environment can use it.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Applications                      │
│  Python │ MATLAB │ Julia │ JavaScript │ curl │ Excel │ ...  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTP/REST
                         │
                         ∨
┌─────────────────────────────────────────────────────────────┐
│                    PyPLECS REST API                          │
│                     (FastAPI Server)                         │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Simulation  │  │    Cache     │  │    Stats     │      │
│  │  Endpoints   │  │  Endpoints   │  │  Endpoints   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ∨
┌─────────────────────────────────────────────────────────────┐
│                  Orchestration Layer                         │
│   (Priority Queue, Task Management, Batch Execution)         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ∨
┌─────────────────────────────────────────────────────────────┐
│                     Cache Layer                              │
│          (Hash-based deduplication, Parquet storage)         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ∨
┌─────────────────────────────────────────────────────────────┐
│                    PLECS Simulation                          │
│                 (Native batch parallel API)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Technical Implementation: FastAPI

I chose **FastAPI** as the framework. Here's why and how:

### Why FastAPI?

**1. Automatic OpenAPI Documentation**

FastAPI generates interactive API docs automatically:

```python
from fastapi import FastAPI

app = FastAPI(
    title="PyPLECS API",
    description="REST API for PLECS simulation automation",
    version="1.0.0"
)

# Visit http://localhost:8000/docs
# → Interactive Swagger UI with all endpoints
# → Try requests in-browser
# → See request/response schemas
# → Copy curl examples
```

**I never wrote API documentation.** FastAPI generated it from my code.

**2. Pydantic Type Validation**

```python
from pydantic import BaseModel, Field, validator

class SimulationRequest(BaseModel):
    """Request model for simulation submission."""

    model_file: str = Field(..., description="Path to PLECS model file")
    parameters: dict = Field(..., description="ModelVars dictionary")
    priority: str = Field(default="NORMAL", description="CRITICAL, HIGH, NORMAL, LOW")
    output_variables: list[str] = Field(default=None, description="Variables to capture")

    @validator("priority")
    def validate_priority(cls, v):
        valid = ["CRITICAL", "HIGH", "NORMAL", "LOW"]
        if v not in valid:
            raise ValueError(f"Priority must be one of {valid}")
        return v

    @validator("model_file")
    def validate_model_file(cls, v):
        from pathlib import Path
        if not Path(v).exists():
            raise ValueError(f"Model file not found: {v}")
        return v
```

Invalid requests fail with clear error messages:

```http
POST /api/simulations
{
  "model_file": "nonexistent.plecs",
  "parameters": {},
  "priority": "URGENT"  # Invalid priority
}

→ 422 Unprocessable Entity
{
  "detail": [
    {"loc": ["body", "priority"], "msg": "Priority must be one of ['CRITICAL', 'HIGH', 'NORMAL', 'LOW']"},
    {"loc": ["body", "model_file"], "msg": "Model file not found: nonexistent.plecs"}
  ]
}
```

**3. Async Support**

FastAPI is built on Starlette (async framework):

```python
@app.post("/api/simulations")
async def submit_simulation(request: SimulationRequest):
    """Submit simulation without blocking."""
    # This doesn't block other requests
    task_id = await orchestrator.submit_simulation(request)

    return {
        "task_id": task_id,
        "status": "QUEUED",
        "estimated_time": orchestrator.estimate_completion_time()
    }
```

High concurrency: handles 1000+ concurrent requests.

**4. Performance**

FastAPI benchmarks among the fastest Python frameworks:
- 20,000+ requests/sec (simple endpoints)
- Low latency (~5ms overhead)
- Efficient JSON serialization (via orjson)

### Core Endpoints

```python
from fastapi import FastAPI, HTTPException, BackgroundTasks
from typing import Optional
import uuid

app = FastAPI()

# Global orchestrator instance
orchestrator = SimulationOrchestrator()
cache = SimulationCache()

@app.post("/api/simulations", status_code=202)
async def submit_simulation(
    request: SimulationRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit a new simulation to the queue.

    Returns immediately with task_id.
    Simulation runs asynchronously in background.
    """
    task_id = str(uuid.uuid4())

    # Submit to orchestrator
    await orchestrator.submit_simulation(
        task_id=task_id,
        model_file=request.model_file,
        parameters=request.parameters,
        priority=TaskPriority[request.priority]
    )

    return {
        "task_id": task_id,
        "status": "QUEUED",
        "links": {
            "status": f"/api/simulations/{task_id}",
            "results": f"/api/simulations/{task_id}/results",
            "cancel": f"/api/simulations/{task_id}"
        }
    }


@app.get("/api/simulations/{task_id}")
async def get_simulation_status(task_id: str):
    """Get current status of simulation task."""
    task = orchestrator.get_task(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return {
        "task_id": task_id,
        "status": task.status,  # QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED
        "progress": task.progress,  # 0-100
        "submitted_at": task.submitted_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "error": task.error if task.status == "FAILED" else None
    }


@app.get("/api/simulations/{task_id}/results")
async def get_simulation_results(task_id: str):
    """Get simulation results (blocks until completion)."""
    task = orchestrator.get_task(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if task.status != "COMPLETED":
        raise HTTPException(
            status_code=409,
            detail=f"Simulation not completed yet (status: {task.status})"
        )

    # Load results from cache
    result = cache.load(task.cache_key)

    return {
        "task_id": task_id,
        "model_file": task.model_file,
        "parameters": task.parameters,
        "results": result,  # Timeseries data + metadata
        "cache_hit": task.cache_hit,
        "execution_time": task.execution_time
    }


@app.delete("/api/simulations/{task_id}")
async def cancel_simulation(task_id: str):
    """Cancel a queued or running simulation."""
    success = orchestrator.cancel_task(task_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found or already completed")

    return {"task_id": task_id, "status": "CANCELLED"}


@app.get("/api/stats")
async def get_statistics():
    """Get orchestrator statistics."""
    stats = orchestrator.get_stats()
    cache_stats = cache.get_stats()

    return {
        "orchestrator": {
            "queue_length": stats.queue_length,
            "active_simulations": stats.active_count,
            "completed_today": stats.completed_today,
            "failed_today": stats.failed_today,
            "avg_execution_time": stats.avg_execution_time
        },
        "cache": {
            "total_entries": cache_stats.total_entries,
            "hit_rate": cache_stats.hit_rate,
            "total_size_mb": cache_stats.total_size_mb
        }
    }


@app.post("/api/cache/clear")
async def clear_cache():
    """Clear all cached simulation results."""
    cache.clear_all()
    return {"message": "Cache cleared successfully"}
```

### Batch Simulation Endpoint

```python
@app.post("/api/simulations/batch", status_code=202)
async def submit_simulation_batch(
    requests: list[SimulationRequest]
):
    """
    Submit multiple simulations as a batch.

    Returns immediately with list of task_ids.
    Leverages PLECS native batch parallel API for performance.
    """
    task_ids = []

    for req in requests:
        task_id = str(uuid.uuid4())
        await orchestrator.submit_simulation(
            task_id=task_id,
            model_file=req.model_file,
            parameters=req.parameters,
            priority=TaskPriority[req.priority]
        )
        task_ids.append(task_id)

    return {
        "task_ids": task_ids,
        "batch_size": len(task_ids),
        "status": "QUEUED"
    }
```

---

## Client Implementations: The Ecosystem Emerges

Once the API existed, users started building client libraries.

### Python Client (Thin Wrapper)

```python
import requests
import time
from typing import Dict, Any

class PyPLECSClient:
    """Python client for PyPLECS REST API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def simulate(
        self,
        model_file: str,
        parameters: Dict[str, Any],
        priority: str = "NORMAL",
        wait: bool = True
    ) -> Dict[str, Any]:
        """
        Submit simulation and optionally wait for completion.

        Args:
            model_file: Path to PLECS model
            parameters: ModelVars dictionary
            priority: CRITICAL, HIGH, NORMAL, LOW
            wait: Block until completion

        Returns:
            Simulation results dictionary
        """
        # Submit simulation
        response = requests.post(
            f"{self.base_url}/api/simulations",
            json={
                "model_file": model_file,
                "parameters": parameters,
                "priority": priority
            }
        )
        response.raise_for_status()

        task_id = response.json()["task_id"]

        if not wait:
            return {"task_id": task_id, "status": "QUEUED"}

        # Poll for completion
        return self.wait_for_completion(task_id)

    def wait_for_completion(self, task_id: str, poll_interval: float = 0.5) -> Dict[str, Any]:
        """Poll until simulation completes."""
        while True:
            status_response = requests.get(f"{self.base_url}/api/simulations/{task_id}")
            status = status_response.json()["status"]

            if status == "COMPLETED":
                break
            elif status == "FAILED":
                raise RuntimeError(f"Simulation failed: {status_response.json()['error']}")

            time.sleep(poll_interval)

        # Get results
        results_response = requests.get(f"{self.base_url}/api/simulations/{task_id}/results")
        return results_response.json()

    def simulate_batch(
        self,
        simulations: list[dict],
        wait: bool = True
    ) -> list[dict]:
        """Submit batch of simulations."""
        response = requests.post(
            f"{self.base_url}/api/simulations/batch",
            json=simulations
        )
        response.raise_for_status()

        task_ids = response.json()["task_ids"]

        if not wait:
            return task_ids

        # Wait for all to complete
        results = []
        for task_id in task_ids:
            result = self.wait_for_completion(task_id)
            results.append(result)

        return results
```

### MATLAB Client

```matlab
% MATLAB client for PyPLECS REST API
classdef PyPLECSClient
    properties
        baseURL
    end

    methods
        function obj = PyPLECSClient(baseURL)
            if nargin < 1
                baseURL = 'http://localhost:8000';
            end
            obj.baseURL = baseURL;
        end

        function result = simulate(obj, modelFile, parameters, varargin)
            % Submit simulation to PyPLECS API
            %
            % Usage:
            %   result = client.simulate('model.plecs', struct('Vi', 24.0))
            %   result = client.simulate('model.plecs', struct('Vi', 24.0), 'priority', 'HIGH')

            p = inputParser;
            addParameter(p, 'priority', 'NORMAL');
            parse(p, varargin{:});

            % Prepare request
            url = sprintf('%s/api/simulations', obj.baseURL);
            options = weboptions('MediaType', 'application/json', 'Timeout', 30);

            request = struct(...
                'model_file', modelFile, ...
                'parameters', parameters, ...
                'priority', p.Results.priority ...
            );

            % Submit
            response = webwrite(url, request, options);
            taskID = response.task_id;

            % Poll for completion
            result = obj.waitForCompletion(taskID);
        end

        function result = waitForCompletion(obj, taskID)
            % Poll until simulation completes
            statusURL = sprintf('%s/api/simulations/%s', obj.baseURL, taskID);
            resultsURL = sprintf('%s/results', statusURL);
            options = weboptions('MediaType', 'application/json', 'Timeout', 30);

            while true
                status = webread(statusURL, options);

                if strcmp(status.status, 'COMPLETED')
                    break;
                elseif strcmp(status.status, 'FAILED')
                    error('Simulation failed: %s', status.error);
                end

                pause(0.5);
            end

            % Get results
            result = webread(resultsURL, options);
        end
    end
end
```

**Real user feedback**:

> "This is brilliant. We're now using PyPLECS caching from our entire MATLAB optimization suite. Simulations that took 12 hours now take 2 hours. We didn't change a single line of our algorithm code."

### JavaScript/Web Client

```javascript
// JavaScript client for browser-based dashboards
class PyPLECSClient {
  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
  }

  async simulate(modelFile, parameters, priority = 'NORMAL', wait = true) {
    // Submit simulation
    const response = await fetch(`${this.baseURL}/api/simulations`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        model_file: modelFile,
        parameters: parameters,
        priority: priority
      })
    });

    const {task_id} = await response.json();

    if (!wait) return {task_id, status: 'QUEUED'};

    // Wait for completion
    return await this.waitForCompletion(task_id);
  }

  async waitForCompletion(taskId, pollInterval = 500) {
    while (true) {
      const response = await fetch(`${this.baseURL}/api/simulations/${taskId}`);
      const {status, error} = await response.json();

      if (status === 'COMPLETED') break;
      if (status === 'FAILED') throw new Error(`Simulation failed: ${error}`);

      await new Promise(r => setTimeout(r, pollInterval));
    }

    // Get results
    const results = await fetch(`${this.baseURL}/api/simulations/${taskId}/results`);
    return results.json();
  }

  async getStats() {
    const response = await fetch(`${this.baseURL}/api/stats`);
    return response.json();
  }
}

// Usage in React dashboard
const client = new PyPLECSClient();

function SimulationDashboard() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    const interval = setInterval(async () => {
      const data = await client.getStats();
      setStats(data);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h2>PyPLECS Orchestrator Status</h2>
      <p>Queue Length: {stats?.orchestrator.queue_length}</p>
      <p>Active Simulations: {stats?.orchestrator.active_simulations}</p>
      <p>Cache Hit Rate: {(stats?.cache.hit_rate * 100).toFixed(1)}%</p>
    </div>
  );
}
```

---

## Unexpected Use Cases

Once the API existed, users built integrations I never imagined:

**1. CI/CD Pipeline Validation**

```yaml
# .github/workflows/validate-design.yml
name: Validate Power Converter Design

on: [push, pull_request]

jobs:
  simulate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Run Design Verification Simulations
        run: |
          # Submit simulation via REST API
          curl -X POST http://plecs-server:8000/api/simulations \
            -H "Content-Type: application/json" \
            -d '{
              "model_file": "designs/buck_converter_v2.plecs",
              "parameters": {"Vi": 24, "Vo": 5, "L": 100e-6, "C": 220e-6},
              "priority": "HIGH"
            }' \
            | jq -r '.task_id' > task_id.txt

      - name: Wait for Completion and Validate
        run: |
          task_id=$(cat task_id.txt)
          # Poll until complete
          # Validate output voltage within spec
          # Fail build if out of spec
```

**2. Excel Integration (VBA)**

```vba
' Excel VBA macro for non-programmers
Sub RunPLECSSimulation()
    Dim modelFile As String
    Dim Vi As Double

    ' Read inputs from Excel cells
    modelFile = Range("B2").Value
    Vi = Range("B3").Value

    ' Call PyPLECS API
    Dim http As Object
    Set http = CreateObject("MSXML2.XMLHTTP")

    http.Open "POST", "http://localhost:8000/api/simulations", False
    http.setRequestHeader "Content-Type", "application/json"

    Dim requestBody As String
    requestBody = "{""model_file"":""" & modelFile & """, ""parameters"":{""Vi"":" & Vi & "}}"

    http.send requestBody

    ' Parse task_id
    Dim taskId As String
    taskId = ExtractTaskId(http.responseText)

    ' Wait and get results
    ' Write results back to Excel
End Sub
```

**3. Slack Bot for Team Collaboration**

```python
from slack_bolt import App

slack_app = App(token=os.environ["SLACK_BOT_TOKEN"])
pyplecs_client = PyPLECSClient()

@slack_app.command("/simulate")
def simulate_command(ack, command, respond):
    ack()

    # Parse: /simulate model.plecs Vi=24 L=100e-6
    args = parse_command_args(command["text"])

    # Submit to PyPLECS
    result = pyplecs_client.simulate(
        model_file=args["model_file"],
        parameters=args["parameters"]
    )

    # Post results to Slack
    respond(f"Simulation complete! Efficiency: {result['efficiency']:.2%}")
```

---

## Strategic Lessons

### 1. API-First Design Enables Ecosystems

A Python library has **users**.
A REST API has an **ecosystem**.

The difference: users extend APIs in ways you never imagined.

### 2. Language-Agnostic = Future-Proof

In 5 years:
- Python might not dominate
- New languages will emerge
- Web will still speak HTTP

**REST APIs age better than language-specific libraries.**

### 3. Auto-Documentation Saves Weeks

FastAPI's auto-generated docs (`/docs` endpoint) saved me **weeks of writing documentation**.

And unlike manually written docs, generated docs **never go stale**.

### 4. Start with HTTP, Not Bindings

I could have written:
- MATLAB bindings (MEX files)
- Julia bindings (C FFI)
- JavaScript bindings (Node.js addon)

Instead, I wrote **one HTTP API** that all of them could use.

**Simpler to build, easier to maintain, more flexible long-term.**

---

## Coming Up Next

**Article 6**: "The Refactoring That Deleted 1,581 Lines"

The terrifying decision to delete nearly half my codebase, and why it was the best technical decision I made.

---

## Code

Full REST API implementation:
- **GitHub**: [PyPLECS v1.0.0](https://github.com/tinix84/pyplecs)
- **API module**: `pyplecs/api/__init__.py`
- **Client examples**: `examples/clients/`
- **API docs**: `http://localhost:8000/docs` (when running)

---

**Subscribe** for Article 6: The psychology and practice of deleting 1,581 lines of working code.

---

**Meta**: 3,056 words | ~15-minute read | Technical depth: Medium-High
**Hook**: Language lock-in problem
**Lesson**: REST API architecture and ecosystem thinking
**CTA**: Share integration ideas and use cases
