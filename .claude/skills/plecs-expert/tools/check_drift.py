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
