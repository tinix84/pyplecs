# The False Economy of Abstraction: When "Clean Code" Becomes Technical Debt

**Substack Article** (2,956 words)
**Theme**: Abstraction analysis + architectural lessons
**Format**: Narrative → Technical Analysis → Pattern Recognition

---

> "The best code is the code you don't write. The second best is the code you delete."

I thought I was being a good software engineer. I created classes to "encapsulate complexity." I wrote clean interfaces. I followed design patterns from the books.

Six months later, that "clean code" had become the biggest source of technical debt in my codebase.

This is the story of `GenericConverterPlecsMdl`—a 68-line abstraction that taught me that **abstraction without purpose is just complexity in disguise**.

---

## The Genesis of an Unnecessary Abstraction

*Continuing from Article 1's wake-up call...*

When I started building PyPLECS (Python automation for PLECS power electronics simulations), I faced what seemed like a reasonable problem:

**PLECS model files are XML. They're awkward to work with directly.**

```xml
<!-- simple_buck.plecs -->
<?xml version="1.0" encoding="UTF-8"?>
<Model version="4.7">
  <ModelVars>
    <Variable Name="Vi" Value="12.0"/>
    <Variable Name="Vo_ref" Value="5.0"/>
    <!-- ... more parameters ... -->
  </ModelVars>
  <!-- ... circuit definition ... -->
</Model>
```

Working with this directly meant:
- String paths: `"/path/to/simple_buck.plecs"`
- Manual parsing to extract metadata
- No type safety
- Path manipulation edge cases

So I did what every "good" object-oriented programmer would do:

**I created an abstraction layer.**

### The Abstraction: GenericConverterPlecsMdl

```python
class GenericConverterPlecsMdl:
    """
    Wrapper for PLECS model files with metadata extraction.

    Provides clean interface for model file operations:
    - Path handling
    - Metadata extraction
    - Variant generation
    - Validation
    """

    def __init__(self, src_path, variant_name=None):
        """Initialize model wrapper."""
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

        # Extract ModelVars
        self.modelvars = self._extract_modelvars(content)

        # Extract circuit topology (for metadata)
        self.topology = self._extract_topology(content)

    def _extract_modelvars(self, content):
        """Parse ModelVars from XML."""
        # Complex regex parsing...
        pattern = r'<Variable Name="([^"]+)" Value="([^"]+)"/>'
        matches = re.findall(pattern, content)
        return {name: float(value) for name, value in matches}

    # ... 40 more lines of "helpful" methods ...
```

At the time, this felt **good**:
- ✅ Clean API
- ✅ Encapsulation
- ✅ Single Responsibility Principle
- ✅ Reusable
- ✅ Testable

I even wrote comprehensive tests (another 100+ lines).

I showed it to colleagues: **"Look how elegant this is!"**

They nodded approvingly. One said: **"Good abstraction. Very clean."**

**We were all wrong.**

---

## The File Generation Subsystem: Cleverness Gone Wrong

But the abstraction didn't stop there. I built an entire **variant generation system** around it:

```python
def generate_variant_plecs_mdl(src_mdl, variant_name, variant_vars):
    """
    Generate a variant model with modified parameters.

    Args:
        src_mdl: Source GenericConverterPlecsMdl object
        variant_name: Unique identifier (e.g., "01", "02")
        variant_vars: Dict of ModelVars to modify

    Returns:
        New GenericConverterPlecsMdl pointing to variant file
    """

    # Step 1: Read source content
    with open(src_mdl.src_path, 'r') as f:
        content = f.read()

    # Step 2: Modify ModelVars via regex
    for var_name, var_value in variant_vars.items():
        # Find the variable
        pattern = f'<Variable Name="{var_name}" Value="[^"]*"'
        replacement = f'<Variable Name="{var_name}" Value="{var_value}"'
        content = re.sub(pattern, replacement, content)

    # Step 3: Create variant directory
    variant_folder = Path(f"data/{variant_name:02d}")
    variant_folder.mkdir(parents=True, exist_ok=True)

    # Step 4: Generate new filename
    new_filename = f"{src_mdl.model_name}{variant_name}.plecs"
    variant_path = variant_folder / new_filename

    # Step 5: Write new file
    with open(variant_path, 'w') as f:
        f.write(content)

    # Step 6: Create new model object
    return GenericConverterPlecsMdl(variant_path, variant_name)
```

This was my **magnum opus** of abstraction. I was proud of it:

✅ Generates physical files for each parameter variant
✅ Organizes them in subdirectories (`data/01/`, `data/02/`, etc.)
✅ Creates new model objects for each variant
✅ Maintains clean separation
✅ Follows design patterns

**This system generated 622-line .plecs files for every parameter variant.**

For a parameter sweep from 12V to 48V in 6V increments:
- Created 7 directories
- Generated 7 physical .plecs files (each 622 lines)
- Total: 4,354 lines of XML on disk
- Plus cleanup code to remove them later

I thought this was **good engineering**.

---

## The Moment of Clarity: A Conversation

Six months later, I was onboarding a new contributor:

**Contributor**: "So to run a simulation with Vi=24V instead of Vi=12V, I need to create a variant file?"

**Me**: "Yes! The system generates a new .plecs file in a subdirectory with the modified parameter."

**Contributor**: "...why?"

**Me**: "For clean separation. Each variant gets its own file."

**Contributor**: "But don't simulation tools usually accept runtime parameters?"

**Me**: "Well, yes, but—"

**Contributor**: "And PLECS supports that, right? ModelVars?"

**Me**: "Yes..."

**Contributor**: "So why create physical files?"

Silence.

**That's when I realized**: I'd built an entire subsystem to work around a feature that **already existed and worked better**.

---

## What PLECS Actually Does (That I Ignored)

Here's what I didn't properly understand when building my abstraction:

### PLECS Native ModelVars

PLECS has **runtime parameters** called ModelVars. You can set them **without modifying the file**:

```python
# Native PLECS approach (what I should have used)
import xmlrpc.client

plecs = xmlrpc.client.ServerProxy("http://localhost:1080/RPC2")
result = plecs.plecs.simulate(
    "simple_buck.plecs",  # One file
    {"Vi": 24.0}           # Runtime parameter
)
```

**That's it.** One file, one call, runtime parameters.

### What My Abstraction Forced

```python
# My overcomplicated approach
from pyplecs import GenericConverterPlecsMdl, generate_variant_plecs_mdl

# Step 1: Create model object
buck_mdl = GenericConverterPlecsMdl("simple_buck.plecs")

# Step 2: Generate variant (creates physical file)
variant_mdl = generate_variant_plecs_mdl(
    src_mdl=buck_mdl,
    variant_name="01",
    variant_vars={"Vi": 24.0}
)

# Step 3: Create server with variant paths
from pyplecs import PlecsServer
server = PlecsServer(
    sim_path=variant_mdl.folder,        # "data/01/"
    sim_name=variant_mdl.simulation_name  # "simple_buck01.plecs"
)

# Step 4: Run simulation
results = server.run_sim_with_datastream()

# Step 5: Clean up generated file (not shown)
```

I turned **one line into six lines** (plus cleanup).

---

## The Technical Cost of Abstraction

Let's break down what my "clean" abstraction actually cost:

### Performance Impact

```
Native PLECS approach:
- File reads: 1 (model.plecs)
- File writes: 0
- Disk I/O time: ~5ms
- Memory overhead: Minimal

My abstraction:
- File reads: 2 (source + variant)
- File writes: 1 (variant generation)
- Disk I/O time: ~25ms
- Disk space: 622 lines × 7 variants = 4,354 lines
- Memory overhead: 7 model objects
- Cleanup overhead: 7 files to delete

Performance penalty: ~5x slower for file operations
```

### Maintenance Cost

```python
# Lines of code
GenericConverterPlecsMdl class: 68 lines
generate_variant_plecs_mdl: 48 lines
Supporting utilities: ~30 lines
Tests for abstraction: 120 lines
Documentation: 200 lines (README, docstrings)
────────────────────────────────────────
Total: ~466 lines

# For functionality that could be:
plecs.simulate("model.plecs", {"Vi": 24.0})  # 1 line
```

### Cognitive Load

Users had to understand:
- What is `GenericConverterPlecsMdl`?
- Why do I create variant files?
- Where do variants get stored?
- How do I clean up variants?
- When should I use variants vs. direct simulation?

**Five concepts to learn for something that should be one function call.**

---

## The Architecture Diagram: Before vs. After

### Before (With Abstraction)

```
User wants to simulate with Vi=24V
    ↓
Create GenericConverterPlecsMdl object
    ↓
Call generate_variant_plecs_mdl
    ↓
    → Read source file (I/O)
    → Parse XML (CPU)
    → Modify parameters (regex)
    → Create directory (I/O)
    → Write new file (I/O)
    → Create new model object
    ↓
Create PlecsServer with variant paths
    ↓
Run simulation on variant file
    ↓
Clean up variant file (I/O)

Complexity: HIGH
Code: 466 lines
Performance: 5x slower (file I/O)
```

### After (Without Abstraction)

```
User wants to simulate with Vi=24V
    ↓
Call plecs.simulate("model.plecs", {"Vi": 24.0})
    ↓
Done.

Complexity: LOW
Code: 1 line
Performance: Fast (no extra I/O)
```

**The abstraction added 465 lines and made things slower.**

---

## The False Economy Revealed

Here's the economic analysis of my abstraction:

**Investment** (costs):
- Development time: ~1 week
- Code maintenance: 466 lines
- Testing: 120 lines
- Documentation: 200 lines
- Cognitive load on users
- Performance penalty: 5x slower
- Disk space: 4KB per variant

**Returns** (benefits):
- Cleaner-looking API? (debatable—actually more complex)
- File-based debugging? (never used for debugging)
- Version control of variants? (not needed—parameters in Git instead)

**ROI**: **Negative.** Heavily negative.

This is the **false economy of abstraction**: investing effort in complexity that provides no actual value.

---

## Why Did I Build This?

Looking back with clarity, I can identify the psychological factors:

### 1. Abstraction Feels Like Good Engineering

We're taught:
- "Encapsulate implementation details"
- "Program to interfaces"
- "Single Responsibility Principle"
- "Don't Repeat Yourself"

These are good principles, but I applied them **without asking if they were needed**.

### 2. Cleverness as Status Signal

The variant generation system was **clever**. Colleagues praised it. Code reviews approved it.

**Cleverness feels good.** It signals expertise.

But **cleverness without purpose is just complexity**.

### 3. Not Reading Documentation Thoroughly

I skimmed the PLECS docs for "how to run simulation" and found the basic example.

I **missed** the section on runtime parameters because I was already thinking about "my solution."

**Confirmation bias**: I saw what I expected to see.

### 4. Premature Optimization of Workflow

I thought: "Physical files will make debugging easier."

Reality: **I never debugged using the generated files. Not once.**

I optimized for a workflow that didn't exist.

---

## The Refactoring: Deletion as Liberation

When I finally refactored (PyPLECS v1.0.0), deleting the abstraction was **terrifying**:

**Fears**:
- What if users depend on this API?
- What if there's a use case I'm forgetting?
- What if the abstraction actually was valuable?

**Reality**:
- Breaking change, but necessary
- No hidden use cases (comprehensive tests proved it)
- The abstraction was pure overhead

### The Delete

```bash
git rm pyplecs/generic_converter.py  # 68 lines
git rm pyplecs/variant_generation.py  # 48 lines
git rm -r tests/test_generic_converter.py  # 120 lines
# Update imports, docs, examples...

Total deletion: 466 lines
Time to delete: 30 seconds
Emotional difficulty: High
Actual risk: Low (tests caught everything)
```

### The Replacement

```python
# Old (with abstraction)
buck_mdl = GenericConverterPlecsMdl("simple_buck.plecs")
variant_mdl = generate_variant_plecs_mdl(buck_mdl, "01", {"Vi": 250})
server = PlecsServer(variant_mdl.folder, variant_mdl.simulation_name)
results = server.run_sim_with_datastream()

# New (without abstraction)
with PlecsServer("simple_buck.plecs") as server:
    results = server.simulate({"Vi": 250})
```

**Results**:
- User code: 6 lines → 2 lines
- Performance: 5x faster
- Cognitive load: Way lower
- Maintenance burden: Gone

**Everyone won when the abstraction died.**

---

## Lessons Learned: The Abstraction Decision Tree

I now use this mental model before creating any abstraction:

### Question 1: What Problem Does This Solve?

If you can't articulate a **specific, real problem**, don't abstract.

**Bad**: "It might be useful someday"
**Good**: "Three different modules need this exact functionality"

### Question 2: Does an Existing Solution Work?

Check:
- Standard library
- Framework features
- Tool-native capabilities

**Most of the time**, something already solves your problem.

### Question 3: What's the Cost?

Calculate:
- Lines of code to write
- Tests to maintain
- Documentation to create
- Cognitive load on users
- Performance impact

If cost > benefit, **don't do it**.

### Question 4: What's the Exit Strategy?

How hard will it be to remove this abstraction if it becomes debt?

**Make abstractions easy to delete from day one.**

---

## Principles I Now Follow

### 1. Resist Abstraction by Default

**Default**: Don't abstract.

Only abstract when you can clearly demonstrate value.

### 2. Start Concrete, Abstract Later

Write the solution concretely first. If you write it three times and notice duplication, **then** consider abstracting.

**Don't abstract preemptively.**

### 3. The Simplest Solution Is Usually Right

Between:
- Complex abstraction that handles edge cases
- Simple solution that handles the common case

**Choose simple.** Handle edge cases when they actually occur.

### 4. Measure Value, Not Elegance

Code is beautiful when it **solves problems simply**, not when it follows patterns for their own sake.

---

## The Meta Lesson

The hardest part of refactoring isn't writing new code.

**It's deleting code you're emotionally attached to.**

That `GenericConverterPlecsMdl` class took me a week to design and build. I was proud of it.

Deleting it took 30 seconds.

**Best 30 seconds I ever spent.**

---

## Coming Up in This Series

**Article 3**: "The 5x Performance Gift Hiding in Plain Sight"
- How PLECS native batch API crushed my custom thread pool
- Why native is almost always faster than custom
- The hidden costs of "rolling your own"

**Later articles**:
- Caching: The Feature That Makes Everything Else Possible
- The Refactoring That Deleted 1,581 Lines
- How AI Changed How I Code

---

## Discussion

**For the comments**:
1. What's an abstraction you created that you later regretted?
2. How do you decide when abstraction is worth it?
3. Have you ever deleted more code than you added in a refactor?

---

## Code

All code from this refactoring is open source:
- **GitHub**: [PyPLECS v1.0.0](https://github.com/tinix84/pyplecs)
- **Before/After examples**: See MIGRATION.md
- **Full diff**: Compare v0.1.0 to v1.0.0

---

**If this resonated**, share it with someone fighting their own abstractions.

**Subscribe** to follow the refactoring journey: 4,081 lines → 2,500 lines.

---

**Meta**: 2,956 words | ~15-minute read | Technical depth: Medium-High
