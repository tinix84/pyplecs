# PyPLECS REST API Reference

Complete reference for the PyPLECS REST API.

---

## Overview

The PyPLECS REST API provides language-agnostic access to simulation capabilities through HTTP endpoints. Built with FastAPI, it offers:

- 🔄 **Submit simulations** from any language (Python, MATLAB, JavaScript, curl)
- 📊 **Monitor status** with real-time updates
- 💾 **Cache management** for performance optimization
- 📈 **Statistics** for queue and orchestrator monitoring
- 📚 **Auto-generated documentation** at `/docs` and `/redoc`

### Base Information

- **Base URL**: `http://localhost:8000` (configurable in config.yml)
- **Protocol**: HTTP/1.1
- **Content-Type**: `application/json`
- **API Version**: v1 (included in v1.0.0)
- **OpenAPI Docs**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc**: `http://localhost:8000/redoc` (Alternative docs)

---

## Table of Contents

- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [Simulations](#simulations)
  - [Cache](#cache)
  - [System](#system)
- [Data Models](#data-models)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [Rate Limiting](#rate-limiting)

---

## Quick Start

### Starting the API Server

```bash
# Method 1: Entry point
pyplecs-api

# Method 2: Direct module
python -m pyplecs.api

# Custom port
pyplecs-api --port 8080

# Custom host (bind to all interfaces)
pyplecs-api --host 0.0.0.0
```

### First API Call

```bash
# Check API health
curl http://localhost:8000/health

# Expected response
{"status": "healthy", "version": "1.0.0"}
```

---

## Authentication

### Current Version (v1.0.0)

**No authentication required** - API is open for local development.

⚠️ **Production Warning**: Do not expose API to untrusted networks without authentication.

### Planned (v1.x)

Future versions will support:
- **API Keys**: Simple token-based authentication
- **JWT**: JSON Web Tokens for stateless auth
- **OAuth 2.0**: Enterprise SSO integration

**Example (future)**:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:8000/simulations
```

---

## Endpoints

### Simulations

#### POST /simulations

Submit a single simulation for execution.

**Request Body**:
```json
{
  "model_file": "path/to/model.plecs",
  "parameters": {
    "Vi": 12.0,
    "Vo": 5.0,
    "fsw": 100000
  },
  "output_variables": ["Vo", "IL", "Iin"],
  "priority": "HIGH",
  "metadata": {
    "user": "engineer@company.com",
    "project": "buck_converter_design"
  }
}
```

**Fields**:
- `model_file` (string, required): Path to PLECS model file
- `parameters` (object, optional): ModelVars parameters as key-value pairs
- `output_variables` (array, optional): Variables to extract from results
- `priority` (string, optional): Task priority (`CRITICAL`, `HIGH`, `NORMAL`, `LOW`). Default: `NORMAL`
- `metadata` (object, optional): Custom metadata for tracking

**Response** (201 Created):
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "queued",
  "priority": "HIGH",
  "submitted_at": "2025-01-25T10:30:00Z",
  "message": "Simulation submitted successfully"
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:8000/simulations \
  -H "Content-Type: application/json" \
  -d '{
    "model_file": "models/buck.plecs",
    "parameters": {"Vi": 12.0, "Vo": 5.0},
    "priority": "HIGH"
  }'
```

**Python Example**:
```python
import requests

response = requests.post(
    "http://localhost:8000/simulations",
    json={
        "model_file": "models/buck.plecs",
        "parameters": {"Vi": 12.0, "Vo": 5.0},
        "priority": "HIGH"
    }
)
task_id = response.json()["task_id"]
print(f"Task submitted: {task_id}")
```

---

#### POST /simulations/batch

Submit multiple simulations for batch execution.

**Request Body**:
```json
[
  {
    "model_file": "models/buck.plecs",
    "parameters": {"Vi": 12.0},
    "priority": "HIGH"
  },
  {
    "model_file": "models/buck.plecs",
    "parameters": {"Vi": 24.0},
    "priority": "HIGH"
  },
  {
    "model_file": "models/buck.plecs",
    "parameters": {"Vi": 48.0},
    "priority": "HIGH"
  }
]
```

**Response** (201 Created):
```json
{
  "task_ids": [
    "abc123-def456-ghi789",
    "jkl012-mno345-pqr678",
    "stu901-vwx234-yza567"
  ],
  "batch_size": 3,
  "message": "Submitted 3 simulations for batch execution",
  "submitted_at": "2025-01-25T10:30:00Z"
}
```

**Benefits**:
- Single API call for multiple simulations
- Orchestrator batches for parallel execution
- Reduced HTTP overhead
- Better performance on large parameter sweeps

**cURL Example**:
```bash
curl -X POST http://localhost:8000/simulations/batch \
  -H "Content-Type: application/json" \
  -d '[
    {"model_file": "buck.plecs", "parameters": {"Vi": 12}},
    {"model_file": "buck.plecs", "parameters": {"Vi": 24}},
    {"model_file": "buck.plecs", "parameters": {"Vi": 48}}
  ]'
```

**Python Example**:
```python
params_list = [{"Vi": v} for v in range(12, 49, 6)]
requests_list = [
    {"model_file": "buck.plecs", "parameters": p}
    for p in params_list
]

response = requests.post(
    "http://localhost:8000/simulations/batch",
    json=requests_list
)
task_ids = response.json()["task_ids"]
```

---

#### GET /simulations/{task_id}

Get simulation status and metadata.

**Parameters**:
- `task_id` (path, required): Simulation task ID

**Response** (200 OK):
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "completed",
  "priority": "HIGH",
  "model_file": "models/buck.plecs",
  "parameters": {"Vi": 12.0, "Vo": 5.0},
  "submitted_at": "2025-01-25T10:30:00Z",
  "started_at": "2025-01-25T10:30:05Z",
  "completed_at": "2025-01-25T10:30:15Z",
  "duration_seconds": 10.0,
  "cache_hit": false,
  "retry_count": 0
}
```

**Status Values**:
- `queued`: Waiting in queue
- `running`: Currently executing
- `completed`: Finished successfully
- `failed`: Execution failed
- `cancelled`: Cancelled by user

**cURL Example**:
```bash
curl http://localhost:8000/simulations/abc123-def456-ghi789
```

---

#### GET /simulations/{task_id}/result

Get simulation results.

**Parameters**:
- `task_id` (path, required): Simulation task ID

**Response** (200 OK):
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "completed",
  "results": {
    "Vo": [0.0, 0.1, 0.2, ..., 5.0],
    "IL": [0.0, 0.5, 1.0, ..., 2.5],
    "t": [0.0, 1e-6, 2e-6, ..., 0.001]
  },
  "metadata": {
    "simulation_time": 10.0,
    "cache_hit": false,
    "plecs_version": "4.7"
  }
}
```

**Error Response** (202 Accepted):
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "running",
  "message": "Simulation still in progress. Poll again later."
}
```

**cURL Example**:
```bash
curl http://localhost:8000/simulations/abc123-def456-ghi789/result
```

**Python Example with Polling**:
```python
import time
import requests

task_id = "abc123-def456-ghi789"
while True:
    response = requests.get(
        f"http://localhost:8000/simulations/{task_id}/result"
    )

    if response.status_code == 200:
        results = response.json()["results"]
        print(f"Vo: {results['Vo']}")
        break
    elif response.status_code == 202:
        print("Still running...")
        time.sleep(1)
    else:
        print(f"Error: {response.text}")
        break
```

---

#### DELETE /simulations/{task_id}

Cancel a queued or running simulation.

**Parameters**:
- `task_id` (path, required): Simulation task ID

**Response** (200 OK):
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "cancelled",
  "message": "Simulation cancelled successfully"
}
```

**Error Response** (400 Bad Request):
```json
{
  "detail": "Cannot cancel completed simulation"
}
```

**cURL Example**:
```bash
curl -X DELETE http://localhost:8000/simulations/abc123-def456-ghi789
```

---

### Cache

#### GET /cache/stats

Get cache statistics.

**Response** (200 OK):
```json
{
  "enabled": true,
  "hits": 1523,
  "misses": 478,
  "hit_rate": 0.761,
  "total_entries": 2001,
  "storage_format": "parquet",
  "compression": "snappy",
  "disk_usage_mb": 145.7,
  "oldest_entry": "2025-01-20T08:00:00Z",
  "newest_entry": "2025-01-25T10:30:00Z"
}
```

**cURL Example**:
```bash
curl http://localhost:8000/cache/stats
```

---

#### POST /cache/clear

Clear the simulation cache.

**Query Parameters**:
- `confirm` (boolean, optional): Confirmation flag (default: false)

**Request**:
```bash
curl -X POST "http://localhost:8000/cache/clear?confirm=true"
```

**Response** (200 OK):
```json
{
  "message": "Cache cleared successfully",
  "entries_removed": 2001,
  "disk_space_freed_mb": 145.7
}
```

**Error Response** (400 Bad Request):
```json
{
  "detail": "Confirmation required. Set confirm=true query parameter."
}
```

---

#### GET /cache/entry/{cache_key}

Get specific cache entry metadata.

**Parameters**:
- `cache_key` (path, required): Cache entry hash

**Response** (200 OK):
```json
{
  "cache_key": "abc123def456...",
  "model_file": "models/buck.plecs",
  "parameters": {"Vi": 12.0, "Vo": 5.0},
  "created_at": "2025-01-25T10:30:15Z",
  "accessed_at": "2025-01-25T10:35:00Z",
  "access_count": 5,
  "size_bytes": 1024000,
  "storage_format": "parquet"
}
```

---

### System

#### GET /health

Health check endpoint.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "plecs_connected": true
}
```

**Use Cases**:
- Load balancer health checks
- Monitoring systems
- Container orchestration (Kubernetes readiness probe)

**cURL Example**:
```bash
curl http://localhost:8000/health
```

---

#### GET /stats

Get orchestrator statistics.

**Response** (200 OK):
```json
{
  "queue": {
    "pending": 5,
    "running": 2,
    "completed": 1523,
    "failed": 12,
    "cancelled": 3
  },
  "performance": {
    "average_duration_seconds": 8.5,
    "total_simulations": 1545,
    "cache_hit_rate": 0.761,
    "speedup_factor": 4.2
  },
  "system": {
    "cpu_cores": 4,
    "batch_size": 4,
    "max_concurrent": 4,
    "uptime_seconds": 3600
  }
}
```

**cURL Example**:
```bash
curl http://localhost:8000/stats
```

---

#### GET /logs

Get recent API logs (if enabled).

**Query Parameters**:
- `limit` (integer, optional): Number of log entries (default: 100, max: 1000)
- `level` (string, optional): Log level filter (`DEBUG`, `INFO`, `WARNING`, `ERROR`)

**Response** (200 OK):
```json
{
  "logs": [
    {
      "timestamp": "2025-01-25T10:30:00Z",
      "level": "INFO",
      "message": "Simulation submitted",
      "task_id": "abc123-def456-ghi789"
    },
    {
      "timestamp": "2025-01-25T10:30:15Z",
      "level": "INFO",
      "message": "Simulation completed",
      "task_id": "abc123-def456-ghi789",
      "duration": 15.0
    }
  ],
  "count": 2
}
```

**cURL Example**:
```bash
curl "http://localhost:8000/logs?limit=50&level=INFO"
```

---

## Data Models

### SimulationRequest

```json
{
  "model_file": "string (required)",
  "parameters": "object (optional)",
  "output_variables": "array of strings (optional)",
  "priority": "enum: CRITICAL|HIGH|NORMAL|LOW (optional, default: NORMAL)",
  "metadata": "object (optional)"
}
```

### SimulationResponse

```json
{
  "task_id": "string (UUID)",
  "status": "enum: queued|running|completed|failed|cancelled",
  "priority": "enum: CRITICAL|HIGH|NORMAL|LOW",
  "model_file": "string",
  "parameters": "object",
  "submitted_at": "datetime (ISO 8601)",
  "started_at": "datetime (ISO 8601, nullable)",
  "completed_at": "datetime (ISO 8601, nullable)",
  "duration_seconds": "number (nullable)",
  "cache_hit": "boolean",
  "retry_count": "integer",
  "error_message": "string (nullable)"
}
```

### SimulationResult

```json
{
  "task_id": "string (UUID)",
  "status": "enum: completed|failed",
  "results": "object (key-value pairs of variable names to arrays)",
  "metadata": "object"
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 202 | Accepted | Request accepted, processing |
| 400 | Bad Request | Invalid request parameters |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource conflict |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

### Error Response Format

```json
{
  "detail": "Descriptive error message",
  "error_code": "VALIDATION_ERROR",
  "field": "model_file",
  "suggestion": "Provide absolute path to .plecs file"
}
```

### Common Errors

#### 400 Bad Request
```json
{
  "detail": "Invalid priority value. Must be one of: CRITICAL, HIGH, NORMAL, LOW",
  "error_code": "INVALID_PRIORITY"
}
```

#### 404 Not Found
```json
{
  "detail": "Task ID not found: abc123-def456-ghi789",
  "error_code": "TASK_NOT_FOUND"
}
```

#### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "model_file"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

#### 500 Internal Server Error
```json
{
  "detail": "PLECS XML-RPC connection failed",
  "error_code": "PLECS_CONNECTION_ERROR",
  "suggestion": "Ensure PLECS is running with XML-RPC enabled"
}
```

---

## Examples

### Python Client

```python
import requests
import time
from typing import Dict, Any, List

class PyPLECSClient:
    """Simple Python client for PyPLECS REST API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def submit_simulation(
        self,
        model_file: str,
        parameters: Dict[str, float],
        priority: str = "NORMAL"
    ) -> str:
        """Submit simulation and return task ID."""
        response = requests.post(
            f"{self.base_url}/simulations",
            json={
                "model_file": model_file,
                "parameters": parameters,
                "priority": priority
            }
        )
        response.raise_for_status()
        return response.json()["task_id"]

    def wait_for_result(
        self,
        task_id: str,
        poll_interval: float = 1.0,
        timeout: float = 300.0
    ) -> Dict[str, Any]:
        """Poll for result until completed or timeout."""
        start_time = time.time()

        while True:
            response = requests.get(
                f"{self.base_url}/simulations/{task_id}/result"
            )

            if response.status_code == 200:
                return response.json()["results"]
            elif response.status_code == 202:
                # Still running
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Simulation timed out after {timeout}s")
                time.sleep(poll_interval)
            else:
                response.raise_for_status()

    def simulate(
        self,
        model_file: str,
        parameters: Dict[str, float],
        **kwargs
    ) -> Dict[str, Any]:
        """Submit and wait for simulation result."""
        task_id = self.submit_simulation(model_file, parameters, **kwargs)
        return self.wait_for_result(task_id)

# Usage
client = PyPLECSClient()
results = client.simulate(
    "models/buck.plecs",
    {"Vi": 12.0, "Vo": 5.0}
)
print(f"Output voltage: {results['Vo']}")
```

### MATLAB Client

```matlab
% MATLAB HTTP client for PyPLECS API
classdef PyPLECSClient
    properties
        baseURL = 'http://localhost:8000';
    end

    methods
        function task_id = submitSimulation(obj, model_file, parameters, priority)
            if nargin < 4
                priority = 'NORMAL';
            end

            % Prepare request
            request_data = struct(...
                'model_file', model_file, ...
                'parameters', parameters, ...
                'priority', priority ...
            );

            % Submit via HTTP POST
            options = weboptions('MediaType', 'application/json');
            response = webwrite(...
                [obj.baseURL '/simulations'], ...
                request_data, ...
                options ...
            );

            task_id = response.task_id;
        end

        function results = waitForResult(obj, task_id, timeout)
            if nargin < 3
                timeout = 300;  % 5 minutes
            end

            start_time = tic;
            while toc(start_time) < timeout
                try
                    options = weboptions('MediaType', 'application/json');
                    response = webread(...
                        [obj.baseURL '/simulations/' task_id '/result'], ...
                        options ...
                    );

                    if strcmp(response.status, 'completed')
                        results = response.results;
                        return;
                    end
                catch ME
                    % Still running (202 status)
                    pause(1);
                end
            end

            error('Simulation timed out');
        end

        function results = simulate(obj, model_file, parameters, varargin)
            task_id = obj.submitSimulation(model_file, parameters, varargin{:});
            results = obj.waitForResult(task_id);
        end
    end
end

% Usage
client = PyPLECSClient();
params = struct('Vi', 12.0, 'Vo', 5.0);
results = client.simulate('models/buck.plecs', params);
plot(results.t, results.Vo);
```

### JavaScript Client

```javascript
// JavaScript/Node.js client for PyPLECS API
class PyPLECSClient {
  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
  }

  async submitSimulation(modelFile, parameters, priority = 'NORMAL') {
    const response = await fetch(`${this.baseURL}/simulations`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        model_file: modelFile,
        parameters: parameters,
        priority: priority
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.task_id;
  }

  async waitForResult(taskId, pollInterval = 1000, timeout = 300000) {
    const startTime = Date.now();

    while (true) {
      const response = await fetch(
        `${this.baseURL}/simulations/${taskId}/result`
      );

      if (response.status === 200) {
        const data = await response.json();
        return data.results;
      } else if (response.status === 202) {
        // Still running
        if (Date.now() - startTime > timeout) {
          throw new Error(`Timeout after ${timeout}ms`);
        }
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      } else {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    }
  }

  async simulate(modelFile, parameters, options = {}) {
    const taskId = await this.submitSimulation(
      modelFile,
      parameters,
      options.priority
    );
    return await this.waitForResult(taskId, options.pollInterval, options.timeout);
  }
}

// Usage
const client = new PyPLECSClient();
const results = await client.simulate(
  'models/buck.plecs',
  {Vi: 12.0, Vo: 5.0}
);
console.log('Output voltage:', results.Vo);
```

---

## Rate Limiting

### Current Version (v1.0.0)

**No rate limiting** - API is open for local development.

### Planned (v1.x)

Future versions may implement:
- **Per-IP rate limiting**: 100 requests/minute
- **Authenticated users**: 1000 requests/minute
- **Batch submissions**: Count as single request

**Rate limit headers** (future):
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1643110800
```

---

## WebSocket Support

For real-time updates, connect to WebSocket endpoint.

**Endpoint**: `ws://localhost:8000/ws`

**Example**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Task update:', update);
  // {task_id: "abc123", status: "running", progress: 0.5}
};

ws.onopen = () => {
  ws.send(JSON.stringify({
    action: 'subscribe',
    task_id: 'abc123-def456-ghi789'
  }));
};
```

See [WEBGUI.md](WEBGUI.md) for Web GUI usage with WebSocket.

---

## Configuration

API server configuration in `config/default.yml`:

```yaml
api:
  host: "0.0.0.0"      # Bind to all interfaces
  port: 8000           # API port
  reload: false        # Auto-reload on code changes (dev only)
  log_level: "info"    # debug, info, warning, error
  cors_origins: ["*"]  # CORS allowed origins
```

**Environment Variables**:
```bash
export PYPLECS_API_HOST="0.0.0.0"
export PYPLECS_API_PORT="8080"
export PYPLECS_API_LOG_LEVEL="debug"

pyplecs-api
```

---

## Support

- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **GitHub Issues**: https://github.com/tinix84/pyplecs/issues
- **Email**: tinix84@gmail.com

---

**Ready to integrate PyPLECS into your workflow!** 🚀
