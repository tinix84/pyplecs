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
