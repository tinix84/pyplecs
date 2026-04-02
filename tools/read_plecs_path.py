"""Read configuration from config/default.yml for batch script consumption.

Usage:
    python tools/read_plecs_path.py plecs    → prints PLECS exe path
    python tools/read_plecs_path.py env_type → prints 'venv' or 'conda'
    python tools/read_plecs_path.py env_name → prints conda env name (or empty)
"""

import sys
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent.parent / "config" / "default.yml"


def main():
    if len(sys.argv) < 2:
        print("Usage: read_plecs_path.py [plecs|env_type|env_name]", file=sys.stderr)
        sys.exit(1)

    key = sys.argv[1]

    if not CONFIG_PATH.exists():
        print(f"ERROR: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)

    if key == "plecs":
        exe_paths = cfg.get("plecs", {}).get("executable_paths", [])
        for p in exe_paths:
            if Path(p).exists():
                print(p)
                return
        print("ERROR: No valid PLECS path in config", file=sys.stderr)
        sys.exit(1)

    elif key == "env_type":
        print(cfg.get("python", {}).get("env_type", "venv"))

    elif key == "env_name":
        print(cfg.get("python", {}).get("env_name", ""))

    elif key == "conda_root":
        print(cfg.get("python", {}).get("conda_root", ""))

    else:
        print(f"ERROR: Unknown key '{key}'", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
