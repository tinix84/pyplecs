# Test import shim so tests can use `from context import pyplecs`
import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the package so tests can access it as `context.pyplecs`
import pyplecs
