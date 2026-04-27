# PLECS-Expert Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `plecs-expert` skill (Claude Code skill + `/plecs` slash command + stdio MCP server) backed by an offline reference of PLECS docs (verbatim factual tables + caveman-style rewritten prose) and live introspection of `pyplecs` modules.

**Architecture:** Single source of truth at `pyplecs/.claude/skills/plecs-expert/references/` is consumed three ways: by Claude Code via the `Skill` tool, by `/plecs` via a slash command stub, and by external AI clients via `pyplecs-mcp` over stdio. MCP tools compose answers from the offline reference (Layer A) and live `pyplecs` introspection (Layer B), preferring the wrapped/typed source when both are available.

**Tech Stack:** Python 3.8+ (project floor), `mcp` SDK (stdio transport), `httpx` for refresh-tooling scrapes, `BeautifulSoup4` for HTML parsing in `sync_tables.py`. `ruff` for lint; `pytest` for tests. No new runtime dependencies for `pyplecs-mcp` itself beyond `mcp`.

**Branch:** `feature/plecs-expert-skill` (already created; spec at `093657b`).

**Spec reference:** [`docs/superpowers/specs/2026-04-27-plecs-expert-skill-design.md`](../specs/2026-04-27-plecs-expert-skill-design.md).

---

## File Structure

| File | Purpose | Phase |
|------|---------|-------|
| `pyplecs/.claude/skills/plecs-expert/SKILL.md` | Frontmatter + body (≤ 4 KB), routing + composition rules | 1 |
| `pyplecs/.claude/skills/plecs-expert/style/caveman.md` | Style rules + banned-words list (test data source) | 1 |
| `pyplecs/.claude/skills/plecs-expert/LICENSE-NOTES.md` | Per-file verbatim/rewritten classification | 1 |
| `pyplecs/.claude/skills/plecs-expert/manifest.json` | Source URL → content hash table | 2 |
| `pyplecs/.claude/skills/plecs-expert/tools/sync_tables.py` | Scrape + extract verbatim tables | 2 |
| `pyplecs/.claude/skills/plecs-expert/tools/check_drift.py` | Diff manifest hashes + introspection diff | 2 |
| `pyplecs/.claude/skills/plecs-expert/tools/REFRESH.md` | Human refresh procedure | 2 |
| `pyplecs/.claude/skills/plecs-expert/references/components/electrical-passive.md` | R, L, C, mutual-L, transformer | 4 |
| `pyplecs/.claude/skills/plecs-expert/references/components/electrical-sources.md` | V, I sources, signal sources | 4 |
| `pyplecs/.claude/skills/plecs-expert/references/components/electrical-switches.md` | MOSFET, IGBT, diode, ideal switch | 4 |
| `pyplecs/.claude/skills/plecs-expert/references/components/electrical-meters.md` | Voltmeter, ammeter, scope, probe | 4 |
| `pyplecs/.claude/skills/plecs-expert/references/components/magnetic.md` | Permeance, MMF source, flux meter | 4 |
| `pyplecs/.claude/skills/plecs-expert/references/components/thermal.md` | Heat sink, thermal capacitor, thermal probe | 4 |
| `pyplecs/.claude/skills/plecs-expert/references/components/control.md` | PI, PID, transfer fn, state machine | 4 |
| `pyplecs/.claude/skills/plecs-expert/references/components/system.md` | Subsystem, configurable subsystem, mask | 4 |
| `pyplecs/.claude/skills/plecs-expert/references/rpc-api.md` | XML-RPC function table | 4 |
| `pyplecs/.claude/skills/plecs-expert/references/plecs-xml-grammar.md` | `.plecs` schematic XML grammar | 4 |
| `pyplecs/.claude/skills/plecs-expert/references/solver.md` | Solver types, params, tolerances | 4 |
| `pyplecs/.claude/skills/plecs-expert/references/codegen.md` | PLECS Coder, target hooks | 4 |
| `pyplecs/.claude/skills/plecs-expert/references/cscript.md` | C-Script block API | 4 |
| `pyplecs/.claude/skills/plecs-expert/references/url-index.md` | Topic → docs.plexim.com URL fallback | 5 |
| `pyplecs/.claude/commands/plecs.md` | `/plecs` slash command stub | 6 |
| `pyplecs/pyplecs/mcp/server.py` | MCP stdio server boilerplate | 7 |
| `pyplecs/pyplecs/mcp/plecs_tools.py` | 8 read-only MCP tool implementations | 7 |
| `pyplecs/pyplecs/mcp/__init__.py` | Wires `create_mcp_server` + `main`; entry point target | 7 |
| `pyplecs/pyproject.toml` | Add `pyplecs-mcp` script + `mcp` extra | 7 |
| `pyplecs/tests/test_plecs_expert.py` | 8 tests per spec | 1, 6, 7 |
| `pyplecs/.claude/hooks/pre_push_lint.py` | Add `tests/test_plecs_expert.py` to platform-independent set | 1 |

---

## Phase 1 — Test infrastructure + skill skeleton

### Task 1: Create skill skeleton + size-budget test

**Files:**
- Create: `pyplecs/.claude/skills/plecs-expert/SKILL.md`
- Create: `pyplecs/.claude/skills/plecs-expert/style/caveman.md` (placeholder)
- Create: `pyplecs/.claude/skills/plecs-expert/LICENSE-NOTES.md` (placeholder)
- Create: `pyplecs/.claude/skills/plecs-expert/references/.gitkeep`
- Create: `pyplecs/.claude/skills/plecs-expert/references/components/.gitkeep`
- Create: `pyplecs/tests/test_plecs_expert.py`

- [ ] **Step 1: Write the failing test**

`pyplecs/tests/test_plecs_expert.py`:
```python
"""Tests for the plecs-expert skill (file layout, content, MCP wiring).

Platform-independent: no PLECS instance, no network, no subprocess.
"""
from __future__ import annotations

from pathlib import Path

SKILL_ROOT = Path(__file__).parent.parent / ".claude" / "skills" / "plecs-expert"


def test_skill_md_under_4kb():
    """SKILL.md body must be lookup-fast; cap at 4 KB."""
    skill_md = SKILL_ROOT / "SKILL.md"
    assert skill_md.exists(), f"missing: {skill_md}"
    size = skill_md.stat().st_size
    assert size <= 4096, f"SKILL.md is {size} bytes (limit 4096)"
```

- [ ] **Step 2: Run test, confirm it fails**

```bash
pytest tests/test_plecs_expert.py::test_skill_md_under_4kb -v
```

Expected: `FAILED` with `AssertionError: missing: ...SKILL.md`.

- [ ] **Step 3: Write SKILL.md (minimal compliant body)**

`pyplecs/.claude/skills/plecs-expert/SKILL.md`:
```markdown
---
name: plecs-expert
description: PLECS authoring help, .plecs schematic format, XML-RPC API, and SPICE-mapping reference. Use when answering "how do I X in PLECS", working on the netlist converter, or extending the PlecsServer XML-RPC wrapper.
allowed-tools: Read, Grep, Glob, WebFetch, Bash
---

# PLECS Expert

Lookup-first PLECS reference grounded in docs.plexim.com. Two layers:

- **Layer A — offline docs**: `references/`. Verbatim factual tables + caveman prose.
- **Layer B — pyplecs code**: `pyplecs.plecs_components`, `pyplecs.pyplecs.PlecsServer`. Live introspection.

## Routing

| Topic | File |
|-------|------|
| Electrical passives (R, L, C, transformer) | `references/components/electrical-passive.md` |
| Sources (V, I, signal) | `references/components/electrical-sources.md` |
| Switches (MOSFET, IGBT, diode) | `references/components/electrical-switches.md` |
| Meters & scopes | `references/components/electrical-meters.md` |
| Magnetic blocks | `references/components/magnetic.md` |
| Thermal blocks | `references/components/thermal.md` |
| Control library | `references/components/control.md` |
| Subsystems & masks | `references/components/system.md` |
| XML-RPC API | `references/rpc-api.md` |
| `.plecs` XML grammar | `references/plecs-xml-grammar.md` |
| Solver | `references/solver.md` |
| Codegen (PLECS Coder) | `references/codegen.md` |
| C-Script block | `references/cscript.md` |
| Long-tail topics | `references/url-index.md` (then WebFetch the listed URL) |

## Composition rule

For component or RPC questions, check Layer B first. If a `*PlecsMdl` class exists in `pyplecs.plecs_components`, cite the wrapper. If a method exists on `PlecsServer`, cite it. Else cite Layer A. Else WebFetch from `references/url-index.md`.

## Citation rule

Every answer cites a `references/*` path or a `docs.plexim.com` URL. No ungrounded claims.

## Style

Generated prose follows `style/caveman.md`: fragments OK, drop articles/hedging/filler, pattern `[thing] [action] [reason]. [next step].`.

## Boundary

This skill does not cover: PLECS RT Box (separate future skill), license/purchasing, third-party libraries.
```

- [ ] **Step 4: Add second test — references_no_dead_links walker (vacuously passes)**

Append to `pyplecs/tests/test_plecs_expert.py`:
```python
import re

MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _walk_md(root: Path):
    return sorted(p for p in root.rglob("*.md"))


def test_references_no_dead_links():
    """Every relative link in references/*.md resolves to an existing file."""
    root = SKILL_ROOT / "references"
    if not root.exists():
        return  # phase 1 vacuous pass
    failures: list[str] = []
    for md in _walk_md(root):
        text = md.read_text(encoding="utf-8")
        for target in MD_LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "#")):
                continue
            target_path = (md.parent / target.split("#", 1)[0]).resolve()
            if not target_path.exists():
                failures.append(f"{md}: dead link → {target}")
    assert not failures, "\n".join(failures)
```

- [ ] **Step 5: Add third test — license_notes_complete (vacuously passes)**

Append:
```python
def test_license_notes_complete():
    """Every references/*.md is classified in LICENSE-NOTES.md."""
    notes = SKILL_ROOT / "LICENSE-NOTES.md"
    refs = SKILL_ROOT / "references"
    if not refs.exists() or not notes.exists():
        return  # phase 1 vacuous pass
    notes_text = notes.read_text(encoding="utf-8")
    failures: list[str] = []
    for md in _walk_md(refs):
        rel = md.relative_to(SKILL_ROOT).as_posix()
        if rel not in notes_text:
            failures.append(f"{rel} not listed in LICENSE-NOTES.md")
    assert not failures, "\n".join(failures)
```

- [ ] **Step 6: Add fourth test — url_index_resolvable (vacuously passes)**

Append:
```python
URL_RE = re.compile(r"https?://[^\s)>\]]+")


def test_url_index_resolvable():
    """URLs in url-index.md are syntactically valid (no fetch)."""
    idx = SKILL_ROOT / "references" / "url-index.md"
    if not idx.exists():
        return  # phase 1 vacuous pass
    failures: list[str] = []
    for url in URL_RE.findall(idx.read_text(encoding="utf-8")):
        if "docs.plexim.com" not in url:
            continue
        if " " in url or url.endswith((".",  ",", ";")):
            failures.append(f"malformed URL: {url}")
    assert not failures, "\n".join(failures)
```

- [ ] **Step 7: Write minimal LICENSE-NOTES.md and caveman.md placeholders**

`pyplecs/.claude/skills/plecs-expert/LICENSE-NOTES.md`:
```markdown
# License Notes

`docs.plexim.com` content is Plexim's proprietary documentation. This skill mirrors only **factual tables** verbatim (parameter names, defaults, units, RPC signatures, XML element grammar — facts not copyrightable) and rewrites all **prose** in our own caveman-style words.

| File | Source URL | Verbatim sections | Rewritten sections |
|------|-----------|-------------------|---------------------|
```

`pyplecs/.claude/skills/plecs-expert/style/caveman.md`:
```markdown
# Caveman Style (placeholder — populated in Task 2)

See https://github.com/juliusbrussee/caveman.
```

- [ ] **Step 8: Run all four tests, confirm they pass**

```bash
pytest tests/test_plecs_expert.py -v
```

Expected: 4 passed. The dead-links / license-notes / url-index tests pass vacuously because `references/` is empty.

- [ ] **Step 9: Add `tests/test_plecs_expert.py` to the pre-push hook's platform-independent set**

In `.claude/hooks/pre_push_lint.py`, modify the `PYTEST_FILES` list:
```python
PYTEST_FILES = [
    "tests/test_installer.py",
    "tests/test_entrypoint.py",
    "tests/test_install_full.py",
    "tests/test_abc_contract.py",
    "tests/test_plecs_expert.py",
]
```

Also update `CLAUDE.md`'s "Build & Test" block to include the new file in the platform-independent subset command:
```bash
pytest -q tests/test_installer.py tests/test_entrypoint.py tests/test_install_full.py tests/test_abc_contract.py tests/test_plecs_expert.py
```

- [ ] **Step 10: Run ruff and the full subset to confirm clean**

```bash
ruff check .
pytest -q tests/test_installer.py tests/test_entrypoint.py tests/test_install_full.py tests/test_abc_contract.py tests/test_plecs_expert.py
```

Expected: both green.

- [ ] **Step 11: Commit**

```bash
git add .claude/skills/plecs-expert/SKILL.md \
        .claude/skills/plecs-expert/style/caveman.md \
        .claude/skills/plecs-expert/LICENSE-NOTES.md \
        .claude/skills/plecs-expert/references \
        tests/test_plecs_expert.py \
        .claude/hooks/pre_push_lint.py \
        CLAUDE.md
git commit -m "feat(skill): bootstrap plecs-expert skill skeleton + tests"
```

---

### Task 2: Style rules — `caveman.md` + compliance test

**Files:**
- Modify: `pyplecs/.claude/skills/plecs-expert/style/caveman.md`
- Modify: `pyplecs/tests/test_plecs_expert.py` (add `test_caveman_compliance`)

- [ ] **Step 1: Write the failing test**

Append to `pyplecs/tests/test_plecs_expert.py`:
```python
BANNED_WORDS = {
    # caveman methodology — drop articles, fillers, hedging.
    # We can't strip articles globally without false positives, so the
    # banned set is just fillers + hedges. See style/caveman.md.
    "basically",
    "really",
    "actually",
    "essentially",
    "obviously",
    "simply",
    "just",     # ambiguous in code contexts; allow override via marker
    "very",
    "quite",
    "perhaps",
    "maybe",
}

ALLOW_MARKER = "<!-- caveman:allow -->"


def _strip_code_blocks(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def test_caveman_compliance():
    """Rewritten prose in references/*.md must avoid banned filler words."""
    refs = SKILL_ROOT / "references"
    if not refs.exists():
        return
    failures: list[str] = []
    for md in _walk_md(refs):
        text = md.read_text(encoding="utf-8")
        if ALLOW_MARKER in text:
            continue
        prose = _strip_code_blocks(text)
        for line_no, line in enumerate(prose.splitlines(), start=1):
            tokens = re.findall(r"\b\w+\b", line.lower())
            for word in BANNED_WORDS:
                if word in tokens:
                    failures.append(f"{md.relative_to(SKILL_ROOT)}:{line_no} banned: {word}")
    assert not failures, "\n".join(failures)
```

- [ ] **Step 2: Run test, confirm it passes (vacuously, references/ still empty)**

```bash
pytest tests/test_plecs_expert.py::test_caveman_compliance -v
```

Expected: PASS (no files to scan).

- [ ] **Step 3: Write the real `caveman.md`**

Replace `pyplecs/.claude/skills/plecs-expert/style/caveman.md`:
```markdown
# Caveman Style — Prose Rules for plecs-expert

Reference: https://github.com/juliusbrussee/caveman

## Core rule

Drop: articles, filler, hedging, pleasantries.
Fragments OK.
Pattern: `[thing] [action] [reason]. [next step].`
Code blocks: never modified — kept exactly as authored.

## Banned words (enforced by `tests/test_plecs_expert.py::test_caveman_compliance`)

`basically`, `really`, `actually`, `essentially`, `obviously`, `simply`, `just`, `very`, `quite`, `perhaps`, `maybe`.

## Allow marker

If a banned word is unavoidable (rare), include the literal marker `<!-- caveman:allow -->` anywhere in the file. The whole file is then exempt. Use sparingly; comment why.

## Examples

**Bad:**
> The Inductor block is basically just a passive component that really stores energy in a magnetic field. You can simply set its initial current via the IL_init parameter.

**Good (caveman):**
> Inductor block. Passive. Stores energy in magnetic field. Param `IL_init` sets initial current.

**Bad:**
> Note that the MOSFET model is actually quite detailed and includes both conduction and switching losses if you configure it properly.

**Good (caveman):**
> MOSFET model. Conduction + switching loss. Enable via `model_level=2`.

## What's verbatim, what's rewritten

| Section type | Posture |
|--------------|---------|
| Parameter tables | Verbatim (facts) |
| RPC function signatures | Verbatim (facts) |
| XML element grammar | Verbatim (facts) |
| Defaults & units | Verbatim (facts) |
| Explanatory prose | Rewritten in caveman style |
| Examples (our own) | Caveman style |

## Style guide for tables

Tables are facts. Keep verbatim from docs.plexim.com. Add a `Source:` line below each table pointing to the source URL.
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/test_plecs_expert.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/plecs-expert/style/caveman.md tests/test_plecs_expert.py
git commit -m "feat(skill): caveman style rules + compliance test"
```

---

## Phase 2 — Refresh tooling

### Task 3: Manifest schema + initial seed

**Files:**
- Create: `pyplecs/.claude/skills/plecs-expert/manifest.json`

- [ ] **Step 1: Write `manifest.json` with URL-to-file mapping (no hashes yet)**

`pyplecs/.claude/skills/plecs-expert/manifest.json`:
```json
{
  "plecs_version_pinned": "4.7",
  "files": {
    "references/components/electrical-passive.md": {
      "source_urls": [
        "https://docs.plexim.com/plecs/latest/UserManual/Electrical/Resistor.html",
        "https://docs.plexim.com/plecs/latest/UserManual/Electrical/Inductor.html",
        "https://docs.plexim.com/plecs/latest/UserManual/Electrical/Capacitor.html",
        "https://docs.plexim.com/plecs/latest/UserManual/Electrical/Transformer.html"
      ],
      "table_section_hashes": {},
      "prose_section_hashes": {}
    },
    "references/components/electrical-sources.md": {
      "source_urls": [
        "https://docs.plexim.com/plecs/latest/UserManual/Electrical/VoltageSourceAC.html",
        "https://docs.plexim.com/plecs/latest/UserManual/Electrical/VoltageSourceDC.html",
        "https://docs.plexim.com/plecs/latest/UserManual/Electrical/VoltageSourceControlled.html",
        "https://docs.plexim.com/plecs/latest/UserManual/Electrical/CurrentSourceControlled.html"
      ],
      "table_section_hashes": {},
      "prose_section_hashes": {}
    },
    "references/components/electrical-switches.md": {
      "source_urls": [
        "https://docs.plexim.com/plecs/latest/UserManual/Electrical/Mosfet.html",
        "https://docs.plexim.com/plecs/latest/UserManual/Electrical/Igbt.html",
        "https://docs.plexim.com/plecs/latest/UserManual/Electrical/Diode.html",
        "https://docs.plexim.com/plecs/latest/UserManual/Electrical/SwitchIdeal.html"
      ],
      "table_section_hashes": {},
      "prose_section_hashes": {}
    },
    "references/components/electrical-meters.md": {
      "source_urls": [
        "https://docs.plexim.com/plecs/latest/UserManual/Electrical/Voltmeter.html",
        "https://docs.plexim.com/plecs/latest/UserManual/Electrical/Ammeter.html",
        "https://docs.plexim.com/plecs/latest/UserManual/System/Scope.html"
      ],
      "table_section_hashes": {},
      "prose_section_hashes": {}
    },
    "references/components/magnetic.md": {
      "source_urls": [
        "https://docs.plexim.com/plecs/latest/UserManual/Magnetic/Permeance.html",
        "https://docs.plexim.com/plecs/latest/UserManual/Magnetic/MmfSource.html",
        "https://docs.plexim.com/plecs/latest/UserManual/Magnetic/FluxMeter.html"
      ],
      "table_section_hashes": {},
      "prose_section_hashes": {}
    },
    "references/components/thermal.md": {
      "source_urls": [
        "https://docs.plexim.com/plecs/latest/UserManual/Thermal/HeatSink.html",
        "https://docs.plexim.com/plecs/latest/UserManual/Thermal/ThermalCapacitor.html",
        "https://docs.plexim.com/plecs/latest/UserManual/Thermal/AmbientTemperature.html"
      ],
      "table_section_hashes": {},
      "prose_section_hashes": {}
    },
    "references/components/control.md": {
      "source_urls": [
        "https://docs.plexim.com/plecs/latest/UserManual/Control/PIController.html",
        "https://docs.plexim.com/plecs/latest/UserManual/Control/TransferFunction.html",
        "https://docs.plexim.com/plecs/latest/UserManual/Control/StateMachine.html"
      ],
      "table_section_hashes": {},
      "prose_section_hashes": {}
    },
    "references/components/system.md": {
      "source_urls": [
        "https://docs.plexim.com/plecs/latest/UserManual/System/Subsystem.html",
        "https://docs.plexim.com/plecs/latest/UserManual/System/ConfigurableSubsystem.html",
        "https://docs.plexim.com/plecs/latest/UserManual/System/Mask.html"
      ],
      "table_section_hashes": {},
      "prose_section_hashes": {}
    },
    "references/rpc-api.md": {
      "source_urls": [
        "https://docs.plexim.com/plecs/latest/UserManual/XmlRpcInterface.html"
      ],
      "table_section_hashes": {},
      "prose_section_hashes": {}
    },
    "references/plecs-xml-grammar.md": {
      "source_urls": [
        "https://docs.plexim.com/plecs/latest/UserManual/PlecsFileFormat.html"
      ],
      "table_section_hashes": {},
      "prose_section_hashes": {}
    },
    "references/solver.md": {
      "source_urls": [
        "https://docs.plexim.com/plecs/latest/UserManual/Simulation/SolverSettings.html"
      ],
      "table_section_hashes": {},
      "prose_section_hashes": {}
    },
    "references/codegen.md": {
      "source_urls": [
        "https://docs.plexim.com/plecs/latest/UserManual/CodeGeneration/Overview.html"
      ],
      "table_section_hashes": {},
      "prose_section_hashes": {}
    },
    "references/cscript.md": {
      "source_urls": [
        "https://docs.plexim.com/plecs/latest/UserManual/CScript.html"
      ],
      "table_section_hashes": {},
      "prose_section_hashes": {}
    }
  }
}
```

> **Note:** The exact URL slugs above are best-effort guesses against the published doc sitemap. The first run of `sync_tables.py` (Task 4) will surface any 404s — fix the manifest then.

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/plecs-expert/manifest.json
git commit -m "feat(skill): add manifest.json with PLECS doc URL mapping"
```

---

### Task 4: `sync_tables.py` — verbatim factual table extractor

**Files:**
- Create: `pyplecs/.claude/skills/plecs-expert/tools/sync_tables.py`

- [ ] **Step 1: Write the script**

`pyplecs/.claude/skills/plecs-expert/tools/sync_tables.py`:
```python
#!/usr/bin/env python3
"""Scrape factual tables from PLECS docs into references/*.md.

Reads URLs from manifest.json. For each URL:
  1. Fetches HTML (httpx).
  2. Extracts <table> elements (BeautifulSoup).
  3. Renders each as a Markdown table.
  4. Writes/updates the verbatim sections of the corresponding references/*.md
     file, preserving any prose between BEGIN/END markers.

Per-section markers are HTML comments:
  <!-- BEGIN VERBATIM TABLE: <slug> -->
  ...table markdown...
  <!-- END VERBATIM TABLE: <slug> -->

Prose between marker pairs is left untouched. Hashes are written to
manifest.json so check_drift.py can detect upstream changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup, Tag

SKILL_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = SKILL_ROOT / "manifest.json"

BEGIN_RE = re.compile(r"<!--\s*BEGIN VERBATIM TABLE:\s*(?P<slug>[^\s-]+)\s*-->")
END_RE = re.compile(r"<!--\s*END VERBATIM TABLE:\s*(?P<slug>[^\s-]+)\s*-->")


def slugify(url: str) -> str:
    return Path(url.rstrip("/")).name.replace(".html", "").lower()


def html_table_to_markdown(table: Tag) -> str:
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |"]
    out.append("| " + " | ".join(["---"] * width) + " |")
    for r in rows[1:]:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def fetch(url: str) -> str:
    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def extract_tables(html: str, url: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    base_slug = slugify(url)
    out: dict[str, str] = {}
    for i, t in enumerate(tables):
        md = html_table_to_markdown(t)
        if md:
            slug = f"{base_slug}-{i}" if i else base_slug
            out[slug] = md
    return out


def replace_section(text: str, slug: str, body: str) -> str:
    begin = f"<!-- BEGIN VERBATIM TABLE: {slug} -->"
    end = f"<!-- END VERBATIM TABLE: {slug} -->"
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
    block = f"{begin}\n\n{body}\n\n{end}"
    if pattern.search(text):
        return pattern.sub(block, text)
    sep = "\n\n" if text and not text.endswith("\n") else "\n"
    return text + sep + block + "\n"


def update_file(target: Path, sections: dict[str, str], source_url: str) -> dict[str, str]:
    target.parent.mkdir(parents=True, exist_ok=True)
    text = target.read_text(encoding="utf-8") if target.exists() else f"# {target.stem}\n"
    hashes: dict[str, str] = {}
    for slug, body in sections.items():
        marked = f"{body}\n\n_Source: {source_url}_"
        text = replace_section(text, slug, marked)
        hashes[slug] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    target.write_text(text, encoding="utf-8")
    return hashes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []
    for rel_file, entry in manifest["files"].items():
        target = SKILL_ROOT / rel_file
        all_hashes: dict[str, str] = {}
        for url in entry["source_urls"]:
            try:
                html = fetch(url)
            except Exception as exc:
                failures.append(f"FETCH {url}: {exc}")
                continue
            sections = extract_tables(html, url)
            if not sections:
                failures.append(f"NO TABLES {url}")
                continue
            if args.dry_run:
                print(f"[dry-run] {rel_file} ← {len(sections)} tables from {url}")
                continue
            new_hashes = update_file(target, sections, url)
            all_hashes.update(new_hashes)
        if not args.dry_run:
            entry["table_section_hashes"] = all_hashes
    if not args.dry_run:
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Add `httpx` and `beautifulsoup4` to dev extras**

In `pyplecs/pyproject.toml`, locate the `[project.optional-dependencies]` block (or `[project] dependencies` block of `dev` extra). Add to the `dev` extra:
```toml
[project.optional-dependencies]
dev = [
    # ... existing entries ...
    "httpx>=0.25",
    "beautifulsoup4>=4.12",
]
```

- [ ] **Step 3: Install + dry-run the script**

```bash
pip install -e ".[dev]"
python .claude/skills/plecs-expert/tools/sync_tables.py --dry-run
```

Expected: prints `[dry-run] ...` lines for every URL. Any FETCH errors mean URLs in `manifest.json` need fixing.

- [ ] **Step 4: Fix any 404s in manifest.json**

If the dry-run reports `FETCH ...: 404`, browse to `https://docs.plexim.com/plecs/latest/` and find the correct page slug. Edit `manifest.json` and re-run dry-run until clean.

- [ ] **Step 5: Run for real (populates table sections in references/*.md)**

```bash
python .claude/skills/plecs-expert/tools/sync_tables.py
```

Expected: every `references/*.md` listed in manifest.json now exists with `<!-- BEGIN VERBATIM TABLE: ... -->` blocks populated; `manifest.json` `table_section_hashes` filled in.

- [ ] **Step 6: Update LICENSE-NOTES.md to list every populated file**

Append a row to the table in `LICENSE-NOTES.md` for each file the script just created/touched, using this template (one row per file):
```markdown
| `references/components/electrical-passive.md` | https://docs.plexim.com/plecs/latest/UserManual/Electrical/ | tables (verbatim) | prose (caveman, hand-authored) |
```

- [ ] **Step 7: Run all tests**

```bash
pytest tests/test_plecs_expert.py -v
```

Expected: all pass. The link-checker may flag missing referenced files; if so, fix or remove the dead link.

- [ ] **Step 8: Commit**

```bash
git add .claude/skills/plecs-expert/manifest.json \
        .claude/skills/plecs-expert/references \
        .claude/skills/plecs-expert/tools/sync_tables.py \
        .claude/skills/plecs-expert/LICENSE-NOTES.md \
        pyproject.toml
git commit -m "feat(skill): sync_tables.py + initial verbatim table population"
```

---

### Task 5: `check_drift.py` — drift detector + REFRESH.md

**Files:**
- Create: `pyplecs/.claude/skills/plecs-expert/tools/check_drift.py`
- Create: `pyplecs/.claude/skills/plecs-expert/tools/REFRESH.md`

- [ ] **Step 1: Write `check_drift.py`**

`pyplecs/.claude/skills/plecs-expert/tools/check_drift.py`:
```python
#!/usr/bin/env python3
"""Detect drift between manifest hashes and current docs / pyplecs surface.

Two checks:

1. **Docs drift**: re-fetch each URL in manifest.json, hash extracted tables,
   compare to stored hashes. Report which references/*.md need a sync.

2. **PyPLECS drift**: introspect `pyplecs.plecs_components` and
   `pyplecs.pyplecs.PlecsServer`. Diff against the snapshot stored under
   manifest.json's `pyplecs_snapshot` key. Report wrappers added/removed and
   RPC methods added/removed.

Output is a Markdown report on stdout. Exit code: 0 if no drift, 1 otherwise.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

SKILL_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = SKILL_ROOT / "manifest.json"

# Reuse extraction logic from sync_tables to keep hashes consistent
sys.path.insert(0, str(SKILL_ROOT / "tools"))
from sync_tables import extract_tables, fetch  # noqa: E402


def docs_drift(manifest: dict) -> list[str]:
    issues: list[str] = []
    for rel_file, entry in manifest["files"].items():
        stored = entry.get("table_section_hashes", {})
        for url in entry["source_urls"]:
            try:
                html = fetch(url)
            except Exception as exc:
                issues.append(f"- FETCH FAILED `{rel_file}` ← {url}: {exc}")
                continue
            for slug, body in extract_tables(html, url).items():
                h = hashlib.sha256(body.encode("utf-8")).hexdigest()
                if stored.get(slug) != h:
                    issues.append(f"- DRIFT `{rel_file}` table `{slug}` (source: {url})")
    return issues


def pyplecs_snapshot() -> dict:
    """Live introspection of pyplecs surface."""
    import pyplecs.plecs_components as comps
    from pyplecs.pyplecs import PlecsServer

    wrappers = sorted(
        n for n, obj in inspect.getmembers(comps, inspect.isclass)
        if obj.__module__ == comps.__name__
    )
    rpc_methods = sorted(
        n for n, _ in inspect.getmembers(PlecsServer, predicate=inspect.isfunction)
        if not n.startswith("_")
    )
    return {"wrappers": wrappers, "rpc_methods": rpc_methods}


def pyplecs_drift(manifest: dict) -> list[str]:
    current = pyplecs_snapshot()
    stored = manifest.get("pyplecs_snapshot", {"wrappers": [], "rpc_methods": []})
    issues: list[str] = []
    for kind in ("wrappers", "rpc_methods"):
        added = set(current[kind]) - set(stored[kind])
        removed = set(stored[kind]) - set(current[kind])
        for name in sorted(added):
            issues.append(f"- ADDED {kind}: `{name}` — update `references/` wrapped/not-wrapped status")
        for name in sorted(removed):
            issues.append(f"- REMOVED {kind}: `{name}` — was wrapped, now isn't; update references/")
    return issues


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    docs = docs_drift(manifest)
    pyp = pyplecs_drift(manifest)
    print("# Drift Report\n")
    print("## Docs drift\n")
    print("\n".join(docs) if docs else "_no docs drift_")
    print("\n## PyPLECS drift\n")
    print("\n".join(pyp) if pyp else "_no pyplecs drift_")
    return 1 if (docs or pyp) else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Snapshot current pyplecs surface into manifest.json**

Add a top-level `pyplecs_snapshot` key to `manifest.json`. Generate it by running:
```bash
python -c "
import json, sys
sys.path.insert(0, '.claude/skills/plecs-expert/tools')
from check_drift import pyplecs_snapshot
m = json.load(open('.claude/skills/plecs-expert/manifest.json'))
m['pyplecs_snapshot'] = pyplecs_snapshot()
json.dump(m, open('.claude/skills/plecs-expert/manifest.json', 'w'), indent=2)
print(m['pyplecs_snapshot'])
"
```

Expected: prints a dict with `wrappers` (e.g. `MosfetWithDiodePlecsMdl`, `ResistorPlecsMdl`, ...) and `rpc_methods` (`PlecsServer` public methods).

- [ ] **Step 3: Run `check_drift.py` — confirm clean baseline**

```bash
python .claude/skills/plecs-expert/tools/check_drift.py
```

Expected: prints `_no docs drift_` and `_no pyplecs drift_`. Exit 0.

- [ ] **Step 4: Write `REFRESH.md`**

`pyplecs/.claude/skills/plecs-expert/tools/REFRESH.md`:
```markdown
# Refresh Procedure

Run on every PLECS minor-version bump or quarterly, whichever is sooner.

## 1. Detect drift

```bash
python .claude/skills/plecs-expert/tools/check_drift.py
```

Output is a Markdown report. Two sections:

- **Docs drift** — tables changed upstream. `sync_tables.py` will re-fetch.
- **PyPLECS drift** — wrappers or RPC methods added/removed since last snapshot. Update `references/` wrapped-vs-not-wrapped notes accordingly.

If both sections say "no drift", you're done.

## 2. Re-sync verbatim tables

```bash
python .claude/skills/plecs-expert/tools/sync_tables.py
```

Updates `<!-- BEGIN VERBATIM TABLE: ... -->` blocks in place. Prose between blocks untouched.

## 3. Re-author flagged prose

For each `DRIFT` line in step 1's report, open the listed file and re-author the surrounding caveman-style prose. Apply `style/caveman.md`.

For each `ADDED`/`REMOVED` line, update the relevant `references/components/*.md` to flip its "wrapped via `pyplecs.<class>`" / "not wrapped, see SPICE map" notes.

## 4. Update pyplecs snapshot

```bash
python -c "
import json, sys
sys.path.insert(0, '.claude/skills/plecs-expert/tools')
from check_drift import pyplecs_snapshot
m = json.load(open('.claude/skills/plecs-expert/manifest.json'))
m['pyplecs_snapshot'] = pyplecs_snapshot()
json.dump(m, open('.claude/skills/plecs-expert/manifest.json','w'), indent=2)
"
```

## 5. Bump version pin

Edit `manifest.json`'s `plecs_version_pinned` if PLECS minor changed.

## 6. Verify + commit

```bash
ruff check .
pytest tests/test_plecs_expert.py
git add .claude/skills/plecs-expert
git commit -m "chore(skill): refresh plecs-expert against PLECS X.Y"
```
```

- [ ] **Step 5: Run all tests**

```bash
pytest tests/test_plecs_expert.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/plecs-expert/tools/check_drift.py \
        .claude/skills/plecs-expert/tools/REFRESH.md \
        .claude/skills/plecs-expert/manifest.json
git commit -m "feat(skill): check_drift.py + REFRESH procedure"
```

---

## Phase 3 — Hand-author caveman prose

> **Scope reminder:** Tasks 6–17 each follow the same template. The first one (Task 6 below) shows the full template. Tasks 7–17 list only file paths, source URLs, and content-specific notes — the steps are identical otherwise.

### Task 6: Author prose for `electrical-passive.md`

**Files:**
- Modify: `pyplecs/.claude/skills/plecs-expert/references/components/electrical-passive.md`
- Modify: `pyplecs/.claude/skills/plecs-expert/LICENSE-NOTES.md` (already has the row from Task 4 — verify)

**Source URLs (already in manifest):**
- https://docs.plexim.com/plecs/latest/UserManual/Electrical/Resistor.html
- https://docs.plexim.com/plecs/latest/UserManual/Electrical/Inductor.html
- https://docs.plexim.com/plecs/latest/UserManual/Electrical/Capacitor.html
- https://docs.plexim.com/plecs/latest/UserManual/Electrical/Transformer.html

- [ ] **Step 1: Read the populated file**

```bash
cat .claude/skills/plecs-expert/references/components/electrical-passive.md
```

You'll see one or more `<!-- BEGIN VERBATIM TABLE: ... -->` blocks (parameters, defaults, units). Prose sections between/around them are empty or stubby — that's what you re-author.

- [ ] **Step 2: For each component, write a caveman-style prose section ABOVE its verbatim table**

Template (apply to every component):
```markdown
## <ComponentName>

`Lib/Electrical/Passive`. <one-sentence purpose>. Pins: <p, n, ...>. Sign convention: <e.g., i flows p→n>.

Wrapped in pyplecs: <yes — `pyplecs.plecs_components.<ClassName>` | no>.

SPICE map: <e.g., `R<name> p n {R}` | n/a>.

<!-- BEGIN VERBATIM TABLE: ... -->
... (left untouched by sync_tables.py) ...
<!-- END VERBATIM TABLE: ... -->

### Notes
- <fact 1: terse, caveman style, factual>.
- <fact 2>.
```

Example — Inductor section:
```markdown
## Inductor

`Lib/Electrical/Passive`. Stores magnetic energy. Pins: 1=p, 2=n. Sign: i_L flows p→n.

Wrapped in pyplecs: no (use raw RPC `set("Inductor1/L", "1e-3")`).

SPICE map: `L<name> p n {L} IC={IL_init}`.

<!-- BEGIN VERBATIM TABLE: inductor -->
... ...
<!-- END VERBATIM TABLE: inductor -->

### Notes
- Initial current `IL_init` requires UIC in the `.tran` directive on SPICE side.
- Pin order matters for sign of `i_L` probe.
```

Apply this to all four components in the file: Resistor, Inductor, Capacitor, Transformer.

For "Wrapped in pyplecs", check the live introspection:
```bash
python -c "import pyplecs.plecs_components as c, inspect; print([n for n,_ in inspect.getmembers(c, inspect.isclass)])"
```

Use the output to label each component as wrapped or not.

- [ ] **Step 3: Run all tests**

```bash
pytest tests/test_plecs_expert.py -v
```

Expected: all pass. Specifically `test_caveman_compliance` must pass — banned words like `just`, `really`, `basically` would fail it.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/plecs-expert/references/components/electrical-passive.md \
        .claude/skills/plecs-expert/LICENSE-NOTES.md
git commit -m "feat(skill): caveman prose for electrical-passive components"
```

---

### Tasks 7–17: Author prose for remaining reference files

Same template as Task 6, applied to:

| Task | File | Source URLs (in manifest.json) |
|------|------|---------------------------------|
| 7 | `references/components/electrical-sources.md` | VoltageSourceAC, VoltageSourceDC, VoltageSourceControlled, CurrentSourceControlled |
| 8 | `references/components/electrical-switches.md` | Mosfet, Igbt, Diode, SwitchIdeal |
| 9 | `references/components/electrical-meters.md` | Voltmeter, Ammeter, Scope |
| 10 | `references/components/magnetic.md` | Permeance, MmfSource, FluxMeter |
| 11 | `references/components/thermal.md` | HeatSink, ThermalCapacitor, AmbientTemperature |
| 12 | `references/components/control.md` | PIController, TransferFunction, StateMachine |
| 13 | `references/components/system.md` | Subsystem, ConfigurableSubsystem, Mask |
| 14 | `references/rpc-api.md` | XmlRpcInterface |
| 15 | `references/plecs-xml-grammar.md` | PlecsFileFormat |
| 16 | `references/solver.md` | SolverSettings |
| 17 | `references/codegen.md` + `references/cscript.md` (combined) | CodeGeneration/Overview, CScript |

**For each task:**

- [ ] Step 1: `cat` the file populated by `sync_tables.py`.
- [ ] Step 2: Author caveman prose ABOVE each `<!-- BEGIN VERBATIM TABLE -->` block, following the Task 6 template. For non-component pages (RPC, XML grammar, solver, codegen, cscript), adapt the template — drop "Pins" and "SPICE map" lines; keep purpose, "wrapped in pyplecs", and Notes.
- [ ] Step 3: `pytest tests/test_plecs_expert.py -v` — all pass.
- [ ] Step 4: Commit with message `feat(skill): caveman prose for <file basename>`.

**Special note for Task 14 (`rpc-api.md`):** the "wrapped in pyplecs" indicator is per RPC function, not per file. For each function in the verbatim table, mark it as wrapped (with the `PlecsServer` method name) or not. Use:
```bash
python -c "import inspect; from pyplecs.pyplecs import PlecsServer; print(sorted(n for n,_ in inspect.getmembers(PlecsServer, inspect.isfunction) if not n.startswith('_')))"
```

**Special note for Task 15 (`plecs-xml-grammar.md`):** the actual `.plecs` file format is sparsely documented online. Supplement the verbatim table with a hand-extracted minimum-viable example from one of the `data/*.plecs` files in this repo (e.g. `data/simple_buck_prb.plecs.bak`). Mark such examples as `<!-- caveman:source: data/simple_buck_prb.plecs.bak (excerpt) -->`.

---

## Phase 4 — URL fallback index

### Task 18: `url-index.md` — long-tail topic table

**Files:**
- Create: `pyplecs/.claude/skills/plecs-expert/references/url-index.md`
- Modify: `pyplecs/.claude/skills/plecs-expert/LICENSE-NOTES.md`

- [ ] **Step 1: Write `url-index.md` with topic → URL fallback table**

```markdown
# URL Fallback Index

Topics not covered offline. Skill should `WebFetch` the URL, summarize in caveman style, cite the URL.

| Topic | URL |
|-------|-----|
| RT Box (covered by future plecs-rtbox skill) | https://docs.plexim.com/rtbox/latest/ |
| Field-oriented control library | https://docs.plexim.com/plecs/latest/UserManual/Control/FOCLibrary.html |
| MagneticSaturable inductor | https://docs.plexim.com/plecs/latest/UserManual/Magnetic/SaturableInductor.html |
| Configurable subsystem variants | https://docs.plexim.com/plecs/latest/UserManual/System/ConfigurableSubsystem.html |
| PLECS Coder target list | https://docs.plexim.com/plecs/latest/UserManual/CodeGeneration/TargetSupport.html |
| Solver tolerance tuning guide | https://docs.plexim.com/plecs/latest/UserManual/Simulation/Tolerances.html |
| MATLAB Coder integration | https://docs.plexim.com/plecs/latest/UserManual/CodeGeneration/Matlab.html |
| Modulator block library | https://docs.plexim.com/plecs/latest/UserManual/Control/Modulators.html |
| Three-phase machines | https://docs.plexim.com/plecs/latest/UserManual/Electrical/Machines.html |
| Power semiconductor thermal modeling | https://docs.plexim.com/plecs/latest/UserManual/Thermal/SemiconductorLossTables.html |
```

> Add more rows as gaps surface during real use.

- [ ] **Step 2: Add row to `LICENSE-NOTES.md`**

```markdown
| `references/url-index.md` | n/a (URL list only) | n/a | URL pointers (no Plexim prose mirrored) |
```

- [ ] **Step 3: Run all tests**

```bash
pytest tests/test_plecs_expert.py -v
```

Expected: pass; `test_url_index_resolvable` now scans real URLs.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/plecs-expert/references/url-index.md \
        .claude/skills/plecs-expert/LICENSE-NOTES.md
git commit -m "feat(skill): url-index.md fallback table"
```

---

## Phase 5 — Slash command

### Task 19: `/plecs` slash command stub + test

**Files:**
- Create: `pyplecs/.claude/commands/plecs.md`
- Modify: `pyplecs/tests/test_plecs_expert.py` (add `test_slash_command_routes`)

- [ ] **Step 1: Write the failing test**

Append to `pyplecs/tests/test_plecs_expert.py`:
```python
def test_slash_command_routes():
    """The /plecs slash command exists and routes to the plecs-expert skill."""
    cmd = SKILL_ROOT.parent.parent / "commands" / "plecs.md"
    assert cmd.exists(), f"missing: {cmd}"
    text = cmd.read_text(encoding="utf-8")
    assert "plecs-expert" in text, "command does not reference the plecs-expert skill"
```

- [ ] **Step 2: Run, confirm it fails**

```bash
pytest tests/test_plecs_expert.py::test_slash_command_routes -v
```

Expected: FAIL with `missing: ...commands/plecs.md`.

- [ ] **Step 3: Write the slash command**

`pyplecs/.claude/commands/plecs.md`:
```markdown
---
description: Look up PLECS docs (components, RPC, XML format, solver, codegen, C-Script). Routes to the plecs-expert skill.
allowed-tools: Skill
---

Use the `plecs-expert` skill to answer the user's question, citing a `.claude/skills/plecs-expert/references/*` file or a `docs.plexim.com` URL. Apply caveman style per `style/caveman.md`.

User question: $ARGUMENTS
```

- [ ] **Step 4: Run, confirm it passes**

```bash
pytest tests/test_plecs_expert.py::test_slash_command_routes -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/commands/plecs.md tests/test_plecs_expert.py
git commit -m "feat(skill): /plecs slash command + routing test"
```

---

## Phase 6 — MCP server

### Task 20: MCP tool implementations (read-only side)

**Files:**
- Create: `pyplecs/pyplecs/mcp/plecs_tools.py`

- [ ] **Step 1: Add `mcp` to optional dependencies**

In `pyplecs/pyproject.toml`, add an `mcp` extra:
```toml
[project.optional-dependencies]
mcp = ["mcp>=1.0"]
dev = [
    # ... existing entries ...
    "mcp>=1.0",
]
```

- [ ] **Step 2: Install + write the tool module**

```bash
pip install -e ".[dev]"
```

`pyplecs/pyplecs/mcp/plecs_tools.py`:
```python
"""Read-only MCP tools backed by the plecs-expert skill content + pyplecs introspection."""
from __future__ import annotations

import inspect
import json
import re
from pathlib import Path
from typing import Any

# Resolve skill root: pyplecs repo .claude/skills/plecs-expert/
PYPLECS_PKG = Path(__file__).resolve().parent.parent  # pyplecs/pyplecs
REPO_ROOT = PYPLECS_PKG.parent  # pyplecs/
SKILL_ROOT = REPO_ROOT / ".claude" / "skills" / "plecs-expert"
REFERENCES = SKILL_ROOT / "references"


def _read_ref(rel: str) -> str:
    path = REFERENCES / rel
    if not path.exists():
        return f"(no offline reference for `{rel}`)"
    return path.read_text(encoding="utf-8")


def plecs_lookup(topic: str) -> str:
    """Read references/<topic>.md (or .md added if missing)."""
    rel = topic if topic.endswith(".md") else f"{topic}.md"
    return _read_ref(rel)


def plecs_search(query: str) -> str:
    """Grep across references/ for `query`. Returns file:line matches."""
    if not REFERENCES.exists():
        return "(references/ not yet populated)"
    needle = query.lower()
    matches: list[str] = []
    for md in sorted(REFERENCES.rglob("*.md")):
        for i, line in enumerate(md.read_text(encoding="utf-8").splitlines(), start=1):
            if needle in line.lower():
                matches.append(f"{md.relative_to(SKILL_ROOT)}:{i}: {line.strip()}")
    return "\n".join(matches) if matches else f"no matches for '{query}'"


def plecs_xml(element: str) -> str:
    """Look up a `.plecs` XML element in plecs-xml-grammar.md."""
    text = _read_ref("plecs-xml-grammar.md")
    pattern = re.compile(rf"`<{re.escape(element)}\b.*", re.IGNORECASE)
    matches = pattern.findall(text)
    if matches:
        return "\n".join(matches[:10])
    return f"element `<{element}>` not documented; try plecs_url('xml-grammar')"


def plecs_url(topic: str) -> str:
    """Return the docs.plexim.com URL for `topic` from url-index.md."""
    text = _read_ref("url-index.md")
    needle = topic.lower()
    for line in text.splitlines():
        if needle in line.lower():
            urls = re.findall(r"https?://[^\s)>\]]+", line)
            if urls:
                return urls[0]
    return f"no URL fallback for '{topic}'"


def pyplecs_wrappers() -> list[str]:
    """List `*PlecsMdl` classes in pyplecs.plecs_components."""
    import pyplecs.plecs_components as comps
    return sorted(
        n for n, obj in inspect.getmembers(comps, inspect.isclass)
        if obj.__module__ == comps.__name__
    )


def pyplecs_rpc_surface() -> list[str]:
    """List PlecsServer public methods."""
    from pyplecs.pyplecs import PlecsServer
    return sorted(
        n for n, _ in inspect.getmembers(PlecsServer, predicate=inspect.isfunction)
        if not n.startswith("_")
    )


def plecs_component(name: str) -> dict[str, Any]:
    """Composed: pyplecs wrapper if present, else search references/components/."""
    wrappers = pyplecs_wrappers()
    matched_wrapper = next((w for w in wrappers if name.lower() in w.lower()), None)
    body = {
        "name": name,
        "pyplecs_wrapper": matched_wrapper,
        "docs_excerpt": plecs_search(name),
    }
    return body


def plecs_rpc(function: str) -> dict[str, Any]:
    """Composed: PlecsServer method introspection if present, else docs lookup."""
    from pyplecs.pyplecs import PlecsServer
    method = getattr(PlecsServer, function, None)
    body: dict[str, Any] = {
        "function": function,
        "wrapped_in_pyplecs": method is not None,
    }
    if method is not None:
        try:
            sig = str(inspect.signature(method))
        except (TypeError, ValueError):
            sig = "(signature not introspectable)"
        body["signature"] = f"PlecsServer.{function}{sig}"
        body["docstring"] = inspect.getdoc(method) or ""
    body["docs_excerpt"] = plecs_search(function)
    return body


# Registry consumed by server.py and the test
TOOL_REGISTRY: dict[str, Any] = {
    "plecs_lookup": plecs_lookup,
    "plecs_search": plecs_search,
    "plecs_xml": plecs_xml,
    "plecs_url": plecs_url,
    "plecs_component": plecs_component,
    "plecs_rpc": plecs_rpc,
    "pyplecs_wrappers": pyplecs_wrappers,
    "pyplecs_rpc_surface": pyplecs_rpc_surface,
}


__all__ = ["TOOL_REGISTRY", *TOOL_REGISTRY.keys()]
```

- [ ] **Step 3: Smoke-test the tool functions directly**

```bash
python -c "
from pyplecs.mcp.plecs_tools import TOOL_REGISTRY, pyplecs_wrappers, plecs_search
print('tools:', sorted(TOOL_REGISTRY))
print('wrappers:', pyplecs_wrappers())
print('search MOSFET:', plecs_search('MOSFET')[:200])
"
```

Expected: prints the 8 tool names, the wrapper class list (`MosfetWithDiodePlecsMdl`, `ResistorPlecsMdl`, ...), and a few `references/.../*.md:NN:` matches.

- [ ] **Step 4: Commit**

```bash
git add pyplecs/mcp/plecs_tools.py pyproject.toml
git commit -m "feat(mcp): plecs_tools registry — 8 read-only MCP tools"
```

---

### Task 21: MCP server boilerplate + entry point

**Files:**
- Create: `pyplecs/pyplecs/mcp/server.py`
- Modify: `pyplecs/pyplecs/mcp/__init__.py`
- Modify: `pyplecs/pyproject.toml`

- [ ] **Step 1: Write the server**

`pyplecs/pyplecs/mcp/server.py`:
```python
"""Stdio MCP server exposing the plecs-expert tools."""
from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .plecs_tools import TOOL_REGISTRY


def _to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, indent=2, default=str)


def build_server() -> Server:
    server: Server = Server("pyplecs-mcp")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=name,
                description=(fn.__doc__ or name).strip().splitlines()[0],
                inputSchema={
                    "type": "object",
                    "properties": {"argument": {"type": "string"}},
                    "required": [],
                },
            )
            for name, fn in TOOL_REGISTRY.items()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        fn = TOOL_REGISTRY.get(name)
        if fn is None:
            return [TextContent(type="text", text=f"unknown tool: {name}")]
        arg = arguments.get("argument", "")
        try:
            result = fn(arg) if arg else fn()
        except TypeError:
            result = fn()
        return [TextContent(type="text", text=_to_text(result))]

    return server


async def _serve() -> None:
    server = build_server()
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> int:
    try:
        asyncio.run(_serve())
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"pyplecs-mcp error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Wire `__init__.py`**

Replace `pyplecs/pyplecs/mcp/__init__.py`:
```python
"""MCP server for PyPLECS.

Exposes the plecs-expert skill content and pyplecs introspection over stdio.
"""
from __future__ import annotations


def create_mcp_server():
    """Create and return the MCP server instance (for embedding/testing)."""
    from .server import build_server
    return build_server()


def main() -> int:
    """Entry point for the `pyplecs-mcp` console script."""
    from .server import main as _main
    return _main()


__all__ = ["create_mcp_server", "main"]
```

- [ ] **Step 3: Add the entry point to `pyproject.toml`**

```toml
[project.scripts]
pyplecs-api = "pyplecs.api:main"
pyplecs-setup = "pyplecs.cli.installer:main"
pyplecs-gui = "pyplecs.webgui:run_app"
pyplecs-mcp = "pyplecs.mcp:main"
```

- [ ] **Step 4: Reinstall the package so the entry point registers**

```bash
pip install -e ".[dev]"
```

- [ ] **Step 5: Smoke-test server construction (no stdio loop)**

```bash
python -c "from pyplecs.mcp import create_mcp_server; s = create_mcp_server(); print(type(s).__name__)"
```

Expected: prints `Server`.

- [ ] **Step 6: Commit**

```bash
git add pyplecs/mcp/__init__.py pyplecs/mcp/server.py pyproject.toml
git commit -m "feat(mcp): pyplecs-mcp stdio server + entry point"
```

---

### Task 22: MCP-side tests + introspection guarantees

**Files:**
- Modify: `pyplecs/tests/test_plecs_expert.py`

- [ ] **Step 1: Append the two MCP-related tests**

Append to `pyplecs/tests/test_plecs_expert.py`:
```python
EXPECTED_MCP_TOOLS = {
    "plecs_lookup",
    "plecs_search",
    "plecs_xml",
    "plecs_url",
    "plecs_component",
    "plecs_rpc",
    "pyplecs_wrappers",
    "pyplecs_rpc_surface",
}


def test_pyplecs_wrappers_introspectable():
    """pyplecs.plecs_components imports clean and exposes *PlecsMdl classes."""
    import pyplecs.plecs_components as comps  # noqa: F401
    from pyplecs.mcp.plecs_tools import pyplecs_wrappers

    wrappers = pyplecs_wrappers()
    assert wrappers, "no wrapper classes found in pyplecs.plecs_components"
    assert any(w.endswith("PlecsMdl") for w in wrappers), (
        f"expected *PlecsMdl naming convention; got: {wrappers}"
    )


def test_mcp_tools_register():
    """Importing pyplecs.mcp.plecs_tools exposes the expected 8 tools."""
    from pyplecs.mcp.plecs_tools import TOOL_REGISTRY

    assert set(TOOL_REGISTRY) == EXPECTED_MCP_TOOLS, (
        f"tool registry mismatch: extra={set(TOOL_REGISTRY) - EXPECTED_MCP_TOOLS} "
        f"missing={EXPECTED_MCP_TOOLS - set(TOOL_REGISTRY)}"
    )
    # Each entry is callable
    for name, fn in TOOL_REGISTRY.items():
        assert callable(fn), f"{name} not callable"
```

- [ ] **Step 2: Run the new tests**

```bash
pytest tests/test_plecs_expert.py::test_pyplecs_wrappers_introspectable tests/test_plecs_expert.py::test_mcp_tools_register -v
```

Expected: both PASS.

- [ ] **Step 3: Run the full test suite for this file**

```bash
pytest tests/test_plecs_expert.py -v
```

Expected: all 8 tests pass.

- [ ] **Step 4: Run ruff**

```bash
ruff check .
```

Expected: clean. Fix any issues (likely import ordering in the new files).

- [ ] **Step 5: Commit**

```bash
git add tests/test_plecs_expert.py
git commit -m "test(mcp): registry + introspection tests"
```

---

## Phase 7 — Final integration

### Task 23: Manual smoke test + PR

**Files:**
- No code changes (verification + PR open).

- [ ] **Step 1: Run the platform-independent test subset (matches pre-push hook)**

```bash
pytest -q tests/test_installer.py tests/test_entrypoint.py tests/test_install_full.py tests/test_abc_contract.py tests/test_plecs_expert.py
```

Expected: all green.

- [ ] **Step 2: Run ruff once more**

```bash
ruff check .
```

Expected: clean.

- [ ] **Step 3: Manual stdio smoke test of `pyplecs-mcp`**

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | pyplecs-mcp 2>/dev/null | head -200
```

Expected: a JSON response listing the 8 tools by name. (Real MCP clients use the `mcp` SDK handshake; this raw probe is a sanity check that the server starts and responds.) If you have Claude Desktop installed, register `pyplecs-mcp` in its `claude_desktop_config.json` and call `plecs_component("Inductor")` for an end-to-end check.

- [ ] **Step 4: Update `CLAUDE.md` with the new skill + MCP server**

Add a row to the Decision Log:
```markdown
| 2026-04-27 | Add `plecs-expert` skill + `pyplecs-mcp` MCP server | Ground PLECS authoring help, netlist converter, and PlecsServer wrapper in docs.plexim.com via offline caveman-style reference. Closes #23. |
```

Add to "Key Documents":
```markdown
- [PLECS Expert Skill](.claude/skills/plecs-expert/SKILL.md) — PLECS docs reference (offline + URL fallback)
```

Add to "Architecture quick reference":
```markdown
- **PLECS docs reference at `.claude/skills/plecs-expert/`** — single source of truth for the skill, `/plecs` command, and `pyplecs-mcp` MCP server. Refresh procedure in `.claude/skills/plecs-expert/tools/REFRESH.md`.
```

- [ ] **Step 5: Push branch**

```bash
git push -u origin feature/plecs-expert-skill
```

Expected: pre-push hook runs ruff + the platform-independent test set; both pass.

- [ ] **Step 6: Open PR**

```bash
gh pr create --title "feat: plecs-expert skill + pyplecs-mcp MCP server (closes #23)" --body "$(cat <<'EOF'
## Summary
- Add `plecs-expert` Claude Code skill at `.claude/skills/plecs-expert/`, grounded in `docs.plexim.com/plecs/latest/`
- Triple delivery: Claude Code skill, `/plecs` slash command, `pyplecs-mcp` stdio MCP server
- Two-layer composition: offline reference (verbatim factual tables + caveman-style rewritten prose) + live `pyplecs` introspection
- Refresh tooling (`sync_tables.py`, `check_drift.py`, `REFRESH.md`) and 8 platform-independent tests

Closes #23.

## Test plan
- [ ] `ruff check .` clean
- [ ] `pytest tests/test_plecs_expert.py` — 8/8 pass
- [ ] Pre-push hook (ruff + 5 platform-independent test files) green
- [ ] `pyplecs-mcp` starts; `tools/list` returns 8 tools
- [ ] Manual: Claude Desktop registers `pyplecs-mcp` and answers `plecs_component("Inductor")` with composed pyplecs+docs answer

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: PR URL printed.

- [ ] **Step 7: Confirm completion criteria**

Read [`docs/superpowers/specs/2026-04-27-plecs-expert-skill-design.md`](../specs/2026-04-27-plecs-expert-skill-design.md) — "Completion criteria" section. Tick each off:

1. ☐ `pyplecs/.claude/skills/plecs-expert/` populated for Full scope minus RT Box
2. ☐ `.claude/commands/plecs.md` slash-command stub exists
3. ☐ `pyplecs/mcp/` implements `create_mcp_server()` + `main()` over stdio with the 8 read-only tools
4. ☐ `pyproject.toml` registers `pyplecs-mcp = "pyplecs.mcp:main"`
5. ☐ `tests/test_plecs_expert.py` passes in the platform-independent subset
6. ☐ `ruff check .` clean
7. ☐ Manual smoke test passed
8. ☐ PR opened referencing #23

---

## Out of scope (do NOT do as part of this plan)

- RT Box content (separate `plecs-rtbox` skill, future).
- Simulation execution as MCP tool (separate `plecs-runner` skill, future).
- HTTP MCP transport.
- Auto-publishing `references/` to mkdocs / GitHub Pages — content stays under `.claude/`.
- Rewriting `pyplecs.plecs_components.py` to expand wrapper coverage.
- Portability of the skill folder as standalone drop-in.
