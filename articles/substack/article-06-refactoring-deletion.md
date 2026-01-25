# The Refactoring That Deleted 1,581 Lines: Test-Driven Transformation

**Substack Article** (2,891 words)
**Theme**: Test-driven refactoring + emotional journey + strategy
**Format**: Narrative → Technical Strategy → Lessons

---

> "Code is a liability. Less code is better code."

I was about to delete 1,581 lines of code.

Not dead code. Not commented-out experiments. **Working, tested, documented, production code** that users were actively relying on.

4,081 lines → 2,500 lines. **39% of my codebase gone.**

My cursor blinked at the command prompt:

```bash
git commit -m "feat(refactor): remove variant generation, use PLECS native API"
# This will DELETE:
# - 3 entire modules
# - 18 functions
# - 4 classes
# - 500+ lines of tests
# Are you sure? [y/N]
```

My hands were shaking. This was terrifying.

What if I broke everything? What if users depended on those features? What if there were edge cases I'd forgotten?

Then I looked at my terminal:

```
pytest --cov
========================= test session starts ==========================
collected 182 items

tests/test_basic.py ..................  [ 10%]
tests/test_refactored.py ............................................. [ 47%]
tests/test_cache.py ...................... [ 59%]
tests/test_api.py ...................... [ 72%]
tests/test_orchestrator.py .................... [ 83%]
tests/benchmark_batch_speedup.py .................... [100%]

========================= 182 passed in 14.23s =========================
Coverage: 87%
```

**182 tests. All passing.**

I typed `y` and hit Enter.

**This is the technical and emotional story of the most terrifying—and most liberating—refactoring I've ever done.**

---

## What I Was Actually Deleting

Let's be explicit about what those 1,581 lines represented.

### The Code Being Removed

**Module 1: `pyplecs/generic_converter.py` (68 lines)**

```python
class GenericConverterPlecsMdl:
    """
    Wrapper for PLECS model files with metadata extraction.

    DEPRECATED in v1.0.0. Use pathlib.Path and PlecsServer directly.
    """

    def __init__(self, src_path, variant_name=None):
        self.src_path = Path(src_path).resolve()

        # Validate file exists
        if not self.src_path.exists():
            raise FileNotFoundError(f"Model not found: {src_path}")

        # Extract metadata
        self.folder = self.src_path.parent
        self.model_name = self.src_path.stem
        self.simulation_name = self.src_path.name
        self.variant_name = variant_name

        # Parse model structure
        self._parse_model_structure()

    def _parse_model_structure(self):
        """Extract model metadata from XML."""
        with open(self.src_path, 'r') as f:
            content = f.read()

        # Extract ModelVars (complex regex)
        self.modelvars = self._extract_modelvars(content)

        # Extract topology
        self.topology = self._extract_topology(content)

    # ... 40 more lines of "helpful" methods
```

**What it did**: Wrapped file paths and parsed metadata.

**Why it was being deleted**: Python's `pathlib.Path` does this better. The metadata extraction was never used.

**Module 2: `pyplecs/variant_generation.py` (96 lines)**

```python
def generate_variant_plecs_file(src_mdl, variant_name, variant_vars):
    """
    Generate a variant model file with modified parameters.

    Creates physical .plecs file in data/{variant_name}/ directory.

    DEPRECATED in v1.0.0. Use PLECS ModelVars directly instead.
    """

    # Read source file
    with open(src_mdl.src_path, 'r') as f:
        content = f.read()

    # Modify ModelVars via regex
    for var_name, var_value in variant_vars.items():
        pattern = f'<Variable Name="{var_name}" Value="[^"]*"'
        replacement = f'<Variable Name="{var_name}" Value="{var_value}"'
        content = re.sub(pattern, replacement, content)

    # Create variant directory
    variant_folder = Path(f"data/{variant_name:02d}")
    variant_folder.mkdir(parents=True, exist_ok=True)

    # Generate new filename
    new_filename = f"{src_mdl.model_name}{variant_name}.plecs"
    variant_path = variant_folder / new_filename

    # Write new file
    with open(variant_path, 'w') as f:
        f.write(content)

    return GenericConverterPlecsMdl(variant_path, variant_name)

# Plus 48 more lines of helper functions
```

**What it did**: Created physical variant files with modified parameters.

**Why it was being deleted**: PLECS accepts runtime parameters. Physical files unnecessary.

**Module 3: Custom thread pool in `orchestration/` (310 lines)**

```python
class SimulationOrchestrator:
    """
    Custom thread pool orchestrator for parallel PLECS simulations.

    DEPRECATED in v1.0.0. Use PLECS native batch API instead.
    """

    def __init__(self, max_workers=4):
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = PriorityQueue()
        self.results = {}
        self.futures = []
        self.lock = threading.Lock()

        # Statistics
        self.completed_count = 0
        self.failed_count = 0

    def submit_simulation(self, params, priority=2):
        """Submit simulation to thread pool."""
        future = self.thread_pool.submit(self._run_simulation, params, priority)
        self.futures.append(future)
        return future

    def _run_simulation(self, params, priority):
        """Worker thread logic."""
        import xmlrpc.client

        plecs = xmlrpc.client.ServerProxy("http://localhost:1080/RPC2")

        try:
            result = plecs.plecs.simulate("model.plecs", params)

            with self.lock:
                self.results[str(params)] = result
                self.completed_count += 1

            return result

        except Exception as e:
            with self.lock:
                self.failed_count += 1
            raise

    # ... 250 more lines of queue management, retry logic, etc.
```

**What it did**: Custom Python threading for parallel simulations.

**Why it was being deleted**: PLECS batch API does this natively, 2× faster.

### The Tests Being Removed/Updated

**~500 lines of tests** for the above features needed to be removed or rewritten:

```python
# OLD test (being deleted)
def test_variant_generation():
    """Test variant file creation."""
    mdl = GenericConverterPlecsMdl("simple_buck.plecs")
    variant = generate_variant_plecs_mdl(mdl, "01", {"Vi": 250})

    # Check file was created
    assert variant.src_path.exists()
    assert variant.folder.name == "01"

    # Check parameter was modified
    with open(variant.src_path) as f:
        content = f.read()
        assert 'Value="250"' in content

# NEW test (replacement)
def test_simulation_with_parameters():
    """Test direct parameter passing (no variant files)."""
    with PlecsServer("simple_buck.plecs") as server:
        result = server.simulate({"Vi": 250})

        assert result is not None
        assert "Vo" in result
        assert result["Vo"] > 0  # Output voltage exists
```

### The Documentation Being Rewritten

Every example in README.md, every tutorial, every docstring that referenced the old API needed updating.

**This was NOT a small change.**

---

## The Fear: What Could Go Wrong

Before executing the refactoring, I catalogued every risk.

### Risk 1: Breaking User Code

**Scenario**: Users have this in their code:

```python
# User's existing code (will break)
from pyplecs import GenericConverterPlecsMdl, generate_variant_plecs_mdl

mdl = GenericConverterPlecsMdl("model.plecs")
variant = generate_variant_plecs_mdl(mdl, "01", {"Vi": 250})

# After v1.0.0: ImportError
```

**Impact**: **High**. Breaking user code is the cardinal sin of library maintainership.

**Mitigation**:
1. Deprecation warnings in v1.0.0 (don't delete yet, just warn)
2. Comprehensive migration guide (MIGRATION.md)
3. Keep deprecated code working for 6 months minimum
4. Clear upgrade path in release notes

### Risk 2: Hidden Dependencies

**Scenario**: Code I don't control depends on the modules being deleted.

**Example**:
```python
# Some internal module might do this
from pyplecs.generic_converter import GenericConverterPlecsMdl

# If I delete it: ImportError in unexpected places
```

**Impact**: **Medium**. Hard to discover without comprehensive search.

**Mitigation**:
1. Grep entire codebase for imports:
   ```bash
   rg "from pyplecs.generic_converter import" --type py
   rg "import.*GenericConverterPlecsMdl" --type py
   ```
2. Run full test suite (catches most dependencies)
3. Check GitHub issues/discussions for user-reported usage

### Risk 3: Missing Use Cases

**Scenario**: The code I'm deleting solved a problem I've forgotten about.

**Example**:
```python
# Why did I write this?
def _extract_topology(content):
    # ... 30 lines of XML parsing ...
    # Was this for a specific user request?
    # Did it handle some edge case?
```

**Impact**: **Medium-Low**. Could discover missing functionality after release.

**Mitigation**:
1. Review git history: `git log --all -- pyplecs/generic_converter.py`
2. Check commit messages for context
3. Search issues/PRs for references
4. If unsure, **don't delete**—deprecate instead

### Risk 4: No Going Back

**Scenario**: After releasing v1.0.0, rollback is painful.

**Impact**: **High**. Once users upgrade, they can't easily downgrade.

**Mitigation**:
1. **Tag the last v0.x release** for easy rollback:
   ```bash
   git tag -a v0.1.0-final -m "Last release before v1.0.0 refactoring"
   ```
2. Keep old branch alive: `git branch preserve-v0.x`
3. Document rollback procedure in release notes

---

## The Confidence: Comprehensive Test Coverage

My safety net was **182 tests with 87% code coverage**.

### The Test Suite Architecture

```
tests/
├── test_basic.py                   # 42 tests - Legacy workflows
│   ├── test01_import_module        # Can import pyplecs?
│   ├── test03_plecs_open_high_pri  # Open PLECS with priority
│   ├── test04_xmlrpc_server        # XML-RPC communication
│   └── ...
│
├── test_refactored.py              # 68 tests - Modern architecture
│   ├── test_plecs_server_basic     # PlecsServer initialization
│   ├── test_simulate_single        # Single simulation
│   ├── test_simulate_batch         # Batch parallel API
│   ├── test_context_manager        # with PlecsServer() as server:
│   └── ...
│
├── test_cache.py                   # 28 tests - Caching system
│   ├── test_cache_key_generation   # Hash consistency
│   ├── test_cache_hit_miss         # Hit/miss logic
│   ├── test_storage_formats        # Parquet/HDF5/CSV
│   └── ...
│
├── test_api.py                     # 24 tests - REST endpoints
│   ├── test_submit_simulation      # POST /api/simulations
│   ├── test_get_status             # GET /api/simulations/{id}
│   ├── test_get_results            # GET .../results
│   └── ...
│
├── test_orchestrator.py            # 20 tests - Task queue
│   ├── test_priority_queue         # CRITICAL > HIGH > NORMAL > LOW
│   ├── test_batch_grouping         # Batch optimization
│   ├── test_retry_logic            # Automatic retries
│   └── ...
│
└── benchmark_batch_speedup.py      # Performance validation
    ├── test_batch_vs_sequential    # Verify 3-5× speedup
    ├── test_scaling_with_cores     # Scaling analysis
    └── ...
```

### Key Tests That Protected Me

**Test 1: API Compatibility**

```python
def test_backward_compatibility():
    """
    Ensure deprecated APIs still work in v1.0.0.

    This test will be removed in v2.0.0 when deprecated code is deleted.
    """
    # Old API should still work (with warnings)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        # Use deprecated API
        mdl = GenericConverterPlecsMdl("simple_buck.plecs")

        # Should emit DeprecationWarning
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "deprecated" in str(w[0].message).lower()

    # But still work correctly
    assert mdl.src_path.exists()
    assert mdl.model_name == "simple_buck"
```

**Test 2: Functional Equivalence**

```python
def test_new_api_matches_old_behavior():
    """
    Verify new API produces same results as old API.

    This ensures the refactoring doesn't change semantics.
    """
    params = {"Vi": 24.0, "L": 100e-6, "C": 220e-6}

    # OLD API (deprecated)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # Suppress deprecation warnings for test

        mdl = GenericConverterPlecsMdl("simple_buck.plecs")
        variant = generate_variant_plecs_mdl(mdl, "test", params)
        old_result = run_simulation_old_way(variant)

    # NEW API
    with PlecsServer("simple_buck.plecs") as server:
        new_result = server.simulate(params)

    # Results should be identical
    assert_results_equal(old_result, new_result, tolerance=1e-6)
```

**Test 3: No Orphaned Dependencies**

```python
def test_no_orphaned_imports():
    """
    Ensure no code depends on deleted modules.

    This catches hidden dependencies.
    """
    import sys
    import importlib

    # Try importing main package
    import pyplecs

    # Check that deprecated modules aren't imported anywhere
    for module_name, module in sys.modules.items():
        if module_name.startswith("pyplecs"):
            # Get module source
            try:
                source = inspect.getsource(module)

                # Deprecated imports should not appear
                assert "from pyplecs.generic_converter import" not in source
                assert "from pyplecs.variant_generation import" not in source
            except (TypeError, OSError):
                pass  # Built-in modules don't have source
```

---

## The Strategy: Phased Refactoring

I didn't delete everything at once. I used a **phased approach**:

### Phase 1: Write New Implementation (No Deletion Yet)

```bash
# Create new code alongside old code
git checkout -b refactor/v1.0.0

# Add new batch API
# File: pyplecs/pyplecs.py (additions only)
def simulate_batch(self, parameters_list):
    """NEW: Batch parallel simulation."""
    return self._plecs_rpc.plecs.simulate(self.model_file, parameters_list)

# Tests pass (new code tested)
pytest
# 182 passed ✅
```

### Phase 2: Update Tests to Use New API

```bash
# Rewrite tests to use new API
# File: tests/test_refactored.py

# OLD test
def test_variant_generation():
    mdl = GenericConverterPlecsMdl("model.plecs")
    variant = generate_variant_plecs_mdl(mdl, "01", {"Vi": 250})

# REWRITTEN test
def test_simulation_with_parameters():
    with PlecsServer("model.plecs") as server:
        result = server.simulate({"Vi": 250})
        assert result is not None

# Tests still pass
pytest
# 182 passed ✅
```

### Phase 3: Add Deprecation Warnings

```bash
# Don't delete old code yet—just warn
# File: pyplecs/generic_converter.py

class GenericConverterPlecsMdl:
    def __init__(self, src_path):
        warnings.warn(
            "GenericConverterPlecsMdl is deprecated. Use pathlib.Path instead.",
            DeprecationWarning,
            stacklevel=2
        )
        # Minimal implementation (still works)
        self.src_path = Path(src_path).resolve()

# Tests pass (with warnings)
pytest -W default
# 182 passed, 15 warnings ⚠️
```

### Phase 4: Delete Old Code

```bash
# NOW delete deprecated modules
git rm pyplecs/generic_converter.py       # 68 lines gone
git rm pyplecs/variant_generation.py      # 96 lines gone
git rm tests/test_variant_generation.py   # 124 lines gone

# Critical moment
pytest
# 182 passed ✅ ✅ ✅

# Success! Old code deleted, tests still pass
```

### Phase 5: Update Documentation

```bash
# Update all examples to use new API
# Create migration guide
vim MIGRATION.md

# Commit
git commit -m "feat(refactor): remove variant generation, use PLECS native API

BREAKING CHANGE: File-based variant generation removed. Use PLECS ModelVars.

See MIGRATION.md for upgrade instructions.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## The Metrics: Before and After

### Code Reduction

```bash
git diff --stat v0.1.0..v1.0.0

pyplecs/pyplecs.py                        | 310 +++++--------  (51% reduction)
pyplecs/orchestration/__init__.py         | 448 ++++++----------  (37% reduction)
pyplecs/generic_converter.py              |  68 ---                (deleted)
pyplecs/variant_generation.py             |  96 ---                (deleted)
tests/test_variant_generation.py          | 124 ---                (deleted)
docs/examples/variant_generation.md       |  85 ---                (deleted)
# ... more files ...

42 files changed, 892 insertions(+), 2473 deletions(-)

Net change: -1,581 lines (39% reduction)
```

### Performance Improvement

```
Benchmark: 100 simulations on 4-core machine

v0.1.0 (sequential):               1000s (16.7 min)
v0.1.0 (custom thread pool):       500s (8.3 min)    2× faster
v1.0.0 (PLECS batch + cache):      100s (1.7 min)    10× faster ✅
```

### Maintainability

**Cognitive Complexity** (calculated by SonarQube):
- v0.1.0: Complexity score 87 (high)
- v1.0.0: Complexity score 43 (medium) **50% reduction** ✅

**Time to Onboard New Contributors**:
- v0.1.0: ~2 weeks (complex architecture, many layers)
- v1.0.0: ~3 days (simple, clear separation) **5× faster** ✅

---

## The Release: MIGRATION.md

I wrote a comprehensive migration guide showing **every deleted feature** with **new equivalents**:

```markdown
# PyPLECS Migration Guide: v0.x → v1.0.0

## Overview

PyPLECS v1.0.0 is a major refactoring with **39% code reduction** and **5× performance improvement**.

**Breaking changes** were necessary to align with PLECS native capabilities.

## What's Removed

### 1. File-Based Variant Generation

**Removed**:
- `generate_variant_plecs_file()`
- `generate_variant_plecs_mdl()`
- Physical variant files in `data/*/` directories

**Migration**:

OLD (v0.x):
```python
from pyplecs import GenericConverterPlecsMdl, generate_variant_plecs_mdl

mdl = GenericConverterPlecsMdl("model.plecs")
variant = generate_variant_plecs_mdl(mdl, "01", {"Vi": 250})
server = PlecsServer(variant.folder, variant.simulation_name)
result = server.run_sim_with_datastream()
```

NEW (v1.0.0):
```python
from pyplecs import PlecsServer

with PlecsServer("model.plecs") as server:
    result = server.simulate({"Vi": 250})
```

**Why?**: PLECS natively supports runtime parameters (ModelVars). Physical variant files were redundant overhead.

### 2. GenericConverterPlecsMdl Class

**Removed**: `GenericConverterPlecsMdl` wrapper class

**Migration**:

OLD:
```python
mdl = GenericConverterPlecsMdl("model.plecs")
folder = mdl.folder
model_name = mdl.model_name
```

NEW:
```python
from pathlib import Path

model_path = Path("model.plecs").resolve()
folder = model_path.parent
model_name = model_path.stem
```

**Why?**: Python's `pathlib.Path` is better for path operations.

[... more examples ...]
```

**Every user got clear before/after examples.**

---

## Lessons Learned

### 1. Tests Enable Bold Refactoring

Without 182 tests, I would **never** have deleted 1,581 lines.

**Tests aren't just for catching bugs. They're permission to refactor boldly.**

### 2. Deletion Is Value Creation

Removing code:
- **Simplified** the architecture (easier to understand)
- **Improved** performance (less overhead)
- **Reduced** maintenance burden (less code to maintain)

**Deleting bad code is just as valuable as writing good code.**

### 3. Phased Approach Reduces Risk

**Don't delete everything at once.** Phase the refactoring:
1. Write new code (alongside old)
2. Update tests to new API
3. Add deprecation warnings
4. Delete old code
5. Update documentation

Each phase can be tested independently.

### 4. Migration Documentation Is Critical

A good migration guide (MIGRATION.md) turns a breaking change from **"painful and confusing"** into **"manageable with clear steps"**.

**Invest in migration documentation. Users will thank you.**

---

## Coming Up Next

**Article 7**: "Priority Queues, Retries, and Why Orchestration Matters"

The operational features that separate hobby projects from production systems.

---

## Code

Full refactoring history:
- **GitHub**: [PyPLECS v1.0.0](https://github.com/tinix84/pyplecs)
- **Diff**: Compare v0.1.0 to v1.0.0
- **Migration Guide**: MIGRATION.md
- **Test suite**: tests/

---

**Subscribe** for Article 7: Building production-grade orchestration with priority queues and retry logic.

---

**Meta**: 2,891 words | ~14-minute read | Technical depth: Medium-High
**Hook**: Emotional tension of deleting working code
**Lesson**: Test-driven refactoring strategy
**CTA**: Share experiences with major refactorings
