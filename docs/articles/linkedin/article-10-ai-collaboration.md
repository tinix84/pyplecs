# Article 10: I Built This With AI. Here's What That Really Means.

**LinkedIn Post** (1,178 words)
**Theme**: Human + AI collaboration, authorship, and the future of development
**Tone**: Honest, reflective, forward-looking

---

I need to tell you something about this entire article series.

And about PyPLECS v1.0.0.

**I didn't build it alone.**

I built it in collaboration with Claude Code—an AI coding assistant from Anthropic.

Not "I used AI to write boilerplate."
Not "AI helped with some refactoring."

**AI was my pair programming partner for 6 weeks of intensive development.**

This final article is the honest, unfiltered truth about:
- What AI was genuinely good at
- Where AI fell flat
- Where human judgment was critical
- What "AI-assisted development" actually means
- The uncomfortable questions about authorship

**Full transparency. No marketing BS.**

---

## What AI Was Genuinely Good At

### 1. Code Generation from Specifications

**Me**: "I need a priority queue implementation. Tasks should be ordered by priority (CRITICAL=0, HIGH=1, NORMAL=2, LOW=3), with ties broken by submission time (FIFO). Use Python dataclasses and heapq."

**Claude Code**:
```python
import heapq
from dataclasses import dataclass, field
from enum import IntEnum
import time

class TaskPriority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3

@dataclass(order=True)
class SimulationTask:
    priority: int
    created_at: float = field(default_factory=time.time)
    request: Any = field(compare=False)
    task_id: str = field(compare=False)

    def __lt__(self, other):
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.created_at < other.created_at
```

**Result**: Perfect. First try. No bugs.

**Human value-add**: The specification. AI executed flawlessly.

---

### 2. Refactoring with Context

**Me**: "This orchestrator uses custom threading. Refactor to use PLECS native batch API. Preserve priority queueing and retry logic."

AI read:
- The existing orchestrator code (450 lines)
- PLECS XML-RPC documentation
- My architecture notes

**Claude Code generated**:
- New `BatchSimulationExecutor` class
- Integration with priority queue
- Preserved all retry/callback logic
- Updated tests

**Time saved**: ~6 hours of mechanical refactoring

**Human value-add**: Architectural decision (use native API). AI handled implementation.

---

### 3. Test Generation

**Me**: "Generate pytest-benchmark tests validating 3-5× speedup claim. Mock PLECS to simulate 4-core parallelization."

**Claude Code**:
```python
@pytest.mark.benchmark
def test_batch_vs_sequential_speedup(self):
    # ... complete test with mocks, assertions, statistical validation
```

**Result**: Test worked first try. Caught performance regression in later commit.

**Human value-add**: Knowing what to test. AI wrote the test.

---

## Where AI Fell Flat

### 1. Architecture Decisions

**Me**: "Should we use file-based variant generation or PLECS native ModelVars?"

**Claude Code**: "Both approaches are valid. File-based provides isolation. ModelVars is simpler. Your choice."

**Useless.** This is the decision that mattered most.

**Human decision**: Delete 1,581 lines, use ModelVars. AI couldn't make this call.

**Lesson**: AI doesn't have product intuition or strategic vision.

---

### 2. Performance Intuition

**Me**: "This cache implementation uses pickle. Is that fast enough?"

**Claude Code**: "Pickle is generally fast. Consider alternatives like parquet or HDF5 for large datasets."

**Human testing**: Pickle was 40× slower than Parquet for typical use case.

**Human decision**: Switch to Parquet. AI suggested it as "alternative," not "mandatory."

**Lesson**: AI doesn't have performance intuition for specific domains.

---

### 3. User Experience Design

**Me**: "Design the REST API endpoints for simulation submission."

**Claude Code** (first attempt):
```python
@app.post("/simulate")
def simulate(model: str, params: dict):
    # Run simulation synchronously (blocks)
    return results
```

**Problem**: Synchronous. Blocks for minutes. Terrible UX.

**Human redesign**:
```python
@app.post("/api/simulations")
async def submit_simulation(request: SimulationRequest):
    # Return immediately with task_id
    # Simulation runs asynchronously
    return {"task_id": task_id, "status": "QUEUED"}
```

**Lesson**: AI defaults to simplest solution. Doesn't consider operational UX.

---

## Where Human Judgment Was Critical

### 1. Deciding What to Delete

AI suggested optimizations. **AI never suggested deletion.**

**The decision to delete 1,581 lines** (39% of codebase) was 100% human.

AI can't say: "This entire subsystem is redundant. Delete it."

**Only humans have the courage to kill code.**

---

### 2. Breaking Changes

**Me**: "Should we deprecate GenericConverterPlecsMdl or remove it immediately?"

**Claude Code**: "Deprecation is safer for users."

**Human decision**: Remove immediately in v1.0.0, but write comprehensive MIGRATION.md.

**Reasoning**: Users upgrading to v1.0.0 expect breaking changes. Ship the pain once, not gradually.

**Lesson**: AI is risk-averse. Humans make bold calls.

---

### 3. Prioritization

AI treated all tasks equally.

**Human decisions**:
- Priority queue > batch optimization > web UI
- MIGRATION.md > tutorial examples
- Performance testing > integration testing

**AI can't prioritize strategically.** It executes what you ask.

---

## The Honest Workflow

Here's what "AI-assisted development" actually looked like:

```
┌─────────────────────────────────────────┐
│   Human: Strategy & Architecture       │
│   - What to build                       │
│   - How to structure it                 │
│   - What to delete                      │
│   - Breaking change decisions           │
└──────────────┬──────────────────────────┘
               │
               ∨
┌─────────────────────────────────────────┐
│   AI: Implementation                    │
│   - Generate code from specs            │
│   - Write tests                         │
│   - Refactor existing code              │
│   - Generate documentation              │
└──────────────┬──────────────────────────┘
               │
               ∨
┌─────────────────────────────────────────┐
│   Human: Review & Refinement            │
│   - Verify correctness                  │
│   - Check edge cases                    │
│   - Performance testing                 │
│   - UX polish                           │
└──────────────┬──────────────────────────┘
               │
               ∨
┌─────────────────────────────────────────┐
│   Human: Integration & Validation       │
│   - Does it solve the real problem?     │
│   - Are users better off?               │
│   - Is the API intuitive?               │
│   - Should we ship this?                │
└─────────────────────────────────────────┘
```

**Human**: Strategy, decisions, taste, validation
**AI**: Execution, implementation, mechanical refactoring

**Neither is sufficient alone.**

---

## The Uncomfortable Question: Authorship

Who "wrote" PyPLECS v1.0.0?

**Lines of code generated by AI**: ~60%
**Lines of code written by human**: ~40%

But:

**Architectural decisions**: 100% human
**Strategic vision**: 100% human
**Performance validation**: 100% human
**UX design**: 100% human
**Deletion decisions**: 100% human

**So who's the author?**

### My Answer

**I am the author. AI is my tool.**

Just like:
- A writer uses spell-check but claims authorship
- An architect uses CAD software but claims the design
- A photographer uses Photoshop but claims the image

**The tool doesn't make the strategic choices.**

AI wrote code. **I decided what code to write, what to delete, and whether to ship it.**

---

## The Economics: Time and Quality

**Total development time**: 6 weeks (240 hours)

**Estimated time without AI**: 14 weeks (560 hours)

**Time saved**: 320 hours (~57% reduction)

**But did quality suffer?**

| Metric | With AI | Estimated Without AI |
|--------|---------|---------------------|
| Test coverage | 87% | 75% (I hate writing tests) |
| Documentation quality | Excellent | Good (I hate docs) |
| Code consistency | Very high | Medium (copy-paste errors) |
| Performance | 5× speedup validated | Same (decisions mine) |
| Architecture quality | Same | Same (decisions mine) |

**AI didn't reduce quality. It improved it.**

Why? AI is tireless at:
- Writing tests (I get bored)
- Writing docs (I get impatient)
- Mechanical refactoring (I make typos)

**AI freed me to focus on strategy, not mechanics.**

---

## What Coding Means in 2026

In 1990: Coding = typing syntax
In 2010: Coding = problem-solving + syntax
In 2026: **Coding = problem-solving + AI orchestration**

**The skill isn't typing code anymore.**

The skill is:
- **Knowing what to build** (product sense)
- **Knowing how to structure it** (architecture)
- **Knowing what's good enough** (taste)
- **Knowing what to delete** (courage)
- **Guiding AI to execute your vision** (prompt engineering)

**Syntax is table stakes. Vision is the differentiator.**

---

## Predictions for 2027

**What I think will happen**:

1. **"AI wrote most of the code"** becomes normal
   - Like "I used Stack Overflow" today
   - No longer worth mentioning

2. **Code reviews focus on architecture, not syntax**
   - "Why this approach?" not "Missing semicolon"
   - Strategic review, not mechanical review

3. **Junior developers start with architecture**
   - Traditional path: syntax → patterns → architecture
   - AI path: **architecture → AI execution → refinement**
   - Faster progression to senior skills

4. **Documentation becomes mandatory**
   - AI needs context to generate correct code
   - Good docs = better AI assistance
   - Documentation ROI increases

5. **"Prompt engineering" becomes "software specification"**
   - Precise specifications = better AI output
   - Writing clear specs becomes core skill

---

## The Big Lesson

**Building PyPLECS with AI taught me**:

AI is a force multiplier, not a replacement.

**I still made every decision that mattered:**
- What to build
- What to delete
- What to ship
- What quality standard to hold

AI made me **faster**. It didn't make me **unnecessary**.

**The future of development isn't human OR AI.**

**It's human AND AI.**

And the humans who learn to leverage AI effectively will build 10× more than those who don't.

---

## Your Turn

Have you built something significant with AI assistance?

What did AI do well? Where did you have to step in?

**Drop a comment**—I want to hear your real experiences, not marketing fluff.

---

**End of series.** Thank you for following along.

If you found value in this series, please share it with someone who'd benefit.

---

#AI #SoftwareEngineering #Productivity #Future #Collaboration #Development #ClaudeCode #Python

---

**P.S.** Some will say "AI wrote this article too, didn't it?"

**Yes, partially.** I wrote the outline, key points, and examples. AI helped with structure and phrasing.

**I claim authorship because I made every strategic decision.**

And I'm comfortable with that.

---

**Meta**: 1,178 words, ~6-minute read
**Hook**: Honest admission of AI collaboration
**Lesson**: Human + AI collaboration, authorship, and the future
**CTA**: Share real AI collaboration experiences
**Series finale**: Closes 10-article arc with reflection
