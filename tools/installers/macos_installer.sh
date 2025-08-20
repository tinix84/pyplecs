#!/usr/bin/env bash
# Minimal macOS installer helper for PyPLECS
# Run from the project root after activating a Python venv

python3 -m pyplecs.cli.installer create-config
python3 -m pyplecs.cli.installer check-macos

echo "Done. Please edit config/default.yml to add your PLECS executable path if needed."
