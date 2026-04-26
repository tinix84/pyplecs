# Repo Hygiene and Tool-Agnostic Contracts — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bundle four cleanups in one PR: (A) vendor real ABCs at `pyplecs/_contracts/` with PyPI-passthrough façade, (B) replace GitHub Actions CI with a pre-push hook, (C) unify lint on ruff, (D) move `articles/` under `docs/articles/` for mkdocs.

**Architecture:** PyPLECS stays standalone (no hard dep on `pycircuitsim-core`). The vendored ABC copy lives at `pyplecs/_contracts/` and is shadowed by a public façade `pyplecs.contracts` that prefers an external PyPI `pycircuitsim_core` if installed and contract-version-compatible, otherwise falls back to the bundled copy. Concrete pyplecs classes inherit from the contracts ABCs and satisfy them by method-name presence; signature reconciliation with upstream's pydantic models is deferred to future ecosystem work.

**Tech Stack:** Python ≥3.10, pydantic v2, ruff, pytest, mkdocs-material. No new runtime dependencies.

**Reference spec:** `docs/superpowers/specs/2026-04-25-repo-hygiene-and-contracts-design.md`

**Upstream source:** `tinix84/pycircuitsim` monorepo, path `packages/pycircuitsim-core/pycircuitsim_core/`, pinned to commit SHA `a065438297155d73469ebce83ef6ecb051aec8aa` (verified 2026-04-25).

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `.github/workflows/ci.yml` | DELETE | Removed; pre-push hook replaces it. |
| `.claude/hooks/pre_push_lint.py` | MODIFY | Run `ruff check . && pytest -q <list>` and exit non-zero on failure (currently just prints a reminder). |
| `CLAUDE.md` | MODIFY | Add Decision Log entry for CI removal. |
| `README.md` | MODIFY | Drop CI badge if any; rewrite testing section; replace black/flake8/mypy/isort with ruff; update `articles/` path references. |
| `docs/contributing.md` | MODIFY | Same — testing & lint sections updated. |
| `.claude/skills.md` | MODIFY | Replace `## Code Quality` block with single `ruff check . && ruff format .`. |
| `requirements-dev.txt` | MODIFY | Drop black/flake8/mypy/isort/sphinx; keep pytest, pytest-asyncio, pytest-cov, ruff. |
| `articles/` | RENAME → `docs/articles/` | Lives inside mkdocs source tree. |
| `mkdocs.yml` | MODIFY | Add `Articles:` nav section pointing into `articles/...` (relative to `docs/`). |
| `docs/articles/README.md` | CREATE | Section landing page for mkdocs. |
| `pycircuitsim_core/` (top-level) | DELETE | Top-level vendored stubs from PR #22 — replaced by `pyplecs/_contracts/`. |
| `pyplecs/_contracts/__init__.py` | CREATE | Re-exports same surface as upstream + `StructuredLoggerBase` + `__contract_version__ = "1.0"`. |
| `pyplecs/_contracts/server.py` | CREATE | Verbatim port of upstream `server.py` with SHA header. |
| `pyplecs/_contracts/cache.py` | CREATE | Verbatim port of upstream `cache.py` with SHA header. |
| `pyplecs/_contracts/config.py` | CREATE | Verbatim port of upstream `config.py` with SHA header. |
| `pyplecs/_contracts/logging.py` | CREATE | Verbatim port of upstream `logging.py` with SHA header. |
| `pyplecs/_contracts/orchestration.py` | CREATE | Verbatim port of upstream `orchestration.py` with SHA header. |
| `pyplecs/_contracts/models.py` | CREATE | Verbatim port of upstream `models.py` with SHA header. |
| `pyplecs/contracts.py` | CREATE | Public façade with PyPI-passthrough + version guard + `_source` diagnostic. |
| `pyplecs/pyplecs.py` | MODIFY | Change ABC import path: `from pycircuitsim_core.X import Y` → `from pyplecs.contracts import Y`. |
| `pyplecs/cache/__init__.py` | MODIFY | Same import path change. |
| `pyplecs/config.py` | MODIFY | Same import path change. |
| `pyplecs/logging/__init__.py` | MODIFY | Same import path change. |
| `pyplecs/orchestration/__init__.py` | MODIFY | Same import path change. |
| `pyproject.toml` | MODIFY | Drop `pycircuitsim_core*` from `packages.find.include`. |
| `tests/test_abc_contract.py` | CREATE | Verifies each concrete class has zero residual abstract methods + `pyplecs.contracts._source` is sane. |
| `tools/SYNC_PYCIRCUITSIM_CORE.md` | CREATE | Docs how to re-sync vendored copy from upstream. |

`pyplecs/core/models.py` is **NOT** modified — see spec "Models — two flavors, no merge".

---

## Task 1: Strengthen the pre-push hook

**Why first:** Phase B of the spec, smallest commit. Lands the safety net before deleting CI in Task 2.

**Files:**
- Modify: `.claude/hooks/pre_push_lint.py`

- [ ] **Step 1: Read the current hook to understand the env var protocol.**

```bash
cat .claude/hooks/pre_push_lint.py
```
Expected output: 19 lines; reads `CLAUDE_TOOL_INPUT` JSON, prints a reminder when command contains `git push`, otherwise no-op.

- [ ] **Step 2: Replace the hook with one that actually runs ruff + tests.**

Write `.claude/hooks/pre_push_lint.py`:
```python
"""Claude Code PostToolUse hook: enforce lint + platform-independent tests on git push.

Reads the tool invocation from CLAUDE_TOOL_INPUT (JSON). If the command is a
``git push``, runs ``ruff check`` and the platform-independent pytest files.
Exits non-zero on failure to block the push.
"""
import json
import os
import subprocess
import sys


PYTEST_FILES = [
    "tests/test_installer.py",
    "tests/test_entrypoint.py",
    "tests/test_install_full.py",
    "tests/test_abc_contract.py",
]


def main() -> int:
    raw = os.environ.get("CLAUDE_TOOL_INPUT", "{}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return 0  # malformed input — let Claude through

    command = data.get("command", "")
    if "git push" not in command:
        return 0

    print("[pre-push] running ruff check...", file=sys.stderr)
    rc = subprocess.call(["ruff", "check", "."])
    if rc != 0:
        print("[pre-push] BLOCKED: ruff check failed", file=sys.stderr)
        return rc

    print("[pre-push] running platform-independent tests...", file=sys.stderr)
    rc = subprocess.call(["pytest", "-q", *PYTEST_FILES])
    if rc != 0:
        print("[pre-push] BLOCKED: pytest failed", file=sys.stderr)
        return rc

    print("[pre-push] OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Smoke-test the hook by invoking it directly with a fake env var.**

Run: `CLAUDE_TOOL_INPUT='{"command":"echo hello"}' python .claude/hooks/pre_push_lint.py; echo "exit=$?"`
Expected: prints nothing (not a git push), exits 0.

- [ ] **Step 4: Smoke-test the git-push branch (will fail because `tests/test_abc_contract.py` does not exist yet).**

Run: `CLAUDE_TOOL_INPUT='{"command":"git push origin master"}' python .claude/hooks/pre_push_lint.py; echo "exit=$?"`
Expected: ruff runs (likely passes); pytest fails on missing `tests/test_abc_contract.py`; exit code non-zero.
This is acceptable — the hook will pass once Task 8 lands the test file. The plan is intentionally TDD-shaped here.

- [ ] **Step 5: Commit.**

```bash
git add .claude/hooks/pre_push_lint.py
git commit -m "chore: pre-push hook now runs ruff + platform-independent tests"
```

---

## Task 2: Delete GitHub Actions CI and update docs

**Files:**
- Delete: `.github/workflows/ci.yml`
- Modify: `CLAUDE.md` (Decision Log section)
- Modify: `README.md` (testing section + any CI badge)
- Modify: `docs/contributing.md` (testing section)

- [ ] **Step 1: Delete the workflow.**

```bash
git rm .github/workflows/ci.yml
```

- [ ] **Step 2: Add a Decision Log row to CLAUDE.md.**

Append the row to the existing table in `CLAUDE.md`. Locate the table (lines ~42–49) and add **at the bottom of the table**:
```
| 2026-04-25 | Remove GitHub Actions CI | Single-maintainer project; pre-push hook covers lint + platform-independent tests; PLECS-dependent tests run manually on Windows. |
```

- [ ] **Step 3: Update README.md testing section.**

Find the "Run Tests" / "Development" section (around line 354 in current README). After the existing `pytest` examples, add:
```markdown
### Pre-push enforcement

This repo has no GitHub Actions CI. A Claude Code pre-push hook
(`.claude/hooks/pre_push_lint.py`) runs `ruff check .` + the four
platform-independent test files (`test_installer.py`, `test_entrypoint.py`,
`test_install_full.py`, `test_abc_contract.py`). The hook blocks `git push`
on failure. Full PLECS-dependent suite must be run manually on Windows.
```

If the README contains a CI badge line (look for `![CI]` or `actions/workflows/ci.yml`) — remove it. Verify with: `grep -nE 'ci\.yml|actions/workflows' README.md`. Expected after edit: no matches.

- [ ] **Step 4: Update docs/contributing.md testing section.**

Locate any text about "GitHub Actions" or "CI runs" or "pull request checks". Replace with the same pre-push paragraph from Step 3. Verify: `grep -nE 'github actions|workflow|ci.yml' docs/contributing.md` — expected no matches after edit.

- [ ] **Step 5: Commit.**

```bash
git add .github/workflows/ci.yml CLAUDE.md README.md docs/contributing.md
git commit -m "chore: remove GitHub Actions CI in favor of pre-push hook"
```

---

## Task 3: Unify lint on ruff

**Files:**
- Modify: `.claude/skills.md`
- Modify: `docs/contributing.md`
- Modify: `README.md`
- Modify: `requirements-dev.txt`

- [ ] **Step 1: Replace the Code Quality block in `.claude/skills.md`.**

Locate `## Code Quality` (around line 30–55). Replace the entire block (Format/Lint/Type Check/Sort Imports/Full Quality Check sub-sections) with:
```markdown
## Code Quality

### Lint
```bash
ruff check .
```

### Format
```bash
ruff format .
```

### Full quality check
```bash
ruff check . && ruff format --check .
```
```

Verify: `grep -nE 'black|flake8|mypy|isort' .claude/skills.md` → no matches.

- [ ] **Step 2: Replace lint references in `docs/contributing.md`.**

Find the lint/style section (search `flake8`, `black`, `mypy`). Replace with:
```markdown
### Lint and format

This project uses `ruff` for both linting and formatting.

```bash
ruff check .         # report issues
ruff check --fix .   # auto-fix
ruff format .        # format code
```

Configuration is in `pyproject.toml` under `[tool.ruff]` (target Python 3.8+ for compatibility with the `target-version` setting; runtime requires Python 3.10+).
```

Verify: `grep -nE 'black|flake8|mypy|isort' docs/contributing.md` → no matches.

- [ ] **Step 3: Replace the Code Quality section in `README.md`.**

Locate the section near line 370–380 starting with `### Code Quality`. Replace its body with:
```markdown
### Code Quality
```bash
# Lint and format
ruff check .
ruff format .
```
Configuration in `pyproject.toml` under `[tool.ruff]`.
```

Verify: `grep -nE 'black|flake8|mypy|isort' README.md` → no matches.

- [ ] **Step 4: Trim `requirements-dev.txt`.**

Open the file. Current content (after the recent Read):
```
# Testing
pytest>=6.2.0
pytest-asyncio>=0.15.0
pytest-cov>=2.12.0

# Code quality
black>=21.0.0
flake8>=3.9.0
mypy>=0.910
isort>=5.9.0

# Documentation
sphinx>=4.0.0
sphinx-rtd-theme>=0.5.0
```

Replace the entire file with:
```
# PyPLECS Development Tools

# Testing
pytest>=6.2.0
pytest-asyncio>=0.15.0
pytest-cov>=2.12.0

# Lint + format (single tool)
ruff>=0.4.0

# Documentation site
mkdocs>=1.5.0
mkdocs-material>=9.0.0
```

Note: `sphinx` is replaced by `mkdocs-material` because the project documentation lives in `docs/*.md` and is built via `mkdocs build`, not Sphinx. If anyone is still using Sphinx anywhere, leave Sphinx in — verify with: `grep -rE 'conf\.py|sphinx-build' . --include='*.py' --include='Makefile' --include='*.yml'`. Expected: no matches in source. If matches exist, **do not delete sphinx** from requirements-dev.txt.

- [ ] **Step 5: Verify ruff runs clean (or document outstanding issues).**

Run: `ruff check .`
Expected: zero or low number of warnings. If pre-existing issues exist, do not fix them in this commit — that's outside the scope. Note them in the commit body if non-trivial.

- [ ] **Step 6: Commit.**

```bash
git add .claude/skills.md docs/contributing.md README.md requirements-dev.txt
git commit -m "chore: unify lint on ruff (drop black/flake8/mypy/isort references)"
```

---

## Task 4: Move articles into mkdocs source tree

**Files:**
- Rename: `articles/` → `docs/articles/` (preserves history)
- Modify: `mkdocs.yml`
- Create: `docs/articles/README.md`
- Audit: `articles/diagrams/generate_all.py`, `articles/animations/generate_linkedin_gifs.py`
- Verify: `.gitignore` does not exclude `docs/articles/`

- [ ] **Step 1: Move the directory.**

```bash
git mv articles docs/articles
```

- [ ] **Step 2: Audit script paths.**

```bash
grep -rEn '^|"|\b(articles/)' docs/articles/diagrams/generate_all.py docs/articles/animations/generate_linkedin_gifs.py docs/articles/diagrams/python/architecture_diagrams.py docs/articles/diagrams/python/performance_comparison.py 2>/dev/null
```
For any line containing a hard-coded `articles/` path that is *not part of a doc string* or comment, replace `articles/` with `docs/articles/`. If a script uses `__file__`-relative paths or `Path(__file__).parent`, no edit is needed. Verify each edit by re-running the script's main entrypoint if feasible (e.g., `python docs/articles/diagrams/generate_all.py --help`).

- [ ] **Step 3: Update `mkdocs.yml` nav section.**

Insert these lines into the existing `nav:` block, after the `Contributing:` line:

```yaml
  - Articles:
    - Overview: articles/README.md
    - LinkedIn Articles: articles/linkedin/
    - LinkedIn Posts: articles/linkedin-posts/
    - Substack Articles: articles/substack/
```

mkdocs-material accepts directory references in nav — they auto-expand to a sub-nav of the markdown files inside.

- [ ] **Step 4: Create `docs/articles/README.md`.**

```markdown
# Articles

Long-form posts and supporting material for the PyPLECS v1.0.0 redesign,
originally published on LinkedIn and Substack.

## Series

- **LinkedIn Articles** — full-length narratives (10 posts). See `linkedin/`.
- **LinkedIn Posts** — short-form summaries (10 posts). See `linkedin-posts/`.
- **Substack Articles** — extended write-ups (10 posts). See `substack/`.

## Supporting material

- `diagrams/` — Mermaid + matplotlib architecture diagrams (source + rendered PNG).
- `animations/` — animated GIFs used in social posts.

These pages are checked into the repo so the documentation site has a stable
URL for each article. The published versions on LinkedIn / Substack are the
canonical reading experience.
```

- [ ] **Step 5: Audit `.gitignore`.**

Run: `grep -nE 'articles' .gitignore`
For each match, evaluate: does the rule still belong (e.g., ignoring build outputs under `articles/diagrams/output/` is fine if `*.png` is still committed elsewhere). If a rule would now ignore content we want shipped to mkdocs, remove or retarget it (e.g., `articles/animations/*.gif` becomes `docs/articles/animations/*.gif` only if the original was an ignore — most likely it isn't).

If unsure, leave `.gitignore` alone for this commit and revisit in a follow-up.

- [ ] **Step 6: Verify mkdocs builds cleanly.**

```bash
mkdocs build --strict
```
Expected: succeeds, no broken-link warnings about `articles/...`. If broken links exist (e.g., a doc referencing the old path), fix them before committing.

If `mkdocs` is not installed in the active venv: `pip install mkdocs mkdocs-material` first.

- [ ] **Step 7: Update `README.md` references.**

```bash
grep -nE '\bin articles/|\(articles/|"articles/' README.md
```
For each match, replace `articles/...` with `docs/articles/...` if the link is a relative file link, or with `https://tinix84.github.io/pyplecs/articles/...` if external.

- [ ] **Step 8: Commit.**

```bash
git add mkdocs.yml docs/articles README.md .gitignore
git commit -m "chore: move articles under docs/articles for mkdocs"
```

Note: `git mv articles docs/articles` already staged the rename in step 1. The above add captures everything else.

---

## Task 5: Vendor 7 ABC files into `pyplecs/_contracts/`

**Files (all CREATE):**
- `pyplecs/_contracts/__init__.py`
- `pyplecs/_contracts/server.py`
- `pyplecs/_contracts/cache.py`
- `pyplecs/_contracts/config.py`
- `pyplecs/_contracts/logging.py`
- `pyplecs/_contracts/orchestration.py`
- `pyplecs/_contracts/models.py`

Upstream pin: commit `a065438297155d73469ebce83ef6ecb051aec8aa` (verified 2026-04-25).
Upstream path: `tinix84/pycircuitsim/packages/pycircuitsim-core/pycircuitsim_core/`.

The header inserted at top of every file:
```python
# Vendored from tinix84/pycircuitsim@a065438297155d73469ebce83ef6ecb051aec8aa
# Source: packages/pycircuitsim-core/pycircuitsim_core/<filename>
# DO NOT EDIT — re-sync via tools/SYNC_PYCIRCUITSIM_CORE.md.
```

- [ ] **Step 1: Create the directory.**

```bash
mkdir -p pyplecs/_contracts
```

- [ ] **Step 2: Fetch and write `pyplecs/_contracts/server.py`.**

```bash
gh api repos/tinix84/pycircuitsim/contents/packages/pycircuitsim-core/pycircuitsim_core/server.py?ref=a065438297155d73469ebce83ef6ecb051aec8aa --jq '.content' | base64 -d > /tmp/server_raw.py
```
Write `pyplecs/_contracts/server.py` as the header above + content of `/tmp/server_raw.py` + a trailing newline. Replace `pycircuitsim_core.models` import inside the body with `pyplecs._contracts.models` so the vendored modules import each other.

Final content (full file, ready to write — header + adjusted import + verbatim body):
```python
# Vendored from tinix84/pycircuitsim@a065438297155d73469ebce83ef6ecb051aec8aa
# Source: packages/pycircuitsim-core/pycircuitsim_core/server.py
# DO NOT EDIT — re-sync via tools/SYNC_PYCIRCUITSIM_CORE.md.

"""Abstract base class for simulation servers.

Both PlecsServer (XML-RPC) and GeckoServer (REST API) implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pyplecs._contracts.models import SimulationRequest, SimulationResult


class SimulationServer(ABC):
    """Abstract simulation server interface.

    Implementations must support:
    - Single simulation (blocking)
    - Batch simulation (parallel where possible)
    - Health check
    - Context manager protocol
    """

    @abstractmethod
    def simulate(self, request: SimulationRequest) -> SimulationResult:
        """Run a single simulation (blocking)."""

    @abstractmethod
    def simulate_batch(self, requests: list[SimulationRequest]) -> list[SimulationResult]:
        """Run multiple simulations (parallel where the backend supports it)."""

    def simulate_raw(
        self,
        model_file: str,
        parameters: dict[str, Any] | None = None,
        simulation_time: float | None = None,
        time_step: float | None = None,
        **options: Any,
    ) -> SimulationResult:
        """Convenience wrapper that builds SimulationRequest internally."""
        req = SimulationRequest(
            model_file=model_file,
            parameters=parameters or {},
            simulation_time=simulation_time,
            time_step=time_step,
            options=options,
        )
        return self.simulate(req)

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the simulation backend is reachable."""

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Return detailed health info from the backend."""

    def close(self) -> None:
        """Release resources. Override if cleanup is needed."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False
```

- [ ] **Step 3: Write `pyplecs/_contracts/cache.py`.**

```python
# Vendored from tinix84/pycircuitsim@a065438297155d73469ebce83ef6ecb051aec8aa
# Source: packages/pycircuitsim-core/pycircuitsim_core/cache.py
# DO NOT EDIT — re-sync via tools/SYNC_PYCIRCUITSIM_CORE.md.

"""Abstract base class for simulation caching."""

from __future__ import annotations

import hashlib
import json
import os
from abc import ABC, abstractmethod
from typing import Any, Optional

import pandas as pd


class SimulationCacheBase(ABC):
    """Abstract simulation cache interface."""

    @abstractmethod
    def get_cached_result(
        self, model_file: str, parameters: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Get cached result for a model+parameters combination."""

    @abstractmethod
    def cache_result(
        self,
        model_file: str,
        parameters: dict[str, Any],
        timeseries_data: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> str:
        """Cache a simulation result. Returns the simulation hash."""

    @abstractmethod
    def invalidate_cache(self, model_file: str, parameters: dict[str, Any]) -> bool:
        """Invalidate a specific cache entry. Returns True if found and deleted."""

    @abstractmethod
    def clear_cache(self) -> None:
        """Clear all cached results."""

    @abstractmethod
    def get_cache_stats(self) -> dict[str, Any]:
        """Return cache usage statistics."""

    @staticmethod
    def compute_hash(
        model_file: str,
        parameters: dict[str, Any],
        include_file_content: bool = True,
        algorithm: str = "sha256",
    ) -> str:
        """Compute deterministic hash for a simulation configuration."""
        hasher = hashlib.new(algorithm)
        hasher.update(str(model_file).encode())
        if include_file_content and os.path.exists(model_file):
            with open(model_file, "rb") as f:
                hasher.update(f.read())
        param_str = json.dumps(parameters, sort_keys=True, default=str)
        hasher.update(param_str.encode())
        return hasher.hexdigest()
```

- [ ] **Step 4: Write `pyplecs/_contracts/config.py`.**

```python
# Vendored from tinix84/pycircuitsim@a065438297155d73469ebce83ef6ecb051aec8aa
# Source: packages/pycircuitsim-core/pycircuitsim_core/config.py
# DO NOT EDIT — re-sync via tools/SYNC_PYCIRCUITSIM_CORE.md.

"""Abstract base class for configuration management."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class CacheConfig:
    """Cache configuration (shared across tools)."""

    enabled: bool = True
    type: str = "file"
    directory: str = "./cache"
    ttl: int = 3600
    timeseries_format: str = "parquet"
    metadata_format: str = "json"
    compression: str = "snappy"
    hash_algorithm: str = "sha256"
    include_files: bool = True
    exclude_fields: list = field(default_factory=lambda: ["timestamp", "run_id"])


@dataclass
class ApiConfig:
    """REST API configuration (shared across tools)."""

    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8081
    prefix: str = "/api/v1"
    rate_limit_enabled: bool = True
    requests_per_minute: int = 100
    docs_enabled: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration (shared across tools)."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    file_path: str = "./logs/app.log"
    file_max_size: str = "10MB"
    file_backup_count: int = 5
    console_enabled: bool = True
    console_level: str = "INFO"
    structured_enabled: bool = True
    structured_path: str = "./logs/structured.jsonl"


class ConfigManagerBase(ABC):
    """Abstract config manager that loads YAML and provides typed sections."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_file()
        self._config_data: dict[str, Any] = {}
        self.load_config()

    @abstractmethod
    def _find_config_file(self) -> str:
        """Find config file in standard locations. Tool-specific."""

    def load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path) as f:
                self._config_data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            self._config_data = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot-notation key path."""
        keys = key.split(".")
        value = self._config_data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def update(self, key: str, value: Any) -> None:
        """Update config value by dot-notation key path."""
        keys = key.split(".")
        d = self._config_data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

    def save_config(self, path: Optional[str] = None) -> None:
        """Save current configuration to YAML file."""
        save_path = path or self.config_path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w") as f:
            yaml.dump(self._config_data, f, default_flow_style=False, sort_keys=False)

    @property
    def raw(self) -> dict[str, Any]:
        """Access the raw config dict."""
        return self._config_data
```

- [ ] **Step 5: Write `pyplecs/_contracts/logging.py`.**

```python
# Vendored from tinix84/pycircuitsim@a065438297155d73469ebce83ef6ecb051aec8aa
# Source: packages/pycircuitsim-core/pycircuitsim_core/logging.py
# DO NOT EDIT — re-sync via tools/SYNC_PYCIRCUITSIM_CORE.md.

"""Abstract base class for structured logging."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class StructuredLoggerBase(ABC):
    """Abstract structured logger interface."""

    @abstractmethod
    def log_simulation_start(
        self,
        task_id: str,
        model_file: str,
        parameters: dict[str, Any],
        worker_id: Optional[str] = None,
    ) -> None:
        """Log simulation start."""

    @abstractmethod
    def log_simulation_complete(
        self,
        task_id: str,
        success: bool,
        execution_time: float,
        worker_id: Optional[str] = None,
        cached: bool = False,
    ) -> None:
        """Log simulation completion."""

    @abstractmethod
    def log_simulation_error(
        self, task_id: str, error_message: str, worker_id: Optional[str] = None
    ) -> None:
        """Log simulation error."""

    @abstractmethod
    def log_cache_hit(self, task_id: str, simulation_hash: str, model_file: str) -> None:
        """Log cache hit."""

    @abstractmethod
    def log_cache_miss(self, task_id: str, simulation_hash: str, model_file: str) -> None:
        """Log cache miss."""

    @abstractmethod
    def log_api_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time: float,
        client_ip: Optional[str] = None,
    ) -> None:
        """Log API request."""
```

- [ ] **Step 6: Write `pyplecs/_contracts/orchestration.py`.**

Note the import path adjustment from `pycircuitsim_core.models` → `pyplecs._contracts.models`.

```python
# Vendored from tinix84/pycircuitsim@a065438297155d73469ebce83ef6ecb051aec8aa
# Source: packages/pycircuitsim-core/pycircuitsim_core/orchestration.py
# DO NOT EDIT — re-sync via tools/SYNC_PYCIRCUITSIM_CORE.md.

"""Abstract base class for simulation orchestration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from pyplecs._contracts.models import SimulationRequest, SimulationResult, TaskPriority


class SimulationOrchestratorBase(ABC):
    """Abstract simulation orchestrator interface."""

    @abstractmethod
    async def submit_simulation(
        self,
        request: SimulationRequest,
        priority: TaskPriority = TaskPriority.NORMAL,
        use_cache: bool = True,
    ) -> str:
        """Submit a simulation for execution. Returns task ID."""

    @abstractmethod
    async def get_task_status(self, task_id: str) -> Optional[dict[str, Any]]:
        """Get status of a specific task."""

    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a queued or running task."""

    @abstractmethod
    async def start(self) -> None:
        """Start the orchestrator loop."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the orchestrator loop."""

    @abstractmethod
    def get_orchestrator_stats(self) -> dict[str, Any]:
        """Get orchestrator statistics."""

    @abstractmethod
    async def wait_for_completion(
        self, task_id: str, timeout: Optional[float] = None
    ) -> Optional[SimulationResult]:
        """Wait for a specific task to complete."""

    @abstractmethod
    async def wait_for_all_tasks(self, timeout: Optional[float] = None) -> bool:
        """Wait for all tasks to complete. Returns True if all done, False if timeout."""

    @abstractmethod
    def add_callback(self, event: str, callback: Callable) -> None:
        """Add callback for orchestrator events.

        Events: on_task_started, on_task_completed, on_task_failed,
                on_queue_empty, on_batch_started, on_batch_completed
        """

    @abstractmethod
    def remove_callback(self, event: str, callback: Callable) -> None:
        """Remove a previously registered callback."""
```

- [ ] **Step 7: Write `pyplecs/_contracts/models.py`.**

```python
# Vendored from tinix84/pycircuitsim@a065438297155d73469ebce83ef6ecb051aec8aa
# Source: packages/pycircuitsim-core/pycircuitsim_core/models.py
# DO NOT EDIT — re-sync via tools/SYNC_PYCIRCUITSIM_CORE.md.

"""Shared data models for circuit simulation tools.

These models define the common interface between pyplecs and pygeckocircuit.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

import pandas as pd
from pydantic import BaseModel, Field


class SimulationStatus(str, Enum):
    """Simulation task status (common across all tools)."""

    QUEUED = "QUEUED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskPriority(Enum):
    """Task priority levels for orchestration."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class SimulationRequest(BaseModel):
    """Tool-agnostic simulation request."""

    model_file: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    simulation_time: Optional[float] = None
    time_step: Optional[float] = None
    output_variables: list[str] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SimulationResult(BaseModel):
    """Tool-agnostic simulation result."""

    task_id: str = ""
    success: bool = False
    time: list[float] = Field(default_factory=list)
    signals: dict[str, list[float]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None
    cached: bool = False

    def to_dataframe(self) -> pd.DataFrame:
        """Convert result to pandas DataFrame with time index."""
        data = {"time": self.time, **self.signals}
        return pd.DataFrame(data)


class SyncSimulationRequest(BaseModel):
    """Request for sync simulation endpoints (FastAPI proxy)."""

    model_file: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    signal_map: Optional[dict[str, str]] = None


class SyncSimulationResponse(BaseModel):
    """Response from sync simulation endpoints."""

    success: bool
    time: list[float] = Field(default_factory=list)
    signals: dict[str, list[float]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
```

- [ ] **Step 8: Write `pyplecs/_contracts/__init__.py`.**

```python
# Vendored from tinix84/pycircuitsim@a065438297155d73469ebce83ef6ecb051aec8aa
# Source: packages/pycircuitsim-core/pycircuitsim_core/__init__.py
# DO NOT EDIT — re-sync via tools/SYNC_PYCIRCUITSIM_CORE.md.
#
# Local divergence: StructuredLoggerBase is added to __all__
# (upstream defines it in logging.py but omits from its __all__).

"""pycircuitsim-core — Shared interfaces for circuit simulation tools.

Provides abstract base classes that both pyplecs and pygeckocircuit implement,
enabling tool-agnostic simulation scripts.
"""

from pyplecs._contracts.cache import SimulationCacheBase
from pyplecs._contracts.config import ConfigManagerBase
from pyplecs._contracts.logging import StructuredLoggerBase
from pyplecs._contracts.models import (
    SimulationRequest,
    SimulationResult,
    SimulationStatus,
    SyncSimulationRequest,
    SyncSimulationResponse,
    TaskPriority,
)
from pyplecs._contracts.orchestration import SimulationOrchestratorBase
from pyplecs._contracts.server import SimulationServer

__version__ = "1.0.0"
__contract_version__ = "1.0"

__all__ = [
    "SimulationServer",
    "SimulationCacheBase",
    "SimulationOrchestratorBase",
    "ConfigManagerBase",
    "StructuredLoggerBase",
    "SimulationRequest",
    "SimulationResult",
    "SimulationStatus",
    "SyncSimulationRequest",
    "SyncSimulationResponse",
    "TaskPriority",
    "__contract_version__",
]
```

- [ ] **Step 9: Smoke-test the vendored package can import standalone.**

Run: `python -c "from pyplecs._contracts import SimulationServer, SimulationCacheBase, ConfigManagerBase, StructuredLoggerBase, SimulationOrchestratorBase, TaskPriority, SimulationRequest, SimulationResult; print('imports OK')"`
Expected: `imports OK`. If `pydantic` or `pyyaml` or `pandas` are missing, the import will fail; install via `pip install pydantic pyyaml pandas` (these are already in `requirements-core.txt`).

- [ ] **Step 10: Commit.**

```bash
git add pyplecs/_contracts/
git commit -m "feat: vendor pycircuitsim_core ABCs at pyplecs/_contracts/

Source: tinix84/pycircuitsim@a065438297155d73469ebce83ef6ecb051aec8aa
Path:   packages/pycircuitsim-core/pycircuitsim_core/

Local divergence: StructuredLoggerBase added to __all__ (upstream omits)
plus __contract_version__ = '1.0' added for shim version-guard support."
```

---

## Task 6: Add `pyplecs/contracts.py` public façade

**Files:**
- Create: `pyplecs/contracts.py`

- [ ] **Step 1: Write the shim.**

```python
"""Stable public namespace for shared simulation contracts.

Imports are tried in this order:
  1. The PyPI ``pycircuitsim_core`` package, if installed AND its contract
     version matches what pyplecs was tested against.
  2. The vendored copy at ``pyplecs._contracts``.

This means pyplecs works standalone (vendored) AND silently picks up the
canonical upstream package when the umbrella PyCircuitSim ecosystem is
present, as long as the contract major version matches.
"""

from __future__ import annotations

# Contract major version pyplecs has been tested against.
# Bumped only when the vendored copy is re-synced from upstream.
__contract_version__ = "1.0"


def _resolve_source() -> str:
    """Decide whether to use external or vendored implementations.

    Returns 'pypi' if external pycircuitsim_core is importable AND
    version-compatible; otherwise 'vendored'. Result is cached at
    module import time via the assignments below.
    """
    try:
        import pycircuitsim_core as _ext
    except ImportError:
        return "vendored"

    ext_version = (
        getattr(_ext, "__contract_version__", None)
        or getattr(_ext, "__version__", "0.0")
    )
    ext_major = str(ext_version).split(".")[0]
    our_major = __contract_version__.split(".")[0]
    if ext_major != our_major:
        return "vendored"
    return "pypi"


_source = _resolve_source()


if _source == "pypi":
    from pycircuitsim_core import (  # type: ignore[import-not-found]
        ConfigManagerBase,
        SimulationCacheBase,
        SimulationOrchestratorBase,
        SimulationRequest,
        SimulationResult,
        SimulationServer,
        SimulationStatus,
        SyncSimulationRequest,
        SyncSimulationResponse,
        TaskPriority,
    )
    # StructuredLoggerBase is missing from upstream __all__; import directly:
    from pycircuitsim_core.logging import StructuredLoggerBase  # type: ignore[import-not-found]
else:
    from pyplecs._contracts import (
        ConfigManagerBase,
        SimulationCacheBase,
        SimulationOrchestratorBase,
        SimulationRequest,
        SimulationResult,
        SimulationServer,
        SimulationStatus,
        StructuredLoggerBase,
        SyncSimulationRequest,
        SyncSimulationResponse,
        TaskPriority,
    )


__all__ = [
    "SimulationServer",
    "SimulationCacheBase",
    "SimulationOrchestratorBase",
    "ConfigManagerBase",
    "StructuredLoggerBase",
    "SimulationRequest",
    "SimulationResult",
    "SimulationStatus",
    "SyncSimulationRequest",
    "SyncSimulationResponse",
    "TaskPriority",
    "__contract_version__",
]
```

- [ ] **Step 2: Smoke-test the façade resolves and reports a sensible source.**

Run: `python -c "from pyplecs import contracts; print(contracts._source); print(contracts.SimulationServer)"`
Expected output:
```
vendored
<class 'pyplecs._contracts.server.SimulationServer'>
```
(`vendored` because PyPI `pycircuitsim_core` is not installed in this environment.)

- [ ] **Step 3: Commit.**

```bash
git add pyplecs/contracts.py
git commit -m "feat: add pyplecs.contracts façade with PyPI passthrough + version guard"
```

---

## Task 7: Update concrete-class imports to use `pyplecs.contracts`

**Files:**
- Modify: `pyplecs/pyplecs.py` (PlecsServer)
- Modify: `pyplecs/cache/__init__.py` (SimulationCache)
- Modify: `pyplecs/config.py` (ConfigManager)
- Modify: `pyplecs/logging/__init__.py` (StructuredLogger)
- Modify: `pyplecs/orchestration/__init__.py` (SimulationOrchestrator)

For each file, replace `from pycircuitsim_core.<module> import <BaseClass>` with `from pyplecs.contracts import <BaseClass>`. The top-level `pycircuitsim_core/` package is still in place at this point — Task 9 deletes it. After Task 7, concrete classes resolve their bases through the façade, which prefers the vendored copy.

- [ ] **Step 1: Update `pyplecs/pyplecs.py`.**

Locate the import (likely top of file, around line 10–30): `from pycircuitsim_core.server import SimulationServer` or similar. Replace with:
```python
from pyplecs.contracts import SimulationServer
```

- [ ] **Step 2: Update `pyplecs/cache/__init__.py` line 16.**

Replace `from pycircuitsim_core.cache import SimulationCacheBase` with:
```python
from pyplecs.contracts import SimulationCacheBase
```

- [ ] **Step 3: Update `pyplecs/config.py`.**

Locate `from pycircuitsim_core.config import ConfigManagerBase`. Replace with:
```python
from pyplecs.contracts import ConfigManagerBase
```

- [ ] **Step 4: Update `pyplecs/logging/__init__.py` line 11.**

Replace `from pycircuitsim_core.logging import StructuredLoggerBase` with:
```python
from pyplecs.contracts import StructuredLoggerBase
```

- [ ] **Step 5: Update `pyplecs/orchestration/__init__.py`.**

Locate `from pycircuitsim_core.orchestration import SimulationOrchestratorBase` (and possibly `from pycircuitsim_core.models import TaskPriority`). Replace with:
```python
from pyplecs.contracts import SimulationOrchestratorBase, TaskPriority
```

- [ ] **Step 6: Verify pyplecs imports without error.**

Run: `python -c "from pyplecs import PlecsServer, SimulationCache, SimulationOrchestrator; print('imports OK'); print('PlecsServer abstract:', PlecsServer.__abstractmethods__)"`
Expected:
```
PyPLECS v1.0.0 - Advanced PLECS Simulation Automation
imports OK
PlecsServer abstract: frozenset()
```
(Trailing message about pywinauto is OK.)

If `__abstractmethods__` is non-empty for any class, the concrete implementation is missing a method — see spec "Concrete-class adaptation". Add a stub raising `NotImplementedError("Pending interop port — see spec 2026-04-25")` to that class to clear the abstract.

- [ ] **Step 7: Commit.**

```bash
git add pyplecs/pyplecs.py pyplecs/cache/__init__.py pyplecs/config.py pyplecs/logging/__init__.py pyplecs/orchestration/__init__.py
git commit -m "refactor: route ABC imports through pyplecs.contracts façade"
```

---

## Task 8: Write the contract test

**Files:**
- Create: `tests/test_abc_contract.py`

This test runs without PLECS, is included in the pre-push hook list, and verifies (a) every concrete class has zero residual abstract methods, (b) inheritance is correctly wired, (c) the façade reports a sensible source.

- [ ] **Step 1: Write the failing test.**

Create `tests/test_abc_contract.py`:
```python
"""Verify pyplecs concrete classes satisfy pycircuitsim_core ABCs.

Runs without PLECS — uses class-level introspection only.
"""
from __future__ import annotations

import pytest


def test_contracts_facade_resolves():
    """The façade resolves to a known source."""
    from pyplecs import contracts

    assert contracts._source in ("pypi", "vendored")
    assert contracts.__contract_version__ == "1.0"


def test_plecs_server_subclasses_simulation_server():
    """PlecsServer inherits from contracts.SimulationServer."""
    from pyplecs.pyplecs import PlecsServer
    from pyplecs.contracts import SimulationServer

    assert issubclass(PlecsServer, SimulationServer)
    assert PlecsServer.__abstractmethods__ == frozenset(), (
        f"PlecsServer has unimplemented abstracts: {PlecsServer.__abstractmethods__}"
    )


def test_simulation_cache_subclasses_cache_base():
    from pyplecs.cache import SimulationCache
    from pyplecs.contracts import SimulationCacheBase

    assert issubclass(SimulationCache, SimulationCacheBase)
    assert SimulationCache.__abstractmethods__ == frozenset(), (
        f"SimulationCache has unimplemented abstracts: {SimulationCache.__abstractmethods__}"
    )


def test_config_manager_subclasses_config_base():
    from pyplecs.config import ConfigManager
    from pyplecs.contracts import ConfigManagerBase

    assert issubclass(ConfigManager, ConfigManagerBase)
    assert ConfigManager.__abstractmethods__ == frozenset(), (
        f"ConfigManager has unimplemented abstracts: {ConfigManager.__abstractmethods__}"
    )


def test_structured_logger_subclasses_logger_base():
    pytest.importorskip("structlog")
    from pyplecs.logging import StructuredLogger
    from pyplecs.contracts import StructuredLoggerBase

    assert issubclass(StructuredLogger, StructuredLoggerBase)
    assert StructuredLogger.__abstractmethods__ == frozenset(), (
        f"StructuredLogger has unimplemented abstracts: {StructuredLogger.__abstractmethods__}"
    )


def test_simulation_orchestrator_subclasses_orchestrator_base():
    from pyplecs.orchestration import SimulationOrchestrator
    from pyplecs.contracts import SimulationOrchestratorBase

    assert issubclass(SimulationOrchestrator, SimulationOrchestratorBase)
    assert SimulationOrchestrator.__abstractmethods__ == frozenset(), (
        f"SimulationOrchestrator has unimplemented abstracts: "
        f"{SimulationOrchestrator.__abstractmethods__}"
    )


def test_contracts_exports_complete():
    """Façade re-exports every name promised in the spec."""
    from pyplecs import contracts

    expected = {
        "SimulationServer",
        "SimulationCacheBase",
        "SimulationOrchestratorBase",
        "ConfigManagerBase",
        "StructuredLoggerBase",
        "SimulationRequest",
        "SimulationResult",
        "SimulationStatus",
        "SyncSimulationRequest",
        "SyncSimulationResponse",
        "TaskPriority",
    }
    missing = expected - set(dir(contracts))
    assert not missing, f"Missing from pyplecs.contracts: {missing}"
```

- [ ] **Step 2: Run the test to see all 7 cases pass.**

Run: `pytest -q tests/test_abc_contract.py`
Expected: `7 passed`. If any test fails with `unimplemented abstracts: frozenset({'<method_name>'})`, see Task 7 Step 6 — add a `NotImplementedError` stub for that method on the concrete class.

If `test_structured_logger_subclasses_logger_base` is skipped (no structlog), that's acceptable; the test will run when structlog is installed.

- [ ] **Step 3: Commit.**

```bash
git add tests/test_abc_contract.py
git commit -m "test: verify concrete classes satisfy pycircuitsim_core ABCs"
```

---

## Task 9: Delete top-level `pycircuitsim_core/` and update `pyproject.toml`

**Files:**
- Delete: `pycircuitsim_core/` (top-level directory, 7 files)
- Modify: `pyproject.toml` (drop from `packages.find.include`)

- [ ] **Step 1: Confirm nothing imports from the top-level `pycircuitsim_core` anymore.**

Run: `grep -rEn "^(from|import) pycircuitsim_core" pyplecs tests --include='*.py'`
Expected: zero matches inside `pyplecs/` and `tests/`. Some matches inside `pyplecs/_contracts/__init__.py` reference `pyplecs._contracts.*`, which is a different module path — that's fine.

If any unexpected matches exist, fix them to use `from pyplecs.contracts import <name>` and re-run before deleting.

- [ ] **Step 2: Delete the top-level package.**

```bash
git rm -r pycircuitsim_core
```

- [ ] **Step 3: Update `pyproject.toml`.**

Locate line 43:
```toml
[tool.setuptools.packages.find]
include = ["pyplecs*", "pycircuitsim_core*"]
```
Replace with:
```toml
[tool.setuptools.packages.find]
include = ["pyplecs*"]
```

- [ ] **Step 4: Verify `pip install -e .` from the existing venv still resolves.**

Run: `pip install -e . 2>&1 | tail -10`
Expected: ends with `Successfully installed pyplecs-1.0.0` (or similar). No mention of `pycircuitsim-core` in pip output. No new dependency resolution because we didn't add any.

- [ ] **Step 5: Re-run the contract tests to confirm nothing regressed.**

Run: `pytest -q tests/test_abc_contract.py`
Expected: `7 passed` (or `6 passed, 1 skipped` if structlog absent).

- [ ] **Step 6: Commit.**

```bash
git add pycircuitsim_core pyproject.toml
git commit -m "chore: remove top-level pycircuitsim_core stub package

The vendored ABC layer now lives at pyplecs/_contracts/ and is exposed
via the pyplecs.contracts façade. Top-level pycircuitsim_core/ is gone
so a future user installing the real pycircuitsim-core from PyPI no
longer collides with our compatibility stubs."
```

---

## Task 10: Add sync documentation

**Files:**
- Create: `tools/SYNC_PYCIRCUITSIM_CORE.md`

- [ ] **Step 1: Write the doc.**

```markdown
# Re-syncing the vendored `pyplecs/_contracts/` package

`pyplecs/_contracts/` is a vendored copy of the ABCs and shared models from
the `tinix84/pycircuitsim` monorepo. PyPLECS works standalone using this
copy. When the umbrella `pycircuitsim-core` package is published to PyPI
and installed alongside pyplecs, the `pyplecs.contracts` façade
auto-detects it and prefers the external copy (subject to the major
version guard).

## Source of truth

- Repo: `https://github.com/tinix84/pycircuitsim`
- Path: `packages/pycircuitsim-core/pycircuitsim_core/`
- Currently pinned to commit: `a065438297155d73469ebce83ef6ecb051aec8aa`

The pinned SHA appears in the header of every file in `pyplecs/_contracts/`.

## When to re-sync

- Upstream adds a new abstract method that pyplecs needs to satisfy.
- Upstream changes a model field that the canonical contract requires.
- Upstream bumps `__contract_version__` (major version bump → breaking change).

## How to re-sync

1. Look up the latest commit on `tinix84/pycircuitsim`:
   ```bash
   gh api repos/tinix84/pycircuitsim/commits/main --jq .sha
   ```

2. Fetch the seven files into `pyplecs/_contracts/`:
   ```bash
   SHA=<new_sha>
   for f in __init__.py server.py cache.py config.py logging.py orchestration.py models.py; do
     gh api repos/tinix84/pycircuitsim/contents/packages/pycircuitsim-core/pycircuitsim_core/$f?ref=$SHA \
       --jq .content | base64 -d > /tmp/$f
   done
   ```

3. For each file, **prepend** the SHA header and **rewrite** any
   `from pycircuitsim_core.<module>` imports to `from pyplecs._contracts.<module>`.
   The `__init__.py` must include `__contract_version__ = "X.Y"` and add
   `StructuredLoggerBase` to `__all__` (upstream omits it).

4. Update the SHA in this file's "Currently pinned to commit" line.

5. Run the contract test:
   ```bash
   pytest -q tests/test_abc_contract.py
   ```
   If any test fails, the re-sync introduced an abstract method that no
   pyplecs concrete satisfies. Either add a stub on the concrete (raising
   `NotImplementedError("Pending interop port")`) or revert the re-sync
   and file an issue.

6. Bump pyplecs's `__contract_version__` in `pyplecs/contracts.py` if the
   upstream major version changed. This may break the PyPI passthrough
   for users with the old upstream version installed — they fall back to
   our vendored copy automatically, which is the safe behavior.

7. Commit:
   ```bash
   git commit -am "chore: re-sync pyplecs/_contracts/ to upstream@$SHA"
   ```

## Why we vendor

Per spec `docs/superpowers/specs/2026-04-25-repo-hygiene-and-contracts-design.md`:
PyPLECS must work standalone (`pip install pyplecs` alone, no transitive
dep on pycircuitsim-core). The vendored copy is the standalone fallback;
the PyPI passthrough is the umbrella-aware upgrade path.

The vendored copy stays forever — there is no exit clause. If upstream
publishes to PyPI and a user installs both, pyplecs picks up the upstream
version automatically (subject to major-version match).
```

- [ ] **Step 2: Commit.**

```bash
git add tools/SYNC_PYCIRCUITSIM_CORE.md
git commit -m "docs: how to re-sync pyplecs/_contracts/ from upstream"
```

---

## Task 11: Final integration check

This is a single-step task that exercises everything as a whole. No new commits.

- [ ] **Step 1: Run the full pre-push hook simulation.**

```bash
CLAUDE_TOOL_INPUT='{"command":"git push origin master"}' python .claude/hooks/pre_push_lint.py
echo "exit=$?"
```
Expected:
```
[pre-push] running ruff check...
[pre-push] running platform-independent tests...
.....                                                                        [100%]
4 passed in <Ns>
[pre-push] OK
exit=0
```

If `ruff check` fails on a file in `docs/articles/` (e.g., articles directory's Python scripts have unrelated style issues), add `docs/articles/*` to the existing `pyproject.toml` `[tool.ruff.lint.per-file-ignores]` block:
```toml
[tool.ruff.lint.per-file-ignores]
"tests/*" = ["F841"]
"docs/articles/*" = ["F841"]   # was articles/* — retargeted in Task 4
```
Commit that as a small follow-up.

- [ ] **Step 2: Verify mkdocs still builds.**

```bash
mkdocs build --strict 2>&1 | tail -10
```
Expected: `INFO    -  Documentation built in N.NN seconds`. No `ERROR` or `WARNING` about broken links.

- [ ] **Step 3: Verify standalone install from a clean venv.**

```bash
python -m venv /tmp/pyplecs-fresh
/tmp/pyplecs-fresh/bin/python -m pip install -e . 2>&1 | tail -10
/tmp/pyplecs-fresh/bin/python -c "from pyplecs import contracts; print('source:', contracts._source); print('contract:', contracts.__contract_version__)"
rm -rf /tmp/pyplecs-fresh
```
Expected: `source: vendored`, `contract: 1.0`. No mention of `pycircuitsim-core` in pip output.

(On Windows: substitute `/tmp/pyplecs-fresh/Scripts/python.exe` and use `rmdir /s /q` for cleanup.)

- [ ] **Step 4: Confirm the four commit categories are present in `git log`.**

```bash
git log --oneline -n 10
```
Expected to see, top to bottom (most recent first):
- `docs: how to re-sync pyplecs/_contracts/ from upstream`
- `chore: remove top-level pycircuitsim_core stub package`
- `test: verify concrete classes satisfy pycircuitsim_core ABCs`
- `refactor: route ABC imports through pyplecs.contracts façade`
- `feat: add pyplecs.contracts façade with PyPI passthrough + version guard`
- `feat: vendor pycircuitsim_core ABCs at pyplecs/_contracts/`
- `chore: move articles under docs/articles for mkdocs`
- `chore: unify lint on ruff (drop black/flake8/mypy/isort references)`
- `chore: remove GitHub Actions CI in favor of pre-push hook`
- `chore: pre-push hook now runs ruff + platform-independent tests`

---

## Acceptance criteria (from spec)

After all tasks complete, all of these must hold:

- [ ] `pip install -e .` from a clean venv succeeds with no mention of `pycircuitsim-core` in pip output.
- [ ] `pytest tests/test_abc_contract.py` passes (7 tests, possibly 1 skipped if structlog absent).
- [ ] `ruff check .` passes (or only fails on pre-existing issues unrelated to this PR — note them in the PR description).
- [ ] `mkdocs build --strict` succeeds and renders the Articles nav section.
- [ ] No `.github/workflows/ci.yml` file remains.
- [ ] No top-level `pycircuitsim_core/` directory remains; `pyplecs/_contracts/` exists with the SHA-pinned vendored files.
- [ ] `python -c "from pyplecs.contracts import _source; print(_source)"` outputs `vendored` in a clean venv (since PyPI `pycircuitsim_core` is not installed).
