#!/usr/bin/env python3
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
