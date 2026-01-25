# Legacy Variant Generation (v0.x - Deprecated)

This example documents the OLD file-based variant generation approach that was **removed in v1.0.0**. This file serves as historical reference for users migrating from v0.x.

## What Was Removed

PyPLECS v0.x included a file-based variant generation system that:
- Created physical `.plecs` files in subdirectories (`data/01/`, `data/02/`, etc.)
- Used the `GenericConverterPlecsMdl` class to wrap model files
- Provided `generate_variant_plecs_mdl()` and `generate_variant_plecs_file()` functions

**Why it was removed**: PLECS native `ModelVars` API already handles parameter variations without file generation. Creating physical files was unnecessary, slow, and cluttered the workspace.

---

## Old Approach (v0.x - DO NOT USE)

### Example: File-Based Variant Generation

```python
from pyplecs import GenericConverterPlecsMdl, generate_variant_plecs_mdl, PlecsServer

# Step 1: Create model object
buck_mdl = GenericConverterPlecsMdl("simple_buck.plecs")

# Step 2: Generate variant file in subdirectory
ModelVars = {"Vi": 250, "Vo_ref": 25}
variant_mdl = generate_variant_plecs_mdl(
    src_mdl=buck_mdl,
    variant_name='01',  # Creates file in data/01/
    variant_vars=ModelVars
)

# Step 3: Run simulation on generated variant file
plecs_server = PlecsServer(
    sim_path=variant_mdl.folder,          # "data/01/"
    sim_name=variant_mdl.simulation_name  # "simple_buck01.plecs"
)
results = plecs_server.run_sim_with_datastream()
```

### What Happened Behind the Scenes

1. **File Generation**:
   - Original model: `simple_buck.plecs`
   - Generated variant: `data/01/simple_buck01.plecs`
   - The variant file was a **physical copy** with ModelVars embedded

2. **Directory Structure Created**:
   ```
   project/
   ├── simple_buck.plecs       # Original
   └── data/
       ├── 01/
       │   └── simple_buck01.plecs  # Generated variant
       └── 02/
           └── simple_buck02.plecs  # Another variant
   ```

3. **Problems with This Approach**:
   - ❌ File I/O overhead (slow)
   - ❌ Disk space wasted on duplicates
   - ❌ Workspace clutter (dozens of variant directories)
   - ❌ PLECS already supports ModelVars without file generation
   - ❌ Unnecessary abstraction layer

---

## New Approach (v1.0.0+ - USE THIS)

### Example: Direct ModelVars Usage

```python
from pyplecs import PlecsServer

# No file generation needed - use ModelVars directly
with PlecsServer("simple_buck.plecs") as server:
    ModelVars = {"Vi": 250, "Vo_ref": 25}
    results = server.simulate(ModelVars)
```

### What Happens Now

1. **No File Generation**: PLECS loads `simple_buck.plecs` and applies ModelVars in memory
2. **No Directory Clutter**: No `data/01/`, `data/02/` subdirectories created
3. **Faster Execution**: No file I/O overhead
4. **Simpler Code**: 3 lines instead of 10+

---

## Batch Simulations: Old vs New

### Old Approach (v0.x - Sequential File Generation)

```python
from pyplecs import GenericConverterPlecsMdl, generate_variant_plecs_mdl, PlecsServer

buck_mdl = GenericConverterPlecsMdl("simple_buck.plecs")

results = []
for i, voltage in enumerate([12, 24, 48, 96]):
    # Generate variant file
    variant_mdl = generate_variant_plecs_mdl(
        src_mdl=buck_mdl,
        variant_name=f"{i:02d}",
        variant_vars={"Vi": voltage}
    )

    # Run simulation on variant file
    server = PlecsServer(variant_mdl.folder, variant_mdl.simulation_name)
    result = server.run_sim_with_datastream()
    results.append(result)

# Result: 4 files created (data/00/, data/01/, data/02/, data/03/)
# Performance: Sequential execution (no parallelization)
```

### New Approach (v1.0.0+ - Batch Parallel)

```python
from pyplecs import PlecsServer

with PlecsServer("simple_buck.plecs") as server:
    # Prepare parameter list
    params_list = [
        {"Vi": 12},
        {"Vi": 24},
        {"Vi": 48},
        {"Vi": 96}
    ]

    # Batch execution - PLECS parallelizes internally
    results = server.simulate_batch(params_list)

# Result: 0 files created (all in-memory)
# Performance: 3-5x faster on multi-core machines
```

---

## Migration Path

If you have code using the old file-based approach:

### Step 1: Remove File Generation
```python
# OLD - Delete this code
buck_mdl = GenericConverterPlecsMdl("simple_buck.plecs")
variant_mdl = generate_variant_plecs_mdl(buck_mdl, "01", {"Vi": 250})

# NEW - Replace with this
# (No model object needed - use path directly)
```

### Step 2: Simplify PlecsServer Usage
```python
# OLD
plecs_server = PlecsServer(
    sim_path=variant_mdl.folder,
    sim_name=variant_mdl.simulation_name
)
results = plecs_server.run_sim_with_datastream()

# NEW
with PlecsServer("simple_buck.plecs") as server:
    results = server.simulate({"Vi": 250})
```

### Step 3: Clean Up Generated Files
```bash
# After migration, delete old variant directories
rm -rf data/01/
rm -rf data/02/
# ... etc
```

---

## Historical Context: Why This Existed

In early versions of PyPLECS (v0.x), the file-based approach seemed logical because:
1. We didn't fully understand PLECS XML-RPC capabilities
2. Physical files felt "safer" for debugging
3. It matched patterns from MATLAB workflows

**The lesson**: Sometimes the best refactoring is deleting code that wraps functionality that already exists natively. The PLECS API is more capable than we initially realized.

---

## Summary

**Don't do this**:
```python
# File-based variant generation (REMOVED)
variant_mdl = generate_variant_plecs_mdl(mdl, "01", params)
server = PlecsServer(variant_mdl.folder, variant_mdl.simulation_name)
```

**Do this instead**:
```python
# Direct ModelVars usage (v1.0.0+)
with PlecsServer("model.plecs") as server:
    results = server.simulate(params)
```

**For complete migration guide**, see [MIGRATION.md](../../MIGRATION.md)

**Performance boost**: Use `simulate_batch()` for 3-5x speedup on multiple simulations!
