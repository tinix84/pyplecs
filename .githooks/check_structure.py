#!/usr/bin/env python3
"""Structural rules that ADR-0004 depends on, checked at push time.

A rule nothing checks gets contradicted -- which is how ``docs/`` reached 97
files before ADR-0004. Invoked by ``.githooks/pre-push``; exits non-zero with
one line per violation.
"""
import sys
from pathlib import Path

# ADR-0004: docs/ holds decisions, terms, roadmap, research, agent conventions.
DOCS_ALLOWED_DIRS = {"adr", "agents", "research"}
DOCS_ALLOWED_FILES = {"index.md", "story-map.md"}

README_MAX_LINES = 150


def check_docs_frozen(root: Path) -> list[str]:
    """Nothing in docs/ outside the allowlist."""
    docs = root / "docs"
    if not docs.is_dir():
        return []
    errors = []
    for entry in sorted(docs.iterdir()):
        if entry.is_dir():
            if entry.name not in DOCS_ALLOWED_DIRS:
                errors.append(f"docs/{entry.name}/ is not an allowed docs directory")
        elif entry.name not in DOCS_ALLOWED_FILES:
            errors.append(f"docs/{entry.name} is not an allowed docs file")
    return errors


def check_readme_cap(root: Path) -> list[str]:
    """README is the only user-facing doc, and it stays short."""
    readme = root / "README.md"
    if not readme.is_file():
        return ["README.md is missing"]
    n = len(readme.read_text(encoding="utf-8").splitlines())
    if n > README_MAX_LINES:
        return [f"README.md is {n} lines, cap is {README_MAX_LINES}"]
    return []


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = check_docs_frozen(root) + check_readme_cap(root)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
