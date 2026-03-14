# The Wake-Up Call: When Your Code Becomes Your Enemy

**Substack Article** (2,847 words)
**Theme**: The realization moment + technical analysis
**Format**: Narrative → Technical Deep-Dive

---

> "The code worked perfectly. Then I tried to maintain it."

Six months after shipping PyPLECS—a Python automation framework for power electronics simulations—I opened the codebase to add what I thought would be a simple feature.

The request was straightforward: add support for batch parameter sweeps. Run the same PLECS simulation with different input voltages. Easy, right?

**Three days later**, I was still trying to understand code I'd written myself.

This is the story of how 4,081 lines of "working" code became my biggest enemy, and what happened when I finally had the courage to delete 1,581 of them.

---

## The Feature That Broke Me

*If you've read this on LinkedIn, the technical details start here.*

The request came from a user running power converter design iterations. They wanted to sweep input voltage from 12V to 48V in 6V increments to find optimal efficiency points.

Reasonable request. Standard use case. Should take 30 minutes to implement.

I opened `pyplecs/pyplecs.py` and immediately hit a wall.

### The Architecture I'd Built

Here's what existed:

**Layer 1: Model Wrapper Class** (68 lines)
```python
class GenericConverterPlecsMdl:
    """Wrapper for PLECS model files with metadata."""

    def __init__(self, src_path, variant_name=None):
        self.src_path = Path(src_path)
        self.variant_name = variant_name
        self.folder = self._determine_folder()
        self.model_name = self._extract_model_name()
        self.simulation_name = self._generate_sim_name()
        # ... more initialization ...

    def _determine_folder(self):
        # Complex logic to determine output folder
        # Handles variant names, creates subdirectories
        # ... 20 lines ...

    def _extract_model_name(self):
        # Parse XML to extract model metadata
        # ... 15 lines ...

    # ... more methods ...
```

**Layer 2: Variant Generation** (48 lines)
```python
def generate_variant_plecs_mdl(src_mdl, variant_name, variant_vars):
    """Generate a variant model file with modified parameters."""

    # Step 1: Read source file
    with open(src_mdl.src_path, 'r') as f:
        content = f.read()

    # Step 2: Parse XML structure
    # (Complex regex patterns to find ModelVars section)
    modelvars_pattern = r'<ModelVars>(.*?)</ModelVars>'
    match = re.search(modelvars_pattern, content, re.DOTALL)

    # Step 3: Modify parameters
    for var_name, var_value in variant_vars.items():
        # More regex to replace values
        var_pattern = f'<Variable Name="{var_name}".*?</Variable>'
        # ... manipulation logic ...

    # Step 4: Create output directory
    variant_folder = Path(f"data/{variant_name:02d}")
    variant_folder.mkdir(parents=True, exist_ok=True)

    # Step 5: Write new file
    output_path = variant_folder / f"{src_mdl.model_name}{variant_name}.plecs"
    with open(output_path, 'w') as f:
        f.write(modified_content)

    # Step 6: Return new model object
    return GenericConverterPlecsMdl(output_path, variant_name)
```

**Layer 3: Custom Thread Pool Orchestration** (310 lines in orchestrator)
```python
class SimulationOrchestrator:
    def __init__(self):
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self.task_queue = PriorityQueue()
        self.results = {}
        self.worker_threads = []
        # ... extensive initialization ...

    def submit_simulation(self, model, parameters):
        # Custom queuing logic
        # Thread pool management
        # Result collection
        # ... 100+ lines ...
```

### What I'd Have to Do

To add batch parameter sweeps, I needed to:

1. **Understand** the variant generation system (why are we creating physical files?)
2. **Figure out** the thread pool logic (why custom threads instead of multiprocessing?)
3. **Modify** the orchestrator to handle batches
4. **Update** file naming to avoid collisions
5. **Implement** cleanup of generated files (they were piling up)
6. **Handle** race conditions in file I/O

For what should have been this:
```python
results = simulate([{"Vi": 12}, {"Vi": 18}, {"Vi": 24}, ...])
```

---

## The "Aha!" Moment (Reading the Manual)

Frustrated, I took a step back. Instead of diving deeper into my code, I did something I should have done **six months earlier**:

**I read the PLECS documentation. Thoroughly.**

Buried on page 47 of the XML-RPC API reference, I found this:

> **Batch Simulation Mode**
>
> The PLECS server supports batch execution of simulations with different parameter sets. Pass an array of `ModelVars` dictionaries to `plecs.simulate()` for parallel execution.
>
> ```matlab
> % MATLAB example
> params = {struct('Vi', 12), struct('Vi', 24), struct('Vi', 48)};
> results = plecs.simulate(params);  % Runs in parallel
> ```

I stared at this for a full minute.

**PLECS could already do this.**

Not just "could do it"—it could do it **better**:
- ✅ Native parallelization across CPU cores
- ✅ Optimized at the C++ level (PLECS is written in C++)
- ✅ No file I/O overhead
- ✅ Automatic load balancing
- ✅ Memory-efficient (in-memory parameter passing)

My "clever" solution:
- ❌ Generated physical files (slow disk I/O)
- ❌ Custom Python threading (GIL limitations)
- ❌ Manual orchestration (complex, error-prone)
- ❌ File cleanup required (maintenance burden)
- ❌ Slower than native API

---

## The Benchmark That Sealed It

I had to know: **How much slower was my approach?**

### Test Setup
- **Model**: Buck converter (simple_buck.plecs)
- **Parameters**: 16 different input voltages
- **Machine**: 4-core Intel i7
- **Each simulation**: ~10 seconds

### Results

```
Approach 1: Sequential (original)
for Vi in [12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72, 78, 84, 90, 96, 102]:
    result = server.simulate({"Vi": Vi})
Time: 160 seconds (16 × 10s)
Speedup: 1x (baseline)

Approach 2: My custom thread pool
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(simulate_one, Vi) for Vi in voltages]
Time: 80 seconds
Speedup: 2x
Issues: GIL contention, file I/O bottleneck

Approach 3: PLECS native batch API
results = server.simulate_batch([{"Vi": v} for v in voltages])
Time: ~40 seconds
Speedup: 4x
Issues: None. It just works.
```

**I'd built complexity that made things 2x slower than the native solution.**

---

## The Technical Analysis: Why Did This Happen?

Looking back, I can identify exactly where I went wrong:

### Mistake 1: Solving the Wrong Problem

I saw: "Need to run simulations with different parameters"

I thought: "Need to create different model files for each parameter set"

**Wrong assumption.** PLECS ModelVars are **runtime parameters**, not compile-time constants. You don't need separate files—just pass different values.

### Mistake 2: Not Reading Documentation Thoroughly

I skimmed the XML-RPC docs for "simulate" function:
```python
result = plecs.simulate(model_file, modelvars)
```

I missed that `modelvars` could be:
- A dict: `{"Vi": 12}` (single simulation)
- **A list of dicts**: `[{"Vi": 12}, {"Vi": 24}, ...]` (batch)

That one parameter type overload would have saved me weeks.

### Mistake 3: Premature Optimization

I thought: "File generation will be cleaner for debugging"

Reality: The files cluttered the workspace, required cleanup, and were **never used for debugging**. Not once.

### Mistake 4: Not Benchmarking Early

I assumed my thread pool was faster without measuring.

**Always benchmark before optimizing.** And always benchmark **against doing nothing** (using the native API).

---

## The Refactoring: Deletion as Creation

Armed with benchmarks and a better understanding of PLECS, I made a terrifying decision:

**Delete 1,581 lines of code.**

### What I Removed

**1. GenericConverterPlecsMdl class** (68 lines)
```python
# DELETE
class GenericConverterPlecsMdl:
    # ... 68 lines of wrapper logic ...

# REPLACE WITH
from pathlib import Path
model_path = Path("simple_buck.plecs")  # That's it.
```

**2. Variant generation functions** (48 lines + supporting code)
```python
# DELETE
def generate_variant_plecs_mdl(src_mdl, variant_name, variant_vars):
    # ... 48 lines of XML manipulation, file I/O ...

# REPLACE WITH
# Nothing. Pass parameters directly to PLECS.
```

**3. Custom thread pool** (310 lines in orchestrator)
```python
# DELETE
class SimulationOrchestrator:
    def __init__(self):
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        # ... 310 lines of custom parallelization ...

# SIMPLIFY
class SimulationOrchestrator:
    def submit_batch(self, model_file, params_list):
        # Let PLECS handle parallelization
        return self.plecs_server.simulate_batch(params_list)
```

### What I Kept (and Enhanced)

The **value-add** layers:
- ✅ **Caching system**: Hash-based deduplication (100-1000x speedup on repeated sims)
- ✅ **Priority queue**: CRITICAL/HIGH/NORMAL/LOW task scheduling
- ✅ **Retry logic**: Automatic retry on transient failures
- ✅ **REST API**: Language-agnostic simulation submission
- ✅ **Web GUI**: Real-time monitoring

These provided genuine value. The file generation didn't.

---

## The New Architecture

### Before (v0.x): Fighting Against PLECS

```
User Request
    ↓
GenericConverterPlecsMdl (parse model)
    ↓
generate_variant_plecs_mdl (create physical file)
    ↓
PlecsServer (complex wrapper, 310 lines)
    ↓
Custom thread pool (Python parallelization)
    ↓
PLECS XML-RPC (sequential simulations)

Complexity: HIGH
Performance: 2x baseline
LOC: 4,081
```

### After (v1.0.0): Working WITH PLECS

```
User Request
    ↓
PlecsServer (thin wrapper, ~150 lines)
    ↓
simulate_batch() (group parameters)
    ↓
PLECS Native Batch API (parallel execution)

Complexity: LOW
Performance: 4-5x baseline
LOC: 2,500 (39% reduction)
```

---

## The Results

**Code Metrics:**
- 39% reduction (4,081 → 2,500 LOC)
- 51% reduction in core module (310 → 150 lines)
- 100% removal of variant generation subsystem

**Performance:**
- 4.01x measured speedup (batch simulations)
- 5.7x with caching (30% hit rate)
- 100-1000x on cache hits

**Maintainability:**
- Simplified architecture diagram
- Reduced cognitive load
- Easier onboarding for contributors
- **I can understand my own code again**

---

## Lessons Learned (The Hard Way)

### 1. Read the F***ing Manual

Not just skim—**read thoroughly**. Especially for domain-specific tools like PLECS, MATLAB, CAD software.

The tool you're using probably already does what you're trying to build.

### 2. Benchmark Before Building

Don't assume your custom solution will be faster. **Measure first.**

Steps:
1. Profile the current approach
2. Benchmark the native API
3. Only build custom logic if native approach is provably inadequate

### 3. Complexity Creeps Slowly

You don't write 4,000 lines of bad code in one day. You write:
- 50 lines to solve a problem
- 100 lines to handle an edge case
- 200 lines because you didn't RTFM
- 500 lines to maintain the previous 350 lines

Six months later: unmaintainable mess.

**Solution**: Regular architecture reviews. Every quarter, ask: "What can we delete?"

### 4. The Best Code Is No Code

Before adding abstraction, ask:
- Does the tool already do this?
- Am I solving a real problem or an imagined one?
- Will this make the codebase simpler or more complex?

If you can solve it by **deleting code**, that's usually the right answer.

### 5. Test Deletion Early

I was terrified to delete 1,581 lines. What if it breaks everything?

But I had comprehensive tests. After deletion:
- **All tests still passed** ✅
- Performance improved 4x
- Codebase became maintainable

**Tests give you courage to refactor boldly.**

---

## What About You?

Have you ever returned to your own code and thought, "Who wrote this mess?" (Spoiler: it was you)

Common patterns I see:
- Over-engineered "future-proofing" that never gets used
- Custom implementations of stdlib functionality
- Abstractions that make simple things complex
- Solutions searching for problems

**The wake-up call varies**, but the lesson is the same: **simplicity beats cleverness.**

---

## Coming Up in This Series

This is **Article 1 of 10** in my PyPLECS refactoring journey:

**Next**: "The False Economy of Abstraction" - Why my GenericConverterPlecsMdl class was a textbook example of over-engineering

**Later in series**:
- The 5x Performance Gift Hiding in Plain Sight
- Caching: The Feature That Makes Everything Else Possible
- The Refactoring That Deleted 1,581 Lines
- How AI Changed How I Code (meta lesson)

Subscribe to follow the journey from 4,081 lines of complexity to 2,500 lines of clarity.

---

## Code Samples

All code from this refactoring is open source:
- **GitHub**: [PyPLECS v1.0.0](https://github.com/tinix84/pyplecs)
- **Migration Guide**: Complete before/after examples
- **Benchmarks**: Reproducible performance tests

---

**If you enjoyed this**, share it with someone fighting their own codebase. We've all been there.

**Comments enabled below** - what's your "wake-up call" moment?

---

**Meta**: 2,847 words | ~14-minute read | Technical depth: Medium-High
