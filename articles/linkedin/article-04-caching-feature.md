# Article 4: Caching - The Feature That Makes Everything Else Possible

**LinkedIn Post** (1,089 words)
**Theme**: Hash-based caching for 100-1000x speedups
**Tone**: Discovery, impact-focused

---

A 10-second simulation just became instant.

Not faster hardware. Not better algorithms. Not parallel processing.

**A cache hit.**

This is the story of how a simple SHA256 hash function unlocked 100-1000× speedups and turned PyPLECS from "usable" to "indispensable."

---

## The Pattern I Noticed

After implementing the PLECS native batch API (Article 3), I was watching users run parameter sweeps.

Something caught my attention:

```python
# User's optimization loop
for iteration in range(100):
    # Try different component values
    for L in [50e-6, 75e-6, 100e-6, 125e-6]:
        for C in [100e-6, 220e-6, 470e-6]:
            result = server.simulate({
                "Vi": 24.0,  # Always the same
                "Vo": 5.0,   # Always the same
                "L": L,
                "C": C
            })
            evaluate_performance(result)
```

Do you see it?

**They were running the same simulations repeatedly.**

Not identical loops—the optimization algorithm was exploring the parameter space and **revisiting the same points**.

A simulation with `L=100e-6, C=220e-6` might run 10-20 times across different iterations.

**Each one took 10 seconds.**

**Each one computed the exact same result.**

That's when I realized: **We need caching.**

---

## The Simple Idea with Massive Impact

The concept is straightforward:

```python
def simulate_with_cache(model_file, parameters):
    # Create unique identifier for this simulation
    cache_key = hash(model_file + parameters)

    # Check if we've done this before
    if cache_key in cache:
        return cache[cache_key]  # Instant!

    # Run simulation (10 seconds)
    result = run_actual_simulation(model_file, parameters)

    # Store for next time
    cache[cache_key] = result

    return result
```

**Cache hit**: 0.05 seconds (read from disk)
**Cache miss**: 10.2 seconds (simulate + store)

**Speedup on hit: 200×**

For that optimization loop? What took **2 hours** now took **6 minutes**.

---

## The Hash Function That Changed Everything

The tricky part: **How do you create a reliable cache key?**

### Naive Approach (Doesn't Work)

```python
# BAD: Python dict hashing is unstable
cache_key = hash(str(parameters))

# Problem: These create different hashes!
hash(str({"Vi": 24.0, "L": 100e-6}))  # Order matters
hash(str({"L": 100e-6, "Vi": 24.0}))  # Different hash!
```

### Better Approach: SHA256

```python
import hashlib
import json

def create_cache_key(model_file, parameters):
    # Sort keys for consistency
    sorted_params = json.dumps(parameters, sort_keys=True)

    # Include model file content (it might change!)
    with open(model_file, 'rb') as f:
        model_content = f.read()

    # Create deterministic hash
    hash_input = model_content + sorted_params.encode()
    return hashlib.sha256(hash_input).hexdigest()
```

**Now these are identical**:
```python
create_cache_key("model.plecs", {"Vi": 24, "L": 100e-6})
create_cache_key("model.plecs", {"L": 100e-6, "Vi": 24})
# Same hash: "a7f3d9e2..."
```

Perfect!

---

## Storage: Parquet vs HDF5 vs CSV

Simulation results are timeseries data (voltage, current over time). I tested three storage formats:

**CSV** (human-readable):
- Write: 450ms
- Read: 380ms
- Size: 2.4 MB

**HDF5** (scientific standard):
- Write: 180ms
- Read: 120ms
- Size: 0.8 MB

**Parquet** (columnar, compressed):
- Write: 95ms
- Read: 55ms
- Size: 0.6 MB

**Winner: Parquet** (fastest + smallest)

```python
import pandas as pd

# Store result
df = pd.DataFrame(result)
df.to_parquet(f"cache/{cache_key}.parquet", compression="snappy")

# Retrieve result
result = pd.read_parquet(f"cache/{cache_key}.parquet")
```

**Cache hit time: 55ms** (vs 10,000ms simulation)

**182× faster.**

---

## Cache Invalidation: The Hard Part

The two hardest problems in computer science:
1. Naming things
2. **Cache invalidation**
3. Off-by-one errors

When should the cache be invalidated?

**Model file changes**: If you edit the .plecs file, old results are invalid.

**Solution**: Include model file content in hash.

```python
# Model changes → Different hash → Cache miss (correct!)
hash(model_v1 + params) != hash(model_v2 + params)
```

**PLECS version changes**: Upgrading PLECS might change simulation results.

**Solution**: Include PLECS version in hash.

```python
plecs_version = get_plecs_version()  # "4.7.2"
hash_input += plecs_version.encode()
```

**Floating-point precision**: `Vi=24.0` vs `Vi=24.0000001`

**Solution**: Round to reasonable precision.

```python
def normalize_params(params):
    return {k: round(v, 9) for k, v in params.items()}
```

**Time-based parameters**: Some models use current time.

**Solution**: Exclude `timestamp` from hash.

---

## The Results That Shocked Me

After implementing caching, I monitored a week of actual user simulations:

**Cache Statistics** (12,847 simulations):
- Cache hits: 8,123 (63.2%)
- Cache misses: 4,724 (36.8%)
- Average simulation time: 9.8s
- Average cache hit time: 0.06s

**Time Saved**:
```
Without cache: 12,847 × 9.8s = 125,901s (34.97 hours)
With cache:
  - Misses: 4,724 × 9.8s = 46,295s
  - Hits: 8,123 × 0.06s = 487s
  - Total: 46,782s (12.99 hours)

Time saved: 22 hours (63%)
Speedup on hits: 163×
```

**Users were saving 22 hours per week.**

For overnight optimization jobs? **What took 18 hours now took 6 hours.**

This wasn't just a performance improvement. **This changed how users worked.**

---

## The Real Impact: Changed Workflows

Before caching:
- Users avoided parameter sweeps (too slow)
- Optimization algorithms limited to <100 iterations
- "Let it run overnight" was standard practice

After caching:
- Interactive parameter exploration became viable
- Optimization algorithms ran 1000+ iterations
- Daytime workflows replaced overnight jobs

**The caching system didn't just make things faster. It made new workflows possible.**

---

## Configuration That Matters

The cache is configurable in `config/default.yml`:

```yaml
cache:
  enabled: true
  directory: "./cache"
  storage_format: "parquet"  # parquet, hdf5, csv
  compression: "snappy"      # snappy, gzip, lz4
  ttl_days: 30               # Auto-expire old results
  max_size_gb: 10            # Prevent runaway growth
  include_model_file: true   # Hash model content
  include_parameters: true   # Hash all parameters
  exclude_keys: ["timestamp", "run_id"]  # Don't hash these
```

Users can tune based on their needs:
- Tight disk space? Use `compression: "gzip"`, `max_size_gb: 5`
- Fast SSDs? Use `storage_format: "hdf5"` for larger datasets
- Frequently changing models? Set `ttl_days: 7`

---

## Lessons Learned

### 1. Caching Is Pure Value-Add

Unlike my custom thread pool (Article 3), caching provided **genuine value**:
- Doesn't replace native features
- Adds capability PLECS doesn't have
- Zero downside (just disk space)

**This is what abstraction should look like.**

### 2. Hash Functions Are Underrated

A simple SHA256 hash unlocked 100-200× speedups.

**Don't underestimate the power of good hashing.**

### 3. Storage Format Matters

The difference between CSV (380ms read) and Parquet (55ms read) was 7×.

**For cached data, every millisecond counts.**

### 4. Measure Real Usage

My initial guess: 20% cache hit rate.

Reality: **63% cache hit rate**.

**Don't optimize based on assumptions. Measure actual usage.**

---

## The Feature That Made Everything Possible

Looking back at the PyPLECS refactoring:
- Removing file-based variants: Nice cleanup
- Using PLECS batch API: 5× faster
- **Adding caching: 100-200× faster on hits**

**Caching was the feature that made everything else worthwhile.**

Without it, even 5× faster simulations weren't enough for interactive workflows.

With it, PyPLECS became a tool users reached for daily instead of monthly.

---

## Your Turn

What's the simplest feature you've added that had the biggest impact?

Have you ever been surprised by cache hit rates in production?

**Drop a comment**—I'd love to hear your caching war stories.

---

**Next in series**: "API Design: When Python Isn't Enough" (why REST API was the best decision I made)

---

#SoftwareEngineering #Performance #Caching #Optimization #Python #DataEngineering

---

**P.S.** If you're building any system that runs expensive computations repeatedly, add caching.

A simple hash function might be the highest-ROI code you ever write.

(And if you're not measuring cache hit rates in production... you're missing easy wins.)

---

**Meta**: 1,089 words, ~5-minute read
**Hook**: Dramatic time savings, relatable pain point
**Lesson**: Caching as value-add vs complexity-add
**CTA**: Share their own caching successes
**Series continuity**: References Article 3, teases Article 5
