#!/usr/bin/env python3
"""
Test runner for all PyPLECS examples
This script validates that all examples can be imported and run correctly.
"""

import os
import sys
import subprocess
import traceback
from pathlib import Path

# Ensure we're running from the correct directory
script_dir = Path(__file__).parent
project_root = script_dir.parent
os.chdir(project_root)

def run_example(example_path):
    """Run a single example and capture its output"""
    try:
        # Set up environment
        env = os.environ.copy()
        env['PYTHONPATH'] = str(project_root)
        
        # Run the example
        result = subprocess.run(
            [sys.executable, str(example_path)],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout
            env=env
        )
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': 'Example timed out after 60 seconds',
            'returncode': -1
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': f'Exception running example: {e}',
            'returncode': -2
        }

def main():
    """Test all examples"""
    print("PyPLECS Examples Test Runner")
    print("=" * 40)
    
    examples_dir = project_root / "examples"
    if not examples_dir.exists():
        print(f"❌ Examples directory not found: {examples_dir}")
        return False
    
    # Find all Python files in examples directory
    example_files = list(examples_dir.glob("*.py"))
    
    if not example_files:
        print(f"❌ No example files found in {examples_dir}")
        return False
    
    print(f"Found {len(example_files)} example files")
    print()
    
    results = {}
    
    for example_file in sorted(example_files):
        example_name = example_file.name
        print(f"Testing {example_name}...")
        
        result = run_example(example_file)
        results[example_name] = result
        
        if result['success']:
            print(f"✅ {example_name} - PASSED")
        else:
            print(f"❌ {example_name} - FAILED")
            if result['stderr']:
                print(f"   Error: {result['stderr'][:200]}...")
        print()
    
    # Summary
    passed = sum(1 for r in results.values() if r['success'])
    total = len(results)
    
    print("=" * 40)
    print(f"SUMMARY: {passed}/{total} examples passed")
    
    if passed < total:
        print("\nFAILED EXAMPLES:")
        for name, result in results.items():
            if not result['success']:
                print(f"- {name}: {result['stderr'][:100]}...")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
