"""Simple installer/initializer CLI for PyPLECS.

This module provides:
- write_default_config(target) -> create a default config file
- check-windows / check-macos checks to validate common prerequisites
- a small CLI entrypoint exposed as `pyplecs-setup`

The implementation is intentionally conservative and dependency-free so it
can run on fresh Python installs.
"""

from __future__ import annotations

import argparse
import platform
import shutil
import sys
import subprocess
from pathlib import Path
from typing import List, Dict

DEFAULT_CONFIG = """# Minimal PyPLECS generated config
app:
  name: "PyPLECS"
  version: "0.1.0"

plecs:
  executable_paths: []

webgui:
  enabled: true
  host: "0.0.0.0"
  port: 8080

paths:
  results: "./results"
  cache: "./cache"
  logs: "./logs"
  static: "./static"
  templates: "./templates"
"""

COMMON_PIP_PACKAGES = ["fastapi", "uvicorn", "jinja2", "pandas", "pyyaml"]

# Optional python packages useful for full feature set
OPTIONAL_PIP_PACKAGES = ["aiofiles", "websockets", "python-multipart", "aioredis"]

# System packages mapping by platform (conservative / non-exhaustive)
SYSTEM_PACKAGES = {
    "Darwin": ["python3", "brew"],  # brew is used to install system deps
    "Linux": ["python3", "build-essential"],
    "Windows": [],
}


def install_packages(packages: List[str], auto_yes: bool = False) -> Dict[str, object]:
    """Install missing packages using pip (invokes the current Python's pip).

    Returns a result dict with installed and failed lists.
    If auto_yes is False the user will be prompted before installing.
    """
    results = {"installed": [], "failed": [], "skipped": [], "missing": []}

    # Determine which packages are missing
    pkg_status = check_python_packages(packages)
    missing = [p for p, ok in pkg_status.items() if not ok]
    results["missing"] = missing

    if not missing:
        return results

    if not auto_yes:
        print("The following packages are missing and will be installed:")
        for p in missing:
            print("  -", p)
        ans = input("Proceed to install? [y/N]: ").strip().lower()
        if ans not in ("y", "yes"):
            results["skipped"] = missing
            return results

    # Use current Python executable to install
    pip_cmd = [sys.executable, "-m", "pip", "install"]
    for pkg in missing:
        try:
            print(f"Installing {pkg}...")
            subprocess.check_call(pip_cmd + [pkg])
            results["installed"].append(pkg)
        except subprocess.CalledProcessError:
            results["failed"].append(pkg)
    return results


def install_system_packages(
    packages: List[str], auto_yes: bool = False
) -> Dict[str, object]:
    """Attempt to install system packages using the platform's package manager.

    This function is conservative: it detects `brew` on macOS or `apt-get` on
    Debian-like Linux and will attempt to run an install command. On Windows it
    will only print instructions.
    """
    res = {"attempted": [], "installed": [], "failed": [], "skipped": []}
    plat = platform.system()

    if plat == "Darwin":
        # prefer brew
        brew = shutil.which("brew")
        if not brew:
            res["skipped"] = packages
            return res
        cmd = ["brew", "install"] + packages
    elif plat == "Linux":
        apt = shutil.which("apt-get")
        if not apt:
            res["skipped"] = packages
            return res
        cmd = [
            "sudo",
            "apt-get",
            "update",
            "&&",
            "sudo",
            "apt-get",
            "install",
            "-y",
        ] + packages
    else:
        # Windows / unknown - don't attempt to run system installers
        res["skipped"] = packages
        return res

    res["attempted"] = packages
    try:
        # Note: shell usage because of '&&' on apt-get compound command
        subprocess.check_call(" ".join(cmd), shell=True)
        res["installed"] = packages
    except subprocess.CalledProcessError:
        res["failed"] = packages
    return res


def write_default_config(target: str | Path = None) -> str:
    """Write a minimal default config to target path and return the path.

    Default location: ./config/default.yml
    """
    target_path = Path(target or Path.cwd() / "config" / "default.yml")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(DEFAULT_CONFIG)
    return str(target_path)


def check_python_packages(packages: List[str]) -> Dict[str, bool]:
    """Check if listed Python packages can be imported.

    Returns a dict of package -> bool.
    """
    results = {}
    for pkg in packages:
        try:
            __import__(pkg)
            results[pkg] = True
        except Exception:
            results[pkg] = False
    return results


def check_windows_installation() -> Dict[str, object]:
    """Run a few conservative checks for Windows installations.

    The function can be run on any platform; it will report which checks are
    applicable. It returns a result dict suitable for printing.
    """
    result = {"platform": platform.system(), "ok": True, "checks": {}}

    # Python version
    py_ok = sys.version_info >= (3, 8)
    result["checks"]["python_version"] = py_ok
    if not py_ok:
        result["ok"] = False

    # pip packages
    pkg_results = check_python_packages(COMMON_PIP_PACKAGES)
    result["checks"]["python_packages"] = pkg_results
    if not all(pkg_results.values()):
        result["ok"] = False

    # PLECS executable common windows locations
    possible = [
        r"C:\Program Files\Plexim\PLECS 4.7 (64 bit)\plecs.exe",
        r"C:\Program Files\Plexim\PLECS 4.6 (64 bit)\plecs.exe",
        r"C:\Program Files\Plexim\PLECS 4.5 (64 bit)\plecs.exe",
    ]
    found = [p for p in possible if Path(p).exists()]
    result["checks"]["plecs_paths_found"] = found
    if not found:
        # Not fatal; user may have a custom installation
        result["checks"]["plecs_note"] = (
            "No common PLECS paths found; add your path to config"
        )

    return result


def check_macos_installation() -> Dict[str, object]:
    """Run a few conservative checks for macOS installations.

    Checks for Python, pip packages and typical Mac installation places.
    """
    result = {"platform": platform.system(), "ok": True, "checks": {}}

    py_ok = sys.version_info >= (3, 8)
    result["checks"]["python_version"] = py_ok
    if not py_ok:
        result["ok"] = False

    pkg_results = check_python_packages(COMMON_PIP_PACKAGES)
    result["checks"]["python_packages"] = pkg_results
    if not all(pkg_results.values()):
        result["ok"] = False

    # Typical macOS PLECS app bundle or binary
    possible = [
        "/Applications/PLECS.app",
        "/usr/local/bin/plecs",
        "/opt/homebrew/bin/plecs",
    ]
    found = [p for p in possible if Path(p).exists()]
    result["checks"]["plecs_paths_found"] = found
    if not found:
        result["checks"]["plecs_note"] = (
            "No common PLECS paths found; add your path to config"
        )

    return result


def print_result(res: Dict[str, object]) -> None:
    print("\n=== PyPLECS setup check ===")
    print(f"Platform: {res.get('platform')}")
    print(f"Overall OK: {res.get('ok')}")
    for k, v in res.get("checks", {}).items():
        print(f"- {k}: {v}")
    print("===========================\n")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pyplecs-setup", description="PyPLECS setup helper"
    )
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser(
        "create-config", help="Create a default config in ./config/default.yml"
    )
    sub.add_parser("check-windows", help="Run a conservative set of checks for Windows")
    sub.add_parser("check-macos", help="Run a conservative set of checks for macOS")
    sub.add_parser("check-all", help="Run all checks appropriate for this platform")
    sub_install = sub.add_parser(
        "install-packages", help="Install common Python packages required by PyPLECS"
    )
    sub_install.add_argument(
        "--yes", "-y", action="store_true", help="Automatically confirm installation"
    )
    sub_install.add_argument(
        "--packages",
        "-p",
        type=str,
        default=None,
        help="Comma-separated list of packages to install (overrides defaults)",
    )
    sub_install.add_argument(
        "--full",
        "-f",
        action="store_true",
        help="Install optional Python packages and attempt system packages for this platform",
    )

    args = parser.parse_args(argv)

    if args.cmd == "create-config":
        path = write_default_config()
        print(f"Wrote default config to: {path}")
        return 0

    if args.cmd == "check-windows":
        res = check_windows_installation()
        print_result(res)
        return 0 if res.get("ok") else 2

    if args.cmd == "check-macos":
        res = check_macos_installation()
        print_result(res)
        return 0 if res.get("ok") else 2

    if args.cmd == "install-packages":
        pkgs = COMMON_PIP_PACKAGES
        auto_yes = bool(getattr(args, "yes", False))
        if getattr(args, "packages", None):
            pkgs = [p.strip() for p in args.packages.split(",") if p.strip()]

        all_results = {"pip": {}, "optional": {}, "system": {}}

        # Install main packages
        res = install_packages(pkgs, auto_yes=auto_yes)
        all_results["pip"] = res

        # If --full: install optional python packages, then try system packages
        if getattr(args, "full", False):
            opt_res = install_packages(OPTIONAL_PIP_PACKAGES, auto_yes=auto_yes)
            all_results["optional"] = opt_res

            # Determine system packages to attempt for this platform
            plat = platform.system()
            sys_pkgs = SYSTEM_PACKAGES.get(plat, [])
            if sys_pkgs:
                sys_res = install_system_packages(sys_pkgs, auto_yes=auto_yes)
            else:
                sys_res = {"skipped": []}
            all_results["system"] = sys_res

        print("\nInstall result:")
        print(all_results)
        # Determine exit code: 0 if at least one of pip/optional completed without missing installs
        any_installed = bool(
            all_results["pip"].get("installed")
            or all_results.get("optional", {}).get("installed")
        )
        if not any_installed:
            return 3
        return 0

    if args.cmd == "check-all" or args.cmd is None:
        plat = platform.system()
        if plat == "Windows":
            res = check_windows_installation()
        elif plat == "Darwin":
            res = check_macos_installation()
        else:
            # Generic checks for other systems (Linux)
            res = {"platform": plat, "ok": True, "checks": {}}
            res["checks"]["python_version"] = sys.version_info >= (3, 8)
            res["checks"]["python_packages"] = check_python_packages(
                COMMON_PIP_PACKAGES
            )
            res["ok"] = (
                all(res["checks"]["python_packages"].values())
                and res["checks"]["python_version"]
            )
        print_result(res)
        return 0 if res.get("ok") else 2

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
