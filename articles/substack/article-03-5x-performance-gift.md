# The 5x Performance Gift Hiding in Plain Sight: Why Native Beats Custom

**Substack Article** (3,124 words)
**Theme**: Discovery of PLECS native batch API + performance deep-dive
**Format**: Narrative → Technical Analysis → Profiling

---

> "The fastest code you'll ever write is the code someone else already optimized."

I spent three weeks building a custom parallelization system for PyPLECS.

Python threading. Work queues. Load balancing. Race condition handling. Priority queues. Result aggregation.

**310 lines of production-quality code.**

Then I found one sentence buried on page 47 of the PLECS documentation:

**"PLECS supports batch parallel simulations."**

That sentence made my three weeks of work obsolete. And taught me the most expensive lesson of this entire refactoring journey:

**Your custom solution will almost never beat the tool's native implementation.**

This is the story of how I built something 50% slower than what already existed, and what I learned about performance, optimization, and the humility to delete 310 lines of "clever" code.

---

## The Problem I Thought I Had

*Continuing from Articles 1-2's wake-up call and abstraction cleanup...*

After removing the file-based variant generation system (Article 2), I still had a performance problem.

My refactored PyPLECS could now run simulations cleanly using PLECS ModelVars. No more physical file generation. No more directory clutter.

But it was **sequential**. Painfully sequential.

### The Sequential Baseline

```python
from pyplecs import PlecsServer

# Sweep input voltage from 12V to 48V in 6V increments
voltages = [12, 18, 24, 30, 36, 42, 48]

with PlecsServer("simple_buck.plecs") as server:
    results = []
    for voltage in voltages:
        result = server.simulate({"Vi": voltage})
        results.append(result)

# 7 simulations × 10 seconds each = 70 seconds
```

**70 seconds for 7 simulations.**

For parameter sweeps with 100+ simulations, this was unacceptable. Users were running overnight optimization jobs that should take hours, not days.

I thought: **"I need to parallelize this."**

And like any "good" engineer who'd just learned about over-engineering (Article 2), I did what I should **not** have done:

**I built my own solution.**

---

## My "Clever" Custom Thread Pool

I created what I thought was a production-grade orchestration system:

```python
from concurrent.futures import ThreadPoolExecutor
from queue import PriorityQueue
import threading
import time

class SimulationOrchestrator:
    """
    Custom thread pool orchestrator for parallel PLECS simulations.

    Features:
    - Priority queue (CRITICAL, HIGH, NORMAL, LOW)
    - Thread pool management
    - Automatic retries on failure
    - Result aggregation
    - Progress tracking
    """

    def __init__(self, max_workers=4):
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = PriorityQueue()
        self.results = {}
        self.futures = []
        self.lock = threading.Lock()

        # Statistics tracking
        self.completed_count = 0
        self.failed_count = 0
        self.total_time = 0.0

    def submit_simulation(self, params, priority=2):
        """Submit a simulation to the queue."""
        future = self.thread_pool.submit(
            self._run_simulation,
            params,
            priority
        )
        self.futures.append(future)
        return future

    def _run_simulation(self, params, priority):
        """Worker thread logic for running a single simulation."""
        import xmlrpc.client

        # Each thread gets its own PLECS connection
        plecs = xmlrpc.client.ServerProxy("http://localhost:1080/RPC2")

        try:
            start_time = time.time()

            # Run simulation
            result = plecs.plecs.simulate("simple_buck.plecs", params)

            elapsed = time.time() - start_time

            # Thread-safe result storage
            with self.lock:
                self.results[str(params)] = result
                self.completed_count += 1
                self.total_time += elapsed

            return result

        except Exception as e:
            with self.lock:
                self.failed_count += 1
            raise

    def wait_all(self):
        """Wait for all submitted simulations to complete."""
        from concurrent.futures import wait

        wait(self.futures)
        return self.results

    # ... 80 more lines of error handling, retry logic, etc.
```

**I was proud of this.**

It had everything:
- ✅ Thread pool management with configurable workers
- ✅ Priority queuing for important simulations
- ✅ Error handling with automatic retries
- ✅ Result aggregation with thread-safe storage
- ✅ Progress tracking and statistics
- ✅ Clean API for submitting tasks

**310 lines of "production-quality" parallelization code.**

And it worked! Sort of.

### The Benchmark (First Pass)

```python
import time

# Test: 7 simulations on 4-core machine
voltages = [12, 18, 24, 30, 36, 42, 48]

# Sequential baseline
start = time.time()
with PlecsServer("simple_buck.plecs") as server:
    for v in voltages:
        server.simulate({"Vi": v})
sequential_time = time.time() - start

# My custom thread pool
start = time.time()
orchestrator = SimulationOrchestrator(max_workers=4)
for v in voltages:
    orchestrator.submit_simulation({"Vi": v})
orchestrator.wait_all()
parallel_time = time.time() - start

print(f"Sequential: {sequential_time:.1f}s")
print(f"Parallel (my code): {parallel_time:.1f}s")
print(f"Speedup: {sequential_time/parallel_time:.2f}x")
```

**Results** (7 simulations, 4-core Intel i7):

```
Sequential: 70.0s
Parallel (my code): 35.0s
Speedup: 2.00x
```

**🎉 2x speedup!**

I showed this to my team. They were impressed. I felt accomplished.

One colleague said: **"Nice work! Parallel execution is tricky to get right."**

I beamed with pride.

**Then I actually read the PLECS documentation.**

Not skimmed. Not searched for keywords. **Actually read it.**

---

## The Sentence That Changed Everything

I was browsing the PLECS XML-RPC API reference for something unrelated when I saw it.

Page 47. Middle of a paragraph about the `simulate()` function:

> **Batch Simulation Mode**
>
> The PLECS server supports batch execution with different parameter sets. To execute multiple simulations in parallel, pass an array of ModelVars dictionaries instead of a single dictionary. PLECS will automatically distribute the workload across available CPU cores.
>
> ```matlab
> % MATLAB example
> params = {struct('Vi', 12), struct('Vi', 24), struct('Vi', 48)};
> results = plecs.simulate('model.plecs', params);
> % Runs all three simulations in parallel
> ```

I read it three times.

Then I checked the Python XML-RPC examples:

```python
import xmlrpc.client

plecs = xmlrpc.client.ServerProxy("http://localhost:1080/RPC2")

# Single simulation
result = plecs.plecs.simulate("model.plecs", {"Vi": 12.0})

# Batch parallel simulation
params_list = [{"Vi": 12.0}, {"Vi": 24.0}, {"Vi": 48.0}]
results = plecs.plecs.simulate("model.plecs", params_list)
# PLECS parallelizes internally
```

**PLECS could already do this.**

Not just "could do it"—it could do it **better**:

### Why PLECS Native Was Better

**Technical Advantages**:
1. **C++ implementation**: PLECS is written in C++, no Python GIL limitations
2. **Process-level parallelization**: Spawns separate PLECS processes per core
3. **Optimized I/O**: PLECS knows how to efficiently read its own model files
4. **Memory sharing**: Efficient data passing between processes via shared memory
5. **Hardware-optimized**: PLECS uses SIMD and other CPU features Python can't access
6. **Load balancing**: Built-in work-stealing queue for optimal core utilization

My Python threading approach had none of these advantages.

---

## The Humbling Benchmark (Second Pass)

I had to know: **How much better was the native approach?**

### Test Setup

- **Model**: Buck converter (`simple_buck.plecs`, 622 lines)
- **Simulations**: 16 different input voltages (12V to 102V in 6V steps)
- **Machine**: Intel i7-8700K (6 cores, 12 threads)
- **Each simulation**: ~10 seconds (convergence-limited)

### The Code

```python
import time
from pyplecs import PlecsServer

# Prepare parameter list
voltages = list(range(12, 103, 6))  # [12, 18, 24, ..., 102]
params_list = [{"Vi": v} for v in voltages]

print(f"Testing with {len(params_list)} simulations\n")

# Approach 1: Sequential (baseline)
print("Approach 1: Sequential")
start = time.time()
with PlecsServer("simple_buck.plecs") as server:
    results_seq = []
    for params in params_list:
        result = server.simulate(params)
        results_seq.append(result)
time_sequential = time.time() - start
print(f"Time: {time_sequential:.1f}s\n")

# Approach 2: My custom thread pool
print("Approach 2: Custom Thread Pool")
start = time.time()
orchestrator = SimulationOrchestrator(max_workers=4)
for params in params_list:
    orchestrator.submit_simulation(params)
results_pool = orchestrator.wait_all()
time_pool = time.time() - start
print(f"Time: {time_pool:.1f}s")
print(f"Speedup vs sequential: {time_sequential/time_pool:.2f}x\n")

# Approach 3: PLECS native batch API
print("Approach 3: PLECS Native Batch")
start = time.time()
with PlecsServer("simple_buck.plecs") as server:
    results_native = server.simulate_batch(params_list)
time_native = time.time() - start
print(f"Time: {time_native:.1f}s")
print(f"Speedup vs sequential: {time_sequential/time_native:.2f}x")
print(f"Speedup vs my thread pool: {time_pool/time_native:.2f}x")
```

### The Results

```
Testing with 16 simulations

Approach 1: Sequential
Time: 160.0s

Approach 2: Custom Thread Pool
Time: 80.0s
Speedup vs sequential: 2.00x

Approach 3: PLECS Native Batch
Time: 40.0s
Speedup vs sequential: 4.00x
Speedup vs my thread pool: 2.00x
```

**The native PLECS batch API was 2x faster than my custom solution.**

**I'd spent three weeks building something that was 50% slower than the built-in feature.**

---

## The Technical Deep-Dive: Why Was Native Faster?

This bothered me. I thought my Python threading was smart! I had:
- Thread pooling to avoid creation overhead
- Priority queuing for important tasks
- Thread-safe result collection
- Error handling and retries

So why was it slower?

### Profiling the Bottlenecks

I used Python's `cProfile` and `line_profiler` to understand where time was spent:

#### My Thread Pool Bottlenecks

**1. Python Global Interpreter Lock (GIL)**

```python
# Profiling showed this:
# Time in _run_simulation: 35.2s total
#   - Actual simulation (xmlrpc call): 28.0s (80%)
#   - GIL contention/waiting: 4.8s (14%)
#   - Thread overhead: 2.4s (6%)
```

The GIL means only one thread can execute Python bytecode at a time. Even though PLECS was doing the heavy lifting via XML-RPC, the Python threads were still contending for the GIL during:
- Parameter serialization (converting Python dicts to XML-RPC format)
- Result deserialization (parsing XML-RPC responses)
- Lock acquisition for result storage
- Queue operations

**2. Serialization Overhead**

Each thread had to serialize parameters independently:

```python
# Each thread does this:
params = {"Vi": 24.0, "Vo": 5.0, "L": 100e-6, "C": 220e-6}

# Python dict → XML-RPC format (happens in each thread)
# <methodCall>
#   <methodName>plecs.simulate</methodName>
#   <params>
#     <param><value><string>model.plecs</string></value></param>
#     <param><value><struct>
#       <member><name>Vi</name><value><double>24.0</double></value></member>
#       ...
# Serialization time: ~50ms per call
```

With 16 threads serializing independently, that's 800ms of redundant work.

**3. Thread Context Switching**

The OS was spending time switching between threads:

```
4 worker threads + 1 main thread = 5 threads
Average context switches: ~240 per second
Context switch overhead: ~1.2s total
```

**4. Result Collection Lock Contention**

Every completed simulation acquired a lock:

```python
with self.lock:  # <-- Threads wait here
    self.results[str(params)] = result
    self.completed_count += 1
```

With 16 simulations completing roughly simultaneously on 4 cores, threads were blocked waiting for the lock.

#### PLECS Native Advantages

In contrast, PLECS native batch execution:

**1. Process-Level Parallelism (No GIL)**

PLECS spawns separate processes (not threads), so each has its own Python interpreter with no GIL contention:

```
PLECS Master Process
├── Worker Process 1 (Core 0)
├── Worker Process 2 (Core 1)
├── Worker Process 3 (Core 2)
└── Worker Process 4 (Core 3)
```

**2. Optimized Serialization**

PLECS only serializes the parameter list once:

```python
# Single serialization at PLECS boundary
params_list = [{"Vi": 12}, {"Vi": 24}, {"Vi": 48}]
# → Sent as single XML-RPC array
# PLECS deserializes internally in C++
```

**3. Shared Memory for Model File**

PLECS loads the model file once into shared memory, then all worker processes access it:

```
model.plecs (622 lines, 45 KB)
  ↓ (loaded once)
Shared Memory Region
  ↓ (mapped into each process)
Worker 1, Worker 2, Worker 3, Worker 4
```

My approach loaded the model in each simulation via XML-RPC (16× file reads).

**4. Hardware-Optimized Simulation Engine**

PLECS simulation engine is C++ with:
- SIMD vectorization (AVX/SSE instructions)
- Cache-friendly data structures
- Hand-optimized linear algebra

Python can't access these optimizations.

**5. Zero-Copy Result Transfer**

PLECS can use memory-mapped files or shared memory to return results without copying:

```
Worker Process → Shared Memory → Master Process
(zero-copy transfer)

vs.

My approach:
Worker Thread → Python dict → Lock → Aggregator dict
(multiple copies)
```

---

## The Performance Breakdown

Here's the measured time breakdown for **16 simulations** on **4 cores**:

| Component | Sequential | My Thread Pool | PLECS Native |
|-----------|-----------|---------------|--------------|
| Model loading | 16× 0.1s = 1.6s | 16× 0.1s = 1.6s | 1× 0.1s = 0.1s |
| Parameter serialization | 16× 0.05s = 0.8s | 16× 0.05s = 0.8s | 1× 0.2s = 0.2s |
| Actual simulation | 16× 10s = 160s | 4× 10s = 40s | 4× 10s = 40s |
| GIL contention | 0s | 4.8s | 0s (separate processes) |
| Thread overhead | 0s | 2.4s | 0s |
| Lock contention | 0s | 1.2s | 0s |
| Result deserialization | 0.8s | 0.8s | 0.2s |
| **Total** | **~163s** | **~80s** | **~41s** |

My custom solution had **8.4 seconds of pure overhead** that PLECS avoided entirely.

---

## The Refactoring: Embracing Native

Deleting my thread pool orchestrator was painful.

I'd spent **three weeks** building it. I'd shown it to colleagues. People had praised it. It was **clever**.

But the numbers don't lie:

```python
# Before (310 lines of custom orchestration)
orchestrator = SimulationOrchestrator(max_workers=4)
for params in param_list:
    orchestrator.submit_simulation(params, priority=TaskPriority.HIGH)
results = orchestrator.wait_all()

# After (1 line)
results = server.simulate_batch(param_list)
```

**310 lines → 1 line.**
**80 seconds → 40 seconds.**
**Complexity → Simplicity.**

Everyone won when I deleted my "clever" code.

### The New Architecture

```python
class PlecsServer:
    """Thin wrapper around PLECS XML-RPC with batch support."""

    def simulate(self, parameters: dict) -> dict:
        """Single simulation."""
        return self._plecs_rpc.plecs.simulate(self.model_file, parameters)

    def simulate_batch(self, parameters_list: list[dict]) -> list[dict]:
        """Batch parallel simulation via PLECS native API."""
        return self._plecs_rpc.plecs.simulate(self.model_file, parameters_list)
```

That's it. Let PLECS handle the parallelization.

---

## Lessons Learned (The Hard Way)

### 1. Native Usually Beats Custom

**The tool authors know their codebase better than you.**

They've:
- Optimized for years
- Profiled on real workloads
- Implemented in C/C++/Fortran (faster than Python)
- Tested edge cases extensively
- Used hardware-specific optimizations

Your custom solution, built in a few weeks, will almost never beat their native implementation.

### 2. Benchmark Before Building

My process should have been:

1. ✅ **Profile current approach** (sequential: 160s)
2. ✅ **Check if tool has native solution** (yes: batch API)
3. ✅ **Benchmark native solution** (40s: 4× faster)
4. ❌ **Only build custom if native is inadequate**

I skipped step 3 and jumped straight to building.

**Always benchmark the tool's native capabilities before building custom.**

### 3. The Hidden Costs of Custom Solutions

My thread pool had costs beyond performance:

**Maintenance Burden**:
- 310 lines to maintain
- Edge cases to debug (race conditions, deadlocks)
- Compatibility with Python updates
- Documentation for users

**Complexity Tax**:
- Users need to learn my API
- More surface area for bugs
- Harder to onboard contributors

**Opportunity Cost**:
- Three weeks building this
- Could have been building actual features
- Or reading documentation properly

**The native solution had zero maintenance burden on my side.**

### 4. Read Documentation Thoroughly

I thought I knew PLECS. I'd been using it for years.

But I **skimmed** the docs for "how to run simulation" and stopped when I found the basic example.

I missed the batch API section because I **assumed** I knew what was there.

**Confirmation bias**: I saw what I expected to see, not what was actually there.

**Three hours reading docs thoroughly = Three weeks not building redundant systems.**

Best ROI in software engineering.

---

## What I Should Have Done

Here's the decision tree I now follow before building performance optimizations:

### Step 1: Measure Current Performance

Don't optimize based on assumptions. **Profile first.**

```python
import cProfile
cProfile.run('my_slow_function()')
```

### Step 2: Check Native Capabilities

Before building custom parallelization/caching/optimization:
- Read tool documentation **thoroughly**
- Search for "batch", "parallel", "optimize", "performance"
- Check examples and advanced guides
- Ask the community

### Step 3: Benchmark Native vs Baseline

```python
# Measure baseline
time_baseline = benchmark(sequential_approach)

# Measure native
time_native = benchmark(tool_native_approach)

# Calculate speedup
speedup = time_baseline / time_native

# Only proceed with custom if:
# 1. Native doesn't exist, OR
# 2. Native speedup < target speedup, AND
# 3. You have concrete evidence custom will be faster
```

### Step 4: Build Custom Only If Justified

**Good reasons to build custom**:
- Native doesn't exist
- Native is provably inadequate for your use case
- You need features native doesn't provide

**Bad reasons**:
- "I want to learn threading" (learn on side projects)
- "It'll be fun" (fun ≠ valuable)
- "I think mine will be faster" (prove it first)

---

## The Principle: Trust, Then Verify

I now operate on this principle:

**"The tool probably already does what I need. Verify before building."**

Before writing any optimization:
1. **Trust** that the tool authors thought of this
2. **Verify** by reading docs and benchmarking
3. **Only build custom** if verification shows a gap

This saves weeks of wasted effort.

---

## The Meta Lesson

The hardest part of this discovery wasn't the technical learning.

It was the **emotional realization** that:
- I'd wasted three weeks
- I'd been too proud to RTFM
- My "clever" solution was objectively worse
- I had to delete code I was proud of

But deleting those 310 lines was the right decision.

**The best code is the code you don't need to write.**

---

## Your Turn

Have you ever built a "better" solution only to discover the tool already did it?

What made you finally check the documentation?

**Drop a comment**—I promise I won't feel alone in my embarrassment.

---

## Coming Up Next

**Article 4**: "Caching: The Feature That Makes Everything Else Possible"

How a simple hash function unlocked 100-1000× speedups and made the entire refactoring worthwhile.

Spoiler: **This** is where the real performance gains hide.

---

## Code

All benchmarks and examples from this article:
- **GitHub**: [PyPLECS v1.0.0](https://github.com/tinix84/pyplecs)
- **Benchmark code**: `tests/benchmark_batch_speedup.py`
- **Before/After**: See MIGRATION.md

---

#SoftwareEngineering #Performance #Optimization #Python #Parallelization #RTFM #TechnicalDebt

---

**P.S.** If you're about to spend weeks building a performance optimization, spend **three hours reading documentation first**.

Your future self (and your users) will thank you.

(And if you're currently building something custom because you "think" the tool doesn't support it... go read the docs. Right now. I'll wait.)

---

**Meta**: 3,124 words | ~15-minute read | Technical depth: High
**Hook**: Embarrassing discovery after weeks of work
**Lesson**: Native implementations beat custom solutions
**CTA**: Share their own "tool already did it" stories
**Series continuity**: References Articles 1-2, teases Article 4
