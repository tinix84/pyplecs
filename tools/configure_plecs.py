"""Interactive PLECS executable path configuration.

Reads config/default.yml, auto-discovers PLECS installations,
prompts user to confirm or change the path, saves back to YAML.

Called by setup_env.bat AFTER the Python environment is activated
and dependencies (including PyYAML) are installed.
"""

import sys
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent.parent / "config" / "default.yml"


def _find_plecs_candidates() -> list[str]:
    """Search common installation paths for PLECS."""
    candidates = []
    search_dirs = [
        Path("D:/OneDrive/Documenti/Plexim"),
        Path("C:/Program Files/Plexim"),
        Path("C:/Program Files (x86)/Plexim"),
    ]
    for base in search_dirs:
        if base.exists():
            for d in sorted(base.iterdir(), reverse=True):
                exe = d / "plecs.exe"
                if exe.exists():
                    candidates.append(str(exe))
    return candidates


def main():
    if not CONFIG_PATH.exists():
        print(f"[ERROR] Config not found: {CONFIG_PATH}")
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)

    plecs_cfg = cfg.get("plecs", {})
    exe_paths = plecs_cfg.get("executable_paths", [])
    current = exe_paths[0] if exe_paths else ""
    candidates = _find_plecs_candidates()

    print("  ── PLECS Path ──")
    print()

    if current and Path(current).exists():
        print(f"  Current path (valid): {current}")
    elif current:
        print(f"  Current path (NOT FOUND): {current}")

    if candidates:
        print()
        print("  Auto-discovered installations:")
        for i, c in enumerate(candidates, 1):
            marker = " <-- current" if c == current else ""
            print(f"    [{i}] {c}{marker}")

    print()

    # Determine default
    default = current if (current and Path(current).exists()) else ""
    if not default and candidates:
        default = candidates[0]

    prompt = f"  PLECS executable path [{default}]: " if default else "  PLECS executable path: "
    user_input = input(prompt).strip()
    chosen = user_input if user_input else default

    # Handle numeric selection
    if chosen.isdigit() and candidates:
        idx = int(chosen) - 1
        if 0 <= idx < len(candidates):
            chosen = candidates[idx]

    if not chosen:
        print("[ERROR] No path provided.")
        sys.exit(1)

    if not Path(chosen).exists():
        print(f"[ERROR] File not found: {chosen}")
        sys.exit(1)

    if "plecs" not in cfg:
        cfg["plecs"] = {}
    cfg["plecs"]["executable_paths"] = [str(Path(chosen))]

    with open(CONFIG_PATH, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)

    print()
    print(f"  [OK] PLECS path saved: {chosen}")
    print(f"  [OK] Config updated: {CONFIG_PATH}")
    print()


if __name__ == "__main__":
    main()
