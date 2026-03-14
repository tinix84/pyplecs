# Article 2: The False Economy of Abstraction

**LinkedIn Post** (1,087 words)
**Theme**: When abstraction becomes technical debt
**Tone**: Reflective, cautionary tale

---

I thought I was being a good engineer.

I created a class to "abstract away complexity." I wrote clean interfaces. I followed design patterns.

Six months later, that abstraction became the biggest source of technical debt in my codebase.

This is the story of `GenericConverterPlecsMdl`—68 lines of "clean code" that should never have existed.

---

## The Birth of an Abstraction

When I started PyPLECS, I had a reasonable goal: make PLECS simulation files easier to work with.

PLECS models are XML files. They're messy to parse directly. Paths are awkward. You need metadata.

So I did what every "good" engineer would do: **I created an abstraction layer.**

```python
class GenericConverterPlecsMdl:
    """Clean wrapper for PLECS model files."""

    def __init__(self, src_path):
        self.src_path = Path(src_path)
        self.folder = self.src_path.parent
        self.model_name = self.src_path.stem
        self.simulation_name = self.src_path.name
        # Plus 60 more lines of "helpful" methods
```

It felt good. Clean API. Encapsulation. Reusability.

I showed it to colleagues: "Look how elegant this is!"

They nodded approvingly. "Good abstraction."

**We were all wrong.**

---

## The Problem with "Clean" Abstractions

Fast forward six months. A user asks: "How do I run a simulation?"

The answer should be:
```python
results = simulate("model.plecs", {"Vi": 12.0})
```

But with my abstraction, it was:
```python
model = GenericConverterPlecsMdl("model.plecs")
server = PlecsServer(model.folder, model.simulation_name)
results = server.run_sim_with_datastream()
```

I'd turned **one line into three**.

"But wait," I told myself, "the abstraction provides value! It handles path parsing, metadata extraction, validation..."

Except:
- **Path parsing**: Python's `pathlib` already does this
- **Metadata extraction**: Never actually used
- **Validation**: Happened in the wrong place (too early)

I'd created an abstraction that **added complexity without adding value**.

---

## The "Clever" File Generation System

But it got worse.

I built an entire system around this class:

```python
def generate_variant_plecs_mdl(src_mdl, variant_name, variant_vars):
    """Generate a new model file with different parameters."""

    # Step 1: Create GenericConverterPlecsMdl object
    model = GenericConverterPlecsMdl(src_mdl.src_path)

    # Step 2: Parse XML content
    content = model.read_content()

    # Step 3: Modify parameters via regex
    for var, value in variant_vars.items():
        content = modify_modelvar(content, var, value)

    # Step 4: Create new directory
    variant_folder = Path(f"data/{variant_name}")
    variant_folder.mkdir(exist_ok=True)

    # Step 5: Write new file
    new_path = variant_folder / f"{model.model_name}{variant_name}.plecs"
    new_path.write_text(content)

    # Step 6: Return new model object
    return GenericConverterPlecsMdl(new_path)
```

I was so proud of this.

It was **clever**. It was **reusable**. It followed **design patterns**.

It was also **completely unnecessary**.

---

## The Moment of Clarity

One day, I was explaining PyPLECS to a new contributor:

**Them**: "So to run a simulation with different voltage, I create a variant file?"

**Me**: "Yes! The system generates a new .plecs file in a subdirectory."

**Them**: "Why not just pass the parameter to PLECS?"

**Me**: "Well, the abstraction layer..."

**Them**: "But PLECS already supports parameter passing, right?"

Silence.

**Me**: "...yes."

**Them**: "So why create files?"

And there it was. The question I should have asked **before** writing 68 lines of abstraction:

**Why does this abstraction exist?**

---

## What PLECS Actually Does

Here's what I didn't know (or forgot) when building my abstraction:

PLECS has a concept called **ModelVars**—runtime parameters you can set **without modifying the file**.

```python
# What I should have done from the start
results = plecs.simulate("model.plecs", {"Vi": 12.0})

# What my abstraction forced users to do
model = GenericConverterPlecsMdl("model.plecs")
variant_model = generate_variant_plecs_mdl(model, "01", {"Vi": 12.0})
server = PlecsServer(variant_model.folder, variant_model.simulation_name)
results = server.run_sim_with_datastream()
```

My abstraction turned **one line into six lines**.

And those six lines:
- Were slower (file I/O overhead)
- Were error-prone (directory creation, cleanup)
- Cluttered the workspace (`data/01/`, `data/02/`, ...)
- Confused users ("Why are there so many .plecs files?")

All because I abstracted **without understanding what needed abstracting**.

---

## The False Economy

Here's the trap I fell into:

**I thought abstraction was always good.**

We're taught: "Encapsulate! Abstract! DRY! Design patterns!"

But **abstraction has a cost**:
- Cognitive load (users need to learn your abstraction)
- Maintenance burden (more code to maintain)
- Indirection (harder to debug)
- Opportunity cost (time spent building abstractions instead of features)

Abstraction is an **investment**. Like any investment, it should have **ROI**.

My `GenericConverterPlecsMdl` class:
- **Cost**: 68 lines to write, document, test, maintain
- **Benefit**: ??? (replaced functionality that already existed)
- **ROI**: Negative

**That's the false economy of abstraction.**

---

## When Abstraction Becomes Technical Debt

Fast forward to refactoring time. I wanted to delete `GenericConverterPlecsMdl`.

But I couldn't—**too much code depended on it**.

It had metastasized:
- Tests referenced it
- Documentation explained it
- Examples used it
- Other classes inherited from it
- Users' code imported it

Removing it meant:
- Updating 15 test files
- Rewriting documentation
- Breaking user code (breaking change)
- Fixing examples

**The abstraction had become technical debt.**

And the longer it lived, the more expensive it became to remove.

---

## The Refactoring

When I finally deleted it (v1.0.0 release), here's what happened:

**Before** (with abstraction):
```python
buck_mdl = GenericConverterPlecsMdl("simple_buck.plecs")
variant_mdl = generate_variant_plecs_mdl(buck_mdl, "01", {"Vi": 250})
server = PlecsServer(variant_mdl.folder, variant_mdl.simulation_name)
results = server.run_sim_with_datastream()
```

**After** (without abstraction):
```python
with PlecsServer("simple_buck.plecs") as server:
    results = server.simulate({"Vi": 250})
```

**Results**:
- 68 lines deleted
- API simplified
- Performance improved (no file I/O)
- Users happy (easier to understand)
- Future maintenance reduced

**Everyone won when the abstraction died.**

---

## Lessons I Learned

### 1. Abstraction Should Add Value, Not Complexity

Before creating an abstraction, ask:
- What problem does this solve?
- Does an existing solution work?
- What's the cost vs. benefit?

If you can't articulate clear value, **don't abstract**.

### 2. The Best Abstraction Is Often No Abstraction

Python's `pathlib` is better than my custom path wrapper.

PLECS' native ModelVars are better than my file generation.

**Use what exists before building your own.**

### 3. Abstraction Has Momentum

Once code depends on an abstraction, it's hard to remove.

**Start simple**. Add abstraction later if genuinely needed.

It's easier to add abstraction than to remove it.

### 4. "Clever" Code Is Future Technical Debt

My file generation was "clever." Colleagues praised it.

But cleverness without purpose is just **complexity waiting to bite you**.

**Simple beats clever**, every time.

---

## The Principle I Now Follow

**Resist abstraction by default.**

When tempted to create a class, function, or pattern, ask:
1. Can I solve this without abstraction?
2. If not, what's the **smallest** abstraction that works?
3. What's the exit strategy if this abstraction becomes debt?

Most of the time, **the simplest solution is the right one**.

---

## Your Turn

Have you ever created an abstraction you later regretted?

What made you realize it was the wrong choice?

**Drop a comment**—I'm genuinely curious what abstractions haunt your codebases.

---

**Next in series**: "The 5x Performance Gift Hiding in Plain Sight" (how PLECS native batch API beat my custom thread pool)

---

#SoftwareEngineering #Abstraction #TechnicalDebt #CodeRefactoring #Python #CleanCode

---

**P.S.** The hardest part of refactoring isn't writing code. It's **deleting code you're emotionally attached to**.

That `GenericConverterPlecsMdl` class took me a week to build. Deleting it took 30 seconds.

**Best 30 seconds I ever spent.**

---

**Meta**: 1,087 words, ~5-minute read
**Hook**: Personal realization, relatable mistake
**CTA**: Share their abstraction regrets
**Series continuity**: References previous article, teases next
