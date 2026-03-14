# Article 3: The 5x Performance Gift Hiding in Plain Sight

**LinkedIn Post** (1,045 words)
**Theme**: Discovery of PLECS native batch API
**Tone**: Revelation, self-deprecating humor

---

I spent three weeks building a custom parallelization system.

Python threading. Work queues. Load balancing. Race condition handling.

Then I found one sentence in the documentation: **"PLECS supports batch parallel simulations."**

That sentence made my three weeks of work obsolete.

And taught me an embarrassing but valuable lesson: **RTFM doesn't mean skim the docs. It means READ them.**

---

## The Problem I Thought I Had

After refactoring out my file-based variant generation, I still had a performance problem.

**Sequential simulation was slow:**

```python
results = []
for voltage in [12, 18, 24, 30, 36, 42, 48]:
    result = server.simulate({"Vi": voltage})
    results.append(result)

# 7 simulations × 10 seconds each = 70 seconds
```

I thought: "I need to parallelize this."

So I did what any "good" engineer would do: **I built my own solution.**

---

## My "Clever" Solution

I created a thread pool system:

```python
from concurrent.futures import ThreadPoolExecutor

class SimulationOrchestrator:
    def __init__(self):
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self.task_queue = PriorityQueue()
        self.results = {}
        # ... 310 lines of orchestration logic ...

    def submit_simulation(self, params):
        future = self.thread_pool.submit(self._run_simulation, params)
        self.futures.append(future)
        return future

    def _run_simulation(self, params):
        # Worker thread logic
        # Queue management
        # Result collection
        # Error handling
        # ... 80 lines ...
```

I was **proud** of this.

It had:
- ✅ Thread pool management
- ✅ Priority queuing
- ✅ Error handling with retries
- ✅ Result aggregation
- ✅ Progress tracking

**310 lines of "production-quality" parallelization.**

And it worked! Sort of.

```
7 simulations, 4 cores
Sequential: 70 seconds
My thread pool: 35 seconds

🎉 2x speedup!
```

I showed it to my team: "Look! Parallelization!"

They were impressed. I felt accomplished.

**Then I actually read the PLECS documentation.**

---

## The Sentence That Changed Everything

I was browsing the PLECS XML-RPC API reference (actually reading it this time, not just searching for keywords).

Page 47, buried in the middle:

> **Batch Simulation Mode**
>
> The PLECS server supports batch execution with different parameter sets. Pass an array to the ModelVars parameter for parallel execution.

I read it three times.

Then I checked the examples.

```matlab
% MATLAB example
params = {struct('Vi', 12), struct('Vi', 24), struct('Vi', 48)};
results = plecs.simulate('model.plecs', params);
% Runs in parallel automatically
```

**PLECS could already do this.**

Not just "could do it." It could do it **better**:
- Native C++ implementation (faster than Python threading)
- Optimized for the specific hardware
- Automatic load balancing
- No GIL limitations (Python Global Interpreter Lock)
- Memory efficient

My entire thread pool system was **redundant**.

---

## The Humbling Benchmark

I had to know: **How much better was the native approach?**

```python
import time

# Approach 1: My thread pool (310 lines)
start = time.time()
orchestrator = SimulationOrchestrator()
for voltage in voltages:
    orchestrator.submit_simulation({"Vi": voltage})
results1 = orchestrator.wait_all()
time1 = time.time() - start

# Approach 2: PLECS native (1 line)
start = time.time()
params_list = [{"Vi": v} for v in voltages]
results2 = server.simulate_batch(params_list)
time2 = time.time() - start

print(f"My approach: {time1:.1f}s")
print(f"Native PLECS: {time2:.1f}s")
print(f"Native is {time1/time2:.1f}x faster")
```

**Results** (16 simulations, 4-core machine):

```
Sequential baseline: 160s
My thread pool: 80s (2x faster)
PLECS native batch: 40s (4x faster)

Native PLECS beat my custom solution by 2x.
```

**I'd spent three weeks building something that was 50% slower than the built-in feature.**

---

## Why Was Native Faster?

This bothered me. I thought my Python threading was smart!

So I profiled both approaches. Here's what I found:

**My Thread Pool Bottlenecks:**
1. **Python GIL** (Global Interpreter Lock): Only one thread executing Python at a time
2. **Serialization overhead**: Passing data between threads
3. **Queue management**: My priority queue added latency
4. **Context switching**: OS overhead switching between threads
5. **Result aggregation**: Collecting results back to main thread

**PLECS Native Advantages:**
1. **C++ implementation**: No GIL, true parallelism
2. **Process-level parallelization**: PLECS spawns separate processes
3. **Optimized I/O**: PLECS knows how to efficiently read its own files
4. **Memory sharing**: Efficient data passing between processes
5. **Hardware-optimized**: PLECS uses CPU features Python can't access

**The native solution was faster at every level.**

---

## The Lesson: Native Usually Beats Custom

Here's the uncomfortable truth I learned:

**Your custom solution will almost never beat the tool's native implementation.**

Why?
- The tool authors know their codebase better than you
- They've optimized for years
- They have C/C++/Fortran (faster than Python)
- They've profiled on real workloads
- They have test suites covering edge cases

**When a tool provides a feature, use it.** Don't rebuild it.

---

## The Refactoring

Deleting my thread pool system hurt my ego.

I'd spent three weeks on it. It worked. People praised it.

But the numbers don't lie:

```python
# Before (310 lines)
orchestrator = SimulationOrchestrator()
for params in param_list:
    orchestrator.submit_simulation(params)
results = orchestrator.wait_all()

# After (1 line)
results = server.simulate_batch(param_list)
```

**310 lines → 1 line.**
**80 seconds → 40 seconds.**

Everyone won when I deleted my "clever" code.

---

## What I Should Have Done

Here's the process I **should have followed**:

### Step 1: Check if the tool already does it
Read documentation **thoroughly**, not just skim.

### Step 2: Benchmark the native approach
Measure performance **before** building custom.

### Step 3: Only build custom if native is inadequate
Have a **concrete reason** why native doesn't work.

### What I actually did:

1. ~~Read docs~~ Skim for keywords
2. ~~Benchmark~~ Assume I need custom solution
3. Build custom solution
4. Discover native feature exists
5. Benchmark (too late)
6. Delete custom solution
7. Feel dumb

**Don't be like me. Do Step 1 properly.**

---

## The Hidden Costs I Ignored

Beyond performance, my custom solution had costs I didn't account for:

**Maintenance:**
- 310 lines to maintain
- Edge cases to handle
- Bug fixes when Python updates
- Documentation for users

**Complexity:**
- Users need to learn my orchestrator API
- Debugging is harder (custom code path)
- More surface area for bugs

**Opportunity cost:**
- Three weeks building this
- Could have been building actual features
- Or reading documentation properly

**The native solution had zero maintenance burden on my side.**

---

## Principles I Now Follow

### 1. Benchmark Native First

Before building custom optimization:
- Profile current approach
- Benchmark tool's native features
- Only proceed if native is provably inadequate

### 2. Trust the Experts

The tool authors **know their tool better than you**.

If they say "use this feature for parallelization," there's usually a good reason.

### 3. Optimization Is About Deletion

The fastest code is the code that doesn't run.

The second fastest is the code someone else maintains (the tool vendor).

### 4. Read Documentation as an Investment

Three hours reading docs thoroughly = Three weeks not building redundant systems.

**Best ROI in software engineering.**

---

## The Embarrassing Part

You know what's really embarrassing?

The PLECS docs had **examples** of batch execution. Clear examples. Multiple examples.

I just never read that section because I **thought I knew what I needed**.

**Confirmation bias**: I saw what I expected to see, not what was actually there.

---

## Your Turn

Have you ever built a "better" solution only to discover the tool already did it?

What made you finally check the documentation?

**Drop a comment**—I promise I won't feel alone in my embarrassment.

---

**Next in series**: "Caching: The Feature That Makes Everything Else Possible" (how 100-1000x speedups hide in hash functions)

---

#SoftwareEngineering #Performance #Optimization #Python #EngineeringLessons #RTFM

---

**P.S.** The next time you're about to spend weeks building a performance optimization, spend three hours reading documentation first.

**Future you will thank past you.**

(And if past you is already current you building something custom... go read the docs. Right now. I'll wait.)

---

**Meta**: 1,045 words, ~5-minute read
**Hook**: Embarrassing discovery, relatable mistake
**Lesson**: Read documentation, trust native implementations
**CTA**: Share their own "tool already did it" moments
