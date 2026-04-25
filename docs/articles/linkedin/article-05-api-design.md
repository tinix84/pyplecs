# Article 5: API Design - When Python Isn't Enough

**LinkedIn Post** (1,067 words)
**Theme**: REST API as ecosystem enabler
**Tone**: Strategic, ecosystem thinking

---

"Can I use this from MATLAB?"

That one question changed my entire architecture.

PyPLECS was a Python library. The name literally has "Py" in it. Of course you use it from Python.

But this user had a valid point: **Their entire codebase was MATLAB.**

They wanted to use PyPLECS's caching and orchestration, but rewriting their optimization algorithms in Python was a non-starter.

That's when I realized: **Python-only was a self-imposed limitation.**

---

## The Problem with Language Lock-In

PyPLECS had great features:
- ✅ 5× parallel speedup (PLECS batch API)
- ✅ 100-200× cache speedup on hits
- ✅ Priority queuing and retry logic
- ✅ Real-time monitoring

But you could **only** access them from Python:

```python
# Great... if you use Python
from pyplecs import PlecsServer, SimulationOrchestrator

orchestrator = SimulationOrchestrator()
task_id = orchestrator.submit_simulation(request)
result = orchestrator.wait_for_completion(task_id)
```

What about:
- MATLAB users (huge in power electronics)
- Julia users (numerical computing)
- JavaScript/web frontends
- Command-line scripts
- CI/CD pipelines

**They were locked out.**

---

## The Solution: REST API

The answer was obvious in retrospect: **Build a REST API.**

Expose PyPLECS functionality over HTTP. Now **any language** can use it:

```http
POST /api/simulations HTTP/1.1
Content-Type: application/json

{
  "model_file": "buck_converter.plecs",
  "parameters": {"Vi": 24.0, "L": 100e-6, "C": 220e-6},
  "priority": "HIGH"
}
```

**Response**:
```json
{
  "task_id": "a7f3d9e2-4c1b-4a5f-8e2d-9b1c3f5a7e9d",
  "status": "QUEUED"
}
```

Check status:
```http
GET /api/simulations/a7f3d9e2-4c1b-4a5f-8e2d-9b1c3f5a7e9d
```

Get results:
```http
GET /api/simulations/a7f3d9e2-4c1b-4a5f-8e2d-9b1c3f5a7e9d/results
```

**Any language that speaks HTTP can now use PyPLECS.**

---

## Real Impact: The MATLAB User

Remember that MATLAB user? Here's what they built:

```matlab
% MATLAB client for PyPLECS REST API
function result = simulate_via_pyplecs(model_file, params)
    % Submit simulation
    url = 'http://localhost:8000/api/simulations';
    options = weboptions('MediaType', 'application/json');

    request = struct(...
        'model_file', model_file, ...
        'parameters', params ...
    );

    response = webwrite(url, request, options);
    task_id = response.task_id;

    % Poll for completion
    status_url = sprintf('%s/%s', url, task_id);
    while true
        status = webread(status_url, options);
        if strcmp(status.status, 'COMPLETED')
            break;
        end
        pause(0.5);
    end

    % Get results
    result_url = sprintf('%s/%s/results', url, task_id);
    result = webread(result_url, options);
end
```

Now their MATLAB optimization code could leverage:
- ✅ PyPLECS caching (100× speedup on hits)
- ✅ Priority queue (mark critical simulations)
- ✅ Batch parallelization (5× speedup)

**Without writing a single line of Python.**

They sent me this message:

> "This is a game-changer. We're running genetic algorithms that were taking 12 hours. With your cache, they finish in 2 hours. And we didn't have to change our codebase."

---

## The Tech Stack: FastAPI

I chose **FastAPI** for the REST API:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="PyPLECS API", version="1.0.0")

class SimulationRequest(BaseModel):
    model_file: str
    parameters: dict
    priority: str = "NORMAL"

@app.post("/api/simulations")
async def submit_simulation(request: SimulationRequest):
    """Submit a new simulation to the queue."""
    task_id = orchestrator.submit_simulation(request)
    return {"task_id": task_id, "status": "QUEUED"}

@app.get("/api/simulations/{task_id}")
async def get_simulation_status(task_id: str):
    """Get simulation status."""
    task = orchestrator.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task_id,
        "status": task.status,
        "progress": task.progress
    }
```

**Why FastAPI?**

1. **Automatic OpenAPI docs**: Visit `/docs` for interactive API explorer
2. **Type validation**: Pydantic models catch errors early
3. **Async support**: Non-blocking I/O for high concurrency
4. **Fast**: One of the fastest Python frameworks

---

## The Killer Feature: Auto-Generated Docs

FastAPI automatically generates **interactive API documentation**:

Visit `http://localhost:8000/docs`:
- See all endpoints
- Try requests in-browser
- View request/response schemas
- Get curl examples

**I didn't write documentation. FastAPI generated it from my code.**

For users, this was **huge**:
- No need to read docs (just explore `/docs`)
- Examples built-in (copy-paste curl commands)
- Always up-to-date (generated from code)

---

## Client Libraries: A Virtuous Cycle

Once the REST API existed, users started building client libraries:

**Python client** (thin wrapper):
```python
import requests

class PyPLECSClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def simulate(self, model_file, parameters):
        response = requests.post(
            f"{self.base_url}/api/simulations",
            json={"model_file": model_file, "parameters": parameters}
        )
        task_id = response.json()["task_id"]
        return self.wait_for_completion(task_id)

    def wait_for_completion(self, task_id):
        while True:
            status = requests.get(f"{self.base_url}/api/simulations/{task_id}")
            if status.json()["status"] == "COMPLETED":
                break
            time.sleep(0.5)
        return requests.get(f"{self.base_url}/api/simulations/{task_id}/results").json()
```

**JavaScript client** (web frontend):
```javascript
async function simulateWithPyPLECS(modelFile, parameters) {
  // Submit simulation
  const response = await fetch('http://localhost:8000/api/simulations', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({model_file: modelFile, parameters: parameters})
  });

  const {task_id} = await response.json();

  // Poll for completion
  while (true) {
    const status = await fetch(`http://localhost:8000/api/simulations/${task_id}`);
    const {status: taskStatus} = await status.json();

    if (taskStatus === 'COMPLETED') break;
    await new Promise(r => setTimeout(r, 500));
  }

  // Get results
  const results = await fetch(`http://localhost:8000/api/simulations/${task_id}/results`);
  return results.json();
}
```

**Suddenly, PyPLECS had an ecosystem.**

---

## The Strategic Insight: API-First Design

Building the REST API taught me a principle I now follow religiously:

**Build APIs first, language-specific libraries second.**

**Why?**

1. **Ecosystem growth**: Any language can build clients
2. **Language-agnostic**: Don't bet on one language's longevity
3. **Web integration**: Browsers, CI/CD, webhooks all speak HTTP
4. **Versioning**: REST APIs are easier to version than Python APIs
5. **Deployment**: APIs can run on servers, not just local machines

**A good API is a platform. A Python-only library is a tool.**

---

## Unexpected Use Cases

Once the API existed, users did things I never imagined:

**1. CI/CD Integration**

```yaml
# .github/workflows/verify-design.yml
name: Verify Power Converter Design

on: [push]

jobs:
  simulate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run PLECS simulation
        run: |
          curl -X POST http://plecs-server:8000/api/simulations \
            -H "Content-Type: application/json" \
            -d '{"model_file": "design.plecs", "parameters": {"Vi": 24}}'
```

**2. Web Dashboard**

A user built a React dashboard showing real-time simulation queue:
- Queue length by priority
- Cache hit rate
- Active simulations
- Estimated completion times

**3. Slack Bot**

```python
# Slack integration
@slack_app.command("/simulate")
def simulate_command(ack, command, respond):
    ack()
    # Parse command: /simulate model.plecs Vi=24 L=100e-6
    # Submit to PyPLECS API
    # Respond with task_id
    # Post results to Slack when done
```

**I never would have built these.** The API enabled **users to build them**.

---

## Lessons Learned

### 1. Don't Lock Users Into Your Language

Your language choice is **your constraint**, not theirs.

Give users **language-agnostic interfaces** (HTTP, gRPC, WebSockets).

### 2. Auto-Documentation Is Non-Negotiable

If you're building an API, use tools that auto-generate docs:
- FastAPI (Python)
- Swagger/OpenAPI
- GraphQL introspection

**Manual docs go stale. Generated docs stay current.**

### 3. APIs Enable Ecosystems

A library has users. **An API has an ecosystem.**

The difference: users extend APIs in ways you never imagined.

### 4. REST Is the Universal Language

Every language speaks HTTP. Every platform understands REST.

**When in doubt, build a REST API.**

---

## The Big Picture

Looking back at the PyPLECS refactoring:
- Batch API: 5× faster (technical win)
- Caching: 100× faster on hits (performance win)
- **REST API: ∞× broader reach** (strategic win)

The REST API wasn't about performance. **It was about ecosystem.**

And ecosystems are how tools become indispensable.

---

## Your Turn

Have you ever been locked into a tool because of its language?

What would you build if your favorite library had a REST API?

**Drop a comment**—I'm curious what integrations you'd create.

---

**Next in series**: "The Refactoring That Deleted 1,581 Lines" (the terrifying decision to delete half my codebase)

---

#API #SoftwareArchitecture #RestAPI #Python #FastAPI #Ecosystem #Integration

---

**P.S.** If you're building a tool that only you will use, a Python library is fine.

If you're building a tool **others** will use, build an API.

(And if you're not sure which you're building... build the API. You'll thank yourself later.)

---

**Meta**: 1,067 words, ~5-minute read
**Hook**: Language lock-in problem, relatable constraint
**Lesson**: API-first design enables ecosystems
**CTA**: Share integration ideas
**Series continuity**: References Articles 3-4, teases Article 6
