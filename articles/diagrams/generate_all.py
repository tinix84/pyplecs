#!/usr/bin/env python3
"""
Generate All Diagrams for PyPLECS Article Series

This script generates all matplotlib charts and architecture diagrams.
Mermaid diagrams are already in markdown format and don't need generation.

Usage:
    python generate_all.py
    python generate_all.py --skip-diagrams  # Skip diagrams library (if Graphviz not installed)
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def check_dependencies():
    """Check if required Python packages are installed."""
    missing = []

    try:
        import matplotlib
        import numpy
        import seaborn
    except ImportError as e:
        missing.append("matplotlib/numpy/seaborn")

    try:
        import diagrams
    except ImportError:
        missing.append("diagrams (optional - for architecture diagrams)")

    return missing


def run_script(script_path, description):
    """Run a Python script and report results."""
    print(f"\n{'='*60}")
    print(f"[*] {description}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=True
        )

        # Print output
        if result.stdout:
            print(result.stdout)

        print(f"[PASS] {description} completed successfully")
        return True

    except subprocess.CalledProcessError as e:
        print(f"[FAIL] Error running {description}:")
        print(e.stderr)
        return False


def create_output_directory():
    """Ensure output directory exists."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    print(f"Output directory: {output_dir.absolute()}")


def main():
    parser = argparse.ArgumentParser(description="Generate all PyPLECS article diagrams")
    parser.add_argument(
        "--skip-diagrams",
        action="store_true",
        help="Skip diagrams library (requires Graphviz)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("PyPLECS Article Series - Diagram Generator")
    print("=" * 60)

    # Check dependencies
    print("\nChecking dependencies...")
    missing = check_dependencies()

    if missing:
        print("\n[WARNING] Missing dependencies:")
        for pkg in missing:
            print(f"   - {pkg}")

        if "diagrams" in str(missing) and not args.skip-diagrams:
            print("\n[TIP] Use --skip-diagrams to skip architecture diagram generation")

        if "matplotlib" in str(missing):
            print("\n[ERROR] matplotlib/numpy/seaborn are required")
            print("   Install with: pip install matplotlib numpy seaborn")
            return 1

    # Create output directory
    create_output_directory()

    # Track results
    results = []

    # Generate performance comparison charts
    script_path = Path("python/performance_comparison.py")
    if script_path.exists():
        success = run_script(
            script_path,
            "Generating Performance Comparison Charts"
        )
        results.append(("Performance Charts", success))
    else:
        print(f"\n[WARNING] Script not found: {script_path}")
        results.append(("Performance Charts", False))

    # Generate architecture diagrams (optional)
    if not args.skip-diagrams:
        script_path = Path("python/architecture_diagrams.py")
        if script_path.exists():
            try:
                import diagrams
                success = run_script(
                    script_path,
                    "Generating Architecture Diagrams"
                )
                results.append(("Architecture Diagrams", success))
            except ImportError:
                print("\n[WARNING] diagrams library not installed")
                print("   Install with: pip install diagrams")
                print("   Also requires Graphviz: https://graphviz.org/download/")
                results.append(("Architecture Diagrams", False))
        else:
            print(f"\n[WARNING] Script not found: {script_path}")
            results.append(("Architecture Diagrams", False))
    else:
        print("\n[SKIP] Skipping architecture diagrams (--skip-diagrams flag)")

    # Summary
    print("\n" + "=" * 60)
    print("Generation Summary")
    print("=" * 60)

    all_success = True
    for name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} {name}")
        if not success:
            all_success = False

    # Mermaid note
    print("\n[NOTE] Mermaid diagrams are already in markdown format")
    print("   Location: mermaid/*.md")
    print("   They render automatically in GitHub/GitLab")

    # List generated files
    output_dir = Path("output")
    if output_dir.exists():
        files = list(output_dir.glob("*.png"))
        if files:
            print(f"\nGenerated {len(files)} image file(s):")
            for f in sorted(files):
                size_kb = f.stat().st_size / 1024
                print(f"   - {f.name} ({size_kb:.1f} KB)")
        else:
            print("\n[WARNING] No files generated in output/ directory")

    print("\n" + "=" * 60)

    if all_success:
        print("[SUCCESS] All diagrams generated successfully!")
        print("\nNext steps:")
        print("1. Review generated images in output/ directory")
        print("2. Embed diagrams in articles using markdown/HTML")
        print("3. Verify all diagrams render correctly")
        return 0
    else:
        print("[WARNING] Some diagrams failed to generate")
        print("\nCheck error messages above for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())
