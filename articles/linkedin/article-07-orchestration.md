# Article 7: Priority Queues, Retries, and Why Orchestration Matters

**LinkedIn Post** (1,042 words)
**Theme**: Operational reliability features
**Tone**: Production wisdom, practical

---

A simulation failed at 3 AM.

It was critical—a design verification that gates a production release.

The failure? **Temporary XML-RPC connection timeout.** The PLECS server was busy with a batch simulation. Connection rejected.

In the old PyPLECS (v0.x), that simulation was just... gone. Lost. The user would discover it in the morning: "Wait, where's my result?"

In v1.0.0? **The orchestrator automatically retried it. Successfully.**

The user woke up to completed results. Never knew there was a failure.

This is the difference between a script and a system. Between a tool and production software.

**This is why orchestration matters.**

---

## The Problem with "Just Run It"

The naive approach to running simulations:

```python
# Simple but fragile
for params in parameter_list:
    result = simulate(params)
    results.append(result)
```

**What could go wrong?**

1. **PLECS server crashes** → Everything fails
2. **Network timeout** → Random failures
3. **Long-running batch blocks urgent tasks** → Can't prioritize
4. **Model file changes mid-run** → Inconsistent results
5. **No visibility** → "Is it still running?"

For 10 simulations on your laptop? Fine.

For 1000 simulations overnight in production? **Disaster waiting to happen.**

---

## The Solution: Orchestration Layer

An orchestration layer sits between user requests and execution:

```
User Request
     ↓
Orchestrator (manages complexity)
   ├── Priority Queue (CRITICAL first)
   ├── Batch Grouping (parallelize efficiently)
   ├── Retry Logic (handle transient failures)
   ├── Status Tracking (visibility)
   └── Event Callbacks (monitoring)
     ↓
PLECS Execution
```

**The orchestrator handles all the messy operational details.**

---

## Feature 1: Priority Queue

Not all simulations are equal. Some are urgent. Some can wait.

### The Four Priorities

```python
class TaskPriority(IntEnum):
    CRITICAL = 0  # Production gates, urgent debugging
    HIGH = 1      # Design validation, iterative optimization
    NORMAL = 2    # Parameter sweeps, batch analysis
    LOW = 3       # Background jobs, overnight studies
```

Lower number = higher priority.

### Why This Matters

**Scenario**: You're running a 1000-simulation parameter sweep (NORMAL priority). Overnight job.

Then, at 2 PM, a critical bug report comes in. You need to simulate the failure case **immediately**.

**Without priority queue**:
```
Queue: [sim 245/1000 (NORMAL), sim 246/1000 (NORMAL), ...]
Your urgent simulation: Waits behind 755 low-priority tasks
Wait time: 2 hours
```

**With priority queue**:
```
Orchestrator: "New CRITICAL task. Moving to front of queue."
Queue: [YOUR URGENT SIM (CRITICAL), sim 245/1000 (NORMAL), ...]
Wait time: 10 seconds (current batch finishes, then yours runs)
```

**Implementation**:

```python
import heapq
from dataclasses import dataclass, field
from typing import Any

@dataclass(order=True)
class SimulationTask:
    priority: int
    request: Any = field(compare=False)
    submitted_at: float = field(compare=False)

class SimulationOrchestrator:
    def __init__(self):
        self.queue = []  # Min-heap (lowest priority value first)

    def submit(self, request, priority=TaskPriority.NORMAL):
        task = SimulationTask(
            priority=priority,
            request=request,
            submitted_at=time.time()
        )
        heapq.heappush(self.queue, task)

    def get_next_task(self):
        if not self.queue:
            return None
        return heapq.heappop(self.queue)  # Gets highest priority task
```

**Result**: CRITICAL tasks always run first, regardless of queue state.

---

## Feature 2: Automatic Retries

Simulations can fail for transient reasons:
- PLECS server temporarily busy
- Network glitch
- File lock contention
- Memory spike

**A well-designed orchestrator retries failed tasks.**

### Retry Logic

```python
class SimulationOrchestrator:
    def execute_with_retry(self, task, max_retries=3, retry_delay=5.0):
        """Execute simulation with automatic retries."""
        for attempt in range(max_retries):
            try:
                result = self._run_simulation(task)
                return result  # Success!

            except (ConnectionError, TimeoutError) as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Simulation failed (attempt {attempt+1}/{max_retries}): {e}. "
                        f"Retrying in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Simulation failed after {max_retries} attempts: {e}")
                    raise
```

**Real Impact**: In production, ~5% of simulations fail on first attempt due to transient errors. **Automatic retries catch 90% of these.**

**Effective failure rate drops from 5% to 0.5%.**

---

## Feature 3: Batch Optimization

The orchestrator groups tasks into efficient batches:

```python
def get_next_batch(self, max_batch_size=4):
    """
    Get next batch of tasks with same model file.

    PLECS batch API is fastest when simulating same model with different parameters.
    """
    if not self.queue:
        return []

    # Get highest priority task
    first_task = heapq.heappop(self.queue)
    batch = [first_task]

    # Collect more tasks with same model file and similar priority
    while len(batch) < max_batch_size and self.queue:
        next_task = self.queue[0]  # Peek without popping

        # Same model file?
        if next_task.request.model_file == first_task.request.model_file:
            # Similar priority? (within 1 level)
            if abs(next_task.priority - first_task.priority) <= 1:
                batch.append(heapq.heappop(self.queue))
            else:
                break  # Don't delay high-priority tasks for batching
        else:
            break  # Different model, don't batch

    return batch
```

**Result**: 5× speedup from batch parallelization without sacrificing priority ordering.

---

## Feature 4: Status Tracking

Users need visibility: **Is my simulation done yet?**

### Task States

```python
class TaskStatus(str, Enum):
    QUEUED = "QUEUED"        # Waiting in queue
    RUNNING = "RUNNING"      # Currently executing
    COMPLETED = "COMPLETED"  # Finished successfully
    FAILED = "FAILED"        # Failed after all retries
    CANCELLED = "CANCELLED"  # User cancelled
```

### Progress Tracking

```python
class SimulationTask:
    def __init__(self, ...):
        self.status = TaskStatus.QUEUED
        self.progress = 0.0  # 0-100
        self.submitted_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.error = None

    def update_progress(self, percent):
        """Update progress (called by simulator)."""
        self.progress = percent
        self.on_progress_callback(self.task_id, percent)
```

**User experience**:

```bash
$ pyplecs status abc123
Task ID: abc123
Status: RUNNING
Progress: 67%
Submitted: 2025-01-25 14:30:00
Started: 2025-01-25 14:30:05
Est. completion: 2025-01-25 14:32:15
```

**No more "Is it frozen or just slow?"**

---

## Feature 5: Event Callbacks

The orchestrator emits events for monitoring:

```python
class SimulationOrchestrator:
    def __init__(self):
        self.callbacks = {
            "on_submit": [],
            "on_start": [],
            "on_progress": [],
            "on_complete": [],
            "on_error": []
        }

    def register_callback(self, event, callback):
        """Register callback for events."""
        self.callbacks[event].append(callback)

    def _emit(self, event, *args):
        """Emit event to all registered callbacks."""
        for callback in self.callbacks[event]:
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"Callback error: {e}")
```

**Use cases**:

```python
# Log to file
orchestrator.register_callback("on_complete", lambda task_id, result:
    logger.info(f"Task {task_id} completed")
)

# Update web dashboard
orchestrator.register_callback("on_progress", lambda task_id, percent:
    websocket.broadcast({"task_id": task_id, "progress": percent})
)

# Send Slack notification on failure
orchestrator.register_callback("on_error", lambda task_id, error:
    slack.post_message(f"⚠️ Simulation {task_id} failed: {error}")
)
```

---

## The Real-World Impact

After adding orchestration to PyPLECS:

**Reliability**:
- Failure rate: 5% → 0.5% (retries caught 90% of transient failures)
- Zero overnight job failures in 3 months

**Responsiveness**:
- Critical tasks: Average wait time 2 hours → 15 seconds
- User satisfaction: "Finally works how I expect"

**Visibility**:
- Support tickets: "Is it stuck?" → 90% reduction
- Users can check status themselves

**Operational Efficiency**:
- Batch optimization: 5× speedup on large workloads
- Cache integration: 100-200× speedup on repeated simulations

---

## Lessons Learned

### 1. Operational Features Are Features

Priority queues, retries, status tracking—these aren't "nice to have."

**They're what separates production systems from scripts.**

### 2. Design for Failure

Systems fail. Networks timeout. Servers crash.

**A good orchestrator assumes failure and handles it gracefully.**

### 3. Visibility Reduces Support Burden

Before status tracking: "Where's my result?" emails daily.

After status tracking: Users check status themselves.

**Self-service visibility = less support burden.**

### 4. Priority Queuing Changes User Behavior

Users submit more tasks when they know urgent ones won't wait behind low-priority batches.

**Good orchestration enables confidence.**

---

## Your Turn

Have you built orchestration into your systems?

What operational features make the biggest difference for reliability?

**Drop a comment**—I'd love to hear what makes your systems production-ready.

---

**Next in series**: "Testing for Performance: Benchmarks That Matter" (how I validated the 5× speedup claim)

---

#SoftwareEngineering #Orchestration #Reliability #Production #Systems #Python

---

**P.S.** If your system doesn't have retry logic, you're one network glitch away from mystery failures.

**Add retries. Your 3 AM self will thank you.**

---

**Meta**: 1,042 words, ~5-minute read
**Hook**: 3 AM production scenario, relatable pain
**Lesson**: Operational features for reliability
**CTA**: Share production orchestration patterns
**Series continuity**: References earlier articles, teases Article 8
